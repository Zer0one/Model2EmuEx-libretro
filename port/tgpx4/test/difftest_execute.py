#!/usr/bin/env python3
"""Native M2C scheduler: FIFO stalls, queues, delayed dispatch and repeat state.

Only instruction/effect bodies are fixtures. The original scheduler runs
unmodified; callback-entry registers/flags, memory and event order are checked.
"""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS,
    UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_EDI, UC_X86_REG_ESI,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW,
)
from difftest_lifecycle import load_original, SP, STOP

U32 = C.c_uint32
STATE, ACTIVE, BASE, RECORD = 0x10EDEF0, 0x10481F4, 0x10481F0, 0x104824C
STOPPED, DELAY = 0x10F0040, 0x10ED9A4
EFFECT_COUNT, WRITE_COUNT, EFFECTS, WRITES = 0x1048248, 0x1048240, 0x1048200, 0x1048120
ARENA, RECORDS, INPUT, OUTPUT, ALTERNATE, CODE = (0x72000000, 0x72000000, 0x72008000,
                                               0x72008100, 0x72008200, 0x72010000)
ENTRY, STRIDE = 0x4B6010, 0x94
REGS = (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS)
PRESERVED = (UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_EDI, UC_X86_REG_ESI)
REGIONS = ((0x1048100, 0x150), (STATE, 0x150), (STOPPED, 12), (DELAY, 4), (ARENA, 0x9000))


class Registers(C.Structure):
    _fields_ = [(name, U32) for name in ('eax', 'ecx', 'edx', 'flags', 'ebx', 'ebp', 'esi', 'edi')] + [('fp_control', C.c_uint16), ('fp_status', C.c_uint16), ('esp', U32)]


READ = C.CFUNCTYPE(U32, C.c_void_p, U32, C.c_uint)
WRITE = C.CFUNCTYPE(None, C.c_void_p, U32, U32, C.c_uint)
CALL = C.CFUNCTYPE(None, C.c_void_p, U32, C.POINTER(Registers))


class Bus(C.Structure):
    _fields_ = [('opaque', C.c_void_p), ('read', READ), ('write', WRITE), ('call', CALL)]


def scenario(read, write, case, initial_control):
    trace, steps = [], [0]
    mode = case % 16
    limit = 1003 if case in (254, 255) else 1 + case % 4

    def execute(entry, r):
        trace.append((entry, r.esp, r.eax, r.ecx, r.edx, r.flags & 0x8D5, r.fp_control | 0x40, r.ebx, r.ebp, r.esi, r.edi,
                      read(RECORD), read(ACTIVE), read(read(ACTIVE) + 0x114),
                      read(EFFECT_COUNT), read(WRITE_COUNT), read(STATE + 0x144)))
        if entry == CODE:
            steps[0] += 1
            if steps[0] >= limit:
                write(STOPPED, 1)
            if mode >= 4:
                write(EFFECT_COUNT, 2)
                write(EFFECTS, CODE + 32)
                write(EFFECTS + 4, CODE + 48)
                write(EFFECTS + 8, CODE + 64)
                write(WRITE_COUNT, 2)
                for n in range(3):
                    write(WRITES + n * 12, 0x11220000 + n)
                    write(WRITES + n * 12 + 4, 0x33440000 + n)
                    write(WRITES + n * 12 + 8, CODE + 80 + n * 16)
            if mode in (8, 9, 10, 11) and steps[0] == 1:
                write(DELAY, 7)
                write(read(ACTIVE) + 0x114, 2)
            if mode == 12 and steps[0] == 1:
                # No delay: callback may replace the cursor/active state.
                write(RECORD, RECORDS + STRIDE)
                write(ACTIVE, ALTERNATE)
            if mode == 13 and steps[0] == 1:
                write(read(ACTIVE) + 0x110, 0x4000)
                write(read(ACTIVE) + 0x122, 1, 16)
            if case in (254, 255):
                # Keep a finite record arena while crossing the 1000-op batch.
                write(RECORD, RECORDS - STRIDE)
                if steps[0] == 1000:
                    write(STATE + 0x148, 0x76543210)
                    write(STATE + 0x14C, 0x12345678)
                    r.fp_control = 0xB7F
        elif entry == CODE + 16:
            # Delayed instruction runs despite STOP and without FIFO gates.
            write(EFFECT_COUNT, 1)
            write(EFFECTS, CODE + 48)
            write(WRITE_COUNT, 1)
            write(WRITES, 0x55667788)
            write(WRITES + 4, 0x99AABBCC)
            write(WRITES + 8, CODE + 96)
            write(read(ACTIVE) + 0x114, 0x999)
            if mode == 11:
                write(ACTIVE, ALTERNATE)
        elif entry == CODE + 32:
            if mode in (5, 9):
                write(EFFECT_COUNT, 3)
            elif mode == 6:
                write(EFFECT_COUNT, 0)
        elif entry == CODE + 80:
            if mode in (5, 10):
                write(WRITE_COUNT, 3)
            elif mode == 7:
                write(WRITE_COUNT, 0)
        # Deliberately change caller-saved registers and flags on every return.
        r.eax = (entry * 3 + steps[0]) & 0xFFFFFFFF
        r.ecx ^= 0x89ABCDEF
        r.edx ^= 0x76543210
        r.flags = 0x202 | ((case * 17) & 0x8D5)

    return execute, trace, steps


