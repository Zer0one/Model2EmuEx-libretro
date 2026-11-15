#!/usr/bin/env python3
"""Compare native memory-to-memory MOVE and ordered effective-address effects."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_memory_dest_compare import MemoryOracle
from a68k_memory_compare import address_model
from a68k_boundary_compare import CTX,SP,STOP,RAM,READ,DATA,WRITE,CALL
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def ea(c,pc,reg,width,mode,ext,low):
    address=address_model(c,(pc-2)&0xffffffff,reg,width,mode,ext,low)
    step=2 if width==1 and reg==7 else width
    if mode=='POSTINC':c[8+reg]=(c[8+reg]+step)&0xffffffff
    if mode=='PREDEC':c[8+reg]=(c[8+reg]-step)&0xffffffff
    words=[] if mode in ('INDIRECT','POSTINC','PREDEC') else [ext,low] if mode=='ABS32' else [ext]
    return address,(pc+2*len(words))&0xffffffff,words


def compare_move_memory(exe,portable):
    o=MemoryOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    text=(Path(__file__).resolve().parents[1]/'port/a68k/move_memory_ops.inc').read_text()
    specs={int(a,16):(int(bits),int(cost),src,dst) for a,bits,cost,src,dst in
        re.findall(r'A68K_MOVE_MEMORY\((0x[0-9a-f]+), (\d+), (\d+), (\w+), (\w+)\)',text)}
    stops={a:a+o.pe.read(a,next(t for t in targets if t>a)-a).rindex(bytes.fromhex('0fb70c2e')) for a in specs}
    rng=random.Random(0xa68d00);counts=collections.Counter();digest=hashlib.sha256();covered=set();same_address=0;same_register=0
    patterns=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)
    values=(0,0xffffffff,0x80,0x8000,0x80000000,0xa5c3e791,1,0x7fffffff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);bits,cost,source,destination=specs[entry];width=bits//8
        src=opcode&7;dst=(opcode>>9)&7
        for i in range(8):
            for direct,write_direct in ((False,False),(False,True),(True,False),(True,True)):
                c=[rng.getrandbits(32) for _ in range(33)];c[17]=0x20 if i&1 else 0;c[19]=i&1
                c[8+src]=(0,0xffffff,0x123fff,0x123000)[i%4]
                if src!=dst:c[8+dst]=(0x123000,0,0xffffff,0x123fff)[(i+1)%4]
                pc=(0,0x123456,0xfffffffe)[i%3];flags=0xac3;host=0x202;budget=cost+i%3-1
                model=c.copy()
                address,after,words=ea(model,(pc+2)&0xffffffff,src,width,source,patterns[i],patterns[(i+3)%8])
                write_address,after,tail=ea(model,after,dst,width,destination,patterns[7-i],patterns[(i+5)%8])
                words=(words+tail+[0]*4)[:4];separate=address!=write_address
                same_address+=not separate;same_register+=src==dst
                value=values[i];write_value=value^0xffffffff
                o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                for base in (READ,DATA,WRITE):o.u.mem_write(base,bytes(65536))
                read_at=RAM+0x18000;write_at=RAM+0x18010 if separate else read_at
                pointer=(read_at-(address^1 if width==1 else address))&0xffffffff if direct else 0
                for base in (READ,DATA):o.put(base+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                pointer=(write_at-(write_address^1 if width==1 else write_address))&0xffffffff if write_direct else 0
                o.put(WRITE+(write_address>>12)*16,pointer,CALL+128,CALL+144,CALL+160)
                def store(at,v):
                    o.u.mem_write(at,bytes([v&255]) if width==1 else struct.pack('<H',v&65535) if width==2 else struct.pack('<HH',v>>16,v&65535))
                store(read_at,value)
                if separate:store(write_at,write_value)
                o.bus_value=value;o.bus_context=[0]*33;o.write_context=[0]*33;o.written_value=0
                o.u.mem_write(RAM+0x1000,struct.pack('<4H',*words))
                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                    UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                p=portable.cpu(7,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host,
                    extension=words[0],extension2=words[1],extension3=words[2],extension4=words[3],
                    bus_value=value,bus_address=address,bus_direct=direct,bus_width=width,
                    write_direct=write_direct,write_address=write_address,write_value=write_value,separate_write=separate)
                expected=o.get(CTX,33);exited=o.stop is None;tag=(hex(opcode),source,destination,i,direct,write_direct)
                assert p['context']==expected,(tag,'context',p['context'],expected)
                assert p['events']==o.events and p['bus_context']==o.bus_context,(tag,'read',p['events'],o.events)
                assert p['write_context']==o.write_context and p['written_value']==o.written_value,(tag,'write')
                data=bytes(o.u.mem_read(write_at,width))
                memory_value=int.from_bytes(data,'little') if width<4 else (int.from_bytes(data[:2],'little')<<16)|int.from_bytes(data[2:],'little')
                assert p['memory_value']==memory_value,(tag,'memory',p['memory_value'],memory_value)
                assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX))
                assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI))
                assert p['cycles']==(budget-cost)&0xffffffff and p['boundary']==(2 if exited else 1) and p['fault']==[0]*7
                counts[source+'_'+destination]+=1;digest.update(json.dumps([opcode,i,direct,write_direct,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
                covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                same_address_cases=same_address,same_register_cases=same_register,
                limits=['All covered MOVE encodings and four direct/callback combinations; operands/extensions vary deterministically.',
                        'Independent read/write maps and exact-address backing aliases; full board mapping and arbitrary callback mutation remain separate.'])
