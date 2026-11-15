#!/usr/bin/env python3
"""Native RESET output callback, preserved prefetch and unconditional dispatch."""
import hashlib
import json
import random
import struct
from a68k_boundary_compare import Oracle, CTX, SP, STOP, RAM, CALL
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class ResetOracle(Oracle):
    def hook(self,u,at,size,data):
        if at==CALL+192:
            self.events.append(['reset']);self.reset_context=self.get(CTX,33)
            if self.reset_mutate:
                self.put(CTX+20*4,self.reset_pc);self.put(CTX+18*4,self.reset_flags)
                self.u.mem_write(RAM+0x1000,struct.pack('<H',self.next_opcode^65535))
            self.ret();return
        super().hook(u,at,size,data)


def compare_reset_instruction(exe,portable):
    o=ResetOracle(exe);table=decode_dispatch(o.pe)[3];entry=0x486e48;opcode=0x4e70
    assert [i for i,t in enumerate(table) if t==entry]==[opcode]
    assert o.pe.read(0x486eba,7)==bytes.fromhex('ff248d16125300')
    rng=random.Random(0xa684e70);digest=hashlib.sha256();cases=odd=0
    for ccr in range(32):
        for supervisor in (False,True):
            for callback in range(3):
                for next_opcode in (0,0x4e71,0x4e70,0x4e75,0x7000,0xffff):
                    for budget in (0,131,132,133,1000):
                        for target in (0xab008000,0x8001):
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[15]=0x123fff;c[16]=0x9000;c[29]=0x100
                            c[17]=(c[17]&0xffffff00)|(0x20 if supervisor else 0)
                            c[25]=RAM+0x500 if callback else 0;c[19]=(c[19]&~1)|((ccr>>4)&1)
                            flags=0xfedc0202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                            flags=(flags&~0x8c1)|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                            pc=(0,0x123456,0xfffffffe)[ccr%3]
                            o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                            o.put(RAM+0x500,CALL+192);o.reset_context=[0]*33;o.reset_mutate=callback==2
                            o.reset_pc=(0,0xffffffff,0xab007001)[ccr%3];o.reset_flags=rng.getrandbits(32);o.next_opcode=next_opcode
                            o.reads={0x120:target};o.u.mem_write(RAM+0x1000,struct.pack('<H',next_opcode))
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(0x486eba,0x486e72,0x462c89))
                            p=portable.cpu(9,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry,extension=next_opcode,
                                           reset_target_pc=o.reset_pc if callback==2 else None,reset_target_flags=o.reset_flags)
                            key=(ccr,supervisor,callback,next_opcode,budget,hex(target));expected=o.get(CTX,33)
                            boundary=7 if o.stop==0x486eba else 3 if o.stop==0x462c89 else 1 if o.stop==0x486e72 else 2
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert p['events']==o.events and p['reset_context']==o.reset_context,(key,'callback')
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                            livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                            liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                            assert p['pc']==livepc and p['flags']==liveflags,(key,'live')
                            assert p['prefetched_opcode']==(o.u.reg_read(UC_X86_REG_ECX) if boundary==7 else 0),(key,'prefetch')
                            if boundary==3:
                                assert p['fault']==[3,0x462c89,8,pc,target,p['cycles'],liveflags];odd+=1
                            else:assert p['fault']==[0]*7
                            cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=1,targets=[f'{entry:08x}'],
                odd_vector_prefix_cases=odd,limits=['RESET output callback absent/present/mutating PC, flags and instruction bytes; native prefetched dispatch preserved.',
                    'Explicit prefetch boundary is prepared for the future execution loop; this is not complete CPU scheduling qualification.'])
