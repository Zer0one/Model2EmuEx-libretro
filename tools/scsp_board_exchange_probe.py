#!/usr/bin/env python3
"""Trace ElSemi's SCSP board scheduler, A68K slice, timer and IRQ exchange."""
import argparse
import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_FPCW)
from a68k_boundary_compare import CTX, DATA, RAM, READ, WRITE, Oracle
from scsp_control_compare import CHIP
from scsp_slot_write_compare import write

BOARD = RAM + 0x10000
DEVICE = RAM + 0x11000
BUDGET = 0x10ed9b0
ACCUMULATOR = 0x10f01d0
TIMER_A = 0x10bdf44
IRQ = CTX + 21 * 4


def block_length(o, rate, fps):
    # Execute both native calculations. Skip the intervening host audio API calls.
    o.u.mem_write(DEVICE + 0x20, struct.pack('<f', fps))
    o.run(0x4eecf0, {UC_X86_REG_EAX: rate, UC_X86_REG_ESI: DEVICE},
          stops=(0x4eed0a,))
    count = o.u.reg_read(UC_X86_REG_EAX)
    o.run(0x4cd392, {UC_X86_REG_EBP: BOARD, UC_X86_REG_EAX: count}, stops=(0x4cd39d,))
    return o.get(BOARD + 0x28)[0]


