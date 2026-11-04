#!/usr/bin/env python3
"""Original M2C driver setup, native name rules and primitive callback surface.

The EXE executes its own CRT string comparisons. Bootstrap construction and
shared geometry are explicit boundaries; their isolated suites are separate.
"""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW, UC_X86_REG_FPTAG
from difftest_wrappers import Registers, Bus, READ, WRITE, CALL, U32, REGS, NAMES
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = tuple(range(0x4C5850, 0x4C58D0, 16)) + (0x4C59D0, 0x4C5A10, 0x4C5A20, 0x4C5A60, 0x4C5C60, 0x4C5C80)
ARENA, INIT, PREPARE, GEOMETRY = 0x72000000, 0x4C5C80, 0x4B7940, 0x4BAA60
REGIONS = ((0x573300, 0x200), (0x5AA720, 0x20), (0x5AEB90, 4),
           (0xDCEC58, 4), (0x10ED950, 0x30), (0x10EE038, 8), (0x10F0040, 12))
BOOT = C.CFUNCTYPE(None, C.c_void_p, U32, U32)
GAMES = ('', 'hotd', 'hotdo', 'HOTD', 'overrev', 'overrevb', 'skisuprg', 'waverunr',
         'segawski', 'dyn', 'dynamcop', 'dyndeka2', 'dynxxx', 'Dynxxx', 'tops', 'topskatr',
         'topskatru', 'top', 'TOPS', 'stcc', 'stccb', 'unknown')


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x1000)
    functions = []
    for path in libraries:
        lib = C.CDLL(str(path.resolve()))
        fn = lib.m2_tgpx4_driver_primitive
        fn.argtypes = [U32, C.POINTER(Bus), C.POINTER(Registers)]
        fn.restype = C.c_bool
        init = lib.m2_tgpx4_driver_initialize
        init.argtypes = [C.POINTER(Bus), C.c_void_p, BOOT, C.c_char_p, U32]
        init.restype = None
        functions.append((fn, init))
    rng = random.Random(INIT)
    events = []

    def read(at, bits=32):
        return int.from_bytes(uc.mem_read(at, bits // 8), 'little')

    def write(at, value, bits=32):
        uc.mem_write(at, (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little'))

    def prepare(source, count, write):
        # Mutate FIFO pointers: verify setup reads them after program creation.
        write(0x5AA724, source ^ count)
        write(0x5AA738, (source + count) & 0xFFFFFFFF)

    def geometry(r):
        r.eax ^= 0x12345678
        r.ecx ^= 0x87654321
        r.edx ^= 0xAA55AA55
        r.flags = 0x246

    def hook(emu, address, size, data):
        stack = emu.reg_read(UC_X86_REG_ESP)
        if address == PREPARE:
            args = (emu.reg_read(UC_X86_REG_EAX), read(stack + 4))
            events.append(('prepare', *args))
            prepare(*args, write)
            cleanup = 8
        else:
            r = Registers(*(emu.reg_read(reg) for reg in REGS), emu.reg_read(UC_X86_REG_FPCW))
            events.append(('geometry', *(getattr(r, name) for name in NAMES)))
            geometry(r)
            for reg, name in zip(REGS, NAMES):
                emu.reg_write(reg, getattr(r, name))
            cleanup = 4
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + cleanup)

    for address in (PREPARE, GEOMETRY):
        uc.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)
    counts = {}
    for entry in ENTRIES:
        cases = 512 if entry == INIT else 256
        for case in range(cases):
            for at, size in REGIONS:
                uc.mem_write(at, rng.randbytes(size))
            game = GAMES[case % len(GAMES)].encode()
            uc.mem_write(ARENA, game + b'\0')
            incoming = [rng.getrandbits(32) for _ in REGS]
            incoming[1] = ARENA
            incoming[3] = 0x202 | (case & 0x8D5)
            for reg, value in zip(REGS, incoming):
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F)
            uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
            uc.reg_write(UC_X86_REG_ESP, SP)
            write(SP, STOP)
            initial = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
            events = []
            uc.emu_start(entry, STOP, count=10000)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
            expected = {at: bytes(uc.mem_read(at, size)) for at, size in REGIONS}
            expected_regs = [uc.reg_read(reg) for reg in REGS]
            for fn, init in functions:
                memory = {at: bytearray(raw) for at, raw in initial.items()}
                errors, trace = [], []

                def locate(at, bits):
                    for base, raw in memory.items():
                        if base <= at and at + bits // 8 <= base + len(raw):
                            return raw, at - base
                    raise AssertionError(hex(at))

                def portable_read(at, bits=32):
                    raw, off = locate(at, bits)
                    return int.from_bytes(raw[off:off + bits // 8], 'little')

                def portable_write(at, value, bits=32):
                    raw, off = locate(at, bits)
                    raw[off:off + bits // 8] = (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little')

                @BOOT
                def boot(_, source, size):
                    trace.append(('prepare', source, size))
                    prepare(source, size, portable_write)

                @CALL
                def call(_, target, regs):
                    if target != GEOMETRY:
                        errors.append(hex(target))
                    r = regs.contents
                    trace.append(('geometry', *(getattr(r, name) for name in NAMES)))
                    geometry(r)

                bus = Bus(None, READ(lambda _, at, bits: portable_read(at, bits)),
                          WRITE(lambda _, at, value, bits: portable_write(at, value, bits)), call)
                r = Registers(*incoming, 0x37F)
                if entry == INIT:
                    init(C.byref(bus), None, boot, game, incoming[2])
                else:
                    assert fn(entry, C.byref(bus), C.byref(r))
                    actual = [getattr(r, name) for name in NAMES]
                    actual[3] &= ~0x10
                    expected_regs[3] &= ~0x10
                    assert actual == expected_regs, (hex(entry), case, actual, expected_regs)
                assert not errors, errors
                assert trace == events, (hex(entry), case, trace, events)
                assert memory == expected, (hex(entry), case, game, 'memory')
        counts[f'{entry:08x}'] = cases
    return {'cases_per_entry': counts, 'original_executions': sum(counts.values()),
            'portable_comparisons': sum(counts.values()) * len(functions),
            'native_crt_name_matching': True, 'game_names': GAMES,
            'stubbed_original_helpers': ['program preparation', 'existing shared geometry'],
            'init_scope': 'memory effects, source/count, ordering; scratch registers not contractual'}


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
