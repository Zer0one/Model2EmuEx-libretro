#!/usr/bin/env python3
"""Compare the isolated Model 2C lifecycle helpers against original x86."""
import argparse
import ctypes as C
import json
import random
import struct
import sys
from pathlib import Path

from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
    UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EIP,
    UC_X86_REG_ESP, UC_X86_REG_FPCW, UC_X86_REG_FPSW,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sharc/test"))
from difftest_bits import load_original, SP, STOP

STATE = 0x10EDEF0
ARENA = 0x72000000
LENGTH = 0x200
ENTRIES = {
    0x4B3470: "state_address",
    0x4B3480: "bind_fifos",
    0x4B34A0: "bind_external",
    0x4B34C0: "setup_fp",
    0x4B34D0: "state_save",
    0x4B34F0: "state_restore",
    0x4B3520: "reset_state",
}


class Bindings(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in
                ("input_fifo", "output_fifo", "read_external", "write_external")]


def portable(path):
    lib = C.CDLL(str(path.resolve()))
    args = {
        "state_address": ([C.POINTER(C.c_uint32), C.c_uint32], C.c_uint32),
        "bind_fifos": ([C.POINTER(Bindings), C.c_uint32, C.c_uint32], None),
        "bind_external": ([C.POINTER(Bindings)], None),
        "setup_fp": ([C.POINTER(C.c_uint16)], None),
        "state_save": ([C.c_void_p, C.c_void_p, C.c_size_t], C.c_void_p),
        "state_restore": ([C.c_void_p, C.c_void_p, C.c_size_t], C.c_void_p),
        "reset_state": ([C.c_void_p], None),
    }
    funcs = {}
    for name, (argtypes, restype) in args.items():
        fn = getattr(lib, "m2_tgpx4_" + name)
        fn.argtypes = argtypes
        fn.restype = restype
        funcs[name] = fn
    return funcs


def compare(exe, libraries):
    uc = load_original(exe)
    uc.mem_map(ARENA, 0x2000)
    libs = [portable(path) for path in libraries]
    rng = random.Random(0x2C)

    def write_word(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def read_word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    cases = {}
    binding_addrs = (0x10F0048, 0x10F0044, 0x10EE03C, 0x10EE038)
    preserved = (UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI)
    for entry, name in ENTRIES.items():
        for i in range(512):
            src = bytearray(rng.randbytes(LENGTH))
            dst = bytearray(rng.randbytes(LENGTH))
            pc = (0, 1, 0xFFFFFFFF, 0x80000000, rng.getrandbits(32))[i % 5]
            for block in (src, dst):
                struct.pack_into("<I", block, 0x114, pc)
            count = (0, 1, 0x113, 0x114, 0x115, 0x140, 0x144, LENGTH,
                     rng.randrange(LENGTH + 1))[i % 9]
            io_in, io_out = rng.getrandbits(32), rng.getrandbits(32)
            bindings = [rng.getrandbits(32) for _ in binding_addrs]
            copy = name in ("state_save", "state_restore")
            destination = ARENA + 0x1000
            uc.mem_write(ARENA, bytes(src))
            uc.mem_write(destination, bytes(dst))
            uc.mem_write(STATE, bytes(dst[:0x148]))
            for addr, value in zip(binding_addrs, bindings):
                write_word(addr, value)
            write_word(0x5AA724, io_in)
            write_word(0x5AA738, io_out)
            uc.mem_write(SP, struct.pack("<II", STOP, count))
            regs = {reg: rng.getrandbits(32) for reg in preserved}
            control = 0x7F | ((i & 3) << 10)
            status = (0, 0x4500, 0x3F)[i % 3]
            for reg, value in regs.items():
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_ESP, SP)
            uc.reg_write(UC_X86_REG_ECX, ARENA if name == "state_save" else destination)
            uc.reg_write(UC_X86_REG_EDX, destination if name == "state_save" else ARENA)
            uc.reg_write(UC_X86_REG_FPCW, control)
            uc.reg_write(UC_X86_REG_FPSW, status)
            uc.emu_start(entry, STOP, count=4096)
            assert uc.reg_read(UC_X86_REG_EIP) == STOP, (name, "return")
            assert uc.reg_read(UC_X86_REG_ESP) == SP + (8 if copy else 4), (name, "stack ABI")
            assert all(uc.reg_read(reg) == value for reg, value in regs.items()), (name, "register ABI")
            assert bytes(uc.mem_read(ARENA, LENGTH)) == src, (name, "source changed")
            for funcs in libs:
                fn = funcs[name]
                if copy:
                    inp, out = C.create_string_buffer(bytes(src)), C.create_string_buffer(bytes(dst))
                    assert fn(out, inp, count) == C.addressof(out)
                    assert bytes(out)[:LENGTH] == uc.mem_read(destination, LENGTH), (name, i)
                elif name == "state_address":
                    program = C.c_uint32(struct.unpack_from("<I", dst, 0x140)[0])
                    assert fn(C.byref(program), STATE) == uc.reg_read(UC_X86_REG_EAX)
                    assert program.value == read_word(STATE + 0x140)
                elif name == "setup_fp":
                    fp = C.c_uint16(control)
                    fn(C.byref(fp))
                    # Unicorn exposes the raw FLDCW word. x87 reads back bit 6 set.
                    assert fp.value == (uc.reg_read(UC_X86_REG_FPCW) | 0x40), (name, i)
                    assert status == uc.reg_read(UC_X86_REG_FPSW), (name, "status changed")
                elif name == "reset_state":
                    out = C.create_string_buffer(bytes(dst[:0x148]))
                    fn(out)
                    assert bytes(out)[:0x148] == uc.mem_read(STATE, 0x148), (name, i)
                else:
                    bound = Bindings(*bindings)
                    if name == "bind_fifos":
                        fn(C.byref(bound), io_in, io_out)
                    else:
                        fn(C.byref(bound))
                    assert [getattr(bound, key) for key, _ in Bindings._fields_] == [
                        read_word(addr) for addr in binding_addrs], (name, i)
        cases[f"{entry:08x}"] = 512
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("libraries", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = compare(args.exe, args.libraries)
    report = {"cases_per_entry": cases, "original_executions": sum(cases.values()),
              "portable_comparisons": sum(cases.values()) * len(args.libraries)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
