#!/usr/bin/env python3
"""Register-only A68K handlers against unchanged original code, no ROMs."""
import collections
import hashlib
import json
import random
import re
from pathlib import Path
from a68k_boundary_compare import Oracle, CTX, SP, STOP
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_registers(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3]
    source=Path(__file__).resolve().parents[1]/'port/a68k/register_ops.inc'
    specs={int(a,16):(name,int(bits),int(cost)) for a,name,bits,cost in
           re.findall(r'A68K_REG\((0x[0-9a-f]+), (\w+), (\d+), (\d+)\)',source.read_text())}
    stops={}
    for target in specs:
        code=o.pe.read(target,160);offset=code.index(bytes.fromhex('0fb70c2e'))
        assert code[offset+4:offset+7]==bytes.fromhex('ff248d')
        stops[target]=target+offset
    rng=random.Random(0xa68002);counts=collections.Counter();digest=hashlib.sha256()
    values=[0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x7fffffff,0x80000000,0xffffffff,0xa5c3e791]
    covered=[]
    for opcode,target in enumerate(table):
        if target not in specs:continue
        covered.append(opcode);name,bits,cost=specs[target]
        for i,value in enumerate(values):
            for x in (0,1):
                for delta in (-1,0,1):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[(8 if name=='TST_A' else 0)+(opcode&7)]=value;c[19]=0xfeed0000|x
                    c[17]=(c[17]&~0x20)|(0x20 if i&1 else 0)
                    pc=(0,0x123456,0xfffffffe)[delta+1];flags=(0x2c3,0xa02)[x]
                    host=(0x202,0x602)[i&1];budget=cost+delta
                    o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                    o.run(target,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,
                                  UC_X86_REG_EDX:flags,UC_X86_REG_EFLAGS:host},stops=(stops[target],))
                    p=portable.cpu(4,c,pc,flags,budget,opcode,costs=o.cost,entry=target,host_flags=host)
                    expected=o.get(CTX,33)
                    assert p['context']==expected,(name,hex(opcode),hex(value),x,delta,'context',p['context'],expected)
                    assert p['pc']==(pc+2)&0xffffffff and p['cycles']==delta&0xffffffff
                    assert p['events']==[] and p['fault']==[0]*7
                    assert p['boundary']==(2 if delta<0 else 1)
                    native_flags=expected[18] if delta<0 else o.u.reg_read(UC_X86_REG_EDX)
                    assert p['flags']==native_flags,(name,hex(opcode),hex(value),hex(p['flags']),hex(native_flags))
                    counts[name]+=1;digest.update(json.dumps([opcode,value,x,delta,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],
                limits=['Register-only forms; no memory operand or complete CPU integration.',
                        'Logical-operation AF is undefined on x86; Unicorn value is not a hardware guarantee.'])
