#!/usr/bin/env python3
"""Native memory NEG/NOT, including read EDX published before the write."""
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, RAM, DATA, WRITE, CALL
from a68k_inventory import decode_dispatch
from a68k_memory_compare import address_model
from a68k_memory_dest_compare import MemoryOracle
from unicorn.x86_const import *


class ScratchOracle(MemoryOracle):
    def hook(self,u,at,size,data):
        if CALL+80<=at<=CALL+112 and at%16==CALL%16:
            u.reg_write(UC_X86_REG_EDX,self.bus_edx)
        super().hook(u,at,size,data)


def compare_unary_scratch(exe,portable):
    o=ScratchOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    rng=random.Random(0xa684400);digest=hashlib.sha256();cases=0;covered=set()
    text=(Path(__file__).resolve().parents[1]/'port/a68k/memory_scratch_ops.inc').read_text()
    specs={int(t,16):(op,int(bits),int(cost),mode) for t,op,bits,cost,mode in
           re.findall(r'A68K_MEMORY_SCRATCH\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    stops={t:t+o.pe.read(t,next(v for v in targets if v>t)-t).rindex(bytes.fromhex('0fb70c2e')) for t in specs}
    values=(0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x7fffffff,0x80000000,
            0xffffffff,0x12345678,0xa5c3e791,0xfffffffe,0x80000001,0x7ffffffe)
    extensions=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,bits,cost,mode=specs[entry];width=bits//8
        for i,value in enumerate(values):
            for direct,write_direct in ((False,False),(False,True),(True,False),(True,True)):
                for delta in (-1,0,1):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[8+(opcode&7)]=(0,0xffffff,0x123fff,0x123000)[i%4]
                    pc=(0,0x123456,0xfffffffe)[delta+1];flags=rng.getrandbits(32)
                    host=0x202|(0x400 if i&1 else 0);ext=extensions[i%8];low=extensions[(i+3)%8]
                    address=address_model(c,pc,opcode&7,width,mode,ext,low);budget=cost+delta
                    o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                    o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                    o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                    at=RAM+0x18000+4*i;offset=address^1 if width==1 else address
                    pointer=(at-offset)&0xffffffff if direct else 0
                    write_pointer=(at-offset)&0xffffffff if write_direct else 0
                    o.put(DATA+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                    o.put(WRITE+(address>>12)*16,write_pointer,CALL+128,CALL+144,CALL+160)
                    packed=bytes([value&255]) if width==1 else struct.pack('<H',value&65535) if width==2 else struct.pack('<HH',value>>16,value&65535)
                    o.u.mem_write(at,packed);o.u.mem_write(RAM+0x1000,struct.pack('<HH',ext,low))
                    o.bus_value=value;o.bus_edx=(0,0xfac3,0xdeadbeef)[delta+1]
                    o.bus_context=[0]*33;o.write_context=[0]*33;o.written_value=0
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                        UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                    p=portable.cpu(11,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host,
                        extension=ext,extension2=low,bus_value=value,bus_address=address,bus_direct=direct,
                        bus_width=width,write_direct=write_direct,bus_edx=pointer if direct else o.bus_edx)
                    key=(hex(opcode),i,direct,write_direct,delta);expected=o.get(CTX,33);exited=o.stop is None
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert p['events']==o.events and p['bus_context']==o.bus_context,(key,'read',p,o.events)
                    assert p['write_context']==o.write_context and p['written_value']==o.written_value,(key,'write',p,o.write_context)
                    assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                    assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                    assert p['cycles']==delta&0xffffffff and p['boundary']==(2 if exited else 1),(key,'boundary')
                    assert p['fault']==[0]*7
                    if direct or write_direct:
                        data=bytes(o.u.mem_read(at,width))
                        memory=data[0] if width==1 else struct.unpack('<H',data)[0] if width==2 else (struct.unpack('<H',data[:2])[0]<<16)|struct.unpack('<H',data[2:])[0]
                        assert p['memory_value']==memory,(key,'memory')
                    cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],limits=[
                    'All memory NEG/NOT encodings, original read/write wrappers, full callback values and observed CPU context.',
                    'Explicit synthetic callback EDX and direct-base tokens; real sound-board bindings remain unqualified.',
                    'No full CPU execution or frontend/audio claim.'])
