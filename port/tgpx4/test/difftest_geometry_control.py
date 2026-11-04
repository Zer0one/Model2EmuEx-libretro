#!/usr/bin/env python3
"""Compare six native Top Skater geometry overrides (memory-visible control).

004bc040 is checked only up to its tail transfer to 004bb280. The common
polygon parser, rasterization and transient x86 registers are outside scope.
"""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from difftest_lifecycle import load_original, SP, STOP
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS


class Control(C.Structure):
    _fields_ = [('primary', C.c_uint32 * 16), ('alternate', C.c_uint32 * 16),
                ('list_position', C.c_uint32), ('special_object', C.c_uint32)]


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
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_geometry_command
        fn.argtypes = [C.POINTER(Control), C.c_uint32, C.POINTER(C.c_uint32)]
        fn.restype = C.c_bool
        functions.append(fn)
    rng = random.Random(0x4bc040)
    entries = (0x4bc040, 0x4ba010, 0x4b94a0, 0x4b9460, 0x4b93e0, 0x4b9900)
    count = 0
    for entry in entries:
        for trial in range(256):
            # Include arbitrary bit patterns; these commands do not do FP math.
            words = [rng.getrandbits(32) for _ in range(32)]
            if trial == 0:
                words = [0, 0x80000000, 0x7fc01234, 0x7f800000] * 8
            position = arena + 16 + (trial % 16) * 4
            mode = rng.getrandbits(32)
            initial = struct.pack('<34I', *words, position, mode)
            inputs = (C.c_uint32 * 12)(*[rng.getrandbits(32) for _ in range(12)])
            uc.mem_write(0x10f00a8, initial[:64])
            uc.mem_write(0x10f0068, initial[64:128])
            uc.mem_write(0x1003018, struct.pack('<I', position))
            uc.mem_write(0xdcec08, struct.pack('<I', mode))
            uc.mem_write(position, bytes(inputs))
            uc.mem_write(SP, struct.pack('<I', STOP))
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.reg_write(UC_X86_REG_EFLAGS, 2)  # Native caller has DF clear.
            stop = 0x4bb280 if entry == 0x4bc040 else STOP
            uc.emu_start(entry, stop, count=1000)
            assert uc.reg_read(UC_X86_REG_EIP) == stop
            expected = (bytes(uc.mem_read(0x10f00a8, 64))
                        + bytes(uc.mem_read(0x10f0068, 64))
                        + bytes(uc.mem_read(0x1003018, 4))
                        + bytes(uc.mem_read(0xdcec08, 4)))
            assert bytes(uc.mem_read(position, 48)) == bytes(inputs)
            for fn in functions:
                state = Control.from_buffer_copy(initial)
                assert fn(C.byref(state), entry, inputs)
                assert bytes(state) == expected, (hex(entry), trial)
                assert not fn(C.byref(state), 0xdeadbeef, inputs)
                assert bytes(state) == expected
            count += 1
    result = dict(original_executions=count, portable_comparisons=count*len(functions),
                  entries=[hex(e) for e in entries],
                  scope='Memory-visible control only; object wrapper stops before common handler',
                  renderer_validation='Separate machine/frontend checks; not compared here')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
