#!/usr/bin/env python3
"""Decode-to-compute integration, all selectors, actual original helper calls.

Finite synthetic operands isolate wiring/alias/lifecycle evidence. Detailed FP
exception/NaN qualification remains in the dual-oracle helper suites.
"""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_condition import ARENA,SIZE,STATUS,P32,pointer,put
from difftest_fp import FP
WORD=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)
DIAG=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p,C.c_uint32)
class Context(C.Structure):_fields_=[('opaque',C.c_void_p),('word',WORD),('diagnostic',DIAG)]+[(n,P32) for n in ('astat','pc','loop_count','stop','current_record')]+[('fp',C.POINTER(FP))]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);mu.mem_map(ARENA,0x1000);mu.mem_write(0x5aeb40,struct.pack('<I',ARENA));mu.mem_write(0x528bc0,struct.pack('<I',ARENA+STATUS))
    libs=[]
    for p in a.libraries:
        lib=C.CDLL(str(p.resolve()));lib.m2_sharc_decode_compute.argtypes=[C.c_uint32]*4+[P32];lib.m2_sharc_bind_condition.argtypes=[C.c_uint32,P32]
        lib.m2_sharc_dispatch_compute.argtypes=[C.POINTER(Context),C.c_bool];lib.m2_sharc_dispatch_compute.restype=C.c_bool;libs.append((p,lib))
    rng=random.Random(22);trace=[];redirect=False;writes=[]
    def diagnostic(uc,address,size,data):
        if address!=0x4f2d80:return
        sp=uc.reg_read(UC_X86_REG_ESP);fmt,pc=struct.unpack('<II',uc.mem_read(sp+4,8));trace.append((bytes(uc.mem_read(fmt,30)).split(b'\0')[0],pc))
        if redirect:uc.mem_write(0x5aeb10,struct.pack('<I',ARENA+0x500))
        uc.reg_write(UC_X86_REG_EAX,0xdeadbeef);uc.reg_write(UC_X86_REG_EIP,struct.unpack('<I',uc.mem_read(sp,4))[0]);uc.reg_write(UC_X86_REG_ESP,sp+4)
    mu.hook_add(UC_HOOK_CODE,diagnostic,begin=0x4f2d80,end=0x4f2d80)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n)))
    preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0xabcdef01,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    cases=0;helpers=set();fp_differences=0;redirects=0
    for selector in range(2048):
        for extension in (0,1,3):
            for move in (False,True):
                for condition in (30,selector&31):
                    data=bytearray(rng.randbytes(SIZE));put(data,8,0x20004);put(data,0x18,1+(selector&1));put(data,STATUS,rng.getrandbits(32))
                    # Raw small integers are finite denormals when interpreted
                    # as FP and bounded signed scale exponents when used as int.
                    for i in range(32):put(data,0xd8+4*i,1+(i&15))
                    record=(C.c_uint32*27).from_buffer_copy(data[0x300:0x36c]);instruction=(selector<<12)|rng.getrandbits(12)
                    libs[0][1].m2_sharc_decode_compute(instruction,extension,ARENA,ARENA+0x300,record)
                    libs[0][1].m2_sharc_bind_condition(condition,record);record[9]=ARENA+0x100;record[10]=ARENA+0xe0
                    data[0x300:0x36c]=bytes(record);put(data,0x500+60,ARENA+0x104);put(data,0x500+36,ARENA+0x108)
                    helpers.add(record[1]);redirect=record[1]==0x4bd520 and bool(selector&1);stop0=rng.getrandbits(32)
                    mu.mem_write(ARENA,bytes(data));mu.mem_write(0x5aeb10,struct.pack('<I',ARENA+0x300));mu.mem_write(0x10ed950,struct.pack('<I',stop0));mu.mem_write(SP-128,bytes(128)+struct.pack('<I',STOP))
                    cw=0x7f|((selector&3)<<10);sw=0x3f if selector&1 else 0
                    for r,v in preserved.items():mu.reg_write(r,v)
                    for r,v in ((UC_X86_REG_ESP,SP),(UC_X86_REG_FPCW,cw),(UC_X86_REG_FPSW,sw),(UC_X86_REG_FPTAG,0xffff)):mu.reg_write(r,v)
                    trace.clear();writes.clear();mu.emu_start(0x4bcb10 if move else 0x4bcb50,STOP,count=1024)
                    if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4 or any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Return/registers')
                    if any(not(SP-128<=p and p+n<=SP or ARENA<=p and p+n<=ARENA+SIZE or n==4 and p in (0x10ed950,0x528bc4,0x528bc8,0x528bcc)) for p,n in writes):raise AssertionError('Writes')
                    expected=bytes(mu.mem_read(ARENA,SIZE));expected_stop=struct.unpack('<I',mu.mem_read(0x10ed950,4))[0];expected_record=struct.unpack('<I',mu.mem_read(0x5aeb10,4))[0]
                    for path,lib in libs:
                        native=(C.c_uint32*(SIZE//4)).from_buffer_copy(data);stop=C.c_uint32(stop0);current=C.c_uint32(ARENA+0x300);fp=FP(cw,sw);seen=[]
                        @WORD
                        def word(opaque,token):
                            if not ARENA<=token<=ARENA+SIZE-4 or token&3:raise AssertionError(f'Bad token {token:x}')
                            return C.addressof(native)+token-ARENA
                        @DIAG
                        def report(opaque,fmt,pc):
                            seen.append((fmt,pc))
                            if redirect:current.value=ARENA+0x500
                        context=Context(None,word,report,pointer(native,STATUS),pointer(native,8),pointer(native,0x18),C.pointer(stop),C.pointer(current),C.pointer(fp))
                        if not lib.m2_sharc_dispatch_compute(C.byref(context),move):raise AssertionError(f'Rejected {selector:x}/{record[1]:x}')
                        if bytes(native)!=expected or (stop.value,current.value)!=(expected_stop,expected_record) or seen!=trace:
                            off=next((i for i,(x,y) in enumerate(zip(bytes(native),expected)) if x!=y),-1)
                            raise AssertionError(f'{path.name} selector{selector:x} ext{extension} move{move} condition{condition} helper{record[1]:x} offset{off:x}')
                        # Unit suites qualify every exception bit separately.
                        # This integration checks the x87 comparison/stack state
                        # and records the already-characterized oracle omissions.
                        actualsw=mu.reg_read(UC_X86_REG_FPSW)
                        if fp.control!=cw or (fp.status^actualsw)&~0x23f:raise AssertionError(f'FP wiring {record[1]:x}: {fp.status:x}/{actualsw:x}')
                        if fp.status!=actualsw:fp_differences+=1
                    cases+=1;redirects+=bool(trace and redirect)
    root=Path(__file__).parents[1]
    report={'status':'passed','cases':cases,'mismatches':0,'skipped':0,'seed':22,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Decode-to-compute(+move) integration, finite operands; FP exception/NaN semantics qualified in separate dual-oracle suites',
        'known_fp_oracle_differences_per_library':fp_differences,'diagnostic_record_redirects':redirects,'helper_addresses':[f'0x{x:08x}' for x in sorted(helpers)],
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sharc_*.c')},'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','libraries')},indent=2))
if __name__=='__main__':main()
