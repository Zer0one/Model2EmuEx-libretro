#!/usr/bin/env python3
"""Replay actual native Model 1 sound CPU port writes and FM ticks into the portable board."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from collections import Counter
from itertools import chain
from pathlib import Path

from model1_board_compare import BOARD, OUTPUT, initialize
from scsp_a68k_board_compare import sound_regions
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI

ROOT=Path(__file__).resolve().parents[1]

def regions(archive):
    # The native sample space is contiguous across the two MAME chip regions.
    names={5:'M1AUDIO_CPU_REGION',6:'M1AUDIO_MPCM1_REGION'}
    alias={'M1AUDIO_MPCM2_REGION':'M1AUDIO_MPCM1_REGION'}
    return sound_regions(archive,names,alias)

def compare(exe,archive,frames,commands):
    data=regions(archive)
    samples=data['M1AUDIO_MPCM1_REGION']
    o=initialize(exe,samples,data['M1AUDIO_CPU_REGION'])
    with tempfile.TemporaryDirectory() as td:
        image=Path(td)/'board.so'
        subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-shared',
            *(str(ROOT/'port/snd'/f) for f in ('model1_original.c','fm_original.c','multipcm_original.c')),
            '-o',str(image)],check=True)
        lib=C.CDLL(str(image))
        ptr=C.c_void_p
        create=lib.m2_original_m1_create
        create.restype=ptr
        create.argtypes=[ptr,C.c_size_t]
        rom=(C.c_uint8*len(samples)).from_buffer(samples)
        b=create(rom,len(rom))
        assert b
        lib.m2_original_m1_begin.argtypes=[ptr,C.c_uint]
        lib.m2_original_m1_write.argtypes=[ptr,C.c_uint32,C.c_uint,C.c_uint32]
        lib.m2_original_m1_tick.argtypes=[ptr]
        lib.m2_original_m1_finish.argtypes=[ptr,ptr,C.c_uint,C.c_uint,C.c_uint]
        lib.m2_original_m1_error.argtypes=[ptr]
        lib.m2_original_m1_error.restype=C.c_char_p
        lib.m2_original_m1_free.argtypes=[ptr]
        events=Counter()
        # Long writes call narrow helpers internally. Observe atomic byte effects
        # inside the chip instead, so each write is applied exactly once.
        def chip_write(u,pc,size,user):
            dev=u.reg_read(UC_X86_REG_EAX)
            port=u.reg_read(UC_X86_REG_ECX)
            value=u.reg_read(UC_X86_REG_EDX)
            lib.m2_original_m1_write(b,0xc40000+dev*0x20000+2*port+1,1,value&255)
            events['MultiPCM writes']+=1
        def fm(u,pc,size,user):
            from unicorn.x86_const import UC_X86_REG_EBX
            port=u.reg_read(UC_X86_REG_EAX)&3
            lib.m2_original_m1_write(b,0xd00000+2*port,1,u.reg_read(UC_X86_REG_EBX)&255)
            events['FM writes']+=1
        def tick(u,pc,size,user):
            lib.m2_original_m1_tick(b)
            events['FM ticks']+=1
        for pc,fn in ((0x4b08f0,chip_write),(0x4b2580,fm),(0x4a9e00,tick)):
            o.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
        # Bank register writes need no CPU-register assumption across widths.
        from unicorn import UC_HOOK_MEM_WRITE
        def bank_store(u,access,address,size,value,user):
            lib.m2_original_m1_write(b,0xc50001+user*0x20000,1,value&7)
            events['bank writes']+=1
        for i in range(2):
            at=0x108a468+0x3450*i
            o.u.hook_add(UC_HOOK_MEM_WRITE,bank_store,i,begin=at,end=at)
        o.u.ctl_flush_tb()
        digest=hashlib.sha256(); nonzero=0; first=None
        for frame in range(frames):
            n=760
            assert lib.m2_original_m1_begin(b,n)
            for v in commands.get(frame,[]):
                o.run(0x4c8660,{UC_X86_REG_ECX:v})
            for line in range(210):
                o.run(0x4cc710,{UC_X86_REG_EAX:BOARD},count=100000)
            o.run(0x4a9d70,count=10000000)
            for i in range(2): o.run(0x4affb0,{UC_X86_REG_EAX:i},count=10000000)
            out=(C.c_int16*(n*2))()
            lib.m2_original_m1_finish(b,out,100,100,100)
            assert lib.m2_original_m1_error(b) is None
            planes=[struct.unpack('<'+'h'*n,o.u.mem_read(OUTPUT+at,2*n)) for at in (0x68,0x2b178)]
            expected=list(chain.from_iterable(zip(*planes)))
            assert expected==list(out),(frame,next((i,x,y) for i,(x,y) in enumerate(zip(expected,out)) if x!=y),events)
            for i in range(n):
                if expected[2*i] or expected[2*i+1]:
                    nonzero+=1
                    if first is None: first=[frame,i]
            digest.update(bytes(out))
        lib.m2_original_m1_free(b)
        return dict(title=archive.stem,frames=frames,stereo_frames=frames*760,
                    first_nonzero=first,nonzero_stereo_frames=nonzero,events=dict(events),
                    commands=commands,sha256=digest.hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe',type=Path); p.add_argument('archive',type=Path)
    p.add_argument('--frames',type=int,default=120)
    p.add_argument('--command',action='append',default=[],help='frame:hex-byte,hex-byte')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    commands={}
    for event in a.command:
        frame,values=event.split(':')
        commands.setdefault(int(frame),[]).extend(int(v,16) for v in values.split(','))
    result=compare(a.exe,a.archive,a.frames,commands)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result)

if __name__=='__main__':
    main()
