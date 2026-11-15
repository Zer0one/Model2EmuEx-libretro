#!/usr/bin/env python3
"""Measure NBCD PUSHFD after native SBB/DAS and compare Windows acquisition."""
import argparse
import hashlib
import json
from pathlib import Path
from a68k_boundary_compare import Oracle, CTX
from unicorn.x86_const import *


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path)
    ap.add_argument('--windows',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();o=Oracle(args.exe);rows=[]
    for value in range(256):
        for x in (0,1):
            c=[0]*33;c[0]=0x12340000|value;c[19]=0xfeed0000|x
            o.setup_exception(c,200)
            o.run(0x486680,{UC_X86_REG_ECX:0x4800,UC_X86_REG_ESI:0x1000,
                           UC_X86_REG_EDX:0xa83,UC_X86_REG_EFLAGS:0x202},stops=(0x4866b9,))
            snapshot=o.get(CTX,33)
            rows.append([value,x,snapshot[0],snapshot[19]])
    windows=None
    if args.windows:
        captured=json.loads(args.windows.read_text(encoding='utf-8-sig'))
        windows=[[int(v,16) for v in row['context']] for row in captured if row['kind']=='nbcd']
        assert len(windows)==512
    differences=[] if windows is None else [dict(index=i,unicorn=a,windows=b) for i,(a,b) in enumerate(zip(rows,windows)) if a!=b]
    result=dict(cases=512,rows=rows,windows_compared=windows is not None,differences=differences,
        original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        windows_sha256=hashlib.sha256(args.windows.read_bytes()).hexdigest() if args.windows else None,
        limits=['All NBCD byte/X pairs with host control flags 0x202; not other instructions or game execution.',
                'A Windows 11 ARM64 comparison does not guarantee the same undefined OF on every x86 processor.'])
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
