#!/usr/bin/env python3
"""TRAP/TRAPV native exception PCs, cycle tails and approved fault prefixes."""
import collections
import hashlib
import json
import random
from a68k_boundary_compare import Oracle, CTX, SP, STOP
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_software_traps(exe, portable, usp=False):
    o=Oracle(exe); table=decode_dispatch(o.pe)[3]
    targets=({0x484a40:(0x484a6b,0x484a8d),0x484a98:(0x484ac3,0x484ae5)} if usp else
             {0x486dd4:(0x486df4,),0x486e00:(0x486e23,0x486e3b)})
    rng=random.Random(0xa68a7); counts=collections.Counter(); digest=hashlib.sha256()
    covered=set(); odd=0
    for opcode,entry in enumerate(table):
        if entry not in targets:continue
        covered.add(opcode)
        for ccr in range(32):
            for supervisor in (False,True):
                for target in (0,0x7000,0x7001,0xab007000):
                    for delta in (-1,0,1):
                        c=[rng.getrandbits(32) for _ in range(33)]
                        c[15]=0x8000;c[16]=0x9000;c[17]=0x20 if supervisor else 0
                        c[19]=0xfeed0000|((ccr>>4)&1);c[29]=0x100
                        flags=0x202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                        vector=(None if supervisor else 8) if usp else 32+(opcode&15) if entry==0x486dd4 else 7 if flags&0x800 else None
                        cost=(o.cost[vector] if vector is not None else 0)+(4 if usp or entry==0x486e00 else 0)
                        budget=cost+delta; pc=(0,0xfffffffe,0x123456)[delta+1]
                        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                        if vector is not None:o.reads={0x100+4*vector:target}
                        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,
                                     UC_X86_REG_EDX:flags},stops=targets[entry]+(0x462c89,))
                        p=portable.cpu(4,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry)
                        key=(hex(opcode),ccr,supervisor,hex(target),delta)
                        expected=o.get(CTX,33)
                        boundary=3 if o.stop==0x462c89 else 1 if o.stop in targets[entry] else 2
                        assert p['context']==expected,(key,'context',p['context'],expected)
                        assert p['events']==o.events,(key,'events')
                        assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                        assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                        assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                        if boundary==3:
                            saved_pc=(pc+2)&0xffffffff if entry==0x486dd4 else pc
                            assert p['fault']==[3,0x462c89,vector,saved_pc,target,p['cycles'],flags]
                            odd+=1
                        else:assert p['fault']==[0]*7
                        name=('MOVE_TO_USP' if entry==0x484a40 else 'MOVE_FROM_USP') if usp else 'TRAP' if entry==0x486dd4 else 'TRAPV'
                        counts[name]+=1
                        digest.update(json.dumps([opcode,ccr,supervisor,target,delta,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in targets],odd_vector_prefix_cases=odd,
                limits=['Synthetic exception callbacks and operands; not complete CPU integration.'])
