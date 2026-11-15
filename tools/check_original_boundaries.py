#!/usr/bin/env python3
"""Execute focused original-code boundary probes using the existing Unicorn setup.

Synthetic RAM only. Results establish address arithmetic, not whether games
reach those paths or how the real Windows allocator arranges adjacent memory.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

from original_inventory import OriginalPE

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'port/tgpx4/test'))
from difftest_lifecycle import load_original, SP, STOP
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                              UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)


def run(exe):
    pe = OriginalPE(exe)
    uc = load_original(exe)

    def word(at, value):
        uc.mem_write(at, struct.pack('<I', value))

    def call(entry, ecx=0, edx=0):
        word(SP, STOP)
        for reg, value in ((UC_X86_REG_EAX, 0), (UC_X86_REG_ECX, ecx),
                           (UC_X86_REG_EDX, edx), (UC_X86_REG_ESP, SP),
                           (UC_X86_REG_EFLAGS, 2)):
            uc.reg_write(reg, value)
        uc.emu_start(entry, STOP, count=1000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP

    # Anchor dispatch and original body, not just a similar instruction sequence.
    geometry_target = struct.unpack('<I', pe.read(0x573340+13*4, 4))[0]
    assert geometry_target == 0x4b95a0
    assert pe.read(geometry_target, 8) == bytes.fromhex('83051830000108c3')
    geometry = []
    for pointer in (0x72000000, 0x72000004, 0xfffffff8):
        word(0x1003018, pointer)
        call(geometry_target)
        actual = struct.unpack('<I', uc.mem_read(0x1003018, 4))[0]
        assert actual == (pointer+8) & 0xffffffff
        geometry.append(dict(before=hex(pointer), after=hex(actual)))

    # Validate representative boundaries against executed original code; enumerate
    # the complete guest-writable 16-bit selector domain separately, arithmetically.
    reads = []
    def capture(_, access, address, size, value, opaque):
        if 0x574d28 <= address < 0x590000:
            reads.append((address, size))
    hook = uc.hook_add(UC_HOOK_MEM_READ, capture)
    protection = []
    for selector in (0, 1, 5, 6, 11, 12, 95, 96, 65534, 65535):
        word(0x10ed90c, selector)
        uc.mem_write(0x5aa770, bytes(256))
        reads.clear()
        call(0x4c73d0, 0x1d9000c, 0x0010)
        source = 0x574d28+(selector*2//12)*8
        expected = pe.read(source, 128)
        assert bytes(uc.mem_read(0x5aa772, 128)) == expected
        assert reads and min(a for a, _ in reads) == source
        assert max(a+n for a, n in reads) == source+128
        protection.append(dict(selector=selector, source=hex(source), end_exclusive=hex(source+128),
            within_recovered_table=source+128 <= 0x574da8,
            response_sha256=hashlib.sha256(expected).hexdigest()))
    uc.hook_del(hook)
    starts = [0x574d28+(selector*2//12)*8 for selector in range(65536)]
    covered = [i for i, at in enumerate(starts) if at+128 <= 0x574da8]
    assert covered == list(range(6))
    # Ensure all calculated source windows actually exist in this pinned file.
    for at in set(starts):
        assert len(pe.read(at, 128)) == 128

    shared = 0x72000000
    uc.mem_map(shared, 0x80000)
    word(0x5aa700, shared)
    invalid = []
    def unmapped(_, access, address, size, value, opaque):
        invalid.append(dict(address=hex(address), size=size))
        return False
    hook = uc.hook_add(UC_HOOK_MEM_INVALID, unmapped)
    shared_cases = []
    for entry, address in ((0x4c5a70, 0x400000), (0x4c5a70, 0x41ffff),
                           (0x4c5a70, 0x420000), (0x4c5a70, 0x7fffff),
                           (0x4c5a90, 0x3fffff), (0x4c5a90, 0x400000),
                           (0x4c5a90, 0x41ffff), (0x4c5a90, 0x7fffff)):
        writing = entry == 0x4c5a70
        target = (shared+(address-(0x400000 if writing else 0))*4
                  if 0x400000 <= address < 0x800000 else None)
        inside = target is None or shared <= target and target+4 <= shared+0x80000
        invalid.clear()
        try:
            call(entry, address, 0x12345678)
            assert inside
            if target is not None:
                assert struct.unpack('<I', uc.mem_read(target, 4))[0] == 0x12345678
            else:
                assert uc.reg_read(UC_X86_REG_EAX) == 0
        except UcError:
            assert not inside and invalid == [dict(address=hex(target), size=4)]
        shared_cases.append(dict(entry=hex(entry), guest_address=hex(address),
            target=hex(target) if target is not None else None, inside_synthetic_allocation=inside))
    uc.hook_del(hook)
    return dict(status='passed', original_sha256=hashlib.sha256(pe.data).hexdigest(),
        geometry_0d=dict(dispatch_target=hex(geometry_target), cases=geometry,
                         conclusion='Original advances the list pointer by eight bytes; port has equivalent normal-list behavior.'),
        protection=dict(original_executions=len(protection), original_cases=protection,
            selector_domain=65536, arithmetically_covered_selectors=covered,
            unique_source_windows=len(set(starts)), source_min=hex(min(starts)),
            source_end_exclusive=hex(max(starts)+128),
            conclusion='Selectors 6..65535 read beyond the recovered table, into file-backed .data; reachability by games is unproven.'),
        shared_memory=dict(original_executions=len(shared_cases), cases=shared_cases,
            allocation_bytes=0x80000, valid_write_guest_range=['0x400000', '0x41ffff'],
            read_guest_range=['0x400000', '0x7fffff'], read_byte_offsets=['0x1000000', '0x1fffffc'],
            conclusion='Every read in this shared window is beyond the 512 KiB buffer; writes also escape above 0x41ffff.'),
        limits=['No game or Windows heap allocation was executed.',
                'Unicorn faults reflect a deliberately bounded synthetic allocation, not proof that Windows always faults.',
                'No expanded RAM, fallback bytes, renderer or audio changes are introduced.'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    report = run(args.exe)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key in ('status', 'original_sha256', 'limits')}, indent=2))
