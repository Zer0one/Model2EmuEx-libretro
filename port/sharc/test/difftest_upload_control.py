#!/usr/bin/env python3
"""Original shared upload controller, including callback/latch ordering."""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn.x86_const import *
from difftest_bits import load_original, EXE_SHA256, STOP, SP
from difftest_host import Host, U32, P32, CALL

ENTRY = 0x4c79c0
FIELDS = ('program_control', 'program_offset', 'data_control', 'data_offset')
GLOBALS = (0x10ed8cc, 0x10ed8d0, 0x10ed8d4, 0x10ed8d8, 0x10ed8e0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('libraries', type=Path, nargs='+')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    mu = load_original(args.exe)
    rng = random.Random(41)
    def read(addr): return struct.unpack('<I', mu.mem_read(addr, 4))[0]
    def write(addr, value): mu.mem_write(addr, struct.pack('<I', value))
    # Native Model 2B driver table: completion entries at +3c and +40.
    write(0x5aa8c0, 0x574c78)
    callbacks = (read(0x574c78 + 0x3c), read(0x574c78 + 0x40))
    assert callbacks == (0x4c6470, 0x4c5ea0)
    original_trace = []
    def transform(values, kind):
        return [(v ^ (0x13579bdf + kind + i)) & 0xffffffff for i, v in enumerate(values)]
    def boundary(uc, address, size, opaque):
        if address not in callbacks: return
        kind = callbacks.index(address)
        values = [read(a) for a in GLOBALS]
        original_trace.append((kind, values))
        for a, v in zip(GLOBALS, transform(values, kind)): write(a, v)
        sp = uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP, read(sp))
        uc.reg_write(UC_X86_REG_ESP, sp + 4)
        uc.reg_write(UC_X86_REG_EAX, 0xdeadbeef)
        uc.reg_write(UC_X86_REG_ECX, 0x11223344)
        uc.reg_write(UC_X86_REG_EDX, 0x55667788)
    mu.hook_add(unicorn.UC_HOOK_CODE, boundary)
    libraries = []
    for path in args.libraries:
        lib = C.CDLL(str(path.resolve()))
        lib.m2_sharc_upload_control.argtypes = [C.POINTER(Host), P32, U32, U32, C.c_void_p, CALL, CALL]
        lib.m2_sharc_upload_control.restype = None
        libraries.append((path, lib))
    addresses = [0x980000, 0x980008, 0x98000c, 0, 0x980001, 0x980004,
                 0x980009, 0x98000d, 0x900008, 0xffffffff]
    addresses += [rng.getrandbits(32) for _ in range(22)]
    cases = 0
    for address in addresses:
        for sample in range(128):
            for phase in range(8):
                values = [rng.getrandbits(32) for _ in GLOBALS]
                value = rng.getrandbits(32)
                index = 2 if address == 0x980008 else 0
                if phase < 4:
                    values[index] = (values[index] & 0x7fffffff) | ((phase & 1) << 31)
                    value = values[index] ^ (0x80000000 if phase < 2 else 0x80000001)
                elif phase == 4: value = values[index]
                elif phase == 5: value = 0
                elif phase == 6: value = 0xffffffff
                for a, v in zip(GLOBALS, values): write(a, v)
                write(SP, STOP)
                mu.reg_write(UC_X86_REG_ESP, SP)
                mu.reg_write(UC_X86_REG_ECX, address)
                mu.reg_write(UC_X86_REG_EDX, value)
                preserved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_ESI: 0x87654321,
                             UC_X86_REG_EDI: 0x11111111, UC_X86_REG_EBP: 0x22222222}
                for reg, v in preserved.items(): mu.reg_write(reg, v)
                original_trace.clear()
                mu.emu_start(ENTRY, STOP, count=128)
                assert mu.reg_read(UC_X86_REG_EIP) == STOP and mu.reg_read(UC_X86_REG_ESP) == SP + 4
                assert all(mu.reg_read(reg) == v for reg, v in preserved.items())
                expected = [read(a) for a in GLOBALS]
                for path, lib in libraries:
                    host = Host()
                    for field, v in zip(FIELDS, values): setattr(host, field, v)
                    reg = U32(values[-1])
                    trace = []
                    def complete(kind):
                        got = [getattr(host, n) for n in FIELDS] + [reg.value]
                        trace.append((kind, got))
                        changed = transform(got, kind)
                        for n, v in zip(FIELDS, changed): setattr(host, n, v)
                        reg.value = changed[-1]
                    program = CALL(lambda _: complete(0))
                    data = CALL(lambda _: complete(1))
                    lib.m2_sharc_upload_control(C.byref(host), C.byref(reg), address, value, None, program, data)
                    actual = [getattr(host, n) for n in FIELDS] + [reg.value]
                    if actual != expected or trace != original_trace:
                        raise AssertionError(f'{path.name}/{address:x}/{sample}/{phase}: {actual} != {expected}')
                cases += 1
    source = Path(__file__).parents[1] / 'sharc_upload.c'
    report = dict(status='passed', entry=f'0x{ENTRY:08x}', cases=cases, mismatches=0, skipped=0,
                  seed=41, exe_sha256=EXE_SHA256, unicorn=unicorn.__version__,
                  scope='Shared i960 upload-control body; original program/data completion calls are explicit boundaries with ordered state mutation',
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  libraries=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p, _ in libraries])
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Upload controller:', cases, 'passed')


if __name__ == '__main__': main()
