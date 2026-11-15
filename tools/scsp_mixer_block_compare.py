#!/usr/bin/env python3
"""Trace the two pinned SCSP mixers at ring writes and the DSP entry point."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_FPCW)
from a68k_boundary_compare import Oracle, WRITE
from scsp_control_compare import CHIP, ROOT
from scsp_board_exchange_probe import initialize_chip
from scsp_dsp_compare import STOP, instruction
from scsp_slot_write_compare import write

RAM = 0x74000000
SLOT = CHIP + 0x30
RING = CHIP + 0x11b0
MIX = CHIP + 0x198c
BUFFER = RAM + 0x100000


DSP = CHIP + 0x123c
EFFECTS = DSP + 0x794
JIT_BUFFER = RAM + 0x120000


def prepare_effect(o, send, effect):
    # Only the Windows allocator is replaced. ElSemi emits and executes the DSP body.
    alloc = STOP + 0x200
    o.u.mem_write(alloc, b'\xb8' + struct.pack('<I', JIT_BUFFER) + b'\xc2\x10\x00')
    o.put(0x5081d8, alloc)
    program = instruction(XSEL=1, YSEL=1, IRA=0x20 + send, ZERO=1)
    program += instruction(EWT=1, EWA=effect)
    o.u.mem_write(DSP + 0xcc, program)
    o.u.mem_write(DSP + 0xc, struct.pack('<h', 0x4000))  # Half gain.
    o.put(DSP + 0x7b8, 2)
    o.run(0x4aa040, {UC_X86_REG_EDI: DSP})
    o.u.ctl_remove_cache(JIT_BUFFER, JIT_BUFFER + 0x10000)


def trace(o, alternate, end, history, adjacent, inhibit=False, *,
          blocks=(3,), effect_route=None, modulation=None, coupled=False, voice_redirect=None, ring_cursor=None, source_case=None):
    o.u.mem_write(CHIP, bytes(0x1a2c))
    o.put(0x5728bc, CHIP)
    o.put(CHIP+0x1234, RAM)
    o.u.mem_write(CHIP+0x123c+0x7b4, b'\x01')  # Stopped DSP leaves its inputs observable.
    o.u.mem_write(0x10ed9da, b'\x00')  # One sound board.
    o.u.mem_write(0x10ed99e, bytes([alternate]))
    o.put(0x109c510, BUFFER)
    o.put(0x10c3a30, BUFFER+0x10000, BUFFER+0x11000)
    o.put(0x10bf558, BUFFER+0x12000, BUFFER+0x13000)
    o.put(SLOT, 0x0810)
    o.u.mem_write(SLOT+4, struct.pack('<HH', 16, end))
    o.u.mem_write(SLOT+12, struct.pack('<H', 0x108 | (inhibit << 9)))  # SDIR, new TL=8.
    o.u.mem_write(SLOT+20, struct.pack('<HH', 7, 7 << 13))
    o.u.mem_write(SLOT+0x20, b'\x01')
    o.put(SLOT+0x24, 0, 0, 4096)
    o.put(SLOT+0x34, 0x3ff00, 0)  # Stable full-scale attack (hold).
    o.u.mem_write(SLOT+0x54, b'\x20')
    o.u.mem_write(SLOT+10, struct.pack('<H', 0x4000))  # Keep attack at peak.
    o.u.mem_write(SLOT+0x7c, struct.pack('<h', history))
    o.put(SLOT+0x80, 4096)  # Cached unity TL from the preceding block.
    o.u.mem_write(RAM, bytes([adjacent, 32, adjacent, 32, adjacent, 32, adjacent, 32]))
    reads = []
    def read_address(u, kind, at, size, value, unused):
        if RING <= at < RING + 128:
            reads.append(['ring', (at - RING) // 2, size])
        else:
            reads.append(['ram', at - RAM, size])

    if source_case is not None:
        selector, source = source_case
        control = 0x800 | ((selector & 3) << 5) | (selector & 16) | (source << 7)
        o.put(SLOT, control)
        o.u.mem_write(SLOT + 0x12, struct.pack('<H', (0x20 if selector & 8 else 0)
                                                 | (1 if selector & 4 else 0)))
        # Constant unity gain keeps both LFO variants active without changing pitch/level.
        waveform, scale = RAM + 0x3000, RAM + 0x4000
        o.put(scale + 128 * 4, 256)
        o.put(scale, 256)
        for field in (0x58, 0x68):
            o.put(SLOT + field, 0, 0x100, waveform, scale)
    if modulation is not None:
        width, depth, ring_value = modulation
        o.put(SLOT, 0x0810 if width == 1 else 0x0800)
        o.u.mem_write(SLOT + 14, struct.pack('<H', depth << 12 | 1 << 6 | 2))
        # The two source taps straddle ring index zero after the 64-word wrap.
        o.u.mem_write(CHIP + 0x1230, bytes([62]))
        o.u.mem_write(RING + 126, struct.pack('<h', ring_value))
        o.u.mem_write(RING, struct.pack('<h', ring_value))
        o.put(SLOT + 0x24, 0x80)  # Allow signed displacement on either side of the base.
        o.u.mem_write(RAM, bytes(range(256)))
    if voice_redirect is not None:
        base, width = voice_redirect
        o.put(DSP, base)
        o.put(SLOT, 0x0810 if width == 1 else 0x0800)
        o.u.mem_write(base, bytes([0x64, 0x77])*8)
        o.put(WRITE + 0x100 * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    if ring_cursor is not None:
        o.put(WRITE + 0x100 * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
        write(o, 0x680, 2, ring_cursor)
    if coupled:
        # Slot 1 reads the ring cell immediately preceding its own position.
        # Slot 0 writes that cell before slot 1 runs. Give each a distinct PCM base.
        second = SLOT + 0x8c
        o.u.mem_write(second, bytes(o.u.mem_read(SLOT, 0x8c)))
        o.put(second + 0x24, 0x100)
        o.put(second + 0x78, 1)  # Per-slot work buffer index.
        o.u.mem_write(SLOT + 14, bytes(2))
        o.u.mem_write(second + 14, struct.pack('<H', 7 << 12 | 63 << 6 | 63))
        o.u.mem_write(RING + 124, bytes(2))
    send = 0
    if effect_route is not None:
        send, effect, listen = effect_route
        o.u.mem_write(DSP + 0x7b4, b'\0')
        o.u.mem_write(SLOT + 20, struct.pack('<HH', (send << 3) | 7, 0))
        # Silence the direct path. Only the chosen effect return reaches stereo.
        o.u.mem_write(SLOT + 0x8c * listen + 22, struct.pack('<H', 7 << 5))
        prepare_effect(o, send, effect)
    ring, dsp, left, right = [], [], [], []
    transfers = []

    def generated_entry(u, at, size, unused):
        transfers.append(dict(inputs=o.get(MIX, 16),
                              returns=list(struct.unpack('<16h', u.mem_read(EFFECTS, 32)))))

    def generated_return(u, kind, at, size, value, unused):
        transfers[-1]['effect'] = list(struct.unpack('<16h', u.mem_read(EFFECTS, 32)))

    def ring_write(u, kind, at, size, value, unused):
        ring.append([(at-RING)//2, (value & 65535)])
    def dsp_entry(u, at, size, unused):
        dsp.append(o.get(MIX + send * 4)[0])
    hooks = [o.u.hook_add(UC_HOOK_MEM_WRITE, ring_write, begin=RING, end=RING+127),
             o.u.hook_add(UC_HOOK_CODE, dsp_entry, begin=0x4a9fa0, end=0x4a9fa0)]
    if modulation is not None:
        for start, end_address in ((RING, RING + 127), (RAM, RAM + 0xfffff)):
            hooks.append(o.u.hook_add(UC_HOOK_MEM_READ, read_address, begin=start, end=end_address))
    if effect_route is not None:
        hooks.append(o.u.hook_add(UC_HOOK_CODE, generated_entry, begin=JIT_BUFFER, end=JIT_BUFFER))
        # The original wrapper decrements DEC immediately after its generated routine.
        hooks.append(o.u.hook_add(UC_HOOK_MEM_WRITE, generated_return, begin=DSP+0x74c, end=DSP+0x74c))
    indirect_stores = []
    if ring_cursor is not None:
        def observe_store(u, kind, at, size, val, data):
            if size == 2:
                indirect_stores.append((at-RING, val & 0xffff))
        hooks.append(o.u.hook_add(UC_HOOK_MEM_WRITE, observe_store, begin=RING+128, end=RING+511))
    voice_reads = []
    if voice_redirect is not None:
        for region in (RAM, voice_redirect[0]):
            hooks.append(o.u.hook_add(UC_HOOK_MEM_READ,
                         lambda u, kind, at, size, val, data: voice_reads.append((at,size)),
                         begin=region, end=region+15))
    try:
        for block, frames in enumerate(blocks):
            if block == 1 and voice_redirect is not None:
                # Change the high half through the actual guest CPU wrapper.
                write(o, 0x686, 2, voice_redirect[0] >> 16)

            o.put(0x10bfd60, frames)
            o.run(0x4af7f0, count=200000)
            for output, offset in ((left, 0x12000), (right, 0x13000)):
                output.extend(struct.unpack(f'<{frames}h', o.u.mem_read(BUFFER + offset, 2 * frames)))
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    # The stopped DSP accumulates across frames. Report each new contribution.
    deltas = [((v - prior) & 0xffffffff) for v, prior in zip(dsp, [0]+dsp)]
    result = dict(ring=ring, dsp=deltas if effect_route is None else dsp, left=left, right=right,
                  active=o.u.mem_read(SLOT+0x20, 1)[0], next_ring=o.u.mem_read(CHIP+0x1230, 1)[0])
    if modulation is not None:
        result.update(reads=reads)
    if ring_cursor is not None:
        result.update(indirect_stores=indirect_stores, final_word=struct.unpack('<H', o.u.mem_read(RING + ring_cursor*2, 2))[0])
    if voice_redirect is not None:
        result.update(voice_reads=voice_reads)
    if effect_route is not None:
        result.update(transfers=transfers, final_inputs=o.get(MIX, 16))
    if source_case is not None:
        result['slot_state'] = bytes(o.u.mem_read(SLOT + 0x20, 0x60)).hex()
    return result


def check_source_controls(o, dll):
    rows = []
    for mode, route in enumerate(('block', 'interleaved')):
        for selector in range(32):
            observed = []
            for source in range(4):
                o.u.mem_write(BUFFER, bytes(0x14000))
                row = trace(o, mode, 32, 8192, 32, blocks=(3,), source_case=(selector, source))
                state = bytes.fromhex(row['slot_state'])
                ring = dict(row['ring'])
                expected = [v for pair in zip(row['left'], row['right']) for v in pair]
                expected += [sum(row['dsp']) & 0xffffffff, struct.unpack_from('<I', state, 8)[0],
                             struct.unpack_from('<h', state, 0x5c)[0], row['active'], row['next_ring'],
                             ring.get(0, 0), ring.get(32, 0), struct.unpack_from('<H', state, 0x38)[0],
                             struct.unpack_from('<H', state, 0x48)[0]]
                out = (C.c_int32 * len(expected))()
                dll.scsp_source_block_probe(mode, selector, source, out)
                assert [v & 0xffffffff for v in out] == [v & 0xffffffff for v in expected], (route, selector, source, list(out), expected)
                observed.append(row)
            assert any(observed[0]['left']), (route, selector)
            if mode:
                muted = observed[1]
                assert not muted['ring'] and not any(muted['dsp'] + muted['left'] + muted['right'])
                assert muted['active'] and muted['next_ring'] == 32
                assert observed[1:] == [muted] * 3
                state = bytes.fromhex(muted['slot_state'])
                assert struct.unpack_from('<I', state, 8)[0] == 0  # cursor
                assert struct.unpack_from('<h', state, 0x5c)[0] == 8192  # history
            else:
                assert observed == [observed[0]] * 4, (route, selector)
            rows.append(dict(route=route, selector=selector, sources=4))
    return rows


def check_dual_effect_returns(o, dll):
    """Isolate each chip's effect returns and observe DSP call order before clipping."""
    stride = 0x1a2c
    rows = []
    for mode, route in enumerate(('block', 'interleaved')):
        for dual in (False, True):
            for first, second in ((0, 197), (301, -197), (6000, 6000), (-6000, -6000)):
                frames = 2
                o.u.mem_write(CHIP, bytes(2 * stride))
                o.u.mem_write(BUFFER, bytes(0x14000))
                o.put(0x5728bc, CHIP)
                o.put(0x109c510, BUFFER)
                o.put(0x109df3c, BUFFER + 0x6000)
                o.put(0x10c3a30, BUFFER + 0x10000, BUFFER + 0x11000)
                o.put(0x10bf558, BUFFER + 0x12000, BUFFER + 0x13000)
                o.put(0x10bfd60, frames)
                o.u.mem_write(0x10ed99e, bytes([mode]))
                o.u.mem_write(0x10ed9da, bytes([dual]))
                for offset, value in ((0, first), (stride, second)):
                    # Stopping the DSP preserves each prepared EFREG at mixer entry.
                    o.u.mem_write(DSP + offset + 0x7b4, bytes([1]))
                    o.u.mem_write(EFFECTS + offset, struct.pack('<h', value))
                    o.u.mem_write(SLOT + offset + 22, struct.pack('<H', 7 << 5))
                calls = []
                def record(u, at, size, user):
                    calls.append(u.reg_read(UC_X86_REG_EAX))
                hook = o.u.hook_add(UC_HOOK_CODE, record, begin=0x4a9fa0, end=0x4a9fa0)
                try:
                    o.run(0x4af7f0, count=200000)
                finally:
                    o.u.hook_del(hook)
                expected_calls = ([DSP, DSP + stride] if dual else [DSP]) * frames
                expected_sample = min(32767, max(-32768, 4 * (first + (second if dual else 0))))
                left, right = [struct.unpack('<2h', o.u.mem_read(BUFFER + off, 4))
                               for off in (0x12000, 0x13000)]
                assert calls == expected_calls, calls
                assert left == right == (expected_sample,) * frames, (route, dual, left, right)
                rendered = (C.c_int32 * 4)()
                dll.scsp_dual_returns_probe(mode, dual, first, second, rendered)
                assert list(rendered) == [v for pair in zip(left, right) for v in pair]
                rows.append(dict(route=route, dual=dual, returns=[first, second],
                                 dsp_calls=[hex(at) for at in calls], stereo=[list(left), list(right)]))
    return rows


