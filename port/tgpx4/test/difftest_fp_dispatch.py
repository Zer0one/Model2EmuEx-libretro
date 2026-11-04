#!/usr/bin/env python3
"""FP dispatch: original operand callback ABI, scratch registers and guest state.

Scalar numerical qualification is separate. Finite inputs avoid known Unicorn
SNaN/denormal defects; x87 C1/exception omissions are explicitly excluded here."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG
from difftest_wrappers import Registers, Bus, READ, WRITE, CALL, U32, REGS, NAMES
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = (0x4B4E60, 0x4B53B0, 0x4B5630, 0x4B56A0, 0x4B5740, 0x4B57B0,
           0x4B5850, 0x4B54B0, 0x4B5460, 0x4B6630, 0x4B65C0, 0x4B5510, 0x4B6530, 0x4B64A0) + tuple(range(0x4B3FB0, 0x4B4030, 16))
ACTIVE, RECORD, ARENA, CODE, CRT = 0x10481F4, 0x104824C, 0x72000000, 0x72010000, 0x10F1FEC
EDGE = (0, 0x80000000, 0x3F800000, 0xBF800000, 0x3F000000, 0xBF000000, 0x40000000,
        0xC0000000, 0x437F0000, 0x43800000, 0xC3800000, 0x4F000000, 0xCF000000,
        0x3F800001, 0x3F7FFFFF, 0x3FC00000)


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x20000)
    functions = []
    for path in libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_execute_fp
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers), U32]
        fn.restype = C.c_bool
        functions.append(fn)
    rng = random.Random(0x4B4DF0)
    action = None

    def write(at, value):
        uc.mem_write(at, struct.pack('<I', value))

    def read(at):
        return int.from_bytes(uc.mem_read(at, 4), 'little')

    def script(read, write, case, values):
        trace = []

        def execute(entry, r):
            regs = [getattr(r, name) for name in NAMES]
            regs[3] &= ~0x10
            trace.append((entry, r.esp, *regs, read(RECORD), read(ACTIVE)))
            if case & 1:
                write(RECORD, ARENA + 0x100)
                write(ACTIVE, ARENA + 0x600)
            r.eax = values[min(len(trace) - 1, 1)]
            r.ecx ^= 0x98765432
            r.edx ^= 0x12345678
            r.flags = 0x202 | ((case * 17) & 0x8D5)

        return execute, trace

    def boundary(emu, address, size, data):
        r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW), emu.reg_read(UC_X86_REG_FPSW), esp=emu.reg_read(UC_X86_REG_ESP))
        action(address, r)
        for reg, name in zip(REGS, NAMES):
            emu.reg_write(reg, getattr(r, name))
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=CODE, end=CODE + 16)
    counts, calls = {}, 0
    for entry in ENTRIES:
        for case in range(2048):
            initial = bytearray(rng.randbytes(0x1000))
            for rec in (0, 0x100):
                for off in (0, 0x14):
                    struct.pack_into('<I', initial, rec + off, CODE)
                for off in (4, 0x18):
                    struct.pack_into('<I', initial, rec + off, CODE + 16)
                struct.pack_into('<I', initial, rec + 0x10, case % 32 << 15)
            values = (EDGE[case % 16], EDGE[case // 16 % 16]) if case < 1024 else (
                rng.randrange(0x30000000, 0x4F000000) | ((case & 1) << 31),
                rng.randrange(0x30000000, 0x4F000000) | ((case & 2) << 30))
            if entry == 0x4B64A0:
                # FYL2X special-case behavior is broken in Unicorn. Use
                # exact log2 arguments here to check callback/register ABI;
                # broad numerical/state qualification runs original code on AMD.
                values = ((127 + case % 7 - 3) << 23, values[1])
            uc.mem_write(ARENA, bytes(initial))
            write(RECORD, ARENA)
            write(ACTIVE, ARENA + 0x400)
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[3] = 0x202 | (case & 0x8D5)
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            cw, sw = 0x7F | ((case % 4) << 10), (0, 0x4500, 0x4700, 0x453F)[case % 4]
            stack = SP - (case % 16) * 4
            write(CRT, case % 2)
            uc.reg_write(UC_X86_REG_FPCW, cw)
            uc.reg_write(UC_X86_REG_FPSW, sw)
            uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
            uc.reg_write(UC_X86_REG_ESP, stack)
            write(stack, STOP)
            action, events = script(read, write, case, values)
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == stack + 4
            expected = bytes(uc.mem_read(ARENA, len(initial)))
            expected_regs = [uc.reg_read(reg) for reg in REGS]
            calls += len(events)
            for fn in functions:
                memory = bytearray(initial)
                globals_copy = {RECORD: ARENA, ACTIVE: ARENA + 0x400, CRT: case % 2}

                def portable_read(at):
                    if at in globals_copy:
                        return globals_copy[at]
                    assert ARENA <= at <= ARENA + len(memory) - 4
                    return int.from_bytes(memory[at - ARENA:at - ARENA + 4], 'little')

                def portable_write(at, value):
                    if at in globals_copy:
                        globals_copy[at] = value
                    else:
                        assert ARENA <= at <= ARENA + len(memory) - 4
                        struct.pack_into('<I', memory, at - ARENA, value)

                execute, traces = script(portable_read, portable_write, case, values)
                bus = Bus(None, READ(lambda _, at, bits: portable_read(at)),
                          WRITE(lambda _, at, value, bits: portable_write(at, value)),
                          CALL(lambda _, target, regs: execute(target, regs.contents)))
                r = Registers(*incoming, cw, sw, stack)
                assert fn(entry, C.byref(bus), C.byref(r), stack)
                assert traces == events, (hex(entry), case, 'callback ABI', traces, events)
                actual = [getattr(r, name) for name in NAMES]
                actual[3] &= ~0x10
                expected_regs[3] &= ~0x10
                assert actual == expected_regs, (hex(entry), case, 'registers',
                                                 list(map(hex, actual)), list(map(hex, expected_regs)))
                assert memory == expected, (hex(entry), case, 'memory')
                assert (r.fp_control | 0x40) == (uc.reg_read(UC_X86_REG_FPCW) | 0x40)
                assert (r.fp_status ^ uc.reg_read(UC_X86_REG_FPSW)) & ~0x23F == 0, (hex(entry), case, 'x87 condition codes')
        counts[f'{entry:08x}'] = 2048
    return {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
            'portable_comparisons': sum(counts.values()) * len(functions),
            'original_callback_events': calls, 'operand_readers': 'mutating fixtures; including record/state rebinding',
            'x87_scope': 'finite-input dispatch; C1 and exception omissions excluded, scalar qualification separate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.exe, args.libraries)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'cases_per_entry'}))


if __name__ == '__main__':
    main()
