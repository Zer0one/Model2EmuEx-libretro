#!/usr/bin/env python3
"""Run inherited i960/TGP suites unchanged and retain explicit evidence limits."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from original_inventory import OriginalPE

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('--libraries', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    OriginalPE(args.exe)
    args.output.mkdir(parents=True, exist_ok=False)
    jobs = [('i960', 'port/i960/test/difftest.py', 'i960-O2.dylib', 8000, seed)
            for seed in range(1, 7)]
    jobs += [('tgp-oracle', 'port/tgp/test/difftest.py', 'tgp-oracle-O2.dylib', 2500, seed)
             for seed in range(1, 9)]
    jobs += [('tgp-board-production', 'port/tgp/test/boardtest.py', 'tgp-production-O2.dylib', 300, seed)
             for seed in range(1, 4)]
    results = []
    for kind, script, library, count, seed in jobs:
        log = args.output/f'{kind}-{seed}.log'
        command = [sys.executable, str(ROOT/script), str(args.exe.resolve()),
                   str((args.libraries/library).resolve()), str(count), str(seed)]
        start = time.monotonic()
        with log.open('w') as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=180)
        text = log.read_text()
        match = re.search(r'(\d+) cases compared(?: over (\d+) kinds)?, (\d+) mismatches', text)
        board = re.search(r'(\d+) sequences, (\d+) driver calls compared, (\d+) failing sequences', text)
        row = dict(suite=kind, seed=seed, requested=count, exit_code=result.returncode,
                   command=command,
                   elapsed_seconds=round(time.monotonic()-start, 3), log=log.name,
                   source_sha256=hashlib.sha256((ROOT/script).read_bytes()).hexdigest(),
                   library_sha256=hashlib.sha256((args.libraries/library).read_bytes()).hexdigest())
        if match:
            row.update(compared=int(match[1]), kinds=int(match[2]) if match[2] else None,
                       mismatches=int(match[3]), skipped=count-int(match[1]))
        elif board:
            row.update(sequences=int(board[1]), compared=int(board[2]), failing_sequences=int(board[3]))
        else:
            row['unparsed_failure'] = True
        row['exclusion_details'] = [line for line in text.splitlines() if line.startswith(('skipped', 'never compared:'))]
        row['unmodelled_access_reported'] = 'not modelled' in text
        results.append(row)
        report = dict(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
            platform=platform.platform(), machine=platform.machine(), python=sys.version,
            sources={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                'port/i960/i960.c', 'port/i960/test/shim.c', 'port/tgp/tgp.c',
                'port/tgp/test/shim.c', 'port/i960/test/difftest.py',
                'port/tgp/test/difftest.py', 'port/tgp/test/boardtest.py')},
            results=results, planned_runs=len(jobs),
            limits=['TGP interpreter uses the inherited Unicorn FLD compatibility macro.',
                    'i960 retains inherited FP tolerances, NaN comparison rules and independent fmod oracle.',
                    'Skipped cases are exclusions, not passes; driver stray-access messages are recorded.',
                    'No ROM/gameplay or native x87 equivalence is implied.'])
        (args.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(row), flush=True)
    return int(any(r['exit_code'] or r.get('unparsed_failure') or r['unmodelled_access_reported'] for r in results))


if __name__ == '__main__':
    sys.exit(main())
