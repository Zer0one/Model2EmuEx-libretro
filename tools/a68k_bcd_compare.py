#!/usr/bin/env python3
"""ABCD/SBCD original x86 decimal adjustment and saved-flag merge."""
import hashlib
import json
import random
from a68k_boundary_compare import Oracle,CTX,SP,STOP
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_bcd(exe,portable,nbcd=False):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3]
    specs=({0x486680:('NBCD',0x4866b9)} if nbcd else
           {0x478468:('SBCD',0x4784c2),0x4787f0:('ABCD',0x47884a)})
    rng=random.Random(0xa68bcd);digest=hashlib.sha256();cases=exhaustive=0
    covered=set();counts={name:0 for name,stop in specs.values()}
    values=(0,1,9,10,15,16,25,0x90,0x99,0x9a,0xa0,0xff)
    def check(opcode,entry,left,right,x,z,delta,full):
        nonlocal cases,exhaustive
        c=[rng.getrandbits(32) for _ in range(33)]
        c[opcode&7]=(c[opcode&7]&~255)|right
        if not nbcd:c[(opcode>>9)&7]=(c[(opcode>>9)&7]&~255)|left
        c[19]=(c[19]&~1)|x;c[17]=(c[17]&~0x20)|(0x20 if z else 0)
        flags=(rng.getrandbits(32)&~0x40)|(0x40 if z else 0)
        pc=(0,0x123456,0xfffffffe)[delta+1];budget=6+delta
        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
        stop=specs[entry][1]
        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                     UC_X86_REG_EFLAGS:0x202|(0x400 if x else 0)},stops=(stop,))
        p=portable.cpu(4,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=0x202|(0x400 if x else 0))
        expected=o.get(CTX,33);key=(hex(opcode),left,right,x,z,delta)
        assert p['context']==expected,(key,'context',p['context'],expected)
        assert p['events']==[] and p['fault']==[0]*7
        assert p['cycles']==delta&0xffffffff and p['boundary']==(2 if delta<0 else 1)
        assert p['pc']==(pc+2)&0xffffffff
        assert p['flags']==(expected[18] if delta<0 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
        cases+=1;exhaustive+=full;counts[specs[entry][0]]+=1
        digest.update(json.dumps([key,p],sort_keys=True).encode())
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode)
        for left in ((0,) if nbcd else values):
            for right in (range(256) if nbcd else values):
                for x in (0,1):
                    for z in (0,1):
                        for delta in (-1,0,1):check(opcode,entry,left,right,x,z,delta,nbcd)
    # Every byte pair (including non-BCD digits) and incoming X. Other tests
    # above cover all register aliases, both sticky-Z states and cycle tails.
    for opcode in (() if nbcd else (0x8300,0xc300)):
        for left in range(256):
            for right in range(256):
                for x in (0,1):check(opcode,table[opcode],left,right,x,(left^right)&1,1,True)
    return dict(cases=cases,groups=counts,exhaustive_operand_cases=exhaustive,
        mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
        targets=[f'{t:08x}' for t in specs],
        limits=['Register forms only; no memory BCD qualification.',
                ('NBCD imports full flags; observed OF=0 qualified independently in original Windows for all byte/X pairs.' if nbcd else 'ABCD/SBCD consume DAA/DAS defined CF/ZF; undefined x86 OF is not imported.'),
                'Original-code boundary comparisons, not complete CPU or audio execution.'])
