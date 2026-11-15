#!/usr/bin/env python3
"""Compare all original MOVEP encodings and each spaced byte transaction."""
import collections
import hashlib
import json
import random
import struct
from a68k_boundary_compare import CTX, SP, STOP, RAM, DATA, WRITE, CALL
from a68k_restore_compare import ScriptOracle
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_movep(exe,portable):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3];rng=random.Random(0xa680108)
    specs={0x46f84c:(2,False,0x46f8ac),0x46f8b8:(4,False,0x46f946),
           0x46f954:(2,True,0x46f9b7),0x46f9c4:(4,True,0x46fa5b)}
    digest=hashlib.sha256();counts=collections.Counter();covered=set()
    for entry,(size,write,stop) in specs.items():
        assert o.pe.read(stop,4)==bytes.fromhex('0fb70c2e')
        for opcode,target in enumerate(table):
            if target!=entry:continue
            covered.add(opcode)
            for i,ext in enumerate((0,1,0x7fff,0x8000,0xffff,2,0x1234,0xfffe)):
                for delta in (-1,0,1):
                    for dirty in (False,True):
                        c=[rng.getrandbits(32) for _ in range(33)]
                        c[8+(opcode&7)]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000,0xfff,0xffe)[i]
                        c[17]=(c[17]&0xffffff00)|(0x20 if i&1 else 0)
                        reg=(opcode>>9)&7
                        c[reg]=(0,0xffffffff,0x80000000,0x7fffffff,0x12345678,0x80ff01fe,1,0xa5c3e791)[i]
                        address=(c[8+(opcode&7)]+(ext-65536 if ext&32768 else ext))&0xffffffff
                        value=c[reg];script=[]
                        for n in range(size):
                            if write:
                                # Native rotates the complete Dn into EDX; high bits reach the callback.
                                rotation=((3 if size==2 else 1)+n)%4*8
                                v=((value<<rotation)|(value>>(32-rotation)))&0xffffffff if rotation else value
                            else:v=(0xaabbcc00 if dirty else 0)|((value>>((size-1-n)*8))&255)
                            script.append([8 if write else 5,(address+2*n)&0xffffff,v])
                        flags=0xfedc0ac3 if dirty else 0;pc=(0,0x123456,0xfffffffe)[i%3]
                        cost=28 if size==2 else 36;budget=cost+delta
                        o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                        o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
                        o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                        o.u.mem_write(RAM+0x1000,struct.pack('<H',ext))
                        o.script=script;o.cursor=0;o.contexts=[]
                        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                    UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stop,))
                        p=portable.cpu(8,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,extension=ext,script=script)
                        key=(hex(opcode),i,delta,dirty);expected=o.get(CTX,33);boundary=1 if o.stop==stop else 2
                        assert p['context']==expected,(key,'context',p['context'],expected)
                        assert o.cursor==len(script) and p['events']==o.events,(key,'events')
                        assert p['script_context']==o.contexts,(key,'callback contexts')
                        assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                        assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                        assert p['flags']==flags and p['fault']==[0]*7,(key,'flags/fault')
                        counts[f'MOVEP_{size*8}_{"WRITE" if write else "READ"}']+=1
                        digest.update(json.dumps([key,p],sort_keys=True).encode())
    assert len(covered)==256
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in specs],
                limits=['All MOVEP encodings through actual original byte wrappers with scripted callbacks.',
                        'Callback value high bits, transaction order and published contexts checked; direct maps and arbitrary callback mutation are separate.'])
