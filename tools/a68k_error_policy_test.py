#!/usr/bin/env python3
"""Qualify the prepared A68K DIVS error policy in isolated POSIX children."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = [root/'port/a68k/divs_error_policy.c', root/'port/a68k/test/divs_error_policy.c']
    runs = []
    with tempfile.TemporaryDirectory(prefix='model2-a68k-policy-') as tmp:
        for mode in ('O0', 'O2', 'ubsan'):
            command = ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                       '-O0' if mode == 'O0' else '-O2', *map(str, sources), '-o', str(Path(tmp)/mode)]
            if mode == 'ubsan':
                command += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
            subprocess.run(command, check=True)
            subprocess.run([str(Path(tmp)/mode)], check=True)
            runs.append(dict(mode=mode, passed=True))
    files = sources + [root/'port/a68k/divs_error_policy.h', root/'port/a68k/a68k.h', Path(__file__)]
    result = dict(runs=runs, host=platform.platform(),
                  evidence='Default returns sticky fault without changing CPU state; Original produces SIGFPE in an owned child; other faults unaffected.',
                  limits=['Prepared policy, not registered in the production frontend while A68K is unlinked.',
                          'Windows policy RaiseException path not executed by this POSIX test.'],
                  source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
