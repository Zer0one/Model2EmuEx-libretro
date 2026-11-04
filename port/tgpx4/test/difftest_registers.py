#!/usr/bin/env python3
"""Original register/control primitives, including partial writes and wraparound."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW
from difftest_wrappers import Registers, Bus, READ, WRITE, CALL, U32, REGS, NAMES
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = sorted(set(
    list(range(0x4B3BA0, 0x4B3C30, 16)) + list(range(0x4B4060, 0x4B40F0, 16))
    + list(range(0x4B3DA0, 0x4B3FA0, 16)) + list(range(0x4B42B0, 0x4B44B0, 16))
    + list(range(0x4B3CA0, 0x4B3DA0, 32)) + list(range(0x4B41B0, 0x4B42B0, 32))
    + [0x4B3750, 0x4B3760, 0x4B3770, 0x4B37A0, 0x4B37B0, 0x4B37E0, 0x4B3820,
       0x4B3830, 0x4B3850, 0x4B3860, 0x4B3880, 0x4B3B70, 0x4B3B80, 0x4B3B90,
       0x4B3C30, 0x4B3C50, 0x4B3C70, 0x4B3C80, 0x4B3FA0, 0x4B4030, 0x4B4040,
       0x4B4050, 0x4B40F0, 0x4B4110, 0x4B4130, 0x4B4140, 0x4B4160, 0x4B4170, 0x4B4190]))
ACTIVE, RECORD, ARENA = 0x10481F4, 0x104824C, 0x72000000


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x2000)
    functions = []
    for path in libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_execute_register
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = C.c_bool
        functions.append(fn)
    rng = random.Random(0x4B3BA0)
    cases = {}
    for entry in ENTRIES:
        for case in range(256):
            state = ARENA + (0x400 if case & 1 else 0x600)
            record = ARENA + (0x100 if case & 2 else 0)
            initial = bytearray(rng.randbytes(0x1000))
            struct.pack_into('<I', initial, record - ARENA + 0x74, state + 0x80 + (case % 8) * 4)
            count = (0, 1, 23, 24, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, rng.getrandbits(32))[case % 8]
            struct.pack_into('<I', initial, state - ARENA + 0xA0, count)
            struct.pack_into('<I', initial, state - ARENA + 0xA4, case % 24 if entry == 0x4B4140 else count)
            struct.pack_into('<I', initial, state - ARENA + 0x114, count)
            uc.mem_write(ARENA, bytes(initial))
            uc.mem_write(ACTIVE, struct.pack('<I', state))
            uc.mem_write(RECORD, struct.pack('<I', record))
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[3] = 0x202 | (case & 0x8D5)
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.mem_write(SP, struct.pack('<I', STOP))
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
            expected = bytes(uc.mem_read(ARENA, len(initial)))
            expected_regs = [uc.reg_read(reg) for reg in REGS]
            expected_globals = {ACTIVE: int.from_bytes(uc.mem_read(ACTIVE, 4), 'little'),
                                RECORD: int.from_bytes(uc.mem_read(RECORD, 4), 'little')}
            for fn in functions:
                memory, globals_copy = bytearray(initial), {ACTIVE: state, RECORD: record}
                errors = []

                @READ
                def read(_, at, bits):
                    if at in globals_copy:
                        return globals_copy[at]
                    if not ARENA <= at < ARENA + len(memory):
                        errors.append(('read', hex(at)))
                        return 0
                    return int.from_bytes(memory[at - ARENA:at - ARENA + bits // 8], 'little')

                @WRITE
                def write(_, at, value, bits):
                    if at in globals_copy:
                        globals_copy[at] = value
                    elif ARENA <= at < ARENA + len(memory):
                        memory[at - ARENA:at - ARENA + bits // 8] = (
                            value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little')
                    else:
                        errors.append(('write', hex(at)))

                bus = Bus(None, read, write, CALL(lambda *args: errors.append('unexpected call')))
                r = Registers(*incoming, 0x37F)
                assert fn(entry, C.byref(bus), C.byref(r))
                assert not errors, errors
                actual_regs = [getattr(r, name) for name in NAMES]
                # AF is undefined after logical operations, so is not a proof target.
                actual_regs[3] &= ~0x10
                expected_regs[3] &= ~0x10
                assert actual_regs == expected_regs, (hex(entry), case, 'registers',
                                                       list(map(hex, actual_regs)), list(map(hex, expected_regs)))
                assert memory == expected, (hex(entry), case, 'memory')
                assert globals_copy == expected_globals, (hex(entry), case, 'globals')
        cases[f'{entry:08x}'] = 256
    return {'cases_per_entry': cases, 'original_executions': sum(cases.values()),
            'portable_comparisons': sum(cases.values()) * len(functions),
            'stubbed_original_helpers': [], 'undefined_logical_AF_compared': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.exe, args.libraries)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases_per_entry'}))
    print(f"Verified {len(report['cases_per_entry'])} entries")


if __name__ == '__main__':
    main()
