#!/usr/bin/env python3
"""Complete original scheduler routines vs C with identical synthetic handlers.

Handlers/events are boundary fixtures; no DSP decoder, game or board is claimed.
Original instructions run to return, including event callbacks and nested slots.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)
from difftest_bits import load_original, EXE_SHA256, STOP, SP
from difftest_condition import FLAG_MASK

STATE, PROGRAM, DISPATCH, EVENT = 0x10edc30, 0x72000000, STOP+0x300, STOP+0x400
FIELDS={'budget':0x5aeb0c,'event_delay':0x5aeb44,'event_count':0x10ed944,
    'stop':0x10ed950,'in_delay':0x10ed954,'current_record':0x5aeb10,
    'saved_record':0x10eded8,'program_base':0x10ededc,'active_base':0x5aeb38,
    'read_binding':0x10edee4,'write_binding':0x10edee8,
    'active_read':0x5aeb3c,'active_write':0x5aeb48,'fp_control':0x528bd0}
FUNCTIONS={0x4bcf70:'m2_sharc_events',0x4bdfa0:'m2_sharc_delay_slots',
           0x4bd000:'m2_sharc_run_bounded',0x4be000:'m2_sharc_run_continuous'}

class State(C.Structure):
    _fields_=[('state',C.c_uint32*169)]+[(n,C.c_uint32) for n in FIELDS]

CALL=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(State),C.c_uint32,C.c_uint32)
class Hooks(C.Structure):
    _fields_=[('dispatch',CALL),('event',CALL),('opaque',C.c_void_p)]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    mu=load_original(args.exe)
    # One real 100,000-instruction batch rollover; other cases are small.
    length=0xb00000
    mu.mem_map(PROGRAM,length)
    mu.mem_write(PROGRAM,struct.pack('<I',DISPATCH)*(length//4))
    for address in (0,0xfffff000,0x7ffff000,0x80000000):
        mu.mem_map(address,0x1000);mu.mem_write(address,struct.pack('<I',DISPATCH)*1024)
    mu.mem_write(DISPATCH,b'\xc3')
    for i in range(8):
        mu.mem_write(EVENT+i*16,b'\xc3')
        mu.mem_write(0x5aeb14+i*4,struct.pack('<I',EVENT+i*16))
    libs=[]
    for path in args.libraries:
        lib=C.CDLL(str(path.resolve()))
        for name in FUNCTIONS.values():
            fn=getattr(lib,name);fn.argtypes=[C.POINTER(State),C.POINTER(Hooks)];fn.restype=None
        libs.append((path,lib))
    def load():
        s=State();C.memmove(C.addressof(s),bytes(mu.mem_read(STATE,676)),676)
        for name,address in FIELDS.items():setattr(s,name,struct.unpack('<I',mu.mem_read(address,4))[0])
        return s
    def store(s):
        mu.mem_write(STATE,bytes(s.state))
        for name,address in FIELDS.items():mu.mem_write(address,struct.pack('<I',getattr(s,name)))
    active={};writes=[]
    def effect(kind,s,token,flags,trace):
        trace.append((kind,token,flags& (FLAG_MASK|2),s.budget,s.current_record,
                      s.state[2],s.stop,s.in_delay,s.event_count,s.event_delay))
        if kind=='D':
            active['dispatch_count']+=1
            count=active['dispatch_count']
            mode=active['mode']
            if mode==1:
                s.state[0x240//4]=(s.state[0x240//4]&~0x43f)|(1 if flags&0x40 else 0)|(4 if flags&0x80 else 0)
            if mode==2:
                s.current_record+=0x6c*2;s.state[2]+=3
            if mode==3 and count==1:s.event_count=2;s.event_delay=0
            if mode==4 and count==1:
                s.budget=1 # Exercise refill and refreshed configured bindings.
                s.program_base+=0x6c;s.read_binding+=17;s.write_binding+=19
            if mode==5 and count==1:s.program_base+=0x6c
            if count>=active['stop_after']:s.stop=1
            return mode==7 and not s.in_delay and count==1
        em=active['event_mode']
        if em==1:s.event_count=0
        if em==2 and token==0:s.event_count=3
        if em==3:s.current_record+=0x6c;s.state[2]+=1;s.stop=1
        if em==4:s.event_delay=9
        return False
    def original_hook(uc,address,size,user):
        if address==DISPATCH or EVENT<=address<EVENT+8*16 and (address-EVENT)%16==0:
            s=load();kind='D' if address==DISPATCH else 'E'
            token=s.current_record if kind=='D' else (address-EVENT)//16
            nested=effect(kind,s,token,uc.reg_read(UC_X86_REG_EFLAGS),active['trace'])
            store(s)
            # Volatile flags may differ after the synthetic handler; every
            # consumed subsequent flag must come from original instructions.
            uc.reg_write(UC_X86_REG_EFLAGS,0x8c7)
            if nested:uc.reg_write(UC_X86_REG_EIP,0x4bdfa0) # Tail call preserves the real return address.
    mu.hook_add(UC_HOOK_CODE,original_hook)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,
               UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    rng=random.Random(9)
    def base():
        s=State()
        for i in range(169):s.state[i]=rng.getrandbits(32)
        s.state[2]=4;s.state[0x14//4]=0xfffffe
        s.state[0x10//4]=1;s.state[0xd4//4]=1
        s.state[0x24//4]=4;s.state[0x9c//4]=7;s.state[0xb8//4]=0xfffffe
        s.budget=3;s.event_delay=10;s.event_count=0;s.stop=0
        s.current_record=PROGRAM;s.saved_record=PROGRAM;s.program_base=PROGRAM
        s.active_base=0xdeadbeef;s.read_binding=0x11223344;s.write_binding=0x55667788
        s.active_read=1;s.active_write=2;s.fp_control=0xaabbbeef
        return s
    scenarios=[]
    def add(entry,s,mode=0,em=0,stop_after=3,label=''):
        scenarios.append((entry,bytes(s),mode,em,stop_after,label))
    for delay in (0,1,2,0xffffffff):
        for count in (0,1,2,3):
            for em in range(5):
                s=base();s.event_delay=delay;s.event_count=count
                add(0x4bcf70,s,em=em,label='events')
    for record in (PROGRAM,PROGRAM-0x6c,0xfffffff0,0x7fffff94):
        for budget in (0,1,2,0xffffffff):
            for stop in (0,1):
                for em in range(5):
                    s=base();s.current_record=record;s.budget=budget;s.stop=stop
                    s.event_delay=0;s.event_count=2
                    add(0x4bdfa0,s,em=em,stop_after=1,label='delay')
    for entry in (0x4bd000,0x4be000):
        for budget in (0,1,2,3,0xffffffff):
            for stop in (0,1):
                for mode in (0,1,2,3,4,5,7):
                    for em in range(5):
                        s=base();s.budget=budget;s.stop=stop
                        add(entry,s,mode,em,3,'basic')
        for condition in range(32):
            for status in (0,0xffffffff,rng.getrandbits(32)):
                for loop_count in (0,1,2):
                    s=base();s.state[0x14//4]=(condition<<24)|4
                    s.state[0x240//4]=status;s.state[0x18//4]=loop_count
                    add(entry,s,0,0,3,'conditional loop raw status')
                    add(entry,s,1,0,3,'conditional loop handler flags')
        for kind in (1,2,3):
            for loop_count in (0,1,2,3,0xffffffff):
                for index in (0,1,2):
                    s=base();s.state[0x14//4]=(kind<<30)|4
                    s.state[0x18//4]=loop_count;s.state[0xd4//4]=index
                    # Wrapping -1 indexes restore the preceding words, as x86.
                    prior=(index-1)&0xffffffff
                    s.state[((0x9c+4*prior)&0xffffffff)//4]=7
                    s.state[((0xb8+4*prior)&0xffffffff)//4]=0xfffffe
                    s.state[(0x9c+4*index)//4]=loop_count
                    add(entry,s,0,0,4,'counted loop')
        s=base();s.state[0x14//4]=(1<<30)|4;s.state[0x18//4]=2
        s.state[0xa0//4]=2
        add(entry,s,5,0,3,'live configured base on loop repeat')
    # Real batch boundary, not an injected shortened budget. STOP occurs on
    # the first instruction of batch 2; that instruction is not budget-charged.
    add(0x4be000,base(),0,0,100001,'100000 batch rollover')
    counts={f'0x{x:08x}':0 for x in FUNCTIONS}
    for case,(entry,raw,mode,em,stop_after,label) in enumerate(scenarios):
        s=State.from_buffer_copy(raw);store(s)
        mu.mem_write(0x528bc0,struct.pack('<I',STATE+0x240))
        mu.mem_write(0x5aeb40,struct.pack('<I',STATE))
        mu.mem_write(SP-256,bytes(256)+struct.pack('<I',STOP))
        for reg,value in preserved.items():mu.reg_write(reg,value)
        mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
        active=dict(mode=mode,event_mode=em,stop_after=stop_after,dispatch_count=0,trace=[])
        writes.clear()
        mu.emu_start(entry,STOP,count=12000000 if stop_after>100000 else 10000)
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:
            raise AssertionError(f'Original failed to return: case{case} {label}')
        if any(mu.reg_read(reg)!=v for reg,v in preserved.items()):raise AssertionError('Preserved registers changed')
        allowed=set(FIELDS.values())|{0x528bc0,0x5aeb40}
        if any(not (SP-256<=a<SP or STATE<=a<STATE+676 or a in allowed) or size not in (2,4) for a,size in writes):
            raise AssertionError('Unexpected original writes')
        if bytes(mu.mem_read(SP,4))!=struct.pack('<I',STOP):raise AssertionError('Return address changed')
        expected=bytes(load());original_trace=active['trace']
        for path,lib in libs:
            native=State.from_buffer_copy(raw);trace=[]
            active=dict(mode=mode,event_mode=em,stop_after=stop_after,dispatch_count=0,trace=trace)
            def dispatch(_,sptr,record,flags):
                nested=effect('D',sptr.contents,record,flags,trace)
                if nested:lib.m2_sharc_delay_slots(sptr,C.byref(hooks))
            def event(_,sptr,index,flags):effect('E',sptr.contents,index,flags,trace)
            dh,eh=CALL(dispatch),CALL(event);hooks=Hooks(dh,eh,None)
            getattr(lib,FUNCTIONS[entry])(C.byref(native),C.byref(hooks))
            if bytes(native)!=expected or trace!=original_trace:
                diffs=[hex(i) for i in range(0,len(expected),4) if bytes(native)[i:i+4]!=expected[i:i+4]]
                td=next(((i,a,b) for i,(a,b) in enumerate(zip(trace,original_trace)) if a!=b),None)
                raise AssertionError(f'{path.name} case{case} {entry:x} {label} mode{mode} em{em}: '
                    f'diffs={diffs}, trace lengths={len(trace)}/{len(original_trace)}, first diff={td}')
        counts[f'0x{entry:08x}']+=1
        if case%400==0:print(f'{case+1}/{len(scenarios)} passed',flush=True)
    root=Path(__file__).resolve().parents[1]
    receipt={'status':'passed','scope':'4 complete scheduler routines with synthetic handler/event boundaries; integer execution state',
        'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':9,'entries':counts,'cases':sum(counts.values()),
        'batch_rollover_instructions':100001,'mismatches':0,'skipped':0,
        'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/n for n in
            ('sharc_execute.c','sharc_execute.h','sharc_flow.c','sharc_flow.h','sharc_condition.c','sharc_integer.c')]},
        'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,lib in libs]}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(counts));print('Total',receipt['cases'])


if __name__=='__main__':main()
