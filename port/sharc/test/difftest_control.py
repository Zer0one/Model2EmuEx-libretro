#!/usr/bin/env python3
"""Original branch/call/return/loop setup vs C, including live delayed records."""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,
    UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS,UC_X86_REG_FPCW,UC_X86_REG_FPSW,UC_X86_REG_FPTAG)
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_integer import ENTRIES,EDGES
from difftest_execute import State,Hooks,CALL,FIELDS,STATE,PROGRAM
from difftest_condition import P32,pointer,FLAG_MASK

from difftest_compute import Context,WORD,DIAG
from difftest_fp import FP,ENTRIES as FP_SIMPLE,ARITHMETIC,SCALING
from difftest_memory import Operation
REC=PROGRAM+0x1000
STUB=STOP+0x300
HANDLERS=(0x4bcad0,0x4bd700,0x4bd750,0x4bd7b0,0x4bda10,0x4bda60,
          0x4be2a0,0x4be310,0x4be380,0x4be460,0x4be540,0x4be610,0x4be6f0,0x4be750,0x4be7c0)
class Record(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ('condition','operation','immediate','count','flags')]+[
        (n,P32) for n in ('value','address','step','lhs','rhs','destination')]
# Returning a raw address avoids ctypes' callback restriction for pointer returns.
RESOLVE=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--backend',action='store_true');ap.add_argument('--bindings',action='store_true');args=ap.parse_args()
    if args.bindings and not args.backend:ap.error('--bindings requires --backend')
    mu=load_original(args.exe);mu.mem_map(PROGRAM,0x10000)
    mu.mem_write(PROGRAM,struct.pack('<I',STUB)*0x4000);mu.mem_write(STUB,b'\xc3')
    tables=struct.unpack('<32I',mu.mem_read(0x573490,128))
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
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_dispatch_control
        fn.argtypes=[C.c_uint32,C.POINTER(State),C.POINTER(Hooks),RESOLVE,C.c_void_p];fn.restype=C.c_bool
        if args.backend:
            fn=lib.m2_sharc_dispatch_control_ex
            fn.argtypes=[C.c_uint32,C.POINTER(State),C.POINTER(Hooks),RESOLVE,C.c_void_p,C.POINTER(Operation)];fn.restype=C.c_bool
            lib.m2_sharc_compute_hooks.argtypes=[C.POINTER(Context)];lib.m2_sharc_compute_hooks.restype=Operation
            if args.bindings:
                lib.m2_sharc_bind_control.argtypes=[P32,WORD,C.c_void_p,C.POINTER(Record)];lib.m2_sharc_bind_control.restype=C.c_bool
        libs.append((p,fn,lib))
    active={};writes=[]
    def slot(s,record,flags,trace):
        trace.append((record,flags&(FLAG_MASK|2),s.budget,s.in_delay,s.state[2]))
        s.state[2]+=7
        # A redirected current record must be re-resolved by the branch after
        # its delay slots. Also mutate stack data read AFTER the delayed call.
        s.state[0x24//4]^=0x80000001
        if active['mode'] and len(trace)==1:s.current_record+=4*0x6c
        s.stop=1 # Does not cancel slot 2 or the enclosing taken branch.
    def hook(uc,a,size,user):
        if a==STUB:
            s=load();slot(s,s.current_record,uc.reg_read(UC_X86_REG_EFLAGS),active['trace']);store(s)
            uc.reg_write(UC_X86_REG_EFLAGS,0x8c7)
    mu.hook_add(UC_HOOK_CODE,hook)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,
               UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    rng=random.Random(10);counts={};operations={e:(e,n) for o,(e,n) in ENTRIES.items()} if args.backend else ENTRIES
    if args.backend:operations.update({e:(e,"FP") for e in FP_SIMPLE+ARITHMETIC+SCALING})
    ops=list(operations)
    layouts=((0x180,0x190,0x194,0x180,0x184,0x188),
             (8,8,0xc,0x180,0x184,0x240),
             (0xc,0x24,0x18,0x240,0x184,0x24),
             (0x18,8,0x24,0x180,0x240,8))
    for handler in HANDLERS:
        count=0
        for code in range(32):
            for flag in range(8):
                for li,layout in enumerate(layouts):
                    for mode in range(2):
                        s=State()
                        for i in range(169):s.state[i]=rng.getrandbits(32)
                        s.state[2]=EDGES[(code+li)%len(EDGES)]
                        s.state[4]=1;s.state[0xd4//4]=1
                        s.state[0x240//4]=(0,0xffffffff,rng.getrandbits(32),1<<(code%23))[li]
                        s.state[0x18//4]=(0,1,2,0xffffffff)[li]
                        s.budget=(0,1,2,0xffffffff)[li];s.event_delay=2;s.event_count=0
                        s.current_record=REC;s.saved_record=REC;s.program_base=PROGRAM;s.active_base=PROGRAM+0x200
                        op=ops[(code+flag+li+mode)%len(ops)];compute=operations[op][0]
                        if args.backend and operations[op][1]=="FP":
                            if li>1:continue
                            s.state[layout[3]//4]=0x3fc00000;s.state[layout[4]//4]=0x3f800000
                            if compute in SCALING:s.state[layout[4]//4]=(flag-3)&0xffffffff
                        initial=bytes(s)
                        immediate=EDGES[(code+flag)%len(EDGES)];counter=EDGES[(code+li+1)%len(EDGES)]
                        for alt in (0,1):
                            addr=REC+alt*4*0x6c
                            word(addr,handler);word(addr+4,compute);word(addr+8,tables[code])
                            word(addr+0x1c,immediate^(0xffffffff if alt else 0))
                            word(addr+0x20,counter);word(addr+0x2c,flag^(7 if alt else 0))
                            for field,off in zip((0x24,0xc,0x10,0x34,0x38,0x3c),layout):word(addr+field,STATE+off)
                        store(s);word(0x5aeb40,STATE);word(0x528bc0,STATE+0x240)
                        mu.mem_write(SP-128,bytes(128)+struct.pack('<I',STOP))
                        for r,v in preserved.items():mu.reg_write(r,v)
                        mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
                        if args.backend:
                            mu.reg_write(UC_X86_REG_FPCW,0x7f);mu.reg_write(UC_X86_REG_FPSW,0);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
                        active=dict(mode=mode,trace=[]);writes.clear()
                        mu.emu_start(handler,STOP,count=1000)
                        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Bad return')
                        if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Preserved register changed')
                        if bytes(mu.mem_read(SP,4))!=struct.pack('<I',STOP):raise AssertionError('Return address changed')
                        if any(not(SP-128<=a and a+size<=SP) and (size!=4 or not(STATE<=a<STATE+676 or a in FIELDS.values() or args.backend and a in (0x528bc4,0x528bc8,0x528bcc))) for a,size in writes):
                            raise AssertionError(f'Unexpected writes {writes}')
                        expected=bytes(load());trace=active['trace']
                        for p,fn,lib in libs:
                            native=State.from_buffer_copy(initial);records=[];native_trace=[]
                            for alt in (0,1):
                                rec=Record(code,op,immediate^(0xffffffff if alt else 0),counter,flag^(7 if alt else 0))
                                for name,off in zip(('value','address','step','lhs','rhs','destination'),layout):setattr(rec,name,pointer(native.state,off))
                                records.append(rec)
                            errors=[]
                            raw_records=[(C.c_uint32*27).from_buffer_copy(bytes(mu.mem_read(REC+alt*4*0x6c,108))) for alt in (0,1)]
                            binding_word=WORD(lambda opaque,t:C.addressof(native.state)+t-STATE if STATE<=t<STATE+676 else None)
                            def resolve(_,addr):
                                if addr not in (REC,REC+4*0x6c):errors.append(addr);return C.addressof(records[0])
                                if args.bindings and not lib.m2_sharc_bind_control(raw_records[addr!=REC],binding_word,None,C.byref(records[addr!=REC])):errors.append('Record binding')
                                return C.addressof(records[addr!=REC])
                            resolver=RESOLVE(resolve)
                            active=dict(mode=mode)
                            dh=CALL(lambda _,sp,r,f:slot(sp.contents,r,f,native_trace))
                            eh=CALL(lambda *_:errors.append('unexpected event'))
                            hooks=Hooks(dh,eh,None)
                            extra=()
                            if args.backend:
                                fp=FP(0x7f,0)
                                wr=WORD(lambda opaque,token:C.addressof(native.state)+token-STATE)
                                report=DIAG(lambda opaque,fmt,pc:errors.append("unexpected diagnostic"))
                                context=Context(None,wr,report,pointer(native.state,0x240),pointer(native.state,8),pointer(native.state,0x18),C.cast(C.byref(native,State.stop.offset),P32),C.cast(C.byref(native,State.current_record.offset),P32),C.pointer(fp))
                                operation=lib.m2_sharc_compute_hooks(C.byref(context));extra=(C.byref(operation),)
                            ok=fn(handler,C.byref(native),C.byref(hooks),resolver,None,*extra)
                            if args.backend and (fp.status^mu.reg_read(UC_X86_REG_FPSW))&~0x23f:raise AssertionError("FP comparison/stack wiring")
                            if not ok or bytes(native)!=expected or native_trace!=trace or errors:
                                diffs=[hex(i) for i in range(0,len(expected),4) if bytes(native)[i:i+4]!=expected[i:i+4]]
                                raise AssertionError(f'{p.name} {handler:x},code{code},flags{flag},layout{li},mode{mode}: '
                                     f'diff={diffs}, trace={native_trace}/{trace}, errors={errors}')
                        count+=1
        counts[f'0x{handler:08x}']=count;print(f'{handler:08x}: {count} passed',flush=True)
    root=Path(__file__).resolve().parents[1]
    sources=('sharc_control.c','sharc_control.h','sharc_execute.c','sharc_condition.c','sharc_integer.c','sharc_flow.c')
    if args.backend:sources=tuple(p.name for p in root.glob("sharc_*.c"))
    receipt={'status':'passed','scope':'15 control/loop handlers; '+('complete compute backend' if args.backend else 'integer compute')+' and synthetic delayed instructions',
        'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':10,'entries':counts,'cases':sum(counts.values()),
        'mismatches':0,'skipped':0,'raw_record_binding':args.bindings,'sources':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources},
        'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn,lib in libs]}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n');print('Total',receipt['cases'])


if __name__=='__main__':main()
