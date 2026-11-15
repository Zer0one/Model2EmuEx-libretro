#!/usr/bin/env python3
"""Original CMPM source/destination postincrements and callback-visible state."""
import collections
import hashlib
import json
import random
import struct
from a68k_boundary_compare import CTX, SP, STOP, DATA, CALL
from a68k_restore_compare import ScriptOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_cmpm(exe,portable):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa68b108)
    specs={0x4851c8:(8,0x485223),0x485230:(8,0x48528a),0x485298:(16,0x4852f6),
           0x485304:(32,0x485361),0x48536c:(8,0x4853c6),0x4853d4:(8,0x48542d)}
    digest=hashlib.sha256();counts=collections.Counter();covered=set()
    for entry,(bits,stop) in specs.items():
        assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
        for opcode,target in enumerate(table):
            if target!=entry:continue
            covered.add(opcode);src=opcode&7;dst=(opcode>>9)&7;width=bits//8
            maximum=(1<<bits)-1;sign=1<<(bits-1)
            values=(0,1,maximum,sign,sign-1,sign+1,maximum-1,0x55&maximum)
            for i in range(16):
                for delta in (-1,0,1):
                    for dirty in (False,True):
                        c=[rng.getrandbits(32) for _ in range(33)]
                        c[8+src]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000,0xfff,0xffe)[i%8]
                        if dst!=src:c[8+dst]=(c[8+src]+(0 if i&1 else 0x2000))&0xffffffff
                        c[17]=(c[17]&0xffffff00)|(0x20 if i&1 else 0)
                        source=c[8+src];destination=(c[8+dst]+((2 if width==1 and src==7 else width) if src==dst else 0))&0xffffffff
                        right=values[i%8];left=values[(i*3+i//8)%8]
                        if dirty and bits<32:right|=0xaabbccdd&~maximum;left|=0x5a5a5a5a&~maximum
                        kind={1:5,2:6,4:7}[width]
                        script=[[kind,source&0xffffff,right],[kind,destination&0xffffff,left]]
                        flags=0xfedc0ac3 if dirty else 0;host=0x602 if dirty else 0x202
                        pc=(0,0x123456,0xfffffffe)[i%3];cost=20 if bits==32 else 12;budget=cost+delta
                        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                        o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                        o.script=script;o.cursor=0;o.contexts=[]
                        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                    UC_X86_REG_EFLAGS:host},stops=(stop,))
                        p=portable.cpu(8,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,host_flags=host,script=script)
                        key=(hex(opcode),i,delta,dirty);expected=o.get(CTX,33);boundary=1 if o.stop==stop else 2
                        assert p['context']==expected,(key,'context',p['context'],expected)
                        assert o.cursor==len(script) and p['events']==o.events,(key,'events')
                        assert p['script_context']==o.contexts,(key,'callback contexts')
                        assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                        assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                        assert p['flags']==(expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)),(key,'flags')
                        assert p['fault']==[0]*7
                        counts[f'CMPM_{bits}']+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    assert len(covered)==192
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in specs],
                limits=['All CMPM encodings, including identical address registers, A7 byte steps and wrapping addresses.',
                        'Original bus wrappers with scripted callbacks; direct maps and arbitrary callback mutation remain separate.'])
