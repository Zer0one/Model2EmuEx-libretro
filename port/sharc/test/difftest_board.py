#!/usr/bin/env python3
"""Original Model 2B word bus and renderer skips, synthetic memory only."""
import argparse,ctypes as C,hashlib,json,random,struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
U32=C.c_uint32;P32=C.POINTER(U32);P8=C.POINTER(C.c_uint8)
class Bus(C.Structure):_fields_=[('ram0',P8),('ram1',P8),('shared',P8),('rom',P8),('input',P32),('output',P32),('astat',P32),('active',U32),('fixed',U32),('stop',U32)]
BASES=(0x72000000,0x73000000,0x74000000,0x76000000)
SIZES=(0x40000,0x40000,0x400000,0x2000000)
FIFO=0x79000000;FIXED=0x10edc30;ASTAT=FIXED+0x240

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    mu=load_original(a.exe);rng=random.Random(19);initial=[]
    for base,size in zip(BASES,SIZES):
        data=rng.randbytes(size);initial.append(data);mu.mem_map(base,size);mu.mem_write(base,data)
    mu.mem_map(FIFO,0x1000)
    for addr,val in zip((0x5aa87c,0x5aa754,0x5aa700,0x5aa8dc),BASES):mu.mem_write(addr,struct.pack('<I',val))
    for addr,val in ((0x5aa724,FIFO),(0x5aa738,FIFO+0x100)):mu.mem_write(addr,struct.pack('<I',val))
    libs=[]
    for path in a.libraries:
        lib=C.CDLL(str(path.resolve()));storage=[(C.c_uint8*len(data)).from_buffer_copy(data) for data in initial]
        lib.m2_sharc_board_read.argtypes=[C.POINTER(Bus),U32];lib.m2_sharc_board_read.restype=U32
        lib.m2_sharc_board_write.argtypes=[C.POINTER(Bus),U32,U32];lib.m2_sharc_board_write.restype=None
        lib.m2_sharc_renderer_skip.argtypes=[U32,P32];lib.m2_sharc_renderer_skip.restype=C.c_bool;libs.append((path,lib,storage))
    def r32(addr):return struct.unpack('<I',mu.mem_read(addr,4))[0]
    def w32(addr,val):mu.mem_write(addr,struct.pack('<I',val))
    writes=[];mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n)))
    preserved={UC_X86_REG_EBX:0x11223344,UC_X86_REG_ESI:0x55667788,UC_X86_REG_EDI:0x12345678,UC_X86_REG_EBP:0x87654321}
    cases=[((hi<<16)|rng.getrandbits(16),i%32,(0,1,31,32,0xffffffff)[i%5]) for i,hi in enumerate(range(65536))]
    cases += [((hi<<16)|lo,lo&31,31) for hi in (2,3,4,5,6,0x40,0xc0,0x140,0x1bf,0x1c0,0x23f,0x240) for lo in (0,1,2,0x7fff,0x8000,0xfffe,0xffff)]
    cases += [((hi<<16)|0x1234,index,count) for hi in (0x40,0xc0) for index in range(32) for count in tuple(range(33))+(0xffffffff,)]
    counts={}
    def compare_storage():
        for base,size,j in zip(BASES[:3],SIZES[:3],range(3)):
            expected=bytes(mu.mem_read(base,size))
            for path,lib,storage in libs:
                if bytes(storage[j])!=expected:raise AssertionError(f'{path.name} RAM mutation')
    for entry in (0x4c6100,0x4c6020):
        for i,(address,index,free) in enumerate(cases):
            fifos=[rng.getrandbits(32) for _ in range(70)];fifos[32]=fifos[68]=index;fifos[33]=fifos[67]=index;fifos[34]=fifos[69]=free
            first=struct.pack('<35I',*fifos[:35]);second=struct.pack('<35I',*fifos[35:]);mu.mem_write(FIFO,first);mu.mem_write(FIFO+0x100,second)
            status=rng.getrandbits(32);active=0x7a000000;stop=rng.getrandbits(32);value=rng.getrandbits(32)
            w32(ASTAT,status);w32(0x5aeb40,active);w32(0x10ed950,stop);mu.mem_write(SP,struct.pack('<I',STOP))
            for reg,val in preserved.items():mu.reg_write(reg,val)
            for reg,val in ((UC_X86_REG_ECX,address),(UC_X86_REG_EDX,value),(UC_X86_REG_ESP,SP)):mu.reg_write(reg,val)
            writes.clear();mu.emu_start(entry,STOP,count=128)
            if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Return')
            if any(mu.reg_read(r)!=v for r,v in preserved.items()):raise AssertionError('Registers')
            if any(not(any(base<=p and p+n<=base+size for base,size in zip(BASES[:3],SIZES[:3])) or FIFO<=p and p+n<=FIFO+0x18c or n==4 and p in (ASTAT,0x5aeb40,0x10ed950)) for p,n in writes):raise AssertionError('Writes')
            for path,lib,storage in libs:
                f0=(U32*35).from_buffer_copy(first);f1=(U32*35).from_buffer_copy(second);astat=U32(status)
                bus=Bus(*storage,f0,f1,C.pointer(astat),active,FIXED,stop)
                if entry==0x4c6100:
                    if lib.m2_sharc_board_read(C.byref(bus),address)!=mu.reg_read(UC_X86_REG_EAX):raise AssertionError(f'Read {address:x}')
                else:lib.m2_sharc_board_write(C.byref(bus),address,value)
                if bytes(f0)!=bytes(mu.mem_read(FIFO,140)) or bytes(f1)!=bytes(mu.mem_read(FIFO+0x100,140)) or (astat.value,bus.active,bus.stop)!=(r32(ASTAT),r32(0x5aeb40),r32(0x10ed950)):raise AssertionError(f'FIFO/state {address:x}/{index}/{free}')
            if i%1024==0:compare_storage()
        compare_storage();counts[f'0x{entry:08x}']=len(cases)
    for entry in (0x4b93d0,0x4b9470,0x4b9480):
        for value in (0,1,0xfffffffc,0xfffffffd,0xffffffff)+tuple(rng.getrandbits(32) for _ in range(1024)):
            w32(0x1003018,value);mu.reg_write(UC_X86_REG_ESP,SP);mu.mem_write(SP,struct.pack('<I',STOP));writes.clear();mu.emu_start(entry,STOP,count=8)
            if mu.reg_read(UC_X86_REG_EIP)!=STOP or writes!=[(0x1003018,4)]:raise AssertionError('Skip boundary')
            for path,lib,storage in libs:
                cursor=U32(value)
                if not lib.m2_sharc_renderer_skip(entry,C.byref(cursor)) or cursor.value!=r32(0x1003018):raise AssertionError('Skip')
        counts[f'0x{entry:08x}']=1029
    report={'status':'passed','cases':sum(counts.values()),'cases_by_entry':counts,'mismatches':0,'skipped':0,'seed':19,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'scope':'Full original bus and stream-skip entries, synthetic RAM/ROM/FIFO; no games',
        'source_sha256':hashlib.sha256((Path(__file__).parents[1]/'sharc_board.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,l,s in libs]}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
