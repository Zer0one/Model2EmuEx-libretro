#!/usr/bin/env python3
"""Native BCD read/read/write order, predecrements and full callback values."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, DATA, WRITE, CALL
from a68k_restore_compare import ScriptOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


class BcdOracle(ScriptOracle):
    def hook(self,u,at,size,data):
        # Acquire the original write argument, then require the portable
        # transaction to match it exactly; no duplicate decimal algorithm.
        if at==CALL+128:self.script[self.cursor][2]=u.reg_read(UC_X86_REG_EDX)
        super().hook(u,at,size,data)


def compare_bcd_memory(exe,portable):
    o=BcdOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table));rng=random.Random(0xa688108)
    specs={int(a,16):int(sub) for a,sub in re.findall(r'A68K_BCD_MEMORY\((0x[0-9a-f]+), (\d+)\)',
                   (Path(__file__).resolve().parents[1]/'port/a68k/bcd_memory_ops.inc').read_text())}
    stops={a:a+o.pe.read(a,next(t for t in targets if t>a)-a).rindex(bytes.fromhex('0fb70c2e')) for a in specs}
    digest=hashlib.sha256();counts=collections.Counter();covered=set()
    values=(0,1,9,10,15,16,25,0x90,0x99,0x9a,0xa0,0xff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);src=opcode&7;dst=(opcode>>9)&7;stop=stops[entry]
        for i,left in enumerate(values):
            for right in values:
                for x in (0,1):
                    for z in (0,1):
                        for delta in (-1,0,1):
                            c=[rng.getrandbits(32) for _ in range(33)]
                            c[8+src]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000)[i%6]
                            if src!=dst:c[8+dst]=(c[8+src]+(0 if i&1 else 0x1000))&0xffffffff
                            c[19]=(c[19]&~1)|x;c[17]=(c[17]&~0x20)|(0x20 if z else 0)
                            source=(c[8+src]-(2 if src==7 else 1))&0xffffff
                            destination=(c[8+dst]-(2 if dst==7 else 1)-((2 if src==7 else 1) if src==dst else 0))&0xffffff
                            script=[[5,source,0xaabbcc00|right],[5,destination,0x12345600|left],[8,destination,0]]
                            flags=(rng.getrandbits(32)&~0x40)|(0x40 if z else 0)
                            pc=(0,0x123456,0xfffffffe)[delta+1];budget=18+delta
                            o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                            o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0);o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                            o.script=script;o.cursor=0;o.contexts=[]
                            o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags},stops=(stop,))
                            p=portable.cpu(8,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,script=script)
                            key=(hex(opcode),left,right,x,z,delta);expected=o.get(CTX,33);boundary=1 if o.stop==stop else 2
                            assert p['context']==expected,(key,'context',p['context'],expected)
                            assert o.cursor==3 and p['events']==o.events,(key,'events')
                            assert p['script_context']==o.contexts,(key,'callback contexts')
                            assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                            assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                            assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                            assert p['fault']==[0]*7
                            counts['SBCD' if specs[entry] else 'ABCD']+=1
                            digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=['All memory ABCD/SBCD encodings, A7 and shared An, sticky-Z/X combinations and valid/invalid BCD samples.',
                        'Byte-pair exhaustive arithmetic remains in the shared register suite; direct-map and arbitrary callback mutation are separate.'])
