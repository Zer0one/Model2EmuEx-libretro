#!/usr/bin/env python3
"""Original JMP/JSR control transfer, stack ordering and odd-vector boundary."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import Oracle, CTX, SP, STOP, RAM
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_jumps(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    text=(Path(__file__).resolve().parents[1]/'port/a68k/jump_ops.inc').read_text()
    specs={int(a,16):(int(call),int(cost),mode) for a,call,cost,mode in re.findall(
        r'A68K_JUMP\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',text)}
    stops={}
    for entry in specs:
        body=o.pe.read(entry,next(t for t in targets if t>entry)-entry)
        stops[entry]=[entry+m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')),body)]
        assert stops[entry]
    rng=random.Random(0xa68ccc);digest=hashlib.sha256();counts=collections.Counter();covered=set();faults=0
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);call,cost,mode=specs[entry]
        for i,extension in enumerate((0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)):
            for ccr in range(16):
                for vector_target in (0x7000,0x7001):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[15]=0x8000;c[16]=0x9000;c[17]=0x20 if i&1 else 0
                    c[8+(opcode&7)]=(0,1,0xfffffe,0xffffffff)[i%4]
                    c[29]=0x100;c[19]=i&1;c[32]=0xab123456
                    flags=2|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)|(0x200 if i&1 else 0)
                    pc=(0,0x123456,0xfffffffe)[i%3];low=(0,1,0xfffe,0xffff)[ccr%4]
                    budget=(cost-1,cost,cost+1,0,1000)[ccr%5]
                    o.setup_exception(c,budget);o.reads={0x10c:vector_target}
                    o.put(SP+4,*([0]*7),STOP);o.u.mem_write(RAM+0x1000,struct.pack('<HH',extension,low))
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops[entry]+[0x462c89])
                    p=portable.cpu(4,c,pc,flags,budget,opcode,vector_target,costs=o.cost,
                                   entry=entry,extension=extension,extension2=low)
                    expected=o.get(CTX,33)
                    key=(hex(opcode),i,ccr,vector_target)
                    boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert p['events']==o.events,(key,'events',p['events'],o.events)
                    assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'cycles/boundary')
                    assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                    assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                    if boundary==3:
                        assert p['fault'][0:3]==[3,0x462c89,3]
                        faults+=1
                    else:assert p['fault']==[0]*7
                    counts[('JSR_' if call else 'JMP_')+mode]+=1
                    digest.update(json.dumps([opcode,i,ccr,vector_target,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
        result_sha256=digest.hexdigest(),covered_entries=len(covered),
        targets=[f'{t:08x}' for t in sorted(specs)],odd_vector_fault_cases=faults,
        limits=['Synthetic instruction stream and stack/vector/bank callbacks, as in the existing branch qualification.',
                'Every encoding and NZVC combination, EA/A7 aliases, raw-PC high byte and odd targets; complete dispatcher/board integration remains open.'])
