#!/usr/bin/env python3
"""Original RTR/RTE stack transactions, restoration and live IRQ re-entry.

Uses actual native DATA wrappers with scripted callbacks. The transaction
fixture checks every callback-observed CPU context; it does not stand in for
full sound-board memory, direct bus aliasing or callbacks that mutate CPU state.
"""
import collections
import hashlib
import json
import random
import struct
from a68k_boundary_compare import CTX, SP, STOP, DATA, READ, WRITE, CALL
from a68k_return_compare import ReturnOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class ScriptOracle(ReturnOracle):
    def __init__(self,exe):
        super().__init__(exe)
        # These fixtures never alter descriptors. Install their callback maps
        # once instead of rewriting identical 64 KiB tables for every case.
        mapping=struct.pack('<4I',0,CALL+80,CALL+96,CALL+112)*4096
        self.u.mem_write(DATA,mapping);self.u.mem_write(READ,mapping)
        self.u.mem_write(WRITE,struct.pack('<4I',0,CALL+128,CALL+144,CALL+160)*4096)

    def hook(self,u,at,size,data):
        if CALL+80<=at<=CALL+160 and at%16==CALL%16:
            kind=(at-CALL)//16;address=u.reg_read(UC_X86_REG_ECX)
            item=self.script[self.cursor];self.cursor+=1
            assert item[:2]==[kind,address],(self.cursor,item,kind,address)
            self.contexts.append(self.get(CTX,33))
            value=u.reg_read(UC_X86_REG_EDX) if kind>=8 else 0
            self.events.append(['bus',kind,address,value])
            if kind>=8:assert value==item[2];self.ret()
            else:self.ret(item[2])
            return
        super().hook(u,at,size,data)


def compare_restore(exe,portable):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3]
    lookup=list(struct.unpack('<32I',o.pe.read(0x528f70,128)))
    assert lookup==[(v&1)|((v&12)<<4)|((v&2)<<10)|((v&16)<<4) for v in range(32)]
    rng=random.Random(0xa68e77);digest=hashlib.sha256();counts=collections.Counter();odd=0
    specs=((0x485c40,0x4e77,(0x485caf,0x485ced)),
           (0x487008,0x4e73,(0x4870b2,0x4870fd,0x48712c,0x462b48)))
    for entry,opcode,stops in specs:
        assert [i for i,t in enumerate(table) if t==entry]==[opcode]
        for stop in stops:assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
        for ccr in range(32):
            for si,stack in enumerate((0,1,0xfffffe,0xffffffff,0x123fff,0x123000)):
                for di,destination in enumerate((0,0x7001,0xab007000,0xffffffff)):
                    for state in range(8):
                        for delta in (-1,0,100):
                            supervisor=bool(state&4);high=(0,7,0x20,0xa7)[state&3]
                            sr=0xabcd0000|(high<<8)|ccr
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[15]=stack;c[16]=0x9000;c[28]=0x123000;c[29]=0x100
                            c[17]=(c[17]&0xffffff00)|(0x20 if supervisor else 0)
                            c[21]=(c[21]&0xffffff00)|(0,3,7)[si%3]|0xf8
                            pc=(0,0x123456,0xfffffffe)[si%3];flags=0xfac3
                            vector_target=0x8001 if di==3 else 0xab008000
                            budget=20+delta;ack=-1 if state&1 else 31
                            o.setup_exception(c,budget);o.ack=ack;o.put(SP+4,*([0]*7),STOP)
                            o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                            # All pages use callbacks. Actual original wrappers still mask addresses.
                            o.reads={0x100+v*4:vector_target for v in range(256)}
                            script=[] if opcode==0x4e73 and not supervisor else [
                                [6,stack&0xffffff,sr],[7,(stack+2)&0xffffff,destination]]
                            o.script=script;o.cursor=0;o.contexts=[]
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags},
                                  stops=stops+(0x462c89,))
                            p=portable.cpu(8,c,pc,flags,budget,opcode,vector_target,ack=ack,
                                           costs=o.cost,entry=entry,script=script)
                            key=(hex(opcode),ccr,hex(stack),hex(destination),state,delta)
                            expected=o.get(CTX,33)
                            boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops else 2
                            assert o.cursor==len(script)
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert p['events']==o.events,(key,'events',p['events'],o.events)
                            assert p['script_context']==o.contexts,(key,'callback contexts')
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary',p)
                            livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                            liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                            assert p['pc']==livepc and p['flags']==liveflags,(key,'live',p,livepc,liveflags)
                            if boundary==3:
                                vector=(o.events[-1][1]-0x100)//4
                                exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
                                assert p['fault']==[3,0x462c89,vector,exception_pc,vector_target,p['cycles'],liveflags]
                                odd+=1
                            else:assert p['fault']==[0]*7
                            counts['RTE' if opcode==0x4e73 else 'RTR']+=1
                            digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=2,targets=[f'{s[0]:08x}' for s in specs],
                odd_vector_prefix_cases=odd,limits=[
                    'Scripted stack callbacks through original bus wrappers, full callback contexts and live IRQ re-entry.',
                    'No direct stack mapping, arbitrary callback mutation, full CPU execution or audio claim.'])
