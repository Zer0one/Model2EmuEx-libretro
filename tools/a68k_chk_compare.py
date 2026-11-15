#!/usr/bin/env python3
"""Original register/immediate CHK bounds, native flag masks and vector 6."""
import hashlib
import json
import random
import struct
from a68k_boundary_compare import Oracle, CTX, SP, STOP, RAM
from a68k_inventory import decode_dispatch
from a68k_return_compare import ReturnOracle
from unicorn.x86_const import *


def compare_chk(exe,portable):
    o=Oracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa684180)
    specs={0x484af0:(False,(0x484b2d,0x484b5a)),0x485084:(True,(0x4850be,0x4850ee))}
    digest=hashlib.sha256();cases=odd=0;covered=set()
    values=(0,1,2,0x7fff,0x8000,0x8001,0xfffe,0xffff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);immediate,stops=specs[entry]
        for left in values:
            for bound in values:
                for delta in (-1,0,1):
                    for supervisor in (False,True):
                        for target in (0xab008000,0x8001):
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[(opcode>>9)&7]=(c[(opcode>>9)&7]&0xffff0000)|left
                            if not immediate:c[opcode&7]=(c[opcode&7]&0xffff0000)|bound
                            actual=c[(opcode>>9)&7]&65535
                            fails=bool(actual&0x8000) or bool(bound&0x8000) or actual>bound
                            c[15]=0x123fff;c[16]=0x9000;c[29]=0x100
                            c[17]=(c[17]&0xffffff00)|(0x20 if supervisor else 0)
                            flags=rng.getrandbits(32);pc=(0,0x123456,0xfffffffe)[delta+1]
                            budget=10+(o.cost[6] if fails else 0)+delta
                            o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                            o.reads={0x118:target};o.u.mem_write(RAM+0x1000,struct.pack('<H',bound))
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops+(0x462c89,))
                            p=portable.cpu(4,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry,extension=bound)
                            key=(hex(opcode),left,bound,delta,supervisor,hex(target));expected=o.get(CTX,33)
                            boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops else 2
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert p['events']==o.events,(key,'events')
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                            livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                            liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                            assert p['pc']==livepc and p['flags']==liveflags,(key,'live')
                            if boundary==3:
                                assert p['fault']==[3,0x462c89,6,(pc+(4 if immediate else 2))&0xffffffff,target,p['cycles'],liveflags];odd+=1
                            else:assert p['fault']==[0]*7
                            cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in specs],odd_vector_prefix_cases=odd,
                limits=['Register and immediate CHK only; memory CHK depends on native read-wrapper EDX scratch.',
                        'Native upper-bound failure keeps only flag bits 0..6; negative operand sets bit 7 without clearing high bits.'])


class ChkMemoryOracle(ReturnOracle):
    def hook(self,u,at,size,data):
        from a68k_boundary_compare import CALL
        if at==CALL+96:
            # Explicitly varied callback return scratch, not guest flags.
            u.reg_write(UC_X86_REG_EDX,self.bus_edx)
        super().hook(u,at,size,data)


def compare_chk_memory(exe,portable):
    import re
    from pathlib import Path
    from a68k_boundary_compare import READ, DATA, CALL
    from a68k_memory_compare import address_model
    o=ChkMemoryOracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa68c4b)
    text=(Path(__file__).resolve().parents[1]/'port/a68k/chk_ops.inc').read_text()
    specs={int(t,16):(mode,int(cost)) for t,mode,cost in
           re.findall(r'A68K_CHK\((0x[0-9a-f]+), (\w+), (\d+)\)',text)
           if mode not in ('REGISTER','IMMEDIATE')}
    targets=sorted(set(table));stops={}
    for entry in specs:
        body=o.pe.read(entry,next(t for t in targets if t>entry)-entry)
        stops[entry]=tuple(entry+m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')),body))
        assert len(stops[entry])==2
    digest=hashlib.sha256();cases=odd=0;covered=set()
    values=(0,1,2,0x7fff,0x8000,0x8001,0xfffe,0xffff)
    extensions=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);mode,cost=specs[entry]
        for i,left in enumerate(values):
            for j,bound in enumerate(values):
                for direct in (False,True):
                    for delta in (-1,0,1):
                        for target in (0xab008000,0x8001):
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[(opcode>>9)&7]=(c[(opcode>>9)&7]&0xffff0000)|left
                            c[15]=0x123fff;c[16]=0x9000;c[29]=0x100
                            c[8+(opcode&7)]=(0,0xffffff,0x123fff,0x123000)[i%4]
                            c[17]=(c[17]&0xffffff00)|(0x20 if j&1 else 0)
                            flags=rng.getrandbits(32);pc=(0,0x123456,0xfffffffe)[delta+1]
                            ext=extensions[i];low=extensions[j]
                            address=address_model(c,pc,opcode&7,2,mode,ext,low)
                            fails=bool(left&0x8000) or bool(bound&0x8000) or left>bound
                            budget=cost+(o.cost[6] if fails else 0)+delta
                            o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                            o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                            o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                            o.reads={0x118:target};o.bus_context=[0]*33
                            # Move the backing allocation too: the direct EDX token varies.
                            at=RAM+0x18000+((i+j)*2)
                            pointer=(at-address)&0xffffffff if direct else 0
                            for base in (READ,DATA):o.put(base+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                            o.u.mem_write(at,struct.pack('<H',bound))
                            o.bus_value=0xa5c30000|bound;o.bus_edx=(0,0xfac3,0xdeadbeef)[delta+1]
                            o.u.mem_write(RAM+0x1000,struct.pack('<HH',ext,low))
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                        UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops[entry]+(0x462c89,))
                            p=portable.cpu(10,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry,
                                extension=ext,extension2=low,bus_value=o.bus_value,bus_address=address,
                                bus_direct=direct,bus_width=2,bus_edx=pointer if direct else o.bus_edx)
                            key=(hex(opcode),left,bound,direct,delta,hex(target));expected=o.get(CTX,33)
                            boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert p['events']==o.events and p['bus_context']==o.bus_context,(key,'bus',p,o.events,o.bus_context)
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                            livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                            liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                            assert p['pc']==livepc and p['flags']==liveflags,(key,'live',p,liveflags)
                            if boundary==3:
                                exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
                                assert p['fault']==[3,0x462c89,6,exception_pc,target,p['cycles'],liveflags];odd+=1
                            else:assert p['fault']==[0]*7
                            cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],odd_vector_prefix_cases=odd,
                limits=['All memory CHK encodings, actual original read wrappers, varied direct bases and callback EDX.',
                        'Original sound-board allocation tokens and device callback EDX still require integration; these are synthetic bindings.',
                        'No full CPU execution, game reachability, sound or frontend qualification.'])
