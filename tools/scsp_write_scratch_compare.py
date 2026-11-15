#!/usr/bin/env python3
"""Qualify SCSP global WRITE/ack completion against original x86 callbacks.

Checks mutable control state plus EAX/EFLAGS consumed by the recovered A68K
executor. Voice-slot writes have a separate comparison in scsp_slot_write_compare.py.
"""
import argparse,ctypes as C,hashlib,itertools,json,struct,subprocess,tempfile
from pathlib import Path
from scsp_control_compare import fixtures,native,native_state,CHIP,ROOT
from a68k_boundary_compare import Oracle,WRITE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS

def cases():
    base=next(fixtures())[2]
    for reg,width,value,flags,queued in itertools.product(range(0x30),(1,2,4),(0,0x1c0,0x8040ff20,0xffffffff),(0x202,0xed7),(0,1)):
        x=base.copy();x[1]=queued;x[3]=6;x[4]=0x1c0;x[5]=0x1c0
        x[14:17]=[0xfe5a,0xff00,0x127f];x[17:20]=[1,0,1];x[20:23]=[0x7fe,0x2ff,0x412]
        x[11]=reg;x[12]=value;x[13]=width;x[59]=flags
        valid=True
        yield 9,x,valid
        if 0x16 <= reg <= 0x29 and valid:
            yield 11,x.copy(),True
    for count,reg,width in itertools.product((15,127,255), (4,6), (1,2,4)):
        x=base.copy()
        x[11:14]=[reg,0xa123bcde,width]
        x[59]=0xed7
        x[63]=count
        yield 9,x,True
    for control in range(512):
        x=base.copy()
        x[11:14]=[2,0xfe00|control,2]
        x[59]=0xed7
        yield 9,x,True
    for group,op,x in fixtures():
        if op==3:
            for flags in (0x202,0xed7):
                x=x.copy();x[59]=flags;yield 10,x,True

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--optimization',choices=('O0','O2'),default='O2');ap.add_argument('--ubsan',action='store_true')
    ap.add_argument('--bound',action='store_true',help='Use actual A68K page bindings and observed write API');a=ap.parse_args()
    o=Oracle(a.exe);fifo=bytes((i*29+17)&255 for i in range(128));counts={'write':0,'ack':0,'guard':0};digest=hashlib.sha256()
    o.put(WRITE+0x100*16,0,0x4afb00,0x4afa20,0x4af900)
    sources=[ROOT/'port/snd/test/scsp_control_shim.c',ROOT/'port/snd/scsp_dsp_original.c']
    if a.bound:sources += [ROOT/'port/a68k/a68k.c',ROOT/'port/a68k/scsp_bus.c']
    with tempfile.TemporaryDirectory(prefix='model2-scsp-write-') as temp:
        lib=Path(temp)/'control.dylib';cmd=['clang','-'+a.optimization,'-std=c11','-Wall','-Wextra','-Werror','-dynamiclib','-fPIC',*map(str,sources),'-lm','-o',str(lib)]
        if a.bound:cmd+=['-DSCSP_A68K_BIND_TEST']
        if a.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            cmd+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(cmd,check=True);dll=C.CDLL(str(lib));fn=dll.scsp_control_probe
        fn.argtypes=[C.c_uint,C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)];fn.restype=C.c_int
        for op,x,valid in cases():
            # Seed both byte lanes and a coherent, nonzero initial ring.
            x[60:63]=[0xa555,0x55,32768]
            o.put(CHIP+0x1240,*x[61:63])
            o.u.mem_write(0x10be458, fifo)
            o.u.mem_write(0x10ed99f, bytes([x[63] & 127]))
            o.u.mem_write(0x107879a, bytes([x[63]]))
            before=native(o,0,x,fifo,execute=False)
            if op == 11:
                o.put(CHIP+0x1238, 0x100)  # Only the low byte enables the gate.
            out=(C.c_uint32*114)();assert fn(op,(C.c_uint32*64)(*x),(C.c_uint8*128)(*fifo),out)
            key=(op,hex(x[11]),x[13],hex(x[12]),hex(x[59]),x[1])
            assert bool(out[77])==valid,(key,'valid',out[77])
            if valid:
                if op==10:
                    o.put(0x528d38,0);o.run(0x4b3090,{UC_X86_REG_EFLAGS:x[59]})
                else:o.run({1:0x4b3130,2:0x4b3100,4:0x4b30c0}[x[13]],{
                    UC_X86_REG_ECX:0x100400+x[11],UC_X86_REG_EDX:x[12],UC_X86_REG_EFLAGS:x[59]})
                want=native_state(o,o.u.reg_read(UC_X86_REG_EAX))+[o.u.reg_read(UC_X86_REG_EFLAGS),1]
                counts['ack' if op==10 else 'write']+=1
            else:want=before+[0,0];counts['guard']+=1
            want+=o.get(CHIP+0x1240,2)
            want += list(struct.unpack('<32I', o.u.mem_read(0x10be458,128)))
            want += [o.u.mem_read(0x10ed99f,1)[0], o.u.mem_read(0x107879a,1)[0]]
            assert list(out)==want,(key,[(i,v,w) for i,(v,w) in enumerate(zip(out,want)) if v!=w])
            digest.update(struct.pack('<114I',*out))
    result=dict(groups=counts,cases=sum(counts.values()),mismatches=0,result_sha256=digest.hexdigest(),optimization=a.optimization,ubsan=a.ubsan,bound=a.bound,
        original_sha256=hashlib.sha256(a.exe.read_bytes()).hexdigest(),
        limits=['Global control writes and acknowledge only; no complete CPU/board binding.',
                'This global-register comparison excludes slot and DSP writes.',
                'Write-return EDX is not consumed by the current executor and is not qualified.'])
    result['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,Path(__file__),ROOT/'port/snd/scsp.c',ROOT/'port/snd/scsp.h',ROOT/'tools/scsp_control_compare.py']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources_sha256'},indent=2))
if __name__=='__main__':main()
