#!/usr/bin/env python3
"""Original SR/CCR moves and logical immediates, privilege and feature gates."""
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


def compare_status(exe,portable,immediate=False):
    o=ScriptOracle(exe);table=decode_dispatch(o.pe)[3];targets=sorted(set(table));rng=random.Random(0xa68003c+immediate)
    text=(Path(__file__).resolve().parents[1]/'port/a68k/status_ops.inc').read_text()
    if immediate:
        specs={int(a,16):(op,int(full),20,'IMMEDIATE') for a,op,full in re.findall(r'A68K_STATUS_LOGIC\((0x[0-9a-f]+), (\w+), (\d+)\)',text)}
    else:
        specs={int(a,16):(op,op in ('TO_SR','FROM_SR'),int(cost),mode) for a,op,cost,mode in re.findall(r'A68K_STATUS_MOVE\((0x[0-9a-f]+), (\w+), (\d+), (\w+)\)',text)}
    stops={}
    for entry in specs:
        body=o.pe.read(entry,next(t for t in targets if t>entry)-entry)
        stops[entry]=tuple(entry+m.start() for m in re.finditer(bytes.fromhex('0fb70c2e'),body))+(0x462b48,0x48b5a8)
    digest=hashlib.sha256();counts=collections.Counter();covered=set();odd=0
    for opcode,entry in enumerate(table):
        if entry not in specs:continue
        covered.add(opcode);op,full,cost,mode=specs[entry]
        for ccr in range(32):
            for incoming in (range(32) if immediate else (ccr,)):
                for scenario in range(8):
                    for delta in (-1,0,100):
                        c=[rng.getrandbits(32) for _ in range(33)]
                        old_high=(0,7,0x20,0x27,0xa0,0xa7,0,0x20)[scenario]
                        new_high=(0,0xffff,0x2000,0x2700,0x8000,0x0700,0xff00,0xa700)[scenario]
                        c[17]=(c[17]&0xffffff00)|old_high;c[19]=(c[19]&~1)|((ccr>>4)&1)
                        c[21]=(c[21]&0xffffff00)|(0,3,7,3,0,7,7,3)[scenario]|0x78
                        c[31]=0 if scenario&1 else 0x87654321
                        c[15]=0x123fff;c[16]=0x9000;c[28]=0x123000;c[29]=0x100
                        c[8+(opcode&7)]=(0,1,0xfffffe,0xffffffff,0x123fff,0x123000,0xfff,0xffe)[scenario]
                        flags=0xfedc0202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                        flags=(flags&~0x8c1)|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
                        value=(new_high&0xff00)|incoming
                        if not immediate:c[opcode&7]=(c[opcode&7]&0xffff0000)|value
                        ext=(0,1,0x7fff,0x8000,0xffff,0x7800,0xf8ff,0x87ff)[scenario];low=0x8001
                        if immediate or mode=='IMMEDIATE':ext=value
                        pc=(0,0x123456,0xfffffffe)[scenario%3]
                        vector_target=0x8001 if scenario in (5,6) else 0xab008000
                        budget=cost+delta;ack=-1 if scenario&1 else 31
                        script=[]
                        privilege=(full and immediate or op=='TO_SR') and not(old_high&0x20)
                        illegal=op=='FROM_CCR' and not c[31]
                        if not immediate and not privilege and not illegal and mode not in ('REGISTER','IMMEDIATE'):
                            address=address_model(c,pc,opcode&7,2,mode,ext,low)
                            v=((old_high<<8)|ccr) if op=='FROM_SR' else ccr if op=='FROM_CCR' else 0xaabb0000|value
                            script=[[9 if op.startswith('FROM_') else 6,address,v]]
                        o.setup_exception(c,budget);o.ack=ack;o.put(SP+4,*([0]*7),STOP)
                        o.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0);o.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
                        if script and script[0][0]==9:o.put(0x572a98,0x4b3100)
                        o.reads={0x100+v*4:vector_target for v in range(256)}
                        o.u.mem_write(RAM+0x1000,struct.pack('<2H',ext,low))
                        o.put(0x10ed9b8,0,0);o.script=script;o.cursor=0;o.contexts=[]
                        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags,
                                    UC_X86_REG_EBP:(RAM+0x1000-pc-2)&0xffffffff},stops=stops[entry]+(0x462c89,))
                        p=portable.cpu(8,c,pc,flags,budget,opcode,vector_target,ack=ack,costs=o.cost,entry=entry,
                                       extension=ext,extension2=low,script=script)
                        key=(hex(opcode),ccr,incoming,scenario,delta);expected=o.get(CTX,33)
                        boundary=3 if o.stop==0x462c89 else 1 if o.stop in stops[entry] else 2
                        assert p['context']==expected,(key,'context',p['context'],expected)
                        assert o.cursor==len(script) and p['events']==o.events,(key,'events',p['events'],o.events)
                        assert p['script_context']==o.contexts,(key,'callback contexts')
                        assert p['cycles']==o.get(0x10ed9b0)[0] and p['boundary']==boundary,(key,'boundary')
                        livepc=expected[20] if boundary==2 else o.u.reg_read(UC_X86_REG_ESI)
                        liveflags=expected[18] if boundary==2 else o.u.reg_read(UC_X86_REG_EDX)
                        assert p['pc']==livepc and p['flags']==liveflags,(key,'live',p,livepc,liveflags)
                        assert [p['illegal_opcode'],p['illegal_pc']]==o.get(0x10ed9b8,2),(key,'illegal metadata')
                        if boundary==3:
                            vector=(o.events[-1][1]-0x100)//4
                            exception_pc=next(e[2] for e in reversed(o.events) if e[0]=='write32')
                            assert p['fault']==[3,0x462c89,vector,exception_pc,vector_target,p['cycles'],liveflags]
                            odd+=1
                        else:assert p['fault']==[0]*7
                        counts[op+('_SR' if full else '_CCR') if immediate else op+'_'+mode]+=1
                        digest.update(json.dumps([key,p],sort_keys=True).encode())
    return dict(cases=sum(counts.values()),groups=dict(counts),mismatches=0,
                result_sha256=digest.hexdigest(),covered_entries=len(covered),targets=[f'{t:08x}' for t in sorted(specs)],
                odd_vector_prefix_cases=odd,limits=[
                    'All status-move encodings and original CCR-export feature gate.' if not immediate else 'All three logical operators and all 32 by 32 CCR input combinations.',
                    'Privilege, stack switching, IRQ re-entry and callback contexts; no full CPU or sound-board qualification.'])
