#!/usr/bin/env python3
"""Ski Super G handshake fragment, not the complete native input routine."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from difftest_lifecycle import load_original, SP, STOP
from unicorn.x86_const import UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_EIP


class State(C.Structure):
    _fields_ = [('command', C.c_uint32), ('phase', C.c_uint32),
                ('countdown', C.c_uint32), ('reply', C.c_uint8)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    uc = load_original(args.exe)
    functions = []
    for path in args.libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_motion_step
        fn.argtypes = [C.POINTER(State)]
        fn.restype = None
        functions.append(fn)
    fields = ((0x574cf0, 4), (0x10f01b8, 4), (0x10f01bc, 4), (0x5aa876, 1))
    rng = random.Random(0x4c9f19)
    cases = [(command, phase, count, rng.randrange(256))
             for command in (*range(256), 0xffffffff, 0x100, 0x1ff)
             for phase in (0, 1, 2, 3, 4, 0xffffffff)
             for count in (0, 1, 9, 10, 0xffffffff)]
    # An actual consecutive command sequence also carries phase/count/reply.
    sequence = [0xff, 0, *([0x80] * 25), 0xffffffff, 0xff, 0, *([0] * 25)]
    previous = (0xffffffff, 0, 0, 0xff)
    for index in range(len(cases) + len(sequence)):
        values = cases[index] if index < len(cases) else (sequence[index-len(cases)], *previous[1:])
        for (at, size), value in zip(fields, values):
            uc.mem_write(at, value.to_bytes(size, 'little'))
        uc.reg_write(UC_X86_REG_EDX, values[0])
        uc.reg_write(UC_X86_REG_ESP, SP)
        uc.reg_write(UC_X86_REG_EBP, SP+8)
        uc.mem_write(SP, struct.pack('<IIII', 0x1234, 0x5678, 0x9abc, STOP))
        uc.emu_start(0x4c9f19, STOP, count=1000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
        expected = tuple(int.from_bytes(uc.mem_read(at, size), 'little') for at, size in fields)
        for fn in functions:
            state = State(*values)
            fn(C.byref(state))
            actual = (state.command, state.phase, state.countdown, state.reply)
            assert actual == expected, (index, values, expected, actual)
        if index >= len(cases): previous = expected
    result = dict(original_fragment_executions=len(cases)+len(sequence),
                  portable_comparisons=(len(cases)+len(sequence))*len(functions),
                  entry='004c9f19', scope='Handshake only; no analog-input or board integration claim')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
