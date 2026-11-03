#!/usr/bin/env python3
"""Original board initialization, real CRT name matching, explicit reset boundary."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_fp import FP
FIELDS={'astat':0x10ede70,'selected_state':0x5aeb40,'stop':0x10ed950,'read_binding':0x10edee4,'write_binding':0x10edee8,'offset_bits':0xdcec58,'scale_bits':0x5aeb90,'mode':0x10ed974,'enabled':0x10ed95c,'variant':0x10ed978,'renderer_a8':0x5733a8,'renderer_b0':0x5733b0,'renderer_150':0x573450,'renderer_158':0x573458}
class Config(C.Structure):_fields_=[(n,C.c_uint32) for n in FIELDS]
RESET=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);mu.mem_map(0x72000000,0x1000);rng=random.Random(21);libs=[]
    for p in a.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_board_initialize;fn.argtypes=[C.POINTER(Config),C.c_char_p,C.c_uint32,C.POINTER(FP),RESET,C.c_void_p];fn.restype=None;libs.append((p,fn))
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    def w32(addr,val):mu.mem_write(addr,struct.pack('<I',val))
    calls=[];writes=[];after=None
    def hook(uc,address,size,data):
        if address!=0x4c0230:return
        sp=uc.reg_read(UC_X86_REG_ESP);calls.append((r32(sp+4),uc.reg_read(UC_X86_REG_EBX)))
        for name,addr in FIELDS.items():w32(addr,getattr(after,name))
        uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,r32(sp))
    mu.hook_add(UC_HOOK_CODE,hook,begin=0x4c0230,end=0x4c0230);mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n)))
    names=['','schamp','sfight','gunblade','fvip','von','lastb','zerogun','dyn','sgt','indy','srallyc','daytona','schampx','sfightx','gunbladex']
    names += [n[:i] for n in ('schamp','gunblade','lastb','zerogun','indy') for i in range(len(n))]
    names += [n+suffix for n in ('fvip','von','lastb','dyn','sgt','indy') for suffix in ('a','2','_test')]
    names += [''.join(chr(rng.randrange(33,127)) for _ in range(rng.randrange(1,32))) for _ in range(128)]
    cases=0
    for name in names:
        for style in range(3):
            game=(name if style==0 else name.upper() if style==1 else ''.join(c.upper() if i&1 else c for i,c in enumerate(name))).encode()
            initial=Config.from_buffer_copy(rng.randbytes(C.sizeof(Config)));after=Config.from_buffer_copy(rng.randbytes(C.sizeof(Config)));sw=rng.choice((0,0x4500,0x4700,0x3f,0x453f));cw=0x7f|((cases&3)<<10)
            for field,addr in FIELDS.items():w32(addr,getattr(initial,field))
            mu.mem_write(0x72000000,game+b'\0');mu.mem_write(SP-256,bytes(256)+struct.pack('<I',STOP));w32(0x594b40,0)
            preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0xabcdef01,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
            for r,v in preserved.items():mu.reg_write(r,v)
            for r,v in ((UC_X86_REG_ESP,SP),(UC_X86_REG_ECX,0x72000000),(UC_X86_REG_EDX,0x73000000),(UC_X86_REG_FPCW,cw),(UC_X86_REG_FPSW,sw),(UC_X86_REG_FPTAG,0xffff)):mu.reg_write(r,v)
            writes.clear();calls.clear();mu.emu_start(0x4c6510,STOP,count=10000)
            if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4 or any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Return/registers')
            if calls!=[(256,0x73000000)]:raise AssertionError('Reset boundary')
            if any(not(SP-256<=p and p+n<=SP or n==4 and p in FIELDS.values()) for p,n in writes):raise AssertionError('Writes')
            expected=Config(*(r32(addr) for addr in FIELDS.values()))
            for path,fn in libs:
                config=Config.from_buffer_copy(bytes(initial));fp=FP(cw,sw);seen=[]
                @RESET
                def reset(opaque,n):seen.append((n,0x73000000));C.memmove(C.addressof(config),C.addressof(after),C.sizeof(Config))
                fn(C.byref(config),game,0x10edc30,C.byref(fp),reset,None)
                if bytes(config)!=bytes(expected) or seen!=calls or fp.control!=cw or fp.status!=mu.reg_read(UC_X86_REG_FPSW)&~0x200:raise AssertionError(f'{path.name} {game}: configuration/FP mismatch')
            cases+=1
    root=Path(__file__).parents[1]
    report={'status':'passed','entry':'0x004c6510','cases':cases,'mismatches':0,'skipped':0,'seed':21,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'scope':'Full board-init body with original C-locale CRT comparisons; reset is an explicit separately verified boundary; known Unicorn C1 omission normalized',
        'source_sha256':hashlib.sha256((root/'sharc_board_init.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,f in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
