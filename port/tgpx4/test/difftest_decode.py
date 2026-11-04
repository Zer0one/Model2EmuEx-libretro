#!/usr/bin/env python3
"""Compare Model 2C class dispatch, FIFO flags and the live subdecoder ABI."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ESI,
)
from difftest_lifecycle import load_original, SP, STOP

ENTRY, BASE, RECORD = 0x4B77A0, 0x10481F0, 0x104824C
STORAGE, SIZE = 0x72000000, 0x94
SUBDECODERS = (0x4B6730, 0x4B6AC0, 0x4B6B90, 0x4B6EF0, 0x4B7100,
               0x4B7440, 0x4B75D0, 0x4B76B0)
READ_SLOTS = (0, 4, 0x14, 0x18, 0x28, 0x44)
WRITE_SLOTS = (8, 0x1C, 0x2C, 0x48)
U32 = C.c_uint32
IMPLEMENTED = SUBDECODERS
STATE_TOKEN = 0x10EDEF0


class Registers(C.Structure):
    _fields_ = [("eax", U32), ("ecx", U32), ("edx", U32), ("esi", U32)]


SUBDECODE = C.CFUNCTYPE(None, C.c_void_p, U32, C.POINTER(Registers), C.POINTER(U32))


def compare(exe, libraries, integrated, composed=False):
    uc = load_original(exe)
    uc.mem_map(STORAGE, 0x1000)
    uc.mem_write(0x10481F4, struct.pack("<I", STATE_TOKEN))
    operand_table = (U32 * 480).from_buffer_copy(uc.mem_read(0x572AC0, 480 * 4))
    alu_table = (U32 * 32).from_buffer_copy(uc.mem_read(0x573248, 32 * 4))
    condition_table = (U32 * 64).from_buffer_copy(uc.mem_read(0x5732C8, 64 * 4))
    functions = []
    for path in libraries:
        library = C.CDLL(str(path.resolve()))
        fn = library.m2_tgpx4_decode_instruction
        fn.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(U32), C.POINTER(Registers),
                       SUBDECODE, C.c_void_p]
        fn.restype = None
        operands = library.m2_tgpx4_decode_operands
        operands.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(Registers),
                             C.POINTER(U32), C.POINTER(U32)]
        operands.restype = None
        decoded = {}
        for entry, name in ((0x4B6AC0, "immediate"), (0x4B6EF0, "transfers"),
                            (0x4B7100, "move"), (0x4B7440, "parallel"),
                            (0x4B6B90, "wide_move"), (0x4B6730, "control")):
            decoder = getattr(library, f"m2_tgpx4_decode_{name}")
            decoder.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(Registers), C.POINTER(U32)]
            if entry == 0x4B6730:
                decoder.argtypes += [C.POINTER(U32)]
            decoder.restype = None
            decoded[entry] = decoder
        native = library.m2_tgpx4_decode_native
        native.argtypes = [U32, U32, U32, U32, C.POINTER(U32), C.POINTER(U32), C.POINTER(Registers)]
        functions.append((fn, operands, decoded, native))

    def put(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def mutations(entry, eax, ecx, edx):
        return ((eax ^ entry) & 0xFFFFFFFF, (ecx + entry) & 0xFFFFFFFF,
                (edx * 3 + entry) & 0xFFFFFFFF)

    def patch_slots(entry, eax, ecx):
        return ((READ_SLOTS[(eax >> 8) % len(READ_SLOTS)], 0x4B5EF0 if eax & 1 else entry),
                (WRITE_SLOTS[(ecx >> 8) % len(WRITE_SLOTS)], 0x4B5DF0 if ecx & 1 else entry))

    events = []
    x86_regs = (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX)

    def boundary(emu, address, size, data):
        values = tuple(emu.reg_read(reg) for reg in x86_regs)
        record = word(RECORD)
        events.append((address, values, emu.reg_read(UC_X86_REG_ESI), bytes(emu.mem_read(record, SIZE))))
        for offset, value in patch_slots(address, values[0], values[1]):
            put(record + offset, value)
        for reg, value in zip(x86_regs, mutations(address, *values)):
            emu.reg_write(reg, value)
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, word(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    for address in SUBDECODERS:
        if not integrated or address not in IMPLEMENTED:
            uc.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)

    rng = random.Random(ENTRY)
    counts = [0] * 8
    for i in range(2048):
        instruction_class = i % 8
        low = rng.getrandbits(32)
        high = instruction_class << 29 | rng.getrandbits(29)
        initial = bytearray(rng.randbytes(2 * SIZE))
        first = (i // 8) % 3 == 0
        record_offset = 0 if first else SIZE
        struct.pack_into("<I", initial, 0x90, (i // 8) % 2)
        for slots, token in ((READ_SLOTS, 0x4B5EF0), (WRITE_SLOTS, 0x4B5DF0)):
            if i & 8:
                struct.pack_into("<I", initial, record_offset + slots[(i // 8) % len(slots)], token)
        incoming = [low, rng.getrandbits(32), rng.getrandbits(32)]
        uc.mem_write(STORAGE, bytes(initial))
        put(BASE, STORAGE)
        put(RECORD, STORAGE + record_offset)
        put(SP, STOP)
        for reg, value in zip(x86_regs, incoming):
            uc.reg_write(reg, value)
        saved_esi = rng.getrandbits(32)
        uc.reg_write(UC_X86_REG_ESI, saved_esi)
        uc.reg_write(UC_X86_REG_EBX, high)
        uc.reg_write(UC_X86_REG_ESP, SP)
        events.clear()
        uc.emu_start(ENTRY, STOP, count=512)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4

        for fn, operands, decoded, native in functions:
            traces = []
            buffer = (U32 * (2 * SIZE // 4)).from_buffer_copy(initial)
            current = C.cast(C.byref(buffer, record_offset), C.POINTER(U32))
            previous = None if first else buffer
            regs = Registers(*incoming, saved_esi)

            @SUBDECODE
            def decode(_, entry, scratch, record):
                if integrated and entry in decoded:
                    args = [STORAGE + record_offset, STATE_TOKEN, record, scratch, operand_table]
                    if entry == 0x4B6730:
                        args.append(condition_table)
                    decoded[entry](*args)
                    return
                if integrated and entry in IMPLEMENTED:
                    operands(entry, STORAGE + record_offset, record, scratch, operand_table, alu_table)
                    return
                r = scratch.contents
                values = (r.eax, r.ecx, r.edx)
                traces.append((entry, values, r.esi, C.string_at(record, SIZE)))
                for offset, value in patch_slots(entry, r.eax, r.ecx):
                    record[offset // 4] = value
                r.eax, r.ecx, r.edx = mutations(entry, *values)

            if composed:
                native(low, high, STORAGE + record_offset, STATE_TOKEN, current, previous, C.byref(regs))
            else:
                fn(low, high, current, previous, C.byref(regs), decode, None)
            assert traces == events, (i, instruction_class, "subdecoder ABI")
            assert bytes(buffer) == uc.mem_read(STORAGE, len(initial)), (i, instruction_class, "record")
            assert regs.esi == uc.reg_read(UC_X86_REG_ESI) == saved_esi
            assert (regs.eax, regs.ecx, regs.edx) == tuple(uc.reg_read(reg) for reg in x86_regs)
        counts[instruction_class] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = compare(args.exe, args.libraries, integrated=False)
    integrated = compare(args.exe, args.libraries, integrated=True)
    composed = compare(args.exe, args.libraries, integrated=True, composed=True)
    total = sum(counts) + sum(integrated) + sum(composed)
    report = {"cases_per_entry": {f"{ENTRY:08x}": total}, "isolated_cases_per_class": counts,
              "integrated_cases_per_class": integrated, "composed_cases_per_class": composed, "original_executions": total,
              "portable_comparisons": total * len(args.libraries),
              "stubbed_subdecoders_in_integrated_test": [f"{a:08x}" for a in SUBDECODERS
                                                        if a not in IMPLEMENTED]}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