def check_ring_voices(o, dll, dual):
    stride = 0x1a2c
    rows = []
    if dual:
        vectors = [(route, frames, modulation) for route in (0, 1)
                   for frames in (1, 2, 3) for modulation in (0, 0x7fff)]
    else:
        # Cover all tap indices on each input and every depth. Index 63
        # reads the preceding slot's write within this sample frame.
        registers = [(i % 16 << 12) | (i << 6) | ((i * 7 + 5) & 63) for i in range(64)]
        registers += [(15 << 12) | (63 << 6) | y for y in (0, 1, 63)]
        vectors = [(route, 3, reg) for route in (0, 1) for reg in registers]
    pattern = [bytes((i * (3 + chip * 2) + (i >> 8) * 11 + 17) & 255
                     for i in range(512 if dual else 0x10000)) for chip in range(1 + dual)]
    initial_ring = struct.pack('<64H', *((i * 1907 + 13) & 65535 for i in range(64)))
    for route, frames, modulation in vectors:
        o.u.mem_write(CHIP, bytes(2 * stride))
        o.u.mem_write(BUFFER, bytes(0x14000))
        o.put(0x5728bc, CHIP)
        o.put(0x109c510, BUFFER)
        o.put(0x109df3c, BUFFER + 0x6000)
        o.put(0x10c3a30, BUFFER + 0x10000, BUFFER + 0x11000)
        o.put(0x10bf558, BUFFER + 0x12000, BUFFER + 0x13000)
        o.put(0x10bfd60, frames)
        o.u.mem_write(0x10ed99e, bytes([route]))
        o.u.mem_write(0x10ed9da, bytes([dual]))
        for chip, cursor in enumerate((3, 53)[:1 + dual]):
            offset = chip * stride
            o.put(CHIP + offset + 0x1234, RAM + chip * 0x1000)
            o.put(CHIP + offset + 0x1230, cursor)
            o.u.mem_write(DSP + offset + 0x7b4, bytes([1]))
            o.u.mem_write(RAM + chip * 0x1000, pattern[chip])
            if not dual:
                o.u.mem_write(RING, initial_ring)
            for sl in (0, 1):
                slot = SLOT + offset + sl * 0x8c
                o.put(slot, 0x810)
                o.u.mem_write(slot+4, struct.pack('<HH', 16, 64))
                o.u.mem_write(slot+10, struct.pack('<HHH', 0x4000, 0x108,
                              modulation if (chip if dual else sl) else 0))
                o.u.mem_write(slot+20, struct.pack('<HH', 7 | (sl << 3), 0xe000))
                o.u.mem_write(slot+0x20, bytes([1]))
                o.put(slot+0x24, (128 if dual else 0x8000) + 32*sl, 0, 4096)
                o.put(slot+0x34, 0x3ff00, 0)
                o.u.mem_write(slot+0x54, bytes([0x20]))
                o.put(slot+0x78, sl)
                o.u.mem_write(slot+0x7c, struct.pack('<h', (chip*2+sl+1)*137))
                o.put(slot+0x80, 4096)
        o.run(0x4af7f0, count=200000)
        channels = [struct.unpack(f'<{frames}h', o.u.mem_read(BUFFER+loc, frames*2))
                    for loc in (0x12000, 0x13000)]
        expected = [v for pair in zip(*channels) for v in pair]
        for chip in range(1 + dual):
            offset = stride*chip
            expected.extend(struct.unpack('<64h', o.u.mem_read(RING+offset, 128)))
            expected.extend(o.get(MIX+offset, 2))
            expected.append(o.get(CHIP+offset+0x1230)[0])
        out = (C.c_int32 * len(expected))()
        dll.scsp_ring_voices_probe(route, frames, dual, modulation, out)
        differences = [(i, a, b) for i, (a, b) in enumerate(zip(out, expected))
                       if (a & 0xffffffff) != (b & 0xffffffff)]
        assert not differences, (route, frames, dual, hex(modulation), differences[:8])
        rows.append(dict(route=route, frames=frames, modulation=modulation,
                         cursors=[expected[2 * frames + chip * 67 + 66] for chip in range(1 + dual)]))
    return rows


