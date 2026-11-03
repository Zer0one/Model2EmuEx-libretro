#!/usr/bin/env python3
"""Full original x86 helper execution plus independent x87 sequence evidence.

Unicorn 2.1.4 omits x87 exception accumulation and SNaN quieting. We assert
exactly those bounded differences, not arbitrary mismatches, and compare full
portable outputs against a separately compiled x87 sequence run under Rosetta.
This is not physical-x86 qualification or production DSP integration.
"""
import argparse,ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from difftest_bits import load_original,EXE_SHA256,STOP,SP

ENTRIES=(0x4bc130,0x4bc170,0x4bc1b0,0x4bc210,0x4be1d0,0x461ae0,0x461b80,0x461c20,0x461cc0,0x461a40,0x461f60,0x462200)
FLAG_UNARY=(0x461ae0,0x461b80,0x461c20,0x461cc0,0x461a40,0x461f60,0x462200)
ARITHMETIC=(0x461700,0x4617a0,0x461840,0x4618e0,0x461980,0x462700,0x462340,0x4623e0)
SCALING=(0x461d60,0x462000,0x462140,0x4622a0)
ARENA=0x72000000
EDGES=(0,0x80000000,1,0x80000001,0x7fffff,0x807fffff,0x800000,0x80800000,
       0x3f000000,0x3f7fffff,0x3f800000,0xbf800000,0x3fc00000,0xbfc00000,
       0x4f000000,0xcf000000,0x4f800000,0x5effffff,0x5f000000,0xdf000000,
       0xdf000001,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,
       0x7fc00000,0xffc12345,0x7f800001,0xff812345)
