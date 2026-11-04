#!/usr/bin/env python3
"""Compare original operand-table subdecoders and inherited register values."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EIP,
    UC_X86_REG_ESI, UC_X86_REG_ESP,
)
from difftest_decode import RECORD, SIZE, STORAGE, Registers, U32
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = (0x4B75D0, 0x4B76B0, 0x4B6AC0, 0x4B6EF0, 0x4B7440, 0x4B7100)
ACTIVE_STATE, STATE_TOKEN = 0x10481F4, 0x10EDEF0
REGISTERS = (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI)


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(STORAGE, 0x1000)
    uc.mem_write(RECORD, struct.pack("<I", STORAGE))
    uc.mem_write(ACTIVE_STATE, struct.pack("<I", STATE_TOKEN))
    operands = (U32 * 480).from_buffer_copy(uc.mem_read(0x572AC0, 480 * 4))
    alu = (U32 * 32).from_buffer_copy(uc.mem_read(0x573248, 32 * 4))
    functions = []
    for path in libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_decode_operands
        fn.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(Registers),
                       C.POINTER(U32), C.POINTER(U32)]
        fn.restype = None
        immediate = C.CDLL(str(path.resolve())).m2_tgpx4_decode_immediate
        immediate.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(Registers), C.POINTER(U32)]
        immediate.restype = None
        transfers = C.CDLL(str(path.resolve())).m2_tgpx4_decode_transfers
        transfers.argtypes = immediate.argtypes
        transfers.restype = None
        parallel = C.CDLL(str(path.resolve())).m2_tgpx4_decode_parallel
        parallel.argtypes = immediate.argtypes
        parallel.restype = None
        move = C.CDLL(str(path.resolve())).m2_tgpx4_decode_move
        move.argtypes = immediate.argtypes
        move.restype = None
        functions.append((fn, immediate, transfers, parallel, move))

    rng = random.Random(0x4B75D0)
    for entry in ENTRIES:
        for i in range(2048):
            high = (rng.getrandbits(32) & ~0x1F000200) | ((i % 32) << 24) | ((i // 32 % 2) << 9)
            low = rng.getrandbits(32)
            values = (high if entry == 0x4B76B0 else rng.getrandbits(32),
                      high if entry == 0x4B75D0 else rng.getrandbits(32),
                      rng.getrandbits(32), low)
            if entry == 0x4B6AC0:
                values = ((low & ~(127 << 19)) | ((i % 128) << 19), *values[1:])
            if entry == 0x4B6EF0:
                values = ((low & ~(3 << 18)) | (i % 4 << 18), values[1],
                          (high & ~(3 << 6)) | (i // 4 % 4 << 6), low)
            if entry == 0x4B7440:
                values = ((low & ~(3 << 24)) | (i % 4 << 24), *values[1:])
            if entry == 0x4B7100:
                values = ((low & 0xF8000FFF) | (i % 128 << 12)
                          | (i // 128 % 4 << 25) | (rng.randrange(64) << 19), *values[1:])
            initial = rng.randbytes(SIZE)
            uc.mem_write(STORAGE, initial)
            uc.mem_write(SP, struct.pack("<I", STOP))
            for reg, value in zip(REGISTERS, values):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4

            for fn, immediate, transfers, parallel, move in functions:
                record = (U32 * (SIZE // 4)).from_buffer_copy(initial)
                registers = Registers(*values)
                if entry == 0x4B6AC0:
                    immediate(STORAGE, STATE_TOKEN, record, C.byref(registers), operands)
                elif entry == 0x4B6EF0:
                    transfers(STORAGE, STATE_TOKEN, record, C.byref(registers), operands)
                elif entry == 0x4B7440:
                    parallel(STORAGE, STATE_TOKEN, record, C.byref(registers), operands)
                elif entry == 0x4B7100:
                    move(STORAGE, STATE_TOKEN, record, C.byref(registers), operands)
                else:
                    fn(entry, STORAGE, record, C.byref(registers), operands, alu)
                assert bytes(record) == uc.mem_read(STORAGE, SIZE), (hex(entry), i, "record")
                assert (registers.eax, registers.ecx, registers.edx, registers.esi) == tuple(
                    uc.reg_read(reg) for reg in REGISTERS), (hex(entry), i, "registers")
    return {f"{entry:08x}": 2048 for entry in ENTRIES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = compare(args.exe, args.libraries)
    report = {"cases_per_entry": cases, "original_executions": sum(cases.values()),
              "portable_comparisons": sum(cases.values()) * len(args.libraries)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
