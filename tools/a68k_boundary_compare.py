#!/usr/bin/env python3
"""Original A68K reset/bus/exception/IRQ/MOVEQ contracts, ROM-free.

Executes unchanged pinned x86 with synthetic callbacks and compares independently
expressed state transitions. This is a research model, not an executable CPU
replacement. All memory is Unicorn-owned; no Windows process or ROM is needed.
"""
import argparse
import collections
import hashlib
import json
import random
import struct
from pathlib import Path
from original_inventory import OriginalPE
from scsp_dsp_compare import load_original, SP, STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

CTX=0x528ce4
RAM=0x72000000
READ=0x10682d0
WRITE=0x10582d0
DATA=0x10482d0
CALL=STOP+0x100


class Oracle:
    def __init__(self,exe):
        self.pe=OriginalPE(exe);self.u=load_original(exe)
        self.u.mem_map(RAM,0x20000)
        self.events=[];self.reads={};self.ack=-1;self.stops=set();self.stop=None
        self.code_hook = self.u.hook_add(UC_HOOK_CODE,self.hook)
        self.cost=list(self.pe.read(0x528ff0,256))

    def put(self,at,*v):self.u.mem_write(at,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def get(self,at,n=1):return list(struct.unpack('<'+'I'*n,self.u.mem_read(at,4*n)))
    def ret(self,value=0):
        sp=self.u.reg_read(UC_X86_REG_ESP)
        self.u.reg_write(UC_X86_REG_EAX,value&0xffffffff)
        self.u.reg_write(UC_X86_REG_ESP,sp+4)
        self.u.reg_write(UC_X86_REG_EIP,self.get(sp)[0])

    def hook(self,u,at,size,data):
        if at in self.stops:self.stop=at;u.emu_stop();return
        if CALL<=at<CALL+0x80:
            kind=(at-CALL)//16;address=u.reg_read(UC_X86_REG_ECX);value=u.reg_read(UC_X86_REG_EDX)
            if kind==0:
                self.events.append(['read32',address]);self.ret(self.reads.get(address,0))
            elif kind in (1,2):
                self.events.append(['write16' if kind==1 else 'write32',address,value& (0xffff if kind==1 else 0xffffffff)]);self.ret()
            elif kind==3:
                self.events.append(['bind',address]);self.put(0x10ed9ac,0x73000000);self.ret()
            elif kind==4:
                self.events.append(['ack',address]);self.ret(self.ack)
            else:
                self.events.append(['bus',kind,address,value]);self.ret(0xa1b2c3d4)

    def run(self,start,regs=None,stops=(),count=10000):
        self.events=[];self.stop=None;self.stops=set(stops)
        self.u.reg_write(UC_X86_REG_ESP,SP);self.put(SP,STOP)
        self.u.reg_write(UC_X86_REG_EFLAGS,0x202)
        for k,v in (regs or {}).items():self.u.reg_write(k,v&0xffffffff)
        self.u.emu_start(start,STOP,count=count)
        assert self.u.reg_read(UC_X86_REG_EIP)==STOP or self.stop is not None

    def setup_exception(self,c,cycles):
        self.put(CTX,*c);self.put(0x10ed9b0,cycles);self.put(0x10ed9ac,0x73000000)
        self.put(0x572a80,0xffffff);self.put(0x572a90,CALL)
        self.put(0x572a98,CALL+16,CALL+32,CALL+48)
        self.put(0x528d40,CALL+64)
        # Include the installed callback token in the comparison baseline.
        c[23]=CALL+64


def exception_model(c,pc,flags,vector,target,cost):
    c=c.copy();events=[]
    # Native packed flags: C bit 0, Z bit 6, N bit 7, V bit 11; X has its
    # own byte at context+0x4c. Do not substitute an ordinary 68000 SR word.
    sr=((c[17]&255)<<8)|(flags&1)|((flags>>4)&12)|((flags>>10)&2)|((c[19]&1)<<4)
    stack=c[15]
    if not c[17]&0x20:
        c[17]|=0x20;c[28]=stack;stack=c[16]
    stack=(stack-6)&0xffffffff;c[15]=stack;c[20]=pc
    events += [['write16',stack,sr],['write32',(stack+2)&0xffffffff,pc],
               ['read32',(c[29]+(vector&255)*4)&0xffffffff]]
    c[32]=target;target &= 0xffffff;c[18]=flags
    events.append(['bind',target])
    return c,target,events,cost


def compare(exe,portable=None):
    o=Oracle(exe);rng=random.Random(68000);counts=collections.Counter();digest=hashlib.sha256()
    def keep(group,value):
        counts[group]+=1;digest.update(json.dumps(value,sort_keys=True).encode())
    def context():return [rng.getrandbits(32) for _ in range(33)]

    # Reset preserves dirty registers/flags/pending IRQ and even SSP storage.
    for direct in (False,True):
        for pc in (0,0x1234,0x12fffe,0x12ffff,0xfff000):
            for sp in (0,0x7ff00,0xffffffff):
                c=context();o.put(CTX,*c);o.put(READ,RAM if direct else 0,0,0,CALL)
                o.put(READ+(pc>>12)*16,0x73800000)
                # PC=0 shares the vector page; preserve its fixture mapping.
                if pc>>12==0:o.put(READ,RAM if direct else 0,0,0,CALL)
                o.u.mem_write(RAM,struct.pack('<4H',sp>>16,sp&65535,pc>>16,pc&65535))
                o.reads={0:sp,4:pc};o.run(0x4b33a0)
                expected=c.copy();expected[15]=sp;expected[20]=pc;expected[17]=0x27;expected[30]=pc>>16
                assert o.get(CTX,33)==expected
                assert o.events==([] if direct else [['read32',0],['read32',4]])
                assert o.get(0x10ed9ac)==o.get(READ+(pc>>12)*16)
                if portable:
                    p=portable.cpu(0,c,arg=sp,target=pc,direct=direct)
                    assert p['context']==o.get(CTX,33) and p['events']==o.events and p['boundary']==0
                    assert p['fetch']==o.get(0x10ed9ac)[0]
                keep('reset',expected)

    # Direct vs callback bus paths, 24-bit aliasing, odd/byte offsets and a
    # longword crossing a page. The original selects only the starting page.
    entries=[(0x4b3160,READ,4,False),(0x4b3190,READ,2,False),(0x4b31c0,READ,1,False),
             (0x4b31f0,DATA,4,False),(0x4b3220,DATA,2,False),(0x4b3250,DATA,1,False),
             (0x4b30c0,WRITE,4,True),(0x4b3100,WRITE,2,True),(0x4b3130,WRITE,1,True)]
    for entry,table,width,write in entries:
        for direct in (False,True):
            for low in (0,1,2,3,7,0xffe,0xfff):
                for upper in (0,0xab000000):
                    address=0x123000+low;aliased=address|upper;value=0x89abcdef
                    initial=bytearray((i*37+11)&255 for i in range(8192));o.u.mem_write(RAM,bytes(initial))
                    o.put(table+(address>>12)*16,(RAM-0x123000) if direct else 0,CALL+80,CALL+96,CALL+112)
                    o.run(entry,{UC_X86_REG_ECX:aliased,UC_X86_REG_EDX:value})
                    if direct:
                        at=low^1 if width==1 else low
                        if write:
                            payload=bytes([value&255]) if width==1 else struct.pack('<H',value&65535) if width==2 else struct.pack('<HH',value>>16,value&65535)
                            initial[at:at+width]=payload;assert bytes(o.u.mem_read(RAM,8192))==initial
                        else:
                            v=initial[at] if width==1 else struct.unpack_from('<H',initial,at)[0] if width==2 else (struct.unpack_from('<H',initial,at)[0]<<16)|struct.unpack_from('<H',initial,at+2)[0]
                            if width<4:v|=(table+(address>>12)*16)&~((1<<(width*8))-1)
                            assert o.u.reg_read(UC_X86_REG_EAX)==v
                        assert not o.events
                    else:
                        slot={1:5,2:6,4:7}[width]
                        assert len(o.events)==1 and o.events[0][:3]==['bus',slot,address]
                        if write:assert o.events[0][3]==value
                        else:assert o.u.reg_read(UC_X86_REG_EAX)==0xa1b2c3d4
                    if portable:
                        # Recreate the PRE-write input rather than passing the
                        # Python model's already-modified bytearray to C.
                        ram=bytes((i*37+11)&255 for i in range(8192))
                        p=portable.memory(write,width,direct,aliased,value,ram,space=int(table==DATA))
                        if direct:
                            assert p['ram']==bytes(o.u.mem_read(RAM,8192))
                            if not write:assert p['value']==o.u.reg_read(UC_X86_REG_EAX)
                            assert not p['events']
                        else:
                            expected_events=[event.copy() for event in o.events]
                            if not write:expected_events[0][3]=0 # EDX is not a read argument.
                            assert p['events']==expected_events
                            if not write:assert p['value']==o.u.reg_read(UC_X86_REG_EAX)
                    keep('memory_bus',[entry,direct,aliased,o.events,
                        None if write else o.u.reg_read(UC_X86_REG_EAX),hashlib.sha256(bytes(o.u.mem_read(RAM,8192))).hexdigest()])

    for vector in range(48):
        for sr_high in (0x00,0x20,0x87,0xa7):
            for ccr in range(32):
                c=context();c[17]=(c[17]&0xffffff00)|sr_high;c[19]=(c[19]&0xffffff00)|((ccr>>4)&1)
                c[15]=0x8000;c[16]=0x9000;c[29]=0x100
                flags=0x202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10);pc=0x123456;target=0xab007000
                o.setup_exception(c,1000);o.reads={0x100+4*vector:target}
                expected,next_pc,events,cost=exception_model(c,pc,flags,vector,target,o.cost[vector])
                o.run(0x462be0,{UC_X86_REG_EAX:vector,UC_X86_REG_EDX:flags,UC_X86_REG_ESI:pc})
                assert o.get(CTX,33)==expected and o.events==events
                assert o.u.reg_read(UC_X86_REG_ESI)==next_pc and o.u.reg_read(UC_X86_REG_EDX)==flags
                assert o.get(0x10ed9b0)[0]==1000-cost
                if portable:
                    p=portable.cpu(1,c,pc,flags,1000,vector,target,costs=o.cost)
                    assert p['context']==o.get(CTX,33) and p['events']==o.events and p['boundary']==0
                    assert p['pc']==next_pc and p['flags']==flags and p['cycles']==1000-cost
                keep('exception',[vector,sr_high,ccr,expected,events,cost])

    for level in range(8):
        for mask in range(8):
            for ack in (-1,-2,5,31):
                for supervisor in (0,0x20):
                    for budget in (-1,0,1000):
                        c=context();c[15]=0x8000;c[16]=0x9000;c[17]=supervisor|mask;c[18]=0x2c3;c[19]=1;c[20]=0x123456;c[21]=0xabcdef80|level;c[29]=0x100
                        o.setup_exception(c,budget);o.ack=ack;vector=24+level if ack<0 else ack;target=0x7000
                        o.reads={0x100+4*vector:target};expected=c.copy();pc=c[20];cycles=budget;events=[]
                        accepted=level!=0 and (level==7 or level>mask)
                        if accepted:
                            expected[21]=(expected[21]&0xffffff00)|((expected[21]&255)&0x78)
                            expected,pc,events,cost=exception_model(expected,pc,c[18],vector,target,o.cost[vector]);cycles-=cost
                            events.insert(0,['ack',level]);expected[17]=(expected[17]&~7)|level
                        if cycles<0:
                            expected[20]=pc;expected[18]=c[18];expected[16 if expected[17]&0x20 else 28]=expected[15]
                        o.run(0x462b1c,stops=(0x462b48,))
                        assert o.events==events and o.get(CTX,33)==expected
                        assert o.get(0x10ed9b0)[0]==cycles&0xffffffff
                        assert (o.stop==0x462b48)==(cycles>=0)
                        if portable:
                            p=portable.cpu(2,c,cycles=budget,target=target,ack=ack,costs=o.cost)
                            assert p['context']==o.get(CTX,33) and p['events']==o.events
                            assert p['cycles']==o.get(0x10ed9b0)[0]
                            assert p['boundary']==(1 if o.stop==0x462b48 else 2)
                        keep('interrupt',[level,mask,ack,supervisor,budget,expected,events])

    # Entire native MOVEQ dispatch family, including bit-8 aliases. Observe
    # flags consumed by the guest (NZVC) and the separate, untouched X storage.
    for opcode in range(0x7000,0x8000):
        for extend in (0,1):
            c=context();c[19]=extend;o.put(CTX,*c);o.put(0x10ed9b0,100)
            pc=0x123456;o.run(0x478438,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc},stops=(0x47845c,))
            value=opcode&255;value=value if value<128 else value-256
            expected=c.copy();expected[(opcode>>9)&7]=value&0xffffffff
            assert o.get(CTX,33)==expected and o.u.reg_read(UC_X86_REG_ESI)==pc+2 and o.get(0x10ed9b0)==[96]
            flags=(0x40 if value==0 else 0)|(0x80 if value<0 else 0)
            assert o.u.reg_read(UC_X86_REG_EDX)&0x8c1==flags
            if portable:
                p=portable.cpu(3,c,pc,cycles=100,arg=opcode)
                assert p['context']==o.get(CTX,33) and p['pc']==pc+2 and p['cycles']==96 and p['boundary']==1
                assert p['flags']&0x8c5==o.u.reg_read(UC_X86_REG_EDX)&0x8c5
            keep('moveq',[opcode,extend,value,flags])
    # Recovered C also has the signed-budget exit tail. Direct entry into
    # MOVEQ skips PUSHAD; supply its 32-byte saved-register frame explicitly.
    # Include unsigned wraparound, rather than using host signed overflow.
    for opcode in (0x7000,0x707f,0x7080,0x70ff,0x7f00,0x7fff):
        for pc in (0,0xfffffffe):
            for budget in (0,3,4,0x80000000,0x80000003):
                for supervisor in (0,0x20):
                    for host_flags in (0x2,0x202):
                        c=context();c[17]=supervisor;c[19]=1;o.put(CTX,*c);o.put(0x10ed9b0,budget)
                        o.put(SP+4,*([0]*7),STOP)
                        o.run(0x478438,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EFLAGS:host_flags},stops=(0x47845c,))
                        cycles=(budget-4)&0xffffffff;next_pc=(pc+2)&0xffffffff
                        value=opcode&255;value=value if value<128 else value-256
                        flags=host_flags|(0x40 if value==0 else 0)|(0x80 if value<0 else 0)|(4 if (value&255).bit_count()%2==0 else 0)
                        expected=c.copy();expected[(opcode>>9)&7]=value&0xffffffff
                        exited=bool(cycles&0x80000000)
                        if exited:expected[20]=next_pc;expected[18]=flags;expected[16 if supervisor else 28]=c[15]
                        assert o.get(CTX,33)==expected and o.get(0x10ed9b0)==[cycles]
                        assert (o.stop is None)==exited
                        if portable:
                            p=portable.cpu(3,c,pc,cycles=budget,arg=opcode,host_flags=host_flags)
                            assert p['context']==o.get(CTX,33) and p['cycles']==cycles and p['pc']==next_pc
                            assert p['boundary']==(2 if exited else 1)
                        keep('moveq_budget_exit',[opcode,pc,budget,supervisor,host_flags,expected,cycles])

    # Observe the precise odd-vector branch BEFORE its unfinished recursive
    # tail. Do not replace the native address error with a normal return.
    for vector in (2,3,4,31):
        for supervisor in (0,0x20):
            for target in (1,0xab007001,0xffffffff):
                c=context();c[15]=0x8000;c[16]=0x9000;c[17]=supervisor;c[19]=1;c[29]=0x100
                pc=0x123456;flags=0x2c3;o.setup_exception(c,1000);o.reads={0x100+4*vector:target}
                o.run(0x462be0,{UC_X86_REG_EAX:vector,UC_X86_REG_EDX:flags,UC_X86_REG_ESI:pc},stops=(0x462c89,))
                assert o.stop==0x462c89 and o.u.reg_read(UC_X86_REG_ESI)==target
                assert o.events[-1]==['read32',0x100+4*vector]
                if portable:
                    p=portable.cpu(1,c,pc,flags,1000,vector,target,costs=o.cost)
                    assert p['boundary']==3 and p['context']==o.get(CTX,33) and p['events']==o.events
                    assert p['pc']==target and p['flags']==flags and p['cycles']==o.get(0x10ed9b0)[0]
                keep('odd_vector_prefix',[vector,supervisor,target,o.get(CTX,33),o.events])
    return dict(original_sha256=hashlib.sha256(o.pe.data).hexdigest(),cases=sum(counts.values()),
        groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
        limits=['Independent Python transition models and synthetic native callbacks; no portable CPU replacement.',
                'Exception vectors 0..47 with even targets; odd-target prefix checked separately, recursive tail remains outside this group.',
                'Memory callback ABI is tested; external device implementations are not.',
                'MOVEQ verifies guest NZVC/X, not all incidental host EFLAGS bits.',
                'No sound ROM execution, full A68K/Musashi comparison or audible-equivalence claim.'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();result=compare(args.exe);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
