#!/usr/bin/env python3
"""Compound FP entries: original body, independent x87 sequence, native O0/O2."""
import argparse,ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP
from difftest_condition import ARENA,SIZE,STATUS,P32,pointer,put
from difftest_fp import EDGES,FP,snan
ENTRIES=(0x4bc310,0x4bd1a0,0x4bd220,0x4bd2a0,0x4bd440,0x4bd4b0,0x4be220)
LAYOUTS=((0x410,0x414),(0x410,0x410),(STATUS,0x414),(0x410,STATUS),(STATUS,STATUS))
def nan(x):return x&0x7fffffff>0x7f800000

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('oracle',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--triple',action='store_true');ap.add_argument('--scaled',action='store_true');args=ap.parse_args()
    if args.triple and args.scaled:ap.error('Choose one suite')
    entries=(0x4bd320,0x4bd3b0) if args.scaled else (0x4bc270,) if args.triple else ENTRIES
    layouts=((0x410,0x414,0x418),(0x410,0x410,0x410),(STATUS,0x414,0x418),(0x410,STATUS,0x418),(0x410,0x414,STATUS),(STATUS,STATUS,STATUS)) if args.triple else LAYOUTS
    outputs=3 if args.triple else 2
    rng=random.Random(18);inputs=[(a,b,EDGES[(i+7)%len(EDGES)],EDGES[(j+11)%len(EDGES)]) for i,a in enumerate(EDGES) for j,b in enumerate(EDGES)]
    inputs += [(a,b,a,b) for a in EDGES for b in EDGES]
    inputs += [tuple(rng.getrandbits(32) for _ in range(4)) for _ in range(512)]
    if args.scaled:
        inputs += [(a,e&0xffffffff,x,y) for a in EDGES for e in (-16500,-150,-31,-1,0,1,31,150,16500) for x,y in ((0,0),(0x7f7fffff,0x7f7fffff),(0x80000001,0x3f000000),(0x7f800000,0))]
    vectors=[]
    for entry in entries:
        for a,b,x,y in inputs:
            for rc in range(4):
                for layout in range(len(layouts)):
                    alias=sum((off==STATUS)<<i for i,off in enumerate(layouts[layout]))
                    vectors.append(((entry,a,b,x,y,rng.getrandbits(32),0x7f|(rc<<10),rng.choice((0,0x4500,0x4700,0x3f,0x453f)),alias),layout))
    refbin=subprocess.run([str(args.oracle.resolve())],input=b''.join(struct.pack('<8I',*v[1:]) if args.triple else struct.pack('<9I',*v) for v,l in vectors),stdout=subprocess.PIPE,check=True).stdout
    if len(refbin)!=len(vectors)*4*(outputs+3):raise AssertionError('Oracle length')
    refs=list(struct.iter_unpack('<6I' if args.triple else '<5I',refbin));mu=load_original(args.exe);mu.mem_map(ARENA,0x1000);mu.mem_write(0x5aeb40,struct.pack('<I',ARENA));mu.mem_write(0x528bc0,struct.pack('<I',ARENA+STATUS))
    libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=lib.m2_sharc_fp_triple if args.triple else lib.m2_sharc_fp_compound;fn.argtypes=[C.c_uint32]*(4 if args.triple else 5)+[P32]*(outputs+1)+[C.POINTER(FP)];fn.restype=C.c_bool;libs.append((p,fn))
    writes=[];mu.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,p,n,v,d:writes.append((p,n,v&0xffffffff,u.reg_read(UC_X86_REG_EIP))))
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}
    template=rng.randbytes(SIZE);nan_diffs=exception_diffs=c1_diffs=0
    for index,((v,li),ref) in enumerate(zip(vectors,refs)):
        entry,a,b,x,y,status,cw,sw,alias=v;first,second=layouts[li][:2];data=bytearray(template);put(data,STATUS,status)
        for off,val in zip((0x400,0x404,0x408,0x40c),(a,b,x,y)):put(data,off,val)
        fields=((0,0x400),(8,0x404),(0x10,first),(0x14,second)) if entry==0x4bc310 else ((4,0x400),(12,0x404),(28,0x408),(32,0x40c),(24,first),(16,second))
        if args.triple:fields+=((20,layouts[li][2]),)
        for field,off in fields:put(data,0x300+field,ARENA+off)
        expected=bytearray(data)
        for off,val in zip(layouts[li],ref[:outputs]):put(expected,off,val)
        put(expected,STATUS,ref[outputs])
        for p,fn in libs:
            native=(C.c_uint32*(SIZE//4)).from_buffer_copy(data);fp=FP(cw,sw)
            if not fn(*((a,b,x,y) if args.triple else (entry,a,b,x,y)),*[pointer(native,o) for o in layouts[li]],pointer(native,STATUS),C.byref(fp)):raise AssertionError('Rejected')
            if bytes(native)!=expected or (fp.control,fp.status)!=ref[outputs+1:]:
                got=(struct.unpack_from('<I',bytes(native),first)[0],struct.unpack_from('<I',bytes(native),second)[0],struct.unpack_from('<I',bytes(native),STATUS)[0],fp.control,fp.status)
                raise AssertionError(f'{p.name} #{index} {v}, layout{li}: {got}/{ref}')
        mu.mem_write(ARENA,bytes(data));mu.mem_write(SP-64,bytes(64)+struct.pack('<I',STOP))
        for r,z in preserved.items():mu.reg_write(r,z)
        for r,z in ((UC_X86_REG_ESP,SP),(UC_X86_REG_ECX,ARENA+0x300),(UC_X86_REG_FPCW,cw),(UC_X86_REG_FPSW,sw),(UC_X86_REG_FPTAG,0xffff)):mu.reg_write(r,z)
        writes.clear();mu.emu_start(entry,STOP,count=256)
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4 or mu.reg_read(UC_X86_REG_EAX):raise AssertionError('Return')
        if any(mu.reg_read(r)!=z for r,z in preserved.items()):raise AssertionError('Registers')
        if any(not(SP-64<=p and p+n<=SP or n==4 and p in tuple(ARENA+o for o in layouts[li]+(STATUS,)) or args.scaled and n==4 and p in (0x528bc4,0x528bc8,0x528bcc)) for p,n,z,ip in writes):raise AssertionError('Writes')
        stores=[z for p,n,z,ip in writes if ip in (0x4bd34b,0x4bd355,0x4bd3db,0x4bd3e5)] if args.scaled else [z for p,n,z,ip in writes if p>=ARENA][:outputs]
        if len(stores)!=outputs:raise AssertionError('Missing output stores')
        for k,(actual,want) in enumerate(zip(stores,ref[:outputs])):
            if actual!=want:
                operands=(b,a) if entry==0x4bc310 and k==0 else (a,b) if entry==0x4bc310 else (y,x) if k==0 else (a,) if entry==0x4be220 else (a,b)
                choices={n for operand in operands for n in (operand,operand|0x400000) if nan(n)}
                if entry==0x4be220 and k==1:choices={n&0x7fffffff for n in choices}
                if not any(snan(o) for o in operands) or actual not in choices or want not in choices:raise AssertionError(f'Original result #{index} {v}: {stores}/{ref[:2]}')
                nan_diffs+=1
        original_expected=bytearray(data)
        for off,value in zip(layouts[li],stores):put(original_expected,off,value)
        flagmask=5 if entry==0x4bc310 else 0x45
        if args.scaled and not alias:
            # The conversion helper sets AF/AI/AV before the final stores. Its
            # known Unicorn exception omissions may clear only AI/AV; final
            # compound comparison flags must still match the sequence exactly.
            actual_status=struct.unpack('<I',mu.mem_read(ARENA+STATUS,4))[0]
            delta=(actual_status^ref[outputs])&~0x45
            if delta&~0x22 or actual_status&delta:raise AssertionError('Scaled ASTAT exception difference')
            put(original_expected,STATUS,actual_status&~0x45)
        base=struct.unpack_from('<I',original_expected,STATUS)[0];put(original_expected,STATUS,(base&~flagmask)|(ref[outputs]&flagmask))
        if bytes(mu.mem_read(ARENA,SIZE))!=original_expected:raise AssertionError(f'Original memory #{index} {v}')
        actualsw=mu.reg_read(UC_X86_REG_FPSW)
        if mu.reg_read(UC_X86_REG_FPCW)!=cw or (actualsw^ref[outputs+2])&~0x23f:raise AssertionError(f'Original FP state #{index}: {actualsw:x}/{ref[outputs+2]:x}')
        if (actualsw^ref[outputs+2])&0x3f:
            if (actualsw&0x3f)!= (0 if args.scaled else sw&0x3f) or (not args.scaled and ref[outputs+2]&sw&0x3f!=sw&0x3f):raise AssertionError('Exception difference')
            exception_diffs+=1
        if (actualsw^ref[outputs+2])&0x200:
            if actualsw&0x200!=sw&0x200 or ref[outputs+2]&0x200:raise AssertionError('C1 difference')
            c1_diffs+=1
    root=Path(__file__).parents[1]
    report={'status':'passed','entries':[f'0x{x:08x}' for x in entries],'cases':len(vectors),'mismatches':0,'skipped':0,'seed':18,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'oracle_scope':'Full original bodies under Unicorn plus independent x87 sequences under Rosetta; no physical x86 claim',
        'bounded_unicorn_discrepancies':{'nan_outputs':nan_diffs,'exception_flags':exception_diffs,'c1_clear':c1_diffs},
        'source_sha256':hashlib.sha256((root/'sharc_fp_arithmetic.c').read_bytes()).hexdigest(),'scale_source_sha256':hashlib.sha256((root/'sharc_fp_scale.c').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'oracle_source_sha256':hashlib.sha256((root/('test/x87_triple_oracle.c' if args.triple else 'test/x87_compound_oracle.c')).read_bytes()).hexdigest(),'oracle_sha256':hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,f in libs]}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
