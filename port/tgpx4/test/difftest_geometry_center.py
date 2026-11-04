#!/usr/bin/env python3
"""Compare original 004bb30c..004bb326 projection-center selection."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from difftest_lifecycle import load_original
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_EFLAGS


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path)
    ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();uc=load_original(args.exe)
    functions=[]
    for path in args.libraries:
        lib=C.CDLL(str(path.resolve()))
        fn=lib.m2_tgpx4_geometry_center
        fn.argtypes=[C.c_uint32,C.c_uint32];fn.restype=C.c_uint32
        functions.append(fn)
    rng=random.Random(0x4bb30c)
    commands=[(low<<6)|(high<<29)|0x8800000 for low in range(4) for high in range(4)]
    commands += [0,0xffffffff,*[rng.getrandbits(32) for _ in range(1024)]]
    cases=0
    for mode in (0,1,2,3,4,0xffffffff):
        for command in commands:
            uc.mem_write(0x10ed978,struct.pack('<I',mode))
            uc.reg_write(UC_X86_REG_ECX,command);uc.reg_write(UC_X86_REG_EFLAGS,2)
            uc.emu_start(0x4bb30c,0x4bb326,count=20)
            assert uc.reg_read(UC_X86_REG_EIP)==0x4bb326
            result=int.from_bytes(uc.mem_read(0xdcec40,4),'little')
            for fn in functions:assert fn(command,mode)==result,(hex(command),mode)
            cases+=1
    report=dict(original_executions=cases,portable_comparisons=cases*len(functions),
        scope='Original object projection-center fragment; memory result, not scratch flags')
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
