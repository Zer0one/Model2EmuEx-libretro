#!/usr/bin/env python3
"""Compare all execution wrappers with mutating indirect callback fixtures."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS,
    UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW,
)
from difftest_execute import Registers, Bus, READ, WRITE, CALL, U32
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = (0x4B3550, 0x4B3560, 0x4B35A0, 0x4B35E0, 0x4B3630, 0x4B3690, 0x4B36E0)
REGS = (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS,
        UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI)
NAMES = ('eax', 'ecx', 'edx', 'flags', 'ebx', 'ebp', 'esi', 'edi')
ACTIVE, RECORD, SAVED_FLAGS = 0x10481F4, 0x104824C, 0x10481E4
ARENA, CODE = 0x72000000, 0x72010000


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x20000)
    functions = []
    for path in libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_execute_wrapper
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = None
        functions.append(fn)
    rng = random.Random(0x4B3550)
    action = None

    def read(at, bits=32):
        return int.from_bytes(uc.mem_read(at, bits // 8), 'little')

    def write(at, value, bits=32):
        uc.mem_write(at, (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little'))

    def script(read, write, case):
        trace = []

        def execute(entry, r):
            trace.append((entry, r.esp, *(getattr(r, name) for name in NAMES), read(RECORD),
                          read(ACTIVE), read(SAVED_FLAGS)))
            if case & 1:
                write(RECORD, ARENA + (0x100 if len(trace) & 1 else 0))
            if case & 2:
                write(ACTIVE, ARENA + 0x400 + (0x200 if len(trace) & 1 else 0))
            r.eax = (entry * 3 + len(trace)) & 0xFFFFFFFF
            r.ecx ^= 0x98765432
            r.edx ^= 0x12345678
            r.flags = 0x202 | ((case * 17 + len(trace)) & 0x8D5)

        return execute, trace

    def boundary(emu, address, size, data):
        r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW), esp=emu.reg_read(UC_X86_REG_ESP))
        action(address, r)
        for reg, name in zip(REGS, NAMES):
            emu.reg_write(reg, getattr(r, name))
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=CODE, end=CODE + 0x400)
    counts, calls = {}, 0
    for entry in ENTRIES:
        for case in range(512):
            initial = bytearray(rng.randbytes(0x1000))
            for base in (0, 0x100):
                for i, offset in enumerate((0x0C, 0x20, 0x28, 0x44, 0x08, 0x1C, 0x2C, 0x48, 0x68)):
                    struct.pack_into('<I', initial, base + offset, CODE + base + i * 16)
            uc.mem_write(ARENA, bytes(initial))
            globals_before = {ACTIVE: ARENA + 0x400, RECORD: ARENA, SAVED_FLAGS: rng.getrandbits(32)}
            for at, value in globals_before.items():
                write(at, value)
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[3] = 0x202 | (case & 0x8D5)
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F)
            uc.reg_write(UC_X86_REG_ESP, SP)
            write(SP, STOP)
            action, events = script(read, write, case)
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
            expected_regs = tuple(uc.reg_read(reg) for reg in REGS)
            expected_globals = {at: read(at) for at in globals_before}
            calls += len(events)
            for fn in functions:
                memory = bytearray(initial)
                globals_copy = dict(globals_before)

                def portable_read(at, bits=32):
                    if at in globals_copy:
                        return globals_copy[at]
                    assert ARENA <= at and at + bits // 8 <= ARENA + len(memory)
                    return int.from_bytes(memory[at - ARENA:at - ARENA + bits // 8], 'little')

                def portable_write(at, value, bits=32):
                    assert at in globals_copy and bits == 32
                    globals_copy[at] = value

                execute, traces = script(portable_read, portable_write, case)
                bus = Bus(None, READ(lambda _, at, bits: portable_read(at, bits)),
                          WRITE(lambda _, at, value, bits: portable_write(at, value, bits)),
                          CALL(lambda _, target, regs: execute(target, regs.contents)))
                r = Registers(*incoming, 0x37F, esp=SP)
                fn(entry, C.byref(bus), C.byref(r))
                assert traces == events, (hex(entry), case, 'callback ABI', traces, events)
                assert tuple(getattr(r, name) for name in NAMES) == expected_regs, (hex(entry), case, 'exit ABI')
                assert globals_copy == expected_globals
                assert memory == uc.mem_read(ARENA, len(memory))
        counts[f'{entry:08x}'] = 512
    return {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
            'portable_comparisons': sum(counts.values()) * len(functions),
            'original_callback_events': calls, 'indirect_operation_bodies': 'fixtures'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.exe, args.libraries)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
