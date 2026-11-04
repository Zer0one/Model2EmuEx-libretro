#!/usr/bin/env python3
"""ROM-free upload/decode/execute integration with native synthetic programs.

Only CRT allocation is replaced. Original decoders, wrappers, arithmetic,
register transfers, queues and FIFO scheduler execute their real bodies.
Class 3 and FP numerical operations are covered by separate fixtures.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import sys
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
import difftest_decode as D
sys.path.insert(0, str(Path(__file__).resolve().parent))
import difftest_execute as E
import difftest_program as P
from difftest_lifecycle import load_original, STATE, SP, STOP

U32, PTR = C.c_uint32, C.c_void_p
SOURCE, STORAGE, FIFO = 0x72000000, 0x72010000, 0x72020000
BASE, ACTIVE, RECORD, STOPPED = 0x10481F0, 0x10481F4, 0x104824C, 0x10F0040
GAMES = ('hotd', 'hotdo', 'HOTD', 'overrev', 'overrevb', 'skisuprg', 'waverunr',
         'segawski', 'dyn', 'dynamcop', 'dyndeka2', 'Dynxxx', 'tops', 'topskatr', 'topskatru', 'TOPS', 'stcc', 'unknown')
WRAPPERS = (0x4B3550, 0x4B3560, 0x4B35A0, 0x4B35E0, 0x4B3630, 0x4B3690, 0x4B36E0)
REGIONS = ((STATE, 0x2164), (0x1048100, 0x150), (0x10ED9A4, 4),
           (STORAGE - 0x1000, 0x11000), (FIFO, 0x1000), (0x10F1FEC, 4))


class Memory(C.Structure):
    _fields_ = [("opaque", PTR), ("release", P.RELEASE), ("allocate", P.ALLOCATE)]


class Device(C.Structure):
    _fields_ = [('program', P.Program), ('registers', E.Registers), ('machine', E.Bus),
                ('bus', E.Bus), ('memory', Memory), ('registration', C.POINTER(P.Registration))]


def program(rng, case, memory=False, fp=False):
    words = []
    if fp:
        # Keep r0/r1 as exact powers of two; every destination is r8 or above.
        # This covers connected FP dispatch without relying on Unicorn's
        # known transcendental/exception deficiencies for numerical proof.
        for i in range(16):
            value = (127 + (2 * (case % 5 - 2) if i == 0 else 1)) << 23
            words.append(((i << 19) | ((value & 31) << 27), 0xE0000000 | (value >> 5)))
        for i in range(96):
            cls = (0, 1, 2, 4, 5, 6)[i // 16]
            high = (cls << 29) | ((i % 16) << 24) | (1 << 15) | (8 << 10) | 0x200
            low = 0
            if cls < 3:
                high |= 1
                if cls != 2: low = 9 << 27
            if cls == 0: low |= (10 << 20) | (1 << 15) | (11 << 10)
            elif cls == 1: low |= (10 << 19) | (1 << 12)
            elif cls == 4: low = (9 << 28) | (1 << 13) | (10 << 8)
            elif cls == 5: low = (1 << 31) | (9 << 24)
            words.append((low, high))
        words.append((0x80000000, 0xA7000218))
        return b''.join(struct.pack('<II', *w) for w in words)
    for i in range(32):
        value = rng.getrandbits(32)
        words.append(((i % 16 << 19) | ((value & 31) << 27), 0xE0000000 | (value >> 5)))
    for i in range(32 + (case % 3) * 32):
        cls = (0, 1, 2, 4, 5, 6)[(i + case) % 6]
        low = 0
        high = (cls << 29) | (rng.randrange(16, 32) << 24) | (rng.randrange(16) << 20)
        high |= (rng.randrange(16) << 15) | (rng.randrange(16) << 10)
        if cls < 3:
            high |= (rng.randrange(16) << 5) | rng.randrange(16)
            if cls != 2: low |= rng.randrange(16) << 27
        else: high |= 0x200
        if cls == 0:
            low |= (rng.randrange(16) << 20) | (rng.randrange(16) << 15)
            low |= (rng.randrange(16) << 10) | (rng.randrange(16) << 5)
        elif cls == 1:
            low |= (rng.randrange(16) << 19) | (rng.randrange(16) << 12)
        elif cls == 4:
            high |= rng.randrange(16) << 1
            low |= (rng.randrange(16) << 28) | (rng.randrange(16) << 13) | (rng.randrange(16) << 8)
        elif cls == 5:
            source = rng.randrange(16)
            high |= source >> 1
            low |= ((source & 1) << 31) | (rng.randrange(16) << 24)
        words.append((low, high))
    if memory:
        def immediate(selector, value, extra=0):
            words.append(((selector << 19) | ((value & 31) << 27) | extra,
                          0xE0000000 | (value >> 5)))
        # Native address registers, kept in the internal memory range while
        # all sixteen original address-generator selectors are exercised.
        for index in range(8): immediate(24 + index, 128 + 16 * index)
        for i in range(32):
            selector = (0x40 if i & 1 else 0x60) + i % 8
            extra = (rng.randrange(8) << 7) | (rng.randrange(8) << 4) | (i % 16)
            immediate(selector, rng.getrandbits(32), extra)
            # Matching native wide-memory reader into one of the data registers.
            words.append((((selector & 1) << 31) | (rng.randrange(16) << 24) | extra,
                          0xA7000200 | (selector >> 1)))
            immediate(48, rng.getrandbits(32))  # Native deferred ring increment.
        for i in range(8):
            immediate(50, rng.getrandbits(32))  # Output FIFO.
            words.append((0x80000000, 0xA7000218))  # Input FIFO.
    # A native FIFO reader sets decoded flag +84. The full-count boundary
    # stops before this instruction; no invented stop opcode or patched record.
    words.append((0x80000000, 0xA7000218))
    return b''.join(struct.pack('<II', *w) for w in words)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--initialize', action='store_true', help='Compare native driver plus bootstrap/decode/reset without running its synthetic program')
    ap.add_argument('--device', action='store_true', help='Use the C device composition and compare complete final memory')
    ap.add_argument('--fp', action='store_true', help='Connected FP/integer program using exact-power operands')
    ap.add_argument('--composed', action='store_true', help='Use the C loader and built-in native decoder tables')
    ap.add_argument('--memory', action='store_true', help='Add internal memory, deferred modifiers/ring and live FIFO transfers')
    args = ap.parse_args()
    if args.initialize: args.device = True
    if args.device: args.composed = True
    if args.fp and (not args.composed or args.memory): ap.error("--fp requires --composed and excludes --memory")
    global REGIONS
    if args.initialize:
        REGIONS += ((0x573300, 0x200), (0x5AA720, 0x20), (0x5AEB90, 4),
                    (0xDCEC58, 4), (0x10ED950, 0x30), (0x5AA87C, 4), (SOURCE, 0x1000))
    uc = load_original(args.exe)
    for address, length in ((SOURCE, 0x1000), (STORAGE - 0x1000, 0x11000), (FIFO, 0x1000)):
        uc.mem_map(address, length)
    operands = (U32 * 480).from_buffer_copy(uc.mem_read(0x572AC0, 1920))
    alu = (U32 * 32).from_buffer_copy(uc.mem_read(0x573248, 128))
    conditions = (U32 * 64).from_buffer_copy(uc.mem_read(0x5732C8, 256))
    libs = []
    for path in args.libraries:
        lib = C.CDLL(str(path.resolve()))
        lib.m2_tgpx4_prepare_program.argtypes = [C.POINTER(P.Program), PTR, U32, U32, C.POINTER(P.Hooks), C.POINTER(P.Registration)]
        lib.m2_tgpx4_decode_instruction.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(U32), C.POINTER(D.Registers), D.SUBDECODE, PTR]
        lib.m2_tgpx4_load_program.argtypes = [C.POINTER(P.Program), PTR, U32, U32, C.POINTER(Memory), C.POINTER(P.Registration)]
        lib.m2_tgpx4_dispatch.argtypes = [U32, C.POINTER(E.Bus), C.POINTER(E.Registers)]
        lib.m2_tgpx4_dispatch.restype = C.c_bool
        lib.m2_tgpx4_device_bind.argtypes = [C.POINTER(Device)]
        lib.m2_tgpx4_device_initialize.argtypes = [C.POINTER(Device), C.c_char_p]
        lib.m2_tgpx4_device_load.argtypes = [C.POINTER(Device), PTR, U32]
        lib.m2_tgpx4_device_run.argtypes = [C.POINTER(Device), U32, C.c_bool]
        decoders = {}
        for entry, name in ((0x4B6730, 'control'), (0x4B6B90, 'wide_move'), (0x4B6AC0, 'immediate'),
                            (0x4B6EF0, 'transfers'), (0x4B7100, 'move'), (0x4B7440, 'parallel'),
                            (0x4B75D0, 'operands'), (0x4B76B0, 'operands')):
            fn = getattr(lib, 'm2_tgpx4_decode_' + name)
            fn.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(D.Registers), C.POINTER(U32)]
            if name in ('control', 'operands'): fn.argtypes += [C.POINTER(U32)]
            decoders[entry] = fn
        handlers = []
        for name in ('register', 'integer', 'control', 'address', 'transfer'):
            fn = getattr(lib, 'm2_tgpx4_execute_' + name)
            fn.argtypes = [U32, C.POINTER(E.Bus), C.POINTER(E.Registers)]
            fn.restype = C.c_bool
            handlers.append(fn)
        lib.m2_tgpx4_execute_wrapper.argtypes = [U32, C.POINTER(E.Bus), C.POINTER(E.Registers)]
        lib.m2_tgpx4_execute.argtypes = [C.POINTER(E.Bus), C.POINTER(E.Registers)]
        libs.append((lib, decoders, handlers))

    def read(at): return int.from_bytes(uc.mem_read(at, 4), 'little')
    def write(at, value): uc.mem_write(at, struct.pack('<I', value))
    original_trace = []

    def boundary(emu, address, size, opaque):
        if address in WRAPPERS:
            original_trace.append((address, emu.reg_read(UC_X86_REG_ESP), read(RECORD), bytes(emu.mem_read(STATE, 0x140))))
            return
        if address not in (0x48D12F, 0x48D0F5): return
        if address == 0x48D12F: emu.reg_write(UC_X86_REG_EAX, STORAGE)
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, read(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    uc.hook_add(UC_HOOK_CODE, boundary, begin=0x4B3550, end=0x4B36E0)
    for address in (0x48D12F, 0x48D0F5):
        uc.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
    rng = random.Random(0x2C7940)
    digest, total, classes = hashlib.sha256(), 0, set()
    for case in range(64):
        source = program(rng, case, args.memory, args.fp)
        game = GAMES[case % len(GAMES)].encode()
        if args.initialize: source = source[:0x100]
        digest.update(source)
        for base, length in REGIONS: uc.mem_write(base, bytes(length))
        uc.mem_write(SOURCE, source)
        write(0x5AA87C, SOURCE)
        write(SP, STOP); write(SP + 4, len(source))
        uc.reg_write(UC_X86_REG_EAX, 0); uc.reg_write(UC_X86_REG_ESP, SP)
        if args.initialize:
            uc.mem_write(SOURCE + 0xF00, game + b'\0')
            uc.reg_write(UC_X86_REG_ECX, SOURCE + 0xF00)
            uc.reg_write(UC_X86_REG_EDX, 0)
            uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
            write(0x5AA724, FIFO); write(0x5AA738, FIFO + 0x100)
        initial = {base: bytes(uc.mem_read(base, length)) for base, length in REGIONS}
        uc.emu_start(0x4C5C80 if args.initialize else 0x4B7940, STOP, count=500000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
        prepared = {base: bytes(uc.mem_read(base, length)) for base, length in REGIONS}
        original_trace.clear()
        if not args.initialize:
            write(0x10F0048, FIFO); write(0x10F0044, FIFO + 0x100)
            write(FIFO + 0x88, 24 if args.memory else 32); write(FIFO + 0x188, 32)
            original_trace.clear()
            write(SP, STOP); uc.reg_write(UC_X86_REG_ESP, SP)
            uc.reg_write(UC_X86_REG_FPCW, 0x37F); uc.reg_write(UC_X86_REG_FPSW, 0)
            uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
            uc.emu_start(0x4B6010, STOP, count=500000)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and read(STOPPED) == 1, case
            expected = {base: bytes(uc.mem_read(base, length)) for base, length in REGIONS}
            assert len(original_trace) == len(source) // 8 - 1, (case, len(original_trace))
            total += len(original_trace)
        else:
            expected = prepared
        classes.update(high >> 29 for low, high in struct.iter_unpack('<II', source))
        for lib, decoders, handlers in libs:
            state = P.Program()
            storage = (U32 * (0x11000 // 4))()
            token_offset = 0x1000
            scratch = D.Registers()
            errors, trace = [], []

            @P.ALLOCATE
            def allocate(_, size, token):
                assert size < 0x10000
                token[0] = STORAGE
                return C.addressof(storage) + token_offset

            @D.SUBDECODE
            def subdecode(_, entry, registers, record):
                argv = [entry, state.record, record, registers, operands, alu] if entry in (0x4B75D0, 0x4B76B0) else [state.record, STATE, record, registers, operands]
                if entry == 0x4B6730: argv.append(conditions)
                decoders[entry](*argv)

            @P.DECODE
            def decode(_, low, high, record):
                previous = None if state.record == STORAGE else C.cast(C.addressof(record.contents) - 0x94, C.POINTER(U32))
                lib.m2_tgpx4_decode_instruction(low, high, record, previous, C.byref(scratch), subdecode, None)

            hooks = P.Hooks(None, P.RELEASE(lambda *_: None), allocate, decode)
            src = C.create_string_buffer(source)
            if args.device:
                pass  # Device load runs below, once the machine bus exists.
            elif args.composed:
                policy = Memory(None, hooks.release, allocate)
                lib.m2_tgpx4_load_program(C.byref(state), src, len(source), STATE, C.byref(policy), None)
            else:
                lib.m2_tgpx4_prepare_program(C.byref(state), src, len(source), STATE, C.byref(hooks), None)
            if not args.device:
                assert bytes(state.state) == prepared[STATE][:0x148], (case, 'prepared state')
                assert bytes(storage) == prepared[STORAGE - 0x1000], (case, 'decoded records')
            memory = {base: bytearray(length) for base, length in REGIONS}
            memory[STATE][:0x148] = bytes(state.state)
            memory[STORAGE - 0x1000][:] = bytes(storage)

            def locate(at, count):
                for base, data in memory.items():
                    if base <= at and at + count <= base + len(data): return data, at - base
                raise AssertionError(f'unmapped {at:08x}/{count}')

            def get(at, bits=32):
                data, off = locate(at, bits // 8)
                return int.from_bytes(data[off:off + bits // 8], 'little')

            def put(at, value, bits=32):
                data, off = locate(at, bits // 8)
                data[off:off + bits // 8] = (value & ((1 << bits) - 1)).to_bytes(bits // 8, 'little')

            for at, val in ((BASE, state.base), (ACTIVE, state.active_state), (RECORD, state.record),
                            (0x10F0048, FIFO), (0x10F0044, FIFO + 0x100), (FIFO + 0x88, 24 if args.memory else 32), (FIFO + 0x188, 32)):
                put(at, val)

            @E.CALL
            def call(_, entry, registers):
                if entry in WRAPPERS:
                    trace.append((entry, registers.contents.esp, get(RECORD), bytes(memory[STATE][:0x140])))
                if args.composed:
                    handled = lib.m2_tgpx4_dispatch(entry, C.byref(bus), registers)
                elif entry in WRAPPERS:
                    lib.m2_tgpx4_execute_wrapper(entry, C.byref(bus), registers)
                    handled = True
                else:
                    handled = any(fn(entry, C.byref(bus), registers) for fn in handlers)
                if not handled:
                    errors.append(f'unimplemented callback {entry:08x}')

            bus = E.Bus(None, E.READ(lambda _, at, bits: get(at, bits)), E.WRITE(lambda _, at, value, bits: put(at, value, bits)), call)
            registers = E.Registers(fp_control=0x37F, esp=SP)
            if args.device:
                device = Device(registers=registers, machine=bus, memory=Memory(None, hooks.release, allocate))
                lib.m2_tgpx4_device_bind(C.byref(device))
                for base, data in memory.items(): data[:] = initial[base]
                if args.initialize:
                    lib.m2_tgpx4_device_initialize(C.byref(device), game)
                else:
                    lib.m2_tgpx4_device_load(C.byref(device), src, len(source))
                memory[STORAGE - 0x1000][:] = bytes(storage)
                for base, data in memory.items():
                    assert data == prepared[base], (case, 'device preparation', hex(base))
                for at, val in (() if args.initialize else ((0x10F0048, FIFO), (0x10F0044, FIFO + 0x100),
                                (FIFO + 0x88, 24 if args.memory else 32), (FIFO + 0x188, 32))):
                    put(at, val)
                if not args.initialize:
                    lib.m2_tgpx4_device_run(C.byref(device), SP, False)
            else:
                lib.m2_tgpx4_execute(C.byref(bus), C.byref(registers))
            assert not errors, (case, errors)
            assert args.device or trace == original_trace, (case, 'instruction-boundary trace', next((i for i, pair in enumerate(zip(trace, original_trace)) if pair[0] != pair[1]), None))
            for base, data in memory.items():
                assert data == expected[base], (case, f'memory {base:08x}', next((i for i, pair in enumerate(zip(data, expected[base])) if pair[0] != pair[1]), None))
    report = dict(programs=64, original_instructions=total, portable_instruction_comparisons=0 if args.device else total * len(libs),
                  original_program_executions=64, portable_program_comparisons=64 * len(libs),
                  instruction_classes=sorted(classes), source_sha256=digest.hexdigest(),
                  replaced_native_boundaries=['CRT malloc/free only'],
                  memory_and_live_fifo=args.memory, native_c_loader=args.composed, connected_fp=args.fp, native_c_device=args.device,
                  instruction_trace_compared=not args.device, driver_initialization=args.initialize,
                  scope='Synthetic programs, native FIFO stopping; no game execution claim')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
