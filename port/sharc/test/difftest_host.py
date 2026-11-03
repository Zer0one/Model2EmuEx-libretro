#!/usr/bin/env python3
"""Model 2B host driver bodies; explicit continuous-run/shared-renderer boundaries."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
U32=C.c_uint32;P32=C.POINTER(U32);P8=C.POINTER(C.c_uint8);CALL=C.CFUNCTYPE(None,C.c_void_p)
class Host(C.Structure):
    _fields_=[(n,P8) for n in ('program','data','shared')]+[(n,P32) for n in ('input','output','astat','stop','selected')]+[(n,U32) for n in ('fixed','program_control','program_offset','data_control','data_offset','shared_write','reg_801008','reg_803008')]+[('opaque',C.c_void_p),('run',CALL),('render',CALL)]
FIELDS={'program_control':0x10ed8cc,'program_offset':0x10ed8d0,'data_control':0x10ed8d4,'data_offset':0x10ed8d8,'shared_write':0x5aa758,'reg_801008':0x5aa720,'reg_803008':0x5aa870}
ASTAT=0x10ede70;STOP_FLAG=0x10ed950;SELECTED=0x5aeb40;FIXED=0x10edc30
PROGRAM=0x72000000;DATA=0x73000000;SHARED=0x74000000;FIFO=0x75000000
ENTRIES=(0x4c5e30,0x4c5e90,0x4c5ea0,0x4c5eb0,0x4c5f70,0x4c5fb0,0x4c5fc0,0x4c5ff0,0x4c6000,0x4c6010,0x4c6220,0x4c6310,0x4c6340,0x4c63a0,0x4c6400,0x4c6460)
READ_MASK={0x4c5fc0:0xffffffff,0x4c5ff0:0xffff,0x4c6000:0xff,0x4c6340:0xffffffff,0x4c63a0:0xffff,0x4c6400:0xff}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);rng=random.Random(37);initial=[]
    for base,size in ((PROGRAM,0x1000),(DATA,0x1000),(SHARED,0x81000)):
        data=rng.randbytes(size);initial.append(data);mu.mem_map(base,size);mu.mem_write(base,data)
    mu.mem_map(FIFO,0x1000)
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    def w32(addr,value):mu.mem_write(addr,struct.pack('<I',value))
    for addr,v in ((0x5aa87c,PROGRAM),(0x5aa8b0,DATA),(0x5aa700,SHARED),(0x5aa724,FIFO),(0x5aa738,FIFO+0x100)):w32(addr,v)
    trace=[]
    def boundary(uc,address,size,opaque):
        if address not in (0x4be000,0x4baa60):return
        if address==0x4be000:
            trace.append(('run',r32(ASTAT),r32(STOP_FLAG),r32(SELECTED),bytes(mu.mem_read(FIFO,140)),bytes(mu.mem_read(FIFO+0x100,140))))
            w32(ASTAT,r32(ASTAT)^0x13579bdf);w32(STOP_FLAG,9);w32(SELECTED,0x78000000);w32(FIFO+0x100,r32(FIFO+0x100)^0xffffffff)
        else:trace.append(('render',))
        sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EIP,r32(sp));uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EAX,0x11223344)
    mu.hook_add(unicorn.UC_HOOK_CODE,boundary);libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()));lib.m2_sharc_host_access.argtypes=[U32,C.POINTER(Host),U32,U32,P32];lib.m2_sharc_host_access.restype=C.c_bool
        storage=[(C.c_uint8*len(d)).from_buffer_copy(d) for d in initial];libs.append((path,lib,storage))
    edges=(0,1,15,16,0x3ef0,0x3fe0,0x3fef,0x3ff0,0x3fff,0x4000,0x4001,0x7fff,0x8000,0xffff)
    addresses=[hi+lo for hi in (0,0x800000,0x880000,0xff0000) for lo in edges]+[0x801008,0x802008,0x803008,0x804000,0x804fff,0x805000]
    addresses += [rng.getrandbits(32) for _ in range(128)]
    counts={}
    for entry in ENTRIES:
        for index,address in enumerate(addresses):
            for phase in range(8):
                scalar={n:rng.getrandbits(32) for n in FIELDS}
                scalar.update(program_control=0x80000000 if phase&1 else 0,program_offset=(0,1,2,0x7fd)[phase%4],data_control=0x80000000 if phase&2 else 0,data_offset=(0,1,0x7fd)[phase%3],shared_write=(0,1,0x7fffc,0x7ffff,0xffffffff,0x12345678,4,7)[phase])
                for n,addr in FIELDS.items():w32(addr,scalar[n])
                status=rng.getrandbits(32);stop=phase;selected=0x77000000;value=rng.getrandbits(32)
                w32(ASTAT,status);w32(STOP_FLAG,stop);w32(SELECTED,selected)
                fifos=[rng.getrandbits(32) for _ in range(70)]
                for start in (0,35):fifos[start+32]=index%32;fifos[start+33]=(index+phase)%32;fifos[start+34]=(0,1,31,32,0xffffffff)[phase%5]
                f0bytes=struct.pack('<35I',*fifos[:35]);f1bytes=struct.pack('<35I',*fifos[35:]);mu.mem_write(FIFO,f0bytes);mu.mem_write(FIFO+0x100,f1bytes)
                mu.mem_write(SP-64,bytes(64)+struct.pack('<I',STOP));mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_ECX,address);mu.reg_write(UC_X86_REG_EDX,value);mu.reg_write(UC_X86_REG_EAX,0xabcdef01)
                preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0x87654321,UC_X86_REG_EDI:0x11111111,UC_X86_REG_EBP:0x22222222}
                for reg,v in preserved.items():mu.reg_write(reg,v)
                trace.clear();mu.emu_start(entry,STOP,count=512)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4 or any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Original ABI return')
                expected_result=mu.reg_read(UC_X86_REG_EAX)&READ_MASK[entry] if entry in READ_MASK else 0xdeadbeef
                for path,lib,storage in libs:
                    f0=(U32*35).from_buffer_copy(f0bytes);f1=(U32*35).from_buffer_copy(f1bytes);astat=U32(status);nstop=U32(stop);nselected=U32(selected);seen=[]
                    def run(_):
                        seen.append(('run',astat.value,nstop.value,nselected.value,bytes(f0),bytes(f1)))
                        astat.value^=0x13579bdf;nstop.value=9;nselected.value=0x78000000;f1[0]^=0xffffffff
                    run_cb=CALL(run);render=CALL(lambda _:seen.append(('render',)))
                    h=Host(*storage,f0,f1,C.pointer(astat),C.pointer(nstop),C.pointer(nselected),FIXED,*(scalar[n] for n in FIELDS),None,run_cb,render);result=U32(0xdeadbeef)
                    ok=lib.m2_sharc_host_access(entry,C.byref(h),address,value,C.byref(result))
                    if not ok or result.value!=expected_result or seen!=trace or bytes(f0)!=bytes(mu.mem_read(FIFO,140)) or bytes(f1)!=bytes(mu.mem_read(FIFO+0x100,140)) or (astat.value,nstop.value,nselected.value)!=(r32(ASTAT),r32(STOP_FLAG),r32(SELECTED)) or any(getattr(h,n)!=r32(addr) for n,addr in FIELDS.items()):raise AssertionError(f'{path.name}/{entry:x}/{address:x}/{phase}: result {result.value:x}/{expected_result:x}, fields {[(n,getattr(h,n),r32(addr)) for n,addr in FIELDS.items() if getattr(h,n)!=r32(addr)]}, trace {seen==trace}')
            for base,j in ((PROGRAM,0),(DATA,1),(SHARED,2)):
                expected=bytes(mu.mem_read(base,len(initial[j])))
                for path,lib,storage in libs:
                    if bytes(storage[j])!=expected:raise AssertionError(f'Buffer {path.name}/{entry:x}/{address:x}/{j}')
        counts[f'0x{entry:08x}']=len(addresses)*8;print(f'{entry:x}: passed',flush=True)
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':sum(counts.values()),'entries':counts,'mismatches':0,'skipped':0,'seed':37,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'16 Model 2B host-driver entries; native continuous-run and shared-renderer are explicit callback boundaries; synthetic storage only',
        'source_sha256':hashlib.sha256((root/'sharc_host.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l,s in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Total:',report['cases'])
if __name__=='__main__':main()
