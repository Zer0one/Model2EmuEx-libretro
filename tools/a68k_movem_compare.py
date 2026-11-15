#!/usr/bin/env python3
"""Original MOVEM ordering, mask publication, address writeback and cycles."""
import collections
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, RAM, DATA, READ, WRITE, CALL
from a68k_restore_compare import ScriptOracle
from a68k_memory_compare import address_model
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_movem(exe,portable):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table));rng=random.Random(0xa684890)
    specs={int(a,16):(int(bits),bool(int(read)),int(cost),mode) for a,bits,read,cost,mode in
           re.findall(r'A68K_MOVEM\((0x[0-9a-f]+), (\d+), (\d+), (\d+), (\w+)\)',
                      (Path(__file__).resolve().parents[1]/'port/a68k/movem_ops.inc').read_text())}
    stops={a:a+o.pe.read(a,next(t for t in targets if t>a)-a).rindex(bytes.fromhex('0fb70c2e')) for a in specs}
    digest=hashlib.sha256();counts=collections.Counter();covered=set()
    masks=(0,0xffff,0xaaaa,0x5555)+tuple(1<<i for i in range(16))
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);bits,read,cost,mode=specs[entry];width=bits//8;base=opcode&7;stop=stops[entry]
        for mask in masks:
            for i,ext in enumerate((0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)):
                for delta in (-1,0,1):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[8+base]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000,0xfff,0xffe)[i]
                    c[17]=(c[17]&0xffffff00)|(0x20 if i&1 else 0)
                    pc=(0,0x123456,0xfffffffe)[i%3];low=(0,0xffff,0x7fff,0x8000)[i%4]
                    # The register-list extension precedes the ordinary EA extension.
                    address=c[8+base] if mode in ('POSTINC','PREDEC') else address_model(c,(pc+2)&0xffffffff,base,width,mode,ext,low)
                    script=[]
                    for bit in range(16):
                        if not mask&(1<<bit):continue
                        reg=15-bit if mode=='PREDEC' else bit
                        if mode=='PREDEC':address=(address-width)&0xffffffff
                        value=(0,0xffffffff,0x8000,0x7fff,0x80000000,0xa5c3e791,1,0x12345678)[(i+bit)%8] if read else c[reg]
                        script.append([(6 if width==2 else 7) if read else (9 if width==2 else 10),address&0xffffff,value])
                        if mode!='PREDEC':address=(address+width)&0xffffffff
                    flags=0xfedc0ac3;budget=cost+len(script)*(4 if width==2 else 8)+delta
                    o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                    o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0);o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                    o.put(0x572a94,0x4b3130,0x4b3100,0x4b30c0)
                    o.u.mem_write(RAM+0x1000,struct.pack('<3H',mask,ext,low))
                    o.script=script;o.cursor=0;o.contexts=[]
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=(stop,))
                    p=portable.cpu(8,c,pc,flags,budget,opcode,costs=o.cost,entry=entry,
                                   extension=mask,extension2=ext,extension3=low,script=script)
                    key=(hex(opcode),hex(mask),i,delta);expected=o.get(CTX,33);boundary=1 if o.stop==stop else 2
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert o.cursor==len(script) and p['events']==o.events,(key,'events')
                    assert p['script_context']==o.contexts,(key,'callback contexts',p['script_context'],o.contexts)
                    assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                    assert p['pc']==(expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)),(key,'pc')
                    assert p['flags']==flags and p['fault']==[0]*7,(key,'flags/fault')
                    counts[f'MOVEM_{bits}_{"READ" if read else "WRITE"}_{mode}']+=1
                    digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                limits=['All MOVEM encodings; empty/full/alternating masks and each of the 16 individual registers.',
                        'Original bus wrappers with scripted callbacks and per-transaction contexts; not exhaustive mask combinations, direct-map aliasing or arbitrary callback mutation.'])
