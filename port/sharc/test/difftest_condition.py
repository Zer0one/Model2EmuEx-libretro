#!/usr/bin/env python3
"""Original condition tables and two integer dispatchers vs portable C.

Eight additional handler prefixes are stopped at helper entry to audit flags;
that evidence is deliberately separate from full-dispatch differential coverage.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI,
    UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS,
)
from difftest_bits import load_original, EXE_SHA256, STOP, SP
from difftest_integer import ENTRIES, EDGES, ENTRY_FLAGS

ARENA, SIZE, STATUS, RECORD = 0x72000000, 0x800, 0x240, 0x300
STOP_FLAG = 0x10ed950
FLAG_MASK = 0x8c5  # CF/PF/ZF/SF/OF; TEST's undefined AF is not a contract.
P32 = C.POINTER(C.c_uint32)


class Record(C.Structure):
    _fields_ = [("condition", C.c_uint), ("operation", C.c_uint),
                ("lhs", P32), ("rhs", P32), ("destination", P32),
                ("move_source", P32), ("move_destination", P32)]


def put(data, offset, value):
    struct.pack_into("<I", data, offset, value)


def pointer(data, offset):
    return C.cast(C.byref(data, offset), P32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mu = load_original(args.exe)
    mu.mem_map(ARENA, 0x1000)
    # Read original tables from the pinned image, not a second hand-written map.
    tables = [struct.unpack("<32I", mu.mem_read(address, 128))
              for address in (0x573490, 0x573510)]
    for address, value in ((0x5aeb40, ARENA), (0x5aeb10, ARENA + RECORD),
                           (0x528bc0, ARENA + STATUS)):
        mu.mem_write(address, struct.pack("<I", value))
    libs = []
    for path in args.libraries:
        lib = C.CDLL(str(path.resolve()))
        lib.m2_sharc_condition.argtypes = [C.c_uint, C.c_uint, C.c_uint32, C.c_uint32, P32, P32]
        lib.m2_sharc_condition.restype = C.c_bool
        lib.m2_sharc_dispatch_integer.argtypes = [C.POINTER(Record), C.c_bool, C.c_uint32, P32, P32]
        lib.m2_sharc_dispatch_integer.restype = C.c_bool
        lib.m2_sharc_integer_supported.argtypes = [C.c_uint32]
        lib.m2_sharc_integer_supported.restype = C.c_bool
        libs.append((path, lib))
    preserved = {UC_X86_REG_EBX: 0xabcdef01, UC_X86_REG_ESI: 0x12345678,
                 UC_X86_REG_EDI: 0x87654321, UC_X86_REG_EBP: 0x5a5a5a5a}
    writes, helper_flags = [], []
    observed_condition = []
    capture = {"entry": 0, "prefix": False}

    def code_hook(uc, address, size, user):
        if address in (0x4bcb1a, 0x4bcb5a):
            observed_condition.append(uc.reg_read(UC_X86_REG_EAX))
        if address == capture["entry"]:
            helper_flags.append(uc.reg_read(UC_X86_REG_EFLAGS) & FLAG_MASK)
            if capture["prefix"]:
                uc.emu_stop()

    mu.hook_add(UC_HOOK_CODE, code_hook)
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    rng = random.Random(6)
    template = rng.randbytes(SIZE)

    def run(entry, data, stop, flags, allowed=()):
        mu.mem_write(ARENA, bytes(data))
        mu.mem_write(STOP_FLAG, struct.pack("<I", stop))
        mu.mem_write(SP - 64, bytes(64) + struct.pack("<I", STOP))
        for reg, value in preserved.items():
            mu.reg_write(reg, value)
        mu.reg_write(UC_X86_REG_ESP, SP)
        mu.reg_write(UC_X86_REG_EFLAGS, flags)
        writes.clear()
        helper_flags.clear()
        observed_condition.clear()
        mu.emu_start(entry, STOP, count=256)
        if capture["prefix"]:
            if mu.reg_read(UC_X86_REG_EIP) != capture["entry"] or len(helper_flags) != 1:
                raise AssertionError("Prefix did not reach compute helper")
        else:
            if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                raise AssertionError("Unbalanced original return")
            if any(mu.reg_read(reg) != value for reg, value in preserved.items()):
                raise AssertionError("Original changed preserved registers")
        for addr, size in writes:
            if size == 4 and (SP - 64 <= addr < SP or addr == STOP_FLAG or addr in allowed):
                continue
            raise AssertionError(f"Unexpected write {addr:08x}/{size}")
        if bytes(mu.mem_read(SP, 4)) != struct.pack("<I", STOP):
            raise AssertionError("Return address changed")
        return (bytes(mu.mem_read(ARENA, SIZE)),
                struct.unpack("<I", mu.mem_read(STOP_FLAG, 4))[0],
                mu.reg_read(UC_X86_REG_EAX))

    statuses = list(range(256)) + [1 << bit for bit in range(32)]
    statuses += [0xffffffff ^ (1 << bit) for bit in range(32)]
    statuses += [rng.getrandbits(32) for _ in range(256)]
    condition_cases = 0
    for table in range(2):
        for code, entry in enumerate(tables[table]):
            # All low flag combinations, each isolated bit/hole, full-width data;
            # explicit loop/stop boundaries supplement cycling randomized cases.
            cases = [(status, (0, 1, 2, 0xffffffff)[i % 4], (0, 1, 7)[i % 3])
                     for i, status in enumerate(statuses)]
            cases += [(status, loop, stop) for status in (0, 0xffffffff)
                      for loop in (0, 1, 2, 0xffffffff) for stop in (0, 1, 7)]
            for status, loop, stop in cases:
                data = bytearray(template)
                put(data, STATUS, status)
                put(data, 0x18, loop)
                expected, expected_stop, result = run(entry, data, stop, ENTRY_FLAGS[condition_cases % 8])
                if expected != data:
                    raise AssertionError("Condition changed the state arena")
                for path, lib in libs:
                    native_stop, native_result = C.c_uint32(stop), C.c_uint32(0xdeadbeef)
                    ok = lib.m2_sharc_condition(table, code, status, loop,
                                               C.byref(native_stop), C.byref(native_result))
                    if not ok or (native_stop.value, native_result.value) != (expected_stop, result):
                        raise AssertionError(f"{path.name}: condition {table}/{code}, "
                                             f"status={status:x}, loop={loop}, stop={stop}: "
                                             f"original={expected_stop:x}/{result:x}, "
                                             f"port={native_stop.value:x}/{native_result.value:x}")
                condition_cases += 1
    print(f"Conditions: {condition_cases} passed", flush=True)

    # Offsets: lhs, rhs, result, move source, move destination. Snapshot and
    # write ordering must survive aliases, including ASTAT itself.
    layouts = [(0x400, 0x404, 0x408, 0x40c, 0x410),
               (STATUS, 0x404, 0x408, STATUS, 0x410),
               (0x400, STATUS, STATUS, 0x408, 0x410),
               (0x400, 0x404, 0x400, 0x400, 0x408),
               (0x400, 0x400, 0x408, 0x404, 0x408),
               (0x400, 0x404, 0x408, STATUS, STATUS)]
    dispatch_cases = 0
    dispatch_statuses = [0, 0xffffffff] + [1 << b for b in (0, 1, 2, 3, 6, 7, 11, 12, 18, 19, 20, 21, 22)]
    for move, entry in ((False, 0x4bcb50), (True, 0x4bcb10)):
        for code in range(32):
            for op, (compute, name) in ENTRIES.items():
                capture["entry"] = compute
                for index, status in enumerate(dispatch_statuses):
                    for layout in layouts:
                        loop, stop = (0, 1, 2, 0xffffffff)[index % 4], (0, 1, 7)[index % 3]
                        data = bytearray(template)
                        for off in (0x400, 0x404, 0x408, 0x40c, 0x410):
                            put(data, off, EDGES[rng.randrange(len(EDGES))])
                        put(data, STATUS, status)
                        put(data, 0x18, loop)
                        put(data, RECORD + 4, compute)
                        put(data, RECORD + 8, tables[0][code])
                        for field, offset in zip((0x34, 0x38, 0x3c, 0x28, 0x24), layout):
                            put(data, RECORD + field, ARENA + offset)
                        expected, expected_stop, _ = run(entry, data, stop, ENTRY_FLAGS[index % 8] | 0x814,
                                                        (ARENA + STATUS, ARENA + layout[2], ARENA + layout[4]))
                        condition, = observed_condition
                        expected_flags = [] if condition == 0 else [
                            (4 if (condition & 255).bit_count() % 2 == 0 else 0) |
                            (0x80 if condition & 0x80000000 else 0)]
                        if helper_flags != expected_flags:
                            raise AssertionError(f"Unexpected helper flags: {helper_flags}, condition={condition:x}")
                        for path, lib in libs:
                            native = (C.c_uint32 * (SIZE // 4)).from_buffer_copy(data)
                            rec = Record(code, op, *(pointer(native, offset) for offset in layout))
                            native_stop = C.c_uint32(stop)
                            if not lib.m2_sharc_dispatch_integer(C.byref(rec), move, loop,
                                                               pointer(native, STATUS), C.byref(native_stop)):
                                raise AssertionError("Supported dispatch rejected")
                            if bytes(native) != expected or native_stop.value != expected_stop:
                                raise AssertionError(f"{path.name}: dispatch {entry:x}/{code}/{name}, "
                                                     f"status={status:x}, layout={layout}")
                        dispatch_cases += 1
    print(f"Full integer dispatch: {dispatch_cases} passed", flush=True)

    # False conditions must not dereference operand pointers at all.
    capture["entry"] = ENTRIES[0x43][0]
    for move, entry in ((False, 0x4bcb50), (True, 0x4bcb10)):
        data = bytearray(template)
        put(data, RECORD + 4, capture["entry"])
        put(data, RECORD + 8, tables[0][14])  # Always false.
        for field in (0x34, 0x38, 0x3c, 0x28, 0x24):
            put(data, RECORD + field, 0)
        expected, expected_stop, _ = run(entry, data, 7, 0x8c7)
        for path, lib in libs:
            native = (C.c_uint32 * (SIZE // 4)).from_buffer_copy(data)
            rec, native_stop = Record(14, 0x43), C.c_uint32(7)
            if not lib.m2_sharc_dispatch_integer(C.byref(rec), move, 0, pointer(native, STATUS), C.byref(native_stop)):
                raise AssertionError("False condition rejected")
            if bytes(native) != expected or native_stop.value != expected_stop or helper_flags:
                raise AssertionError("False condition had side effects")
        dispatch_cases += 1

    # Stop at helper entry, before memory callbacks: this is flag provenance
    # evidence only. Never count these as implemented full dispatchers.
    capture["prefix"] = True
    prefix_counts = {}
    for conditional, entries in ((True, (0x4bd810, 0x4bd890, 0x4bd910, 0x4bd990)),
                                  (False, (0x4bddb0, 0x4bde20, 0x4bdea0, 0x4bdf20))):
        for entry in entries:
            for bits in range(32):
                flags = 2 | (bits & 1) | ((bits & 2) << 1) | ((bits & 4) << 4) | ((bits & 8) << 4) | ((bits & 16) << 7)
                data = bytearray(template)
                put(data, RECORD + 4, capture["entry"])
                put(data, RECORD + 8, tables[0][14])
                for field in (0x24, 0x28, 0x34, 0x38, 0x3c):
                    put(data, RECORD + field, ARENA + 0x400)
                run(entry, data, 0, flags)
                if helper_flags != [0x44 if conditional else flags & FLAG_MASK]:
                    raise AssertionError(f"Prefix flags {entry:x}: {helper_flags}, input={flags:x}")
            prefix_counts[f"0x{entry:08x}"] = {"cases": 32, "flags": "TEST zero: ZF/PF set" if conditional else "inherited handler entry flags"}

    for path, lib in libs:
        for op in range(256):
            if lib.m2_sharc_integer_supported(op) != (op in ENTRIES):
                raise AssertionError("Support predicate mismatch")
        for table, code in ((2, 0), (0, 32), (0xffffffff, 0xffffffff)):
            stop, result = C.c_uint32(7), C.c_uint32(9)
            if lib.m2_sharc_condition(table, code, 0, 0, C.byref(stop), C.byref(result)) or (stop.value, result.value) != (7, 9):
                raise AssertionError("Invalid condition mutated outputs")
        for code, op in ((32, 1), (9, 0), (9, 0x81)):
            # ASTAT would set stop if validation happened after condition evaluation.
            rec, status, stop = Record(code, op), C.c_uint32(0xffffffff), C.c_uint32(7)
            if lib.m2_sharc_dispatch_integer(C.byref(rec), True, 0, C.byref(status), C.byref(stop)) or (status.value, stop.value) != (0xffffffff, 7):
                raise AssertionError("Unsupported dispatch was not atomic")

    root = Path(__file__).resolve().parents[1]
    sources = [root / name for name in ("sharc_condition.c", "sharc_condition.h", "sharc_integer.c", "sharc_integer.h")]
    receipt = {"status": "passed", "exe_sha256": EXE_SHA256, "unicorn": unicorn.__version__, "seed": 6,
               "condition_cases": condition_cases, "condition_distinct_entries": len(set(tables[0] + tables[1])),
               "tables": [[f"0x{x:08x}" for x in table] for table in tables],
               "dispatch_cases": dispatch_cases, "dispatch_entries": ["0x004bcb50", "0x004bcb10"],
               "prefix_only": prefix_counts, "mismatches": 0, "skipped": 0,
               "sources": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
               "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p, lib in libs]}
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "tables"}, indent=2))


if __name__ == "__main__":
    main()
