#!/usr/bin/env python3
"""Original state/setup/diagnostic entries with explicit CRT boundaries."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_fp import FP
ARENA=0x72000000
ENTRIES=(0x4bc0d0,0x4bc0f0,0x4bc120,0x460f20,0x4bca40,0x4bd520)
REPORT=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p,C.c_uint32)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);mu.mem_map(ARENA,0x2000)
    libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()))
        for name in ('save','restore'):
            f=getattr(lib,'m2_sharc_state_'+name);f.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t];f.restype=C.c_void_p
        lib.m2_sharc_state_address.argtypes=[C.POINTER(C.c_uint32),C.c_uint32];lib.m2_sharc_state_address.restype=C.c_uint32
        lib.m2_sharc_setup.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.POINTER(FP)];lib.m2_sharc_setup.restype=C.c_uint32
        lib.m2_sharc_bad_compute.argtypes=[C.c_uint32,C.c_uint32,REPORT,C.c_void_p];lib.m2_sharc_bad_compute.restype=C.c_uint32
        lib.m2_sharc_nop.argtypes=[];lib.m2_sharc_nop.restype=None;libs.append((path,lib))
    def r32(p):return struct.unpack('<I',mu.mem_read(p,4))[0]
    def w32(p,v):mu.mem_write(p,struct.pack('<I',v))
    calls=[];writes=[]
    def external(uc,address,size,data):
        if address not in (0x4936f0,0x4f2d80):return
        sp=uc.reg_read(UC_X86_REG_ESP);ret=r32(sp)
        if address==0x4936f0:
            dst,src,n=(r32(sp+x) for x in (4,8,12));calls.append(('copy',dst,src,n))
            uc.mem_write(dst,bytes(uc.mem_read(src,n)));uc.reg_write(UC_X86_REG_EAX,dst)
        else:
            fmt,pc=r32(sp+4),r32(sp+8);text=bytes(uc.mem_read(fmt,30)).split(b'\0')[0]
            calls.append(('report',text,pc));uc.reg_write(UC_X86_REG_EAX,0xdeadbeef)
            # The original snapshots LHS across this arbitrary caller-clobber.
            uc.reg_write(UC_X86_REG_ECX,0x1234);uc.reg_write(UC_X86_REG_EDX,0x5678)
        uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,ret)
    mu.hook_add(UC_HOOK_CODE,external)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n)))
    rng=random.Random(17);counts={}
    for entry in ENTRIES:
        for i in range(1024):
            src=rng.randbytes(0x300);dst=rng.randbytes(0x300);n=i%0x301
            if i%7==0:n=0x2a4
            pc=(0,0xffffffff,0x20004,0x20018,rng.getrandbits(32))[i%5]
            src=src[:8]+struct.pack('<I',pc)+src[12:]
            lhs=rng.getrandbits(32);ctrl=rng.getrandbits(32);alloc=rng.getrandbits(32);eax=rng.getrandbits(32)
            sw=rng.choice((0,0x4500,0x3f));cw=0x7f|((i&3)<<10)
            mu.mem_write(ARENA,src);mu.mem_write(ARENA+0x1000,dst)
            w32(0x5aeb40,ARENA);w32(0x10eded4,alloc);w32(0x528bc0,0x12345678);w32(0x528bd0,ctrl)
            mu.mem_write(SP-64,bytes(64)+struct.pack('<II',STOP,n))
            for reg,value in ((UC_X86_REG_EBX,0x11223344),(UC_X86_REG_ESI,0x55667788),(UC_X86_REG_EDI,0x12345678),(UC_X86_REG_EBP,0x87654321),(UC_X86_REG_ESP,SP),(UC_X86_REG_EAX,eax),(UC_X86_REG_ECX,lhs),(UC_X86_REG_EDX,rng.getrandbits(32)),(UC_X86_REG_FPCW,cw),(UC_X86_REG_FPSW,sw),(UC_X86_REG_FPTAG,0xffff)):
                mu.reg_write(reg,value)
            if entry==0x4bc0d0:mu.reg_write(UC_X86_REG_ECX,ARENA);mu.reg_write(UC_X86_REG_EDX,ARENA+0x1000)
            if entry==0x4bc0f0:mu.reg_write(UC_X86_REG_ECX,ARENA+0x1000);mu.reg_write(UC_X86_REG_EDX,ARENA)
            writes.clear();calls.clear();mu.emu_start(entry,STOP,count=256)
            if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+(8 if entry in ENTRIES[:2] else 4):raise AssertionError('Return')
            for reg,value in ((UC_X86_REG_EBX,0x11223344),(UC_X86_REG_ESI,0x55667788),(UC_X86_REG_EDI,0x12345678),(UC_X86_REG_EBP,0x87654321)):
                if mu.reg_read(reg)!=value:raise AssertionError('Preserved register')
            allowed={(ARENA+0x12a8,4)} if entry==0x4bc0f0 else {(0x10eded4,4)} if entry==0x4bc120 else {(0x528bc0,4),(0x528bd0,2)} if entry==0x460f20 else set()
            if any(not SP-64<=p<p+size<=SP and (p,size) not in allowed for p,size in writes):raise AssertionError('Writes')
            if bytes(mu.mem_read(ARENA,0x300))!=src:raise AssertionError('Source mutation')
            want_calls=[('copy',ARENA+0x1000,ARENA,n)] if entry in ENTRIES[:2] else [('report',b'SHARC bad compute opcode at %X',pc)] if entry==0x4bd520 else []
            if calls!=want_calls:raise AssertionError(('CRT boundary',calls,want_calls))
            for path,lib in libs:
                sb=C.create_string_buffer(src);db=C.create_string_buffer(dst);fp=FP(cw,sw)
                if entry in ENTRIES[:2]:
                    f=getattr(lib,'m2_sharc_state_'+('save' if entry==0x4bc0d0 else 'restore'))
                    if f(db,sb,n)!=C.addressof(db) or bytes(db)[:0x300]!=bytes(mu.mem_read(ARENA+0x1000,0x300)):raise AssertionError('Copy/rebind')
                    result=ARENA+0x1000
                elif entry==0x4bc120:
                    token=C.c_uint32(alloc);result=lib.m2_sharc_state_address(C.byref(token),0x10edc30)
                    if token.value!=r32(0x10eded4):raise AssertionError('Allocation')
                elif entry==0x460f20:
                    binding=C.c_uint32(0x12345678);memory=C.c_uint32(ctrl)
                    result=lib.m2_sharc_setup(lhs,eax,C.byref(binding),C.byref(memory),C.byref(fp))
                    if (binding.value,memory.value,fp.control,fp.status)!=(r32(0x528bc0),r32(0x528bd0),mu.reg_read(UC_X86_REG_FPCW)|0x40,mu.reg_read(UC_X86_REG_FPSW)):raise AssertionError('Setup')
                elif entry==0x4bd520:
                    observed=[]
                    callback=REPORT(lambda opaque,fmt,value:observed.append(('report',fmt,value)))
                    result=lib.m2_sharc_bad_compute(lhs,pc,callback,None)
                    if observed!=calls:raise AssertionError('Diagnostic')
                else:lib.m2_sharc_nop();result=eax
                if result!=mu.reg_read(UC_X86_REG_EAX):raise AssertionError('EAX')
                if entry!=0x460f20 and (mu.reg_read(UC_X86_REG_FPCW),mu.reg_read(UC_X86_REG_FPSW))!=(cw,sw):raise AssertionError('FP mutation')
        counts[f'0x{entry:08x}']=1024
    report={'status':'passed','cases':sum(counts.values()),'cases_by_entry':counts,'mismatches':0,'skipped':0,'seed':17,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'scope':'Full original helper bodies; memcpy and diagnostic output are explicit CRT callbacks; architectural CW reserved bit 6 normalized',
        'source_sha256':hashlib.sha256((Path(__file__).parents[1]/'sharc_lifecycle.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
