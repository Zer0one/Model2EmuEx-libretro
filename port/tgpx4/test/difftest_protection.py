#!/usr/bin/env python3
"""Original protection handlers, normalized to i960 read/write widths.

Synthetic mutable globals; immutable tables come from the pinned executable.
No game ROMs, machine-map integration or x86 scratch-flag equivalence claimed.
"""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from difftest_lifecycle import load_original, SP, STOP
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)

READ = C.CFUNCTYPE(C.c_uint32, C.c_void_p, C.c_uint32, C.c_uint)
WRITE = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint)


class Bus(C.Structure):
    _fields_ = [('opaque', C.c_void_p), ('read', READ), ('write', WRITE), ('call', C.c_void_p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    uc = load_original(args.exe)
    regions = ((0x5aa770, 256), (0x10ed908, 8), (0x10f01b0, 4))
    # Independent byte copies for the portable bus. Fallback reads are constants
    # from the executable, not values computed by an original handler.
    current = {}
    errors = []

    @READ
    def read(_, at, bits):
        for base, data in current.items():
            if base <= at and at + bits//8 <= base + len(data):
                return int.from_bytes(data[at-base:at-base+bits//8], 'little')
        if not (0x508000 <= at < 0x594c00):
            errors.append(('read', hex(at)))
            return 0
        return int.from_bytes(uc.mem_read(at, bits//8), 'little')

    @WRITE
    def write(_, at, value, bits):
        for base, data in current.items():
            if base <= at and at + bits//8 <= base + len(data):
                data[at-base:at-base+bits//8] = (value & ((1 << bits)-1)).to_bytes(bits//8, 'little')
                return
        errors.append(('write', hex(at)))

    bus = Bus(None, read, write, None)
    functions = []
    constant_checks = 0
    for path in args.libraries:
        lib = C.CDLL(str(path.resolve()))
        rd, wr = lib.m2_tgpx4_protection_read, lib.m2_tgpx4_protection_write
        rd.argtypes = [C.POINTER(Bus), C.c_uint32, C.c_uint]
        rd.restype = C.c_uint32
        wr.argtypes = [C.POINTER(Bus), C.c_uint32, C.c_uint32, C.c_uint]
        wr.restype = None
        constant = lib.m2_tgpx4_protection_constant
        constant.argtypes = [C.c_uint32, C.c_uint, C.POINTER(C.c_uint32)]
        constant.restype = C.c_bool
        for base, size in ((0x51b8a0,51), (0x51b8d4,17), (0x51b8e8,11), (0x574d18,144)):
            for width in (8,16,32):
                for offset in range(size-width//8+1):
                    value=C.c_uint32()
                    assert constant(base+offset,width,C.byref(value))
                    assert value.value == int.from_bytes(uc.mem_read(base+offset,width//8),'little')
                    constant_checks += 1
        value=C.c_uint32()
        assert not constant(0x574da8,8,C.byref(value))
        functions.append((rd, wr))
    rng = random.Random(0x4c73d0)
    keys = (0x10, 0x935, 0x1049, 0x113d, 0x1326, 0x13cd, 0x234d, 0x3422,
            0x4d53, 0x556d, 0x7140, 0x7700, 0x983c, 0x9845, 0x98cc,
            0x993d, 0xa1bc, 0xad23)
    cases = [(True, 16, 0x1d9000c, value, 12, 0, 0) for value in range(65536)]
    selectors = (0, 1, 5, 6, 7, 11, 12, 13, 65534, 65535,
                 0x80000000, 0x80000006, *[rng.randrange(65536) for _ in range(32)])
    cases += [(True, 16, 0x1d9000c, key, selector, 9, 2)
              for key in keys for selector in selectors]
    for bits in (8, 16, 32):
        for at in (0x1d90000, 0x1d90008, 0x1d9000c, 0x1d9000e,
                   0x1d8400c, 0x1d87ff8, 0x1d87ff2, 0x1df0000):
            for value in (0, 1, 0xffff, 0xffff0000, 0x12345678):
                cases.append((True, bits, at, value, 7, 3, 0))
            for index in (0, 1, 24, 25, 26, 63, 64):
                for toggle in (0, 1, 2, 0xffffffff):
                    cases.append((False, bits, at, 0, 7, index, toggle))
    for index, (writing, bits, at, value, selector, cursor, toggle) in enumerate(cases):
        initial = {0x5aa770: rng.randbytes(256),
                   0x10ed908: struct.pack('<II', cursor, selector),
                   0x10f01b0: struct.pack('<I', toggle)}
        for base, data in initial.items():
            uc.mem_write(base, data)
        uc.mem_write(SP, struct.pack('<I', STOP))
        for reg, val in ((UC_X86_REG_EAX, 0xdeadbeef), (UC_X86_REG_ECX, at),
                         (UC_X86_REG_EDX, value), (UC_X86_REG_ESP, SP), (UC_X86_REG_EFLAGS, 2)):
            uc.reg_write(reg, val)
        entry = ({8: 0x4c75e0, 16: 0x4c73d0, 32: 0x4c73c0} if writing else
                 {8: 0x4c73b0, 16: 0x4c7340, 32: 0x4c7330})[bits]
        uc.emu_start(entry, STOP, count=1000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
        expected = {base: bytes(uc.mem_read(base, size)) for base, size in regions}
        result = uc.reg_read(UC_X86_REG_EAX) & ((1 << bits)-1)
        for rd, wr in functions:
            current.clear()
            current.update({base: bytearray(data) for base, data in initial.items()})
            if writing:
                wr(C.byref(bus), at, value, bits)
            else:
                assert rd(C.byref(bus), at, bits) == result, (index, hex(entry))
            assert current == expected, (index, hex(entry), hex(value), selector)
            assert not errors, errors
    report = dict(original_executions=len(cases), portable_comparisons=len(cases)*len(functions),
                  all_16bit_commands=True, native_handlers=6, constant_comparisons=constant_checks,
                  scope='Physical-width results and mutable globals; no x86 scratch flags or machine integration')
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
