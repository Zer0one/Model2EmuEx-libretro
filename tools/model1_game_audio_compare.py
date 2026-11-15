#!/usr/bin/env python3
"""Compare a primary Model 1 audio board with native-timing Libretro PCM and i960 commands."""
import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path

from model1_board_compare import AUDIO_RAM, BOARD, OUTPUT, initialize
from model1_mix_compare import regions
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP


def replay(exe, archive, trace, pcm, frames, windows_block=False, capture_fixed=False):
    events = defaultdict(list)
    recorded_irqs = []
    for row in trace.read_text().splitlines():
        if not row.startswith(('A68K_COMMAND ', 'A68K_IRQ ')):
            continue
        kind, at, value = row.split()
        at = int(at)
        if at > 210*frames:
            break
        if kind == 'A68K_IRQ':
            recorded_irqs.append((at, int(value)))
        else:
            events[at].append(int(value))
    blobs = regions(archive)
    program = blobs['M1AUDIO_CPU_REGION']
    o = initialize(exe, blobs['M1AUDIO_MPCM1_REGION'], program)
    o.u.mem_write(AUDIO_RAM, bytes(program[:8]))
    o.run(0x4b33a0)
    irqs = []
    def ack(cpu, pc, size, user):
        irqs.append((scanline, o.get(cpu.reg_read(UC_X86_REG_ESP)+4)[0]))
    o.u.hook_add(UC_HOOK_CODE, ack, begin=0x4b3090, end=0x4b3090)
    o.u.ctl_flush_tb()
    debt = 0.0
    scanline = total = active = captured_frames = differences = 0
    first_difference = None
    digest = hashlib.sha256()
    captured_digest = hashlib.sha256()
    with pcm.open('rb') as captured:
        for frame in range(frames):
            debt += 44100/58
            captured_width = int(debt)
            debt -= captured_width
            if capture_fixed:
                captured_width = 760
            width = 760 if windows_block else captured_width
            o.put(0x10e3fe8, width)
            o.put(0x1092dd0, width)
            o.run(0x4cc4a0, {UC_X86_REG_ECX: BOARD}, count=20000000)
            channels = [struct.unpack('<'+'h'*width, o.u.mem_read(OUTPUT+offset, 2*width))
                        for offset in (0x68, 0x2b178)]
            block = b''.join(struct.pack('<hh', *pair) for pair in zip(*channels))
            full_block = captured.read(4*captured_width)
            if len(full_block) != 4*captured_width:
                raise ValueError(('incomplete native-timing capture', frame))
            captured_frames += captured_width
            got = full_block[:4*width]
            if got != block:
                for i,(a,b) in enumerate(zip(struct.iter_unpack('<hh', block),
                                             struct.iter_unpack('<hh', got))):
                    if a != b:
                        if first_difference is None:
                            first_difference = dict(frame=frame+1, sample=i, original=a, core=b)
                        differences += 1
                if not windows_block or capture_fixed:
                    raise ValueError(('PCM', first_difference, 'IRQs so far', len(irqs)))
            digest.update(block)
            captured_digest.update(got)
            total += width
            active += sum(bool(l or r) for l, r in zip(*channels))
            next_width = 760 if windows_block else int(debt+44100/58)
            o.put(0x10e3fe8, next_width)
            for _ in range(210):
                scanline += 1
                for value in events.get(scanline, ()):
                    o.run(0x4c8660, {UC_X86_REG_ECX: value})
                o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=200000)
    if irqs != recorded_irqs:
        raise ValueError(('interrupt trace', len(irqs), len(recorded_irqs)))
    return dict(game=archive.stem, machine_frames=frames, stereo_frames=total,
                active_stereo_frames=active, commands=sum(map(len, events.values())),
                accepted_irqs=len(irqs), pcm_sha256=digest.hexdigest(),
                compared_core_sha256=captured_digest.hexdigest(), captured_frames=captured_frames,
                different_stereo_frames=differences, first_pcm_difference=first_difference,
                board_cadence='Windows, 760' if windows_block else 'matched to adapter, 760/761')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'archive', 'trace', 'pcm'):
        p.add_argument(name, type=Path)
    p.add_argument('--frames', type=int, required=True)
    p.add_argument('--windows-block', action='store_true',
                   help='Use the fixed native block and compare the shared prefix of each machine frame')
    p.add_argument('--capture-fixed', action='store_true',
                   help='The diagnostic adapter submitted exactly 760 samples per machine frame')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.capture_fixed and not a.windows_block:
        p.error('--capture-fixed requires --windows-block')
    result = replay(a.exe, a.archive, a.trace, a.pcm, a.frames, a.windows_block, a.capture_fixed)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result)
