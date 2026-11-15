#!/usr/bin/env python3
"""Original A68K opcode-entry/exception-tail qualification and coverage.

Imported by a68k_portable_compare.py so the same built module is used for all
checks. Coverage counts dispatch entries/targets, never total CPU effort.
"""
import collections
import hashlib
import json
import random
import re
from pathlib import Path
from a68k_boundary_compare import Oracle,CTX,CALL,SP,STOP,exception_model
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *

ENTRIES={0x478438:('MOVEQ',0x47845c,None),
         0x48b518:('Line-A',0x48b535,10),
         0x48b540:('Line-F',0x48b55d,11),
         0x48b568:('Illegal',0x48b5a8,4)}


class FlowOracle(Oracle):
    def __init__(self,exe):
        self.targets=None
        super().__init__(exe)

    def hook(self,u,at,size,data):
        if at==CALL and self.targets is not None:
            assert self.targets,'Unexpected extra vector read'
            self.reads[u.reg_read(UC_X86_REG_ECX)]=self.targets.pop(0)
        super().hook(u,at,size,data)


def compare_flow(exe,portable):
    o=FlowOracle(exe);targets=decode_dispatch(o.pe)[3]
    assert o.pe.read(0x4b3360,3)==bytes.fromhex('33c0c3'),'Native illegal stub changed'
    counts=collections.Counter();digest=hashlib.sha256();rng=random.Random(0xa68f10)
    def keep(group,record):
        counts[group]+=1;digest.update(json.dumps(record,sort_keys=True).encode())
    for opcode,entry in enumerate(targets):
        if entry not in ENTRIES:continue
        name,stop,vector=ENTRIES[entry]
        c=[rng.getrandbits(32) for _ in range(33)]
        c[15]=0x8000;c[16]=0x9000;c[17]=(c[17]&0xffffff00)|(0xa7 if opcode&32 else 7)
        ccr=opcode%32;c[19]=(ccr>>4)&1;c[29]=0x100
        flags=0x202|(ccr&1)|((ccr&12)<<4)|((ccr&2)<<10)
        pc=(0,0xfffffffe,0x123456)[opcode%3]
        target=(0,0x7000,0xab007000,0xfffffffe)[opcode%4]
        cost=4 if vector is None else o.cost[vector]
        budget=cost+(opcode%3)-1
        o.setup_exception(c,budget);o.put(0x10ed9b8,0,0)
        if vector is not None:o.reads={0x100+4*vector:target}
        o.put(SP+4,*([0]*7),STOP)
        o.run(entry,{UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags},stops=(stop,))
        p=portable.cpu(4,c,pc,flags,budget,opcode,target,costs=o.cost,entry=entry)
        assert p['fault']==[0]*7 and portable.library.a68k_probe_fault_latch()==0
        assert p['context']==o.get(CTX,33),(name,hex(opcode),'context')
        assert p['events']==o.events and p['cycles']==o.get(0x10ed9b0)[0]
        assert p['boundary']==(1 if o.stop==stop else 2)
        assert [p['illegal_opcode'],p['illegal_pc']]==o.get(0x10ed9b8,2)
        if o.stop==stop:
            assert p['pc']==o.u.reg_read(UC_X86_REG_ESI)
            assert p['flags']==o.u.reg_read(UC_X86_REG_EDX)
        # Independently expressed model for trap frame and return adjustment.
        if vector is not None:
            fault_pc=(pc-2)&0xffffffff if name=='Illegal' else pc
            expected,next_pc,events,charge=exception_model(c,fault_pc,flags,vector,target,cost)
            remaining=(budget-charge)&0xffffffff
            if not remaining or remaining&0x80000000:
                expected[20]=next_pc;expected[18]=flags;expected[16 if expected[17]&0x20 else 28]=expected[15]
            elif name=='Illegal':next_pc=(next_pc+2)&0xffffffff
            assert p['context']==expected and p['pc']==next_pc and p['events']==events
        keep(name,[opcode,p])

    # Unknown targets must not silently become ILLEGAL. While reconstruction
    # is partial, also cover a known unrecovered target. The full inventory
    # legitimately has no such target; do not make that a StopIteration error.
    implemented=set(ENTRIES)
    for include in (Path(__file__).resolve().parents[1]/'port/a68k').glob('*_ops.inc'):
        implemented.update(int(token,16) for token in re.findall(r'\((0x[0-9a-f]+)(?:,|\))',include.read_text()))
    unknown=0;assert unknown not in targets and unknown not in implemented
    pending=sorted(set(targets)-implemented)
    for other in [unknown]+pending[:1]:
        c=list(range(33));p=portable.cpu(4,c,pc=0x1234,flags=0x202,cycles=100,arg=0,entry=other)
        assert p['boundary']==5 and p['context']==c and p['pc']==0x1234 and not p['events']

    # Probe the actual original host-stack problem through IRQ entry, including
    # its PUSHAD and nested CALLs. Stop before RET can jump to arbitrary saved
    # data. No original instruction is patched, and no game is executed.
    stack_rows=[]
    for budget in (46,1000):
        c=[0]*33;c[15]=0x8000;c[16]=0x9000;c[17]=0x20;c[18]=0x202;c[20]=0x123456;c[21]=1;c[29]=0x100
        o.setup_exception(c,budget);o.ack=-1;o.targets=[0x7001,0x8000]
        o.run(0x462b1c,{UC_X86_REG_ECX:0x12345678},stops=(0x462ca3,0x462b7b))
        esp=o.u.reg_read(UC_X86_REG_ESP)
        if budget==46:
            assert o.stop==0x462b7b and esp==SP-8 and o.get(esp)==[0x12345678]
        else:assert o.stop==0x462ca3 and esp==SP-40 and o.get(esp)==[0x462bc8]
        stack_rows.append(dict(budget=budget,stop=f'{o.stop:08x}',stack_delta=esp-SP,
                              next_stack_word=f'{o.get(esp)[0]:08x}',events=o.events))
        o.targets=None
    covered=sum(counts.values());distinct=len(set(targets));trap=sum(v for k,v in counts.items() if k!='MOVEQ')
    return dict(cases=covered,groups=dict(counts),mismatches=0,result_sha256=digest.hexdigest(),
        coverage=dict(indexed_entries=len(targets),total_entries=65536,index_percent=100,
            implemented_tested_entries=covered,entry_percent=100*covered/65536,
            implemented_tested_targets=len(ENTRIES),total_targets=distinct,target_percent=100*len(ENTRIES)/distinct,
            ordinary_instruction_entries=counts['MOVEQ'],exception_routing_entries=trap,
            warning='Entry aliases and invalid encodings make this unsuitable as a total CPU completion estimate.'),
        native_odd_stack=stack_rows,
        limits=['Even vector targets for complete opcode paths; odd-vector recursion has a native host-stack defect.',
                'One deterministic state per covered encoding, plus the separate boundary suite; not every encoding/state cross-product.',
                'No complete execution loop, sound-board integration, Save State or frontend CPU switch.'])


