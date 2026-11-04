#!/usr/bin/env python3
"""Address generators, transfers and FIFO effects against original x86 bodies.

Half of the indirect transfer cases execute real address generators, the other
half stress callback ABI/state changes with fixtures. Deferred writes/effects
are then drained using their original bodies and the recovered primitives.
"""
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

ADDRESS = tuple(range(0x4B3A70, 0x4B3B20, 16)) + (
    0x4B58C0, 0x4B5920, 0x4B5980, 0x4B59E0, 0x4B5A40, 0x4B5AA0, 0x4B5B00,
    0x4B5B40, 0x4B5B80, 0x4B5BC0, 0x4B5C00, 0x4B5C40, 0x4B5C80, 0x4B5CC0)
TRANSFER = (0x4B5D00, 0x4B5D60, 0x4B5D90, 0x4B5DC0, 0x4B5DF0, 0x4B5E20,
            0x4B5E50, 0x4B5EB0, 0x4B5ED0, 0x4B5EF0, 0x4B5F40, 0x4B5F70,
            0x4B5FA0, 0x4B5FD0, 0x4B5FF0, 0x4B66A0, 0x4B66D0, 0x4B6700)
ACTIVE, RECORD, WC, EC = 0x10481F4, 0x104824C, 0x1048240, 0x1048248
ARENA, CODE = 0x72000000, 0x72010000
REGIONS = ((0x1048100, 0x150), (ARENA, 0x4000))
EDGE = (0, 1, 31, 32, 63, 127, 128, 0x3FE, 0x3FF, 0x400, 0x3FFF, 0x4000,
        0xFFFF, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000)


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x20000)
    functions = []
    for path in libraries:
        lib = C.CDLL(str(path.resolve()))
        group = []
        for name in ('address', 'transfer', 'register', 'control'):
            fn = getattr(lib, 'm2_tgpx4_execute_' + name)
            fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
            fn.restype = C.c_bool
            group.append(fn)
        functions.append(group)
    rng = random.Random(0x4B58C0)
    action = None
    events = []

    def read(at, bits=32):
        return int.from_bytes(uc.mem_read(at, bits // 8), 'little')

    def write(at, value, bits=32):
        uc.mem_write(at, (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little'))

    def record_event(entry, r, read, trace):
        values = [getattr(r, name) for name in NAMES]
        values[3] &= ~0x10  # AF undefined after logical instructions.
        trace.append((entry, r.esp, *values, read(RECORD), read(ACTIVE)))

    def script(read, write, case):
        def execute(entry, r):
            if case & 2:
                write(RECORD, ARENA + 0x100)
                write(ACTIVE, ARENA + 0x600)
                write(0x10481F8, ARENA + 0x2000)
                write(0x10481FC, ARENA + 0x1000)
            r.eax = EDGE[case // 4 % len(EDGE)] if case < 512 else case * 997
            r.ecx ^= 0x98765432
            r.edx ^= 0x12345678
            r.flags = 0x202 | ((case * 17) & 0x8D5)
        return execute

    def boundary(emu, address, size, data):
        r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW), esp=emu.reg_read(UC_X86_REG_ESP))
        record_event(address, r, read, events)
        action(address, r)
        for reg, name in zip(REGS, NAMES):
            emu.reg_write(reg, getattr(r, name))
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    def observe(emu, address, size, data):
        if address in ADDRESS:
            # The body runs unchanged. Top-level calls are not indirect events.
            if emu.reg_read(UC_X86_REG_ESP) != SP:
                r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW), esp=emu.reg_read(UC_X86_REG_ESP))
                record_event(address, r, read, events)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=CODE, end=CODE + 32)
    uc.hook_add(UC_HOOK_CODE, observe, begin=min(ADDRESS), end=max(ADDRESS))

    def run_original(entry):
        uc.reg_write(UC_X86_REG_ESP, SP)
        write(SP, STOP)
        uc.emu_start(entry, STOP, count=512)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4

    def snapshot():
        return ([uc.reg_read(reg) for reg in REGS],
                {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS})

    def drain(read, run, setreg):
        # Match native ordering; these primitives cannot append more effects.
        for i in range(read(EC)):
            run(read(0x1048200 + i * 4))
        for i in range(read(WC)):
            at = 0x1048120 + i * 12
            setreg('ecx', read(at))
            setreg('edx', read(at + 4))
            run(read(at + 8))

    counts, calls, integrated = {}, 0, 0
    for entry in ADDRESS + TRANSFER:
        for case in range(1024):
            for at, size in REGIONS:
                uc.mem_write(at, rng.randbytes(size))
            for at, value in ((ACTIVE, ARENA + 0x400), (RECORD, ARENA),
                              (0x10481F8, ARENA + 0x1000), (0x10481FC, ARENA + 0x2000),
                              (0x10481E0, ARENA + 0x3000), (0x10481E8, ARENA + 0x3100),
                              (0x1048244, CODE + 16), (0x10481EC, CODE + 32),
                              (WC, case % 4), (EC, case % 4)):
                write(at, value)
            # Seed existing queues with real harmless operations, then verify
            # all old and new entries, including 14-bit modifier wraparound.
            for i in range(4):
                write(0x1048200 + i * 4, 0x4B3750)
                write(0x1048120 + i * 12, ARENA + 0x840 + 4 * i)
                write(0x1048124 + i * 12, rng.getrandbits(32))
                write(0x1048128 + i * 12, 0x4B4530)
            limit = EDGE[case % len(EDGE)] if case < 512 else rng.getrandbits(32)
            for state in (ARENA + 0x400, ARENA + 0x600):
                write(state + 0xA0, case % 24)
                write(state + 0xA4, case // 24 % 24)
                write(state + 0x11C, (case % 8 << 8) | (case // 8 % 8 << 12))
                write(state + 0x108, limit)
            for fifo in (ARENA + 0x3000, ARENA + 0x3100):
                write(fifo + 0x80, case % 32)
                write(fifo + 0x84, case // 32 % 32)
                write(fifo + 0x88, (case // 32 % 33))
            write(ARENA + 0x800, limit)
            write(ARENA + 0x804, EDGE[case // 16 % 16] if case < 512 else rng.getrandbits(32))
            for record in (ARENA, ARENA + 0x100):
                for off in (0x30, 0x4C):
                    write(record + off, ADDRESS[case // 2 % len(ADDRESS)] if case & 1 else CODE)
                for off in (0x34, 0x38, 0x50, 0x54):
                    write(record + off, ARENA + 0x800)
                for off in (0x3C, 0x58):
                    write(record + off, ARENA + (0x800 if case & 4 else 0x804))
                write(record + 0x64, case % 64 if case < 512 else rng.getrandbits(32))
            initial = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[1] = limit if entry in (0x4B5FD0, 0x4B5FF0) else ARENA + 0x800
            incoming[2] = ARENA + 0x804
            incoming[3] = 0x202 | (case & 0x8D5)
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F)
            action = script(read, write, case)
            events = []
            run_original(entry)
            expected = [snapshot()]
            drain(read, run_original, lambda name, value: uc.reg_write(REGS[NAMES.index(name)], value))
            expected.append(snapshot())
            calls += len(events)
            integrated += sum(e[0] in ADDRESS for e in events)
            for group in functions:
                memory = {at: bytearray(raw) for at, raw in initial.items()}
                errors, traces = [], []

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

                execute = script(portable_read, portable_write, case)

                def dispatch(target, regs):
                    for fn in group:
                        if fn(target, C.byref(bus), C.byref(regs)):
                            return
                    raise AssertionError(hex(target))

                @CALL
                def call(_, target, regs):
                    try:
                        record_event(target, regs.contents, portable_read, traces)
                        if target in ADDRESS:
                            dispatch(target, regs.contents)
                        else:
                            assert CODE <= target <= CODE + 32
                            execute(target, regs.contents)
                    except Exception as error:
                        errors.append(error)

                bus = Bus(None, READ(lambda _, at, bits: portable_read(at, bits)),
                          WRITE(lambda _, at, value, bits: portable_write(at, value, bits)), call)
                r = Registers(*incoming, 0x37F, esp=SP)
                dispatch(entry, r)
                for phase in range(2):
                    if phase:
                        drain(portable_read, lambda target: dispatch(target, r),
                              lambda name, value: setattr(r, name, value))
                    assert not errors, errors
                    actual = [getattr(r, name) for name in NAMES]
                    actual[3] &= ~0x10
                    expected[phase][0][3] &= ~0x10
                    assert actual == expected[phase][0], (hex(entry), case, phase, 'exit ABI',
                        list(map(hex, actual)), list(map(hex, expected[phase][0])))
                    assert memory == expected[phase][1], (hex(entry), case, phase, 'memory')
                assert traces == events, (hex(entry), case, 'callback ABI', traces, events)
        counts[f'{entry:08x}'] = 1024
    return {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
            'portable_comparisons': sum(counts.values()) * len(functions),
            'original_callback_events': calls, 'integrated_address_calls': integrated,
            'queue_drain': 'original deferred primitives, memory and exit-register comparison',
            'stubbed_original_helpers': ['half of address callbacks', 'external read/write']}


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
