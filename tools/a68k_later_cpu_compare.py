#!/usr/bin/env python3
"""Native RTD/MOVEC feature gating, opcode-PC quirks and selector aliases."""
import collections
import hashlib
import json
import random
import struct
from a68k_boundary_compare import CTX, SP, STOP, RAM, DATA, CALL
from a68k_restore_compare import ScriptOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_later_cpu(exe,portable):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa684e74)
    specs={0x4e74:(0x48b5b4,(0x48b612,0x48b650)),0x4e7a:(0x48b65c,(0x48b6ac,0x48b6cf)),
           0x4e7b:(0x48b6dc,(0x48b734,0x48b757))}
    for opcode,(entry,stops) in specs.items():
        assert [i for i,t in enumerate(table) if t==entry]==[opcode]
        for stop in stops:assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
    digest=hashlib.sha256();counts=collections.Counter();odd=0
    def check(opcode,ext,feature,supervisor,budget,target,stack,destination):
        nonlocal odd
        c=[rng.getrandbits(32) for _ in range(33)]
        c[15]=stack;c[16]=0x9000;c[28]=0x123000;c[29]=0x100
        c[17]=(c[17]&0xffffff00)|(0x20 if supervisor else 0);c[31]=feature
        pc=(0,0x123456,0xfffffffe)[ext%3];flags=rng.getrandbits(32)
        entry,stops=specs[opcode];stops=stops+(0x48b5a8,)
        script=[[7,stack&0xffffff,destination]] if opcode==0x4e74 and feature else []
        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
        o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
        o.reads={0x100+v*4:target for v in range(256)}
        # Map the actual opcode at PC too: original RTD reads THIS word as its
        # displacement. The varying extension must not affect its A7 update.
        o.u.mem_write(RAM+0x1000,struct.pack('<2H',opcode,ext))
        o.put(0x10ed9b8,0,0);o.script=script;o.cursor=0;o.contexts=[]
        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                    UC_X86_REG_EBP:(RAM+0x1000-pc)&0xffffffff},stops=stops+(0x462c89,))
        p=portable.cpu(8,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry,extension=ext,script=script)
        key=(hex(opcode),ext,feature,supervisor,budget,hex(target),hex(stack),hex(destination))
        expected=o.get(CTX,33);boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops else 2
        assert p['context']==expected,(key,'context',p['context'],expected)
        assert o.cursor==len(script) and p['events']==o.events,(key,'events')
        assert p['script_context']==o.contexts,(key,'callback contexts')
        assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
        livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
        liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
        assert p['pc']==livepc and p['flags']==liveflags,(key,'live')
        assert [p['illegal_opcode'],p['illegal_pc']]==o.get(0x10ed9b8,2),(key,'illegal metadata')
        if boundary==3:
            vector=(o.events[-1][1]-0x100)//4
            exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
            assert p['fault']==[3,0x462c89,vector,exception_pc,target,p['cycles'],liveflags]
            odd+=1
        else:assert p['fault']==[0]*7
        counts[{0x4e74:'RTD',0x4e7a:'MOVEC_FROM',0x4e7b:'MOVEC_TO'}[opcode]]+=1
        digest.update(json.dumps([key,p],sort_keys=True).encode())
    for opcode in (0x4e7a,0x4e7b):
        for ext in range(65536):check(opcode,ext,1,True,5,0xab008000,0x123fff,0)
        for ext in (0,1,0x800,0x801,0xffff,0x7000,0xf800,0x5555):
            for feature in (0,1,0x80000000):
                for supervisor in (False,True):
                    for budget in (3,4,5,100):
                        for target in (0xab008000,0x8001):check(opcode,ext,feature,supervisor,budget,target,0xffffffff,0)
    for ext in (0,0x7fff,0x8000,0xffff):
        for feature in (0,1,0x80000000):
            for supervisor in (False,True):
                for budget in (15,16,17,100):
                    for stack in (0,1,0xfffffe,0xffffffff,0x123fff,0x123000):
                        for destination in (0,0x7001,0xab007000,0xffffffff):
                            for target in (0xab008000,0x8001):check(0x4e74,ext,feature,supervisor,budget,target,stack,destination)
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=3,targets=[f'{v[0]:08x}' for v in specs.values()],
                odd_vector_prefix_cases=odd,limits=['All 65,536 MOVEC extension encodings in both directions, plus gated/privilege/budget paths.',
                    'RTD retains original opcode-address displacement read; no generic 68010 correctness or full sound execution claim.'])
