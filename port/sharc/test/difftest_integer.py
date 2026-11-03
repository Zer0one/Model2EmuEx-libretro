#!/usr/bin/env python3
"""Original integer ALU vs portable C, including inherited x86 entry flags."""
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

ENTRIES = {
    0x01: (0x460f40, "ADD"), 0x02: (0x460fc0, "SUB"),
    0x05: (0x461040, "ADDC"), 0x06: (0x4610c0, "SUBC"),
    0x09: (0x461140, "HALF_SUM"), 0x0a: (0x4611a0, "COMPARE"),
    0x21: (0x4614e0, "PASS"), 0x22: (0x4613e0, "NEGATE"),
    0x25: (0x4611e0, "INCREMENT_C"), 0x26: (0x461260, "DECREMENT_C"),
    0x29: (0x4612e0, "INCREMENT"), 0x2a: (0x461360, "DECREMENT"),
    0x30: (0x461460, "ABS"), 0x40: (0x461520, "AND"),
    0x41: (0x461560, "OR"), 0x42: (0x4615a0, "XOR"),
    0x43: (0x4615e0, "NOT"), 0x61: (0x461620, "MIN"),
    0x62: (0x461660, "MAX"),
}
ARENA, SIZE, STATUS = 0x72000000, 0x300, 0x240
P32 = ctypes.POINTER(ctypes.c_uint32)
EDGES = (0, 1, 2, 0x7ffffffe, 0x7fffffff, 0x80000000, 0x80000001,
         0xfffffffe, 0xffffffff, 0x55555555, 0xaaaaaaaa, 0x10000, 0xffff0000)
ENTRY_FLAGS = tuple(2 | (i & 1) | ((i & 2) << 5) | ((i & 4) << 5) for i in range(8))


