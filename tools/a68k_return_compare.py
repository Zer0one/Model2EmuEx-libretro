#!/usr/bin/env python3
"""Original RTS stack read/publication, PC rebind and odd-target exceptions."""
import hashlib
import json
import random
import struct
from a68k_boundary_compare import CTX, SP, STOP, RAM, READ, DATA, CALL
from a68k_memory_compare import MemoryOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class ReturnOracle(MemoryOracle):
    def hook(self,u,at,size,data):
        # Reuse the established synthetic vector service independently from
        # the real stack-read wrapper. This fixture has one operand mapping;
        # it does not claim stack/vector bus-alias or full-board coverage.
        if at==0x4b31f0 and self.get(u.reg_read(UC_X86_REG_ESP))[0]==0x462c7a:
            address=u.reg_read(UC_X86_REG_ECX)
            self.events.append(['read32',address]);self.ret(self.reads[address]);return
        super().hook(u,at,size,data)


def compare_returns(exe,portable):
    o=ReturnOracle(exe);table=decode_dispatch(o.pe)[3]
    entry=0x485cf8;opcode=0x4e75
    assert [i for i,t in enumerate(table) if t==entry]==[opcode]
    stops=(0x485d43,0x485d81)
    for stop in stops:assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
    rng=random.Random(0xa68e75);digest=hashlib.sha256();cases=odd=0
    for stack in (0,1,0xfffffe,0xffffffff,0x123fff,0x123000):
        for destination in (0,1,0x7000,0x7001,0xab007000,0xffffffff):
            for ccr in range(32):
                for supervisor in (False,True):
                    for direct in (False,True):
                        for vector_target in (0x8000,0x8001):
                            for delta in (-1,0,1):
                                c=[rng.getrandbits(32) for _ in range(33)]
                                c[15]=stack;c[16]=0x9000;c[17]=0x20 if supervisor else 0
                                c[19]=0xaabbcc00|((ccr>>4)&1);c[29]=0x100
                                flags=0x202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                                pc=(0,0x123456,0xfffffffe)[delta+1]
                                budget=16+(o.cost[3] if destination&1 else 0)+delta
                                o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                                o.put(0x572a90,0x4b31f0);o.reads={0x10c:vector_target}
                                o.u.mem_write(DATA,bytes(65536));address=stack&0xffffff;at=RAM+0x18000
                                pointer=(at-address)&0xffffffff if direct else 0
                                o.put(DATA+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                                o.u.mem_write(at,struct.pack('<HH',destination>>16,destination&65535))
                                o.bus_value=destination;o.bus_context=[0]*33
                                o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags},
                                      stops=stops+(0x462c89,))
                                p=portable.cpu(5,c,pc,flags,budget,opcode,vector_target,costs=o.cost,entry=entry,
                                    bus_value=destination,bus_address=stack,bus_direct=direct,bus_width=4)
                                key=(hex(stack),hex(destination),ccr,supervisor,direct,hex(vector_target),delta)
                                expected=o.get(CTX,33)
                                boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops else 2
                                assert p['context']==expected,(key,'context',p['context'],expected)
                                assert p['events']==o.events and p['bus_context']==o.bus_context,(key,'events',p,o.events)
                                assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                                assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                                assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                                if boundary==3:
                                    assert p['fault']==[3,0x462c89,3,(destination-2)&0xffffffff,vector_target,p['cycles'],flags]
                                    odd+=1
                                else:assert p['fault']==[0]*7
                                cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=1,
                targets=[f'{entry:08x}'],odd_vector_prefix_cases=odd,
                limits=['RTS only. Synthetic direct/callback stack, vector and rebind; not full execution or audio qualification.'])
