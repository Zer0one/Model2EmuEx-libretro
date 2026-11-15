#!/usr/bin/env python3
"""Original STOP status import, privilege fault and IRQ-before-idle ordering."""
import hashlib
import json
import random
import struct
from a68k_boundary_compare import Oracle, CTX, SP, STOP, RAM
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_stop(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];entry=0x486ee0;opcode=0x4e72
    assert [i for i,t in enumerate(table) if t==entry]==[opcode]
    stops=(0x486f70,0x486f93,0x462b48)
    for stop in stops:assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
    rng=random.Random(0xa684e72);digest=hashlib.sha256();cases=odd=0
    for ccr in range(32):
        for high in (0,1,3,7,0x20,0x21,0xa3,0xa7):
            for irq in range(8):
                for supervisor in (False,True):
                    for budget in (0xffffffff,0,100):
                        for target in (0xab008000,0x8001):
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[15]=0x123fff;c[16]=0x9000;c[28]=0x123000;c[29]=0x100
                            c[17]=(c[17]&0xffffff00)|(0x20 if supervisor else 0)
                            c[21]=(c[21]&0xffffff00)|irq|0x78
                            pc=(0,0x123456,0xfffffffe)[ccr%3];flags=0xfedc0ac3;sr=(high<<8)|ccr
                            ack=-1 if ccr&1 else 31
                            o.setup_exception(c,budget);o.ack=ack;o.put(SP+4,*([0]*7),STOP)
                            o.reads={0x100+v*4:target for v in range(256)}
                            o.u.mem_write(RAM+0x1000,struct.pack('<H',sr))
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops+(0x462c89,))
                            p=portable.cpu(4,c,pc,flags,budget,opcode,target,ack=ack,costs=o.cost,entry=entry,extension=sr)
                            key=(ccr,high,irq,supervisor,budget,hex(target));expected=o.get(CTX,33)
                            boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops else 2
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert p['events']==o.events,(key,'events',p['events'],o.events)
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                            livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                            liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                            assert p['pc']==livepc and p['flags']==liveflags,(key,'live')
                            if boundary==3:
                                vector=(o.events[-1][1]-0x100)//4
                                exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
                                assert p['fault']==[3,0x462c89,vector,exception_pc,target,p['cycles'],liveflags]
                                odd+=1
                            else:assert p['fault']==[0]*7
                            cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=1,targets=[f'{entry:08x}'],
                odd_vector_prefix_cases=odd,limits=['Original STOP boundary including all IRQ levels, imported CCR and privilege paths.',
                'CPU boundary only; stopped-CPU scheduler wakeup and full sound execution remain integration work.'])
