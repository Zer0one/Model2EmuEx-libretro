#!/usr/bin/env python3
"""All recovered instruction forms composed with real delay slots and events.

Original EXE instruction, compute, bank and board-bus bodies execute together.
Storage is synthetic. This is not a production machine/game qualification.
"""
import argparse,ctypes as C,hashlib,json,os,random,struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_execute import State,FIELDS,STATE
from difftest_condition import P32,pointer,put
from difftest_compute import WORD,DIAG
from difftest_fp import FP
from difftest_memory import Bus,READ_FN,WRITE_FN,HANDLERS as MEMORY
from difftest_control import HANDLERS as CONTROL
from difftest_board import Bus as Board,BASES,SIZES,FIFO

PROGRAM=0x7a000000;COUNT=128;BASE=(PROGRAM-0x20000*108)&0xffffffff
CURRENT=PROGRAM+16*108
TRANSFER=(0x4bca50,0x4bca80,0x4bcab0,0x4bcac0,0x4bd540,0x4bd650,0x4bd680,0x4bd6a0,0x4bd6c0,0x4bd6e0)
HANDLERS=(0x4bca40,0x4bcb50,0x4bcb10,0x4bd550,0x4bd5d0)+MEMORY+TRANSFER+CONTROL
FAIL=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class Runtime(C.Structure):
    _fields_=[('execution',C.POINTER(State)),('fp',C.POINTER(FP)),('word',WORD),('opaque',C.c_void_p),('diagnostic',DIAG),('bus',C.POINTER(Bus)),('queue',P32),('failure',FAIL)]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--scheduled',action='store_true');a=ap.parse_args()
    mu=load_original(a.exe);rng=random.Random(31);initial=[]
    for base,size in zip(BASES,SIZES):
        data=rng.randbytes(size);initial.append(data);mu.mem_map(base,size);mu.mem_write(base,data)
    mu.mem_map(FIFO,0x1000);mu.mem_map(PROGRAM,0x10000)
    def w32(addr,v):mu.mem_write(addr,struct.pack('<I',v))
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    for addr,v in zip((0x5aa87c,0x5aa754,0x5aa700,0x5aa8dc),BASES):w32(addr,v)
    for addr,v in ((0x5aa724,FIFO),(0x5aa738,FIFO+0x100),(0x528bc0,STATE+0x240)):w32(addr,v)
    table=struct.unpack('<32I',mu.mem_read(0x573490,128));libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()));storage=[(C.c_uint8*len(d)).from_buffer_copy(d) for d in initial]
        lib.m2_sharc_board_read.argtypes=[C.POINTER(Board),C.c_uint32];lib.m2_sharc_board_read.restype=C.c_uint32
        lib.m2_sharc_board_write.argtypes=[C.POINTER(Board),C.c_uint32,C.c_uint32];lib.m2_sharc_board_write.restype=None
        lib.m2_sharc_runtime_dispatch.argtypes=[C.POINTER(Runtime),C.c_uint32];lib.m2_sharc_runtime_dispatch.restype=C.c_bool
        for n in ('bounded','continuous'):
            fn=getattr(lib,'m2_sharc_runtime_run_'+n);fn.argtypes=[C.POINTER(Runtime)];fn.restype=None
        libs.append((path,lib,storage))
    counts={};banks=(0x4bce10,0x4bce60,0x4bceb0,0x4bcf00)
    instructions=[]
    if a.scheduled:mu.hook_add(unicorn.UC_HOOK_CODE,lambda u,addr,size,data:instructions.append(addr) if addr in HANDLERS else None)
    for handler in ((0x4bd000,0x4be000) if a.scheduled else HANDLERS):
        for code in range(32):
            for phase in range(8):
                s=State();program=(C.c_uint32*(27*COUNT))()
                for i in range(169):s.state[i]=rng.getrandbits(32)
                s.state[2]=0x20010;s.state[4]=1;s.state[0xd4//4]=1;s.state[0x24//4]=0x20030
                s.state[0x18//4]=phase%3;s.state[0x14//4]=0xffffff;s.state[0xb8//4]=0xffffff
                s.state[0x238//4]=(0,0x480)[phase%2];s.state[0x240//4]=(0,0xffffffff,1<<code,0x180000)[phase%4]
                for off,v in ((0x138,0x20030),(0x158,0x20030),(0x178,0),(0x198,0),(0xd8,0x3f800000),(0xdc,0x40000000)):s.state[off//4]=v
                s.budget=17;s.event_delay=phase%3;s.event_count=phase%3;s.stop=phase%2;s.in_delay=0
                s.program_base=BASE;s.active_base=BASE;s.current_record=CURRENT;s.saved_record=CURRENT
                s.active_read=s.read_binding=0x4c6100;s.active_write=s.write_binding=0x4c6020;s.fp_control=0x7f
                queue=(C.c_uint32*8)(*(banks[i%4] for i in range(8)))
                for i in range(COUNT):
                    p=C.cast(C.byref(program,i*108),P32);p[0]=0x4bca40;p[1]=(0x460f40,0x4615e0,0x4613e0,0x461700)[phase%4];p[2]=table[code]
                    p[3]=STATE+0x138;p[4]=STATE+0x178;p[5]=STATE+0x158;p[6]=STATE+0x198
                    p[7]=0x20030;p[8]=2;p[9]=STATE+0xe0;p[10]=STATE+0xe4;p[11]=phase
                    p[13]=STATE+0xd8;p[14]=STATE+0xdc;p[15]=STATE+0xe8
                p=C.cast(C.byref(program,16*108),P32);p[0]=handler
                if handler in (0x4bd550,0x4bd5d0):p[9]=STATE+0x238;p[7]=0x480
                # Actual slots, not hooks supplying effects: compute, mode write,
                # or a branch redirecting the second slot and outer rebind.
                slot=C.cast(C.byref(program,17*108),P32);slot[0]=(0x4bcb50,0x4bd5d0,0x4bcad0)[phase%3]
                if slot[0]==0x4bd5d0:slot[9]=STATE+0x238;slot[7]=0x480
                if slot[0]==0x4bcad0:slot[2]=table[30];slot[7]=0x20040
                C.cast(C.byref(program,18*108),P32)[0]=0x4bcb50
                # The outer handler must not validate a redirected record's
                # entry/condition: those words are not used after the slots.
                C.cast(C.byref(program,62*108),P32)[2]=0xdeadbeef
                if a.scheduled:
                    s.state[2]=0x20000;s.state[0x14//4]=0xffffff;s.state[0x18//4]=0
                    s.state[0x9c//4]=0;s.state[0xb8//4]=0xffffff
                    s.current_record=s.saved_record=PROGRAM;s.program_base=BASE
                    s.budget=(0,1,2,3,8,16,64,128)[code%8];s.stop=1 if phase==7 else 0
                    s.fp_control=0xaabbbeef
                    def rec(i,entry):
                        p=C.cast(C.byref(program,i*108),P32);p[0]=entry;p[2]=table[30];p[11]=0
                        p[1]=(0x460f40,0x4615e0,0x4613e0)[phase%3];return p
                    for i in range(COUNT):rec(i,0x4bca40)
                    p=rec(0,0x4bd5d0);p[9]=STATE+0x238;p[7]=0x480
                    rec(1,0x4bcb50);rec(2,(0x4bddb0,0x4bde20,0x4bdea0,0x4bdf20)[phase%4])
                    p=rec(3,0x4bd7b0);p[7]=0x40020008;p[8]=2
                    rec(4,0x4bcb10);rec(5,0x4bdcb0)
                    p=rec(6,0x4bd550);p[9]=STATE+0x238;p[7]=0x480
                    p=rec(7,0x4bd6c0);p[7]=0xc00000
                    rec(8,0x4bcb50)
                    p=rec(9,0x4be7c0);p[7]=0x2000e
                    rec(10,0x4bcb50);p=rec(11,0x4bcac0);p[7]=0x12345678
                    p=rec(14,0x4be380);p[7]=0x20014;p[11]=5
                    rec(15,0x4bcb50);p=rec(16,0x4bd5d0);p[9]=STATE+0x238;p[7]=0x480
                    for i in (17,18,19):p=rec(i,0x4bd6e0);p[7]=0x400000
                    rec(20,0x4bcb50);p=rec(21,0x4be2a0);p[11]=1
                    rec(22,0x4bcb50);p=rec(23,0x4bd550);p[9]=STATE+0x238;p[7]=0x480
                f0=(C.c_uint32*35)(*(rng.getrandbits(32) for _ in range(35)));f1=(C.c_uint32*35)(*(rng.getrandbits(32) for _ in range(35)))
                for f in (f0,f1):f[32]=phase;f[33]=31-phase;f[34]=(0,1,31,32)[phase%4]
                if a.scheduled:f0[34]=31 if phase%2 else 32
                raw=bytes(s);pr=bytes(program);qr=bytes(queue);fr0=bytes(f0);fr1=bytes(f1)
                mu.mem_write(STATE,bytes(s.state));mu.mem_write(PROGRAM,pr);mu.mem_write(0x5aeb14,qr);mu.mem_write(FIFO,fr0);mu.mem_write(FIFO+0x100,fr1)
                for n,addr in FIELDS.items():w32(addr,getattr(s,n))
                w32(0x5aeb40,STATE);mu.mem_write(SP-512,bytes(512)+struct.pack('<I',STOP));mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
                mu.reg_write(UC_X86_REG_FPCW,0x37f if a.scheduled else 0x7f);mu.reg_write(UC_X86_REG_FPSW,0);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
                mu.emu_start(handler,STOP,count=30000)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Original return')
                expected=State();C.memmove(C.addressof(expected.state),bytes(mu.mem_read(STATE,676)),676)
                for n,addr in FIELDS.items():setattr(expected,n,r32(addr))
                eq=bytes(mu.mem_read(0x5aeb14,32));ep=bytes(mu.mem_read(PROGRAM,len(pr)));ef0=bytes(mu.mem_read(FIFO,140));ef1=bytes(mu.mem_read(FIFO+0x100,140))
                for path,lib,storage in libs:
                    native=State.from_buffer_copy(raw);np=(C.c_uint32*(27*COUNT)).from_buffer_copy(pr);nq=(C.c_uint32*8).from_buffer_copy(qr)
                    nf0=(C.c_uint32*35).from_buffer_copy(fr0);nf1=(C.c_uint32*35).from_buffer_copy(fr1);fp=FP(0x37f if a.scheduled else 0x7f,0);errors=[]
                    board=Board(*storage,nf0,nf1,pointer(native.state,0x240),STATE,STATE,native.stop)
                    @WORD
                    def word(_,token):
                        if STATE<=token<=STATE+672:return C.addressof(native.state)+token-STATE
                        if PROGRAM<=token<=PROGRAM+C.sizeof(np)-4:return C.addressof(np)+token-PROGRAM
                        return None # Unused allocator fields are not guest loads.
                    def read(_,addr):
                        board.stop=native.stop;v=lib.m2_sharc_board_read(C.byref(board),addr);native.stop=board.stop;return v
                    def write(_,addr,v):
                        board.stop=native.stop;lib.m2_sharc_board_write(C.byref(board),addr,v);native.stop=board.stop
                    rd=READ_FN(read);wr=WRITE_FN(write);bus=Bus(rd,wr,None);diag=DIAG(lambda *args:errors.append('diagnostic'))
                    def fatal(_,entry,record):
                        os.write(2,f'Unexpected runtime failure {entry:x}/{record:x}\n'.encode());os._exit(1)
                    failure=FAIL(fatal);runtime=Runtime(C.pointer(native),C.pointer(fp),word,None,diag,C.pointer(bus),nq,failure)
                    if a.scheduled:
                        getattr(lib,'m2_sharc_runtime_run_'+('bounded' if handler==0x4bd000 else 'continuous'))(C.byref(runtime));ok=True
                    else:ok=lib.m2_sharc_runtime_dispatch(C.byref(runtime),0x8c7)
                    if not ok or errors or bytes(native)!=bytes(expected) or bytes(np)!=ep or bytes(nq)!=eq or bytes(nf0)!=ef0 or bytes(nf1)!=ef1:
                        diffs=[hex(i) for i in range(0,C.sizeof(native),4) if bytes(native)[i:i+4]!=bytes(expected)[i:i+4]]
                        raise AssertionError(f'{path.name} {handler:x}/cond{code}/phase{phase}: {diffs}, queue {list(nq)}/{struct.unpack("<8I",eq)}, {errors}')
                    if (fp.status^mu.reg_read(UC_X86_REG_FPSW))&~0x23f:raise AssertionError('FP comparison/stack')
                    # Unicorn retains reserved CW bit 6 verbatim after FLDCW;
                    # architectural x87 reads it as one (setup unit evidence).
                    if fp.control!=(mu.reg_read(UC_X86_REG_FPCW)|0x40):raise AssertionError(f'FP control {fp.control:x}/{mu.reg_read(UC_X86_REG_FPCW):x}')
            # Full RAM comparison, persistent across cases on both sides.
            for base,size,j in zip(BASES[:3],SIZES[:3],range(3)):
                expected_ram=bytes(mu.mem_read(base,size))
                for path,lib,storage in libs:
                    if bytes(storage[j])!=expected_ram:raise AssertionError(f'RAM {path.name}/{handler:x}/{code}')
        counts[f'0x{handler:08x}']=256;print(f'{handler:x}: passed',flush=True)
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':sum(counts.values()),'cases_by_entry':counts,'mismatches':0,'skipped':0,'seed':31,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':('Bounded/continuous mixed programs with loops, delayed calls/returns, real board FIFO stop and bank events' if a.scheduled else '47 instruction forms with real compute, board bus, delay-slot instructions and bank events')+'; synthetic storage, no machine/game binding',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sharc_*.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l,s in libs]}
    if a.scheduled:report['executed_instructions']=len(instructions)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Total:',report['cases'],'instructions:',len(instructions))
if __name__=='__main__':main()
