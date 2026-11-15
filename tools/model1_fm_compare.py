#!/usr/bin/env python3
"""Compare historical Tatsuyuki Satoh fm.c and Model 2 Emulator 1.1a at chip boundaries."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from model1_board_compare import initialize, OUTPUT, SP
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX

SOURCE_HASH = '91213dfb4f059a1d64b15e44ded85d2f81247f4f7650194abd5dc94a5e2fb0cd'

def build(source, header, work):
    if hashlib.sha256(source.read_bytes()).hexdigest()!=SOURCE_HASH:
        raise ValueError('Expected mamedev/historic-mame mame037b12 or mame037b14 fm.c')
    (work/'fm.c').write_bytes(source.read_bytes())
    (work/'fm.h').write_bytes(header.read_bytes())
    (work/'ay8910.h').write_text('#define AY8910_set_clock(chip,clock) ((void)0)\n')
    (work/'driver.h').write_text('#define HAS_YM2612 1\n#define INLINE static inline\n'
        '#define logerror(...) ((void)0)\nvoid YM2612UpdateRequest(int);\n')
    # Suppress only the board's write-triggered rendering; the harness similarly
    # sets the native callback's available frame count to zero while writing.
    (work/'compare.c').write_text('#include "fm.c"\nvoid YM2612UpdateRequest(int n) {(void)n;}\n'
        'const int *ref_detune(void) { return &FM2612[0].OPN.ST.DT_TABLE[0][0]; }\n'
        'const int *ref_envelope(void) { return ENV_CURVE; }\n'
        'const int *ref_tl(void) { return TL_TABLE; }\n'
        'const int *ref_attack(void) { return FM2612[0].OPN.ST.AR_TABLE; }\n'
        'const int *ref_decay(void) { return FM2612[0].OPN.ST.DR_TABLE; }\n'
        'const int *ref_frequency(void) { return (int*)FM2612[0].OPN.FN_TABLE; }\n')
    image=work/'ref.so'
    subprocess.run(['cc','-shared','-fPIC','-O2','-fwrapv','-ffp-contract=off',
                    str(work/'compare.c'),'-lm','-o',str(image)],check=True)
    return C.CDLL(str(image))


def compare(exe,dll, native_levels=False):
    o=initialize(exe)
    assert dll.YM2612Init(1,8000000,44100,None,None)==0
    o.put(0x10e3fe8,0)
    buffer=OUTPUT+0x64000
    left,right=buffer+0x1000,buffer+0x4000
    o.put(buffer,left,right)
    def reg(bank,idx,value):
        for addr,v in ((2*bank,idx),(2*bank+1,value)):
            o.run(0x4b2580,{UC_X86_REG_EAX:addr,UC_X86_REG_EBX:v})
            dll.YM2612Write(0,addr,v)
    def render(n):
        o.put(SP+4,n)
        o.run(0x4b1b50,{UC_X86_REG_EAX:buffer},count=40000000)
        a=(C.c_int16*n)(); b=(C.c_int16*n)()
        dll.YM2612UpdateOne(0,(C.POINTER(C.c_int16)*2)(a,b),n)
        return (bytes(o.u.mem_read(left,n*2))+bytes(o.u.mem_read(right,n*2)),
                bytes(a)+bytes(b))
    chip=o.get(0x10ed9d4)[0]
    def tables(func,addr,n):
        fn=getattr(dll,'ref_'+func)
        fn.restype=C.POINTER(C.c_int32)
        values=list(fn()[:n])
        original=list(struct.unpack('<'+'i'*n,o.u.mem_read(addr,4*n)))
        return dict(words=n,differences=sum(a!=b for a,b in zip(original,values)),
                    first=next(([i,a,b] for i,(a,b) in enumerate(zip(original,values)) if a!=b),None))
    tbl={name:tables(name,addr,n) for name,addr,n in [('detune',chip+0x40,256),
             ('frequency',chip+0x758,2048), ('attack',chip+0x440,94), ('decay',chip+0x5b8,94),
             ('envelope',0x107c7f0,8193),('tl',o.get(0x107c7d4)[0],12460)]}
    if native_levels:
        # Change only the amplitude lookup, keeping the historical implementation
        # and the entire native execution independent.
        C.memmove(dll.ref_tl(), bytes(o.u.mem_read(o.get(0x107c7d4)[0],12460*4)),12460*4)
    results={}
    def sample(name,n):
        a,b=render(n)
        words=struct.unpack('<'+'h'*(2*n),a)
        ref=struct.unpack('<'+'h'*(2*n),b)
        results[name]=dict(frames=n,nonzero=sum(v!=0 for v in words),
            differences=sum(x!=y for x,y in zip(words,ref)),
            first=next(([i,x,y] for i,(x,y) in enumerate(zip(words,ref)) if x!=y),None),
            original_sha256=hashlib.sha256(a).hexdigest(),source_sha256=hashlib.sha256(b).hexdigest())
    sample('reset',32)
    reg(0,0x2b,128)
    reg(0,0x2a,0xc7)
    sample('direct_dac',16)
    reg(0,0x2b,0)
    for slot in range(4):
        for index,v in [(0x30,0x37),(0x40,8),(0x50,31),(0x60,15),(0x70,5),(0x80,0x34)]:
            reg(0,index+slot*4,v)
    reg(0,0xb4,0xc0)
    reg(0,0xa4,0x22)
    reg(0,0xa0,0x08)
    for alg in range(8):
        reg(0,0xb0,alg|0x18)
        reg(0,0x28,0xf0)
        sample(f'algorithm_{alg}',128)
        reg(0,0x28,0)
        sample(f'release_{alg}',48)
    dll.YM2612Shutdown()
    return dict(reference_sha256=SOURCE_HASH,tables=tbl,pcm=results)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('exe','source','header'): p.add_argument(name,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    with tempfile.TemporaryDirectory() as td:
        dll=build(a.source,a.header,Path(td))
        result=compare(a.exe,dll)
        isolated=compare(a.exe,dll,native_levels=True)
        result['with_original_level_table']=isolated['pcm']
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['tables'])
    for series in ('pcm','with_original_level_table'):
        print(series,{k:v['differences'] for k,v in result[series].items() if v['differences']})

if __name__=='__main__':
    main()
