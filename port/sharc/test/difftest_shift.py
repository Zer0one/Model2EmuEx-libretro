#!/usr/bin/env python3
"""Original shifts/rotates/bit operations, flag quirks and operand aliases."""
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

ENTRIES = {0x200: 0x4627a0, 0x204: 0x462900, 0x208: 0x462960,
           0x220: 0x462800, 0x224: 0x462880,
           0x2c0: 0x462a20, 0x2c4: 0x4629c0, 0x2c8: 0x462a60, 0x2cc: 0x4bc3f0}
ARENA, SIZE, STATUS, RECORD = 0x72000000, 0x400, 0x240, 0x300
P32 = ctypes.POINTER(ctypes.c_uint32)
VALUES = (0, 1, 0xffffffff, 0x80000000, 0x7fffffff, 0x55555555, 0xaaaaaaaa)


def scenarios(rng, merge):
    for control in range(256):
        for value in VALUES:
            for status in (0, 0xffffffff, rng.getrandbits(32)):
                yield value, control, status, "separate"
    for control in (0xffffff00, 0xffffffe0, 0xffffffff, 0x80000000,
                    0x80000001, 0x7fffffff, 0x100, 0x120):
        for value in VALUES:
            yield value, control, rng.getrandbits(32), "separate"
    for _ in range(2048):
        yield rng.getrandbits(32), rng.getrandbits(32), rng.getrandbits(32), "separate"
    if merge:
        for alias in ("source_status", "base_status", "control_status", "shared_operands", "all_status"):
            for control in (0, 1, 31, 32, 33, 127, 128, 224, 225, 255):
                for value in VALUES:
                    yield value, control, rng.getrandbits(32), alias


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mu = load_original(args.exe)
    mu.mem_map(ARENA, 0x1000)
    mu.mem_write(0x528bc0, struct.pack("<I", ARENA + STATUS))
    mu.mem_write(0x5aeb40, struct.pack("<I", ARENA))
    libraries = []
    for path in args.libraries:
        lib = ctypes.CDLL(str(path.resolve()))
        fn = lib.m2_sharc_shift_compute
        fn.argtypes = [ctypes.c_uint32] * 3 + [P32] * 3
        fn.restype = ctypes.c_bool
        libraries.append((path, lib, fn))
    rng = random.Random(5)
    template = rng.randbytes(SIZE)
    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    saved = {UC_X86_REG_EBX: 0xfedcba98, UC_X86_REG_ESI: 0x12345678,
             UC_X86_REG_EDI: 0x87654321, UC_X86_REG_EBP: 0xa5a5a5a5}
    counts, alias_cases = {}, 0
    for opcode, entry in ENTRIES.items():
        merge = opcode in (0x220, 0x224)
        count = 0
        for value, control, status, alias in scenarios(rng, merge):
            arena = bytearray(template)
            src, base, ctrl = 0x380, 0x384, 0x388
            if alias in ("source_status", "all_status"):
                src = STATUS
            if alias in ("base_status", "all_status"):
                base = STATUS
            if alias in ("control_status", "all_status"):
                ctrl = STATUS
            if alias == "shared_operands":
                base = src
            struct.pack_into("<I", arena, STATUS, status)
            struct.pack_into("<I", arena, base, rng.getrandbits(32))
            struct.pack_into("<I", arena, src, value)
            struct.pack_into("<I", arena, ctrl, control)
            struct.pack_into("<III", arena, RECORD + 4, ARENA + ctrl, ARENA + base, ARENA + src)
            if merge:
                value = struct.unpack_from("<I", arena, src)[0]
                control = struct.unpack_from("<I", arena, ctrl)[0]
            initial_status = struct.unpack_from("<I", arena, STATUS)[0]
            mu.mem_write(ARENA, bytes(arena))
            mu.mem_write(SP - 8, bytes(8) + struct.pack("<I", STOP))
            for reg, content in saved.items():
                mu.reg_write(reg, content)
            mu.reg_write(UC_X86_REG_EAX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_ECX, ARENA + RECORD if merge else value)
            mu.reg_write(UC_X86_REG_EDX, rng.getrandbits(32) if merge else control)
            mu.reg_write(UC_X86_REG_ESP, SP)
            mu.reg_write(UC_X86_REG_EFLAGS, 2 | (rng.getrandbits(12) & 0x8d5))
            writes.clear()
            try:
                mu.emu_start(entry, STOP, count=128)
                if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                    raise AssertionError("Original did not return with balanced stack")
                if any(mu.reg_read(reg) != content for reg, content in saved.items()):
                    raise AssertionError("Preserved register changed")
                allowed = {(SP - 4, 4), (ARENA + STATUS, 4)}
                if merge:
                    allowed.add((SP - 8, 4))
                if any(write not in allowed for write in writes):
                    raise AssertionError(f"Unexpected writes: {writes}")
                if bytes(mu.mem_read(SP, 4)) != struct.pack("<I", STOP):
                    raise AssertionError("Return address changed")
                expected = bytes(mu.mem_read(ARENA, SIZE))
                result = mu.reg_read(UC_X86_REG_EAX)
                final_status = struct.unpack_from("<I", expected, STATUS)[0]
                mask = 0x1000 if opcode == 0x2cc else (0x3800 if opcode >= 0x2c0 else 0x2880)
                if (initial_status ^ final_status) & ~mask:
                    raise AssertionError("Unrelated ASTAT bits changed")
                for path, lib, fn in libraries:
                    native = (ctypes.c_uint32 * (SIZE // 4)).from_buffer_copy(arena)
                    ps = ctypes.cast(ctypes.byref(native, STATUS), P32)
                    pb = ctypes.cast(ctypes.byref(native, base), P32) if merge else None
                    output = ctypes.c_uint32(0xdeadbeef)
                    if not fn(opcode, value, control, pb, ps, ctypes.byref(output)):
                        raise AssertionError("Port rejected supported operation")
                    if output.value != result or bytes(native) != expected:
                        raise AssertionError(f"{path.name}: original={result:08x}/{final_status:08x}, "
                                             f"port={output.value:08x}/{ps[0]:08x}")
            except Exception as error:
                raise RuntimeError(f"Entry={entry:08x}, case={count}, value={value:08x}, "
                                   f"control={control:08x}, alias={alias}: {error}") from error
            count += 1
            alias_cases += alias != "separate"
        counts[f"0x{entry:08x}"] = count
    for path, lib, fn in libraries:
        ps, out = ctypes.c_uint32(0x12345678), ctypes.c_uint32(0xabcdef01)
        if fn(0xffffffff, 0, 0, None, ctypes.byref(ps), ctypes.byref(out)) or (ps.value, out.value) != (0x12345678, 0xabcdef01):
            raise AssertionError("Unsupported selector did not reject atomically")
    source = Path(__file__).resolve().parents[1] / "sharc_shift.c"
    receipt = {
        "status": "passed", "scope": "Nine original shift/bit helpers; no full DSP",
        "exe_sha256": EXE_SHA256, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "unicorn": unicorn.__version__, "seed": 5, "entries": counts,
        "cases": sum(counts.values()), "alias_cases": alias_cases,
        "mismatches": 0, "skipped": 0,
        "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p, lib, fn in libraries],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
