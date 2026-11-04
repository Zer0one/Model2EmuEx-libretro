#!/usr/bin/env python3
"""Exercise every control/mode/condition combination and wide transfer pair.

The original runs through 004b6280 and the two register-address helpers without
stubs. Compare all record bytes and the complete declared subdecoder ABI.
"""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP
from difftest_decode import RECORD, SIZE, STORAGE, Registers, U32
from difftest_operands import ACTIVE_STATE, STATE_TOKEN, REGISTERS
from difftest_lifecycle import load_original, SP, STOP


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(STORAGE, 0x1000)
    uc.mem_write(RECORD, struct.pack('<I', STORAGE))
    uc.mem_write(ACTIVE_STATE, struct.pack('<I', STATE_TOKEN))
    operands = (U32 * 480).from_buffer_copy(uc.mem_read(0x572AC0, 480 * 4))
    conditions = (U32 * 64).from_buffer_copy(uc.mem_read(0x5732C8, 64 * 4))
    names = {0x4B6730: 'control', 0x4B6B90: 'wide_move', 0x4B6280: 'target',
             0x4B3B20: 'register_address', 0x4B3B50: 'register_address'}
    libraries = [C.CDLL(str(p.resolve())) for p in libraries]
    counts = {}
    rng = random.Random(0x4B6730)
    for entry, name in names.items():
        functions = [getattr(lib, 'm2_tgpx4_decode_' + name) for lib in libraries]
        for fn in functions:
            fn.restype = None
            fn.argtypes = ([U32, U32, C.POINTER(Registers)] if name == 'register_address'
                           else [U32, U32, C.POINTER(U32), C.POINTER(Registers)])
            if name in ('control', 'wide_move'):
                fn.argtypes += [C.POINTER(U32)]
            if name == 'control':
                fn.argtypes += [C.POINTER(U32)]
        count = 65536 if name == 'control' else 17408 if name == 'wide_move' else 2048
        for i in range(count):
            low, ecx, edx, esi = (rng.getrandbits(32) for _ in range(4))
            if name == 'control':
                # 32 operations x 64 conditions x 16 target modes x both banks.
                low = (low & 0xF80007FF) | ((i % 32) << 22) | ((i // 32 % 64) << 16)
                low |= (i // 2048 % 16) << 12 | (i // 32768) << 11
            elif name == 'wide_move':
                source, destination = i % 128, i // 128 % 128
                low = (low & 0xFFFFFF) | destination << 24 | (source & 1) << 31
                edx = (edx & ~127) | (source >> 1)
                if i >= 16384:
                    # Both port directions, every destination and sign bit.
                    low = (low & 0xFFFFFF) | (i % 128) << 24 | (i // 128 % 2) << 31
                    edx |= 0x40 | (i // 256 % 2) << 5
            elif name == 'target':
                low = (low & ~0xFF80) | (i % 16) << 12 | (i // 16 % 2) << 11
            else:
                low = i if i < 32 else low
            incoming = (low, ecx, edx, esi)
            initial = rng.randbytes(SIZE)
            uc.mem_write(STORAGE, initial)
            uc.mem_write(SP, struct.pack('<I', STOP))
            for reg, value in zip(REGISTERS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.emu_start(entry, STOP, count=512)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
            expected = bytes(uc.mem_read(STORAGE, SIZE))
            expected_regs = tuple(uc.reg_read(reg) for reg in REGISTERS)
            for fn in functions:
                record = (U32 * (SIZE // 4)).from_buffer_copy(initial)
                regs = Registers(*incoming)
                if name == 'register_address':
                    fn(entry, STATE_TOKEN, C.byref(regs))
                else:
                    args = [STORAGE, STATE_TOKEN, record, C.byref(regs)]
                    if name in ('control', 'wide_move'):
                        args.append(operands)
                    if name == 'control':
                        args.append(conditions)
                    fn(*args)
                assert bytes(record) == expected, (hex(entry), i, hex(low), 'record',
                    [(hex(j * 4), hex(record[j]), hex(struct.unpack_from('<I', expected, j * 4)[0]))
                     for j in range(SIZE // 4) if bytes(record)[j*4:j*4+4] != expected[j*4:j*4+4]])
                actual = (regs.eax, regs.ecx, regs.edx, regs.esi)
                assert actual == expected_regs, (hex(entry), i, hex(low), 'registers',
                                                  tuple(map(hex, actual)), tuple(map(hex, expected_regs)))
        counts[f'{entry:08x}'] = count
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    counts = compare(args.exe, args.libraries)
    report = {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
              'portable_comparisons': sum(counts.values()) * len(args.libraries),
              'stubbed_original_helpers': []}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
