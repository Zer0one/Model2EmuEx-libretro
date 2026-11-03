#!/usr/bin/env python3
"""Native mode writes, bank swaps, stack helpers and queued-event integration."""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,
    UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS)
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_integer import EDGES
from difftest_execute import State,Hooks,CALL,FIELDS,STATE,PROGRAM
from difftest_memory import Bus,READ_FN,WRITE_FN
from difftest_condition import P32,pointer
ENTRIES=(0x4bd550,0x4bd5d0,0x4bce10,0x4bce60,0x4bceb0,0x4bcf00,
         0x4bcd50,0x4bcd60,0x4bcd90,0x4bcdc0,0x4bcdd0,0x4bcdf0,0x4bcf50,0x4bcfc0,0x4bcfe0)
BANKS=(0x4bce10,0x4bce60,0x4bceb0,0x4bcf00)
READ=STOP+0x100


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    mu=load_original(args.exe);mu.mem_map(PROGRAM,0x1000);mu.mem_write(READ,b'\xc3')
    def word(a,v):mu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def load():
        s=State();C.memmove(C.addressof(s),bytes(mu.mem_read(STATE,676)),676)
        for n,a in FIELDS.items():setattr(s,n,struct.unpack('<I',mu.mem_read(a,4))[0])
        return s
    def store(s):
        mu.mem_write(STATE,bytes(s.state))
        for n,a in FIELDS.items():word(a,getattr(s,n))
    libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_state_helper
        fn.argtypes=[C.c_uint32,C.POINTER(State),P32,C.c_uint32,C.c_uint32,P32,C.POINTER(Bus),P32];fn.restype=C.c_bool
        lib.m2_sharc_events.argtypes=[C.POINTER(State),C.POINTER(Hooks)];lib.m2_sharc_events.restype=None
        libs.append((p,lib,fn))
    trace=[];writes=[]
    def read(a):return a^0xa55a5aa5
    def hook(uc,a,size,u):
        if a==READ:
            addr=uc.reg_read(UC_X86_REG_ECX);trace.append(('read',addr))
            uc.reg_write(UC_X86_REG_EAX,read(addr))
        if a in BANKS:trace.append(('bank',a))
    mu.hook_add(UC_HOOK_CODE,hook)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,
               UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    def call(entry,a0,a1):
        mu.mem_write(SP-128,bytes(128)+struct.pack('<I',STOP))
        for r,v in preserved.items():mu.reg_write(r,v)
        mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
        mu.reg_write(UC_X86_REG_ECX,a0);mu.reg_write(UC_X86_REG_EDX,a1);mu.reg_write(UC_X86_REG_EAX,a0)
        mu.emu_start(entry,STOP,count=2000)
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Bad return')
        if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Preserved register changed')
        if bytes(mu.mem_read(SP,4))!=struct.pack('<I',STOP):raise AssertionError('Return address changed')
        return mu.reg_read(UC_X86_REG_EAX)
    rng=random.Random(11);counts={};integration=0
    for entry in ENTRIES:
        for case in range(1024):
            s=State()
            for i in range(169):s.state[i]=rng.getrandbits(32)
            index=(0,1,2,0xffffffff)[case%4];s.state[4]=index;s.state[0xd4//4]=index
            s.current_record=PROGRAM;s.active_read=READ;s.event_count=(0,2,6)[case%3];s.event_delay=case%3
            target=(0x238,0x240,0x180,0x238)[case%4]
            a0=(EDGES[case%len(EDGES)] if case<256 else rng.getrandbits(32))
            if case<128:a0=(0,0x80,0x400,0x480)[case%4]
            a1=rng.getrandbits(32)
            queue=(C.c_uint32*8)(*(BANKS[i%4] for i in range(8)))
            raw=bytes(s);queue_raw=bytes(queue);store(s);mu.mem_write(0x5aeb14,queue_raw)
            word(0x5aeb40,STATE);word(PROGRAM+0x24,STATE+target);word(PROGRAM+0x1c,a0)
            trace.clear();writes.clear()
            result=call(entry,a0,a1)
            compound=entry in (0x4bd550,0x4bd5d0) and case%4==3
            if compound:call(0x4bcf70,0,0);call(0x4bcf70,0,0);integration+=1
            expected=bytes(load());expected_queue=bytes(mu.mem_read(0x5aeb14,32));original_trace=list(trace)
            if any(size!=4 or not(STATE<=a<STATE+676 or a in FIELDS.values() or a==0x5aeb40 or 0x5aeb14<=a<0x5aeb34 or SP-128<=a<SP) for a,size in writes):
                raise AssertionError('Unexpected writes')
            for p,lib,fn in libs:
                native=State.from_buffer_copy(raw);nqueue=(C.c_uint32*8).from_buffer_copy(queue_raw);nresult=C.c_uint32(0xdeadbeef)
                native_trace=[]
                def busread(_,a):native_trace.append(('read',a));return read(a)
                rb=READ_FN(busread);wb=WRITE_FN(lambda *_:None);bus=Bus(rb,wb,None)
                ok=fn(entry,C.byref(native),pointer(native.state,target),a0,a1,nqueue,C.byref(bus),C.byref(nresult))
                if entry in BANKS:native_trace.append(('bank',entry))
                errors=[]
                def event(_,sp,i,flags):
                    token=nqueue[i];native_trace.append(('bank',token))
                    if not fn(token,sp,P32(),0,0,nqueue,C.byref(bus),C.byref(nresult)):errors.append(token)
                dh=CALL(lambda *_:errors.append('unexpected dispatch'));eh=CALL(event);hooks=Hooks(dh,eh,None)
                if compound:lib.m2_sharc_events(C.byref(native),C.byref(hooks));lib.m2_sharc_events(C.byref(native),C.byref(hooks))
                meaningful=entry in (0x4bcd50,0x4bcdc0,0x4bcdd0)
                if not ok or bytes(native)!=expected or bytes(nqueue)!=expected_queue or native_trace!=original_trace or errors or meaningful and nresult.value!=result:
                    diffs=[hex(i) for i in range(0,len(expected),4) if bytes(native)[i:i+4]!=expected[i:i+4]]
                    raise AssertionError(f'{p.name} {entry:x} case{case}: diffs={diffs}, trace={native_trace}/{original_trace}, result={nresult.value:x}/{result:x}')
        counts[f'0x{entry:08x}']=1024;print(f'{entry:08x}: 1024 passed',flush=True)
    root=Path(__file__).resolve().parents[1]
    receipt={'status':'passed','scope':'15 state/mode helpers plus original queued-bank integration',
        'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':11,'entries':counts,'cases':sum(counts.values()),
        'compound_cases_included':integration,'mismatches':0,'skipped':0,
        'sources':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('sharc_mode.c','sharc_mode.h','sharc_execute.c')},
        'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,lib,fn in libs]}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n');print('Total',receipt['cases'])


if __name__=='__main__':main()
