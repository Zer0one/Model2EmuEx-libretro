#!/usr/bin/env python3
"""Recover the original A68K opcode dispatch inventory; no CPU replacement.

The compressed table is decoded independently and optionally compared with
the original initialization routine using the existing Unicorn environment.
Distinct targets may share tails/labels: they are not a function denominator.
"""
import argparse
import collections
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path

from original_inventory import OriginalPE

ROOT = Path(__file__).resolve().parents[1]


def decode_dispatch(pe):
    base = struct.unpack('<I', pe.read(0x529020, 4))[0]
    cursor = 0x529024
    targets = []
    runs = 0
    while True:
        value = struct.unpack('<I', pe.read(cursor, 4))[0]
        cursor += 4
        count = value >> 24
        if count == 0:
            count = struct.unpack('<H', pe.read(cursor, 2))[0]
            cursor += 2
        if count == 0:
            break
        target = base + (value & 0xffffff)
        if not pe.is_code(target) or len(targets)+count > 65536:
            raise ValueError('Invalid decoded A68K table')
        targets.extend([target]*count)
        runs += 1
    assert len(targets) == 65536 and cursor == 0x531216
    return base, cursor, runs, targets


def emit_dispatch(pe, destination):
    """Embed emulator-owned RLE data, never ROM-derived code or host pointers."""
    _, end, _, _ = decode_dispatch(pe)
    data = pe.read(0x529020, end-0x529020)
    lines = ['/* Original ElSemi 1.1a A68K dispatch RLE, 00529020..00531216.',
             ' * Reproduce with tools/a68k_inventory.py --emit-dispatch.',
             ' * Original EXE SHA-256: '+hashlib.sha256(pe.data).hexdigest(),
             ' * Data SHA-256: '+hashlib.sha256(data).hexdigest(),
             ' * Emulator metadata only; no ROM input. */']
    lines += ['    '+','.join(f'0x{v:02x}' for v in data[i:i+16])+','
              for i in range(0,len(data),16)]
    destination.write_text('\n'.join(lines)+'\n')


def inventory(exe, verify=False):
    pe = OriginalPE(exe)
    base, cursor, runs, targets = decode_dispatch(pe)
    table = struct.pack('<65536I', *targets)
    original_executions = 0
    if verify:
        sys.path.insert(0, str(ROOT/'port/tgpx4/test'))
        from difftest_lifecycle import load_original, SP, STOP
        from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EDX,
                                      UC_X86_REG_ESP, UC_X86_REG_EIP)
        uc = load_original(exe)
        uc.mem_write(0x531216, bytes(len(table)))
        uc.mem_write(SP, struct.pack('<I', STOP))
        uc.reg_write(UC_X86_REG_ESP, SP)
        uc.reg_write(UC_X86_REG_EAX, 0)
        uc.reg_write(UC_X86_REG_EDX, 0)
        uc.emu_start(0x462ae0, STOP, count=1000000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
        assert bytes(uc.mem_read(0x531216, len(table))) == table
        original_executions = 1
    exported = {int(r['address'], 16) for r in csv.DictReader(
        (ROOT/'src/functions.tsv').open(), delimiter='\t')}
    counts = collections.Counter(targets)
    return dict(schema_version=1, original_sha256=hashlib.sha256(pe.data).hexdigest(),
        initializer='00462ae0', packed_start='00529024', packed_end_exclusive=f'{cursor:08x}',
        dispatch_destination='00531216', relative_base=f'{base:08x}',
        packed_runs=runs, opcode_entries=len(targets), distinct_targets=len(counts),
        targets_present_in_function_export=len(counts.keys() & exported),
        targets_absent_from_function_export=len(counts.keys() - exported),
        decoded_table_sha256=hashlib.sha256(table).hexdigest(),
        original_initializer_executions=original_executions,
        compared_opcode_entries=len(targets) if verify else 0,
        targets=[dict(address=f'{at:08x}', opcode_count=count, exported_entry=at in exported)
                 for at, count in sorted(counts.items())],
        limits=['This recovers dispatch identity, not opcode semantics, timing or CPU equivalence.',
                'Shared labels/tails and invalid-opcode dispatch prevent a function-count interpretation.',
                'Musashi remains unchanged; replacement needs a separate implementation decision.'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('--verify-original', action='store_true')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--emit-dispatch', type=Path)
    args = ap.parse_args()
    report = inventory(args.exe, args.verify_original)
    if args.emit_dispatch:
        emit_dispatch(OriginalPE(args.exe), args.emit_dispatch)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('targets', 'limits')}, indent=2))
