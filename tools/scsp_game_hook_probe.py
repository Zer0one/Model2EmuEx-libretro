#!/usr/bin/env python3
"""Watch the SCSP chip-count flag while running the original per-game setup hooks."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ECX

from a68k_boundary_compare import Oracle

GAME_TABLE = 0x10ed4b0
MODE = 0x10ed99e
DUAL = 0x10ed9da
MACHINE = 0x73000000
CACHE = 0x74000000


def probe(exe, catalog):
    o = Oracle(exe)
    data = catalog.read_bytes()

    def word(address):
        return struct.unpack_from('<I', data, address - 0x528000)[0]

    games = {}
    for index in range(128):
        entry = GAME_TABLE + index * 8
        name, record = word(entry), word(entry + 4)
        if not name:
            break
        shortname = o.pe.read(name, 64).split(b'\0')[0].decode('ascii')
        target = word(record + 0x3c)
        if target and not o.pe.is_code(target):
            raise ValueError(f'Invalid setup pointer for {shortname}')
        games.setdefault(target, []).append(shortname)
    else:
        raise ValueError('Missing game table terminator')
    if index != 67 or sum(map(len, games.values())) != 67:
        raise ValueError('Incomplete game table')

    o.u.mem_map(MACHINE, 0x204000)
    o.u.mem_map(CACHE, 0x600000)
    stores = []
    def observe(u, kind, address, size, value, data):
        if address <= DUAL < address + size:
            stores.append(address)
    o.u.hook_add(UC_HOOK_MEM_WRITE, observe, begin=DUAL-15, end=DUAL)
    results = []
    for target, names in sorted(games.items()):
        if not target:
            continue
        for initial in (0, 1):
            # Exercise both paths of the native configuration test at 004c7e50.
            for config in (0, 1):
                o.u.mem_write(MACHINE, bytes(0x204000))
                o.u.mem_write(CACHE, bytes(0x600000))
                o.put(0x10ed940, CACHE)
                o.put(MACHINE + 0x40 + 0x200028, CACHE)
                o.u.mem_write(0x10ed8b8, bytes([config]))
                o.u.mem_write(DUAL, bytes([initial]))
                o.u.mem_write(MODE, bytes(1))
                o.run(target, {UC_X86_REG_ECX: MACHINE})
                if stores or o.u.mem_read(DUAL, 1)[0] != initial:
                    raise ValueError(f'Dual-chip flag written by {target:08x}')
                if o.u.mem_read(MODE, 1)[0] != (target == 0x4c6710):
                    raise ValueError(f'Unexpected mixer selection at {target:08x}')
        results.append(dict(entry=f'{target:08x}', games=names))
    return dict(original_sha256=hashlib.sha256(o.pe.data).hexdigest(),
                catalog_memory_sha256=hashlib.sha256(data).hexdigest(),
                records=index, no_setup_hook=games[0], hooks=results,
                calls=len(results)*4, flag_stores=len(stores))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('catalog_memory', type=Path, help='Existing dump_games.py .mem result')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = probe(args.exe, args.catalog_memory)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(report['records'], 'records;', report['calls'], 'setup calls;', report['flag_stores'], 'flag stores')
