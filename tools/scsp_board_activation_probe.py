#!/usr/bin/env python3
"""Check the original SCSP board installer for every distinct catalog configuration."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_FPCW
from a68k_boundary_compare import Oracle
from original_inventory import OriginalPE
from scsp_control_compare import CHIP
from scsp_game_hook_probe import DUAL, GAME_TABLE, MODE


def configurations(exe, prefix):
    pe = OriginalPE(exe)
    images = [(base, prefix.with_suffix(suffix).read_bytes()) for base, suffix in
              [(0x528000, '.mem'), (0x20000000, '.heap')]]
    if images[0][1][DUAL - images[0][0]] != 0:
        raise ValueError('Chip-count flag already set in the initialized catalog')

    def word(address):
        for base, image in images:
            offset = address - base
            if 0 <= offset <= len(image) - 4:
                return struct.unpack_from('<I', image, offset)[0]
        raise ValueError(f'Outside the registered catalog images: {address:08x}')

    groups = defaultdict(list)
    for index in range(68):
        entry = GAME_TABLE + index * 8
        name = word(entry)
        if not name:
            if index != 67:
                raise ValueError('Unexpected catalog length')
            break
        record = word(entry + 4)
        head, count = word(record + 0x30), word(record + 0x34)
        node = word(head)
        options = {}
        for _ in range(count):
            if node == head:
                raise ValueError('Short ROM descriptor list')
            if word(node + 8) == 4:
                # The loader reads the low byte of the type-4 option index.
                options[word(node + 12) & 255] = word(node + 16)
            node = word(node)
        if node != head:
            raise ValueError('Unterminated ROM descriptor list')
        groups[options.get(0, 0), options.get(1, 0)].append(
            pe.read(name, 64).split(b'\0')[0].decode('ascii'))
    else:
        raise ValueError('Missing catalog terminator')
    return groups


def check_installer(exe, board_type, digital, initial):
    o = Oracle(exe)
    o.u.hook_del(o.code_hook)
    machine, device, output = 0x73000000, 0x73400000, 0x73500000
    voices, program, samples = 0x74000000, 0x74200000, 0x74400000
    heap, heap_size = 0x75000000, 0x200000
    for base, size in ((machine, 0x204000), (device, 0x1000), (output, 0xb0000),
                       (voices, 0x100000), (program, 0x80000), (samples, 0x800000),
                       (heap, heap_size)):
        o.u.mem_map(base, size)
    o.put(machine + 4, device)
    o.put(machine + 0x14, output)
    o.put(machine + 0x3c, board_type)
    o.put(machine + 0x20389c, voices)
    o.put(device + 0x28, program, 0x80000, samples, 0x800000)
    o.put(device + 0x104, digital)
    o.put(output + 0xac4a8, 44100)
    o.put(0x10f1fec, 1)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    thread = 0x72018000
    o.put(thread + 0x14, 1)
    o.u.mem_write(DUAL, bytes([initial]))
    o.u.mem_write(MODE, b'\x01')
    o.u.mem_write(0x107878b, b'\xff')  # Distinguish an absent DSB from a type store.

    allocations = []
    def malloc(u, at, size, data):
        amount = o.get(u.reg_read(UC_X86_REG_ESP) + 4)[0]
        start = allocations[-1][0] + allocations[-1][1] if allocations else heap
        start = (start + 15) & ~15
        assert amount and start + amount <= heap + heap_size
        allocations.append((start, amount))
        o.ret(start)

    channels = []
    def stream(u, at, size, data):
        # Only the Windows stream constructor is replaced. Native board code
        # supplies the two pan values and halves the first return value.
        sp = u.reg_read(UC_X86_REG_ESP)
        channels.append(o.get(sp + 4)[0])
        o.ret(1520)
        u.reg_write(UC_X86_REG_ESP, sp + 8)  # ret 4

    secondary = CHIP + 0x1a2c
    watched = dict.fromkeys((DUAL, MODE, CHIP + 0x1234, CHIP + 0x123c,
                             secondary + 0x1234, secondary + 0x123c), 0)
    def write(u, kind, address, width, value, data):
        for target in watched:
            length = 1 if target in (DUAL, MODE) else 4
            if address < target + length and target < address + width:
                watched[target] += 1

    # No ROM or host audio device is required to install these bindings.
    for at, fn in ((0x48d12f, malloc), (0x4980b1, lambda *_: o.ret(thread)),
                   (0x4eecf0, stream)):
        o.u.hook_add(UC_HOOK_CODE, fn, begin=at, end=at)
    for first, last in ((MODE, DUAL), (CHIP + 0x1234, CHIP + 0x123f),
                        (secondary + 0x1234, secondary + 0x123f)):
        o.u.hook_add(UC_HOOK_MEM_WRITE, write, begin=first - 15, end=last)
    o.run(0x4ccbe0, {UC_X86_REG_ECX: machine}, count=12000000)

    assert not watched[DUAL] and o.u.mem_read(DUAL, 1)[0] == initial
    assert o.u.mem_read(MODE, 1)[0] == 0 and watched[MODE]
    assert o.get(CHIP + 0x1234)[0] == voices and watched[CHIP + 0x1234]
    assert o.get(CHIP + 0x123c)[0] == allocations[-1][0] and allocations[-1][1] == 0x100000
    assert not watched[secondary + 0x1234] and not watched[secondary + 0x123c]
    assert o.get(secondary + 0x1234)[0] == o.get(secondary + 0x123c)[0] == 0
    assert channels == [0, 255] and o.get(machine + 0x28)[0] == 760
    assert o.u.mem_read(0x107878b, 1)[0] == (digital or 255)
    return dict(initial_flag=initial, final_flag=o.u.mem_read(DUAL, 1)[0],
                flag_stores=watched[DUAL], primary_voice_stores=watched[CHIP + 0x1234],
                primary_dsp_stores=watched[CHIP + 0x123c],
                secondary_voice_stores=watched[secondary + 0x1234],
                secondary_dsp_stores=watched[secondary + 0x123c])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('catalog_prefix', type=Path, help='Prefix of dump_games.py .mem and .heap')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    groups = configurations(args.exe, args.catalog_prefix)
    report = dict(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                  catalog_sha256={suffix: hashlib.sha256(args.catalog_prefix.with_suffix(
                      suffix).read_bytes()).hexdigest() for suffix in ('.mem', '.heap')},
                  flag_after_catalog_initialization=0,
                  configurations=[])
    for (board_type, digital), names in sorted(groups.items()):
        cases = [check_installer(args.exe, board_type, digital, initial)
                 for initial in (0, 1)] if board_type else []
        report['configurations'].append(dict(board_type=board_type, dsb=digital,
                                             records=names, scsp_installer_cases=cases))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
