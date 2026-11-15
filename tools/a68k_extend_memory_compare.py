#!/usr/bin/env python3
"""Original memory ADDX/SUBX and sticky Z from the second read's EDX."""
import hashlib
import json
import random
import re
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, CALL
from a68k_restore_compare import ScriptOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class ExtendOracle(ScriptOracle):
    def hook(self,u,at,size,data):
        if CALL+80<=at<=CALL+112 and at%16==CALL%16:
            u.reg_write(UC_X86_REG_EDX,self.script_edx[self.cursor])
        elif CALL+128<=at<=CALL+160 and at%16==CALL%16:
            self.script[self.cursor][2]=u.reg_read(UC_X86_REG_EDX)
        super().hook(u,at,size,data)


def compare_extend_memory(exe,portable):
    o=ExtendOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    rng=random.Random(0xa68adc);digest=hashlib.sha256();cases=0;covered=set()
    text=(Path(__file__).resolve().parents[1]/'port/a68k/extend_memory_ops.inc').read_text()
    specs={int(t,16):(op,int(bits),int(cost)) for t,op,bits,cost in
           re.findall(r'A68K_EXTEND_MEMORY\((0x[0-9a-f]+), (\w+), (\d+), (\d+)\)',text)}
    stops={t:t+o.pe.read(t,next(v for v in targets if v>t)-t).rindex(bytes.fromhex('0fb70c2e')) for t in specs}
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,bits,cost=specs[entry];width=bits//8;src=opcode&7;dst=(opcode>>9)&7
        mask=(1<<bits)-1;sign=1<<(bits-1)
        pairs=((0,0),(0,1),(1,mask),(sign-1,1),(sign,mask),(mask,1),(mask,mask),(sign,sign),
               (0x7f,1),(0x80,0xff),(0x7fff,1),(0x8000,0xffff))
        for i,(left,right) in enumerate(pairs):
            for x in (0,1):
                for z in (0,1):
                    for delta in (-1,0,1):
                        c=[rng.getrandbits(32) for _ in range(33)]
                        c[8+src]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000)[i%6]
                        if src!=dst:c[8+dst]=(c[8+src]+(0 if i&1 else 0x1000))&0xffffffff
                        c[19]=(c[19]&~1)|x
                        source=(c[8+src]-(2 if width==1 and src==7 else width))&0xffffff
                        destination=(c[8+dst]-(2 if width==1 and dst==7 else width)-
                                     ((2 if width==1 and src==7 else width) if src==dst else 0))&0xffffff
                        kind={1:5,2:6,4:7}[width]
                        left=(0xa5c36900&~mask)|(left&mask);right=(0xbadcfe00&~mask)|(right&mask)
                        script=[[kind,source,right],[kind,destination,left],[kind+3,destination,0]]
                        edx=(rng.getrandbits(32)&~0x40)|(0x40 if z else 0)
                        script_edx=[edx^0x40,edx,0]
                        # Both incoming guest Z and first-read Z oppose the second-read Z.
                        flags=(rng.getrandbits(32)&~0x40)|(0 if z else 0x40)
                        host=0x202|(0x400 if i&1 else 0)
                        pc=(0,0x123456,0xfffffffe)[delta+1];budget=cost+delta
                        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                        o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0);o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                        o.script=script;o.script_edx=script_edx;o.cursor=0;o.contexts=[]
                        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                    UC_X86_REG_EFLAGS:host},stops=(stops[entry],))
                        p=portable.cpu(12,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,
                                       host_flags=host,script=script,script_edx=script_edx)
                        key=(hex(opcode),i,x,z,delta);expected=o.get(CTX,33);exited=o.stop is None
                        assert p['context']==expected,(key,'context',p['context'],expected)
                        assert o.cursor==3 and p['events']==o.events,(key,'events')
                        assert p['script_context']==o.contexts,(key,'callback contexts',p['script_context'],o.contexts)
                        assert p['flags']==(expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                        assert p['pc']==(expected[20] if exited else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                        assert p['cycles']==delta&0xffffffff and p['boundary']==(2 if exited else 1),(key,'boundary')
                        assert p['fault']==[0]*7
                        cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],limits=[
                    'All memory ADDX/SUBX encodings, paired predecrement callbacks, shared An/A7, X, second-read sticky Z and cycle boundaries.',
                    'Synthetic callback EDX deliberately differs from incoming flags and first-read EDX.',
                    'Direct paired mappings, arbitrary callback mutation, real board execution and audio remain separate.'])
