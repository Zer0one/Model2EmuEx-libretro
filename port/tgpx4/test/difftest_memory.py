#!/usr/bin/env python3
"""Compare native Model 2C memory routing and program-completion dispatch."""
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
from difftest_host import DECODE, Host, OFFSET
from difftest_lifecycle import load_original, SP, STOP

SHARED, DATA, EXTERNAL = 0x20000000, 0x22000000, 0x22100000
DATA_CONTROL, DATA_OFFSET = 0x10ED8D4, 0x10ED8D8
WRITE, READ, REG_803008 = 0x5AA758, 0x5AA720, 0x5AA870
DECODE_SETUP = 0x4B7940
CASES = {
    0x4C58D0: (0x801008, 0x803008, 0x804000, 0x804FFF, 0x805000,
               0x800000, 0x800001, 0x8003F0, 0x803FE0, 0x803FF0,
               0x80400F, 0x807FFF, 0x808000, 0xFFFF4000),
    0x4C5990: (0x804000, 0x804004, 0, 0xFFF, 0xFFFFFFFF),
    0x4C59E0: (0x801008, 0x802008, 0x803008, 0x804008, 0),
    0x4C5A70: (0, 0x3FFFFF, 0x400000, 0x400001, 0x7FFFFF, 0x800000, 0xFFFFFFFF),
    0x4C5A90: (0, 0x3FFFFF, 0x400000, 0x400001, 0x7FFFFF, 0x800000, 0x800FFF),
    0x4C5C70: (0,),
}
READ_ENTRIES = {0x4C59E0, 0x4C5A90}


def compare(exe, libraries):
    uc = load_original(exe)
    for base, size in ((SHARED, 0x2000000), (DATA, 0x1000), (EXTERNAL, 0x4000)):
        uc.mem_map(base, size)
    accessors = []
    for path in libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_host_access
        fn.argtypes = [C.POINTER(Host), C.c_uint32, C.c_uint32, C.c_uint32,
                       C.POINTER(C.c_uint32)]
        fn.restype = C.c_bool
        accessors.append(fn)

    def write_word(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def read_word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    for address, value in ((0x5AA700, SHARED), (0x5AA8B0, DATA), (0x5AA8DC, EXTERNAL)):
        write_word(address, value)

    decoded = []

    def decode_boundary(emu, address, size, data):
        sp = emu.reg_read(UC_X86_REG_ESP)
        decoded.append((emu.reg_read(UC_X86_REG_EAX), read_word(sp + 4)))
        emu.reg_write(UC_X86_REG_ESP, sp + 8)
        emu.reg_write(UC_X86_REG_EIP, read_word(sp))

    uc.hook_add(UC_HOOK_CODE, decode_boundary, begin=DECODE_SETUP, end=DECODE_SETUP)
    buffers = {SHARED: C.create_string_buffer(0x2000000), DATA: C.create_string_buffer(0x1000),
               EXTERNAL: C.create_string_buffer(0x4000)}
    rng = random.Random(0x4C58D0)
    counts = {}
    for entry, addresses in CASES.items():
        for i in range(512):
            address = addresses[i % len(addresses)]
            write = (0, 1, 0x7FFFC, 0x7FFFF, 0xC0010004)[i // len(addresses) % 5]
            control = (0, 0x80000000, 0x80000001, 0x7FFFFFFF)[i % 4]
            data_offset = i % 32
            upload_offset = (0, 1, 7, 8, 0x100, 0xFFFFFFFF)[i % 6]
            value, read, reg = (rng.getrandbits(32) for _ in range(3))
            probes = {(SHARED, write & 0x7FFFF), (DATA, data_offset)}
            if entry == 0x4C5A70 and 0x400000 <= address < 0x800000:
                probes.add((SHARED, (address - 0x400000) * 4))
            if entry == 0x4C5A90 and 0x400000 <= address < 0x800000:
                probes.add((SHARED, address * 4))
                probes.add((SHARED, (address - 0x400000) * 4))
            if entry == 0x4C5A90 and address >= 0x800000:
                probes.add((EXTERNAL, (address - 0x800000) * 4))
            initial = {key: rng.randbytes(4) for key in sorted(probes)}
            for (base, offset), raw in initial.items():
                uc.mem_write(base + offset, raw)
            registers = (DATA_CONTROL, DATA_OFFSET, WRITE, READ, REG_803008, OFFSET)
            values = (control, data_offset, write, read, reg, upload_offset)
            for where, word in zip(registers, values):
                write_word(where, word)
            write_word(SP, STOP)
            for x86reg, word in ((UC_X86_REG_ESP, SP), (UC_X86_REG_ECX, address),
                                 (UC_X86_REG_EDX, value), (UC_X86_REG_EAX, 0xAABBCCDD)):
                uc.reg_write(x86reg, word)
            decoded.clear()
            uc.emu_start(entry, STOP, count=256)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
            for access in accessors:
                for (base, offset), raw in initial.items():
                    C.memmove(C.addressof(buffers[base]) + offset, raw, 4)
                portable_calls = []

                @DECODE
                def decode(_, size):
                    portable_calls.append((0, size))

                host = Host()
                host.shared, host.data, host.external = (C.addressof(buffers[base])
                                                        for base in (SHARED, DATA, EXTERNAL))
                host.data_control, host.data_offset = control, data_offset
                host.shared_write, host.shared_read, host.reg_803008 = write, read, reg
                host.offset, host.decode_uploaded_program = upload_offset, decode
                result = C.c_uint32(0xC0DEC0DE)
                assert access(C.byref(host), entry, address, value, C.byref(result))
                want = uc.reg_read(UC_X86_REG_EAX) if entry in READ_ENTRIES else 0xC0DEC0DE
                assert result.value == want, (hex(entry), i, "result")
                assert (host.data_control, host.data_offset, host.shared_write, host.shared_read,
                        host.reg_803008, host.offset) == tuple(map(read_word, registers)), (hex(entry), i, "latches")
                assert portable_calls == decoded, (hex(entry), i, "decoder boundary")
                for base, offset in probes:
                    assert C.string_at(C.addressof(buffers[base]) + offset, 4) == uc.mem_read(base + offset, 4), (
                        hex(entry), i, "memory", hex(base + offset))
        counts[f"{entry:08x}"] = 512
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
              "stubbed_native_boundary": f"{DECODE_SETUP:08x}"}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
