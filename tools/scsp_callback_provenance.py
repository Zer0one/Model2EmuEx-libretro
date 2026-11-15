#!/usr/bin/env python3
"""Record original A68K DATA-wrapper/SCSP callback register provenance.

With --compare, qualifies the recovered research observation helper. Reuses
the qualified control fixtures and actual original x86;
no game ROMs, host pointers substituted into emulated state, or CPU-wide tests.
"""
import argparse,ctypes as C,hashlib,json,subprocess,tempfile
from pathlib import Path
from scsp_control_compare import fixtures,native,CHIP
from a68k_boundary_compare import Oracle,DATA
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--compare',action='store_true');ap.add_argument('--optimization',choices=('O0','O2'),default='O2')
    ap.add_argument('--ubsan',action='store_true')
    ap.add_argument('--bound',action='store_true',help='Compare through actual A68K page binding and read API')
    a=ap.parse_args();o=Oracle(a.exe);rows=[]
    temporary=tempfile.TemporaryDirectory(prefix='model2-scsp-scratch-');fn=None;qualified=guards=0
    if a.compare:
        root=Path(__file__).resolve().parents[1];lib=Path(temporary.name)/'control.dylib'
        cmd=['clang','-'+a.optimization,'-std=c11','-Wall','-Wextra','-Werror','-dynamiclib','-fPIC',
             str(root/'port/snd/test/scsp_control_shim.c'),str(root/'port/snd/scsp_dsp_original.c'),'-lm','-o',str(lib)]
        if a.bound:cmd+=['-DSCSP_A68K_BIND_TEST',str(root/'port/a68k/a68k.c'),str(root/'port/a68k/scsp_bus.c')]
        if a.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            cmd+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(cmd,check=True);dll=C.CDLL(str(lib));fn=dll.scsp_control_probe
        fn.argtypes=[C.c_uint,C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)];fn.restype=C.c_int
    for page in range(0x100,0x110):o.put(DATA+page*16,0,0x4ae870,0x4ae800,0x4ab220)
    fifo=bytes((i*29+17)&255 for i in range(128))
    cases=[(group,x[11]+0x400,x[13],x) for group,op,x in fixtures() if op==1]
    base=next(fixtures())[2]
    for offset in (0,1,0x1f,0x3ff,0x400,0x402,0x406,0x42e,0x42f,0x430,0x444,0x454,0x500,0x600,0x601,0x6ff,0x700,0xfff,0x1000,0xffff):
        for width in (1,2,4):cases.append(('width-boundary',offset,width,base))
    # Traverse both mirrored CPU windows, including updates that consume a
    # queued byte even though the returned bytes belong to a voice register.
    pending = next(x for _,_,x in fixtures() if x[1] == 40)
    for window in (0x400, 0x500):
        for at in range(0x30, 0x100):
            for width in (1, 2):
                cases.append(('slot-object', window + at, width, pending))
    for offset in range(0x680, 0x700):
        cases.append(('ring-alias-read',offset,2,base))
    for group,offset,width,x in cases:
        for flags in (0x202,0x203,0xad7,0xed7):
            native(o,0,x,fifo,execute=False)
            for slot in range(32):
                o.u.mem_write(CHIP+0x30+slot*0x8c,bytes((i+slot*7)&255 for i in range(32)))
                o.u.mem_write(CHIP+0x50+slot*0x8c,b'\1')
            o.u.mem_write(CHIP+0x11b0,bytes(range(256)))
            for slot in (0,1):
                address = CHIP + 0x30 + slot*0x8c
                o.u.mem_write(address+0x20, bytes(0x6c))
                o.u.mem_write(address+0x20, bytes((1,0xc7)))
                o.put(address+0x34, 0x18800, 2, 0, 101, 23, 17, 5, 12, 32)
                o.put(address+0x58, 0x9876, 38, 0x010c31b0, 0x010986e8 + 7*0x400)
                o.put(address+0x68, 0xabc1, 51, 0x010bdf50, 0x010c11b0 + 4*0x400)
                o.put(address+0x78, slot, 0xffff & -4521, 2899, 8211, 16384)
                o.put(address+0x24, 0x12345 + slot, x[24+slot], 0x13579bdf-slot)
                o.u.mem_write(address+0x30, bytes([slot & 1]))
            o.run({1:0x4b3250,2:0x4b3220,4:0x4b31f0}[width],{
                UC_X86_REG_ECX:0x100000+offset,UC_X86_REG_EAX:0x12345678,
                UC_X86_REG_EDX:0x87654321,UC_X86_REG_EFLAGS:flags})
            rows.append(dict(group=group,offset=f'{offset:04x}',width=width,
                input_flags=f'{flags:08x}',eax=f'{o.u.reg_read(UC_X86_REG_EAX):08x}',
                edx=f'{o.u.reg_read(UC_X86_REG_EDX):08x}',flags=f'{o.u.reg_read(UC_X86_REG_EFLAGS):08x}'))
            if fn:
                inp=x.copy();inp[57:60]=[offset,width,flags];out=(C.c_uint32*79)()
                assert fn(8,(C.c_uint32*64)(*inp),(C.c_uint8*128)(*fifo),out)
                assert out[78], rows[-1]
                actual=dict(eax=f'{out[0]:08x}',edx=f'{out[76]:08x}',flags=f'{out[77]:08x}')
                assert all(rows[-1][k]==v for k,v in actual.items()),(rows[-1],actual)
                assert list(out[1:4]) == [o.u.mem_read(i,1)[0] for i in (0x10ed9d9,0x10ed9d8,0x1078799)]
                qualified+=1
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    result=dict(cases=len(rows),result_sha256=digest,original_sha256=hashlib.sha256(a.exe.read_bytes()).hexdigest(),
        qualified=qualified,guarded_aliases=guards,optimization=a.optimization,ubsan=a.ubsan,bound=a.bound,
        rows=rows,limits=['The bound run uses the production A68K page callbacks with a synthetic chip.',
        'Arithmetic EFLAGS observations are x86/Unicorn results, including architecturally undefined flag bits.',
        'Waveform and scale addresses use the PE address space.',
        'No original sound-thread scheduling, whole-game execution or A68K production activation.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    temporary.cleanup()
if __name__=='__main__':main()
