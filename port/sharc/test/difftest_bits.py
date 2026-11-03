#!/usr/bin/env python3
"""Compare the recovered helper with ElSemi's original x86 code under Unicorn.

Reuses the PE section-mapping/isolated-call method of port/tgp/test/difftest.py.
No game ROMs or native Windows process are used. All failures are fatal; there
are no skipped inputs. Executable identity is checked before emulation.
"""
import argparse
import ctypes
import hashlib
import json
import platform
import random
import struct
from pathlib import Path

import unicorn
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
    UC_X86_REG_EIP, UC_X86_REG_EFLAGS,
)

EXE_SHA256 = "2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc"
ENTRY = 0x004BCD10
STACK, STOP = 0x71000000, 0x70000000
SP = STACK + 0x8000


def load_original(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXE_SHA256:
        raise ValueError("Unsupported executable: expected the recorded ElSemi 1.1a image")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optsize = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 52)[0]
    size = struct.unpack_from("<I", data, pe + 80)[0]
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(base, (size + 0xfff) & ~0xfff)
    for index in range(count):
        _, _, va, rawsize, rawptr = struct.unpack_from(
            "<8sIIII", data, pe + 24 + optsize + index * 40)
        mu.mem_write(base + va, data[rawptr:rawptr + rawsize])
    mu.mem_map(STACK, 0x10000)
    mu.mem_map(STOP, 0x1000)
    return mu


def values(width, rng, random_cases):
    # Include each bit alone and each single-bit hole, plus sign/mask edges.
    sign = 1 << ((width - 1) & 31)
    mask = (1 << (width & 31)) - 1
    fixed = [0, 1, 0xffffffff, 0xaaaaaaaa, 0x55555555,
             0x7fffffff, 0x80000000, sign - 1, sign, sign + 1,
             mask, (mask + 1) & 0xffffffff]
    fixed += [1 << bit for bit in range(32)]
    fixed += [0xffffffff ^ (1 << bit) for bit in range(32)]
    return list(dict.fromkeys(fixed)) + [rng.getrandbits(32) for _ in range(random_cases)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--random-per-width", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.random_per_width < 0:
        parser.error("--random-per-width must be non-negative")
    mu = load_original(args.exe)
    libraries = []
    for path in args.libraries:
        lib = ctypes.CDLL(str(path.resolve()))
        fn = lib.m2_sharc_extend_immediate
        fn.argtypes = [ctypes.c_uint32, ctypes.c_uint8]
        fn.restype = ctypes.c_uint32
        libraries.append((path, lib, fn))
    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    rng = random.Random(args.seed)
    cases = 0
    preserved = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
    for width in range(256):
        for value in values(width, rng, args.random_per_width):
            saved = {reg: rng.getrandbits(32) for reg in preserved}
            for reg, content in saved.items():
                mu.reg_write(reg, content)
            mu.reg_write(UC_X86_REG_EAX, value)
            mu.reg_write(UC_X86_REG_ECX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_EDX, (rng.getrandbits(24) << 8) | width)
            mu.reg_write(UC_X86_REG_ESP, SP)
            mu.reg_write(UC_X86_REG_EFLAGS, 2)
            mu.mem_write(SP - 4, struct.pack("<II", 0xa5a5a5a5, STOP))
            writes.clear()
            try:
                mu.emu_start(ENTRY, STOP, count=64)
                if mu.reg_read(UC_X86_REG_EIP) != STOP:
                    raise AssertionError("Original did not return within instruction limit")
                if mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                    raise AssertionError("Original stack was not balanced")
                if any(mu.reg_read(reg) != content for reg, content in saved.items()):
                    raise AssertionError("Original corrupted a preserved register")
                if writes != [(SP - 4, 4)]:
                    raise AssertionError(f"Unexpected original writes: {writes}")
                if bytes(mu.mem_read(SP - 4, 8)) != struct.pack("<II", saved[UC_X86_REG_ESI], STOP):
                    raise AssertionError("Unexpected original stack content")
                if mu.reg_read(UC_X86_REG_EDX) != width or mu.reg_read(UC_X86_REG_ECX) != width:
                    raise AssertionError("Unexpected original scratch-register result")
                original = mu.reg_read(UC_X86_REG_EAX)
                for path, lib, fn in libraries:
                    actual = fn(value, width)
                    if actual != original:
                        raise AssertionError(
                            f"{path.name}: original={original:08x}, port={actual:08x}")
            except Exception as error:
                raise RuntimeError(
                    f"Case {cases}, seed={args.seed}, width={width}, value={value:08x}: {error}") from error
            cases += 1
    source = Path(__file__).resolve().parents[1] / "sharc_bits.c"
    result = {
        "status": "passed", "scope": "One native SHARC decoder helper; no board/game execution",
        "entry": f"0x{ENTRY:08x}", "exe_sha256": EXE_SHA256,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "unicorn": unicorn.__version__, "python": platform.python_version(),
        "host": platform.platform(), "seed": args.seed,
        "random_per_width": args.random_per_width, "encoded_widths": 256,
        "cases": cases, "mismatches": 0, "skipped": 0,
        "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p, lib, fn in libraries],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
