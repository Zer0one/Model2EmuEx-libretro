#!/usr/bin/env python3
"""Compare six original field helpers, including status/operand aliasing.

Uses the pinned image loader from the first helper experiment. Native input
values are captured before status mutation; merge bases remain live pointers.
Checks the whole synthetic data arena, not only the expected status word.
"""
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
from difftest_bits import load_original, EXE_SHA256, STACK, STOP, SP

ARENA = 0x72000000
RECORD, SOURCE, BASE = 0x300, 0x380, 0x384
SIZE = 0x400
ENTRIES = {0x4bc420: "deposit", 0x4bc470: "extract", 0x4bc4c0: "direct",
           0x4bc510: "deposit", 0x4bc560: "indirect", 0x4bc5b0: "deposit"}
P32 = ctypes.POINTER(ctypes.c_uint32)


def load_library(path):
    lib = ctypes.CDLL(str(path.resolve()))
    for name in ("deposit", "extract"):
        fn = getattr(lib, "m2_sharc_field_" + name)
        fn.argtypes = [ctypes.c_uint32, ctypes.c_uint32, P32]
        fn.restype = ctypes.c_uint32
    lib.m2_sharc_field_merge.argtypes = [ctypes.c_uint32, P32, ctypes.c_uint32, P32]
    lib.m2_sharc_field_merge.restype = ctypes.c_uint32
    return lib


def scenarios(kind):
    for control in range(4096):
        for value in (0, 0xffffffff, 0x80000000, 0x40000000, 0xaaaaaaaa, None):
            yield control, value, "separate"
    if kind in ("direct", "indirect"):
        aliases = ["source_status", "base_status"]
        if kind == "indirect":
            aliases += ["both_status", "shared_operands"]
        for width in (0, 1, 12, 13, 31, 32, 33, 63):
            for position in (0, 1, 12, 31, 32, 63):
                for alias in aliases:
                    for value in (0, 0xffffffff, 0x80000000, 0x40000000, 0xaaaaaaaa, None):
                        yield (width << 6) | position, value, alias


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mu = load_original(args.exe)
    mu.mem_map(ARENA, 0x1000)
    libs = [(path, load_library(path)) for path in args.libraries]
    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    rng = random.Random(2)
    template = rng.randbytes(SIZE)
    saved = {UC_X86_REG_EBX: 0xfedcba98, UC_X86_REG_ESI: 0x12345678,
             UC_X86_REG_EDI: 0x87654321, UC_X86_REG_EBP: 0xa5a5a5a5}
    counts = {}
    aliases_checked = 0
    for entry, kind in ENTRIES.items():
        count = 0
        for low_control, value, alias in scenarios(kind):
            if value is None:
                value = rng.getrandbits(32)
            control = (rng.getrandbits(20) << 12) | low_control
            arena = bytearray(template)
            status_offset = 0x240
            source_offset, base_offset = SOURCE, BASE
            if kind == "direct":
                source_offset, base_offset = RECORD + 12, RECORD + 8
                if alias == "source_status":
                    status_offset = source_offset
                elif alias == "base_status":
                    status_offset = base_offset
            elif kind == "indirect":
                if alias in ("source_status", "both_status"):
                    source_offset = status_offset
                if alias in ("base_status", "both_status"):
                    base_offset = status_offset
                elif alias == "shared_operands":
                    base_offset = source_offset
                struct.pack_into("<II", arena, RECORD + 8,
                                 ARENA + base_offset, ARENA + source_offset)
            struct.pack_into("<I", arena, status_offset, rng.getrandbits(32))
            struct.pack_into("<I", arena, base_offset, rng.getrandbits(32))
            struct.pack_into("<I", arena, source_offset, value)
            initial_status = struct.unpack_from("<I", arena, status_offset)[0]
            mu.mem_write(ARENA, bytes(arena))
            mu.mem_write(0x5aeb40, struct.pack("<I", ARENA + status_offset - 0x240))
            mu.mem_write(SP - 16, bytes(16) + struct.pack("<I", STOP))
            for reg, content in saved.items():
                mu.reg_write(reg, content)
            mu.reg_write(UC_X86_REG_EAX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_ECX, ARENA + RECORD if kind in ("direct", "indirect") else value)
            mu.reg_write(UC_X86_REG_EDX, control)
            mu.reg_write(UC_X86_REG_ESP, SP)
            mu.reg_write(UC_X86_REG_EFLAGS, 2)
            writes.clear()
            try:
                mu.emu_start(entry, STOP, count=64)
                if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                    raise AssertionError("Original did not return with balanced stack")
                if any(mu.reg_read(reg) != content for reg, content in saved.items()):
                    raise AssertionError("Preserved register changed")
                allowed = {(ARENA + status_offset, 4), (SP - 4, 4)}
                if kind != "extract":
                    allowed.add((SP - 8, 4))
                if any(write not in allowed for write in writes):
                    raise AssertionError(f"Unexpected writes: {writes}")
                expected = bytes(mu.mem_read(ARENA, SIZE))
                result = mu.reg_read(UC_X86_REG_EAX)
                final_status = struct.unpack_from("<I", expected, status_offset)[0]
                if (initial_status ^ final_status) & ~0x1000:
                    raise AssertionError("Original changed unrelated status bits")
                for path, lib in libs:
                    native = (ctypes.c_uint32 * (SIZE // 4)).from_buffer_copy(arena)
                    status_ptr = ctypes.cast(ctypes.byref(native, status_offset), P32)
                    if kind in ("direct", "indirect"):
                        base_ptr = ctypes.cast(ctypes.byref(native, base_offset), P32)
                        actual = lib.m2_sharc_field_merge(value, base_ptr, control, status_ptr)
                    else:
                        actual = getattr(lib, "m2_sharc_field_" + kind)(value, control, status_ptr)
                    if actual != result or bytes(native) != expected:
                        raise AssertionError(
                            f"{path.name}: original={result:08x}, port={actual:08x}, "
                            f"original status={final_status:08x}, port status={status_ptr[0]:08x}")
            except Exception as error:
                raise RuntimeError(
                    f"Entry={entry:08x}, case={count}, control={control:08x}, "
                    f"value={value:08x}, alias={alias}: {error}") from error
            count += 1
            aliases_checked += alias != "separate"
        counts[f"0x{entry:08x}"] = count
    source = Path(__file__).resolve().parents[1] / "sharc_bits.c"
    receipt = {
        "status": "passed", "scope": "Six original bit-field helpers; no board/game execution",
        "exe_sha256": EXE_SHA256, "unicorn": unicorn.__version__, "seed": 2,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "cases_by_entry": counts, "cases": sum(counts.values()),
        "alias_cases": aliases_checked, "mismatches": 0, "skipped": 0,
        "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p, lib in libs],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
