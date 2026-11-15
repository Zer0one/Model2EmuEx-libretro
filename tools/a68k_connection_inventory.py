#!/usr/bin/env python3
"""Compare preprocessed observed-dispatch target tokens with original RLE table.

This is a switch inventory, not execution/path or whole-CPU qualification.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from a68k_inventory import decode_dispatch
from original_inventory import OriginalPE
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();table=decode_dispatch(OriginalPE(a.exe))[3]
    source=ROOT/'port/a68k/a68k.c'
    pre=subprocess.check_output(['clang','-E','-P',str(source)],text=True)
    start=pre.index('a68k_boundary a68k_step_observed(a68k_cpu *s,')
    end=pre.index('a68k_boundary a68k_run_live(',start)
    cases={int(t,0) for t in re.findall(r'case (0x[0-9a-f]+|[0-9]+):',pre[start:end])}
    missing=sorted(set(table)-cases);extra=sorted(cases-set(table))
    result={'group':'observed_dispatch_inventory','targets':len(cases),'encodings':len(table),
            'missing':missing,'extra':extra,'original_sha256':hashlib.sha256(a.exe.read_bytes()).hexdigest(),
            'limits':['Switch coverage only; no all-path, native callback or whole-CPU completion claim.']}
    paths=[Path(__file__),source,ROOT/'port/a68k/a68k.h',*sorted((ROOT/'port/a68k').glob('*.inc'))]
    result['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='sources_sha256'})
    if missing or extra:raise SystemExit(1)


if __name__=='__main__':main()
