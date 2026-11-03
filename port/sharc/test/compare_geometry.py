#!/usr/bin/env python3
"""Bounded diagnostic of original x87 transforms and current renderer helpers.

Reports numerical differences instead of treating them as reconstruction
failures. Original runtime FPU mode and full Windows rendering remain unproven.
No ROMs, graphics context, renderer changes or helper-coverage claims.
"""
import argparse
import hashlib
import json
import random
import struct
import subprocess
from pathlib import Path

import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original, EXE_SHA256, SP, STOP


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("exe", type=Path)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--portable", type=Path, nargs="+", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--oracle-only-cw", type=lambda value: int(value, 0),
                    choices=(0x7f, 0x27f, 0x37f),
                    help="Compare one precision mode against the independent x87 oracle without Unicorn")
    args = ap.parse_args()
    if hashlib.sha256(args.exe.read_bytes()).hexdigest() != EXE_SHA256:
        ap.error("Expected the pinned ElSemi 1.1a executable")
    control_words = (args.oracle_only_cw,) if args.oracle_only_cw else (0x7f, 0x27f, 0x37f)
    arena = 0x72000000
    rng = random.Random(0x4b9cb0)
    inputs = []
    for point in (0, 1):
        for i in range(1024):
            values = [rng.uniform(-8, 8) * 2**rng.randrange(-10, 11)
                      for _ in range(15)]
            if i == 0:
                values = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 3, 4]
            if i == 1:
                values = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0,
                          2**24, 1, -2**24]
            words = struct.unpack("<15I", struct.pack("<15f", *values))
            for cw in control_words:
                inputs.append((point, cw, *words))
    blob = b"".join(struct.pack("<17I", *v) for v in inputs)
    binaries = [args.oracle, *args.portable]
    results = {}
    for binary in binaries:
        run = subprocess.run([str(binary.resolve())], input=blob,
                             capture_output=True, check=True, timeout=30)
        if len(run.stdout) != len(inputs) * 12:
            raise RuntimeError(f"Unexpected output size: {binary}")
        results[binary.name] = [run.stdout[i:i+12]
                               for i in range(0, len(run.stdout), 12)]
    originals = []
    if not args.oracle_only_cw:
        mu = load_original(args.exe)
        mu.mem_map(arena, 0x1000)
    for index, record in enumerate(inputs if not args.oracle_only_cw else ()):
        point, cw = record[:2]
        m = record[2:14]
        expanded = (*m[:3], 0, *m[3:6], 0, *m[6:9], 0, *m[9:], 0x3f800000)
        # Exercise both original matrix branches with identical selected data.
        alternate = index & 1
        matrix = 0x10f0068 if alternate else 0x10f00a8
        mu.mem_write(matrix, struct.pack("<16I", *expanded))
        mu.mem_write(0x573330, struct.pack("<I", matrix))
        mu.mem_write(0x10ed95a, bytes([alternate]))
        mu.mem_write(arena, struct.pack("<4I", *record[14:], alternate))
        mu.mem_write(SP, struct.pack("<I", STOP))
        for reg, value in ((UC_X86_REG_ESP, SP), (UC_X86_REG_EAX, arena),
                           (UC_X86_REG_ECX, arena), (UC_X86_REG_FPCW, cw),
                           (UC_X86_REG_FPSW, 0), (UC_X86_REG_FPTAG, 0xffff)):
            mu.reg_write(reg, value)
        mu.emu_start(0x4b9cb0 if point else 0x4b9df0, STOP, count=128)
        if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
            raise RuntimeError("Original call did not return cleanly")
        originals.append(bytes(mu.mem_read(arena, 12)))
    if not args.oracle_only_cw:
        results["original_unicorn"] = originals
    groups = []
    oracle = results[args.oracle.name]
    for point in (0, 1):
        for cw in control_words:
            indices = [i for i, v in enumerate(inputs) if v[:2] == (point, cw)]
            row = {"kind": "point" if point else "vector", "cw": hex(cw),
                   "cases": len(indices), "different_from_x87_oracle": {}}
            for name, output in results.items():
                if name == args.oracle.name:
                    continue
                diff = [i for i in indices if output[i] != oracle[i]]
                row["different_from_x87_oracle"][name] = {
                    "count": len(diff),
                    "first_witness": None if not diff else {
                        "input_words": [hex(v) for v in inputs[diff[0]]],
                        "actual_hex": output[diff[0]].hex(),
                        "oracle_hex": oracle[diff[0]].hex()}}
            groups.append(row)
    report = {"status": "diagnostic_completed", "cases": len(inputs),
              "scope": "Finite transform helpers only; no full renderer or runtime FPU-mode claim",
              "exe_sha256": EXE_SHA256,
              "unicorn": None if args.oracle_only_cw else unicorn.__version__, "groups": groups,
              "files": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [*binaries, Path(__file__),
                                  Path(__file__).with_name("geometry_probe.c"),
                                  Path(__file__).parents[2] / "m2/m2geo.c"]}}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cases": len(inputs), "groups": [
        {**{k: v for k, v in g.items() if k != "different_from_x87_oracle"},
         "differences": {k: v["count"] for k, v in g["different_from_x87_oracle"].items()}}
        for g in groups]}, indent=2))


if __name__ == "__main__":
    main()
