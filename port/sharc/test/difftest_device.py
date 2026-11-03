#!/usr/bin/env python3
"""Power-on, native program upload and host/FIFO execution through one device.

Only CRT allocation/memset and shared renderer boundaries are fixtures. SHARC
reset, decode, CPU, FIFO and host-driver bodies execute in the original EXE.
"""
import argparse,ctypes as C,hashlib,json,os,random,struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_execute import State,FIELDS as EXEC_FIELDS,STATE
from difftest_reset import Context,Registration
from difftest_program import Memory,FREE,ALLOC,Program
from difftest_board_init import Config,FIELDS as CONFIG_FIELDS
from difftest_board import Bus as Board,BASES,SIZES,FIFO
from difftest_host import Host,CALL,FIELDS as HOST_FIELDS,READ_MASK
from difftest_runtime import Runtime,FAIL
from difftest_memory import Bus
from difftest_compute import DIAG
from difftest_fp import FP
U32=C.c_uint32;P32=C.POINTER(U32);P8=C.POINTER(C.c_uint8)
OUTPUT=0x7a000000;DATA=0x7b000000;GAME=0x7c000000;CAPACITY=0x10000
class Device(C.Structure):
    _fields_=[('core',Context),('configuration',Config),('fp',FP),('board',Board),('host',Host),('runtime',Runtime),('bus',Bus),('memory',Memory),('queue',U32*8),('fixed',U32),('source',U32),('opaque',C.c_void_p),('diagnostic',DIAG),('failure',FAIL),('render',CALL),('registration',C.POINTER(Registration))]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);rng=random.Random(41)
    for base,size in zip(BASES,SIZES):mu.mem_map(base,size)
    for base,size in ((FIFO,0x1000),(OUTPUT,CAPACITY),(DATA,0x40000),(GAME,0x1000)):mu.mem_map(base,size)
    def w32(addr,v):mu.mem_write(addr,struct.pack('<I',v))
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    trace=[]
    def boundary(uc,addr,size,opaque):
        if addr not in (0x493a60,0x48d0f5,0x48d12f,0x4baa60):return
        sp=uc.reg_read(UC_X86_REG_ESP)
        if addr==0x493a60:
            dst,value,n=r32(sp+4),r32(sp+8),r32(sp+12)
            if (dst,value,n)!=(STATE,0,676):raise AssertionError('Memset')
            mu.mem_write(dst,bytes(n));uc.reg_write(UC_X86_REG_EAX,dst)
        elif addr==0x4baa60:trace.append(('render',))
        else:
            value=r32(sp+4);trace.append(('allocate' if addr==0x48d12f else 'free',value))
            if addr==0x48d12f:
                if value>CAPACITY:raise AssertionError('Allocation capacity')
                uc.reg_write(UC_X86_REG_EAX,OUTPUT)
        uc.reg_write(UC_X86_REG_EIP,r32(sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
    mu.hook_add(unicorn.UC_HOOK_CODE,boundary);libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()))
        lib.m2_sharc_device_bind.argtypes=[C.POINTER(Device),U32,U32];lib.m2_sharc_device_bind.restype=None
        lib.m2_sharc_device_power_on.argtypes=[C.POINTER(Device),C.c_char_p,C.POINTER(Registration)];lib.m2_sharc_device_power_on.restype=None
        lib.m2_sharc_device_upload_complete.argtypes=[C.POINTER(Device)];lib.m2_sharc_device_upload_complete.restype=None
        lib.m2_sharc_device_host_access.argtypes=[C.POINTER(Device),U32,U32,U32,P32];lib.m2_sharc_device_host_access.restype=C.c_bool
        libs.append((path,lib))
    cases=0;scenarios=0
    for game in ('schamp','sfight','gunblade','fvip','von','lastb','zerogun','dyn','sgt','indy','unknown'):
        for variant in range(4):
            storage=[(C.c_uint8*size)() for size in SIZES];upload=(C.c_uint8*0x40000)();decoded=(U32*(CAPACITY//4)).from_buffer_copy(rng.randbytes(CAPACITY))
            f0=(U32*35)();f1=(U32*35)();f0[34]=f1[34]=32
            core=Context();core.selected_state=STATE
            config=Config.from_buffer_copy(rng.randbytes(C.sizeof(Config)));config.astat=0;config.stop=0;config.selected_state=STATE;config.read_binding=config.write_binding=0
            fp=FP(0x37f,0x200 if variant&1 else 0)
            for base,buf in zip(BASES,storage):mu.mem_write(base,bytes(buf))
            mu.mem_write(DATA,bytes(upload));mu.mem_write(OUTPUT,bytes(decoded));mu.mem_write(STATE,bytes(core.execution.state));mu.mem_write(FIFO,bytes(f0));mu.mem_write(FIFO+0x100,bytes(f1));mu.mem_write(GAME,game.encode()+b'\0')
            for name,addr in EXEC_FIELDS.items():w32(addr,getattr(core.execution,name))
            for name,addr in CONFIG_FIELDS.items():w32(addr,getattr(config,name))
            for addr in HOST_FIELDS.values():w32(addr,0)
            for addr,value in zip((0x5aa87c,0x5aa754,0x5aa700,0x5aa8dc),BASES):w32(addr,value)
            for addr,value in ((0x5aa8b0,DATA),(0x5aa724,FIFO),(0x5aa738,FIFO+0x100),(0x10eded4,0),(0x10edee0,0),(0x5aeb08,0),(0x5aeb34,0),(0x594b40,0)):w32(addr,value)
            mu.mem_write(0x5aeb14,bytes(32));mu.reg_write(UC_X86_REG_FPCW,fp.control);mu.reg_write(UC_X86_REG_FPSW,fp.status);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
            natives=[]
            for path,lib in libs:
                d=Device();d.core=Context.from_buffer_copy(bytes(core));d.configuration=Config.from_buffer_copy(bytes(config));d.fp=FP.from_buffer_copy(bytes(fp))
                ns=[(C.c_uint8*len(b)).from_buffer_copy(bytes(b)) for b in storage];nd=(C.c_uint8*len(upload))();np=(U32*(CAPACITY//4)).from_buffer_copy(bytes(decoded));nf0=(U32*35).from_buffer_copy(bytes(f0));nf1=(U32*35).from_buffer_copy(bytes(f1));seen=[]
                d.board=Board(*ns,nf0,nf1,P32(),0,STATE,0);d.host.data=nd
                def release(_,p,token,seen=seen):seen.append(('free',token))
                def allocate(_,size,token,np=np,seen=seen):
                    if size>CAPACITY:raise AssertionError('Allocation')
                    seen.append(('allocate',size));token[0]=OUTPUT;return C.addressof(np)
                free=FREE(release);alloc=ALLOC(allocate);d.memory=Memory(None,free,alloc)
                diag=DIAG(lambda *args:os._exit(2))
                def fatal(_,entry,record):os.write(2,f'Device failure {entry:x}/{record:x}\n'.encode());os._exit(1)
                failure=FAIL(fatal);render=CALL(lambda _,seen=seen:seen.append(('render',)))
                d.diagnostic=diag;d.failure=failure;d.render=render;lib.m2_sharc_device_bind(C.byref(d),STATE,BASES[0])
                natives.append((path,lib,d,ns,nd,np,nf0,nf1,seen,(free,alloc,diag,failure,render)))
            # Source instruction 4 reads input, 5 emits output, 6 reads again,
            # 7 branches back. Commands after stop exercise saved-PC resumption.
            source=bytes(24)+struct.pack('<IH',0x400000,0x1000)+struct.pack('<IH',0xc00000,0x1100)+struct.pack('<IH',0x400000,0x1001)+struct.pack('<IH',0x20004,0x063c)
            operations=[('power',0x4c6510,0,0),('begin',0,0,0)]
            operations += [('host',0x4c6220,0x884000,struct.unpack_from('<H',source,i)[0]) for i in range(0,len(source),2)]
            operations += [('upload',0x4c6470,0,0)]
            for i in range(8):
                operations += [('host',0x4c6220,0x880000 if variant&1 else 0x884000,0x10203040+i+variant),('host',(0x4c6340,0x4c63a0,0x4c6400)[i%3],0x884000,0)]
            operations += [('host',0x4c6460,0,0)]
            for kind,entry,address,value in operations:
                trace.clear()
                for *_,seen,refs in natives:seen.clear()
                if kind=='begin':
                    w32(HOST_FIELDS['program_control'],0x80000000);w32(HOST_FIELDS['program_offset'],0)
                    for _,_,d,*_ in natives:d.host.program_control=0x80000000;d.host.program_offset=0
                    continue
                if kind=='upload':
                    # Enclosing upload-control handler calls reset before latching
                    # the new control value; latch it after the native call below.
                    pass
                mu.mem_write(SP-512,bytes(512)+struct.pack('<I',STOP));mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_ECX,GAME if kind=='power' else address);mu.reg_write(UC_X86_REG_EDX,0 if kind=='power' else value)
                mu.emu_start(entry,STOP,count=100000)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Original return')
                for path,lib,d,ns,nd,np,nf0,nf1,seen,refs in natives:
                    result=U32(0xdeadbeef)
                    if kind=='power':lib.m2_sharc_device_power_on(C.byref(d),game.encode(),None)
                    elif kind=='upload':lib.m2_sharc_device_upload_complete(C.byref(d))
                    elif not lib.m2_sharc_device_host_access(C.byref(d),entry,address,value,C.byref(result)):raise AssertionError('Host dispatch')
                    if kind=='host' and entry in READ_MASK and result.value!=mu.reg_read(UC_X86_REG_EAX)&READ_MASK[entry]:raise AssertionError('Read result')
                    if seen!=trace:raise AssertionError(f'Callbacks {seen}/{trace}')
                    if bytes(d.core.execution.state)!=bytes(mu.mem_read(STATE,676)) or any(getattr(d.core.execution,n)!=r32(addr) for n,addr in EXEC_FIELDS.items()):raise AssertionError(f'{path.name}/{game}/{variant}/{kind}/{entry:x}: execution {[n for n,addr in EXEC_FIELDS.items() if getattr(d.core.execution,n)!=r32(addr)]}')
                    if any(getattr(d.configuration,n)!=r32(addr) for n,addr in CONFIG_FIELDS.items()):raise AssertionError(f'Config {[(n,getattr(d.configuration,n),r32(addr)) for n,addr in CONFIG_FIELDS.items() if getattr(d.configuration,n)!=r32(addr)]}')
                    if any(getattr(d.host,n)!=r32(addr) for n,addr in HOST_FIELDS.items()):raise AssertionError('Host fields')
                    if bytes(np)!=bytes(mu.mem_read(OUTPUT,CAPACITY)) or bytes(nf0)!=bytes(mu.mem_read(FIFO,140)) or bytes(nf1)!=bytes(mu.mem_read(FIFO+0x100,140)):raise AssertionError('Program/FIFOs')
                    if (d.core.source_binding,d.core.source_next,d.core.selected_state,d.core.program.allocation_token,d.core.program.count)!=(r32(0x5aeb08),r32(0x5aeb34),r32(0x5aeb40),r32(0x10eded4),r32(0x10edee0)):raise AssertionError('Bindings')
                    if d.fp.control!=(mu.reg_read(UC_X86_REG_FPCW)|0x40) or (d.fp.status^mu.reg_read(UC_X86_REG_FPSW))&~0x23f:raise AssertionError('FP wiring')
                    if bytes(ns[0])!=bytes(mu.mem_read(BASES[0],SIZES[0])):raise AssertionError('Upload memory')
                if kind=='upload':
                    w32(HOST_FIELDS['program_control'],0)
                    for _,_,d,*_ in natives:d.host.program_control=0
                cases+=1
            scenarios+=1
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':cases,'scenarios':scenarios,'mismatches':0,'skipped':0,'seed':41,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Power-on through actual reset/decode, synthetic 48-bit upload, host commands, FIFO execution/resume and shared-renderer forwarding; CRT allocation/memset and renderer are explicit boundaries; no i960/game binding',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sharc_*.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','libraries')},indent=2))
if __name__=='__main__':main()
