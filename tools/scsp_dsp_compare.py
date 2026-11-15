#!/usr/bin/env python3
"""Execute original generated SCSP DSP bodies vs the unchanged portable loop.

First group: MEMS/TEMP arithmetic, shifts and writeback, zero initial scratch.
No sample RAM, MIXS/EXTS scaling, chip synthesis, scheduling or ROM input.
"""
import argparse
import collections
import ctypes as C
import hashlib
import json
import random
import struct
import sys
from pathlib import Path
from audio_re_inventory import FIELDS
from original_inventory import OriginalPE

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'port/sharc/test'))
from difftest_bits import load_original, SP, STOP
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP


def instruction(**fields):
    words=[0]*4
    for name,i,shift,mask in FIELDS:
        value=fields.pop(name,0)
        assert 0<=value<=mask
        words[i] |= value<<shift
    assert not fields
    return struct.pack('<4H',*words)


class OriginalDSP:
    ctx=0x72000000
    code=0x73000000
    def __init__(self,exe):
        OriginalPE(exe)
        self.uc=load_original(exe)
        self.uc.mem_map(self.ctx,0x10000); self.uc.mem_map(self.code,0x10000)
        # Reuse the allocator boundary established in audio_re_inventory.py.
        alloc,free=STOP+0x100,STOP+0x120
        self.uc.mem_write(alloc,b'\xb8'+struct.pack('<I',self.code)+b'\xc2\x10\x00')
        self.uc.mem_write(free,b'\xb8\x01\x00\x00\x00\xc2\x0c\x00')
        self.uc.mem_write(0x5081d8,struct.pack('<I',alloc))
        self.uc.mem_write(0x5081e0,struct.pack('<I',free))
        self.writes=[]
        self.uc.hook_add(UC_HOOK_MEM_WRITE,lambda u,t,a,n,v,d:self.writes.append((a,n)),begin=self.code,end=self.code+0xffff)

    def call(self,entry):
        self.uc.mem_write(SP,struct.pack('<I',STOP))
        self.uc.reg_write(UC_X86_REG_ESP,SP)
        self.uc.reg_write(UC_X86_REG_EAX,self.ctx)
        self.uc.reg_write(UC_X86_REG_EDI,self.ctx)
        self.uc.emu_start(entry,STOP,count=1000000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==STOP

    def prepare(self,state):
        self.uc.mem_write(self.ctx,bytes(state)); self.uc.mem_write(self.code,bytes(0x10000))
        self.writes.clear()
        self.call(0x4aa040)
        size=max(a+n for a,n in self.writes)-self.code
        code=bytes(self.uc.mem_read(self.code,size))
        # Programs overwrite the same host code buffer; discard earlier JIT
        # translations before executing the newly generated original code.
        self.uc.ctl_remove_cache(self.code,self.code+0x10000)
        self.generated_code=code
        return hashlib.sha256(code).hexdigest()

    def step(self):
        self.call(0x4a9fa0)
        return bytes(self.uc.mem_read(self.ctx,0x800))

    def run(self,state):
        code_hash=self.prepare(state)
        return self.step(),code_hash


def fixtures():
    rng=random.Random(0x5c5b01)
    def state(program,x,y,b=0,dec=0):
        s=bytearray(0x800)
        struct.pack_into('<I',s,8,8192)
        s[0xcc:0xcc+len(program)]=program
        struct.pack_into('<I',s,0x7b8,len(program)//8)
        struct.pack_into('<h',s,0xc+3*2,y)
        struct.pack_into('<i',s,0x4cc+((5+dec)&127)*4,b)
        struct.pack_into('<i',s,0x6cc+7*4,x)
        struct.pack_into('<I',s,0x74c,dec)
        return s
    xs=[-8388608,-8388607,-4096,-1,0,1,4095,8388606,8388607]
    ys=[-32768,-32760,-8,0,8,32760,32767]
    for shift in range(4):
        for x in xs:
            for y in ys:
                p=instruction(XSEL=1,YSEL=1,IRA=7,COEF=3,ZERO=1)
                p+=instruction(TRA=5,TWT=1,TWA=11,EWT=1,EWA=2,SHIFT=shift)
                yield 'multiply-shift',state(p,x,y),dict(x=x,y=y,shift=shift)
    for i in range(512):
        shift,neg,xsel,zero,bsel=[rng.randrange(n) for n in [4,2,2,2,2]]
        x,b=rng.randrange(-8388608,8388608),rng.randrange(-8388608,8388608)
        y,dec=rng.randrange(-32768,32768),rng.randrange(128)
        p=instruction(TRA=5,XSEL=xsel,YSEL=1,IRA=7,COEF=3,ZERO=zero,NEGB=neg,BSEL=bsel)
        p+=instruction(TRA=5,TWT=1,TWA=11,EWT=1,EWA=2,SHIFT=shift)
        yield 'arithmetic-select',state(p,x,y,b,dec),dict(index=i,x=x,y=y,b=b,dec=dec,shift=shift,xsel=xsel,zero=zero,neg=neg,bsel=bsel)
    for i in range(256):
        # Short dependent chains exercise FRC/Y feedback, old-ACC writeback,
        # TEMP wraparound and multiple additions into the same effect output.
        p=b''
        for step in range(8):
            p+=instruction(TRA=rng.randrange(128),TWT=1,TWA=rng.randrange(128),
                XSEL=rng.randrange(2),YSEL=rng.randrange(4),IRA=rng.randrange(32),
                IWT=rng.randrange(2),IWA=rng.randrange(32),EWT=1,EWA=rng.randrange(4),
                FRCL=rng.randrange(2),SHIFT=rng.randrange(4),YRL=rng.randrange(2),
                NEGB=rng.randrange(2),ZERO=rng.randrange(2),BSEL=rng.randrange(2),COEF=rng.randrange(64))
        s=state(p,0,0,dec=rng.randrange(128))
        for j in range(128):struct.pack_into('<i',s,0x4cc+j*4,rng.randrange(-8388608,8388608))
        for j in range(32):struct.pack_into('<i',s,0x6cc+j*4,rng.randrange(-8388608,8388608))
        for j in range(64):struct.pack_into('<h',s,0xc+j*2,rng.randrange(-32768,32768))
        yield 'feedback-chain',s,dict(index=i)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('library',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    original=OriginalDSP(args.exe)
    lib=C.CDLL(str(args.library.resolve()))
    lib.scsp_dsp_probe.argtypes=[C.c_void_p,C.c_void_p]
    fields=[('TEMP',0x4cc,512),('MEMS',0x6cc,128),('DEC',0x74c,4),('MIXS',0x750,64),('EFREG',0x794,32)]
    counts=collections.Counter();bad=collections.Counter();failures=[];digest=hashlib.sha256()
    inputs=hashlib.sha256(); generated=hashlib.sha256(); changed=0
    for index,(group,state,parameters) in enumerate(fixtures()):
        native,code_hash=original.run(state)
        inputs.update(state); generated.update(bytes.fromhex(code_hash))
        out=(C.c_uint8*0x800)(); inp=(C.c_uint8*0x800).from_buffer_copy(state)
        assert lib.scsp_dsp_probe(inp,out)==1
        portable=bytes(out); diff=[]
        if native[0x4cc:0x74c]!=state[0x4cc:0x74c] or native[0x794:0x7b4]!=state[0x794:0x7b4]: changed+=1
        for name,start,length in fields:
            a,b=native[start:start+length],portable[start:start+length]
            digest.update(a+b)
            if a!=b:
                first=next(n for n in range(length) if a[n]!=b[n]); at=first&~3
                diff.append(dict(field=name,byte_offset=first,original=a[at:at+4].hex(),portable=b[at:at+4].hex()))
        if group=='multiply-shift':
            # Independent scalar expectation for the first observable result;
            # this also prevents two inert fixture paths from appearing equal.
            value=(parameters['x']*(parameters['y']>>3))>>12
            shift=parameters['shift']
            value*=2 if shift in (1,2) else 1
            if shift<2:value=max(-8388608,min(8388607,value))
            else:value=((value+8388608)&0xffffff)-8388608
            assert struct.unpack_from('<i',native,0x4cc+11*4)[0]==value
        counts[group]+=1
        if diff:
            bad[group]+=1
            failures.append(dict(index=index,group=group,parameters=parameters,differences=diff,
                program_hex=state[0xcc:0xcc+struct.unpack_from('<I',state,0x7b8)[0]*8].hex(),generated_sha256=code_hash))
    assert changed>0
    report=dict(cases=sum(counts.values()),groups=dict(counts),mismatches=sum(bad.values()),
        mismatch_groups=dict(bad),failures=failures,result_sha256=digest.hexdigest(),
        input_sha256=inputs.hexdigest(),generated_code_hashes_sha256=generated.hexdigest(),
        cases_changing_temp_mems_or_effects=changed,
        original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
        library_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256((ROOT/'port/snd/scsp.c').read_bytes()).hexdigest(),
        limits=['Zero initial scratch, valid MEMS inputs and no external/sample RAM.',
                'Compares persistent DSP state, not PCM, scheduling or full SCSP behavior.',
                'Original x86 generator and generated code run in Unicorn; host allocator imports are fixtures.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['cases','groups','mismatches','mismatch_groups']},indent=2))
    return bool(failures)


if __name__=='__main__':sys.exit(main())
