#!/usr/bin/env python3
"""Native binary register operations and X/CCR propagation."""
import collections
import hashlib
import json
import random
import re
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,SP,STOP
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_binary(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa68add)
    text=(Path(__file__).resolve().parents[1]/'port/a68k/binary_ops.inc').read_text()
    specs={int(a,16):(name,int(bits),int(cost),int(mask)) for a,name,bits,cost,mask in
           re.findall(r'A68K_BINARY\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\d+)\)',text)}
    stops={t:t+o.pe.read(t,160).index(bytes.fromhex('0fb70c2e')) for t in specs}
    counts=collections.Counter();covered=set();digest=hashlib.sha256()
    pairs=[(0,0),(0,1),(1,0xffffffff),(0x7f,1),(0x80,0xff),(0xff,1),
           (0x7fff,1),(0x8000,0xffff),(0xffff,1),(0x7fffffff,1),(0x80000000,0xffffffff),
           (0xffffffff,1),(0xffffffff,0xffffffff),(0x01234567,0x89abcdef)]
    pairs += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(8)]
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);name,bits,cost,source_mask=specs[entry]
        for i,(left,right) in enumerate(pairs):
            for x in (0,1):
                c=[rng.getrandbits(32) for _ in range(33)]
                src=opcode&source_mask;dst=(opcode>>9)&7
                if name in ('ADDA','SUBA','CMPA'):dst+=8
                if name=='EOR':src,dst=dst,src
                c[src]=right;c[dst]=left # Self-aliasing naturally uses one value.
                c[19]=0xfeed0000|x;c[17]=(c[17]&~0x20)|(0x20 if i&1 else 0)
                flags=2|(0x40 if (i+x)&1 else 0);host=0x202|(0x400 if i&1 else 0)
                pc=(0,0x123456,0xfffffffe)[i%3];budget=cost+(i%3)-1
                o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                             UC_X86_REG_EFLAGS:host},stops=(stops[entry],))
                p=portable.cpu(4,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host)
                expected=o.get(CTX,33)
                assert p['context']==expected,(name,hex(opcode),i,x,'context',p['context'],expected)
                exited=o.stop is None
                assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX)),(name,hex(opcode),i,x,'flags')
                assert p['pc']==(pc+2)&0xffffffff and p['cycles']==(budget-cost)&0xffffffff
                assert p['boundary']==(2 if exited else 1) and p['events']==[] and p['fault']==[0]*7
                counts[name]+=1;digest.update(json.dumps([opcode,i,x,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=['Register operands only; no memory forms or complete sound CPU integration.',
                        'Boundary and seeded random pairs, not exhaustive operand products.'])