def compare_faults(exe,portable):
    """Compare the native prefix, then test the approved stop separately.

    The original oracle stops before recursive dispatch. Portable retry guards
    are a host safety policy, not a claim to reproduce the original bad RET.
    """
    o=Oracle(exe);digest=hashlib.sha256();cases=0;retry_guards=0
    paths=[('Exception',1,0x462be0,3),('IRQ',2,0x462b1c,25),
           ('Line-A',4,0x48b518,10),('Line-F',4,0x48b540,11),
           ('Illegal',4,0x48b568,4)]
    for name,operation,entry,vector in paths:
        for supervisor in (False,True):
            for target in (1,0x7001,0xffffffff):
                for budget in (0,46,1000):
                    c=[0]*33;c[15]=0x8000;c[16]=0x9000
                    c[17]=0x20 if supervisor else 0;c[18]=0xa83;c[19]=1
                    c[20]=0x123456;c[21]=1;c[29]=0x100
                    pc=c[20];flags=c[18];opcode=0x4afc
                    o.setup_exception(c,budget);o.ack=-1
                    o.reads={c[29]+4*vector:target};o.put(0x10ed9b8,0,0)
                    regs={UC_X86_REG_ECX:opcode,UC_X86_REG_ESI:pc,UC_X86_REG_EDX:flags}
                    if operation==1:regs[UC_X86_REG_EAX]=vector
                    o.run(entry,regs,stops=(0x462c89,))
                    arg=vector if operation==1 else opcode
                    p=portable.cpu(operation,c,pc,flags,budget,arg,target,costs=o.cost,entry=entry)
                    assert o.stop==0x462c89 and p['boundary']==3
                    assert p['context']==o.get(CTX,33) and p['events']==o.events,(name,supervisor,hex(target),budget)
                    assert p['pc']==o.u.reg_read(UC_X86_REG_ESI)==target
                    assert p['cycles']==o.get(0x10ed9b0)[0]
                    assert p['fault']==[3,0x462c89,vector,pc-2 if name=='Illegal' else pc,
                                        target,(budget-o.cost[vector])&0xffffffff,flags]
                    assert [p['illegal_opcode'],p['illegal_pc']]==o.get(0x10ed9b8,2)
                    guards=portable.library.a68k_probe_fault_latch();assert guards==14
                    retry_guards+=guards;cases+=1
                    digest.update(json.dumps([name,supervisor,budget,p],sort_keys=True).encode())
    # Recreating a CPU clears the host diagnostic; normal execution resumes.
    p=portable.cpu(3,c,pc=0x1000,cycles=4,arg=0x7001)
    assert p['boundary']==1 and p['fault']==[0]*7 and p['context'][0]==1
    assert portable.library.a68k_probe_fault_latch()==0
    return dict(native_prefix_cases=cases,mismatches=0,post_fault_retry_guards=retry_guards,
                fresh_cpu_recovery_cases=1,result_sha256=digest.hexdigest(),
                policy='User-approved sticky fatal diagnostic at 00462c89; native reset does not resume a faulted CPU.',
                limits=['Original recursion/invalid RET is not reproduced or repaired.',
                        'No game reachability or frontend content-stop qualification; A68K is not integrated.'])