def check_pcm_fetch(o, dll):
    # Keep the entire synthetic MiB available to the port. The native oracle
    # also maps guard bytes so its original out-of-allocation read is observable.
    size = 1 << 20
    data = bytes((i * 47 + (i >> 8) * 13 + 157) & 255 for i in range(8192))
    backing = (C.c_uint8 * size)()
    backing[:len(data)] = data
    o.u.mem_write(RAM, data)
    o.put(0x5728bc, CHIP)
    o.put(CHIP + 0x1234, RAM)
    o.u.mem_write(CHIP + 0x1230, bytes([62]))
    table = o.get(0x572980, 32)
    observed_reads, mixed = [], []
    read_hook = o.u.hook_add(UC_HOOK_MEM_READ,
        lambda u, kind, at, width, value, user: observed_reads.append((at - RAM, width)),
        begin=RAM, end=RAM + size + 4)
    mix_hook = o.u.hook_add(UC_HOOK_CODE,
        lambda u, at, length, user: mixed.append(u.reg_read(UC_X86_REG_EDI)),
        begin=0x454a47, end=0x454a47)
    scratch = BUFFER + 0x10000
    digest = hashlib.sha256()
    checked = [0, 0]
    guarded = [0, 0]
    try:
        for route in (0, 1):
            for width in (1, 2):
                for mode in range(4):
                    for sb in range(4):
                        for base, cursor, step, back, tap in (
                            (128, 0x7ff, 1, 0, None), (128, 0xfff, 1, 0, 9),
                            (128, 2*4096, 4096, 0, -9), (128, 4*4096, 4096, 1, -3),
                            (128, 8*4096, 5000, 0, 0), (128, 0xfff800, 0, 0, 7),
                            (size-1 if width == 1 else size-2, 0, 4096, 0, None)):
                            control = 0x800 | (0x10 if width == 1 else 0) | mode << 5 | sb << 9
                            o.u.mem_write(SLOT, bytes(0x8c))
                            o.put(SLOT, control)
                            o.u.mem_write(SLOT+4, struct.pack('<HH', 3, 8))
                            o.u.mem_write(SLOT+10, struct.pack('<H', 0x4000))
                            o.u.mem_write(SLOT+14, struct.pack('<H', 0 if tap is None else 0xf042))
                            for cell in (0, 63):
                                o.u.mem_write(RING+2*cell, struct.pack('<h', tap or 0))
                            o.u.mem_write(SLOT+0x20, bytes([1]))
                            o.put(SLOT+0x24, base, cursor, step)
                            o.put(SLOT+0x30, back, 0x20000, 0)
                            o.u.mem_write(SLOT+0x7c, struct.pack('<h', -1234))
                            for idx, pointer in enumerate((0x10c11a8, 0x10982e4, 0x10be350, 0x10c3a38)):
                                o.put(pointer, scratch + 8*idx)
                            observed_reads.clear()
                            mixed.clear()
                            if route:
                                o.run(0x4548c0, {UC_X86_REG_ESI: SLOT})
                                raw, = mixed
                            else:
                                o.run(table[mode + (16 if width == 1 else 0)],
                                      {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1})
                                raw = struct.unpack('<h', o.u.mem_read(scratch, 2))[0] & 0xffffffff
                            reads = observed_reads
                            index = (cursor >> 12) * width
                            if route and tap is not None:
                                index += tap * 1024 >> 11
                                if width == 2:
                                    index &= ~1
                            offsets = [index]
                            if route:
                                offsets = [index, index+1] if width == 1 else [index+2, index]
                            expected_reads = [((base+x) ^ (width == 1), width) for x in offsets]
                            assert reads == expected_reads, (route, reads, expected_reads)
                            output = (C.c_uint32 * 9)()
                            dll.scsp_pcm_fetch_probe(backing, route, control, base, cursor, step,
                                                     back, tap or 0, int(tap is not None), output)
                            escaped = next((at for at, w in reads if at+w > size), None)
                            if escaped is None:
                                expected = [raw, o.get(SLOT+0x28)[0], o.u.mem_read(SLOT+0x30, 1)[0],
                                            o.u.mem_read(SLOT+0x20, 1)[0], o.get(SLOT+0x7c)[0] & 65535,
                                            o.get(SLOT+0x38)[0], o.get(SLOT)[0] & 65535, 0, 0]
                                assert list(output) == expected, (route, width, mode, sb, cursor, list(output), expected)
                            else:
                                assert tuple(output[7:]) == (1, escaped)
                                assert output[1:5] == [cursor, back, 1, (-1234) & 65535]
                                guarded[route] += 1
                            checked[route] += 1
                            digest.update(bytes(output))
    finally:
        o.u.hook_del(read_hook)
        o.u.hook_del(mix_hook)
    return dict(cases_per_route=checked, bounded_faults_per_route=guarded, sha256=digest.hexdigest())


