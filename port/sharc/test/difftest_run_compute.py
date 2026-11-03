#!/usr/bin/env python3
"""Bounded scheduler + decoded real compute handlers, no stub dispatch effects.

Synthetic straight-line/count-loop programs use separated integer/finite FP
register banks. This qualifies composition, not arbitrary-game FP exceptions.
"""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_execute import State,FIELDS,STATE,Hooks,CALL
from difftest_compute import Context,WORD,DIAG
from difftest_fp import FP
from difftest_condition import P32,pointer
PROGRAM=0x72000000;COUNT=128;BASE=(PROGRAM-0x20000*108)&0xffffffff

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);mu.mem_map(PROGRAM,0x10000);rng=random.Random(23);libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()));lib.m2_sharc_decode_compute.argtypes=[C.c_uint32]*4+[P32];lib.m2_sharc_bind_condition.argtypes=[C.c_uint32,P32]
        lib.m2_sharc_dispatch_compute.argtypes=[C.POINTER(Context),C.c_bool];lib.m2_sharc_dispatch_compute.restype=C.c_bool
        lib.m2_sharc_run_bounded.argtypes=[C.POINTER(State),C.POINTER(Hooks)];lib.m2_sharc_run_bounded.restype=None;libs.append((path,lib))
    def w32(addr,value):mu.mem_write(addr,struct.pack('<I',value))
    cases=0;instructions=0
    for seed in range(64):
        records=(C.c_uint32*(27*COUNT))()
        for i in range(COUNT):
            floating=(i+seed)%3==0
            ops=(0x81,0x82,0x89,0xa1,0xa2,0xb0,0xe1,0xe2,0x130) if floating else (1,2,5,6,9,0x21,0x22,0x25,0x26,0x29,0x2a,0x30,0x40,0x41,0x42,0x43,0x61,0x62)
            op=rng.choice(ops);bank=8 if floating else 0
            x,y,z=(bank+rng.randrange(8) for _ in range(3));instruction=(op<<12)|(z<<8)|(y<<4)|x
            p=C.cast(C.byref(records,i*108),P32);p[0]=0x4bcb50
            libs[0][1].m2_sharc_decode_compute(instruction,0,STATE,PROGRAM+i*108,p)
            libs[0][1].m2_sharc_bind_condition(30 if i%4 else seed%32,p)
        for budget in (0,1,2,4,17,64):
            for looped in (False,True):
                initial=State()
                for i in range(169):initial.state[i]=rng.getrandbits(32)
                initial.state[2]=0x20000;initial.state[4]=1;initial.state[0xd4//4]=1
                initial.state[0x24//4]=0x20000;initial.state[0x9c//4]=0;initial.state[0xb8//4]=0xffffff
                initial.state[0x14//4]=(0x40020003 if looped else 0xffffff)
                initial.state[0x18//4]=3 if looped else 0;initial.state[0xa0//4]=initial.state[0x18//4]
                initial.state[0x240//4]=0
                for i in range(16):initial.state[(0xd8//4)+i]=(i+1) if i<8 else 0x3f800000+((i-8)<<20)
                initial.budget=budget;initial.stop=1 if seed%7==0 else 0;initial.event_count=0;initial.event_delay=10
                initial.program_base=BASE;initial.current_record=PROGRAM;initial.saved_record=PROGRAM;initial.fp_control=0xaabbbeef
                mu.mem_write(STATE,bytes(initial.state));mu.mem_write(PROGRAM,bytes(records))
                for name,addr in FIELDS.items():w32(addr,getattr(initial,name))
                w32(0x5aeb40,STATE);mu.mem_write(SP-256,bytes(256)+struct.pack('<I',STOP))
                mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_FPCW,0x37f);mu.reg_write(UC_X86_REG_FPSW,0);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
                mu.emu_start(0x4bd000,STOP,count=100000)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Original scheduler return')
                expected=State();C.memmove(C.addressof(expected.state),bytes(mu.mem_read(STATE,676)),676)
                for name,addr in FIELDS.items():setattr(expected,name,struct.unpack('<I',mu.mem_read(addr,4))[0])
                expected_records=bytes(mu.mem_read(PROGRAM,C.sizeof(records)));expected_sw=mu.reg_read(UC_X86_REG_FPSW)
                for path,lib in libs:
                    native=State.from_buffer_copy(bytes(initial));program=(C.c_uint32*(COUNT*27)).from_buffer_copy(bytes(records));fp=FP(0x7f,0);errors=[];dispatched=[]
                    @WORD
                    def word(opaque,token):
                        if STATE<=token<=STATE+672:return C.addressof(native.state)+token-STATE
                        if PROGRAM<=token<=PROGRAM+C.sizeof(program)-4:return C.addressof(program)+token-PROGRAM
                        errors.append(('token',token));return C.addressof(program)
                    diagnostic=DIAG(lambda opaque,fmt,pc:errors.append(('diagnostic',pc)))
                    context=Context(None,word,diagnostic,pointer(native.state,0x240),pointer(native.state,8),pointer(native.state,0x18),C.cast(C.byref(native,State.stop.offset),P32),C.cast(C.byref(native,State.current_record.offset),P32),C.pointer(fp))
                    @CALL
                    def dispatch(opaque,state,record,flags):
                        dispatched.append(record)
                        if not lib.m2_sharc_dispatch_compute(C.byref(context),False):errors.append(('dispatch',record))
                    event=CALL(lambda *args:errors.append('unexpected event'))
                    hooks=Hooks(dispatch,event,None);lib.m2_sharc_run_bounded(C.byref(native),C.byref(hooks))
                    if errors or bytes(native)!=bytes(expected) or bytes(program)!=expected_records or (fp.status^expected_sw)&~0x23f:
                        diffs=[hex(i) for i in range(0,C.sizeof(native),4) if bytes(native)[i:i+4]!=bytes(expected)[i:i+4]]
                        raise AssertionError(f'{path.name} seed{seed} budget{budget} loop{looped}: {diffs}, {errors}, SW{fp.status:x}/{expected_sw:x}')
                    if path==libs[0][0]:instructions+=len(dispatched)
                cases+=1
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':cases,'executed_instructions':instructions,'mismatches':0,'skipped':0,'seed':23,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Bounded scheduler with real decoded integer/finite-FP compute, conditions, counted loops and preexisting stop; no machine/ROM/game binding',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sharc_*.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','libraries')},indent=2))
if __name__=='__main__':main()
