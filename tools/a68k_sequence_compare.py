#!/usr/bin/env python3
"""Continuous original A68K dispatch versus portable scratch propagation.

ROM-free streams enter unchanged 00462b1c and use the native dispatch table.
No register reinjection between original instructions. Synthetic write callback
observes a final Scc; its outgoing scratch is not a continuation claim.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import re
import struct
import subprocess
import tempfile
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,RAM,WRITE,CALL
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *

ROOT=Path(__file__).resolve().parents[1]
WORDS=41

def words(code):return [word for block in code for word in (block if isinstance(block,tuple) else (block,))]
def opcode(block):return block[0] if isinstance(block,tuple) else block

class ChainOracle(Oracle):
    def __init__(self,exe):
        super().__init__(exe)
        self.table=decode_dispatch(self.pe)[3]
        self.put(0x531216,*self.table)
        self.put(WRITE,*([0,CALL+128,CALL+128,CALL+128]*4096))
        self.entries=set(self.table);self.trace=[];self.limit=0;self.terminal=False
        self.writes=[];self.callback_eax=0;self.callback_control_xor=0
    def snapshot(self,boundary=1,valid=1):
        return self.get(CTX,33)+[self.u.reg_read(UC_X86_REG_ESI),self.u.reg_read(UC_X86_REG_EDX),
            self.get(0x10ed9b0)[0],self.u.reg_read(UC_X86_REG_EAX),
            self.u.reg_read(UC_X86_REG_EFLAGS)&~0x8d5,valid,boundary,valid]
    def configure_bus(self):
        self.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
    def hook(self,u,at,size,data):
        if at in self.entries:
            self.trace.append(self.snapshot(valid=int(not(self.terminal and len(self.trace)==self.limit))))
            if len(self.trace)>self.limit:
                self.stop=at;u.emu_stop();return
        if at==CALL+128:
            self.writes.append([u.reg_read(UC_X86_REG_ECX),u.reg_read(UC_X86_REG_EDX)])
            self.ret(self.callback_eax)
            u.reg_write(UC_X86_REG_EFLAGS,u.reg_read(UC_X86_REG_EFLAGS)^self.callback_control_xor);return
        super().hook(u,at,size,data)
    def stream(self,c,cycles,eax,host,code,terminal,callback_eax=0,callback_control_xor=0):
        self.trace=[];self.writes=[];self.limit=len(code);self.terminal=terminal
        self.callback_eax=callback_eax;self.callback_control_xor=callback_control_xor
        self.setup_exception(c,cycles)
        self.put(0x10ed9ac,(RAM-c[20])&0xffffffff)
        program=words(code)
        self.u.mem_write(RAM,struct.pack('<'+'H'*(len(program)+1),*program,0x4e71))
        self.configure_bus()
        try:self.run(0x462b1c,{UC_X86_REG_EAX:eax,UC_X86_REG_EFLAGS:host},count=100000)
        except Exception as error:
            raise AssertionError(('native-stream',hex(self.u.reg_read(UC_X86_REG_EIP)),hex(self.u.reg_read(UC_X86_REG_ESP)),code,cycles,self.trace,self.writes)) from error
        if self.stop is None:
            # POPAD restores host caller registers; live PC/EDX were published.
            out=self.snapshot(2,0);out[33]=out[20];out[34]=out[18];self.trace.append(out)
        return self.trace,self.writes

class ChainPortable:
    def __init__(self,lib):
        self.lib=C.CDLL(str(lib));f=self.lib.a68k_probe_sequence
        f.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.POINTER(C.c_uint32),C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
        f.restype=C.c_int
    def stream(self,c,cycles,eax,host,code,table,terminal,callback_eax=0,callback_control_xor=0):
        code=words(code)
        data=(C.c_uint32*38)(*c,cycles&0xffffffff,eax,host,callback_eax,callback_control_xor)
        ops=(C.c_uint16*len(code))(*code);targets=(C.c_uint32*len(code))(*(table[op] for op in code))
        out=(C.c_uint32*(4+(len(code)+1)*WORDS+len(code)*2))()
        assert self.lib.a68k_probe_sequence(data,ops,targets,len(code),terminal,out)
        n=out[0];trace=[list(out[4+i*WORDS:4+(i+1)*WORDS]) for i in range(n+1)]
        start=4+(len(code)+1)*WORDS
        return trace,[list(out[start+i*2:start+i*2+2]) for i in range(out[1])]

def compare_sequences(exe,portable):
    o=ChainOracle(exe);rng=random.Random(0xa685e0);digest=hashlib.sha256()
    specs={int(t,16):(name,int(cost)) for t,name,bits,cost in re.findall(
        r'A68K_REG\((0x[0-9a-f]+), (\w+), (\d+), (\d+)\)',(ROOT/'port/a68k/register_ops.inc').read_text())}
    specs[0x478438]=('MOVEQ',4)
    for t,cc in re.findall(r'A68K_CONTROL\((0x[0-9a-f]+), SCC, (\d+)\)',(ROOT/'port/a68k/control_ops.inc').read_text()):specs[int(t,16)]=('SCC',6)
    lengths={t:0 for t in specs}
    for t,name,bits,cost,mask in re.findall(r'A68K_BINARY\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\d+)\)',(ROOT/'port/a68k/binary_ops.inc').read_text()):
        t=int(t,16);specs[t]=(name,int(cost));lengths[t]=0
    for t,name,bits,cost,source in re.findall(r'A68K_OPERAND\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',(ROOT/'port/a68k/operand_ops.inc').read_text()):
        t=int(t,16);specs[t]=(name,int(cost));lengths[t]=(2 if int(bits)==32 else 1) if source.startswith('IMMEDIATE') else 0
    shifts={}
    for t,bits,left,extend,variable,cost in re.findall(r'A68K_ROTATE\((0x[0-9a-f]+), (\d+), (\d+), (\d+), (\d+), (\d+)\)',(ROOT/'port/a68k/rotate_ops.inc').read_text()):
        t=int(t,16);specs[t]=('ROTATE',int(cost));lengths[t]=0;shifts[t]=int(variable)
    for t,name,bits,variable,cost,special in re.findall(r'A68K_SHIFT_REGISTER\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\d+), (\d+)\)',(ROOT/'port/a68k/shift_register_ops.inc').read_text()):
        t=int(t,16);specs[t]=(name,int(cost));lengths[t]=0;shifts[t]=int(variable)
    for t,name,cost,source in re.findall(r'A68K_BIT\((0x[0-9a-f]+), (\w+), 32, (\d+), REGISTER, (\w+)\)',(ROOT/'port/a68k/bit_ops.inc').read_text()):
        t=int(t,16);specs[t]=(name,int(cost));lengths[t]=int(source=='IMMEDIATE_LOW')
    for t,sign,cost,mode in re.findall(r'A68K_MULTIPLY\((0x[0-9a-f]+), (\d+), (\d+), (REGISTER|IMMEDIATE)\)',(ROOT/'port/a68k/multiply_ops.inc').read_text()):
        t=int(t,16);specs[t]=('MUL',int(cost));lengths[t]=int(mode=='IMMEDIATE')
    for t,sign in re.findall(r'A68K_BCD_REGISTER\((0x[0-9a-f]+), (\d+)\)',(ROOT/'port/a68k/bcd_register_ops.inc').read_text()):
        t=int(t,16);specs[t]=('BCD',6);lengths[t]=0
    specs[0x486680]=('NBCD',6);lengths[0x486680]=0
    memory_conditions={}
    for t,cc,cost,mode in re.findall(r'A68K_SCC_MEMORY\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',(ROOT/'port/a68k/scc_memory_ops.inc').read_text()):
        t=int(t,16);specs[t]=('MEM_SCC',int(cost));lengths[t]=2 if mode=='ABS32' else int(mode in ('DISP16','INDEXED','ABS16'));memory_conditions[t]=int(cc)
    def instruction(op):return (op,*(rng.getrandbits(16) for _ in range(lengths[o.table[op]])))
    bytarget={t:[op for op,v in enumerate(o.table) if v==t] for t in specs}
    opcodes=[op for op,t in enumerate(o.table) if t in specs]
    cases=0;steps=0;entries=set();transitions=set()
    def check(code,cycles,eax,host,c,terminal,key,callback_eax=0,callback_control_xor=0):
        nonlocal cases,steps
        native,writes=o.stream(c,cycles,eax,host,code,terminal,callback_eax,callback_control_xor)
        actual,pwrites=portable.stream(c,cycles,eax,host,code,o.table,terminal,callback_eax,callback_control_xor)
        assert len(native)==len(actual),(key,'length',len(native),len(actual))
        for i,(a,b) in enumerate(zip(actual,native)):
            if not a[38]:
                # EAX/control flags after host return are outside the next-entry contract.
                b[36:38]=a[36:38]
            assert a==b,(key,i,a,b)
            if i<len(code):entries.add(o.table[opcode(code[i])])
            if i and i<len(code):transitions.add((o.table[opcode(code[i-1])],o.table[opcode(code[i])]))
        assert pwrites==writes,(key,'write',pwrites,writes)
        steps+=len(actual)-1;cases+=1
        digest.update(json.dumps([key,actual,pwrites],sort_keys=True).encode())
    values=(0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x7fffffff,0x80000000,0xffffffff,0xa5c3e791)
    # Every qualified encoding drives a following full-register Scc write.
    # NOP between them proves preservation rather than repeated initialization.
    for op in opcodes:
        name,cost=specs[o.table[op]]
        for k in range(4):
            c=[rng.getrandbits(32) for _ in range(33)];c[20]=0x1000;c[17]=0x27
            c[21]=(0,1,6,0)[k];c[18]=(0x202,0xa43,0x2c3,0x602)[k];c[19]=k&1
            c[(8 if name=='TST_A' else 0)+(op&7)]=values[(op+k)%len(values)]
            cc=(op+k)%16;last=0x50d0+(cc<<8);c[8+(last&7)]=0x123456
            code=[instruction(op),0x4e71,last];eax=(0,0xffffffff,0x12345678,0x89abcdef)[k]
            # Exit just after, or just before, the terminal write.
            budget=(1000,1001,cost-1,0xffffffff)[k]
            check(code,budget,eax,(0x202,0x602)[k&1],c,True,(op,k),eax^0xa5c3e791,0x400 if k&1 else 0)
    # Every signed/unsigned register condition followed by MOVEQ distinguishes
    # host DF inherited from the caller from DF restored out of guest/live EDX.
    for op in opcodes:
        if specs[o.table[op]][0]!='SCC':continue
        for ccr in range(16):
            for df in range(4):
                c=[rng.getrandbits(32) for _ in range(33)];c[20]=0x1800;c[17]=0x27;c[21]=0
                c[18]=2|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)|(0x400 if df&1 else 0)
                c[19]=ccr&1;c[8]=0x123456
                check([op,0x70ff,0x4e71,0x50d0],100,0x89abcdef,
                      0x202|(0x400 if df&2 else 0),c,True,('conditions',op,ccr,df))
    for target,variable in shifts.items():
        for count in (0,1,8,16,31,32,33,63):
            for value in (0,0xffffffff,0x89abcdef):
                for alias in (False,True):
                    candidates=[op for op in bytarget[target] if (((op>>9)&7)==(op&7))==alias]
                    if not candidates:continue
                    op=candidates[0]
                    c=[rng.getrandbits(32) for _ in range(33)];c[20]=0x1800;c[17]=0x27;c[21]=0;c[18]=0xa43;c[19]=count&1
                    c[op&7]=value
                    if variable:c[(op>>9)&7]=count
                    check([op,0x4e71,0x50d0],1000,0x76543210,0x602,c,True,('shift',target,count,value,alias))
    for target,cc in memory_conditions.items():
        for ccr in range(16):
            for df in range(4):
                op=bytarget[target][ccr%len(bytarget[target])]
                c=[rng.getrandbits(32) for _ in range(33)];c[20]=0x1800;c[17]=0x27;c[21]=0
                c[18]=2|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)|(0x400 if df&1 else 0);c[19]=ccr&1
                check([instruction(op),0x4e71,0x70ff,0x50d0,0x4e71],1000,0x89abcdef,
                      0x202|(0x400 if df&2 else 0),c,False,('memory-conditions',target,ccr,df),
                      (0,0xffffffff,0x12345678,0x89abcdef)[df],0x400 if df&2 else 0)
    # Longer native runs mix producers and retainers; boundaries include zero,
    # positive and exhausted budgets. No re-entry or oracle-provided scratch.
    for k in range(1024):
        c=[rng.getrandbits(32) for _ in range(33)];c[20]=0x2000;c[17]=0x27;c[21]=k%7
        c[18]=0x202;c[19]=k&1
        code=[instruction(rng.choice(bytarget[rng.choice(list(specs))])) for _ in range(48)]
        cost=sum(specs[o.table[opcode(op)]][1] for op in code)
        check(code,(0,cost-1,cost,cost+1)[k%4],rng.getrandbits(32),(0x202,0x602)[k&1],c,False,('chain',k),rng.getrandbits(32),0x400 if k&1 else 0)
    assert set(specs)<=entries
    guards=portable.lib.a68k_probe_sequence_guards();assert guards==7
    return dict(cases=cases,executed_steps=steps,mismatches=0,guards=guards,result_sha256=digest.hexdigest(),
        qualified_scratch_targets=[f'{t:08x}' for t in sorted(specs)],qualified_scratch_entries=len(opcodes),qualified_scratch_target_count=len(specs),
        observed_target_transitions=len(transitions),limits=[
            'Original sequences execute continuously through the original dispatcher; no per-instruction scratch injection.',
            'Portable next-entry scratch qualifies register arithmetic/transfers/immediates/quick, shifts/rotates, bit/BCD/MUL and Scc with synthetic observed write callbacks. Native board callbacks remain separate.',
            'Accepted IRQ and other scratch targets are rejected before mutation. No sound-board, scheduler, Save State, frontend or complete CPU claim.',
            'EFLAGS control qualification varies IF/DF in the existing user-mode fixture; privileged/reserved host flags are not a hardware-equivalence claim.'])

def compare_write_observations(exe,portable):
    o=ChainOracle(exe);fn=portable.lib.a68k_probe_observed_write
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)];fn.restype=C.c_int
    digest=hashlib.sha256();cases=0;guards=0
    original=bytes((i*37+11)&255 for i in range(8192))
    for width,entry in ((1,0x4b3130),(2,0x4b3100),(4,0x4b30c0)):
        for direct in (False,True):
            for low in (0,1,2,3,0xffe,0xfff):
                for upper in (0,0xab000000):
                    for host in (0x202,0x602):
                        address=0x123000+low;value=0x89abcdef;base=RAM-0x123000
                        o.callback_eax=0x13579bdf;o.callback_control_xor=0x400;o.writes=[]
                        o.put(WRITE+(address>>12)*16,base if direct else 0,CALL+128,CALL+128,CALL+128)
                        o.u.mem_write(RAM,original)
                        o.run(entry,{UC_X86_REG_ECX:address|upper,UC_X86_REG_EDX:value,UC_X86_REG_EFLAGS:host})
                        memory=(C.c_uint8*8192).from_buffer_copy(original);out=(C.c_uint32*8)()
                        data=(C.c_uint32*8)(width,int(direct),address|upper,value,base,o.callback_eax,host^0x400,host)
                        assert fn(data,memory,out)
                        assert out[0] and out[1]==o.u.reg_read(UC_X86_REG_EAX) and out[3]==1
                        assert out[2]&~0x8d5==o.u.reg_read(UC_X86_REG_EFLAGS)&~0x8d5
                        assert out[4]==len(o.writes) and not out[7]
                        if o.writes:assert list(out[5:7])==o.writes[0]
                        assert bytes(memory)==bytes(o.u.mem_read(RAM,8192))
                        cases+=1;digest.update(struct.pack('<5I',*out[:5])+bytes(memory))
        for mode in (2,3,4,5):
            if mode==4 and width!=4:continue
            memory=(C.c_uint8*8192).from_buffer_copy(original);out=(C.c_uint32*8)()
            data=(C.c_uint32*8)(width,mode,0x123fff,0x89abcdef,RAM-0x123000,0x13579bdf,0x602,0x202)
            assert fn(data,memory,out)
            assert not out[0] and list(out[1:4])==[0xa5c3e791,0x202,1]
            assert out[4]==int(mode==5) and not out[7] and bytes(memory)==original
            guards+=1
    return dict(cases=cases,guards=guards,mismatches=0,result_sha256=digest.hexdigest(),
        limits=['Direct byte/word/long wrappers and synthetic callbacks; native board callback implementation and write-return EDX remain separate.',
                'Missing provenance never invokes the ordinary void callback or writes direct storage; invalid callback output is rejected after that callback.'])

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--optimization',choices=('O0','O2'),default='O2');ap.add_argument('--ubsan',action='store_true')
    args=ap.parse_args()
    sources=[ROOT/'port/a68k/a68k.c',ROOT/'port/a68k/test/sequence_shim.c']
    with tempfile.TemporaryDirectory(prefix='model2-a68k-sequence-') as d:
        lib=Path(d)/'sequence.dylib';command=['clang','-'+args.optimization,'-g','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-dynamiclib',*map(str,sources),'-o',str(lib)]
        if args.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            command+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(command,check=True)
        portable=ChainPortable(lib)
        result=compare_sequences(args.exe,portable)
        result['write_observations']=compare_write_observations(args.exe,portable)
    result.update(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),optimization=args.optimization,ubsan=args.ubsan)
    paths=[Path(__file__),ROOT/'tools/a68k_boundary_compare.py',ROOT/'tools/a68k_inventory.py',ROOT/'tools/original_inventory.py',ROOT/'tools/scsp_dsp_compare.py',ROOT/'port/a68k/a68k.h',*sources,*sorted((ROOT/'port/a68k').glob('*.inc'))]
    result['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources_sha256','limits','qualified_scratch_targets')},indent=2))
if __name__=='__main__':main()
