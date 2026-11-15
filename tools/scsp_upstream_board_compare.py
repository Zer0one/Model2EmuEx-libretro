#!/usr/bin/env python3
"""Compare a 58 Hz core PCM capture to the pinned standalone board with the same i960 command trace."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile

from scsp_a68k_board_compare import ROOT, sound_regions


def compare(args):
    revision = subprocess.check_output(['git', '-C', args.standalone, 'rev-parse', 'HEAD'], text=True).strip()
    if revision != '25d82be56f339c754cc566f771ca9ffb90b69289':
        raise ValueError('Unexpected standalone revision')
    subprocess.run(['git', '-C', args.standalone, 'diff', '--quiet', 'HEAD', '--', 'port'], check=True)
    port = args.standalone.resolve() / 'port'
    commands = [bytearray() for _ in range(args.frames)]
    last_line = 0
    end_line = args.frames * 210
    for line in args.trace.read_text().splitlines():
        if line.startswith('A68K_'):
            kind, scanline, value = line.split()
            position = int(scanline)
            if position < last_line or position > end_line:
                break
            last_line = position
            if kind == 'A68K_COMMAND':
                if position < 1:
                    raise ValueError('Invalid command scanline')
                commands[(position - 1) // 210].append(int(value))
    if not any(commands):
        raise ValueError('Missing cold-boot command trace')
    data = bytearray()
    names = {5: 'audiocpu', 6: 'samples'}
    aliases = {}
    if args.model1:
        names = {5: 'M1AUDIO_CPU_REGION', 6: 'M1AUDIO_MPCM1_REGION'}
        aliases = {'M1AUDIO_MPCM2_REGION': names[6]}
    regions = sound_regions(args.archive, names, aliases)
    for name in names.values():
        data.extend(struct.pack('<I', len(regions[name])))
        data.extend(regions[name])
    for frame in commands:
        data.append(len(frame))
        data.extend(frame)
    with tempfile.TemporaryDirectory() as directory:
        build = Path(directory)
        # The standalone Makefile can build its unmodified objects outside the checkout.
        objects = ('snd/m2snd', 'snd/scsp', 'snd/multipcm', 'snd/ym3438', 'ymfm/ymfm_opn',
                   'ymfm/ymfm_adpcm', 'ymfm/ymfm_ssg', 'm68k/m68kcpu', 'm68k/m68kops',
                   'm68k/softfloat/softfloat')
        paths = [build / (o + '.o') for o in objects]
        subprocess.run(['make', '-s', '-j4', '-C', port, f'BUILD={build}', *paths], check=True)
        subprocess.run(['cc', '-I', port, '-c', ROOT/'port/snd/test/upstream_board_replay.c',
                        '-o', build/'replay.o'], check=True)
        subprocess.run(['c++', build/'replay.o', *paths, '-lm', '-o', build/'replay'], check=True)
        reference = subprocess.check_output([build/'replay', '0' if args.model1 else '1'], input=data)
    actual = args.pcm.read_bytes()
    if not any(reference) or reference != actual:
        first = next((i // 4 for i, (a,b) in enumerate(zip(reference,actual)) if a != b), None)
        raise ValueError(f'Upstream PCM mismatch: first divergent stereo frame {first}, sizes {len(reference)}/{len(actual)}')
    print(f'{sum(map(len,commands))} commands, {len(reference)//4} identical stereo frames, '
          f'SHA-256 {hashlib.sha256(reference).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('standalone', 'archive', 'trace', 'pcm'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--frames', type=int, default=420)
    parser.add_argument('--model1', action='store_true', help='Use the primary Model 1-style audio board')
    compare(parser.parse_args())
