#!/usr/bin/env python3
"""Audit direct i960 calls to the protection command routine in the USA Model 2C set."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile

from i960dis import dis


CATALOG = Path(__file__).resolve().parents[1] / 'src/libretro/data/mame_model2_catalog.json'
START, LAST = 0xb67b0, 0xb6850
PORTS = {0x1d90008, 0x1d9000c}


def load_program(archive):
    games = json.loads(CATALOG.read_text())['games']
    chips = [f for g in games if g['name'] == 'dynamcopc'
             for f in g['mame_files'] if f['region'] == 'maincpu']
    image = bytearray(0x200000)
    with ZipFile(archive) as roms:
        for chip in chips:
            entry = roms.getinfo(chip['name'])
            if (chip['load'] != 'ROM_LOAD32_WORD' or entry.CRC != chip['crc']
                    or entry.file_size != chip['size']):
                raise ValueError(f"Unexpected program chip: {entry.filename}")
            block = roms.read(entry)
            offset = chip['offset']
            end = offset + len(block) * 2
            image[offset:end:4] = block[::2]
            image[offset+1:end:4] = block[1::2]
    digest = sha256(image).hexdigest()
    if digest != 'c2c8415569a114223e46c8fdd3310a2714c11d1c02a1cef698547a8e94c60545':
        raise ValueError('Unrecognized USA Model 2C i960 image')
    return image, digest


def sites(image):
    calls, stores, other = [], [], []
    for pc in range(0, len(image), 4):
        word = unpack_from('<I', image, pc)[0]
        op = word >> 24
        if START <= word <= LAST:
            other.append((pc, 'literal pointer', word))
        if op in (8, 9, 11) or 0x10 <= op <= 0x17 or 0x30 <= op <= 0x3f:
            sign = 0x1000 if op >= 0x30 else 0x800000
            displacement = ((word & (2 * sign - 4)) ^ sign) - sign
            target = (pc + displacement) & 0xffffffff
            if not START <= pc <= LAST and START <= target <= LAST:
                if op == 9 and target == START:
                    calls.append(pc)
                else:
                    other.append((pc, 'relative transfer', target))
        elif op in (0x84, 0x85, 0x86, 0x8a, 0x8c, 0xca) and pc + 8 <= len(image):
            mode = (word >> 10) & 15
            if mode not in (5, 12):
                continue
            target = unpack_from('<I', image, pc + 4)[0]
            if mode == 5:
                # ea_ip_disp in port/i960/i960.c uses the displacement word + 8.
                target = (pc + 12 + target) & 0xffffffff
            if START <= target <= LAST:
                other.append((pc, 'memory-format reference', target))
            if target in PORTS:
                if op == 0x8a:
                    stores.append((pc, target))
                else:
                    other.append((pc, 'other port reference', target))
    return calls, stores, other


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    image, digest = load_program(args.archive)
    calls, stores, other = sites(image)
    if (calls != [0x67224, 0x672d8] or stores != [(0xb67c4, 0x1d90008), (0xb67cc, 0x1d9000c)]
            or other):
        raise ValueError(f'Unexpected reference inventory: {calls}, {stores}, {other}')
    print(f'USA Model 2C i960 SHA-256 {digest}')
    # Verify the straight-line argument setup and the intervening local
    # register operations. Neither caller reloads the selector before CALL.
    for command_site, call, command in zip((0x67208, 0x672c8), calls, (0x1326, 0x7700)):
        pc = command_site
        expected = [f'lda {command:#x},g1', 'mov 20,0,g2', 'mov 0,0,g3']
        if call == calls[0]:
            expected += ['lda 0xcd1c0,r6', 'addo r6,15,r7']
        for instruction in expected:
            length, actual = dis(image, 0, pc)
            if actual != instruction:
                raise ValueError(f'Unexpected argument setup at {pc:08x}: {actual}')
            pc += length
        if pc != call:
            raise ValueError('Unreviewed instructions before call')
        print(f'Call {call:08x}: command {command:#06x}, selector argument 0, length argument 20')
    print('Two direct calls; one word-store site per port. Computed aliases are outside this scan.')


if __name__ == '__main__':
    main()
