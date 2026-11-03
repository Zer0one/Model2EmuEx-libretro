#!/usr/bin/env python3
"""Whole original program decode with controlled CRT allocation callbacks."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
STATE=0x72000000
SOURCE=0x73000000
OUTPUT=0x74000000
CAPACITY=108*65536
U32=C.c_uint32;P32=C.POINTER(U32)
class Program(C.Structure):_fields_=[('allocation',P32),('allocation_token',U32),('count',U32),('program_base',U32),('current_record',U32)]
FREE=C.CFUNCTYPE(None,C.c_void_p,P32,U32)
ALLOC=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U32,P32)
class Memory(C.Structure):_fields_=[('opaque',C.c_void_p),('release',FREE),('allocate',ALLOC)]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    mu=load_original(args.exe);mu.mem_map(STATE,0x1000);mu.mem_map(SOURCE,0x100000);mu.mem_map(OUTPUT,CAPACITY+0x1000)
    mu.mem_write(0x5aeb40,struct.pack('<I',STATE))
    rng=random.Random(15);libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_decode_program;fn.argtypes=[C.POINTER(C.c_uint8),U32,U32,U32,C.POINTER(Program),C.POINTER(Memory)];fn.restype=None;libs.append((p,fn,lib))
    def read32(a):return struct.unpack('<I',mu.mem_read(a,4))[0]
    trace=[];allocation_bytes=0;write_count=0
    def callback(uc,address,size,data):
        if address not in (0x48d0f5,0x48d12f):return
        sp=uc.reg_read(UC_X86_REG_ESP);arg=read32(sp+4)
        trace.append(('free' if address==0x48d0f5 else 'allocate',arg,read32(0x10edee0)))
        if address==0x48d12f:
            if arg!=allocation_bytes:raise AssertionError('Allocation size')
            uc.reg_write(UC_X86_REG_EAX,OUTPUT)
        uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,read32(sp))
    mu.hook_add(UC_HOOK_CODE,callback,begin=0x48d0f5,end=0x48d12f)
    def write(uc,access,address,size,value,data):
        nonlocal write_count
        write_count+=1
        if not(SP-256<=address and address+size<=SP+12 or OUTPUT<=address and address+size<=OUTPUT+allocation_bytes or size==4 and address in (0x10edee0,0x10eded4,0x10ededc,0x5aeb10)):
            raise AssertionError(f'Unexpected write {address:x}/{size}')
    mu.hook_add(UC_HOOK_MEM_WRITE,write)
    cases=[]
    for pattern in (0,0xffffffff,None):
        for start in range(0,65536,1024):
            cases.append(b''.join(struct.pack('<IH',rng.getrandbits(32) if pattern is None else pattern,hi) for hi in range(start,start+1024)))
    cases += [rng.randbytes(n) for n in range(13)]
    cases += [b''.join(struct.pack('<IH',rng.getrandbits(32),hi) for hi in range(65536))]
    # Explicit loop-distance descriptors 1/2/default and +/-24-bit boundaries.
    cases += [b''.join(struct.pack('<IH',raw,hi) for hi in (0xc00,0xd00,0xe00,0x700) for raw in (0,1,2,3,0x7fffff,0x800000,0xffffff))]
    preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0xabcdef01,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    records=0;handlers=set()
    for n,source in enumerate(cases):
        count=len(source)//6;allocation_bytes=count*108;records+=count
        initial=rng.randbytes(max(4,allocation_bytes)+64);old=0x75000000 if n&1 else 0
        mu.mem_write(OUTPUT,initial);mu.mem_write(SOURCE,source or bytes(1));mu.mem_write(STATE,rng.randbytes(0x2a4))
        for addr,value in ((0x10edee0,0x1234),(0x10eded4,old),(0x10ededc,0xabc),(0x5aeb10,0xdef)):mu.mem_write(addr,struct.pack('<I',value))
        mu.mem_write(SP-256,bytes(256)+struct.pack('<3I',STOP,SOURCE,len(source)))
        for r,v in preserved.items():mu.reg_write(r,v)
        mu.reg_write(UC_X86_REG_ESP,SP);trace.clear();write_count=0
        mu.emu_start(0x4bf610,STOP,count=max(4096,count*512))
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+12:raise AssertionError('Return')
        if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Preserved registers')
        expected=bytes(mu.mem_read(OUTPUT,len(initial)));meta=tuple(read32(x) for x in (0x10eded4,0x10edee0,0x10ededc,0x5aeb10))
        if expected[allocation_bytes:]!=initial[allocation_bytes:]:raise AssertionError('Allocation guard')
        for off in range(0,allocation_bytes,108):handlers.add(struct.unpack_from('<I',expected,off)[0])
        for p,fn,lib in libs:
            storage=(U32*((len(initial)+3)//4)).from_buffer_copy(initial+bytes((-len(initial))%4))
            program=Program(C.cast(storage,P32),old,0x1234,0xabc,0xdef);seen=[]
            @FREE
            def release(opaque,pointer,token):seen.append(('free',token,program.count))
            @ALLOC
            def allocate(opaque,size,token):
                seen.append(('allocate',size,program.count));token[0]=OUTPUT;return C.addressof(storage)
            hooks=Memory(None,release,allocate);src=(C.c_uint8*max(1,len(source))).from_buffer_copy(source or bytes(1))
            fn(src,len(source),STATE,0x10edc30,C.byref(program),C.byref(hooks))
            actual=bytes(storage)[:len(initial)]
            if actual!=expected:
                off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);index=off//108
                raise AssertionError(f'{p.name} case{n} instruction{index} {source[index*6:index*6+6].hex()} recordbyte{off%108}: {actual[off:off+4].hex()}/{expected[off:off+4].hex()}')
            if (program.allocation_token,program.count,program.program_base,program.current_record)!=meta or seen!=trace:raise AssertionError('Lifecycle')
    # Standalone condition-binding entry has EAX input/result and masks code.
    binder_cases=0
    for code in list(range(256))+[rng.getrandbits(32) for _ in range(256)]:
        allocation_bytes=108;initial=rng.randbytes(108);mu.mem_write(OUTPUT,initial);mu.mem_write(0x5aeb10,struct.pack('<I',OUTPUT));mu.mem_write(SP,struct.pack('<I',STOP));mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EAX,code)
        mu.emu_start(0x4bc660,STOP,count=32);expected=bytes(mu.mem_read(OUTPUT,108))
        if mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Binder return')
        for p,fn,lib in libs:
            bind=lib.m2_sharc_bind_condition;bind.argtypes=[U32,P32];bind.restype=U32;r=(U32*27).from_buffer_copy(initial)
            if bind(code,r)!=mu.reg_read(UC_X86_REG_EAX) or bytes(r)!=expected:raise AssertionError('Binder')
        binder_cases+=1
    root=Path(__file__).resolve().parents[1]
    report={'status':'passed','entries':['0x004bf610','0x004bc660'],'cases':len(cases)+binder_cases,'program_calls':len(cases),'condition_binding_cases':binder_cases,'decoded_instructions':records,'mismatches':0,'skipped':0,'seed':15,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Original decoder to return with controlled CRT allocation/free; all 65536 high opcode words, full register encodings, fresh/replacement/empty/trailing inputs. Invalid opcodes preserve allocator words.',
        'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('sharc_program.c','sharc_decode.c','sharc_registers.c','sharc_bits.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn,lib in libs]}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
