#!/usr/bin/env python3
"""Compare Model 2C host FIFO/upload effects at the native scheduler boundary."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EIP, UC_X86_REG_ESP,
)
from difftest_lifecycle import load_original, SP, STOP

PROGRAM, INPUT, OUTPUT = 0x72000000, 0x72001000, 0x72002000
CONTROL, OFFSET, STOPPED = 0x10ED8CC, 0x10ED8D0, 0x10F0040
RUN = 0x4B6010
WIDTH = {0x4C5A30: 0, 0x4C5AC0: 0, 0x4C5B70: 32, 0x4C5BC0: 16, 0x4C5C10: 8}
ADDRESSES = (0, 0x87FFFF, 0x880000, 0x880001, 0x880010, 0x883FF0,
             0x883FFF, 0x884000, 0x884003, 0x887FFF, 0x888000, 0xFFFFFFFF)
CALLBACK = C.CFUNCTYPE(None, C.c_void_p)
DECODE = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32)


class Fifo(C.Structure):
    _fields_ = [("words", C.c_uint32 * 32), ("read", C.c_uint32),
                ("write", C.c_uint32), ("free", C.c_int32)]


class Host(C.Structure):
    _fields_ = [("program", C.c_void_p), ("input", C.POINTER(Fifo)), ("output", C.POINTER(Fifo)),
                ("control", C.c_uint32), ("offset", C.c_uint32), ("stopped", C.c_uint32),
                ("opaque", C.c_void_p), ("run", CALLBACK),
                ("shared", C.c_void_p), ("data", C.c_void_p), ("external", C.c_void_p),
                ("data_control", C.c_uint32), ("data_offset", C.c_uint32),
                ("shared_write", C.c_uint32), ("shared_read", C.c_uint32),
                ("reg_803008", C.c_uint32), ("decode_uploaded_program", DECODE)]


def compare(exe, paths):
    uc = load_original(exe)
    uc.mem_map(PROGRAM, 0x3000)
    accessors = []
    for path in paths:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_host_access
        fn.argtypes = [C.POINTER(Host), C.c_uint32, C.c_uint32, C.c_uint32,
                       C.POINTER(C.c_uint32)]
        fn.restype = C.c_bool
        accessors.append(fn)

    def write_word(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def read_word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    calls = []

    def boundary(emu, address, size, data):
        # The CPU execution loop is a separate recovery group. Stub precisely
        # its native call/tail-call boundary and observe FIFO state at entry.
        calls.append((read_word(STOPPED), bytes(emu.mem_read(INPUT, C.sizeof(Fifo))),
                      bytes(emu.mem_read(OUTPUT, C.sizeof(Fifo)))))
        sp = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_ESP, sp + 4)
        emu.reg_write(UC_X86_REG_EIP, read_word(sp))

    uc.hook_add(UC_HOOK_CODE, boundary, begin=RUN, end=RUN)
    write_word(0x5AA87C, PROGRAM)
    write_word(0x5AA724, INPUT)
    write_word(0x5AA738, OUTPUT)
    rng = random.Random(0x4C5A30)
    counts = {}
    for entry, bits in WIDTH.items():
        for i in range(768):
            program = rng.randbytes(96)
            addr = ADDRESSES[i % len(ADDRESSES)]
            value, stopped = rng.getrandbits(32), rng.getrandbits(32)
            control = (0, 0x80000000, 0x80000001, 0x7FFFFFFF)[i // 12 % 4]
            offset = (0, 1, 12, 87)[i // 48 % 4]
            fifos = [Fifo((C.c_uint32 * 32)(*(rng.getrandbits(32) for _ in range(32))),
                         (i + 31) % 32, i % 32, (-1, 0, 1, 31, 32, -(1 << 31), (1 << 31) - 1)[i % 7])
                     for _ in range(2)]
            for base, fifo in zip((INPUT, OUTPUT), fifos):
                uc.mem_write(base, bytes(fifo))
            uc.mem_write(PROGRAM, program)
            for where, word in ((CONTROL, control), (OFFSET, offset), (STOPPED, stopped), (SP, STOP)):
                write_word(where, word)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.reg_write(UC_X86_REG_ECX, addr)
            uc.reg_write(UC_X86_REG_EDX, value)
            calls.clear()
            uc.emu_start(entry, STOP, count=192)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP
            assert uc.reg_read(UC_X86_REG_ESP) == SP + 4

            for access in accessors:
                dest = C.create_string_buffer(program)
                inp, out = [Fifo.from_buffer_copy(bytes(fifo)) for fifo in fifos]
                portable_calls = []
                host = Host()

                @CALLBACK
                def run(_):
                    portable_calls.append((host.stopped, bytes(inp), bytes(out)))

                host = Host(C.addressof(dest), C.pointer(inp), C.pointer(out),
                            control, offset, stopped, None, run)
                result = C.c_uint32(0xC0DEC0DE)
                assert access(C.byref(host), entry, addr, value, C.byref(result))
                want = uc.reg_read(UC_X86_REG_EAX) & ((1 << bits) - 1) if bits else 0xC0DEC0DE
                observed = (result.value, bytes(dest)[:len(program)], bytes(inp), bytes(out),
                            host.control, host.offset, host.stopped, portable_calls)
                original = (want, bytes(uc.mem_read(PROGRAM, len(program))),
                            bytes(uc.mem_read(INPUT, C.sizeof(Fifo))),
                            bytes(uc.mem_read(OUTPUT, C.sizeof(Fifo))),
                            read_word(CONTROL), read_word(OFFSET), read_word(STOPPED), calls)
                assert observed == original, (hex(entry), i, hex(addr))
        counts[f"{entry:08x}"] = 768
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = compare(args.exe, args.libraries)
    report = {"cases_per_entry": counts, "original_executions": sum(counts.values()),
              "portable_comparisons": sum(counts.values()) * len(args.libraries),
              "stubbed_native_boundary": f"{RUN:08x}"}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
