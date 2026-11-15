#!/usr/bin/env python3
"""Audit original Save State registrations with synthetic memory, without ROMs.

Executes unchanged registration fragments and the raw-entry load loop. Only
host allocation/list construction/INI and ZIP I/O are replaced by fixtures.
This is not a Windows frontend or audible-continuity test.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from scsp_dsp_compare import load_original, SP, STOP
from original_inventory import OriginalPE
from a68k_boundary_compare import CTX, DATA, READ
from scsp_control_compare import CHIP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX,
    UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI,
    UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP)


def audit(exe):
    pe = OriginalPE(exe)
    u = load_original(exe)
    u.mem_map(0, 0x1000)  # synthetic SEH chain
    u.mem_map(0x72000000, 0x300000)
    u.mem_map(0x73000000, 0x10000)
    u.mem_map(0x74000000, 0x2000000)
    board, owner, head = 0x72000000, 0x73000000, 0x73001000
    next_alloc, next_node = 0x74000000, 0x73002000
    allocations, rows, reads = {}, [], []

    def put(at, *values):
        u.mem_write(at, struct.pack('<'+'I'*len(values), *values))

    def get(at, n=1):
        return struct.unpack('<'+'I'*n, u.mem_read(at, 4*n))

    def ret(value=0, pop=0):
        sp = u.reg_read(UC_X86_REG_ESP)
        u.reg_write(UC_X86_REG_EAX, value)
        u.reg_write(UC_X86_REG_EIP, get(sp)[0])
        u.reg_write(UC_X86_REG_ESP, sp+4+pop)

    def record():
        desc = bytes(u.mem_read(u.reg_read(UC_X86_REG_ESI), 24))
        kind, name, ptr, size, load, save = struct.unpack('<6I', desc)
        label = bytes(u.mem_read(name, 32)).split(b'\0')[0].decode()
        row = dict(name=label, kind=kind & 255, size=size,
                   pointer=f'{ptr:08x}')
        if row['kind']:
            row.update(load=f'{load:08x}', save=f'{save:08x}')
        else:
            row['allocation_bytes'] = allocations[ptr]
        rows.append(row)
        return desc

    def hook(mu, address, size, data):
        nonlocal next_alloc, next_node
        if address == 0x4cd495:  # GetPrivateProfileIntA(default=0)
            mu.reg_write(UC_X86_REG_ESP, mu.reg_read(UC_X86_REG_ESP)+16)
            mu.reg_write(UC_X86_REG_EAX, 0)
            mu.reg_write(UC_X86_REG_EIP, 0x4cd49b)
        elif address == 0x4fc340:
            n = mu.reg_read(UC_X86_REG_EAX)
            at = next_alloc; next_alloc += (n+4095) & ~4095
            assert next_alloc <= 0x76000000
            allocations[at] = n
            ret(at)
        elif address == 0x401050:
            desc = record()
            sp = mu.reg_read(UC_X86_REG_ESP)
            put(next_node, *get(sp+4, 2))
            mu.mem_write(next_node+8, desc)
            ret(next_node, 8); next_node += 32
        elif address == 0x4ebe20:  # ZIP member lookup succeeds
            ret(0)
        elif address == 0x4ebd70:  # ZIP read supplies deterministic bytes
            ptr, n = get(mu.reg_read(UC_X86_REG_ESP)+4, 2)
            reads.append(dict(pointer=f'{ptr:08x}', size=n))
            mu.mem_write(ptr, bytes(sound_member) if ptr == scsp else b'\x3c'*n)
            ret(1, 8)

    u.hook_add(UC_HOOK_CODE, hook)
    put(board+0x18, owner); put(owner+0x10c, head, 0)
    put(head, head, head)

    def run(start, end, regs, count=100000):
        u.reg_write(UC_X86_REG_ESP, SP)
        for reg, value in regs.items():
            u.reg_write(reg, value)
        u.emu_start(start, end, count=count)
        assert u.reg_read(UC_X86_REG_EIP) == end

    run(0x4cd450, 0x4cdb71, {UC_X86_REG_ECX: board})
    assert len(rows) == 15 and rows[-1]['name'] == 'M2SCSP'
    # CPU registration prefixes: stop before insertion and decode the exact
    # descriptor populated by the original instructions, not the decompiler.
    for start, end, regs in (
        (0x4a9a80, 0x4a9ad0, {}),
        (0x4b7940, 0x4b799b, {UC_X86_REG_EAX: owner+0x10c}),
        (0x4c0230, 0x4c027a, {UC_X86_REG_EBX: owner+0x10c}),
        (0x4c4ff6, 0x4c502a, {UC_X86_REG_EDX: owner+0x10c,
                              UC_X86_REG_ESI: board}),
    ):
        put(SP, STOP, owner+0x10c)
        run(start, end, regs)
        record()
    assert [r['name'] for r in rows[-4:]] == ['TGP', 'TGPX4', 'SHARC', 'I960']

    # The native raw-entry load traversal restores exactly the registered
    # ranges. Seed sound RAM, DSP context and its separate private RAM.
    scsp = int(rows[14]['pointer'], 16)
    dsp_ram = next_alloc
    u.mem_write(scsp, b'\xa5'*0x100000)
    u.mem_write(dsp_ram, b'\x69'*0x100000)
    context = bytearray(b'\x96'*0x7ec)
    struct.pack_into('<I', context, 0, dsp_ram)
    u.mem_write(0x109bd24, bytes(context))
    # Lower sound RAM carries program bytes in the raw member. Live CPU and
    # board state describe the instant of loading and are deliberately distinct.
    sound_member = bytearray([0x3c]) * 0x10000
    program = (0x3039, 0x10, 0x404, 0x3239, 0x10, 0x420, 0x60fe)
    struct.pack_into('<7H', sound_member, 0x140, *program)
    put(SP, STOP)
    run(0x462ae0, STOP, {}, count=1000000)
    put(0x10ed9ac, scsp)
    put(READ, scsp, 0, 0, 0)
    put(DATA+0x100*16, 0, 0x4ae870, 0x4ae800, 0x4ab220)
    put(0x572a8c, 0x4b3220)  # DATA word callback (checked below through guest reads).
    put(CTX, *([0]*33))
    put(CTX+68, 0x27)
    put(CTX+80, 0x140, 5)
    put(0x5728bc, CHIP)
    u.mem_write(CHIP+0x1e, struct.pack('<HH', 0x40, 0x40))
    put(0x572890, 3, 0, 5)
    u.mem_write(0x10ed9d8, bytes([1, 0]))
    u.mem_write(0x1078799, bytes([1]))
    u.mem_write(0x10c35b0, bytes([0x59]))
    put(0x10bdf44, 0x10000, 0x3481, 0x1740)
    u.mem_write(0x10bdf40, bytes([1,0,0]))
    put(0x10f01d0, 0x71)
    regions = dict(cpu=(CTX, 128), timers=(0x10bdf40, 16), phase=(0x10f01d0, 4),
                   midi_ring=(0x10c35b0, 128), midi_indices=(0x10ed9d8, 2),
                   midi_count=(0x1078799, 1), enables_and_pending=(CHIP+0x1e, 4))
    def exchange_state():
        return {key:bytes(u.mem_read(at, size)) for key, (at, size) in regions.items()}
    live = exchange_state()
    put(SP+0x108, owner+0x10c)
    run(0x4f7483, 0x4f751b, {UC_X86_REG_EDI: get(head)[0],
                             UC_X86_REG_EBP: SP+0x100})
    assert len(reads) == 15
    checks = dict(
        scsp_first_64k_restored=bytes(u.mem_read(scsp, 0x10000)) == sound_member,
        scsp_remaining_960k_untouched=bytes(u.mem_read(scsp+0x10000, 0xf0000)) == b'\xa5'*0xf0000,
        dsp_context_untouched=bytes(u.mem_read(0x109bd24, 0x7ec)) == bytes(context),
        dsp_private_ram_untouched=bytes(u.mem_read(dsp_ram, 0x100000)) == b'\x69'*0x100000)
    checks['live_exchange_survives_raw_load'] = exchange_state() == live
    # Run the actual post-load vtable target with empty renderer resource
    # lists and room for its reset vector. No GPU or graphics API stub needed.
    for at, node in ((0x10f00f8, owner+0x4000), (0x10f017c, owner+0x4010)):
        put(at, node)
        put(node, node, node)
    put(0x10f0188, owner+0x4100, owner+0x4100, owner+0x4180)
    post_load = get(0x51bbcc+0x30)[0]
    assert post_load == 0x4caf00
    put(SP, STOP)
    run(post_load, STOP, {UC_X86_REG_ECX: board})
    checks['live_exchange_survives_post_load'] = exchange_state() == live
    assert get(0x573320, 2) == (1, 1)
    # Run the restored instructions at the surviving PC. Level five is
    # masked in SR so both reads complete before any interrupt can intervene.
    put(SP, STOP)
    put(0x10ed9b0, 100)
    run(0x462b1c, STOP, {})
    checks['guest_reads_live_command_and_timer'] = get(CTX, 2) == (0x59, 0x40) and get(CTX+80)[0] == 0x14c
    assert all(checks.values())
    return dict(original_sha256=hashlib.sha256(pe.data).hexdigest(),
                registrations=rows, raw_load_reads=reads, checks=checks,
                limits=['Synthetic native fragments, no ROMs or Windows frontend.',
                        'CPU callback descriptors captured; callbacks not invoked by this probe.',
                        'Post-load hook executed with empty renderer resource lists; native guest resume tested with masked IRQ.'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = audit(args.exe)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['checks']))
