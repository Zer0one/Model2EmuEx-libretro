#!/usr/bin/env python3
"""Compare the caller's stack at A68K bus writes with Model 2 Emulator 1.1a."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from collections import Counter

from a68k_boundary_compare import CALL, CTX, RAM, SP, Oracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ECX,
                               UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_ESP)
from unicorn import UC_HOOK_CODE

ROOT=Path(__file__).resolve().parents[1]


def compare(exe):
    o=Oracle(exe)
    table=decode_dispatch(o.pe)[3]
    representatives={}
    for opcode, target in enumerate(table):
        representatives.setdefault(target,opcode)
    # The original emitters dispatch in address order. Look for the indirect
    # byte/word/long store operands in each handler up to the next entry.
    entries=sorted(representatives)
    cases=[]
    slots=[b'\xff\x15'+struct.pack('<I',slot) for slot in (0x572a94,0x572a98,0x572a9c)]
    for index,target in enumerate(entries):
        end=entries[index+1] if index+1<len(entries) else 0x48b730
        body=o.pe.read(target,end-target)
        if any(token in body for token in slots):
            cases.append((representatives[target],target,False))
    # The interrupt path saves the accepted level across exception entry.
    # Compare it independently from a guest TRAP, with the same guest stack.
    assert len(cases) == 976, "unexpected direct-store inventory for the pinned dispatch table"
    cases += [(0x4e40,table[0x4e40],False),(0,0,True)]
    o.put(0x572a88,*([CALL+0xd0]*3),*([CALL+0xe0]*3))
    o.put(0x572aa0,CALL+0xf0)
    o.put(0x572aa4,*([CALL+0xd0]*3))
    o.put(0x572a80,0xffffff)
    depths=[]
    dispatch_sp=SP
    def bus(u,pc,size,user):
        if pc==CALL+0xe0:
            depths.append(dispatch_sp-u.reg_read(UC_X86_REG_ESP))
        if pc==CALL+0xd0:
            u.reg_write(UC_X86_REG_EDX,0)
        if pc==CALL+0xf0:
            o.put(0x10ed9ac,RAM)
        o.ret(0xffffffff if pc==CALL+0xc0 else 0)
    for offset in (0xc0,0xd0,0xe0,0xf0):
        o.u.hook_add(UC_HOOK_CODE,bus,begin=CALL+offset,end=CALL+offset)
    o.u.ctl_flush_tb()
    result=Counter()
    digest=hashlib.sha256()
    with tempfile.TemporaryDirectory() as temp:
        library=Path(temp)/'frames.so'
        subprocess.run(['cc','-std=c11','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',
                        str(ROOT/'port/a68k/test/write_frame_shim.c'),str(ROOT/'port/a68k/a68k.c'),
                        '-o',str(library)],check=True)
        probe=C.CDLL(str(library)).probe_write_frames
        probe.argtypes=[C.POINTER(C.c_uint16),C.POINTER(C.c_uint32),C.c_uint32,
                        C.c_uint32,C.c_int,C.POINTER(C.c_uint32)]
        observed=(C.c_uint32*32)()
        for opcode,target,irq in cases:
            code=[opcode,2,2,2,2,2,2,2]
            regs=[0]*33
            regs[8:16]=[0x80]*8
            regs[17]=0x20
            regs[21]=2 if irq else 0
            regs[23]=CALL+0xc0
            regs[31]=1
            o.put(CTX,*regs)
            o.put(0x10ed9ac,RAM)
            o.put(0x10ed9b0,0)
            o.u.mem_write(RAM,struct.pack('<8H',*code))
            depths.clear()
            dispatch_sp=SP-32 if irq else SP
            # Stop before POPAD or the next guest instruction. IRQ enters
            # via PUSHAD in the normal dispatcher at 00462b1c.
            o.run(0x462b1c if irq else target,
                  {UC_X86_REG_EBP:RAM,UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:0,
                   UC_X86_REG_EDX:0,UC_X86_REG_EAX:0},stops=(0x462b54,0x462b48,0x462ca3))
            n=probe((C.c_uint16*8)(*code),(C.c_uint32*33)(*regs),target,dispatch_sp,irq,observed)
            if not depths or list(observed[:n])!=depths or n<0:
                raise ValueError((hex(opcode),hex(target),irq,depths,n,list(observed[:max(n,0)])))
            result.update(depths)
            digest.update(struct.pack('<IH',target,opcode)+bytes(depths))
    return dict(original_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                direct_store_targets=len(cases)-2,exception_and_irq_cases=2,
                observed_store_calls=sum(result.values()),depths_in_bytes=dict(sorted(result.items())),
                sha256=digest.hexdigest())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=compare(a.exe)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result)
