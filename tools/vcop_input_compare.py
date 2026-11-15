#!/usr/bin/env python3
"""Compare the Libretro Virtua Cop byte lanes with ElSemi's original hook.

The supplied probe calls the production input bridge and board reader. The
original host-device poll is replaced by its already-calibrated outputs.
No game ROMs are required. Both revision bindings and all P1/P2 trigger and
offscreen combinations are checked at the three axis positions.
"""
import argparse
import ctypes
import itertools
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'port/sharc/test'))
from difftest_bits import load_original, SP, STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX


def compare(exe, library):
    original = load_original(exe)
    board = 0x72000000
    original.mem_map(board, 0x1000)
    original.mem_write(0x5aa730, struct.pack('<I', board))
    original.mem_write(board + 0x3c, bytes(4))

    def skip_device_poll(cpu, address, size, data):
        stack = cpu.reg_read(UC_X86_REG_ESP)
        target = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cpu.reg_write(UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(UC_X86_REG_EIP, target)

    original.hook_add(UC_HOOK_CODE, skip_device_poll, begin=0x4caa80, end=0x4caa80)

    def call(entry, offset=0):
        original.mem_write(SP, struct.pack('<I', STOP))
        original.reg_write(UC_X86_REG_ESP, SP)
        original.reg_write(UC_X86_REG_ECX, offset)
        original.emu_start(entry, STOP, count=1000)
        assert original.reg_read(UC_X86_REG_EIP) == STOP
        return original.reg_read(UC_X86_REG_EAX) & 255

    probe = ctypes.CDLL(str(library.resolve()))
    function = probe.vcop_case
    function.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
                         ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
    function.restype = ctypes.c_int
    count = 0
    for game, x, y, flags in itertools.product(
            ('vcop', 'vcopa'), (-32768, 0, 32767), (-32768, 0, 32767), range(16)):
        result = (ctypes.c_uint * 18)()
        assert function(game.encode(), x, y, flags, result) == 0
        # 004cb9b0 converts host coordinates to guest counters with +83/+24.
        coordinates = [result[0]-0x83, result[1]-0x24,
                       result[2]-0x83, result[3]-0x24]
        original.mem_write(0x574cf8, struct.pack('<4I', *(v & 0xffffffff for v in coordinates)))
        original.mem_write(0x5aa734, struct.pack('<I', (~result[4]) & 3))
        original.mem_write(0x5aa875, bytes([result[5]]))
        call(0x4cb9b0)
        expected = [call(0x4c88a0, 0x100 + i*2) for i in range(9)]
        expected.append(call(0x4c88a0, 0x12))
        actual = list(result)[6:16]
        assert actual == expected, (game, x, y, flags, actual, expected)
        assert result[16] == 0 and result[17] & 3 == 3, 'Release did not restore inputs'
        count += 1
    return dict(status='pass', cases=count, byte_comparisons=count*10,
                release_checks=count, revisions=['vcop', 'vcopa'],
                original_hook='004cb9b0', original_reader='004c88a0',
                device_poll_boundary='004caa80')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('library', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.exe, args.library)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
