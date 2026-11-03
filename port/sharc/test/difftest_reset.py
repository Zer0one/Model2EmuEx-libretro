#!/usr/bin/env python3
"""Native reset through real decoder, including serializer registration/failure."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_execute import State,FIELDS
from difftest_program import Program,Memory,FREE,ALLOC,U32,P32
FIXED=0x10edc30;SOURCE=0x73000000;OUTPUT=0x74000000;LIST=0x75000000;HEAD=LIST+0x100;NEXT=LIST+0x200;NODE=LIST+0x300
class Context(C.Structure):_fields_=[('execution',State),('program',Program),('source_binding',U32),('source_next',U32),('selected_state',U32)]
class Descriptor(C.Structure):_fields_=[(n,U32) for n in ('flag','state','bytes','restore','save')]+[('name',C.c_char_p)]
READ=C.CFUNCTYPE(U32,C.c_void_p,U32);WRITE=C.CFUNCTYPE(None,C.c_void_p,U32,U32);CREATE=C.CFUNCTYPE(U32,C.c_void_p,U32,U32,C.POINTER(Descriptor));FATAL=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p)
class Registration(C.Structure):_fields_=[('opaque',C.c_void_p),('list',U32),('read',READ),('write',WRITE),('create',CREATE),('fatal',FATAL)]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--upload',action='store_true');a=ap.parse_args()
    mu=load_original(a.exe)
    for addr,size in ((SOURCE,0x10000),(OUTPUT,0x40000),(LIST,0x1000)):mu.mem_map(addr,size)
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    def w32(addr,val):mu.mem_write(addr,struct.pack('<I',val))
    libs=[]
    for p in a.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_test_reset;fn.argtypes=[C.POINTER(Context),C.POINTER(C.c_uint8),U32,U32,U32,C.POINTER(Memory),C.POINTER(Registration)];fn.restype=C.c_int
        if a.upload:
            upload=lib.m2_sharc_upload_complete;upload.argtypes=[C.POINTER(Context),C.POINTER(C.c_uint8),U32,U32,U32,C.POINTER(Memory)];upload.restype=None
            def fn(ctx,src,token,length,fixed,memory,registration,upload=upload):upload(ctx,src,token,length,fixed,memory);return 0
        libs.append((p,fn))
    rng=random.Random(20);trace=[];writes=[];fatal=False;mutate=False
    def external(uc,address,size,data):
        nonlocal fatal
        if address not in (0x401050,0x4a68db,0x493a60,0x48d0f5,0x48d12f):return
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address==0x4a68db:
            message=bytes(uc.mem_read(r32(sp+4),30)).split(b'\0')[0];trace.append(('fatal',message));fatal=True;uc.emu_stop();return
        if address==0x401050:
            head,nxt=r32(sp+4),r32(sp+8);d=uc.reg_read(UC_X86_REG_ESI)
            descriptor=(uc.mem_read(d,1)[0],r32(d+8),r32(d+12),r32(d+16),r32(d+20),bytes(uc.mem_read(r32(d+4),6)).split(b'\0')[0])
            trace.append(('create',head,nxt,descriptor));w32(NODE,head);w32(NODE+4,nxt)
            if mutate:w32(0x5aeb40,0x76000000);w32(0x5aa87c,SOURCE+0x8000)
            uc.reg_write(UC_X86_REG_EAX,NODE);pop=12
        elif address==0x493a60:
            dst,value,n=r32(sp+4),r32(sp+8),r32(sp+12)
            if (dst,value,n)!=(FIXED,0,0x2a4):raise AssertionError('Memset boundary')
            uc.mem_write(dst,bytes(n));uc.reg_write(UC_X86_REG_EAX,dst);pop=4
        else:
            arg=r32(sp+4);trace.append(('free' if address==0x48d0f5 else 'allocate',arg,r32(0x10edee0),r32(FIXED+8)))
            if address==0x48d12f:uc.reg_write(UC_X86_REG_EAX,OUTPUT)
            pop=4
        uc.reg_write(UC_X86_REG_EIP,r32(sp));uc.reg_write(UC_X86_REG_ESP,sp+pop)
    mu.hook_add(UC_HOOK_CODE,external)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n)))
    cases=0;fatal_cases=0
    for n in range(256):
        registered=not a.upload and n%4!=0;count=(0,1,0xaaaaaa8,0xaaaaaa9,0xaaaaaaa,0xffffffff)[n%6];mutate=n%3==0
        length=(0,1,5,6,7,256,1024)[n%7];source=rng.randbytes(max(1,length));initial=rng.randbytes(max(4,length//6*108)+64)
        rawstate=rng.randbytes(C.sizeof(State));state=State.from_buffer_copy(rawstate);state.program_base=0xdead0000;state.current_record=0xbeef0000
        old=OUTPUT+0x30000 if n&1 else 0;selected=0x77000000
        for name,addr in FIELDS.items():w32(addr,getattr(state,name))
        mu.mem_write(FIXED,bytes(state.state));mu.mem_write(SOURCE,source);mu.mem_write(OUTPUT,initial);mu.mem_write(LIST,bytes(0x400))
        for addr,val in ((LIST,HEAD),(LIST+4,count),(HEAD+4,NEXT),(0x5aa87c,SOURCE),(0x5aeb40,selected),(0x10eded4,old),(0x10edee0,0x1234),(0x5aeb08,0x1111),(0x5aeb34,0x2222)):w32(addr,val)
        w32(0x10ed8d0,length);mu.mem_write(SP-256,bytes(256)+struct.pack('<II',STOP,length))
        preserved={UC_X86_REG_EBX:LIST if registered else 0,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0xabcdef01}
        for r,v in preserved.items():mu.reg_write(r,v)
        mu.reg_write(UC_X86_REG_ESP,SP);trace.clear();writes.clear();fatal=False;mu.emu_start(0x4c6470 if a.upload else 0x4c0230,STOP,count=100000)
        if not fatal and (mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+(4 if a.upload else 8) or any(mu.reg_read(r)!=v for r,v in preserved.items())):raise AssertionError('Return/registers')
        expected_state=State();C.memmove(C.addressof(expected_state.state),bytes(mu.mem_read(FIXED,0x2a4)),0x2a4)
        for name,addr in FIELDS.items():setattr(expected_state,name,r32(addr))
        expected_program=bytes(mu.mem_read(OUTPUT,len(initial)));expected_list=bytes(mu.mem_read(LIST,0x400))
        allowed_globals=set(FIELDS.values())|{0x5aeb08,0x5aeb34,0x10eded4,0x10edee0}
        if any(not(SP-256<=p and p+size<=SP or FIXED<=p and p+size<=FIXED+0x2a4 or OUTPUT<=p and p+size<=OUTPUT+length//6*108 or LIST<=p and p+size<=LIST+0x400 or size==4 and p in allowed_globals) for p,size in writes):raise AssertionError('Writes')
        for path,fn in libs:
            storage=(U32*((len(initial)+3)//4)).from_buffer_copy(initial+bytes((-len(initial))%4));ctx=Context(state,Program(C.cast(storage,P32),old,0x1234,state.program_base,state.current_record),0x1111,0x2222,selected)
            listdata=bytearray(0x400);struct.pack_into('<2I',listdata,0,HEAD,count);struct.pack_into('<I',listdata,0x104,NEXT);seen=[]
            @READ
            def read(opaque,address):return struct.unpack_from('<I',listdata,address-LIST)[0]
            @WRITE
            def write(opaque,address,value):struct.pack_into('<I',listdata,address-LIST,value)
            @CREATE
            def create(opaque,head,nxt,desc):
                d=desc.contents;seen.append(('create',head,nxt,(d.flag,d.state,d.bytes,d.restore,d.save,d.name)))
                write(None,NODE,head);write(None,NODE+4,nxt)
                if mutate:ctx.selected_state=0x76000000
                return NODE
            @FREE
            def release(opaque,pointer,token):seen.append(('free',token,ctx.program.count,ctx.execution.state[2]))
            @ALLOC
            def allocate(opaque,size,token):
                seen.append(('allocate',size,ctx.program.count,ctx.execution.state[2]));token[0]=OUTPUT;return C.addressof(storage)
            hooks=Memory(None,release,allocate);reg=Registration(None,LIST if registered else 0,read,write,create,FATAL())
            src=(C.c_uint8*len(source)).from_buffer_copy(source)
            result=fn(C.byref(ctx),src,SOURCE,length,FIXED,C.byref(hooks),C.byref(reg) if n&1 else (C.byref(reg) if registered else None))
            if result==1:seen.append(('fatal',b'list<T> too long'))
            if result!=int(fatal) or seen!=trace:raise AssertionError(f'Lifecycle {n}: {seen}/{trace}')
            if bytes(ctx.execution)!=bytes(expected_state) or bytes(storage)[:len(initial)]!=expected_program or bytes(listdata)!=expected_list:raise AssertionError(f'{path.name} state/program/list case{n}')
            if (ctx.source_binding,ctx.source_next,ctx.selected_state)!=(r32(0x5aeb08),r32(0x5aeb34),r32(0x5aeb40)):raise AssertionError('Source/binding')
            if (ctx.program.allocation_token,ctx.program.count,ctx.program.program_base,ctx.program.current_record)!=(r32(0x10eded4),r32(0x10edee0),r32(0x10ededc),r32(0x5aeb10)):raise AssertionError('Program metadata')
        cases+=1;fatal_cases+=fatal
    root=Path(__file__).parents[1]
    report={'status':'passed','entry':'0x004c6470' if a.upload else '0x004c0230','cases':cases,'fatal_cases':fatal_cases,'mismatches':0,'skipped':0,'seed':20,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Upload completion and real program decode; explicit CRT allocation/memset boundaries' if a.upload else 'Full reset and program decode; explicit native list-node, exception and CRT allocation/memset boundaries',
        'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('sharc_reset.c','sharc_program.c','sharc_decode.c','sharc_registers.c','sharc_bits.c','test/reset_fixture.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,f in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
