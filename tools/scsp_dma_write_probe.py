#!/usr/bin/env python3
"""Compare the native and portable CPU DMA-write paths.

Synthetic RAM-to-coefficient request only; no game reachability claim.
"""
import argparse,ctypes as C,hashlib,json,struct,subprocess,tempfile
from pathlib import Path
from a68k_boundary_compare import Oracle
from scsp_control_compare import ROOT,CHIP
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EDX

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--require-match',action='store_true');a=ap.parse_args()
    o=Oracle(a.exe);o.put(0x5728bc,CHIP);o.u.mem_write(CHIP,b'\0'*0x30);o.u.mem_write(CHIP+0x1238,b'\1')
    o.u.mem_write(CHIP+0x1248,struct.pack('<H',0x369a))
    for reg,value in ((0x412,0x100),(0x414,0x700),(0x416,0x1002)):
        o.run(0x4afa20,{UC_X86_REG_ECX:0x100000+reg,UC_X86_REG_EDX:value})
    word=lambda at:struct.unpack('<H',o.u.mem_read(CHIP+at,2))[0]
    original=[word(0x1248),word(0x12),word(0x14),word(0x16)]
    with tempfile.TemporaryDirectory(prefix='model2-scsp-dma-') as temp:
        lib=Path(temp)/'probe.dylib'
        subprocess.run(['clang','-O2','-std=c11','-dynamiclib','-fPIC',str(ROOT/'port/snd/test/scsp_control_shim.c'),str(ROOT/'port/snd/scsp_dsp_original.c'),'-lm','-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));fn=dll.scsp_dma_cpu_probe;fn.argtypes=[C.POINTER(C.c_uint32)];out=(C.c_uint32*7)();fn(out)
        portable=list(out[:4]);internal=list(out[4:])
        assert internal==[0x1122,0x1122,0x2002],internal
    assert original==[0x369a,0x100,0x700,0x1002],original
    if a.require_match:assert portable==original,(portable,original)
    result=dict(original=original,portable=portable,same=original==portable,internal_dma_roundtrip=internal,
        fields=['coefficient_0','DMA_memory_address','DMA_register_address','DMA_control_length'],
        original_sha256=hashlib.sha256(a.exe.read_bytes()).hexdigest(),
        limits=['Synthetic request, not evidence that any game uses DMA.',
                'Internal DMA round-trip is a separate port regression check, not native equivalence.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
