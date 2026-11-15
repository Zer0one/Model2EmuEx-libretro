#!/usr/bin/env python3
"""Native register transfers, immediate operands and quick arithmetic."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,SP,STOP,RAM
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_operands(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa68ea)
    text=(Path(__file__).resolve().parents[1]/'port/a68k/operand_ops.inc').read_text()
    specs={int(a,16):(op,int(bits),int(cost),src) for a,op,bits,cost,src in
        re.findall(r'A68K_OPERAND\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\w+)\)',text)}
    stops={t:t+o.pe.read(t,160).index(bytes.fromhex('0fb70c2e')) for t in specs}
    counts=collections.Counter();covered=set();digest=hashlib.sha256()
    values=[0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x7fffffff,0x80000000,0xffffffff,0x12345678,0xabcdef01]
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,bits,cost,source=specs[entry]
        for i,value in enumerate(values):
            for delta in (-1,0,1):
                c=[rng.getrandbits(32) for _ in range(33)]
                dest=(opcode>>9)&7 if source in ('REGISTER_HIGH','IMMEDIATE_HIGH') else opcode&7
                if op in ('MOVEA','ADDA','SUBA','CMPA'):dest+=8
                c[opcode&15]=value;c[dest]=values[(i+delta)%len(values)]
                c[19]=0xaabbcc00|(i&1);c[17]=(c[17]&~0x20)|(0x20 if i&1 else 0)
                flags=0xac3;host=0x202|(0x400 if i&1 else 0);pc=(0,0x123456,0xfffffffe)[delta+1]
                hi=value>>16 if bits==32 else value&65535;lo=value&65535
                o.setup_exception(c,cost+delta);o.put(SP+4,*([0]*7),STOP)
                o.u.mem_write(RAM+0x1000,struct.pack('<HH',hi,lo))
                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                    UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stops[entry],))
                p=portable.cpu(4,c,pc,flags,cost+delta,opcode,costs=o.cost,entry=entry,host_flags=host,extension=hi,extension2=lo)
                expected=o.get(CTX,33);exited=o.stop is None
                assert p['context']==expected,(op,source,hex(opcode),i,delta,p['context'],expected)
                assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX))
                assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI))
                assert p['cycles']==delta&0xffffffff and p['boundary']==(2 if exited else 1)
                assert p['events']==[] and p['fault']==[0]*7
                counts[op+'_'+source]+=1;digest.update(json.dumps([opcode,i,delta,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
                covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=['Register destinations, current fetch binding and synthetic immediate stream only.',
                        'No complete executor or audio integration; memory destination forms remain open.'])
