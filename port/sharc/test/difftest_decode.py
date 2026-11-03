#!/usr/bin/env python3
"""Whole original compute decoder, including compound and invalid selectors."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
BASE=0x72000000
RECORD=BASE+0x400
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    mu=load_original(args.exe);mu.mem_map(BASE,0x1000)
    mu.mem_write(0x5aeb40,struct.pack('<I',BASE));mu.mem_write(0x5aeb10,struct.pack('<I',RECORD))
    rng=random.Random(14);libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_decode_compute;fn.argtypes=[C.c_uint32]*4+[C.POINTER(C.c_uint32)];fn.restype=None;libs.append((p,fn))
    # Every 11-bit selector, every immediate-mode selector, all 12-bit register
    # combinations for representative paths, and full-width extension garbage.
    cases=[((op<<12)|reg,ext) for op in range(2048) for reg in (0,0xfff,0x5a3,0xc69) for ext in (0,1,2,3)]
    cases += [((op<<12)|regs,0) for op in (0,1,0xa,0x70,0xf0,0x220,0x400,0x410,0x580,0x700) for regs in range(4096)]
    cases += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(4096)]
    writes=[];mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0xabcdef01,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    paths={}
    for instruction,ext in cases:
        data=rng.randbytes(0x800);mu.mem_write(BASE,data);mu.mem_write(SP-128,bytes(128)+struct.pack('<2I',STOP,instruction))
        for r,v in preserved.items():mu.reg_write(r,v)
        mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_ECX,ext);mu.reg_write(UC_X86_REG_EFLAGS,2);writes.clear();mu.emu_start(0x4be800,STOP,count=1024)
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+8:raise AssertionError('Return')
        if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Register clobber')
        if any(not(SP-128<=addr and addr+size<=SP+8 or RECORD<=addr and addr+size<=RECORD+108) for addr,size in writes):raise AssertionError('Writes')
        expected=bytes(mu.mem_read(RECORD,108));actual=bytes(mu.mem_read(BASE,0x800))
        if actual[:0x400]!=data[:0x400] or actual[0x46c:]!=data[0x46c:]:raise AssertionError('Arena clobber')
        handler=struct.unpack_from('<I',expected,4)[0];paths[f'0x{handler:08x}']=paths.get(f'0x{handler:08x}',0)+1
        for p,fn in libs:
            rec=(C.c_uint32*27).from_buffer_copy(data[0x400:0x46c]);fn(instruction,ext,BASE,RECORD,rec)
            if bytes(rec)!=expected:
                differences=[(i*4,hex(rec[i]),hex(x)) for i,x in enumerate(struct.unpack('<27I',expected)) if rec[i]!=x]
                raise AssertionError(f'{p.name} instruction={instruction:08x} extension={ext:08x}: {differences}')
    root=Path(__file__).resolve().parents[1]
    report={'status':'passed','entry':'0x004be800','cases':len(cases),'mismatches':0,'skipped':0,'seed':14,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'selected_handlers':paths,
        'source_sha256':hashlib.sha256((root/'sharc_decode.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn in libs]}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Passed',len(cases),'cases;',len(paths),'selected handlers')
if __name__=='__main__':main()
