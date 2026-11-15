#!/usr/bin/env python3
"""Original memory DIV, read scratch on vector 5 and native host IDIV fault."""
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from a68k_boundary_compare import CTX, SP, STOP, RAM, READ, DATA, CALL
from a68k_chk_compare import ChkMemoryOracle
from a68k_memory_compare import address_model
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_divide_memory(exe,portable):
    o=ChkMemoryOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table))
    rng=random.Random(0xa68d1f2);digest=hashlib.sha256();cases=odd=faults=guards=0;covered=set()
    text=(Path(__file__).resolve().parents[1]/'port/a68k/divide_memory_ops.inc').read_text()
    specs={int(t,16):(int(sign),int(cost),mode,int(fault,0)) for t,sign,cost,mode,fault in
           re.findall(r'A68K_DIVIDE_MEMORY\((0x[0-9a-f]+), (\d+), (\d+), (\w+), (0x[0-9a-f]+|0)\)',text)}
    stops={}
    for entry in specs:
        body=o.pe.read(entry,next(t for t in targets if t>entry)-entry)
        stops[entry]=tuple(entry+m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')),body))
        assert len(stops[entry])==3
    pairs=((0,0),(1,0),(0x80000000,0),(0xffffffff,0),(0,1),(1,2),(0x7fff,1),(0x8000,1),
           (0xffff,1),(0x10000,1),(0x7fffffff,0xffff),(0x80000000,0xffff),(0x80000001,0xffff),
           (0xffff8000,0xffff),(0xfffffffe,3),(0xffffffff,0x8000),(0x80000000,1),(0x7fffffff,2),
           (1,0xfffe),(2,0x7fff))
    extensions=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);signed,cost,mode,idiv=specs[entry]
        for i,(dividend,divisor) in enumerate(pairs):
            for direct in (False,True):
                for delta in (-1,0,1):
                    c=[rng.getrandbits(32) for _ in range(33)]
                    c[(opcode>>9)&7]=dividend;c[15]=0x8000;c[16]=0x9000;c[29]=0x100
                    c[8+(opcode&7)]=(0,0xffffff,0x123fff,0x123000)[i%4]
                    c[17]=0x20 if i&1 else 0;c[19]=0xaabbcc00|(i&1)
                    pc=(0,0x123456,0xfffffffe)[delta+1];flags=rng.getrandbits(32)
                    host=0x202|(0x400 if i&1 else 0);ext=extensions[i%8];low=extensions[(i+3)%8]
                    address=address_model(c,pc,opcode&7,2,mode,ext,low)
                    budget=(cost if divisor else cost-(112 if signed else 95)+o.cost[5])+delta
                    target=0x7000+(i+delta)%2
                    o.setup_exception(c,budget);o.put(SP+4,*([0]*7),STOP)
                    o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0);o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                    o.reads={0x114:target};o.bus_context=[0]*33
                    at=RAM+0x18000+2*i;pointer=(at-address)&0xffffffff if direct else 0
                    for base in (READ,DATA):o.put(base+(address>>12)*16,pointer,CALL+80,CALL+96,CALL+112)
                    o.u.mem_write(at,struct.pack('<H',divisor));o.u.mem_write(RAM+0x1000,struct.pack('<HH',ext,low))
                    o.bus_value=0xa5c30000|divisor;o.bus_edx=(0,0xfac3,0xdeadbeef)[delta+1]
                    expected_fault=bool(signed and dividend==0x80000000 and divisor==0xffff)
                    # The separate original Windows/Unicorn audit proved #DE.
                    # Compare its exact prefix without reinjecting engine faults.
                    o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                        UC_X86_REG_EFLAGS:host,UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},
                        stops=stops[entry]+(0x462c89,)+((idiv,) if expected_fault else ()))
                    p=portable.cpu(10,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry,host_flags=host,
                        extension=ext,extension2=low,bus_value=o.bus_value,bus_address=address,bus_direct=direct,
                        bus_width=2,bus_edx=pointer if direct else o.bus_edx)
                    key=(hex(opcode),i,direct,delta);expected=o.get(CTX,33)
                    failed=bool(expected_fault and o.stop==idiv);assert failed==expected_fault
                    boundary=6 if failed else 3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
                    assert p['context']==expected,(key,'context',p['context'],expected)
                    assert p['events']==o.events and p['bus_context']==o.bus_context,(key,'bus',p,o.events)
                    assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary',p,boundary)
                    livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                    liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                    assert p['pc']==livepc and p['flags']==liveflags,(key,'live',p,liveflags)
                    if failed:
                        assert p['fault']==[6,idiv,0,pc,0xffffffff,p['cycles'],0xffffffff];faults+=1
                    elif boundary==3:
                        exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
                        assert p['fault']==[3,0x462c89,5,exception_pc,target,p['cycles'],liveflags];odd+=1
                    else:assert p['fault']==[0]*7
                    if failed or boundary==3:
                        assert portable.library.a68k_probe_fault_latch()==14;guards+=14
                    cases+=1;digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=cases,mismatches=0,result_sha256=digest.hexdigest(),covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],odd_vector_prefix_cases=odd,
                host_overflow_prefix_cases=faults,post_fault_retry_guards=guards,limits=[
                    'All memory DIVU/DIVS encodings, direct/callback reads, vector 5, signed/unsigned quotient limits and host IDIV prefix.',
                    'Synthetic memory bindings; original board allocation/callback provenance, full CPU and audio remain separate.',
                    'Existing explicit fault guard is preserved; no guest arithmetic correction or new Windows runtime claim.'])