class FP(C.Structure):_fields_=[('control',C.c_uint16),('status',C.c_uint16)]
def snan(x):return x&0x7fffffff>0x7f800000 and not x&0x400000

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('oracle',type=Path);ap.add_argument('libraries',type=Path,nargs='+');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--arithmetic',action='store_true');ap.add_argument('--scaling',action='store_true');args=ap.parse_args()
    if args.arithmetic and args.scaling:ap.error('Select only one suite')
    entries=SCALING if args.scaling else ARITHMETIC if args.arithmetic else ENTRIES
    flags_helpers=FLAG_UNARY+ARITHMETIC+SCALING
    rng=random.Random(13);vectors=[]
    inputs=[(a,b) for a in EDGES for b in EDGES]+[(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(2048)]
    if args.arithmetic:
        inputs += [(a,b) for a in (0x3f800000,0x3f800001,0x00800000,0x00800001,0x7f7fffff,0x80000001)
                   for b in (0x33800000,0xb3800000,0x3f7fffff,0x3f800001,0xbf800000,0x3f000000)]
    if args.scaling:
        exponents=(0,1,2,23,24,31,32,126,127,128,149,150,255,16382,16383,16445,16446,16500,2147483647,-2147483648)
        inputs=[(a,b&0xffffffff) for a in EDGES+(0x7fffffff,0x80000000,0xffffffff) for b in exponents+tuple(-x for x in exponents if x>0)] + inputs
    for entry in entries:
        for a,b in inputs:
            for rounding in range(4):
                # Architectural FNSTCW has reserved bit 6 set. The scheduler's
                # memory constant 0x003f becomes 0x007f after FLDCW/FNSTCW.
                cw=0x7f|(rounding<<10)|(0 if args.arithmetic or args.scaling else ((0,2,3,0)[rounding]<<8))
                sw=rng.choice((0,0x4500,0x4700,0x3f,0x453f))
                vectors.append((entry,a,b,rng.getrandbits(32),cw,sw))
    binary=b''.join(struct.pack('<6I',*v) for v in vectors)
    native=subprocess.run([str(args.oracle.resolve())],input=binary,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    if len(native.stdout)!=len(vectors)*16:raise AssertionError(native.stderr)
    expected=list(struct.iter_unpack('<4I',native.stdout))
    mu=load_original(args.exe);mu.mem_map(ARENA,0x1000);mu.mem_write(0x5aeb40,struct.pack('<I',ARENA))
    mu.mem_write(0x528bc0,struct.pack('<I',ARENA+0x240))
    libs=[]
    for p in args.libraries:
        lib=C.CDLL(str(p.resolve()));fn=getattr(lib,'m2_sharc_fp_scale' if args.scaling else 'm2_sharc_fp_arithmetic' if args.arithmetic else 'm2_sharc_fp_simple');fn.argtypes=[C.c_uint32]*3+[C.POINTER(C.c_uint32),C.POINTER(FP),C.POINTER(C.c_uint32)];fn.restype=C.c_bool;libs.append((p,fn))
    writes=[];mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,size,v,u:writes.append((addr,size)))
    preserved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0x87654321,UC_X86_REG_EDI:0xabcdef01,UC_X86_REG_EBP:0x5a5a5a5a}
    quiet_differences=0;exception_differences=0;c1_differences=0;astat_differences=0;nan_selection_differences=0;scale_tiny_differences=0
    for i,(v,ref) in enumerate(zip(vectors,expected)):
        entry,a,b,status,cw,sw=v
        for r,x in preserved.items():mu.reg_write(r,x)
        mu.reg_write(UC_X86_REG_ECX,a);mu.reg_write(UC_X86_REG_EDX,b);mu.reg_write(UC_X86_REG_ESP,SP)
        mu.reg_write(UC_X86_REG_FPCW,cw);mu.reg_write(UC_X86_REG_FPSW,sw);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
        mu.mem_write(SP-64,bytes(64)+struct.pack('<I',STOP));mu.mem_write(ARENA+0x240,struct.pack('<I',status));writes.clear();mu.emu_start(entry,STOP,count=256)
        actual=(mu.reg_read(UC_X86_REG_EAX),struct.unpack('<I',mu.mem_read(ARENA+0x240,4))[0],mu.reg_read(UC_X86_REG_FPCW),mu.reg_read(UC_X86_REG_FPSW))
        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:raise AssertionError('Return')
        if any(mu.reg_read(r)!=x for r,x in preserved.items()):raise AssertionError('Register clobber')
        if any(not(SP-64<=addr and addr+size<=SP or (entry==0x4bc1b0 or entry in flags_helpers) and addr==ARENA+0x240 and size==4 or entry in flags_helpers and addr in (0x528bc4,0x528bc8,0x528bcc) and size==4) for addr,size in writes):raise AssertionError('Writes')
        if actual[0]!=ref[0]:
            if snan(actual[0]) and actual[0]|0x400000==ref[0]:quiet_differences+=1
            elif entry in ARITHMETIC and (snan(a) or snan(b)) and actual[0]&0x7fffffff>0x7f800000 and ref[0]&0x7fffffff>0x7f800000:
                # Missing FLD quieting changes which NaN wins the subsequent
                # memory arithmetic. Both outputs must be operand NaNs, with
                # only the known quiet-bit/FABS transformations allowed.
                choices={x for operand in (a,b) for x in (operand,operand|0x400000) if x&0x7fffffff>0x7f800000}
                if entry in (0x461840,0x4618e0):choices={x&0x7fffffff for x in choices}
                if actual[0] not in choices or ref[0] not in choices:raise AssertionError('Unbounded NaN selection difference')
                nan_selection_differences+=1
            else:raise AssertionError(f'Original output #{i} {v}: {actual}/{ref}')
        if actual[1]!=ref[1]:
            missing_invalid=(a&0x7fffffff>0x7f800000 or b&0x7fffffff>0x7f800000) if entry==0x461a40 else snan(a)
            mask=0x200 if entry==0x462700 else 0x20
            if entry in ARITHMETIC:
                missing_invalid=snan(a) or snan(b) or ((a&0x7fffffff)==0x7f800000 and (b&0x7fffffff)==0x7f800000 and bool((a^b)&0x80000000)!=(entry in (0x4617a0,0x4618e0))) or (entry==0x462700 and ((a&0x7fffffff)==0x7f800000 and (b&0x7fffffff)==0 or (b&0x7fffffff)==0x7f800000 and (a&0x7fffffff)==0))
                if entry in (0x462340,0x4623e0):missing_invalid=snan(a) or (entry==0x4623e0 and bool(a&0x80000000) and 0<(a&0x7fffffff)<=0x7f800000)
            permitted=mask if missing_invalid and not sw&1 else 0
            if entry in SCALING:
                scale=b if b<0x80000000 else b-0x100000000
                magnitude=(0x100000000-a if a&0x80000000 else a) if entry==0x4622a0 else ((a&0x7fffff)|0x800000 if (a>>23)&255 else a&0x7fffff)
                power=0 if entry==0x4622a0 else (((a>>23)&255)-150 if (a>>23)&255 else -149)
                finite=entry==0x4622a0 or a&0x7fffffff<0x7f800000
                if finite and magnitude and power+magnitude.bit_length()-1+scale>16383 and not sw&8:permitted|=2
            tiny_difference=False
            if entry in SCALING and finite and magnitude and power+magnitude.bit_length()-1+scale<-16382:
                # Unicorn FSCALE loses extended subnormals before FTST. Allow
                # only zero-vs-signed-tiny compare bits in this narrow domain;
                # final values and the native sequence comparison stay exact.
                if actual[1]&5==1 and ref[1]&5==(4 if a&0x80000000 else 0):
                    tiny_difference=True;scale_tiny_differences+=1
            delta=(actual[1]^ref[1])&(~5 if tiny_difference else 0xffffffff)
            if entry not in flags_helpers or delta&~permitted or actual[1]&delta:raise AssertionError(f'ASTAT #{i} {v}: {actual}/{ref}')
            astat_differences+=1
        if actual[2]!=ref[2] or (actual[3]^ref[3])&~(0x433f if entry in SCALING and actual[1]!=ref[1] and tiny_difference else 0x23f):raise AssertionError(f'Original state #{i} {v}: {actual}/{ref}')
        if (actual[3]^ref[3])&0x200:
            if entry in flags_helpers:
                if actual[3]&0x200!=sw&0x200:raise AssertionError('Unexpected C1 difference')
            elif actual[3]&0x200!=sw&0x200 or ref[3]&0x200:raise AssertionError('Unexpected C1 difference')
            c1_differences+=1
        if (actual[3]^ref[3])&0x3f:
            # Known oracle omission must preserve incoming exceptions exactly;
            # the instruction-sequence reference can only accumulate them.
            if entry in flags_helpers:
                if actual[3]&0x3f:raise AssertionError('Unexpected x87 exception difference after FNCLEX')
            elif actual[3]&0x3f!=sw&0x3f or ref[3]&sw&0x3f!=sw&0x3f:raise AssertionError('Unexpected x87 exception difference')
            exception_differences+=1
        for p,fn in libs:
            st=C.c_uint32(status);fp=FP(cw,sw);result=C.c_uint32()
            if not fn(entry,a,b,C.byref(st),C.byref(fp),C.byref(result)):raise AssertionError('Rejected input')
            got=(result.value,st.value,fp.control,fp.status)
            if got!=ref:raise AssertionError(f'{p.name} #{i} {v}: {got}/{ref}')
    root=Path(__file__).resolve().parents[1]
    report={'status':'passed','entries':[f'0x{x:08x}' for x in entries],'cases':len(vectors),'mismatches':0,'skipped':0,'seed':13,'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,
        'oracle_scope':'Original x86 under Unicorn plus independently transcribed x87 sequences under macOS Rosetta; no physical x86 claim',
        'bounded_unicorn_discrepancies':{'snan_quieting':quiet_differences,'snan_operand_selection':nan_selection_differences,'exception_flags':exception_differences,'c1_clear':c1_differences,'astat_exception':astat_differences,'scale_extended_subnormal':scale_tiny_differences},
        'source_sha256':hashlib.sha256((root/('sharc_fp_scale.c' if args.scaling else 'sharc_fp_arithmetic.c' if args.arithmetic else 'sharc_fp.c')).read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'x87_oracle_source_sha256':hashlib.sha256((root/'test/x87_simple_oracle.c').read_bytes()).hexdigest(),'x87_oracle_sha256':hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn in libs]}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
