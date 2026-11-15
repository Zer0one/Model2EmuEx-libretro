#!/usr/bin/env python3
"""Original fetch/data/write range installers versus bounded host bindings."""
import ctypes as C
import hashlib
import struct
from a68k_boundary_compare import Oracle,READ,DATA,WRITE,SP
from unicorn.x86_const import *


def compare_maps(exe,portable):
    o=Oracle(exe);digest=hashlib.sha256();cases=0
    fn=portable.library.a68k_probe_maps
    fn.argtypes=[C.c_uint,C.c_uint32,C.c_uint32,C.c_uint,C.POINTER(C.c_uint32)];fn.restype=C.c_int
    sentinel=struct.pack('<4I',(0x12340000-0xfeed1234)&0xffffffff,0,0,0)*4096
    ranges=[(0,0),(0,0xfff),(0,0xffffff),(0x123000,0x125fff),
            (0xfff,0x1000),(0x1001,0x2000),(0x1001,0x2001),
            (0xffffff,0xffffff),(0xfff000,0xffffff),(0x37,0x9237)]
    for kind,entry,table in ((0,0x4b3280,READ),(1,0x4b32c0,DATA),(2,0x4b3310,WRITE)):
        for start,end in ranges:
            for direct in (False,True):
                o.u.mem_write(table,sentinel)
                ptr=0x72000000 if direct else 0
                regs={UC_X86_REG_EAX:end}
                if kind==0:regs.update({UC_X86_REG_ESI:start,UC_X86_REG_EDI:ptr})
                else:
                    o.put(SP+4,start,ptr)
                    regs.update({UC_X86_REG_EBX:0x71000100,UC_X86_REG_EDI:0x71000110,UC_X86_REG_ESI:0x71000120})
                o.run(entry,regs,count=100000)
                out=(C.c_uint32*(4096*4))();assert fn(kind,start,end,direct,out)
                got=bytes(out);expected=bytes(o.u.mem_read(table,len(sentinel)))
                assert got==expected,(kind,hex(start),hex(end),direct)
                count=((end-start)>>12)+1;first=start>>12
                row=struct.pack('<4I',(ptr-start)&0xffffffff if ptr else 0,
                    *([0]*3 if kind==0 else [0x71000100,0x71000110,0x71000120]))
                assert expected==sentinel[:first*16]+row*count+sentinel[(first+count)*16:]
                cases+=1;digest.update(struct.pack('<4I',kind,start,end,direct)+got)
    guards=0
    for kind,start,end in ((0,1,0),(0,0,0x1000000),(0,0xffffffff,0xffffffff),(3,0,0),(0xffffffff,0,0)):
        out=(C.c_uint32*(4096*4))();assert not fn(kind,start,end,True,out)
        assert bytes(out)==sentinel;guards+=1
    return dict(cases=cases,mismatches=0,host_range_guards=guards,result_sha256=digest.hexdigest(),
                native_entries=['004b3280','004b32c0','004b3310'],
                limits=['Map descriptor effects only; board device bindings remain separate.',
                        'Malformed host ranges rejected without writes, not executed against native out-of-table accesses.'])
