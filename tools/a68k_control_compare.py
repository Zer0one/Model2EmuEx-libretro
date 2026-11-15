#!/usr/bin/env python3
"""Native Scc/DBcc/Bcc/BRA/BSR handler qualification, synthetic instruction stream."""
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


def compare_control(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    text=(Path(__file__).resolve().parents[1]/'port/a68k/control_ops.inc').read_text()
    specs={int(a,16):(name,int(cc)) for a,name,cc in re.findall(r'A68K_CONTROL\((0x[0-9a-f]+), (\w+), (\d+)\)',text)}
    stops={}
    for target in specs:
        end=next(t for t in targets if t>target);code=o.pe.read(target,end-target)
        stops[target]=[target+m.start() for m in re.finditer(bytes.fromhex('0fb70c2e'),code)]
        assert stops[target]
    rng=random.Random(0xa68bcc);counts=collections.Counter();digest=hashlib.sha256();covered=set();odd_faults=0
    def run(opcode,ccr,serial,extension,remaining,vector_target=0x7000):
        nonlocal odd_faults
        entry=table[opcode];name,condition=specs[entry];covered.add(opcode)
        c=[rng.getrandbits(32) for _ in range(33)]
        c[15]=0x8000;c[16]=0x9000;c[17]=0x20 if serial&1 else 0
        c[opcode&7]=(c[opcode&7]&0xffff0000)|(0,1,0xffff,0x8000)[serial%4]
        c[29]=0x100;c[19]=serial&1
        flags=2|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)|(0x200 if serial&1 else 0)
        pc=(0,0x123456,0xfffffffe)[serial%3]
        o.setup_exception(c,remaining);o.reads={0x10c:vector_target}
        o.put(SP+4,*([0]*7),STOP)
        o.u.mem_write(RAM+0x1000,struct.pack('<H',extension))
        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                     UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops[entry]+[0x462c89])
        p=portable.cpu(4,c,pc,flags,remaining,opcode,vector_target,costs=o.cost,entry=entry,extension=extension)
        expected=o.get(CTX,33)
        assert p['context']==expected,(hex(opcode),ccr,serial,'context',p['context'],expected)
        assert p['events']==o.events,(hex(opcode),ccr,serial,'events',p['events'],o.events)
        assert p['cycles']==o.get(0x10ed9b0)[0]
        boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
        assert p['boundary']==boundary,(hex(opcode),ccr,serial,'boundary')
        assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI))
        assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX))
        if boundary==3:
            assert p['fault'][0:3]==[3,0x462c89,3] and p['fault'][4]==vector_target
            assert portable.library.a68k_probe_fault_latch()==14;odd_faults+=1
        else:assert p['fault']==[0]*7
        counts[name]+=1;digest.update(json.dumps([opcode,ccr,serial,extension,remaining,p],sort_keys=True).encode())
    # All covered opcodes, all NZVC combinations. Cycle, wrap, counters and
    # extension data vary deterministically; this is not their full product.
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        for ccr in range(16):
            serial=opcode+ccr
            run(opcode,ccr,serial,(0,1,0x7fff,0x8000,0xfffe,0xffff)[serial%6],
                (0,4,6,8,10,12,18,30)[ccr%8])
    # Every branch condition/width: taken odd destination whose vector is odd
    # must use the approved sticky stop, never continue through recursive tail.
    for cc in range(16):
        for opcode in (0x6000+cc*256,0x6001+cc*256):
            for ccr in range(16):run(opcode,ccr,ccr,1,1000,0x7001)
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
        result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
        odd_vector_fault_cases=odd_faults,
        limits=['Synthetic instruction extension and callbacks; complete dispatcher/board integration remains open.',
                'All covered encodings and NZVC states; other dimensions use deterministic combinations, not exhaustive products.',
                'Native DBcc retains unchecked/unmasked target and current fetch binding.'])