def scenarios(rng):
    # Boundary pairs under both guest carry states and all host CF/ZF/SF inputs.
    for lhs in EDGES:
        for rhs in EDGES:
            for status in (0, 8, 0xffffffff, 0xfffffff7):
                for flags in ENTRY_FLAGS:
                    yield lhs, rhs, status, flags
    # Isolate every ASTAT bit; also exercise each low ALU flag combination.
    for status in list(range(64)) + [1 << bit for bit in range(32)]:
        for lhs, rhs in ((0, 0), (0xffffffff, 1), (0x7fffffff, 1), (0x80000000, 1)):
            yield lhs, rhs, status, ENTRY_FLAGS[status & 7]
    # Full-width values/state and unrelated host OF/AF/PF variability.
    for _ in range(2048):
        flags = ENTRY_FLAGS[rng.randrange(8)] | (rng.getrandbits(12) & 0x814)
        yield rng.getrandbits(32), rng.getrandbits(32), rng.getrandbits(32), flags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--aux", action="store_true")
    args = parser.parse_args()
    entries = {entry: (entry, name) for entry, name in ((0x4bc200,"ZERO_STUB"), (0x4bc240,"CLIP"),
        (0x4bc600,"MULTIPLY_LOW"), (0x4bc630,"PASS_630"), (0x4bc640,"PASS_640"), (0x462480,"COPY_SIGN_BITS"))} if args.aux else ENTRIES
    mu = load_original(args.exe)
    mu.mem_map(ARENA, 0x1000)
    mu.mem_write(0x528bc0, struct.pack("<I", ARENA + STATUS))
    mu.mem_write(0x5aeb40, struct.pack("<I", ARENA))
    libraries = []
    for path in args.libraries:
        lib = ctypes.CDLL(str(path.resolve()))
        fn = lib.m2_sharc_integer_compute
        fn.argtypes = [ctypes.c_uint32] * 4 + [P32, P32]
        fn.restype = ctypes.c_bool
        if args.aux:
            aux = lib.m2_sharc_aux
            aux.argtypes = [ctypes.c_uint32]*3 + [P32,P32]
            aux.restype = ctypes.c_bool
            def fn(op,lhs,rhs,flags,status,result,aux=aux):
                return aux(op,lhs,rhs,status,result)
        libraries.append((path, lib, fn))
    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE,
                lambda uc, access, addr, size, value, user: writes.append((addr, size)))
    rng = random.Random(4)
    template = rng.randbytes(SIZE)
    preserved = {UC_X86_REG_EBX: 0xabcdef01, UC_X86_REG_ESI: 0x12345678,
                 UC_X86_REG_EDI: 0x87654321, UC_X86_REG_EBP: 0x5a5a5a5a}
    counts, witnesses = {}, []
    for opcode, (entry, name) in entries.items():
        count = 0
        for lhs, rhs, status, flags in scenarios(rng):
            arena = bytearray(template)
            struct.pack_into("<I", arena, STATUS, status)
            mu.mem_write(ARENA, bytes(arena))
            mu.mem_write(SP - 4, struct.pack("<II", 0xa5a5a5a5, STOP))
            for reg, value in preserved.items():
                mu.reg_write(reg, value)
            mu.reg_write(UC_X86_REG_EAX, rng.getrandbits(32))
            mu.reg_write(UC_X86_REG_ECX, lhs)
            mu.reg_write(UC_X86_REG_EDX, rhs)
            mu.reg_write(UC_X86_REG_ESP, SP)
            mu.reg_write(UC_X86_REG_EFLAGS, flags)
            writes.clear()
            try:
                mu.emu_start(entry, STOP, count=128)
                if mu.reg_read(UC_X86_REG_EIP) != STOP or mu.reg_read(UC_X86_REG_ESP) != SP + 4:
                    raise AssertionError("Original did not return with balanced stack")
                if any(mu.reg_read(reg) != value for reg, value in preserved.items()):
                    raise AssertionError("Original changed a preserved register")
                if any(write not in {(SP - 4, 4), (ARENA + STATUS, 4)} for write in writes):
                    raise AssertionError(f"Unexpected writes: {writes}")
                if bytes(mu.mem_read(SP, 4)) != struct.pack("<I", STOP):
                    raise AssertionError("Original modified return address")
                expected = bytes(mu.mem_read(ARENA, SIZE))
                result = mu.reg_read(UC_X86_REG_EAX)
                final_status = struct.unpack_from("<I", expected, STATUS)[0]
                if (final_status ^ status) & ~(0x40 if args.aux else 0x43f):
                    raise AssertionError("Original changed status outside the ALU mask")
                for path, lib, fn in libraries:
                    native = (ctypes.c_uint32 * (SIZE // 4)).from_buffer_copy(arena)
                    status_ptr = ctypes.cast(ctypes.byref(native, STATUS), P32)
                    output = ctypes.c_uint32(0xdeadbeef)
                    if not fn(opcode, lhs, rhs, flags, status_ptr, ctypes.byref(output)):
                        raise AssertionError("Port rejected a supported operation")
                    if output.value != result or bytes(native) != expected:
                        raise AssertionError(
                            f"{path.name}: original={result:08x}/{final_status:08x}, "
                            f"port={output.value:08x}/{status_ptr[0]:08x}")
            except Exception as error:
                raise RuntimeError(
                    f"{name} @{entry:08x}, case={count}, lhs={lhs:08x}, rhs={rhs:08x}, "
                    f"ASTAT={status:08x}, EFLAGS={flags:08x}: {error}") from error
            if name in ("INCREMENT", "DECREMENT", "NOT") and lhs == 0 and rhs == 0 and status == 0:
                witnesses.append({"operation": name, "entry_eflags": flags,
                                  "result": result, "status": final_status})
            count += 1
        counts[name] = {"entry": f"0x{entry:08x}", "cases": count}
    # The subset must reject unsupported selectors atomically, never invent an opcode.
    for path, lib, fn in libraries:
        for opcode in (0, 3, 0x63, 0x81, 0x10201, 0xffffffff):
            status, output = ctypes.c_uint32(0x12345678), ctypes.c_uint32(0xabcdef01)
            if fn(opcode, 1, 2, 2, ctypes.byref(status), ctypes.byref(output)):
                raise AssertionError(f"{path.name}: accepted unsupported selector {opcode:x}")
            if (status.value, output.value) != (0x12345678, 0xabcdef01):
                raise AssertionError("Unsupported selector changed outputs")
    source = Path(__file__).resolve().parents[1] / ("sharc_aux.c" if args.aux else "sharc_integer.c")
    receipt = {
        "status": "passed", "scope": "6 auxiliary integer helpers" if args.aux else "19 integer helpers, not full DSP or dispatcher",
        "exe_sha256": EXE_SHA256, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "unicorn": unicorn.__version__, "seed": 4, "entries": counts,
        "cases": sum(item["cases"] for item in counts.values()),
        "mismatches": 0, "skipped": 0, "entry_flag_witnesses": witnesses,
        "libraries": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p, lib, fn in libraries],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "entry_flag_witnesses"}, indent=2))


if __name__ == "__main__":
    main()
