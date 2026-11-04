#!/usr/bin/env python3
"""Compare native ROM transform 004f77b0 on synthetic byte regions."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from difftest_lifecycle import load_original, SP, STOP
from unicorn.x86_const import (UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBX,
    UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    uc = load_original(args.exe)
    arena = 0x72000000
    uc.mem_map(arena, 0x10000)
    functions = []
    for path in args.libraries:
        fn = C.CDLL(str(path.resolve())).m2_rom_transform
        fn.argtypes = [C.c_uint32, C.c_void_p, C.c_uint32]
        fn.restype = C.c_int
        functions.append(fn)
    lengths = [*range(258), 4095, 4096, 4097, 32767, 32768]
    rng = random.Random(0x4f77b0)
    for length in lengths:
        raw = rng.randbytes(length+32)
        uc.mem_write(arena, raw)
        uc.reg_write(UC_X86_REG_ECX, arena+16)
        uc.reg_write(UC_X86_REG_EDX, length)
        uc.reg_write(UC_X86_REG_EBX, 0x12345678)
        uc.reg_write(UC_X86_REG_ESI, 0x9abcdef0)
        uc.reg_write(UC_X86_REG_ESP, SP)
        uc.mem_write(SP, struct.pack('<I', STOP))
        uc.emu_start(0x4f77b0, STOP, count=200000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
        assert uc.reg_read(UC_X86_REG_ESP) == SP+4
        assert uc.reg_read(UC_X86_REG_EBX) == 0x12345678
        assert uc.reg_read(UC_X86_REG_ESI) == 0x9abcdef0
        expected = bytes(uc.mem_read(arena, len(raw)))
        for fn in functions:
            buf = C.create_string_buffer(raw, len(raw))
            assert fn(0x4f77b0, C.byref(buf, 16), length) == 0
            assert buf.raw == expected, length
            assert fn(0xdeadbeef, C.byref(buf, 16), length) == -1
            assert buf.raw == expected
    result = dict(original_executions=len(lengths), portable_comparisons=len(lengths)*len(functions),
                  checked=['all region bytes and guards', 'odd tail', 'unknown callback rejection'],
                  scope='Native ROM transform on synthetic input; no ROM data')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
