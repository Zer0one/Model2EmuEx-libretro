#!/usr/bin/env python3
"""CPU-facing external-memory bodies: values, pointer tokens and scratch flags."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
from difftest_wrappers import Registers, Bus, READ, WRITE, CALL, U32, REGS, NAMES
from difftest_lifecycle import load_original, SP, STOP


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    uc = load_original(args.exe)
    shared, rom = 0x72000000, 0x74000000
    addresses = (0, 1, 0x3FFFFF, 0x400000, 0x400001, 0x41FFFF,
                 0x7FFFFF, 0x800000, 0x800001, 0x800100)
    pages = set()
    functions = []
    for path in args.libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_execute_board_memory
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = C.c_bool
        functions.append(fn)
    rng = random.Random(0x4C5A90)
    count = 0
    for entry in (0x4C5A70, 0x4C5A90):
        for case in range(1024):
            address = addresses[case % len(addresses)]
            target = None
            if 0x400000 <= address < 0x800000:
                target = shared + (address - (0x400000 if entry == 0x4C5A70 else 0)) * 4
            elif address >= 0x800000 and entry == 0x4C5A90:
                target = rom + (address - 0x800000) * 4
            memory = {0x5AA700: shared, 0x5AA8DC: rom}
            if target is not None:
                page = target & ~0xFFF
                if page not in pages:
                    uc.mem_map(page, 0x1000); pages.add(page)
                memory[target] = rng.getrandbits(32)
            for at, value in memory.items(): uc.mem_write(at, struct.pack('<I', value))
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[1] = address
            incoming[3] = 0x202 | (rng.getrandbits(12) & 0x8D5)
            for reg, value in zip(REGS, incoming): uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_ESP, SP); uc.mem_write(SP, struct.pack('<I', STOP))
            uc.emu_start(entry, STOP, count=100)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP
            expected = [uc.reg_read(reg) for reg in REGS]
            expected_memory = {at: int.from_bytes(uc.mem_read(at, 4), 'little') for at in memory}
            for fn in functions:
                actual_memory, errors = dict(memory), []
                @READ
                def read(_, at, bits):
                    if bits != 32 or at not in actual_memory:
                        errors.append(('read', hex(at), bits)); return 0
                    return actual_memory[at]
                @WRITE
                def write(_, at, value, bits):
                    if bits != 32 or at not in actual_memory: errors.append(('write', hex(at), bits))
                    actual_memory[at] = value
                bus = Bus(None, read, write, CALL(lambda *_: errors.append('unexpected callback')))
                r = Registers(*incoming, esp=SP)
                assert fn(entry, C.byref(bus), C.byref(r))
                actual = [getattr(r, name) for name in NAMES]
                assert not errors and actual == expected and actual_memory == expected_memory, (hex(entry), case, errors, actual, expected)
            count += 1
    report = dict(original_executions=count, portable_comparisons=count*len(functions),
                  scope='External-memory CPU callback ABI; sparse ample fixture mapping does not authorize expanded guest RAM')
    args.output.write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report))

if __name__ == '__main__': main()
