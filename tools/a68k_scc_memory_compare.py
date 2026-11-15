#!/usr/bin/env python3
"""Original conditional byte stores, including inherited EAX high bytes."""
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, RAM, WRITE, CALL
from a68k_memory_dest_compare import MemoryOracle
from a68k_memory_compare import address_model
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_scc_memory(exe,portable):
    o=MemoryOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    rng=random.Random(0xa685cc);digest=hashlib.sha256();cases=0;covered=set()
    text=(Path(__file__).resolve().parents[1]/'port/a68k/scc_memory_ops.inc').read_text()
    specs={int(t,16):(int(cc),int(cost),mode) for t,cc,cost,mode in
           re.findall(r'A68K_SCC_MEMORY\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',text)}
    stops={t:t+o.pe.read(t,next(v for v in targets if v>t)-t).rindex(bytes.fromhex('0fb70c2e')) for t in specs}
    extensions=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);cc,cost,mode=specs[entry]
        for ccr in range(16):
            for i,eax in enumerate((0,0xffffffff,0x12345678,0x89abcdef)):
                for direct in (False,True):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[8+(opcode&7)]=(0,0xffffff,0x123fff,0x123000)[i]
                    serial=ccr+i;delta=serial%3-1;pc=(0,0x123456,0xfffffffe)[serial%3]
                    flags=2|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)|(0x200 if i&1 else 0)
                    ext=extensions[serial%8];low=extensions[(serial+3)%8]
                    address=address_model(c,pc,opcode&7,1,mode,ext,low);budget=cost+delta
                    o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                    o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                    at=RAM+0x18000;pointer=(at-(address^1))&0xffffffff if direct else 0
                    o.put(WRITE+(address>>12)*16,pointer,CALL+128,CALL+144,CALL+160)
                    o.u.mem_write(at,b'\x78');o.u.mem_write(RAM+0x1000,struct.pack('<HH',ext,low))
                    o.bus_context=[0]*33;o.write_context=[0]*33;o.written_value=0
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                        UC_X86_REG_EAX:eax,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                    p=portable.cpu(13,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,
                        extension=ext,extension2=low,bus_value=0x78,bus_address=address,
                        bus_width=1,write_direct=direct,native_eax=eax)
                    key=(hex(opcode),ccr,i,direct);expected=o.get(CTX,33);exited=o.stop is None
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert p['events']==o.events and p['bus_context']==[0]*33,(key,'events',p,o.events)
                    assert p['write_context']==o.write_context and p['written_value']==o.written_value,(key,'write',p,o.write_context)
                    assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                    assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                    assert p['cycles']==delta&0xffffffff and p['boundary']==(2 if exited else 1),(key,'boundary')
                    assert p['fault']==[0]*7
                    if direct:assert p['memory_value']==bytes(o.u.mem_read(at,1))[0],(key,'memory')
                    cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],limits=[
                    'Every memory Scc encoding and NZVC combination; varied incoming EAX, direct/callback writes and addressing extensions.',
                    'Entry EAX is explicit synthetic input. Propagation from previous instructions and native callback return EAX remains executor/board work.',
                    'No complete CPU, sound, state or frontend execution claim.'])
