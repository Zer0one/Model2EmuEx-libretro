#!/usr/bin/env python3
"""Generate ROM-free i960 FP vectors; compare raw results with native PE bodies.

Build linux_original_fp.c/.S with I960_FP_ORACLE and execute on physical x86.
No tolerance or NaN normalization is used. Native records are 16 bytes:
result (8), x87 CW (2 + padding), SW (2 + padding); only result bytes compare.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
from original_inventory import OriginalPE

OPS = [('sqrtr', 0x688, 0x4c3d80), ('sqrtrl', 0x698, 0x4c3d40),
       ('divr', 0x78b, 0x4c2d30), ('mulr', 0x78c, 0x4c2dc0),
       ('subr', 0x78d, 0x4c2e50), ('addr', 0x78f, 0x4c2ee0),
       ('divrl', 0x79b, 0x4c2cf0), ('mulrl', 0x79c, 0x4c2d80),
       ('subrl', 0x79d, 0x4c2e10), ('addrl', 0x79f, 0x4c2ea0)]


def vectors():
    # Matching categories in binary32/binary64, including both NaN signs,
    # signalling/quiet payload ordering, signed zeros and exponent boundaries.
    edges32 = [0, 0x80000000, 0x3f800000, 0xbf800000, 0x40000000,
               0xc0000000, 0x7f800000, 0xff800000, 1, 0x800000,
               0x7f7fffff, 0x7fc00001, 0xffc00001, 0x7fc01234,
               0x7f800001, 0xff800001, 0x7f801234]
    edges64 = [0, 0x8000000000000000, 0x3ff0000000000000,
               0xbff0000000000000, 0x4000000000000000, 0xc000000000000000,
               0x7ff0000000000000, 0xfff0000000000000, 1, 0x10000000000000,
               0x7fefffffffffffff, 0x7ff8000000000001, 0xfff8000000000001,
               0x7ff8000000001234, 0x7ff0000000000001,
               0xfff0000000000001, 0x7ff0000000001234]
    rng = random.Random(960)
    for name, key, entry in OPS:
        wide = name.endswith('l')
        for raw in ([0] if wide else range(0, 0x4000, 0x800)):
            a64, b64 = wide or raw & 0x800, wide or raw & 0x1000
            aa, bb = edges64 if a64 else edges32, edges64 if b64 else edges32
            pairs = list(itertools.product(aa, bb)) if not name.startswith('sqrt') else [(a, 0) for a in aa]
            pairs += [(rng.getrandbits(64 if a64 else 32), rng.getrandbits(64 if b64 else 32)) for _ in range(128)]
            for a, b in pairs:
                words = (entry, raw, a & 0xffffffff, a >> 32, b & 0xffffffff, b >> 32, 0x27f)
                yield name, key, words


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exe', type=Path, required=True)
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--library', type=Path)
    ap.add_argument('--portable-output', type=Path, help='Records from native fp_runner instead of ctypes')
    ap.add_argument('--native', type=Path)
    ap.add_argument('--report', type=Path)
    args = ap.parse_args()
    OriginalPE(args.exe)  # Pinned SHA and PE identity, not merely a filename.
    cases = list(vectors())
    blob = b''.join(struct.pack('<7I', *words) for _, _, words in cases)
    if args.native is None:
        args.input.write_bytes(blob)
        print(f'{len(cases)} vectors, SHA256 {hashlib.sha256(blob).hexdigest()}')
        return 0
    assert args.input.read_bytes() == blob, 'Input/version mismatch'
    native = args.native.read_bytes()
    assert len(native) == len(cases)*16, 'Truncated/extra native results'
    if bool(args.library) == bool(args.portable_output):
        ap.error('Comparison requires exactly one of --library or --portable-output')
    if args.report is None:
        ap.error('Comparison requires --report')
    if args.library:
        lib = C.CDLL(str(args.library.resolve()))
        lib.t_fp.argtypes = [C.c_uint32, C.c_uint32, C.c_void_p, C.c_void_p, C.c_void_p]
    else:
        portable = args.portable_output.read_bytes()
        assert len(portable) == len(native), 'Truncated/extra portable results'
    failures, counts = [], {}
    for i, (name, key, w) in enumerate(cases):
        a, b, out = (C.c_uint32*2)(*w[2:4]), (C.c_uint32*2)(*w[4:6]), (C.c_uint32*2)()
        if args.library:
            assert lib.t_fp(key, w[1], a, b, out) == 1
            got = bytes(out)
        else:
            got = portable[i*16:i*16+8]
        expected = native[i*16:i*16+8]
        counts[name] = counts.get(name, 0)+1
        if got != expected:
            failures.append(dict(index=i, op=name, raw=hex(w[1]),
                src1=bytes(a).hex(), src2=bytes(b).hex(),
                original=expected.hex(), portable=got.hex()))
    report = dict(cases=len(cases), mismatches=len(failures), operations=counts,
        input_sha256=hashlib.sha256(blob).hexdigest(),
        original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
        native_sha256=hashlib.sha256(native).hexdigest(),
        portable_source=str(args.library or args.portable_output),
        portable_sha256=hashlib.sha256((args.library or args.portable_output).read_bytes()).hexdigest(), failures=failures)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(f'{len(cases)} cases, {len(failures)} mismatches')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
