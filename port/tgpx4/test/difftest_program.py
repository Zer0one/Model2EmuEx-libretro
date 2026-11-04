#!/usr/bin/env python3
"""Compare Model 2C program setup around the native subdecoder boundary."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_EIP,
    UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EDI,
)
from difftest_decode import Registers, SUBDECODE
from difftest_lifecycle import load_original, STATE, SP, STOP

SOURCE, STORAGE, LIST = 0x72000000, 0x72011000, 0x72020000
HEAD, NEXT, NODE = LIST + 0x100, LIST + 0x200, LIST + 0x300
BASE, ACTIVE_STATE, RECORD = 0x10481F0, 0x10481F4, 0x104824C
ENTRY = 0x4B7940
PREFIX, RECORD_BYTES = 0x2C, 0x94
U32, PTR = C.c_uint32, C.c_void_p


class Program(C.Structure):
    _fields_ = [("state", C.c_uint8 * 0x148), ("base", U32), ("active_state", U32),
                ("record", U32)]


class Descriptor(C.Structure):
    _fields_ = [(name, U32) for name in ("flag", "state", "bytes", "restore", "save")]
    _fields_ += [("name", C.c_char_p)]


RELEASE = C.CFUNCTYPE(None, PTR, U32)
ALLOCATE = C.CFUNCTYPE(PTR, PTR, U32, C.POINTER(U32))
DECODE = C.CFUNCTYPE(None, PTR, U32, U32, C.POINTER(U32))
READ = C.CFUNCTYPE(U32, PTR, U32)
WRITE = C.CFUNCTYPE(None, PTR, U32, U32)
CREATE = C.CFUNCTYPE(U32, PTR, U32, U32, C.POINTER(Descriptor))
FATAL = C.CFUNCTYPE(None, PTR, C.c_char_p)


class Hooks(C.Structure):
    _fields_ = [("opaque", PTR), ("release", RELEASE), ("allocate", ALLOCATE), ("decode", DECODE)]


class Registration(C.Structure):
    _fields_ = [("opaque", PTR), ("list", U32), ("read", READ), ("write", WRITE),
                ("create", CREATE), ("fatal", FATAL)]


def compare(exe, libraries, integrated=False):
    uc = load_original(exe)
    for base, size in ((SOURCE, 0x1000), (STORAGE - 0x1000, 0x2000), (LIST, 0x1000)):
        uc.mem_map(base, size)
    operands = (U32 * 480).from_buffer_copy(uc.mem_read(0x572AC0, 480 * 4))
    alu = (U32 * 32).from_buffer_copy(uc.mem_read(0x573248, 32 * 4))
    conditions = (U32 * 64).from_buffer_copy(uc.mem_read(0x5732C8, 64 * 4))
    functions = []
    for path in libraries:
        library = C.CDLL(str(path.resolve()))
        fn = library.m2_tgpx4_prepare_program
        fn.argtypes = [C.POINTER(Program), PTR, U32, U32, C.POINTER(Hooks), C.POINTER(Registration)]
        fn.restype = None
        dispatcher = library.m2_tgpx4_decode_instruction
        dispatcher.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(U32), C.POINTER(Registers), SUBDECODE, PTR]
        dispatcher.restype = None
        subdecoders = {}
        for entry, name in ((0x4B6730, 'control'), (0x4B6B90, 'wide_move'),
                            (0x4B6AC0, 'immediate'), (0x4B6EF0, 'transfers'),
                            (0x4B7100, 'move'), (0x4B7440, 'parallel'),
                            (0x4B75D0, 'operands'), (0x4B76B0, 'operands')):
            decoder = getattr(library, 'm2_tgpx4_decode_' + name)
            decoder.argtypes = [U32, U32, C.POINTER(U32), C.POINTER(Registers), C.POINTER(U32)]
            if name in ('control', 'operands'):
                decoder.argtypes += [C.POINTER(U32)]
            decoder.restype = None
            subdecoders[entry] = decoder
        functions.append((fn, dispatcher, subdecoders))

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def put(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def rewrite_inputs(low, high):
        # Give the orchestration test full control over the decoder output,
        # including the exact two magic values that enable the native rewrite.
        return (0x4B38E0 if low & 1 else low, 0x4B3820 if low & 2 else high)

    events = []

    def boundary(emu, address, size, data):
        stack = emu.reg_read(UC_X86_REG_ESP)
        pop = 4
        if address == 0x401050:
            desc = emu.reg_read(UC_X86_REG_ESI)
            name = bytes(emu.mem_read(word(desc + 4), 6)).split(b"\0")[0]
            events.append(("register", word(stack + 4), word(stack + 8), word(desc) & 255,
                           *(word(desc + offset) for offset in (8, 12, 16, 20)), name))
            put(NODE + 4, NEXT)
            emu.reg_write(UC_X86_REG_EAX, NODE)
            pop = 12
        elif address == 0x48D0F5:
            events.append(("release", word(stack + 4), word(BASE)))
        elif address == 0x48D12F:
            events.append(("allocate", word(stack + 4), word(ACTIVE_STATE)))
            emu.reg_write(UC_X86_REG_EAX, STORAGE)
        else:
            low, high = emu.reg_read(UC_X86_REG_EAX), emu.reg_read(UC_X86_REG_EBX)
            record = word(RECORD)
            events.append(("decode", low, high, record, word(record + 0x8C),
                           word(STATE + 0x140)))
            if integrated:
                return  # Observe the real dispatcher; do not replace it.
            first, second = rewrite_inputs(low, high)
            put(record + 0xC, first)
            put(record + 0x68, second)
        emu.reg_write(UC_X86_REG_EIP, word(stack))
        emu.reg_write(UC_X86_REG_ESP, stack + pop)

    for address in (0x401050, 0x48D0F5, 0x48D12F, 0x4B77A0):
        uc.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)

    rng = random.Random(0x4B7940)
    for i in range(512):
        length = (0, 1, 7, 8, 9, 16, 31, 48, 79)[i % 9]
        source = rng.randbytes(max(length, 1))
        old = 0x72010000 if i & 1 else 0
        state = bytearray(rng.randbytes(0x148))
        struct.pack_into("<I", state, 0x140, old)
        initial = bytearray(rng.randbytes(PREFIX + 10 * RECORD_BYTES))
        # Seed both record-zero allocator prefix and in-array predecessors.
        for at in range(0, len(initial) - 3, RECORD_BYTES):
            if i & 2:
                struct.pack_into("<I", initial, at, 0x4B37E0)
        registration = LIST if i & 4 else 0
        initial_list = bytearray(0x400)
        for where, value in ((LIST, HEAD), (LIST + 4, (0, 0x0AAAAAA8, 0xFFFFFFFF)[i % 3]),
                             (HEAD + 4, NEXT)):
            struct.pack_into("<I", initial_list, where - LIST, value)

        for where, raw in ((STATE, state), (SOURCE, source), (STORAGE - PREFIX, initial),
                           (LIST, initial_list)):
            uc.mem_write(where, bytes(raw))
        put(0x5AA87C, SOURCE)
        put(SP, STOP)
        put(SP + 4, length)
        registers = {UC_X86_REG_EBP: 0x66778899, UC_X86_REG_ESI: 0x12345678,
                     UC_X86_REG_EDI: 0xABCDEF01, UC_X86_REG_EBX: 0x01122334}
        for register, value in registers.items():
            uc.reg_write(register, value)
        uc.reg_write(UC_X86_REG_EAX, registration)
        uc.reg_write(UC_X86_REG_ESP, SP)
        events.clear()
        uc.emu_start(ENTRY, STOP, count=4096)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 8
        assert all(uc.reg_read(register) == value for register, value in registers.items())

        for fn, dispatcher, subdecoders in functions:
            traces = []
            portable = Program()
            portable.state[:] = state
            storage = C.create_string_buffer(bytes(initial))
            list_data = bytearray(initial_list)
            src = C.create_string_buffer(source)

            @RELEASE
            def release(_, token):
                traces.append(("release", token, portable.base))

            @ALLOCATE
            def allocate(_, size, token):
                traces.append(("allocate", size, portable.active_state))
                token[0] = STORAGE
                return C.addressof(storage) + PREFIX

            scratch = Registers()

            @SUBDECODE
            def subdecode(_, entry, registers, record):
                if entry in (0x4B75D0, 0x4B76B0):
                    args = [entry, portable.record, record, registers, operands, alu]
                else:
                    args = [portable.record, STATE, record, registers, operands]
                    if entry == 0x4B6730:
                        args.append(conditions)
                subdecoders[entry](*args)

            @DECODE
            def decode(_, low, high, record):
                traces.append(("decode", low, high, portable.record, record[0x8C // 4],
                               struct.unpack_from("<I", bytes(portable.state), 0x140)[0]))
                if integrated:
                    previous = None if portable.record == STORAGE else C.cast(
                        C.addressof(record.contents) - RECORD_BYTES, C.POINTER(U32))
                    dispatcher(low, high, record, previous, C.byref(scratch), subdecode, None)
                else:
                    record[0xC // 4], record[0x68 // 4] = rewrite_inputs(low, high)

            @READ
            def read(_, address):
                return struct.unpack_from("<I", list_data, address - LIST)[0]

            @WRITE
            def write(_, address, value):
                struct.pack_into("<I", list_data, address - LIST, value)

            @CREATE
            def create(_, head, next_node, descriptor):
                desc = descriptor.contents
                traces.append(("register", head, next_node, desc.flag, desc.state, desc.bytes,
                               desc.restore, desc.save, desc.name))
                write(None, NODE + 4, NEXT)
                return NODE

            hooks = Hooks(None, release, allocate, decode)
            reg = Registration(None, registration, read, write, create, FATAL())
            fn(C.byref(portable), src, length, STATE, C.byref(hooks), C.byref(reg))
            assert traces == events, (i, traces, events)
            assert bytes(portable.state) == uc.mem_read(STATE, 0x148), i
            assert (portable.base, portable.active_state, portable.record) == tuple(
                map(word, (BASE, ACTIVE_STATE, RECORD))), i
            assert bytes(storage)[:len(initial)] == uc.mem_read(STORAGE - PREFIX, len(initial)), i
            assert list_data == uc.mem_read(LIST, len(list_data)), i
    return {f"{ENTRY:08x}": 512}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    isolated = compare(args.exe, args.libraries)
    integrated = compare(args.exe, args.libraries, integrated=True)
    cases = {key: value + integrated[key] for key, value in isolated.items()}
    report = {"cases_per_entry": cases, "original_executions": sum(cases.values()),
              "portable_comparisons": sum(cases.values()) * len(args.libraries),
              "stubbed_native_boundaries_isolated": ["00401050", "0048d0f5", "0048d12f", "004b77a0"],
              "stubbed_native_boundaries_integrated": ["00401050", "0048d0f5", "0048d12f"],
              "integrated_original_executions": sum(integrated.values())}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
