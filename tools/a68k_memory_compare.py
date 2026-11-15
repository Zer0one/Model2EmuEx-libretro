#!/usr/bin/env python3
"""Native MOVE memory-source handlers, including actual original bus wrappers."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,SP,STOP,RAM,READ,DATA,CALL
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class MemoryOracle(Oracle):
    def hook(self,u,at,size,data):
        if CALL+80<=at<=CALL+112 and at%16==CALL%16:
            kind=(at-CALL)//16;self.bus_context=self.get(CTX,33)
            self.events.append(['bus',kind,u.reg_read(UC_X86_REG_ECX),0]);self.ret(self.bus_value);return
        super().hook(u,at,size,data)


def address_model(c,pc,reg,width,mode,ext,low):
    signed=lambda value,bits:value-(1<<bits) if value&(1<<(bits-1)) else value
    base=c[8+reg];pc=(pc+2)&0xffffffff
    if mode in ('INDIRECT','POSTINC'):address=base
    elif mode=='PREDEC':address=base-(2 if width==1 and reg==7 else width)
    elif mode=='ABS16':address=signed(ext,16)
    elif mode=='ABS32':address=(ext<<16)|low
    elif mode in ('DISP16','PCDISP'):address=(pc if mode=='PCDISP' else base)+signed(ext,16)
    else:
        index=c[ext>>12];index=index if ext&0x800 else signed(index&65535,16)
        address=(pc if mode=='PCINDEX' else base)+index+signed(ext&255,8)
    return address&0xffffff


def compare_memory(exe,portable,multiply=False):
    o=MemoryOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table));rng=random.Random(0xa68ea2)
    if multiply:
        text=(Path(__file__).resolve().parents[1]/'port/a68k/multiply_ops.inc').read_text()
        specs={int(a,16):('MULS' if sign=='1' else 'MULU',16,int(cost),mode) for a,sign,cost,mode in
            re.findall(r'A68K_MULTIPLY\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',text)}
    else:
        text=(Path(__file__).resolve().parents[1]/'port/a68k/memory_move_ops.inc').read_text()
        specs={int(a,16):('MOVE',int(bits),int(cost),mode) for a,bits,cost,mode in
            re.findall(r'A68K_MEMORY_MOVE\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',text)}
        text=(Path(__file__).resolve().parents[1]/'port/a68k/memory_binary_ops.inc').read_text()
        specs.update({int(a,16):(op,int(bits),int(cost),mode) for a,op,bits,cost,mode in
            re.findall(r'A68K_MEMORY_BINARY\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)})
        text=(Path(__file__).resolve().parents[1]/'port/a68k/memory_address_ops.inc').read_text()
        specs.update({int(a,16):(op,int(bits),int(cost),mode) for a,op,bits,cost,mode in
            re.findall(r'A68K_MEMORY_ADDRESS\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)})
    stops={a:a+o.pe.read(a,next(t for t in targets if t>a)-a).rindex(bytes.fromhex('0fb70c2e')) for a in specs}
    # Verify original callback-to-wrapper identity, including PC-relative space.
    assert list(struct.unpack('<3I',o.pe.read(0x572a88,12)))==[0x4b3250,0x4b3220,0x4b31f0]
    assert list(struct.unpack('<3I',o.pe.read(0x572aa4,12)))==[0x4b31c0,0x4b3190,0x4b3160]
    counts=collections.Counter();covered=set();digest=hashlib.sha256()
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,bits,cost,mode=specs[entry];width=bits//8
        for i,ext in enumerate((0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)*(2 if multiply else 1)):
            for direct in (False,True):
                c=[rng.getrandbits(32) for _ in range(33)]
                c[17]=0x20 if i&1 else 0;c[19]=i&1
                c[8+(opcode&7)]=(0,0xffffff,0x123fff,0x123000)[i%4]
                pc=(0,0x123456,0xfffffffe)[i%3];flags=0xac3;host=0x202
                low=(0,0xffff,0x7fff,0x8000)[i%4];value=(0,0xffffffff,0x80,0x8000,0x80000000,0xa5c3e791,1,0x7fffffff)[i%8]
                if multiply:
                    values=(0,1,0x7fff,0x8000,0xffff,0x7ffe,0x8001,0xfffe)
                    value=(value&0xffff0000)|values[i%8]
                    c[(opcode>>9)&7]=(c[(opcode>>9)&7]&0xffff0000)|values[(i*3+(i//8))%8]
                    if mode=='REGISTER':c[opcode&7]=(c[opcode&7]&0xffff0000)|(value&65535)
                    if mode=='IMMEDIATE':ext=value&65535
                address=0x123000 if mode in ('REGISTER','IMMEDIATE') else address_model(c,pc,opcode&7,width,mode,ext,low);budget=cost+i%3-1
                o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                o.u.mem_write(READ,bytes(65536));o.u.mem_write(DATA,bytes(65536))
                at=RAM+0x18000;pointer=(at-(address^1 if width==1 else address))&0xffffffff if direct else 0
                for base in (READ,DATA):o.put(base+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                if width==1:o.u.mem_write(at,bytes([value&255]))
                elif width==2:o.u.mem_write(at,struct.pack('<H',value&65535))
                else:o.u.mem_write(at,struct.pack('<HH',value>>16,value&65535))
                o.bus_value=value;o.bus_context=[0]*33
                o.u.mem_write(RAM+0x1000,struct.pack('<HH',ext,low))
                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                    UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                p=portable.cpu(5,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host,
                    extension=ext,extension2=low,bus_value=value,bus_address=address,bus_direct=direct,bus_width=width)
                expected=o.get(CTX,33);exited=o.stop is None
                assert p['context']==expected,(hex(opcode),mode,i,direct,'context',p['context'],expected)
                assert p['events']==o.events and p['bus_context']==o.bus_context,(hex(opcode),mode,i,direct,'bus')
                assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX))
                assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI))
                assert p['cycles']==(budget-cost)&0xffffffff and p['boundary']==(2 if exited else 1)
                counts[op+'_'+mode]+=1;digest.update(json.dumps([opcode,i,direct,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
                covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=[('MULU/MULS register, memory and immediate forms.' if multiply else 'MOVE/MOVEA/OR/AND/ADD/ADDA/SUB/SUBA/CMP/CMPA memory sources; other opcode families remain separate.'),
                        'Direct and callback wrappers plus callback-observed context; arbitrary callback mutation remains separate.'])
