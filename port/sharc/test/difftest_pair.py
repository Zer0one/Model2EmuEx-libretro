#!/usr/bin/env python3
"""Original simultaneous integer sum/difference, including output/ASTAT aliases."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP)
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_integer import EDGES
from difftest_condition import ARENA,SIZE,STATUS,P32,pointer,put


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    mu=load_original(args.exe);mu.mem_map(ARENA,0x1000);mu.mem_write(0x5aeb40,struct.pack('<I',ARENA))
    libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_add_sub;fn.argtypes=[C.c_uint32,C.c_uint32,P32,P32,P32];fn.restype=C.c_uint32;libs.append((p,fn))
    writes=[];mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    rng=random.Random(12);template=rng.randbytes(SIZE);count=0
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    inputs=[(a,b) for a in EDGES for b in EDGES]+[(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(2048)]
    layouts=((0x400,0x404,0x408,0x40c),(0x400,0x404,0x408,0x408),(0x400,0x404,STATUS,0x40c),
             (0x400,0x404,0x408,STATUS),(0x400,0x404,STATUS,STATUS),(STATUS,0x404,0x400,0x404))
    for lhs,rhs in inputs:
        for layout in layouts:
            for status in (0,0xffffffff):
                data=bytearray(template);put(data,STATUS,status);put(data,layout[0],lhs);put(data,layout[1],rhs)
                lhs0,rhs0=(struct.unpack_from('<I',data,o)[0] for o in layout[:2])
                for field,off in zip((0,8,0x10,0x14),layout):put(data,0x300+field,ARENA+off)
                mu.mem_write(ARENA,bytes(data));mu.mem_write(SP-16,bytes(16)+struct.pack('<I',STOP))
                for r,v in preserved.items():mu.reg_write(r,v)
                mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_ECX,ARENA+0x300);writes.clear();mu.emu_start(0x4bc3a0,STOP,count=128)
                if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4 or mu.reg_read(UC_X86_REG_EAX)!=0:raise AssertionError('Bad return')
                if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Preserved registers')
                if any(size!=4 or addr not in {SP-4,ARENA+STATUS,ARENA+layout[2],ARENA+layout[3]} for addr,size in writes):raise AssertionError('Writes')
                expected=bytes(mu.mem_read(ARENA,SIZE))
                for p,fn in libs:
                    native=(C.c_uint32*(SIZE//4)).from_buffer_copy(data)
                    if fn(lhs0,rhs0,pointer(native,layout[2]),pointer(native,layout[3]),pointer(native,STATUS)) or bytes(native)!=expected:raise AssertionError(f'{p.name} {lhs:x}/{rhs:x}, layout{layout}')
                count+=1
    root=Path(__file__).resolve().parents[1]
    r={'status':'passed','scope':'Simultaneous sum/difference with aliases','entry':'0x004bc3a0','cases':count,'mismatches':0,'skipped':0,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':12,'source_sha256':hashlib.sha256((root/'sharc_aux.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn in libs]}
    args.output.write_text(json.dumps(r,indent=2)+'\n');print('Passed',count)


if __name__=='__main__':main()
