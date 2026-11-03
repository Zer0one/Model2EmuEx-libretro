#!/usr/bin/env python3
"""Real memory wrappers + original board bus, synthetic storage and FIFO only.

The portable side composes the same recovered pieces. No bus-result stubs,
machine ROMs, production bindings or gameplay claims are involved.
"""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_condition import P32,pointer,put
from difftest_compute import Context,WORD,DIAG
from difftest_fp import FP
from difftest_memory import Record,Bus,READ_FN,WRITE_FN,Operation,HANDLERS
from difftest_board import Bus as Board,BASES,SIZES,FIFO,FIXED

RECORD=0x7a000000;SIZE=0x600

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);rng=random.Random(29);initial=[]
    for base,size in zip(BASES,SIZES):
        data=rng.randbytes(size);initial.append(data);mu.mem_map(base,size);mu.mem_write(base,data)
    mu.mem_map(FIFO,0x1000);mu.mem_map(RECORD,0x1000)
    def w32(addr,v):mu.mem_write(addr,struct.pack('<I',v))
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    for addr,v in zip((0x5aa87c,0x5aa754,0x5aa700,0x5aa8dc),BASES):w32(addr,v)
    for addr,v in ((0x5aa724,FIFO),(0x5aa738,FIFO+0x100),(0x5aeb3c,0x4c6100),(0x5aeb48,0x4c6020),(0x528bc0,FIXED+0x240),(0x5aeb38,RECORD)):w32(addr,v)
    conditions=struct.unpack('<32I',mu.mem_read(0x573490,128));libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()));storage=[(C.c_uint8*len(d)).from_buffer_copy(d) for d in initial]
        lib.m2_sharc_board_read.argtypes=[C.POINTER(Board),C.c_uint32];lib.m2_sharc_board_read.restype=C.c_uint32
        lib.m2_sharc_board_write.argtypes=[C.POINTER(Board),C.c_uint32,C.c_uint32];lib.m2_sharc_board_write.restype=None
        lib.m2_sharc_compute_hooks.argtypes=[C.POINTER(Context)];lib.m2_sharc_compute_hooks.restype=Operation
        lib.m2_sharc_dispatch_memory_ex.argtypes=[C.c_uint32,C.POINTER(Record),C.POINTER(Bus),C.c_uint32,C.c_uint32,P32,P32,P32,P32,C.POINTER(Operation)]
        lib.m2_sharc_dispatch_memory_ex.restype=C.c_bool;libs.append((path,lib,storage))
    cases=0;counts={}
    addresses=(0x20004,0x30004,0x40004,0x60004,0x400000,0xc00000,0x1400004,0x1c00004,0x2400000)
    # Compute writes ASTAT before the real bus; data can also alias ASTAT.
    # FIFO empty/full flags must survive or be overwritten in native order.
    for handler in HANDLERS:
        counts[f'0x{handler:08x}']=0
        for address in addresses:
            for phase in range(24):
                state=bytearray(rng.randbytes(SIZE));record=bytearray(108)
                code=(0,9,16,30)[phase%4];entry=(0x460f40,0x4615e0,0x4613e0,0x461700)[phase%4]
                status=(0,0xffffffff,0x180000,1)[phase%4];free=(0,1,31,32,0xffffffff,2)[phase%6]
                put(state,0x240,status);put(state,8,0x20000);put(state,0x18,phase%3)
                offsets=(0x400,0x404,0x408,0x40c,0x240 if phase&4 else 0x500,0x504,0x510,0x514,0x518)
                for off,value in ((0x400,address),(0x404,addresses[(addresses.index(address)+phase)%len(addresses)]),(0x408,0),(0x40c,0),(0x510,0x3f800000),(0x514,0x40000000)):put(state,off,value)
                put(record,4,entry);put(record,8,conditions[code]);put(record,0x1c,0x20004);put(record,0x2c,phase%4)
                for field,off in zip((0xc,0x14,0x10,0x18,0x24,0x28,0x34,0x38,0x3c),offsets):put(record,field,FIXED+off)
                fifos=[rng.getrandbits(32) for _ in range(70)]
                for start in (0,35):fifos[start+32]=(phase*7)&31;fifos[start+33]=(phase*11)&31;fifos[start+34]=free
                f0bytes=struct.pack('<35I',*fifos[:35]);f1bytes=struct.pack('<35I',*fifos[35:])
                mu.mem_write(FIXED,bytes(state));mu.mem_write(RECORD,bytes(record));mu.mem_write(FIFO,f0bytes);mu.mem_write(FIFO+0x100,f1bytes)
                w32(0x5aeb40,FIXED);w32(0x5aeb10,RECORD);w32(0x10ed950,0)
                mu.mem_write(SP-256,bytes(256)+struct.pack('<I',STOP));mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,0x8c7)
                mu.reg_write(UC_X86_REG_FPCW,0x7f);mu.reg_write(UC_X86_REG_FPSW,0);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
                mu.emu_start(handler,STOP,count=1024)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Original return')
                expected=bytes(mu.mem_read(FIXED,SIZE));ef0=bytes(mu.mem_read(FIFO,140));ef1=bytes(mu.mem_read(FIFO+0x100,140))
                for path,lib,storage in libs:
                    native=(C.c_uint32*(SIZE//4)).from_buffer_copy(state);f0=(C.c_uint32*35).from_buffer_copy(f0bytes);f1=(C.c_uint32*35).from_buffer_copy(f1bytes)
                    stop=C.c_uint32(0);offset=C.c_uint32(0);token=C.c_uint32(RECORD);fp=FP(0x7f,0)
                    board=Board(*storage,f0,f1,pointer(native,0x240),FIXED,FIXED,0)
                    def read(_,addr):
                        board.stop=stop.value;value=lib.m2_sharc_board_read(C.byref(board),addr);stop.value=board.stop;return value
                    def write(_,addr,value):
                        board.stop=stop.value;lib.m2_sharc_board_write(C.byref(board),addr,value);stop.value=board.stop
                    rd=READ_FN(read);wr=WRITE_FN(write);bus=Bus(rd,wr,None)
                    rec=Record(code,entry,0x20004,phase%4)
                    for field,offs in (('address',offsets[:2]),('step',offsets[2:4]),('data',offsets[4:6]),('mirror',(offsets[4]-128,offsets[5]-128))):setattr(rec,field,(P32*2)(*(pointer(native,o) for o in offs)))
                    rec.lhs,rec.rhs,rec.destination=(pointer(native,o) for o in offsets[6:])
                    word=WORD(lambda opaque,t:C.addressof(native)+t-FIXED);diag=DIAG(lambda *args:None)
                    context=Context(None,word,diag,pointer(native,0x240),pointer(native,8),pointer(native,0x18),C.pointer(stop),C.pointer(token),C.pointer(fp))
                    ops=lib.m2_sharc_compute_hooks(C.byref(context))
                    ok=lib.m2_sharc_dispatch_memory_ex(handler,C.byref(rec),C.byref(bus),0x8c7,phase%3,pointer(native,0x240),C.byref(stop),pointer(native,8),C.byref(offset),C.byref(ops))
                    if not ok or bytes(native)!=expected or bytes(f0)!=ef0 or bytes(f1)!=ef1 or stop.value!=r32(0x10ed950) or board.active!=r32(0x5aeb40) or offset.value!=(r32(0x5aeb10)-RECORD)&0xffffffff:
                        diffs=[hex(i) for i in range(0,SIZE,4) if bytes(native)[i:i+4]!=expected[i:i+4]]
                        raise AssertionError(f'{path.name} {handler:x}/{address:x}/{phase}: {diffs}, stop {stop.value}/{r32(0x10ed950)}')
                    if (fp.status^mu.reg_read(UC_X86_REG_FPSW))&~0x23f:raise AssertionError('FP comparison/stack')
                cases+=1;counts[f'0x{handler:08x}']+=1
            # Compare full RAM after every address batch, including cross-view writes.
            for base,size,j in zip(BASES[:3],SIZES[:3],range(3)):
                expected_ram=bytes(mu.mem_read(base,size))
                for path,lib,storage in libs:
                    if bytes(storage[j])!=expected_ram:raise AssertionError(f'{path.name} RAM mismatch {handler:x}/{address:x}')
        print(f'{handler:x}: passed',flush=True)
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':cases,'cases_by_entry':counts,'mismatches':0,'skipped':0,'seed':29,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'17 memory wrappers with real recovered compute and board bus; fixed selected state, synthetic RAM/ROM/FIFOs, no scheduler or game binding',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sharc_*.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l,s in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Total:',cases)
if __name__=='__main__':main()
