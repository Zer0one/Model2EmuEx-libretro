#!/usr/bin/env python3
"""Register/immediate DIV against original x86, including original host fault."""
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


def compare_divides(exe, portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    source=Path(__file__).resolve().parents[1]/'port/a68k/divide_ops.inc'
    specs={int(a,16):(int(s),int(cost),mode,int(fault,0)) for a,s,cost,mode,fault in
        re.findall(r'A68K_DIVIDE\((0x[0-9a-f]+), (\d+), (\d+), (\w+), (0x[0-9a-f]+|0)\)',source.read_text())}
    stops={}
    for entry in specs:
        body=o.pe.read(entry,next(t for t in targets if t>entry)-entry)
        stops[entry]=[entry+m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')),body)]
        assert len(stops[entry])==3
    dividends=(0,1,2,0x7fff,0x8000,0xffff,0x10000,0x7fffffff,0x80000000,
               0x80000001,0xffff8000,0xfffffffd,0xfffffffe,0xffffffff)
    divisors=(0,1,2,3,0x7fff,0x8000,0xfffd,0xfffe,0xffff,0x1234)
    rng=random.Random(0xa68d1f);digest=hashlib.sha256();counts=collections.Counter()
    covered=set();host_faults=0;odd_faults=0;guards=0
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);signed,cost,mode,idiv=specs[entry]
        for i,dividend in enumerate(dividends):
            for j,divisor in enumerate(divisors):
                for delta in (-1,0,1):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[opcode&7]=divisor;c[(opcode>>9)&7]=dividend
                    actual=divisor if mode=='IMMEDIATE' else c[opcode&7]&65535
                    c[15]=0x8000;c[16]=0x9000;c[17]=0x20 if i&1 else 0
                    c[29]=0x100;c[19]=0xaabbcc00|(j&1)
                    pc=(0,0x123456,0xfffffffe)[delta+1]
                    flags=(0xac3,0x2c3,0x202,0xa02)[(i+j)%4];host=0x202|(0x400 if j&1 else 0)
                    # Exercise the zero-divisor exception at its own budget
                    # boundary; refund is independent of source addressing.
                    zero_cost=cost-(112 if signed else 95)+o.cost[5]
                    budget=(zero_cost if not actual else cost)+delta
                    vector_target=0x7000+(j+i)%2
                    o.setup_exception(c,budget);o.reads={0x114:vector_target}
                    o.put(SP+4,*([0]*7),STOP)
                    o.u.mem_write(RAM+0x1000,struct.pack('<H',divisor))
                    expected_fault=bool(signed and dividend==0x80000000 and actual==0xffff)
                    # The separate fault probe executes IDIV and proves #DE.
                    # Stop before that already-verified instruction here:
                    # repeatedly injecting #DE into one Unicorn instance has
                    # sticky engine exception state unrelated to the CPU.
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,
                        UC_X86_REG_EDX:flags,UC_X86_REG_EFLAGS:host,
                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},
                        stops=stops[entry]+[0x462c89]+([idiv] if expected_fault else []))
                    failed=bool(expected_fault and o.stop==idiv)
                    assert failed==expected_fault
                    p=portable.cpu(4,c,pc,flags,budget,opcode,vector_target,costs=o.cost,
                                   entry=entry,host_flags=host,extension=divisor)
                    expected=o.get(CTX,33)
                    boundary=6 if failed else 3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
                    key=(hex(opcode),i,j,delta)
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert p['events']==o.events,(key,'events',p['events'],o.events)
                    assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary',p,boundary)
                    assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                    assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                    if failed:
                        assert p['fault']==[6,idiv,0,pc,0xffffffff,p['cycles'],0xffffffff]
                        host_faults+=1
                    elif boundary==3:
                        assert p['fault'][0:3]==[3,0x462c89,5]
                        odd_faults+=1
                    else:assert p['fault']==[0]*7
                    if failed or boundary==3:
                        assert portable.library.a68k_probe_fault_latch()==14;guards+=14
                    counts[('DIVS_' if signed else 'DIVU_')+mode]+=1
                    digest.update(json.dumps([opcode,i,j,delta,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
        result_sha256=digest.hexdigest(),covered_entries=len(covered),
        targets=[f'{t:08x}' for t in sorted(specs)],host_overflow_prefix_cases=host_faults,
        odd_vector_prefix_cases=odd_faults,post_fault_retry_guards=guards,
        limits=['Register/immediate source forms only; memory DIV has pending read-wrapper host-scratch dependencies.',
                'Native prefix preserved at host IDIV fault; no claim of continued original execution or full Windows crash.',
                'Synthetic operands, exception callbacks and cycle boundaries; not complete CPU/sound-board integration.'])
