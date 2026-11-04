#!/usr/bin/env python3
"""M2C scalar FP: original x86 plus an independent x87/Rosetta sequence oracle.

No host float conversions: all inputs/results are binary32 bit patterns.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import subprocess
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from difftest_lifecycle import load_original, SP, STOP

ENTRIES = (0x4B4E60, 0x4B53B0, 0x4B5630, 0x4B56A0, 0x4B5740, 0x4B57B0,
           0x4B5850, 0x4B54B0, 0x4B5460, 0x4B6630, 0x4B65C0, 0x4B5510, 0x4B6530, 0x4B64A0) + tuple(range(0x4B3FB0, 0x4B4030, 16))
EDGE = (0, 0x80000000, 1, 0x80000001, 0x7FFFFF, 0x807FFFFF, 0x800000, 0x80800000,
        0x3F000000, 0x3F7FFFFF, 0x3F800000, 0xBF800000, 0x3FC00000, 0xBFC00000,
        0x4F000000, 0xCF000000, 0x4F800000, 0x5EFFFFFF, 0x5F000000, 0xDF000000,
        0xDF000001, 0x7F7FFFFF, 0xFF7FFFFF, 0x7F800000, 0xFF800000,
        0x7FC00000, 0xFFC12345, 0x7F800001, 0xFF812345,
        0x437F0000, 0x437FFFFF, 0x43800000, 0xBF000000, 0x33800000, 0xB3800000)
ARENA, CODE, ACTIVE, RECORD = 0x72000000, 0x72001000, 0x10481F4, 0x104824C


class FP(C.Structure):
    _fields_ = [('control', C.c_uint16), ('status', C.c_uint16), ('crt_sse2', C.c_uint32)]


def snan(x):
    return x & 0x7FFFFFFF > 0x7F800000 and not x & 0x400000


def denorm(x):
    return 0 < x & 0x7FFFFFFF < 0x800000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('oracle', type=Path)
    parser.add_argument('libraries', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--portable-only', action='store_true')
    parser.add_argument('--x87-output', type=Path, help='Recorded six-word output from the native x87 sequence probe')
    parser.add_argument('--export-input', type=Path)
    parser.add_argument('--windows-output', '--original-output', dest='windows_output', type=Path)
    parser.add_argument('--original-backend', default='Windows x86 process')
    parser.add_argument('--windows-diagnostic', action='store_true',
                        help='Record translator differences; never report original equivalence')
    parser.add_argument('--log-only', action='store_true')
    parser.add_argument('--exclude-log', action='store_true', help='Qualified Unicorn baseline without FYL2X')
    args = parser.parse_args()
    if args.windows_diagnostic and not args.windows_output:
        parser.error('--windows-diagnostic requires --windows-output')
    if args.log_only and args.exclude_log:
        parser.error('--log-only and --exclude-log are mutually exclusive')
    rng = random.Random(0x4B4E60)
    inputs = [(a, b) for a in EDGE for b in EDGE] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(1024)]
    entries = ENTRIES
    if args.exclude_log:
        entries = tuple(e for e in ENTRIES if e != 0x4B64A0)
    if args.log_only:
        entries = (0x4B64A0,)
        values = list(EDGE) + list(range(0x3F800000 - 128, 0x3F800000 + 129))
        values += [(e << 23) + d for e in range(1, 255) for d in (-1, 0, 1)]
        values += [rng.randrange(1, 0x7F800000) for _ in range(16384)]
        inputs = [(x, 0) for x in dict.fromkeys(values)]
    vectors = [(entry, a, b, rng.getrandbits(32), 0x7F | (mode << 10), rng.choice((0, 0x4500, 0x4700, 0x3F, 0x453F)), sse2)
               for entry in entries for a, b in inputs for mode in range(4)
               for sse2 in ((0, 1) if entry == 0x4B5460 else (0,))]
    raw = b''.join(struct.pack('<7I', *v) for v in vectors)
    if args.export_input:
        args.export_input.write_bytes(raw)
        print(f'Exported {len(vectors)} vectors to {args.export_input}')
        return
    windows = None
    if args.windows_output:
        windows = list(struct.iter_unpack('<4I', args.windows_output.read_bytes()))
        assert len(windows) == len(vectors)
    if args.x87_output:
        reference_bytes = args.x87_output.read_bytes()
    else:
        run = subprocess.run([str(args.oracle.resolve())], input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        reference_bytes = run.stdout
    assert len(reference_bytes) == len(vectors) * 24
    refs = list(struct.iter_unpack('<6I', reference_bytes))
    functions = []
    for path in args.libraries:
        fn = C.CDLL(str(path.resolve())).m2_tgpx4_fp_operation
        fn.argtypes = [C.c_uint32] * 3 + [C.POINTER(C.c_uint32), C.POINTER(FP), C.POINTER(C.c_uint32)]
        fn.restype = C.c_bool
        functions.append(fn)
    uc = None if args.portable_only or windows is not None else load_original(args.exe)
    if uc is not None:
        uc.mem_map(ARENA, 0x2000)

    def write(at, value):
        uc.mem_write(at, struct.pack('<I', value))

    if uc is not None:
        write(ACTIVE, ARENA + 0x200)
        write(RECORD, ARENA)
        for off in (0, 0x14): write(ARENA + off, CODE)
        for off in (4, 0x18): write(ARENA + off, CODE + 16)
    operands = (0, 0)

    def read_operand(emu, address, size, data):
        emu.reg_write(UC_X86_REG_EAX, operands[address != CODE])
        stack = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, int.from_bytes(emu.mem_read(stack, 4), 'little'))
        emu.reg_write(UC_X86_REG_ESP, stack + 4)

    if uc is not None:
        uc.hook_add(UC_HOOK_CODE, read_operand, begin=CODE, end=CODE + 16)
    differences = {'numeric': 0, 'guest_flags': 0, 'x87': 0}
    windows_differences = {}
    for index, (v, reference) in enumerate(zip(vectors, refs)):
        ref, unflushed, captured = reference[:4], reference[4], reference[5]
        entry, a, b, status, cw, sw, sse2 = v
        for fn in functions:
            st, fp, result = C.c_uint32(status), FP(cw, sw, sse2), C.c_uint32()
            assert fn(entry, a, b, C.byref(st), C.byref(fp), C.byref(result)), hex(entry)
            got = result.value, st.value, fp.control | 0x40, fp.status
            assert got == ref, (index, tuple(map(hex, v)), 'portable/x87', tuple(map(hex, got)), tuple(map(hex, ref)))
        if args.portable_only: continue
        if windows is not None:
            original = windows[index]
            if args.windows_diagnostic:
                stats = windows_differences.setdefault(f'{entry:08x}',
                    dict(cases=0, numeric=0, guest_flags=0, control=0, x87=0, samples=[]))
                stats['cases'] += 1
                for field, a_value, b_value in zip(('numeric', 'guest_flags', 'control', 'x87'), original, ref):
                    stats[field] += a_value != b_value
                if original != ref and len(stats['samples']) < 4:
                    stats['samples'].append(dict(input=[f'{x:08x}' for x in v],
                        original=[f'{x:08x}' for x in original], reference=[f'{x:08x}' for x in ref]))
            else:
                assert original == ref, (index, tuple(map(hex, v)), 'original/x87',
                    tuple(map(hex, original)), tuple(map(hex, ref)))
            continue
        operands = a, b
        write(ARENA + 0x310, status)
        write(SP, STOP)
        write(0x10F1FEC, sse2)
        uc.reg_write(UC_X86_REG_MXCSR, 0x1F80)
        uc.reg_write(UC_X86_REG_ESP, SP)
        uc.reg_write(UC_X86_REG_FPCW, cw)
        uc.reg_write(UC_X86_REG_FPSW, sw)
        uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        uc.emu_start(entry, STOP, count=1000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP and uc.reg_read(UC_X86_REG_ESP) == SP + 4
        original = (uc.reg_read(UC_X86_REG_EAX), int.from_bytes(uc.mem_read(ARENA + 0x310, 4), 'little'),
                    uc.reg_read(UC_X86_REG_FPCW) | 0x40, uc.reg_read(UC_X86_REG_FPSW))
        why = (index, tuple(map(hex, v)), 'Unicorn/x87', tuple(map(hex, original)), tuple(map(hex, ref)))
        assert original[2] == ref[2], why
        expected_value = unflushed if entry == 0x4B4E60 and captured & 2 else ref[0]
        if original[0] != expected_value:
            # Missing FLD SNaN quieting may also change NaN operand selection.
            # Bound this to input NaN payloads, with only quiet/sign changes.
            assert snan(a) or snan(b), why
            choices = {x for operand in (a, b) for x in (operand, operand | 0x400000)
                       if x & 0x7FFFFFFF > 0x7F800000}
            if entry in (0x4B6630, 0x4B65C0): choices = {x & 0x7FFFFFFF for x in choices}
            assert original[0] in choices and expected_value in choices, why
        if original[1] != ref[1]:
            assert entry == 0x4B4E60 and captured & 2, why
            x = original[0]
            native_flags = (status & ~0x190000) | (0x100000 if x >> 31 and 0 < x & 0x7FFFFFFF <= 0x7F800000 else 0)
            native_flags |= 0x80000 if not x & 0x7FFFFFFF else 0
            assert original[1] == native_flags and ref[1] & 0x10000, why
        differences['numeric'] += original[0] != ref[0]
        differences['guest_flags'] += original[1] != ref[1]
        expected_sw = ref[3]
        if entry == 0x4B4E60 and captured & 2:
            x = original[0]
            cc = 0x4500 if x & 0x7FFFFFFF > 0x7F800000 else 0x4000 if not x & 0x7FFFFFFF else 0x100 if x >> 31 else 0
            expected_sw = (expected_sw & ~0x4700) | cc
        delta = original[3] ^ expected_sw
        assert not delta & ~0x23F, why
        if delta & 0x200:
            # Unicorn retains incoming C1 instead of the instruction's C1.
            assert original[3] & 0x200 == sw & 0x200, why
        if delta & 0x3F:
            # This is the established Unicorn omission, checked explicitly.
            assert original[3] & 0x3F == (0 if entry == 0x4B4E60 else sw & 0x3F), why
            if entry != 0x4B4E60:
                assert ref[3] & sw & 0x3F == sw & 0x3F, why
        differences['x87'] += bool(delta)
    root = Path(__file__).resolve().parents[1]
    report = {'scalar_cases_per_entry': {f'{e:08x}': len(inputs) * (8 if e == 0x4B5460 else 4) for e in entries},
              'scalar_original_executions': 0 if args.portable_only else len(vectors),
              'scalar_portable_comparisons': len(vectors) * len(functions),
              'original_backend': None if args.portable_only else args.original_backend if windows is not None else 'Unicorn',
              'input_sha256': hashlib.sha256(raw).hexdigest(),
              'indirect_operand_callbacks': 'fixtures; scalar body only',
              'oracle_scope': 'recorded x87 sequence probe; see host receipt' if args.x87_output else 'independent x87 sequences under Rosetta; not physical x86',
              'oracle_output_sha256': hashlib.sha256(reference_bytes).hexdigest(),
              'bounded_unicorn_discrepancies': differences,
              'source_sha256': hashlib.sha256((root / 'tgpx4_fp.c').read_bytes()).hexdigest(),
              'oracle_source_sha256': hashlib.sha256((root / 'test/x87_oracle.c').read_bytes()).hexdigest()}
    if args.windows_diagnostic:
        report['qualification'] = 'diagnostic only; Windows ARM x86 translator differs from Rosetta x87'
        report['windows_differences'] = windows_differences
    if windows is not None:
        report['original_output_sha256'] = hashlib.sha256(args.windows_output.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