def trace(o, hz, idle):
    # Enter through the machine's scanline sound callback. Supply a guest NOP stream
    # and mask level 3 in SR so the pending level is visible at the next A68K entry.
    o.put(BOARD + 0x3c, 1)
    o.put(0x5728bc, CHIP)
    o.u.mem_write(CHIP, bytes(0x30))
    o.put(0x10482a4, 0x80 if idle else 0)
    o.put(CTX, *([0] * 33))
    o.put(CTX + 17 * 4, 0x27)
    o.put(CTX + 20 * 4, 0x1000)
    o.put(0x10ed9ac, RAM - 0x1000)
    o.u.mem_write(RAM, struct.pack('<H', 0x4e71) * 0x4000)
    o.u.mem_write(0x574dcc, struct.pack('<f', hz))
    o.put(ACCUMULATOR, 0)
    o.put(BUDGET, 0)
    o.put(TIMER_A, 0xfe00)
    o.u.mem_write(0x10bdf40, bytes((0, 1, 1)))
    o.u.mem_write(CHIP + 0x1e, struct.pack('<H', 0x40))  # Enable timer A IRQ.
    o.u.mem_write(0x10ed9d8, bytes(2))                    # Empty MIDI input.
    o.put(0x572890, 3)                                     # Timer A IRQ level.
    events = []
    sites = {0x462b1c: 'cpu', 0x4ab0e0: 'timers', 0x4aea40: 'irq', 0x4af032: 'end'}

    def observe(u, at, size, data):
        events.append(dict(stage=sites[at], budget=o.get(BUDGET)[0],
                           irq=o.get(IRQ)[0], timer=o.get(TIMER_A)[0], pc=o.get(CTX+80)[0]))

    hooks = [o.u.hook_add(UC_HOOK_CODE, observe, begin=at, end=at) for at in sites]
    slices = []
    try:
        for _ in range(3):
            events.clear()
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
            stages = ['timers', 'irq', 'end'] if idle else ['cpu', 'timers', 'irq', 'end']
            assert [row['stage'] for row in events] == stages * (len(events) // len(stages))
            slices.append(dict(residue=o.get(ACCUMULATOR)[0], events=events.copy()))
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    clocks = int(11289600 / (hz * 210))
    assert [s['residue'] for s in slices] == [clocks*n % 256 for n in (1, 2, 3)]
    ticks = [r for s in slices for r in s['events'] if r['stage'] == 'end']
    assert len(ticks) == 3 * clocks // 256
    assert [r['irq'] for r in ticks] == [0] + [3] * (len(ticks)-1)
    assert [r['timer'] for r in ticks] == [0xff00] + [0x10000] * (len(ticks)-1)
    if not idle:
        for s in slices:
            starts = [r for r in s['events'] if r['stage'] == 'cpu']
            ends = [r for r in s['events'] if r['stage'] == 'end']
            assert starts[0]['budget'] == 272
            for before, after in zip(starts[1:], ends):
                assert before['budget'] == (272 - after['budget']) & 0xffffffff
        entries = [r for s in slices for r in s['events'] if r['stage'] == 'cpu']
        assert [r['irq'] for r in entries[:3]] == [0, 0, 3]
    return dict(fps=hz, cpu_inhibited=idle, ticks=len(ticks), slices=slices)


def guest_words(o, address, *values):
    o.u.mem_write(RAM + address, struct.pack('<' + 'H' * len(values), *values))


def init_sound_cpu(o):
    for page in range(16):
        for table in (DATA, READ, WRITE):
            o.put(table + page * 16, RAM, 0, 0, 0)
    o.put(DATA + 0x100 * 16, 0, 0x4ae870, 0x4ae800, 0x4ab220)
    o.put(WRITE + 0x100 * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    guest_words(o, 0, 0, 0x8000, 0, 0x100)
    o.u.mem_write(0x1048250, bytes(128))
    o.run(0x4cd2e8, stops=(0x4cd326,), count=1000000)
    o.run(0x4cd355, {UC_X86_REG_EBP: BOARD}, stops=(0x4cd381,))


def midi_exchange(o, force_scsp_ack):
    # Use the same short guest interrupt handler as scripts/check-dsp-integration.c.
    guest_words(o, 0x78, 0, 0x120)
    guest_words(o, 0x100, 0x207c, 0, 0x2000, 0x46fc, 0x2000, 0x60fe)
    guest_words(o, 0x120, 0x3039, 0x0010, 0x0404, 0x30c0, 0x4e73)
    init_sound_cpu(o)
    live, configured = o.get(CTX + 0x5c)[0], o.get(0x10482ac)[0]
    assert (live, configured) == (0x4b3090, 0x4aeac0)
    if force_scsp_ack:
        # Counterfactual to isolate the callback from the scheduler and guest code.
        o.put(CTX + 0x5c, configured)
    o.put(BOARD + 0x3c, 1)
    o.put(0x5728bc, CHIP)
    o.u.mem_write(0x574dcc, struct.pack('<f', 60))
    o.put(ACCUMULATOR, 0)
    o.put(0x10482a4, 0)
    o.u.mem_write(CHIP, bytes(0x30))
    o.u.mem_write(0x10bdf40, bytes((1, 1, 1)))
    o.u.mem_write(0x10ed9d8, bytes(2))
    o.u.mem_write(0x1078799, bytes(1))
    o.put(0x572898, 6)
    for command in range(1, 41):
        o.run(0x4c868a, {UC_X86_REG_ECX: command}, stops=(0x4c86a8,))
    counts = {live: 0, configured: 0, 0x4ae800: 0}
    def observe(u, at, size, data):
        counts[at] += 1
    hooks = [o.u.hook_add(UC_HOOK_CODE, observe, begin=at, end=at) for at in counts]
    try:
        for _ in range(18):
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    consumed = list(struct.unpack('<40H', o.u.mem_read(RAM + 0x2000, 80)))
    assert consumed == list(range(1, 41)), (counts, consumed)
    reads = 41 if force_scsp_ack else 40
    assert counts[0x4ae800] == reads
    assert counts[live] == (0 if force_scsp_ack else 40)
    assert counts[configured] == (41 if force_scsp_ack else 0)
    assert o.get(CTX + 32)[0] == 0x2000 + 2 * reads
    return dict(force_scsp_ack=force_scsp_ack, live_after_init=hex(live), configured=hex(configured), consumed=consumed,
                observations={hex(at): n for at, n in counts.items()}, final_a0=hex(o.get(CTX + 32)[0]))


def init_scsp_exchange(o, hz):
    o.put(BOARD + 0x3c, 1)
    o.put(0x5728bc, CHIP)
    o.u.mem_write(CHIP, bytes(0x30))
    o.u.mem_write(CHIP + 0x1238, bytes([1]))  # SCSP master register callbacks.
    o.u.mem_write(0x10bdf40, bytes(3))
    o.put(TIMER_A, 0, 0, 0)
    o.put(0x572890, 0, 0, 0)
    o.u.mem_write(0x10ed9d8, bytes(2))
    o.u.mem_write(0x574dcc, struct.pack('<f', hz))
    o.put(ACCUMULATOR, 0)
    o.put(0x10482a4, 0)
    o.u.mem_write(RAM + 0x2000, bytes(64))
    o.u.mem_write(0x1078799, bytes(1))


def timer_service(o, timer, clear_first, hz):
    """Let guest interrupt code reload the timer and acknowledge its source."""
    bit = 0x40 << timer
    reg = 0x418 + 2 * timer
    level_bit = 0x40 if timer == 0 else 0x80  # Timers B/C share the level selector.

    def store(address, value):  # MOVE.W #value,(address).L
        return (0x33fc, value, 0x10, address)

    reload_timer = store(reg, 0)
    acknowledge = store(0x422, bit)
    first, second = (acknowledge, reload_timer) if clear_first else (reload_timer, acknowledge)
    sample = (0x30f9, 0x10, 0x420)  # MOVE.W SCIPD,(A0)+
    guest_words(o, 0x6c, 0, 0x200)  # Level three autovector.
    guest_words(o, 0x100, 0x207c, 0, 0x2000, *store(0x424, level_bit),
                *store(0x426, level_bit), *store(0x41e, bit), *store(reg, 0xfe),
                0x46fc, 0x2000, 0x60fe)
    guest_words(o, 0x200, *sample, *first, *sample, *second, *sample, 0x4e73)
    init_sound_cpu(o)
    assert o.get(CTX + 0x5c)[0] == 0x4b3090
    init_scsp_exchange(o, hz)
    ticks, accepts, returns = [], [], []
    rte = o.get(0x531216 + 4 * 0x4e73)[0]  # RTE in the expanded A68K dispatch table.

    def observe(u, address, size, data):
        if address == 0x462b1c:
            ticks.append(o.get(IRQ)[0])
        elif address == rte:
            returns.append((len(ticks), o.get(IRQ)[0]))
        else:
            accepts.append((len(ticks), u.reg_read(UC_X86_REG_ECX)))

    hooks = [o.u.hook_add(UC_HOOK_CODE, observe, begin=at, end=at) for at in (0x462b1c, 0x4b3090, rte)]
    try:
        for _ in range(4):
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    written = o.get(CTX + 32)[0] - 0x2000
    assert written == (12 if clear_first else 6), (timer, clear_first, accepts, written)
    count = written // 2
    samples = list(struct.unpack('<' + 'H' * count, o.u.mem_read(RAM + 0x2000, count * 2)))
    assert ticks[:3] == [0, 0, 3] and accepts[0] == (3, 3)
    expected = [bit, bit, bit, bit, 0, 0] if clear_first else [bit, bit, 0]
    assert samples == expected, (timer, clear_first, samples, ticks, accepts)
    assert accepts == ([(3, 3), (3, 3)] if clear_first else [(3, 3)]), accepts
    assert returns == ([(3, 3), (4, 0)] if clear_first else [(3, 0)]), returns
    assert not any(ticks[3:]) and o.get(IRQ)[0] == 0
    return dict(timer='ABC'[timer], fps=hz, clear_first=clear_first, cpu_entries=len(ticks),
                acknowledge_tick_and_level=accepts, rte_tick_and_pending_level=returns, guest_pending_words=samples)


def source_handoff(o, commands, midi_level, timer_level, recheck):
    """Expire timer A with MIDI already queued. Observe both guest handlers."""
    guest_words(o, (24 + midi_level) * 4, 0, 0x200)
    guest_words(o, (24 + timer_level) * 4, 0, 0x240)
    guest_words(o, 0x100, 0x207c, 0, 0x2000, 0x46fc, 0x2000, 0x60fe)
    # The optional SCIRE write clears no bits but runs the native IRQ check.
    check = (0x33fc, 0, 0x10, 0x422) if recheck else ()
    guest_words(o, 0x200, 0x30f9, 0x10, 0x404, *check, 0x4e73)
    guest_words(o, 0x240, 0x30f9, 0x10, 0x420, 0x33fc, 0, 0x10, 0x418,
                0x33fc, 0x40, 0x10, 0x422, 0x4e73)
    init_sound_cpu(o)
    init_scsp_exchange(o, 60)
    o.u.mem_write(CHIP + 0x1e, struct.pack('<H', 0x40))
    o.put(TIMER_A, 0xff00, 0, 0)
    o.put(0x572890, timer_level, 0, midi_level)
    for data in commands:
        o.run(0x4c868a, {UC_X86_REG_ECX: data}, stops=(0x4c86a8,))
    tick = 0
    accepts = []
    def observe(u, at, size, data):
        nonlocal tick
        if at == 0x462b1c:
            tick += 1
        else:
            accepts.append((tick, u.reg_read(UC_X86_REG_ECX)))
    hooks = [o.u.hook_add(UC_HOOK_CODE, observe, begin=at, end=at) for at in (0x462b1c, 0x4b3090)]
    try:
        for _ in range(4):
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    assert [level for _, level in accepts] == [midi_level]*len(commands) + [timer_level], accepts
    if recheck:
        expected_ticks = [2] * len(commands) + [2 if len(commands) == 1 else 3]
    else:
        expected_ticks = list(range(2, 3 + len(commands)))
    assert [when for when, _ in accepts] == expected_ticks, accepts
    expected = [*commands, 0x40]
    assert o.get(CTX + 32)[0] == 0x2000 + 2*len(expected)
    observed = list(struct.unpack('<'+'H'*len(expected), o.u.mem_read(RAM+0x2000, 2*len(expected))))
    assert observed == expected, observed
    assert o.get(IRQ)[0] == 0 and o.u.mem_read(CHIP+0x20, 2) == bytes(2)
    return dict(midi_level=midi_level, timer_level=timer_level, guest_recheck=recheck,
                accepts=accepts, guest_words=observed)


def stop_dispatch(o, mask, enable_timer):
    # Mark resumed guest execution in RAM independently of the IRQ routine.
    guest_words(o, 0x100, 0x4e72, 0x2000 | (mask << 8), 0x33fc, 0xbeef, 0, 0x2100, 0x60fe)
    guest_words(o, 0x6c, 0, 0x200)
    guest_words(o, 0x200, 0x33fc, 0xcafe, 0, 0x2102, 0x33fc, 0, 0x10, 0x418,
                0x33fc, 0x40, 0x10, 0x422, 0x4e73)
    init_sound_cpu(o)
    init_scsp_exchange(o, 60)
    o.put(RAM+0x2100, 0)
    o.put(TIMER_A, 0xfe00, 0, 0)
    o.put(0x572890, 3)
    if enable_timer:
        o.u.mem_write(CHIP + 0x1e, struct.pack('<H', 0x40))
    entries, exits, accepts = [], [], []
    def record(u, at, size, data):
        if at == 0x462b1c:
            entries.append([o.get(CTX+80)[0], o.get(IRQ)[0], o.get(0x10482a4)[0]])
        elif at == 0x4af022:
            exits.append([o.get(CTX+80)[0], o.get(IRQ)[0], o.get(RAM+0x2100)[0]])
        else:
            accepts.append([len(entries), u.reg_read(UC_X86_REG_ECX)])
    hooks = [o.u.hook_add(UC_HOOK_CODE, record, begin=at, end=at)
             for at in (0x462b1c, 0x4af022, 0x4b3090)]
    try:
        for _ in range(2):
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    assert exits[0] == [0x104, 0x80, 0] and entries[1] == [0x104, 0x80, 0], (entries, exits)
    assert exits[1][2] == 0xbeef
    assert accepts == ([[3, 3]] if enable_timer and mask < 3 else []), (mask, enable_timer, entries, exits, accepts, o.get(CTX+68))
    assert exits[-1][2] == (0xcafebeef if accepts else 0xbeef)
    return dict(sr_mask=mask, enable_timer=enable_timer, cpu_entries=entries, cpu_exits=exits, accepts=accepts)


def board_reset(o):
    """Invoke board vtable +0x14 with separate i960, sound and work memories."""
    board = 0x74000000
    work = board + 0x300000
    device = board + 0x280000
    vectors = device + 0x400
    i960_pages = device + 0x1000
    o.u.mem_map(board, 0x440000)
    o.u.mem_map(RAM + 0x20000, 0xe0000)
    try:
        o.u.mem_write(RAM, bytes(range(256)) * 4096)
        init_sound_cpu(o)
        init_scsp_exchange(o, 60)
        o.put(board, 0x51bbcc)
        o.put(board + 4, device)
        o.put(device + 0x28, vectors)
        o.put(board + 0x20389c, RAM)
        o.put(board + 0x203850, work)
        o.put(board + 0x203858, work + 0x100000)
        o.put(0x5aa8f4, i960_pages)
        o.put(i960_pages, device + 0x2000)
        o.u.mem_write(device + 0x2000, bytes(32))
        o.u.mem_write(work, bytes([0x61])*0x140000)
        # Distinct vector ROM and prior RAM contents, including bytes 8..15.
        o.u.mem_write(vectors, struct.pack('<4H', 0, 0x8200, 0, 0x140))
        guest_words(o, 0, 0, 0x8400, 0, 0x160, 0xabcd, 0xef12, 0x3456, 0x789a)
        guest_words(o, 0x6c, 0, 0x200)
        guest_words(o, 0x140, 0x46fc, 0x2000, 0x60fe)  # Unmask the surviving request.
        guest_words(o, 0x200, 0x3039, 0x10, 0x404, 0x60fe)
        o.u.mem_write(CHIP + 0x1e, struct.pack('<H', 0x40))
        o.u.mem_write(CHIP+0x20, struct.pack('<H', 0x40))
        o.put(TIMER_A, 0x10000, 0x3481, 0x1740)
        o.u.mem_write(0x10bdf40, bytes([1,0,0]))
        o.put(0x572890, 2, 0, 3)
        o.run(0x4c868a, {UC_X86_REG_ECX: 0x59}, stops=(0x4c86a8,))
        o.run(0x4aea40)
        o.put(ACCUMULATOR, 0x71)
        o.put(CTX, 0x12813485)
        o.put(CTX + 80, 0x160)
        ram_image = bytes(o.u.mem_read(RAM, 0x100000))
        def exchange_state():
            return [o.get(IRQ)[0], o.get(ACCUMULATOR)[0], *o.get(TIMER_A, 3),
                    *o.u.mem_read(0x10bdf40, 3), *o.u.mem_read(0x10ed9d8, 2),
                    o.u.mem_read(0x1078799, 1)[0], o.u.mem_read(0x10c35b0, 1)[0],
                    *struct.unpack('<HH', o.u.mem_read(CHIP + 0x1e, 4))]
        before = exchange_state()
        assert before == [3, 0x71, 0x10000, 0x3481, 0x1740, 1, 0, 0, 1, 0, 1, 0x59, 0x40, 0x40]
        entry = o.get(o.get(board)[0] + 0x14)[0]
        assert entry == 0x4cad60
        o.run(entry, {UC_X86_REG_ECX: board}, count=2000000)
        assert bytes(o.u.mem_read(work, 0x140000)) == bytes(0x140000)
        assert bytes(o.u.mem_read(RAM, 0x100000)) == bytes(o.u.mem_read(vectors, 8)) + ram_image[8:]
        assert exchange_state() == before
        assert (o.get(CTX+60)[0], o.get(CTX+80)[0], o.get(CTX+68)[0]) == (0x8200, 0x140, 0x27)
        assert o.get(CTX)[0] == 0x12813485
        o.put(board+0x3c, 1)
        o.run(0x4cc710, {UC_X86_REG_EAX: board}, count=100000)
        assert o.get(CTX)[0] == 0x12810059 and o.u.mem_read(0x1078799, 1)[0] == 0
        return dict(entry=hex(entry), sound_ram_bytes=0x100000, vector_bytes_copied=8,
                    sp=0x8200, pc=0x140, sr_high=0x27, preserved_irq_level=before[0],
                    preserved_phase=before[1], preserved_timers=before[2:5], command_after_reset=0x59)
    finally:
        o.u.mem_unmap(board, 0x440000)
        o.u.mem_unmap(RAM+0x20000, 0xe0000)


def midi_output(o):
    # Word/byte stores use the real A68K page wrappers and SCSP register handlers.
    o.put(0x5728bc, CHIP)
    o.put(WRITE + 0x100 * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    o.u.mem_write(CHIP + 6, bytes(2))
    o.u.mem_write(0x10ed99f, bytes(1))
    o.u.mem_write(0x107879a, bytes(1))
    o.u.mem_write(0x10be458, bytes(128))
    submitted = []
    for idx in range(260):
        width, address = ((2, 6), (1, 6), (1, 7))[idx % 3]
        value = (0xa35a + idx * 37) & 0xffff
        write(o, 0x400 + address, width, value)
        current = o.u.mem_read(CHIP + 6, 1)[0]
        submitted.append(current)
        assert o.u.mem_read(0x10be458 + idx % 128, 1)[0] == current
        assert o.u.mem_read(0x10ed99f, 1)[0] == (idx + 1) % 128
        assert o.u.mem_read(0x107879a, 1)[0] == (idx + 1) % 256
    final = bytes(o.u.mem_read(0x10be458, 128))
    assert final[4:] + final[:4] == bytes(submitted[-128:])
    return dict(stores=len(submitted), final_count=4, write_index=4, first_bytes=submitted[:6])


def i960_sound_ports(o):
    o.put(0x5aa730, BOARD)
    o.put(BOARD + 4, DEVICE)
    o.put(DEVICE + 0x104, 0)
    cases = 0
    for scsp in (False, True):
        o.put(BOARD + 0x3c, int(scsp))
        fifo, index, mask = (0x10c35b0, 0x10ed9d8, 127) if scsp else (0x5aa6e0, 0x5a96be, 31)
        for base in (0x9c0000, 0x1c80000):
            for width, writer, reader in ((1, 0x4cb570, 0x4c7650), (2, 0x4cb500, 0x4c7620),
                                          (4, 0x4cb480, 0x4c75f0)):
                for j, offset in enumerate((0, 2, 4, 0x100, 0x102, 0xff)):
                    address = base + offset
                    value = 0xa9724d16 + width * 31 + j
                    accepted = (offset & 255) == 0
                    o.put(0x10ed8f8, 0xffffffff)
                    o.put(0x5aa74c, 0xffffffff)
                    o.put(0x10f0bb0, 0x98b74d21)
                    o.u.mem_write(index, bytes([mask]))
                    o.u.mem_write(fifo + mask, bytes(1))
                    o.run(writer, {UC_X86_REG_ECX: address, UC_X86_REG_EDX: value})
                    assert o.get(0x10ed8f8)[0] == o.get(0x5aa74c)[0] == (0 if accepted else 0xffffffff)
                    assert o.get(0x10f0bb0)[0] == (value if width == 4 and accepted else 0x98b74d21)
                    assert o.u.mem_read(index, 1)[0] == (0 if accepted else mask)
                    assert o.u.mem_read(fifo + mask, 1)[0] == (value & 255 if accepted else 0)
                    o.put(0x5aa74c, 1)
                    o.run(reader, {UC_X86_REG_ECX: address})
                    status = (offset & 255) in (2, 4)
                    assert o.u.reg_read(UC_X86_REG_EAX) & ((1 << (8 * width)) - 1) == (7 if status else 255)
                    assert o.get(0x5aa74c)[0] == int(status)
                    cases += 1
    return dict(transactions=cases, boards=['Model 1 sound', 'SCSP'], aliases=2, widths=[1, 2, 4])


def return_path(o):
    ring, cursor, count = 0x10be458, 0x10ed99f, 0x107879a
    # Locate absolute operands AND stored pointers, including unaligned occurrences
    # and references to the interior of the queue in every file-backed PE section.
    refs = {}
    for s in o.pe.sections:
        raw = o.pe.data[s['offset']:s['offset'] + s['raw_size']]
        for address in (*range(ring, ring+128), cursor, count, 0x10ed9cf):
            needle = struct.pack('<I', address)
            pos = raw.find(needle)
            while pos >= 0:
                refs.setdefault(hex(address), []).append(hex(s['address'] + pos))
                pos = raw.find(needle, pos+1)
    assert refs == {
        hex(ring): ['0x4aa914', '0x4af0e6'], hex(ring + 124): ['0x4af513'],
        hex(cursor): ['0x4aa901', '0x4aa919', '0x4af0ca', '0x4af0eb', '0x4af364'],
        hex(count): ['0x4aa907', '0x4af0e0', '0x4af372'], '0x10ed9cf': ['0x4af36b']}
    touched = []
    def watch(u, kind, addr, size, value, data):
        touched.append((kind, addr, size))
    hooks = [o.u.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, watch, begin=lo, end=hi)
             for lo, hi in ((ring, ring+127), (cursor, cursor), (count, count), (0x10ed9cf, 0x10ed9cf))]
    try:
        # The operand at 004af513 points four bytes below the pan table.
        # Its first x86 index is one. No iteration touches the MIDI buffer.
        o.run(0x4af3ce, {UC_X86_REG_EBX: 0, UC_X86_REG_EBP: 0},
              stops=(0x4af5aa,), count=1000000)
        assert not touched
        # Use the native byte command handler so the host-side count is real.
        o.put(BOARD + 4, DEVICE)
        o.put(BOARD + 0x3c, 1)
        o.put(DEVICE + 0x104, 0)
        o.put(0x5aa730, BOARD)
        checks = 0
        for base in (0x9c0000, 0x1c80000):
            for width, entry in ((1, 0x4c7650), (2, 0x4c7620), (4, 0x4c75f0)):
                o.put(0x5aa74c, 0)
                o.put(0x10ed8f8, 0)
                for cmd in (0x39, 0xa7):
                    o.run(0x4cb570, {UC_X86_REG_ECX: base, UC_X86_REG_EDX: cmd})
                assert o.get(0x5aa74c)[0] == o.get(0x10ed8f8)[0] == 2
                for offset in (2, 4, 0, 0x102, 0x100, 1, 6, 0xff):
                    address = base + offset
                    before = o.get(0x5aa74c)[0]
                    o.run(entry, {UC_X86_REG_ECX: address, UC_X86_REG_EAX: 0xabcd1234})
                    value = o.u.reg_read(UC_X86_REG_EAX) & ((1 << (width*8))-1)
                    status = (offset & 255) in (2, 4)
                    assert value == (7 if status else 255)
                    assert o.get(0x5aa74c)[0] == (before if status else max(0, before-1))
                    checks += 1
                assert o.get(0x10ed8f8)[0] == 2
        assert not touched, touched
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    return dict(absolute_references=refs, host_reads=checks, watched_accesses=len(touched))


def initialize_chip(o):
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.put(0x10f1fec, 1)
    # Run the entire chip initializer, including the envelope gain table,
    # slot indices and both LFO tables. Only the CRT allocator and TLS are
    # supplied by the host. The original clears its mix buffers itself.
    work = 0x79000000
    o.u.mem_map(work,0x80000)
    buffers = iter((work,work+0x10000,work+0x40000))
    alloc = o.u.hook_add(UC_HOOK_CODE, lambda *_: o.ret(next(buffers)), begin=0x48d12f, end=0x48d12f)
    thread = 0x72018000
    o.put(thread+0x14, 1)
    tls = o.u.hook_add(UC_HOOK_CODE, lambda *_: o.ret(thread), begin=0x4980b1, end=0x4980b1)
    o.run(0x4af2c0, count=5000000)
    o.u.hook_del(tls)
    o.u.hook_del(alloc)
    return work


def dual_chip_initialization(exe):
    o = Oracle(exe)
    flag = 0x10ed9da
    assert bytes(o.u.mem_read(flag, 1)) == bytes(1)
    # A nonzero sentinel distinguishes initialization which preserves the flag
    # from a write of zero to its original zero-filled address.
    o.u.mem_write(flag, bytes([1]))
    stores = []
    def observe(u, kind, address, size, value, data):
        if address <= flag < address + size:
            stores.append((address, size))
    o.u.hook_add(UC_HOOK_MEM_WRITE, observe, begin=flag-15, end=flag)
    initialize_chip(o)
    after = o.u.mem_read(flag, 1)[0]
    assert not stores and after == 1
    return dict(loader_default=0, before_initializer=1, after_initializer=after,
                overlapping_stores=len(stores))


def host_pcm_submission(exe):
    """Observe submitted PCM descriptors; replace only the Windows API calls."""
    o = Oracle(exe)
    stream = 0x79000000
    o.u.mem_map(stream, 0x60000)
    o.put(BOARD + 0x14, stream, DEVICE)
    voices = [DEVICE + 0x400, DEVICE + 0x500]
    table = DEVICE + 0x600
    o.put(stream + 0xc, *voices)
    for voice in voices:
        o.put(voice, table)
    events, submitted, levels = [], [], {}
    stack_bytes = {'state': 8, 'start': 12, 'stop': 12, 'submit': 12, 'wait': 8}
    for index, (name, slot) in enumerate((('state', 0x64), ('start', 0x4c),
                                         ('stop', 0x50), ('submit', 0x54), ('wait', None))):
        address = RAM + 0x19000 + 16 * index
        if slot is None:
            o.put(0x508084, address)
        else:
            o.put(table + slot, address)
        o.u.mem_write(address, b'\xc2' + struct.pack('<H', stack_bytes[name]))

        def watch(u, at, size, user, operation=name):
            sp = u.reg_read(UC_X86_REG_ESP)
            arg, second = o.get(sp + 4, 2)
            if operation == 'wait':
                assert second == 100
                events.append(('wait', arg))
                return
            channel = voices.index(arg)
            events.append((operation, channel))
            if operation == 'state':
                o.put(second + 4, levels[channel].pop(0))
            elif operation == 'submit':
                flags, length, data = o.get(second, 3)
                assert flags == 0
                submitted.append((channel, data, bytes(u.mem_read(data, length))))
        o.u.hook_add(UC_HOOK_CODE, watch, begin=address, end=address)
    rows = []
    for frames in (735, 760):
        o.put(BOARD + 0x28, frames)
        o.put(stream + 0x1c, 3)
        o.put(stream + 0x34, frames, frames)
        for queued, running, expected in ((0, 0, []), (2, 0, ['start']),
                                         (3, 1, ['wait', 'state']), (0, 1, ['stop'])):
            events.clear()
            submitted.clear()
            samples = []
            for channel in (0, 1):
                raw = struct.pack(f'<{frames}H', *[(i * 1543 + 347 * channel) & 65535 for i in range(frames)])
                samples.append(raw)
                o.u.mem_write(stream + 0x68 + channel * 0x2b110, raw)
                o.put(stream + 0x24 + 4 * channel, 2)
                o.put(stream + 0x4c + 8 * channel, channel)
                o.u.mem_write(stream + 0x44 + channel, bytes([running]))
                levels[channel] = [queued, 1] if queued == 3 else [queued]
            o.run(0x4c8190, {UC_X86_REG_ECX: BOARD}, count=100000)
            assert len(submitted) == 2
            for channel, (voice, address, raw) in enumerate(submitted):
                assert voice == channel and raw == samples[channel]
                assert address == stream + 0x68 + channel * 0x2b110 + 4 * frames * 2
                assert o.get(stream + 0x24 + 4 * channel)[0] == 0
                assert [op for op, ch in events if ch == channel] == ['state', *expected, 'submit']
            rows.append(dict(frames=frames, queued=queued, running=running, submitted_bytes=frames*4))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    o = Oracle(args.exe)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.run(0x462ae0, count=1000000)  # Expand the original A68K dispatch table.
    results = []
    for hz in (58, 60):
        length = block_length(o, 44100, hz)
        assert length == 44100 // hz
        for idle in (False, True):
            result = trace(o, hz, idle)
            result['mixer_block_frames'] = length
            results.append(result)
    receipt = dict(scheduler=results, midi=[midi_exchange(o, force) for force in (False, True)],
                   midi_output=midi_output(o), return_path=return_path(o), i960_sound_ports=i960_sound_ports(o),
                   timer_service=[timer_service(o, timer, first, hz) for hz in (58, 60)
                                  for timer in range(3) for first in (False, True)])
    receipt['source_handoff'] = [source_handoff(o, commands, midi, timer, check)
                                 for commands in ((0x39,), (0x39, 0x5b, 0xa7))
                                 for midi, timer in ((2, 5), (5, 2)) for check in (False, True)]
    receipt['guest_stop'] = [stop_dispatch(o, mask, enable) for mask in (0, 3) for enable in (False, True)]
    receipt['board_reset'] = board_reset(o)
    receipt['dual_chip_initializer'] = dual_chip_initialization(args.exe)
    receipt['host_pcm_submission'] = host_pcm_submission(args.exe)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Passed scheduler, MIDI and timer exchange, guest STOP and board reset.')


if __name__ == '__main__':
    main()