def check_voice_dispatch(o):
    """Enumerate the original selector independently of game register writes."""
    table = o.get(0x572980, 32)
    assert all(o.pe.is_code(target) for target in table)
    rows = []
    for board, start, call, slot in ((0, 0x4aa992, 0x4aaa31, SLOT),
                                     (1, 0x4aaa92, 0x4aab34, SLOT + 0x1a2c)):
        for index, target in enumerate(table):
            control = ((index & 3) << 5) | (index & 16)
            # Nonzero PLFOS (bits 7:5) and ALFOS (2:0) each select one bank.
            lfo = (0xe0 if index & 8 else 0) | (7 if index & 4 else 0)
            o.put(slot, control)
            o.put(slot + 0x12, lfo)
            o.run(start, {UC_X86_REG_ESI: slot + 0x12}, stops=(call,))
            assert o.stop == call
            assert o.u.reg_read(UC_X86_REG_EDI) == index
            assert o.u.reg_read(UC_X86_REG_EAX) == target
            rows.append(dict(board=board, index=index, target=f'{target:08x}'))
    return rows


def check_transfers(o, dll):
    comparisons = []
    for alternate, route in ((0, 'block'), (1, 'interleaved')):
        for blocks in ((3,), (1, 2), (2, 1), (1, 1, 1)):
            for send, effect, listen in ((0, 0, 0), (15, 13, 13), (15, 13, 12)):
                o.u.mem_write(BUFFER, bytes(0x14000))
                result = trace(o, alternate, 2, 8192, 32, blocks=blocks,
                               effect_route=(send, effect, listen))
                records = result['transfers']
                assert len(records) == 3
                assert result['final_inputs'] == [0] * 16
                for mix, row in zip(result['dsp'], records):
                    assert row['inputs'] == [mix if n == send else 0 for n in range(16)]
                    assert row['returns'] == [0] * 16
                    assert row['effect'] == [mix // 512 if n == effect else 0 for n in range(16)]
                expected_inputs = ([1482752, 1482752, 0] if alternate else
                                   [1482752 if blocks[0] == 1 else 0, 0, 0])
                assert result['dsp'] == expected_inputs
                expected_stereo = [value // 128 if listen == effect else 0 for value in expected_inputs]
                assert result['left'] == result['right'] == expected_stereo
                program = instruction(XSEL=1, YSEL=1, IRA=0x20 + send, ZERO=1)
                program += instruction(EWT=1, EWA=effect)
                out = (C.c_int32 * 23)()
                dll.scsp_active_effect_probe(alternate, send, effect, listen,
                        (C.c_uint16 * 8).from_buffer_copy(program),
                        (C.c_uint * len(blocks))(*blocks), len(blocks), out)
                assert list(out[:6]) == [v for pair in zip(result['left'], result['right']) for v in pair]
                assert list(out[6:22]) == result['final_inputs']
                assert out[22] == records[-1]['effect'][effect]
                comparisons.append(dict(route=route, blocks=blocks, send=send, effect=effect,
                                        listen=listen, inputs=result['dsp'],
                                        returns=[row['effect'][effect] for row in records],
                                        stereo=result['left']))
    return comparisons


def check_power_on(exe, dll):
    o = Oracle(exe)
    initialize_chip(o)
    o.put(0x5728bc, CHIP)
    o.put(WRITE + 0x100 * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    values = (C.c_int32 * 5120)()
    dll.scsp_gain_tables(values)
    cursor = 0
    gains = {}
    for name, address, size in [('envelope', 0x10be558, 1024),
                                ('pitch_lfo', 0x10986e8, 2048),
                                ('amplitude_lfo', 0x10c11b0, 2048)]:
        raw = bytes(o.u.mem_read(address, size * 4))
        native = struct.unpack(f'<{size}i', raw)
        diffs = [(i, a, b) for i, (a, b) in enumerate(zip(native, values[cursor:cursor+size])) if a != b]
        assert not diffs, (name, len(diffs), diffs[:12])
        gains[name] = dict(entries=size, sha256=hashlib.sha256(raw).hexdigest())
        cursor += size
    expected = []
    for value in (None, 0x1800, 0x1000, 0x1800):
        if value is not None:
            write(o, 0, 2, value)
        for i in range(32):
            slot = SLOT + i * 0x8c
            expected.extend((o.get(slot+0x78)[0], o.u.mem_read(slot+0x20, 1)[0],
                             o.get(slot+0x38)[0], o.get(slot)[0] & 0xffff, o.get(slot+0x34)[0]))
    out = (C.c_uint32 * len(expected))()
    dll.scsp_cold_key_scans(out)
    assert list(out) == expected, [(i, a, b) for i, (a, b) in enumerate(zip(out, expected)) if a != b][:12]
    return dict(gains=gains, slot_observations=32*4)

def check_ring_reads(o):
    rows = []
    for alternate, route in ((0, 'block'), (1, 'interleaved')):
        for width in (1, 2):
            for tap in (-8, 0, 8):
                o.u.mem_write(BUFFER, bytes(0x14000))
                result = trace(o, alternate, 32, 8192, 32, blocks=(1,),
                               modulation=(width, 15, tap))
                if alternate:
                    base = 0x80 + tap // 2
                    expected = [['ring', 63, 2], ['ring', 0, 2]]
                    addresses = [base ^ 1, (base+1) ^ 1] if width == 1 else [base+2, base]
                else:
                    expected = []
                    addresses = [0x81 if width == 1 else 0x80]
                expected.extend(['ram', at, width] for at in addresses)
                assert result['reads'] == expected, (route, width, tap, result)
                rows.append(dict(route=route, width=width, tap=tap, reads=result['reads']))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    o = Oracle(args.exe)
    o.u.mem_map(RAM, 0x130000)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.run(0x4af3ce, {UC_X86_REG_EBX: 0, UC_X86_REG_EBP: 0}, stops=(0x4af5aa,), count=1000000)
    results = {}
    cases = (
            ('gain_change', 32, 8192, 32, False), ('inhibit', 32, 8192, 32, True),
            ('one_shot', 2, 8192, 32, False), ('history', 32, 4096, 64, False))
    for alternate, name in ((0, 'block'), (1, 'interleaved')):
        for label, end, history, adjacent, inhibit in cases:
            o.u.mem_write(BUFFER, bytes(0x14000))
            results[name+'_'+label] = trace(o, alternate, end, history, adjacent, inhibit)
    with tempfile.TemporaryDirectory(prefix='scsp-block-') as temp:
        library = Path(temp) / 'slots.dylib'
        sources = ['port/snd/test/scsp_control_shim.c', 'port/snd/scsp_dsp_original.c',
                   'port/a68k/a68k.c', 'port/a68k/scsp_bus.c']
        subprocess.run(['clang', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-DSCSP_A68K_BIND_TEST', '-dynamiclib', *[str(ROOT/f) for f in sources],
                        '-lm', '-o', str(library)], check=True)
        dll = C.CDLL(str(library))
        tables = (C.c_uint32*128)()
        dll.scsp_envelope_tables(tables)
        for backend in (0, 1):
            for label, end, history, adjacent, inhibit in cases:
                rows = (C.c_uint32*19)()
                dll.scsp_block_route_probe(backend, end, history, adjacent, inhibit, 0, 0, rows)
                results[f'port_{backend}_{label}'] = dict(ring_after=[[rows[i], rows[i+1]] for i in range(0,15,5)],
                    dsp=list(rows[2:15:5]), left=list(rows[3:15:5]), right=list(rows[4:15:5]))
        portable = []
        for mode in (0, 1):
            for source in range(4):
                output = (C.c_uint32 * 19)()
                dll.scsp_block_route_probe(0, 32, 8192, 32, 0, mode, source, output)
                if source == 0:
                    reference = list(output)
                    assert any(reference[3:15:5])
                if mode and source:
                    assert all(output[i] == 0 for i in range(15) if i % 5)
                    assert list(output[15:]) == [0, 0x3ff00, 8192, 1]
                else:
                    assert list(output) == reference
                portable.append(dict(interleaved=bool(mode), source=source,
                                     stereo=list(output[3:15:5]), cursor=output[15]))
        results['portable_source_controls'] = portable
        checked = []
        for mode, name in enumerate(('block', 'interleaved')):
            for label, end, history, adjacent, inhibit in cases:
                for frames, cursors in ((3, (0,)), (1, (0, 63, 64, 65, 66, 68, 70, 75, 76, 139, 140, 171, 172, 255))):
                    for cursor in cursors:
                        o.u.mem_write(BUFFER, bytes(0x14000))
                        row = trace(o, mode, end, history, adjacent, inhibit, blocks=(frames,), ring_cursor=cursor)
                        out = (C.c_uint32 * 10)()
                        dll.scsp_mixer_block_probe(mode, end, history, adjacent, inhibit, cursor, frames, out)
                        expected = [v & 0xffffffff for pair in zip(row['left'], row['right']) for v in pair]
                        assert list(out[:2*frames]) == expected, (name, label, cursor, 'pcm')
                        # At a silent ring write the original and portable RAM addresses
                        # differ numerically. Compare stored words when a write occurred.
                        assert list(out[6:9]) == [sum(row['dsp']) & 0xffffffff, row['next_ring'], row['active']], (name, label, cursor, list(out), row)
                        if row['ring'] or row['indirect_stores']:
                            assert out[9] == row['final_word'], (name, label, cursor, out[9], row)
                        checked.append([name, label, cursor, frames])
        results['portable_block_cases'] = len(checked)
        results['pcm_fetch'] = check_pcm_fetch(o, dll)
        results['active_transfers'] = check_transfers(o, dll)
        results['power_on'] = check_power_on(args.exe, dll)
        results['source_controls'] = check_source_controls(o, dll)
        results['dual_effect_returns'] = check_dual_effect_returns(o, dll)
        results['dual_voices'] = check_ring_voices(o, dll, True)
        results['coupled_voice_taps'] = check_ring_voices(o, dll, False)
    assert results['interleaved_gain_change']['ring'] == [[0,4092], [32,2896], [0,2896]]
    assert results['block_gain_change']['ring'] == [[0,8192]] * 3
    assert results['block_one_shot']['dsp'] == [0,0,0]
    assert results['interleaved_one_shot']['dsp'] == [1482752,1482752,0]
    for label, *_ in cases:
        assert results['port_0_'+label]['dsp'] == results['port_1_'+label]['dsp']
    for backend in (0, 1):
        assert results[f'port_{backend}_gain_change']['dsp'] == results['block_gain_change']['dsp']
        # The portable probe calls three distinct single-frame blocks. Only the
        # first ends with the ordinary one-shot voice still active.
        assert results[f'port_{backend}_one_shot']['dsp'] == [results['block_gain_change']['dsp'][0], 0, 0]
    assert results['interleaved_inhibit']['ring'] == []
    assert results['block_inhibit']['ring'] == results['block_gain_change']['ring']
    results['ring_modulation'] = check_ring_reads(o)
    coupled = {}
    for alternate, route in ((0, 'block'), (1, 'interleaved')):
        o.u.mem_write(BUFFER, bytes(0x14000))
        coupled[route] = trace(o, alternate, 32, 8192, 32, blocks=(1,),
                               modulation=(1, 15, 0), coupled=True)
    assert coupled['block']['reads'] == [['ram', 129, 1], ['ram', 257, 1]]
    assert coupled['interleaved']['ring'][0] == [62, 0xc08f]
    assert coupled['interleaved']['reads'] == [
        ['ram', 129, 1], ['ram', 128, 1], ['ring', 62, 2], ['ring', 62, 2],
        ['ram', 225, 1], ['ram', 224, 1]]
    # Probe the reverse direction with a live voice. Both allocations have
    # distinct synthetic data; a stopped DSP cannot itself issue a memory read.
    private = 0x78000000
    o.u.mem_map(private, 0x1000)
    redirects = []
    for alternate, route in ((0,'block'), (1,'interleaved')):
        for width in (1,2):
            o.u.mem_write(BUFFER, bytes(0x14000))
            row = trace(o, alternate, 32, 8192, 32, blocks=(1,1),
                        voice_redirect=(private,width))
            reads = row['voice_reads']
            count = 2 if alternate else 1
            assert len(reads) == 2*count, (route,width,reads)
            assert all(ram <= at < ram+16 and size == width for ram, group in
                       ((RAM,reads[:count]), (private,reads[count:])) for at,size in group), (route,width,reads)
            redirects.append(dict(route=route, width=width, reads=[hex(at) for at,_ in reads]))
    results['voice_ram_redirect'] = redirects
    cursor_cases = []
    for alternate, route in ((0,'block'), (1,'interleaved')):
        for cursor in (63, 66, 70, 76, 255):
            o.u.mem_write(BUFFER, bytes(0x14000))
            row = trace(o, alternate, 32, 8192, 32, blocks=(1,), ring_cursor=cursor)
            cursor_cases.append(dict(route=route, cursor=cursor, stores=row['indirect_stores'],
                                     ring=row['ring'], next_cursor=row['next_ring']))
    results['cpu_written_ring_cursor'] = cursor_cases
    results['adjacent_voices'] = coupled
    results['ordinary_voice_dispatch'] = check_voice_dispatch(o)
    results['original_sha256'] = hashlib.sha256(args.exe.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(results, indent=2)+'\n')
    print(f"Compared {len(cases)} mixer inputs and {len(results['active_transfers'])} active DSP transfers.")


if __name__ == '__main__':
    main()
