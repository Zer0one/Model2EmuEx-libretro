#!/usr/bin/env python3
"""Execution-loop flag producers vs original x86, plus bounded loop traces.

Fragments and traces do NOT count as recovered complete execution routines.
The traces invoke the original NOT through an original unconditional dispatcher;
stop before its bus callbacks, then resume in the outer loop for the next entry.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)
from difftest_bits import load_original, EXE_SHA256, STOP, SP
from difftest_condition import FLAG_MASK

ARENA=0x72000000
STATE=0x10edc30
BUDGET=0x5aeb0c
RECORD=0x5aeb10
MASK=FLAG_MASK|2


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    mu=load_original(args.exe);mu.mem_map(ARENA,0x1000)
    libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_flow_flags
        fn.argtypes=[C.c_uint,C.c_uint32,C.POINTER(C.c_uint32)];fn.restype=C.c_bool
        libs.append((p,fn))
    def word(a,v):mu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def native(origin,value):
        out=[]
        for p,fn in libs:
            flags=C.c_uint32()
            if not fn(origin,value,C.byref(flags)):raise AssertionError('Rejected supported producer')
            out.append(flags.value)
        return out
    rng=random.Random(8)
    values=[0,1,2,3,0x7fffff93,0x7fffff94,0x7fffffff,0x80000000,0xffffff93,0xffffff94,0xffffffff]
    values += [1<<i for i in range(32)]+[rng.getrandbits(32) for _ in range(1024)]
    cases=0
    # Execute the actual flag-producing instruction only, avoiding unrelated
    # memory/branch effects. Multi-instruction loop traces below connect callers.
    producers=((0,0x4bd058),(1,0x4be076),(2,0x4bd13a),(2,0x4be165),(3,0x4bdfa5),(3,0x4bdfce))
    for origin,entry in producers:
        for value in values:
            word(BUDGET,value)
            mu.reg_write(UC_X86_REG_EAX,value)
            mu.reg_write(UC_X86_REG_EBX,0)
            mu.reg_write(UC_X86_REG_EBP,1)
            mu.reg_write(UC_X86_REG_ESI,1)
            mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
            mu.emu_start(entry,STOP,count=1)
            original=mu.reg_read(UC_X86_REG_EFLAGS)&MASK
            if any(x!=original for x in native(origin,value)):
                raise AssertionError(f'{entry:x}/{value:x}: original={original:x}, port={native(origin,value)}')
            cases+=1
    print(f'Flag producers: {cases} passed',flush=True)

    traces=[]
    active={}
    def hook(uc,address,size,user):
        if address==0x4bdf20:
            active['flags'].append(uc.reg_read(UC_X86_REG_EFLAGS)&MASK)
        if address==0x4bdf35:
            # NOT has returned. Record its ASTAT, then simulate only a neutral
            # handler return; no memory transfer/loop completion is claimed.
            active['astat'].append(struct.unpack('<I',uc.mem_read(STATE+0x240,4))[0])
            esp=uc.reg_read(UC_X86_REG_ESP)
            esi,ret=struct.unpack('<II',uc.mem_read(esp,8))
            uc.reg_write(UC_X86_REG_ESI,esi)
            uc.reg_write(UC_X86_REG_ESP,esp+8)
            uc.reg_write(UC_X86_REG_EIP,ret)
            if len(active['flags'])==active['limit']:uc.emu_stop()
    handle=mu.hook_add(UC_HOOK_CODE,hook)
    for entry in (0x4bd000,0x4be000):
        for budget in ((1,2,3,128,129,0x80000000,0xffffffff) if entry==0x4bd000 else (100000,)):
            mu.mem_write(STATE,bytes(0x2c0))
            word(STATE+8,5);word(STATE+0x14,0x123456) # No loop end in this bounded trace.
            word(0x10eded8,ARENA);word(0x10ededc,ARENA)
            word(0x10ed950,0);word(0x10ed944,0);word(0x5aeb44,10)
            word(BUDGET,budget)
            for i in range(2):
                rec=ARENA+i*0x6c
                word(rec,0x4bdf20);word(rec+4,0x4615e0)
                word(rec+0x34,ARENA+0x800);word(rec+0x38,ARENA+0x804)
            word(ARENA+0x800,0);word(ARENA+0x804,0)
            word(SP,STOP);mu.reg_write(UC_X86_REG_ESP,SP)
            mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
            active={'flags':[],'astat':[],'limit':1 if budget==1 else 2}
            mu.emu_start(entry,STOP,count=1000)
            expected=[native(0 if entry==0x4bd000 else 1,budget)[0]]
            if budget!=1:expected.append(native(2,budget)[0])
            if active['flags']!=expected:raise AssertionError(f'Loop {entry:x}: {active}, expected={expected}')
            astat=[(1 if f&0x40 else 0)|(4 if f&0x80 else 0) for f in expected]
            if active['astat']!=astat:raise AssertionError(f'NOT status mismatch: {active}')
            traces.append({'entry':f'0x{entry:08x}','budget':budget,**active})
    mu.hook_del(handle)
    for p,fn in libs:
        out=C.c_uint32(0x12345678)
        if fn(4,0,C.byref(out)) or out.value!=0x12345678:raise AssertionError('Invalid producer mutated output')
    root=Path(__file__).resolve().parents[1]
    receipt={'status':'passed','scope':'6 flag-producing sites and 8 bounded loop traces; not complete loop recovery',
        'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':8,'fragment_cases':cases,
        'traces':traces,'mismatches':0,'skipped':0,
        'sources':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('sharc_flow.c','sharc_flow.h')},
        'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn in libs]}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(traces,indent=2))


if __name__=='__main__':main()
