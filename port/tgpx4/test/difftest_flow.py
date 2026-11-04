#!/usr/bin/env python3
"""Native flow/memory primitives with real code and explicit external-call fixtures."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW
from difftest_wrappers import Registers, Bus, READ, WRITE, CALL, U32, REGS, NAMES
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = (0x4B44B0, 0x4B44C0, 0x4B44D0, 0x4B4510, 0x4B4520, 0x4B4530, 0x4B4540,
           0x4B4560, 0x4B4570, 0x4B4590, 0x4B45B0, 0x4B45E0, 0x4B4600, 0x4B4610,
           0x4B4620, 0x4B4630, 0x4B4640, 0x4B4650, 0x4B48C0, 0x4B4910, 0x4B4970,
           0x4B49E0, 0x4B4A50, 0x4B4AA0, 0x4B4AF0, 0x4B4B60, 0x4B4BA0, 0x4B4BF0,
           0x4B4C40, 0x4B4C80, 0x4B4CB0, 0x4B4CE0, 0x4B4D00, 0x4B4D30,
           0x4B4D50, 0x4B4D80, 0x4B4DA0, 0x4B4DD0)
ACTIVE, BASE, RECORD, SAVED_FLAGS = 0x10481F4, 0x10481F0, 0x104824C, 0x10481E4
ARENA, CODE = 0x72000000, 0x72010000
REGIONS = ((0x1048100, 0x150), (0x10ED9A4, 4), (0x10F0040, 4), (ARENA, 0x4000))


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x20000)
    functions = []
    for path in libraries:
        lib = C.CDLL(str(path.resolve()))
        fn = lib.m2_tgpx4_execute_control
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = C.c_bool
        queue = lib.m2_tgpx4_enqueue_write
        queue.argtypes = [C.POINTER(Bus), C.POINTER(Registers), U32, U32]
        queue.restype = None
        functions.append((fn, queue))
    rng = random.Random(0x4B48C0)
    action = None

    def read(at, bits=32):
        return int.from_bytes(uc.mem_read(at, bits // 8), 'little')

    def write(at, value, bits=32):
        uc.mem_write(at, (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little'))

    def script(read, write, case):
        trace = []

        def execute(entry, r):
            values = [getattr(r, name) for name in NAMES]
            values[3] &= ~0x10  # Undefined AF after TEST.
            trace.append((entry, r.esp, *values, read(RECORD), read(ACTIVE)))
            if case & 2:
                write(RECORD, ARENA + 0x100)
                write(ACTIVE, ARENA + 0x600)
            r.eax = (0, 1, 0xFFFFFFFF, 0x80000000, case * 997)[case % 5]
            r.ecx ^= 0x98765432
            r.edx ^= 0x12345678
            r.flags = 0x202 | ((case * 17) & 0x8D5)

        return execute, trace

    def boundary(emu, address, size, data):
        r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW), esp=emu.reg_read(UC_X86_REG_ESP))
        action(address, r)
        for reg, name in zip(REGS, NAMES):
            emu.reg_write(reg, getattr(r, name))
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=CODE, end=CODE)
    counts, calls = {}, 0
    for entry in ENTRIES:
        for case in range(512):
            for at, size in REGIONS:
                uc.mem_write(at, rng.randbytes(size))
            for at, value in ((ACTIVE, ARENA + 0x400), (BASE, rng.getrandbits(32)),
                              (RECORD, ARENA), (SAVED_FLAGS, 0 if case & 1 else 0xFFFFFFFF),
                              (0x10481F8, ARENA + 0x1000), (0x10481FC, ARENA + 0x2000),
                              (0x1048244, CODE), (0x10481EC, CODE),
                              (0x1048240, case % 4), (0x1048248, case % 4)):
                write(at, value)
            limit = (0, 1, 2, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFF, 23)[case % 8]
            for state in (ARENA + 0x400, ARENA + 0x600):
                write(state + 0x124, 1 + case % 4)
                write(state + 0x114, limit)
                write(state + 0x118, limit)
                write(state + 0x120, limit & 0xFFFF, 16)
                write(state + 0x80, 0 if case & 1 else 0xFFFFFFFF)
            for record in (ARENA, ARENA + 0x100):
                write(record + 0x6C, CODE if entry in (0x4B4C40, 0x4B4C80) else 1 << (case % 32))
                write(record + 0x74, ARENA + 0x480)
                write(record + 0x7C, CODE)
            initial = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[1] = ARENA + 0x800
            incoming[3] = 0x202 | (case & 0x8D5)
            args = (rng.getrandbits(32), rng.getrandbits(32))
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.mem_write(SP, struct.pack('<III', STOP, *args))
            action, events = script(read, write, case)
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP
            assert uc.reg_read(UC_X86_REG_ESP) == SP + (12 if entry == 0x4B44D0 else 4)
            expected_regs = [uc.reg_read(reg) for reg in REGS]
            expected = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
            calls += len(events)
            for fn, queue in functions:
                memory = {at: bytearray(raw) for at, raw in initial.items()}
                errors = []

                def locate(at, bits):
                    for base, raw in memory.items():
                        if base <= at and at + bits // 8 <= base + len(raw):
                            return raw, at - base
                    raise AssertionError((hex(entry), case, hex(at), bits))

                def portable_read(at, bits=32):
                    raw, off = locate(at, bits)
                    return int.from_bytes(raw[off:off + bits // 8], 'little')

                def portable_write(at, value, bits=32):
                    raw, off = locate(at, bits)
                    raw[off:off + bits // 8] = (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little')

                execute, traces = script(portable_read, portable_write, case)

                @CALL
                def call(_, target, regs):
                    try:
                        execute(target, regs.contents)
                    except Exception as error:
                        errors.append(error)

                bus = Bus(None, READ(lambda _, at, bits: portable_read(at, bits)),
                          WRITE(lambda _, at, value, bits: portable_write(at, value, bits)), call)
                r = Registers(*incoming, 0x37F, esp=SP)
                if entry == 0x4B44D0:
                    queue(C.byref(bus), C.byref(r), *args)
                else:
                    assert fn(entry, C.byref(bus), C.byref(r))
                assert not errors, errors
                assert traces == events, (hex(entry), case, 'callback ABI', traces, events)
                actual = [getattr(r, name) for name in NAMES]
                actual[3] &= ~0x10
                expected_regs[3] &= ~0x10
                assert actual == expected_regs, (hex(entry), case, 'exit ABI',
                                                 list(map(hex, actual)), list(map(hex, expected_regs)))
                assert memory == expected, (hex(entry), case, 'memory')
        counts[f'{entry:08x}'] = 512
    return {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
            'portable_comparisons': sum(counts.values()) * len(functions),
            'original_callback_events': calls,
            'stubbed_original_helpers': ['record-selected target/operand', 'external read/write']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.exe, args.libraries)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'cases_per_entry'}))
    print(f"Verified {len(report['cases_per_entry'])} entries")


if __name__ == '__main__':
    main()