def compare(exe, libraries, batch=False):
    entry = 0x4B4660 if batch else ENTRY
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x20000)
    functions = []
    for path in libraries:
        fn = getattr(C.CDLL(str(path.resolve())), "m2_tgpx4_execute_batch" if batch else "m2_tgpx4_execute")
        fn.argtypes = [C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = None
        functions.append(fn)

    def read(at, bits=32):
        return int.from_bytes(uc.mem_read(at, bits // 8), 'little')

    def write(at, value, bits=32):
        uc.mem_write(at, int(value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little'))

    native_execute = None

    def boundary(emu, address, size, data):
        r = Registers(*(emu.reg_read(reg) for reg in REGS),
                      *(emu.reg_read(reg) for reg in (UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI)),
                      emu.reg_read(UC_X86_REG_FPCW), esp=emu.reg_read(UC_X86_REG_ESP))
        native_execute(address, r)
        for reg, name in zip(REGS, ('eax', 'ecx', 'edx', 'flags')):
            emu.reg_write(reg, getattr(r, name))
        emu.reg_write(UC_X86_REG_FPCW, r.fp_control)
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=CODE, end=CODE + 112)
    rng = random.Random(ENTRY)
    total_calls = 0
    for case in range(256):
        for at, size in REGIONS:
            uc.mem_write(at, rng.randbytes(size))
        mode = case % 16
        write(STATE + 0x140, RECORDS)
        write(STATE + 0x144, RECORDS)
        write(STATE + 0x114, 0)
        write(STATE + 0x110, 0x4000 if mode in (14, 15) and case < 254 else 0)
        write(STATE + 0x122, (0, 1, 2, 65535)[case // 16 % 4], 16)
        write(ALTERNATE + 0x110, 0)
        write(ALTERNATE + 0x114, 1)
        write(0x10F0048, INPUT)
        write(0x10F0044, OUTPUT)
        write(STOPPED, 1 if mode == 0 else 0)
        write(DELAY, 0)
        write(INPUT + 0x88, 32 if mode in (1, 3) else 31)
        write(OUTPUT + 0x88, 0 if mode in (2, 3) else 1)
        for n in range(16):
            write(RECORDS + n * STRIDE + 0x80, CODE + (16 if n == 7 else 0))
            write(RECORDS + n * STRIDE + 0x84, 1)
            write(RECORDS + n * STRIDE + 0x88, 1)
        initial = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
        incoming = [rng.getrandbits(32) for _ in range(3)] + [0x202]
        control = 0x37F
        native_execute, events, steps = scenario(read, write, case, control)
        for reg, value in zip(REGS, incoming):
            uc.reg_write(reg, value)
        preserved = [rng.getrandbits(32) for _ in PRESERVED]
        for reg, value in zip(PRESERVED, preserved):
            uc.reg_write(reg, value)
        uc.reg_write(UC_X86_REG_FPCW, control)
        uc.reg_write(UC_X86_REG_ESP, SP)
        write(SP, STOP)
        try:
            uc.emu_start(entry, STOP, count=1000000)
        except Exception as error:
            raise AssertionError((case, hex(uc.reg_read(UC_X86_REG_EIP)), events[-3:])) from error
        assert uc.reg_read(UC_X86_REG_EIP) == STOP, (case, 'execution budget')
        assert uc.reg_read(UC_X86_REG_ESP) == SP + 4
        assert [uc.reg_read(reg) for reg in PRESERVED] == preserved
        expected = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
        total_calls += len(events)
        for fn in functions:
            memory = {at: bytearray(raw) for at, raw in initial.items()}

            def locate(at, bits):
                for base, raw in memory.items():
                    if base <= at and at + bits // 8 <= base + len(raw):
                        return raw, at - base
                raise AssertionError((case, hex(at), bits, 'unmapped'))

            def portable_read(at, bits=32):
                raw, off = locate(at, bits)
                return int.from_bytes(raw[off:off + bits // 8], 'little')

            def portable_write(at, value, bits=32):
                raw, off = locate(at, bits)
                raw[off:off + bits // 8] = (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little')

            execute, traces, portable_steps = scenario(portable_read, portable_write, case, control)
            errors = []

            @CALL
            def call(_, entry, r):
                try:
                    execute(entry, r.contents)
                except Exception as error:
                    errors.append(error)
                    portable_write(STOPPED, 1)

            bus = Bus(None, READ(lambda _, at, bits: portable_read(at, bits)),
                      WRITE(lambda _, at, value, bits: portable_write(at, value, bits)), call)
            r = Registers(*incoming, preserved[0], preserved[1], preserved[3], preserved[2], control, esp=SP)
            fn(C.byref(bus), C.byref(r))
            assert not errors, errors
            assert traces == events, (case, 'trace', next(
                ((i, a, b) for i, (a, b) in enumerate(zip(traces, events)) if a != b),
                (len(traces), len(events))))
            assert memory == expected, (case, 'memory', [hex(at) for at in memory if memory[at] != expected[at]])
            assert (r.eax, r.ecx, r.edx) == tuple(uc.reg_read(reg) for reg in REGS[:3]), (case, 'registers')
            assert (r.ebx, r.ebp, r.edi, r.esi) == tuple(preserved)
            assert r.fp_control | 0x40 == uc.reg_read(UC_X86_REG_FPCW) | 0x40
    return {'cases_per_entry': {f'{entry:08x}': 256}, 'original_executions': 256,
            'portable_comparisons': 256 * len(functions), 'original_callback_events': total_calls,
            'stubbed_instruction_and_effect_bodies': True,
            'checked': ['FIFO gates', 'stopped entry', 'mutable queues', 'delayed execution',
                        'repeat counter wrap/expiry', '1000-instruction batches', 'callback ABI and flags']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--batch', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.exe, args.libraries, args.batch)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
