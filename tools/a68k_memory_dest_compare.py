#!/usr/bin/env python3
"""Native Dn-to-memory arithmetic, including read and write callback timing."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,SP,STOP,RAM,READ,DATA,WRITE,CALL
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class MemoryOracle(Oracle):
    def hook(self,u,at,size,data):
        if CALL+80<=at<=CALL+112 and at%16==CALL%16:
            kind=(at-CALL)//16;self.bus_context=self.get(CTX,33)
            self.events.append(['bus',kind,u.reg_read(UC_X86_REG_ECX),0]);self.ret(self.bus_value);return
        if CALL+128<=at<=CALL+160 and at%16==CALL%16:
            kind=(at-CALL)//16;self.write_context=self.get(CTX,33)
            self.written_value=u.reg_read(UC_X86_REG_EDX)
            self.events.append(['bus',kind,u.reg_read(UC_X86_REG_ECX),self.written_value]);self.ret(0);return
        super().hook(u,at,size,data)


from a68k_memory_compare import address_model


def compare_memory_dest(exe,portable,immediate=False,unary=False,address_group=False,bit=False,transfer=False,shift=False):
    o=MemoryOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table));rng=random.Random(0xa68ea2)
    root=Path(__file__).resolve().parents[1]
    if shift:
        text=(root/'port/a68k/shift_memory_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,'SHIFT') for a,op,bits,cost,mode in
            re.findall(r'A68K_SHIFT_MEMORY\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    elif transfer:
        text=(root/'port/a68k/move_dest_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,source) for a,op,bits,cost,mode,source in
            re.findall(r'A68K_MOVE_DEST\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+), (\w+)\)',text)}
    elif bit:
        text=(root/'port/a68k/bit_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,source) for a,op,bits,cost,mode,source in
            re.findall(r'A68K_BIT\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+), (\w+)\)',text)}
    elif address_group:
        text=(root/'port/a68k/address_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,'ADDRESS') for a,op,bits,cost,mode in
            re.findall(r'A68K_ADDRESS\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    elif unary:
        text=(root/'port/a68k/memory_unary_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,'UNARY') for a,op,bits,cost,mode in
            re.findall(r'A68K_MEMORY_UNARY\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    elif immediate:
        text=(root/'port/a68k/memory_operand_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,source) for a,op,bits,cost,mode,source in
            re.findall(r'A68K_MEMORY_OPERAND\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+), (\w+)\)',text)}
    else:
        text=(root/'port/a68k/memory_dest_ops.inc').read_text()
        specs={int(a,16):(op,int(bits),int(cost),mode,'REGISTER_HIGH') for a,op,bits,cost,mode in
            re.findall(r'A68K_MEMORY_DEST\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    # Immediate bit handlers also fetch their count into ECX. Stop at the final
    # opcode fetch, not the earlier identical extension-read instruction.
    stops={a:a+o.pe.read(a,next(t for t in targets if t>a)-a).rindex(bytes.fromhex('0fb70c2e')) for a in specs}
    # Verify original callback-to-wrapper identity, including PC-relative space.
    assert list(struct.unpack('<3I',o.pe.read(0x572a88,12)))==[0x4b3250,0x4b3220,0x4b31f0]
    assert list(struct.unpack('<3I',o.pe.read(0x572aa4,12)))==[0x4b31c0,0x4b3190,0x4b3160]
    counts=collections.Counter();covered=set();digest=hashlib.sha256()
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,bits,cost,mode,source=specs[entry];width=bits//8
        for i,ext in enumerate((0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)*(2 if unary or bit or shift else 1)):
            for direct,write_direct in ((False,False),(False,True),(True,False),(True,True)):
                c=[rng.getrandbits(32) for _ in range(33)]
                c[17]=0x20 if i&1 else 0;c[19]=i&1
                reg=(opcode>>9)&7 if transfer else opcode&7
                c[8+reg]=(0,0xffffff,0x123fff,0x123000)[i%4]
                pc=(0,0x123456,0xfffffffe)[i%3];flags=(i*0x11111111)&0xffffffff if bit else (0xac3 if i&8 else 0xa83) if unary else 0xac3;host=0x202
                low=(0,0xffff,0x7fff,0x8000)[i%4];value=(0,0xffffffff,0x80,0x8000,0x80000000,0xa5c3e791,1,0x7fffffff)[i%8]
                imm=(0xffff,0x80000000,0xffffffff,1,0,0x7fff,0x8000,0x7fffffff)[i%8]
                if bit:
                    imm=(0,1,7,8,15,16,31,32,33,63,255,65535,0x80000000,0xffffffff,5,27)[i]
                    if mode=='REGISTER':c[opcode&7]=value
                    if source=='REGISTER_HIGH':c[(opcode>>9)&7]=imm
                if transfer and source=='REGISTER_LOW':
                    c[opcode&15]=(0,0xffffffff,0x80,0x8000,0x80000000,0xa5c3e791,1,0x7fffffff)[(i+1)%8]
                prefix=([imm>>16,imm&65535] if bits==32 and not bit else [imm&65535]) if source=='IMMEDIATE_LOW' else []
                words=(prefix+[ext,low]+[0]*4)[:4]
                address=0x123000 if mode in ('REGISTER','IMMEDIATE') else address_model(c,(pc+2*len(prefix))&0xffffffff,reg,width,mode,ext,low);budget=cost+i%3-1
                if address_group:
                    address=((c[15]-4) if op in ('LINK','PEA') else c[8+(opcode&7)] if op=='UNLK' else 0x123000)&0xffffff
                o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                o.u.mem_write(READ,bytes(65536));o.u.mem_write(DATA,bytes(65536));o.u.mem_write(WRITE,bytes(65536))
                at=RAM+0x18000;pointer=(at-(address^1 if width==1 else address))&0xffffffff if direct else 0
                for base in (READ,DATA):o.put(base+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                write_pointer=(at-(address^1 if width==1 else address))&0xffffffff if write_direct else 0
                o.put(WRITE+(address>>12)*16,write_pointer,CALL+128,CALL+144,CALL+160)
                if width==1:o.u.mem_write(at,bytes([value&255]))
                elif width==2:o.u.mem_write(at,struct.pack('<H',value&65535))
                else:o.u.mem_write(at,struct.pack('<HH',value>>16,value&65535))
                o.bus_value=value;o.bus_context=[0]*33;o.write_context=[0]*33;o.written_value=0
                o.u.mem_write(RAM+0x1000,struct.pack('<4H',*words))
                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                    UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                p=portable.cpu(6,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host,
                    extension=words[0],extension2=words[1],extension3=words[2],extension4=words[3],bus_value=value,bus_address=address,bus_direct=direct,bus_width=width,write_direct=write_direct)
                expected=o.get(CTX,33);exited=o.stop is None
                assert p['context']==expected,(hex(opcode),mode,i,direct,'context',p['context'],expected)
                assert p['events']==o.events and p['bus_context']==o.bus_context,(hex(opcode),mode,i,direct,'bus')
                assert p['write_context']==o.write_context and p['written_value']==o.written_value,(hex(opcode),mode,i,direct,write_direct,'write')
                data=bytes(o.u.mem_read(at,width))
                memory_value=int.from_bytes(data,'little') if width<4 else (int.from_bytes(data[:2],'little')<<16)|int.from_bytes(data[2:],'little')
                assert p['memory_value']==memory_value,(hex(opcode),mode,i,direct,write_direct,'memory',hex(p['memory_value']),hex(memory_value))
                assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX))
                assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI))
                assert p['cycles']==(budget-cost)&0xffffffff and p['boundary']==(2 if exited else 1)
                counts[op+'_'+mode]+=1;digest.update(json.dumps([opcode,i,direct,write_direct,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
                covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=[('Word memory shifts/rotates only.' if shift else 'MOVE register/immediate to memory only.' if transfer else 'BTST/BCHG/BCLR/BSET register/memory and native BTST immediate-destination forms.' if bit else 'LEA/PEA/LINK/UNLK only.' if address_group else 'CLR/TST/TAS/NEGX/NBCD memory forms only.' if unary else 'Immediate/quick memory operands only.' if immediate else 'OR/AND/EOR/ADD/SUB Dn to memory only.')+' Other memory destinations and instruction families remain open.',
                        'All four direct/callback read/write combinations, including full write value and context at both callbacks; arbitrary callback mutation remains separate.'])
