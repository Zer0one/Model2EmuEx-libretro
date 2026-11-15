#!/usr/bin/env python3
"""Compare native serial selectors, ADC sequencing and I/O widths with ElSemi.

No game ROMs. Calls complete original read wrappers and original byte/word
writes, selecting the original driver table for each board. Synthetic arrays
supply controlled counter, panel and analog values. Unknown adjacent-process
memory beyond the 16 portable analog slots is outside the comparison.
"""
import argparse
import ctypes
import itertools
import json
import random
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'port/sharc/test'))
from difftest_bits import load_original,SP,STOP
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESP,UC_X86_REG_EIP


def compare(exe,library):
    u=load_original(exe)
    context=0x72000000
    u.mem_map(context,0x204000)
    def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    put(0x5aa730,context)
    fn=ctypes.CDLL(str(library.resolve())).protocol_case
    fn.argtypes=[ctypes.c_uint]*5+[ctypes.POINTER(ctypes.c_uint32)]
    fn.restype=None
    rng=random.Random(1)
    failures=[];counts={'reads':0,'writes':0}
    bases=[0x574b88,0x574b88,0x574c78,0x574c00]
    def case(board,write,width,address,value,state):
        put(context+0x3c,board);put(0x5aa8c0,bases[board])
        put(0x574cf8,*state[2:6]);put(0x5aa734,state[6])
        u.mem_write(0x5aa70c,bytes(state[7:23]))
        u.mem_write(0x5aa874,bytes(state[23:31]))
        u.mem_write(0x10ed8fe,bytes((state[1],state[0])))
        put(0x10ed900,0)
        entry=({1:0x4cb5e0,2:0x4c86c0}[width] if write else {1:0x4cb700,2:0x4cb720,4:0x4cb740}[width])
        u.mem_write(SP,struct.pack('<I',STOP))
        u.reg_write(UC_X86_REG_ESP,SP);u.reg_write(UC_X86_REG_ECX,address);u.reg_write(UC_X86_REG_EDX,value)
        u.emu_start(entry,STOP,count=1000)
        assert u.reg_read(UC_X86_REG_EIP)==STOP
        expected=[u.mem_read(0x10ed8ff,1)[0],u.mem_read(0x10ed8fe,1)[0],
                  0 if write else u.reg_read(UC_X86_REG_EAX)&(0xffffffff if width==4 else 255)]
        data=(ctypes.c_uint32*32)(*state)
        fn(board,write,width,address,value,data)
        actual=[data[0],data[1],data[31]]
        counts['writes' if write else 'reads']+=1
        if actual!=expected:
            failures.append(dict(board=board,write=write,width=width,address=hex(address),
                                 value=value,actual=actual,expected=expected))
    for board,width,mux,vector in itertools.product(range(4),(1,2,4),(*range(11),255),range(8)):
        state=[mux,vector,*(rng.getrandbits(32) for _ in range(4)),vector&3,
               *(rng.randrange(256) for _ in range(16)),
               *(rng.randrange(256) for _ in range(8)),0]
        for address in (2,4,6,8,0x10,0x12,0x14,0x16,0x18,0x1c,0x1e,0x24,0x40,0x42):
            case(board,0,width,address,0,state)
    for board,width,index in itertools.product(range(4),(1,2,4),range(8,16)):
        state=[0,index,*([0]*4),0,*range(16),*([255]*8),0]
        case(board,0,width,0x1e,0,state)
    for board,width,address,value in itertools.product(range(4),(1,2),(0x12,0x14,0x1e),range(256)):
        state=[255,7,*([0]*4),0,*range(16),*([255]*8),0]
        case(board,1,width,address,value,state)
    # Outside the portable analog array, the original exposes process data.
    # Seed a known virtual pointer to demonstrate the existing containment.
    put(0x5aa71c,0x72004000)
    adjacent=[]
    for index in range(16,20):
        state=[0,index,*([0]*4),0,*range(16),*([255]*8),0]
        put(context+0x3c,1);put(0x5aa8c0,bases[1])
        u.mem_write(0x10ed8fe,bytes([index]))
        u.mem_write(SP,struct.pack('<I',STOP))
        u.reg_write(UC_X86_REG_ESP,SP);u.reg_write(UC_X86_REG_ECX,0x1e)
        u.emu_start(0x4cb700,STOP,count=1000)
        assert u.reg_read(UC_X86_REG_EIP)==STOP
        native_byte=u.reg_read(UC_X86_REG_EAX)&255
        data=(ctypes.c_uint32*32)(*state)
        fn(1,0,1,0x1e,0,data)
        adjacent.append(dict(index=index,original=native_byte,portable=data[31]))
    return dict(status='pass' if not failures else 'mismatch',**counts,
                adjacent_process_pointer_observation=adjacent,
                mismatches=len(failures),examples=failures[:8],
                read_entries=['004cb700','004cb720','004cb740'],
                write_entries=['004cb5e0','004c86c0'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe',type=Path);p.add_argument('library',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=compare(a.exe,a.library)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(result['status']!='pass')

if __name__=='__main__':main()
