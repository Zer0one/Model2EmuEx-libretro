#!/usr/bin/env python3
"""Exhaust the original register selector's byte encodings and flag effects."""
import argparse
import ctypes
import hashlib
import json
import random
import struct
from pathlib import Path

import unicorn
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
    UC_X86_REG_EIP, UC_X86_REG_EFLAGS,
)
from difftest_bits import load_original, EXE_SHA256, STOP, SP

ARENA, RECORD = 0x72000000, 0x300
SIZE, ENTRY = 0x400, 0x4bcb80
P32 = ctypes.POINTER(ctypes.c_uint32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mu = load_original(args.exe)
    mu.mem_map(ARENA, 0x1000)
    mu.mem_write(0x5aeb40, struct.pack("<I", ARENA))
    mu.mem_write(0x5aeb10, struct.pack("<I", ARENA + RECORD))
    libraries = []
    for path in args.libraries:
        lib = ctypes.CDLL(str(path.resolve()))
        fn = lib.m2_sharc_register_location
        fn.argtypes = [P32, P32, ctypes.c_uint8]
        fn.restype = ctypes.c_void_p
        libraries.append((path, lib, fn))
    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    rng = random.Random(3)
    cases = 0
    for code in range(256):
        for initial_flags in (0, 0x80, 0xffff, 0xff7f):
            arena = bytearray(rng.randbytes(SIZE))
            struct.pack_into("<H", arena, RECORD + 0x2c, initial_flags)
            mu.mem_write(ARENA, bytes(arena))
            mu.mem_write(SP, struct.pack("<I", STOP))
            saved = {reg: rng.getrandbits(32) for reg in
                     (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)}
            for reg, value in saved.items():
                mu.reg_write(reg, value)
            mu.reg_write(UC_X86_REG_EAX, (rng.getrandbits(24) << 8) | code)
            mu.reg_write(UC_X86_REG_ECX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_EDX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_ESP, SP)
            mu.reg_write(UC_X86_REG_EFLAGS, 2)
            writes.clear()
            try:
                mu.emu_start(ENTRY, STOP, count=64)
                if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                    raise AssertionError("Original did not return with balanced stack")
                if any(mu.reg_read(reg) != value for reg, value in saved.items()):
                    raise AssertionError("Preserved register changed")
                allowed = [(ARENA + RECORD + 0x2c, 2)] if code >> 4 == 4 else []
                if writes != allowed:
                    raise AssertionError(f"Unexpected writes: {writes}")
                offset = mu.reg_read(UC_X86_REG_EAX) - ARENA
                if not ((0 <= offset < 0x2a4 or offset == RECORD + 0x30) and offset % 4 == 0):
                    raise AssertionError(f"Unexpected original location: {offset:x}")
                expected = bytes(mu.mem_read(ARENA, SIZE))
                for path, lib, fn in libraries:
                    native = (ctypes.c_uint32 * (SIZE // 4)).from_buffer_copy(arena)
                    state_ptr = ctypes.cast(native, P32)
                    record_ptr = ctypes.cast(ctypes.byref(native, RECORD), P32)
                    actual = fn(state_ptr, record_ptr, code) - ctypes.addressof(native)
                    if actual != offset or bytes(native) != expected:
                        raise AssertionError(f"{path.name}: original offset={offset:x}, port={actual:x}")
            except Exception as error:
                raise RuntimeError(f"Code={code:02x}, flags={initial_flags:04x}: {error}") from error
            cases += 1
    source = Path(__file__).resolve().parents[1] / "sharc_registers.c"
    receipt = {
        "status": "passed", "scope": "Original register selector; no decoder/board execution",
        "entry": f"0x{ENTRY:08x}", "exe_sha256": EXE_SHA256,
        "unicorn": unicorn.__version__, "seed": 3, "codes": 256,
        "cases": cases, "mismatches": 0, "skipped": 0,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p, lib, fn in libraries],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
