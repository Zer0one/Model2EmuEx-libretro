#!/usr/bin/env python3
"""Compare SCSP slot stores and probe the key-on sample base in ElSemi 1.1a."""
import argparse
import ctypes as C
import hashlib
import json
import random
from pathlib import Path
import struct
import subprocess
import tempfile

from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI,
    UC_X86_REG_EDX, UC_X86_REG_EFLAGS, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_FPCW,
)
from a68k_boundary_compare import Oracle, WRITE, SP, STOP
from scsp_control_compare import CHIP, ROOT

SLOT = CHIP + 0x30
STRIDE = 0x8c
SAMPLES = 0x74000000
WRAPPERS = {1: 0x4b3130, 2: 0x4b3100, 4: 0x4b30c0}
U16 = C.c_uint16
U32 = C.c_uint32


def write(o, offset, width, value, flags=0x202, wrapper_sp=SP):
    o.put(wrapper_sp, STOP)
    o.run(WRAPPERS[width], {UC_X86_REG_ECX: 0x100000 + offset,
          UC_X86_REG_EDX: value, UC_X86_REG_EFLAGS: flags, UC_X86_REG_ESP: wrapper_sp}, count=100000)


def check_stores(o, dll):
    fn = dll.scsp_slot_write_probe
    fn.argtypes = [U32, U32, U32, U32, U32, C.POINTER(U16), C.POINTER(U32)]
    o.put(0x10be358, *range(100, 164))
    o.put(0x10e3e40, *range(200, 264))
    initial = bytes((i * 57 + (i >> 5) * 3) & 255 for i in range(1024))
    # Native slot structures have private fields between register banks.
    slots = bytearray(32 * STRIDE)
    for i in range(32):
        slots[i*STRIDE:i*STRIDE+32] = initial[i*32:i*32+32]
    for i in range(32):
        struct.pack_into('<I', slots, i*STRIDE+0x38, i % 4)
        slots[i*STRIDE+0x20] = int(i % 4 != 3)
    digest = hashlib.sha256()
    counts = {'write': 0, 'guard': 0}
    for slot in (0, 1, 15, 31):
        for reg in range(32):
            for width in WRAPPERS:
                offset = slot * 32 + reg
                value = 0x93e6157b ^ (offset << 16)
                flags = 0xed7 if (width + slot) & 1 else 0x202
                regs = (U16*512).from_buffer_copy(initial)
                result = (U32*(5+11*32))()
                assert fn(offset, width, value, flags, 0, regs, result)
                last = reg + 2 if width == 4 else reg
                start = reg ^ 1 if width == 1 else reg
                payload = ((value << 16 | value >> 16) & 0xffffffff) if width == 4 else value
                depth = initial[slot*32 + 0x12]
                if start <= 0x12 < start+width:
                    depth = payload >> (8*(0x12-start))
                supported = (last & ~1) != 0x12 or not depth & 7
                if supported:
                    o.u.mem_write(SLOT, bytes(slots))
                    write(o, offset, width, value, flags)
                    raw = o.u.mem_read(SLOT, len(slots))
                    expected = b''.join(raw[i*STRIDE:i*STRIDE+32] for i in range(32))
                    if reg >= 2:
                        reference = bytearray(slots)
                        last = reg + 2 if width == 4 else reg
                        if reg in (16, 17) or last in (16, 17):
                            at = slot*STRIDE+0x2c
                            reference[at:at+4] = raw[at:at+4]
                        if reg <= 19 and last >= 18:
                            at = slot*STRIDE+0x58
                            reference[at:at+32] = raw[at:at+32]
                        if reg < 12 and last >= 8 and slots[slot*STRIDE+0x20]:
                            at = slot*STRIDE + 0x40
                            reference[at:at+21] = raw[at:at+21]
                        for byte in range(width):
                            if start+byte >= 32:
                                reference[slot*STRIDE+start+byte] = (payload >> (8*byte)) & 255
                        assert all(raw[i*STRIDE+32:(i+1)*STRIDE] ==
                               reference[i*STRIDE+32:(i+1)*STRIDE] for i in range(32))
                    scratch = [1, o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
                    for i in range(32):
                        r = i*STRIDE
                        scratch.extend((raw[r+0x20], struct.unpack_from('<I', raw, r+0x38)[0],
                                        struct.unpack_from('<I', raw, r+0x24)[0],
                                        struct.unpack_from('<I', raw, r+0x2c)[0],
                                        struct.unpack_from('<I', raw, r+0x34)[0],
                                        *struct.unpack_from('<5IB', raw, r+0x40)))
                    scratch.extend((o.get(SLOT+slot*STRIDE+0x5c)[0], o.get(SLOT+slot*STRIDE+0x6c)[0]))
                    counts['write'] += 1
                else:
                    expected, scratch = initial, [0, 0xa5a5, flags]
                    for i in range(32):
                        scratch.extend((int(i % 4 != 3), i % 4, *([0]*9)))
                    counts['guard'] += 1
                    scratch.extend((0, 0))
                assert list(result) == scratch and bytes(regs) == expected, (offset, width, scratch, list(result))
                digest.update(bytes(regs) + bytes(result))
    # Qualify both pitch-only and amplitude guard paths, including a long
    # store whose first update is pitch, and one whose first update is LFO.
    lfo_cases = 0
    for reg,width in ((0x12,1), (0x13,1), (0x12,2), (0x10,4), (0x12,4)):
        for rate in range(32):
            for pitch_depth,amp_depth in ((0,0), (7,0), (0,3), (3,7)):
                control = rate << 10 | pitch_depth << 5 | amp_depth
                start = bytearray(1024)
                struct.pack_into('<H', start, 0x12, control)
                value = (control >> 8 if reg == 0x12 else control) if width == 1 else control
                if reg == 0x12 and width == 4:
                    value = (control << 16) | 0x052a
                if reg == 0x10:
                    value |= 0x0200 << 16
                regs = (U16*512).from_buffer_copy(start)
                result = (U32*(5+11*32))()
                assert fn(reg, width, value, 0xed7, 0, regs, result)
                if amp_depth and not (reg == 0x12 and width == 4):
                    assert result[0] == 0 and bytes(regs) == start and list(result[-2:]) == [0,0]
                else:
                    o.u.mem_write(SLOT, bytes(STRIDE))
                    o.u.mem_write(SLOT, bytes(start[:32]))
                    write(o, reg, width, value, 0xed7)
                    assert bytes(regs)[:32] == bytes(o.u.mem_read(SLOT,32))
                    assert list(result[:3]) == [1,o.u.reg_read(UC_X86_REG_EAX),o.u.reg_read(UC_X86_REG_EFLAGS)]
                    assert list(result[-2:]) == [o.get(SLOT+0x5c)[0],o.get(SLOT+0x6c)[0]]
                # Exercise the same write with a known native frame. Rotate
                # the low stack bits and waveform across all rate settings.
                wrapper_sp = SP - 4 * (rate % 16)
                control |= (rate % 4) << 3
                struct.pack_into('<H', start, 0x12, control)
                if width == 4 and reg == 0x12:
                    value = control << 16 | 0x052a
                elif width == 1 and reg == 0x12:
                    value = control >> 8
                else:
                    value = value & 0xffff0000 | control
                regs = (U16*512).from_buffer_copy(start)
                assert fn(reg, width, value, 0xed7, wrapper_sp, regs, result)
                o.u.mem_write(SLOT, bytes(STRIDE))
                o.u.mem_write(SLOT, bytes(start[:32]))
                write(o, reg, width, value, 0xed7, wrapper_sp)
                assert bytes(regs)[:32] == bytes(o.u.mem_read(SLOT,32))
                assert list(result[:3]) == [1,o.u.reg_read(UC_X86_REG_EAX),o.u.reg_read(UC_X86_REG_EFLAGS)]
                assert list(result[-2:]) == [o.get(SLOT+0x5c)[0],o.get(SLOT+0x6c)[0]]
                lfo_cases += 1
    return dict(**counts, lfo_unbound_cases=lfo_cases, lfo_bound_cases=lfo_cases, result_sha256=digest.hexdigest())


def sample_addresses(o, dll):
    fn = dll.scsp_voice_sample_probe
    fn.argtypes = [C.POINTER(C.c_uint8), U32, U32, U32, U32, U32, C.c_int32, U32,
                   C.POINTER(C.c_int32), C.POINTER(U32), C.POINTER(C.c_int32), C.POINTER(U32)]
    size = 1 << 20
    # A distinct, synthetic page beyond the original allocation safely exposes
    # an escaped guest read. The C port gets exactly the allocated 1 MiB.
    ram = bytearray(size)
    for at, value in ((0x4000, 0x1133), (0x4010, 0x2255), (0x84000, 0x4477),
                      (0x80000, 0x3322), (0, 0x2211)):
        struct.pack_into('<H', ram, at, value)
    o.u.mem_map(SAMPLES, size + 4096)
    o.u.mem_write(SAMPLES, bytes(ram))
    o.u.mem_write(SAMPLES + size, b'\x66\x77')
    o.put(CHIP+0x1234, SAMPLES)
    backing = (C.c_uint8*size).from_buffer(ram)
    rows = []
    for width, base, live_low, index, want_base, want_offset in (
        (1, 0x04000, 0x4000, 0, 0x04000, 0x04001),
        (1, 0x84000, 0x4000, 0, 0x84000, 0x84001),
        (1, 0x04000, 0x4010, 0, 0x04000, 0x04001),
        (2, 0x84001, 0x4001, 0, 0x04000, 0x04000),
        (2, 0x7fffe, 0xfffe, 1, 0x7fffe, 0x80000),
        (1, 0xfffff, 0xffff, 1, 0xfffff, 0x100001),
    ):
        o.u.mem_write(SLOT, bytes(32*STRIDE))
        o.put(SLOT+0x38, 3)  # RELEASE
        control = 0x1800 | (0x10 if width == 1 else 0) | (base >> 16)
        write(o, 2, 2, base & 0xffff)
        write(o, 0, 2, control)
        write(o, 2, 2, live_low)
        latched = o.get(SLOT+0x24)[0]
        assert latched == want_base and o.u.mem_read(SLOT+0x20, 1) == b'\1'
        # Execute the actual sample-address arithmetic and signed load, stopping
        # before interpolation. The raw sample becomes history after a full step.
        start, stop = (0x4ab8f6, 0x4ab90f) if width == 1 else (0x4ad056, 0x4ad074)
        o.run(start, {UC_X86_REG_ECX: SLOT, UC_X86_REG_ESI: CHIP,
                      UC_X86_REG_EDI: index << 12}, stops=(stop,))
        physical = o.u.reg_read(UC_X86_REG_EAX) - SAMPLES
        assert physical == want_offset
        raw = int.from_bytes(o.u.mem_read(SAMPLES + physical, width), 'little', signed=True)
        assert o.u.reg_read(UC_X86_REG_EBP) == raw & 0xffffffff
        native_sample = raw * (256 if width == 1 else 1)
        sample, history = C.c_int32(), C.c_int32()
        fault = U32()
        assert fn(backing, control, base & 0xffff, live_low, index << 12, 4096, 0, 65535,
                  C.byref(sample), C.byref(fault), C.byref(history), C.byref(U32()))
        if physical >= size:
            assert fault.value == physical
        else:
            assert fault.value == 0 and sample.value == 0 and history.value == native_sample
        rows.append(dict(width=width, programmed=hex(base), live_low=hex(live_low),
                         cursor=index, latched=hex(latched), native_byte_offset=hex(physical),
                         outside_allocation=physical >= size, native_sample=native_sample,
                         portable_history=None if fault.value else history.value, portable_fault=hex(fault.value)))
    return rows


def interpolation(o, dll):
    size = 1 << 20
    ram = bytearray(size)
    backing = (C.c_uint8*size).from_buffer(ram)
    results = []
    for width, base, value in ((1, 0xfffff, 0x44), (1, 0x4010, 0xbf),
                               (2, 0x7fffe, 0xfedd), (2, 0x4010, 0x1234)):
        physical = base ^ 1 if width == 1 else base
        data = value.to_bytes(width, 'little')
        ram[physical:physical+width] = data
        o.u.mem_write(SAMPLES+physical, data)
        control = 0x1800 | (0x10 if width == 1 else 0) | (base >> 16)
        start, mixed, tail, end = ((0x4aceed, 0x4acf39, 0x4acfb1, 0x4acfcd) if width == 1
                                   else (0x4ae6ed, 0x4ae73e, 0x4ae7b2, 0x4ae7ce))
        for cursor, step, previous in ((0x800, 0x1000, 0), (0, 0, -1234),
                                       (0x7ff, 1, -2345), (0x800, 1, 321),
                                       (0xfff, 1, 7621), (0, 0x1800, -32768)):
            o.u.mem_write(SLOT, bytes(STRIDE))
            o.put(SLOT+0x38, 3)
            write(o, 2, 2, base & 0xffff)
            write(o, 0, 2, control)
            o.put(SLOT+0x2c, step)
            o.u.mem_write(SLOT+0x7c, struct.pack('<h', previous))
            o.run(start, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDI: cursor}, stops=(mixed,))
            native_pcm = C.c_int32(o.u.reg_read(UC_X86_REG_ESI)).value
            # Skip envelope, ring and mixer. The native tail compares the two
            # cursors and reads the raw sample still held by EBP or the stack.
            o.run(tail, stops=(end,))
            native_history, = struct.unpack('<h', o.u.mem_read(SLOT+0x7c, 2))
            sample, history, fault = C.c_int32(), C.c_int32(), U32()
            assert dll.scsp_voice_sample_probe(backing, control, base & 0xffff, base & 0xffff,
                        cursor, step, previous, 65535, C.byref(sample), C.byref(fault), C.byref(history), C.byref(U32()))
            assert (sample.value, history.value, fault.value) == (native_pcm, native_history, 0), (
                width, base, cursor, step, previous, native_pcm, native_history, sample.value, history.value)
            results.append(dict(width=width, base=hex(base), cursor=cursor, step=step, previous=previous,
                                pcm=native_pcm, history=native_history))
    return results


def pitch_survey(o, dll, receipt):
    table = o.u.mem_read(0x10c0168, 4096)
    digest = hashlib.sha256(table).hexdigest()
    # Acquired immediately after native table initialization in the Windows VM.
    assert digest == '0f6bc7835cdda22c5203af777e3bf9e078a325a0a516ecd35ef896575ab07492'
    if receipt:
        measured = json.loads(receipt.read_text())
        assert measured['control_word'] == 0x007f
        assert list(struct.unpack('<1024I', table)) == measured['table']
    steps = (U32*(16*1024*4))()
    dll.scsp_pitch_survey.argtypes = [C.POINTER(U32)]
    assert dll.scsp_pitch_survey(steps)
    for octave in range(16):
        for fine in range(1024):
            pitch = (octave << 11) | fine
            o.u.mem_write(SLOT+0x10, struct.pack('<H', pitch))
            o.run(0x4af73b, {UC_X86_REG_EDI: SLOT}, stops=(0x4af77e,))
            key_on = o.get(SLOT+0x2c)[0]
            write(o, 0x10, 2, pitch, 0xed7)
            live = o.get(SLOT+0x2c)[0]
            expected = [key_on, live, o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
            at = (octave*1024+fine)*4
            assert steps[at:at+4] == expected, (octave, fine, steps[at:at+4], expected)
    return dict(control_word='0x007f', table_sha256=digest, combinations=16*1024,
                result_sha256=hashlib.sha256(bytes(steps)).hexdigest())


def envelope(o, dll):
    # Run the original attack/decay table builder at the measured x87 precision.
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.put(0x10f1fec, 1)  # CRT truncating SSE2 conversion
    o.run(0x4af5aa, {UC_X86_REG_EBP: 0}, stops=(0x4af632,), count=30000)
    tables = (U32*128)()
    dll.scsp_envelope_tables(tables)
    assert list(tables) == o.get(0x10be358, 64) + o.get(0x10e3e40, 64)
    rng = random.Random(68000)
    levels = (0, 1, 31*256, 32*256-1, 32*256, 32*256+1, 1023*256-1, 1023*256)
    digest = hashlib.sha256()
    for i in range(4096):
        first, second, pitch = (rng.randrange(65536) for _ in range(3))
        state = i % 4
        volume = levels[(i//4) % len(levels)] if i < 2048 else rng.randrange(1023*256+1)
        o.u.mem_write(SLOT, bytes(STRIDE))
        o.put(SLOT, 0x800)
        o.u.mem_write(SLOT+10, struct.pack('<H', second))
        o.u.mem_write(SLOT+16, struct.pack('<H', pitch))
        o.u.mem_write(SLOT+0x20, bytes([1]))
        o.put(SLOT+0x34, volume, state)
        write(o, 8, 2, first)
        expected = o.get(SLOT+0x40, 5) + [o.u.mem_read(SLOT+0x54, 1)[0]]
        o.run(0x4ab390, {UC_X86_REG_ECX: SLOT})
        expected += [o.u.reg_read(UC_X86_REG_EAX), *o.get(SLOT+0x34, 2),
                     o.u.mem_read(SLOT+0x20, 1)[0], o.get(SLOT)[0]]
        actual = (U32*11)()
        dll.scsp_envelope_step(first, second, pitch, state, volume, actual)
        assert list(actual) == expected, (i, first, second, pitch, state, volume, list(actual), expected)
        digest.update(bytes(actual))
    return dict(rate_table_entries=128, transitions=4096, trace_sha256=digest.hexdigest())


def decay2_boundary(o, dll):
    # Zero D2R and an already quiet voice isolate the native cutoff from rate generation.
    rows = []
    for level in (0, 1, 31, 32, 33):
        o.u.mem_write(SLOT, bytes(STRIDE))
        o.put(SLOT, 0x800)
        o.u.mem_write(SLOT+0x20, bytes([1]))
        o.put(SLOT+0x34, level << 8, 2)
        o.run(0x4ab390, {UC_X86_REG_ECX: SLOT})
        original = [o.u.reg_read(UC_X86_REG_EAX), o.u.mem_read(SLOT+0x20, 1)[0], o.get(SLOT)[0]]
        result = (U32*3)()
        dll.scsp_decay2_boundary(level, result)
        assert original == ([0, 0, 0] if level < 32 else [level*4, 1, 0x800])
        assert list(result) == original
        rows.append(dict(level=level, original=original, portable=list(result)))
    return rows


def loop_traces(o, dll):
    fn = dll.scsp_loop_trace
    fn.argtypes = [C.POINTER(C.c_uint8), *([U32] * 8), C.POINTER(U32)]
    ram = (C.c_uint8*(1 << 20))()
    samples = bytes((i * 43 + 17) & 255 for i in range(128))
    ram[0x4000:0x4080] = samples
    o.u.mem_write(SAMPLES+0x4000, samples)
    # Separate synthetic scratch for the x86 LFO, ring and mixer pointers.
    wave = SAMPLES + 0x2000
    scale = wave + 0x400
    mix = scale + 0x400
    o.put(scale, 256)
    o.put(scale+0x200, 256)
    digest = hashlib.sha256()
    sequences = 0
    compared_frames = 0
    for index, entry in enumerate(o.get(0x572980, 32)):
        control = 0x1800 | ((index & 3) << 5) | (index & 16)
        for start, end, cursor, step, back in (
            (2, 5, 0, 4096, 0), (2, 5, 4*4096+900, 4800, 0),
            (2, 5, 3*4096, 4096, 1), (2, 5, 2*4096+1, 2, 1),
            (0, 4, 0, 4096, 1), (3, 3, 3*4096, 1, 1),
            (5, 2, 4096, 4096, 0), (1, 2, 0, 0, 0),
            (2, 5, 4096, 0x80004, 0)):
            frames = 1 if step == 0x80004 else 8
            o.u.mem_write(SLOT, bytes(STRIDE))
            o.put(SLOT+0x38, 3)
            for reg, value in ((2, 0x4000), (4, start), (6, end), (0, control)):
                write(o, reg, 2, value)
            o.put(SLOT+0x28, cursor, step)
            o.u.mem_write(SLOT+0x30, bytes([back]))
            o.u.mem_write(SLOT+0x7c, struct.pack('<h', -1234))
            for table in (0x60, 0x70):
                o.put(SLOT+table, wave, scale)
            rows = (U32*(frames*6))()
            assert fn(ram, control, start, end, cursor, step, back, index, frames, rows)
            for frame in range(frames):
                for offset, pointer in enumerate((0x10c11a8, 0x10982e4, 0x10be350, 0x10c3a38)):
                    o.put(pointer, mix+offset*8)
                o.put(mix, 0)
                o.run(entry, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1})
                expected = [o.get(mix)[0] & 65535, o.get(SLOT+0x28)[0],
                            o.u.mem_read(SLOT+0x30, 1)[0], o.u.mem_read(SLOT+0x20, 1)[0],
                            o.get(SLOT+0x7c)[0] & 65535, o.get(SLOT)[0] & 65535]
                actual = rows[frame*6:frame*6+6]
                assert actual == expected, (index, start, end, cursor, step, back, frame, actual, expected)
            sequences += 1
            compared_frames += frames
            digest.update(bytes(rows))
    return dict(dispatch_entries=32, sequences=sequences, frames=compared_frames,
                trace_sha256=digest.hexdigest())


def pcm_mixer(o, dll):
    # Run the original table builder and the complete dry/send gain fragment.
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.run(0x4af3ce, {UC_X86_REG_EBX: 0, UC_X86_REG_EBP: 0}, stops=(0x4af5aa,), count=1000000)
    dll.scsp_pcm_mix.restype = U32
    rng = random.Random(44100)
    digest = hashlib.sha256()
    for i in range(4096):
        sample = rng.randrange(-32768, 32768)
        tl, pan, level, send = i & 255, rng.randrange(32), rng.randrange(8), rng.randrange(8)
        o.u.mem_write(SLOT+12, struct.pack('<H', tl | ((i & 1) << 8)))
        o.u.mem_write(SLOT+20, struct.pack('<HH', 24 | send, pan << 8 | level << 13))
        o.put(0x109c474+12, 0)
        o.run(0x4aeb2d, {UC_X86_REG_EDI: SLOT+22, UC_X86_REG_EAX: sample,
                          UC_X86_REG_EBP: 0, UC_X86_REG_EBX: 0}, stops=(0x4aebbb,))
        expected = [o.u.reg_read(UC_X86_REG_EBP), o.u.reg_read(UC_X86_REG_EBX), o.get(0x109c474+12)[0]]
        left, right = C.c_int32(), C.c_int32()
        leveled = dll.scsp_pcm_level(sample, tl)
        contribution = dll.scsp_pcm_mix(leveled, pan, level, send, C.byref(left), C.byref(right))
        actual = [left.value & 0xffffffff, right.value & 0xffffffff, contribution]
        assert actual == expected, (i, sample, tl, pan, level, send, actual, expected)
        digest.update(struct.pack('<3I', *actual))
    return dict(cases=4096, trace_sha256=digest.hexdigest())


def direct_envelope(o, dll):
    entry = o.get(0x572980 + 16*4)[0]  # 8-bit one-shot, no LFO.
    rows = []
    for direct in (0, 1):
        o.u.mem_write(SLOT, bytes(STRIDE))
        o.put(SLOT, 0x810)
        o.u.mem_write(SLOT+6, struct.pack('<H', 8))
        o.u.mem_write(SLOT+12, struct.pack('<H', 0x200 | direct << 8))
        o.u.mem_write(SLOT+0x20, bytes([1]))
        o.put(SLOT+0x34, 31 << 8, 2)
        for i, ptr in enumerate((0x10c11a8, 0x10982e4, 0x10be350, 0x10c3a38)):
            o.put(ptr, SAMPLES+0x2000+i*8)
        o.run(entry, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1})
        active = o.u.mem_read(SLOT+0x20, 1)[0]
        rows.append(dict(direct=direct, native_active=active, portable_active=dll.scsp_direct_envelope_probe(direct)))
        assert rows[-1]['portable_active'] == active == 0
    return rows


def forward_loop_boundary(o, dll):
    # Dispatch index 17 selects 8-bit forward looping with both LFOs off.
    entry = o.get(0x572980 + 17*4)[0]
    assert entry == 0x4acd90
    o.u.mem_write(SLOT, bytes(STRIDE))
    o.put(SLOT+0x38, 3)
    write(o, 2, 2, 0xffff)
    write(o, 6, 2, 1)
    write(o, 0, 2, 0x183f)
    o.put(SLOT+0x2c, 4096)
    o.run(entry, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1}, stops=(0x4ace18,))
    native_cursor = o.get(SLOT+0x28)[0]
    o.run(entry, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1}, stops=(0x4acdde,))
    physical = o.u.reg_read(UC_X86_REG_EAX) - SAMPLES
    ram = (C.c_uint8*(1 << 20))()
    cursor, fault, pcm, history = U32(), U32(), C.c_int32(), C.c_int32()
    assert dll.scsp_voice_sample_probe(ram, 0x183f, 0xffff, 0xffff, 0, 4096, 0, 1,
                                       C.byref(pcm), C.byref(fault), C.byref(history), C.byref(cursor))
    assert native_cursor == 4096 and physical == 0x100001 and not fault.value
    assert cursor.value == native_cursor
    assert dll.scsp_voice_sample_probe(ram, 0x183f, 0xffff, 0xffff, cursor.value, 4096,
                                       history.value, 1, C.byref(pcm), C.byref(fault),
                                       C.byref(history), C.byref(cursor))
    assert fault.value == physical
    return dict(native_cursor=native_cursor, portable_fault=hex(fault.value),
                native_second_fetch=hex(physical), guard_page=True)


def lfo_exchange(o, dll):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP

    # Only substitute the CRT thread-data lookup. All 256 random draws and
    # both waveform/scale table builders execute in the original image.
    thread_data = 0x72010000
    o.put(thread_data + 0x14, 1)
    hook = o.u.hook_add(UC_HOOK_CODE, lambda *args: o.ret(thread_data), begin=0x4980b1, end=0x4980b1)
    try:
        o.run(0x4ab6a0, count=2000000)
    finally:
        o.u.hook_del(hook)
    waves = ((0x10bf560, 0x10bfd68), (0x10bf960, 0x10c3630),
             (0x10c31b0, 0x109a6e8), (0x10982e8, 0x10bdf50))
    steps, port_waves, port_gain = (U32*32)(), (C.c_int32*2048)(), (U32*256)()
    noise_gain = (U32 * (7*256*2))()
    dll.scsp_lfo_reference(steps, port_waves, port_gain, noise_gain)
    diffs = []
    for wave, banks in enumerate(waves):
        changes = []
        for kind, addr in enumerate(banks):
            native = struct.unpack('<256i', o.u.mem_read(addr, 1024))
            start = wave*512 + kind*256
            changes.append(sum(a != b for a, b in zip(native, port_waves[start:start+256])))
        diffs.append(changes)
    assert diffs == [[0,0]] * 4, diffs
    # When amplitude modulation is enabled the last arithmetic flags come
    # from the compiler's ADD ESP,12. Capture its actual operand, never a
    # portable address. All four waveform arms have their own return.
    stack = []
    def observe(u, at, size, data):
        stack.append(u.reg_read(UC_X86_REG_ESP))
    hooks = [o.u.hook_add(UC_HOOK_CODE, observe, begin=at, end=at) for at in
             (0x4ab5b7, 0x4ab5d0, 0x4ab5e9, 0x4ab602)]
    cases = 0
    try:
        for rate in range(32):
            for wave in range(4):
                for pd, ad in ((0,0), (7,0), (0,7), (1 + rate%7, 1 + (rate+3)%7)):
                    initial = [0x1234, 0xbeef, 0xdead, 0xabcd, 0x5678, 0xcafe, 0xbabe, 0x1234]
                    o.put(SLOT+0x58, *initial)
                    control = (rate<<10) | (wave<<8) | (pd<<5) | (wave<<3) | ad
                    if rate & 1:
                        control |= 0x8000
                    stack.clear()
                    write(o, 0x12, 2, control, 0xed7)
                    expected = initial.copy()
                    if pd:
                        expected[1:4] = [steps[rate], waves[wave][0], 0x10986e8+1024*pd]
                    if ad:
                        expected[5:8] = [steps[rate], waves[wave][1], 0x10c11b0+1024*ad]
                    assert o.get(SLOT+0x58, 8) == expected, (rate, wave, pd, ad)
                    assert o.u.reg_read(UC_X86_REG_EAX) == (steps[rate] if pd or ad else 3)
                    if ad:
                        assert len(stack) == 1
                        # The fixture stack is positive, far from signed/unsigned wrap.
                        low = stack[0] + 12
                        flags = 0x602 | (4 if (low & 255).bit_count()%2 == 0 else 0)
                        flags |= 16 if (stack[0] & 15) + 12 > 15 else 0
                    else:
                        flags = 0x646  # Final TEST of zero amplitude depth.
                    assert o.u.reg_read(UC_X86_REG_EFLAGS) == flags
                    cases += 1
    finally:
        for hook in hooks:
            o.u.hook_del(hook)
    # Run the real pitch-modulated voice up to its sample fetch. With base
    # step 4096 the resulting step equals the pitch gain in this fixture.
    write(o, 0x12, 2, 0xe0)
    o.u.mem_write(SLOT+0x20, bytes([1]))
    o.put(SLOT+0x28, 0, 4096)
    for phase in range(256):
        o.put(SLOT+0x58, phase << 8)
        o.run(0x4ab890, {UC_X86_REG_ECX:SLOT, UC_X86_REG_EDX:1}, stops=(0x4ab901,))
        assert o.u.reg_read(UC_X86_REG_EDX) == port_gain[phase], (phase, port_gain[phase])
    assert port_gain[128] == 5424
    # Zero amplitude noise produces signed pitch +128. Native scale rows
    # contain only 256 words. Observe the adjacent word used by the real
    # voice, including the amplitude triangle following the last pitch row.
    noise_table = bytes(o.u.mem_read(waves[3][1], 1024))
    zero_phases = [i for i, v in enumerate(struct.unpack('<256I', noise_table)) if v == 0]
    assert zero_phases == [211]
    edge_steps = []
    for depth in range(1, 8):
        write(o, 0x12, 2, (3 << 8) | (depth << 5))
        o.put(SLOT + 0x58, zero_phases[0] << 8)
        o.run(0x4ab890, {UC_X86_REG_ECX: SLOT, UC_X86_REG_EDX: 1}, stops=(0x4ab901,))
        step = o.u.reg_read(UC_X86_REG_EDX)
        next_word = 0x10986e8 + (depth + 1) * 1024
        assert step == o.get(next_word)[0] * 16, (depth, step)
        edge_steps.append(step)
        for phase, amplitude in enumerate(struct.unpack('<256I', noise_table)):
            pitch = 128 - amplitude
            native_pitch = o.get(0x10986e8 + depth*1024 + (pitch+128)*4)[0] * 16
            native_amplitude = o.get(0x10c11b0 + depth*1024 + amplitude*4)[0] * 16
            index = ((depth-1)*256 + phase)*2
            assert noise_gain[index:index+2] == [native_pitch, native_amplitude], (depth, phase)
    assert next_word == waves[2][1] and edge_steps[-1] == 4080
    return dict(noise_table_sha256=hashlib.sha256(noise_table).hexdigest(),
                noise_zero_phases=zero_phases, noise_edge_steps=edge_steps, noise_phase_gains=7*256*2,
                word_writes=cases, rates=list(steps), waveform_differences=diffs,
                saw_phases=256, saw_step_at_phase_128=port_gain[128], native_test_crt_seed=1)


def dsp_register_writes(o, dll):
    span = 64*2 + 32*2 + 512*2 + 4
    initial = bytes((i * 13 + 7) & 255 for i in range(span))
    buf = C.c_uint8 * span
    fn = dll.scsp_dsp_write_probe
    fn.argtypes = [U32, U32, U32, U32, U32, U32, C.POINTER(C.c_uint8), C.c_size_t, C.POINTER(U32)]
    tested = rejected = 0
    for offset in (0x700, 0x77c, 0x77e, 0x780, 0x7be, 0x7c0, 0x7fe, 0x800, 0xbf0, 0xbfa, 0xbfc, 0xbfe):
        for width, reg in ((1, offset), (1, offset+1), (2, offset), (2, offset+1), (4, offset), (4, offset+1)):
            trigger = 0xbfc if width == 4 else 0xbfe
            supported = reg != trigger
            for flags in (0x202, 0xed7):
                value = 0x1122a35a
                if supported:
                    o.u.mem_write(CHIP + 0x1248, initial)
                    write(o, reg, width, value, flags)
                    expected = bytes(o.u.mem_read(CHIP + 0x1248, span))
                    native = [o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
                for backend in (0, 1):
                    image, scratch = buf.from_buffer_copy(initial), (U32*4)()
                    accepted = fn(reg, width, value, flags, backend, 0, image, span, scratch)
                    assert accepted == int(supported), (reg, width, accepted)
                    if supported:
                        assert bytes(image) == expected and list(scratch[:2]) == native, (reg, width, backend)
                        tested += 1
                    else:
                        assert bytes(image) == initial, (reg, width, backend)
                        rejected += 1
    from scsp_write_exchange_probe import bind_test_allocator
    o.u.mem_map(0x77000000, 0x10000)
    bind_test_allocator(o, 0x77000000)
    starts = 0
    for width, reg in ((1,0xbfe), (2,0xbfe), (4,0xbfc)):
        for prior_steps, value in ((0,0), (82,0), (0,1), (128,0)):
            seed = bytearray(span)
            if prior_steps:
                # Last word of the final occupied instruction. A zero trigger
                # can shorten the program; a byte write preserves the low byte.
                struct.pack_into('<H', seed, 192 + prior_steps*8 - 2, 1)
            for wrapper_sp in (SP, SP-4, SP-20):
                o.u.mem_write(CHIP+0x123c, bytes(0x800))
                o.u.mem_write(CHIP+0x1248, bytes(seed))
                write(o, reg, width, value, 0xed7, wrapper_sp)
                native = [o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
                expected = bytes(o.u.mem_read(CHIP+0x1248, span))
                length = o.get(CHIP+0x123c+0x7b8)[0]
                for backend in (0,1):
                    image, scratch = buf.from_buffer_copy(seed), (U32*4)()
                    assert fn(reg, width, value, 0xed7, backend, wrapper_sp, image, span, scratch)
                    assert bytes(image) == expected and list(scratch[:2]) == native
                    assert list(scratch[2:]) == ([0, length] if backend == 0 else [1, 0])
                    starts += 1
    ring_fn = dll.scsp_ring_write_probe
    ring_fn.argtypes = [U32, U32, U32, U32, C.POINTER(U16), C.POINTER(U32)]
    ring_writes = 0
    for offset in range(0x600, 0x700, 2):
        for width, reg in ((1,offset), (1,offset+1), (2,offset), (2,offset+1), (4,offset), (4,offset+1)):
            seed = initial[:256]
            ring, scratch = (U16*128).from_buffer_copy(seed), (U32*2)()
            accepted = ring_fn(reg, width, 0xa123bcde, 0xed7, ring, scratch)
            o.u.mem_write(CHIP+0x11b0, seed)
            write(o, reg, width, 0xa123bcde, 0xed7)
            assert accepted and bytes(ring) == bytes(o.u.mem_read(CHIP+0x11b0, 256))
            assert list(scratch) == [o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
            ring_writes += 1
    idle_fn = dll.scsp_idle_write_probe
    idle_fn.argtypes = [U32, U32, U32, C.POINTER(U32)]
    holes = 0
    from unicorn import UC_HOOK_MEM_WRITE
    native_stores = []
    watch = o.u.hook_add(UC_HOOK_MEM_WRITE, lambda u, access, at, size, value, data: native_stores.append(at),
                         begin=CHIP, end=CHIP + 0x123c + 0x800 - 1)
    try:
        for page in range(0x100, 0x110):
            o.put(WRITE + page * 16, 0, 0x4afb00, 0x4afa20, 0x4af900)
        for offset in (0x430, 0x4fe, 0x500, 0x5fe, 0xc00, 0xffe, 0x1000, 0x8ffe, 0xfffe):
            for width, reg in ((1,offset), (1,offset+1), (2,offset), (2,offset+1), (4,offset), (4,offset+1)):
                for flags in (0x202, 0xed7):
                    scratch = (U32*2)()
                    write(o, reg, width, 0x1234abcd, flags)
                    assert idle_fn(reg, width, flags, scratch) == 1
                    assert list(scratch) == [o.u.reg_read(UC_X86_REG_EAX), o.u.reg_read(UC_X86_REG_EFLAGS)]
                    holes += 1
        assert not native_stores, native_stores
    finally:
        o.u.hook_del(watch)
    return dict(original_matches=tested, nonmutating_guards=rejected, idle_window_writes=holes, bound_dsp_starts=starts, bound_ring_writes=ring_writes)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--optimization', choices=('O0','O2'), default='O2')
    ap.add_argument('--ubsan', action='store_true')
    ap.add_argument('--pitch-survey', action='store_true', help='Compare every pitch setting with the EXE')
    ap.add_argument('--windows-pitch', type=Path, help='Compare the acquired Windows table entry by entry')
    ap.add_argument('--lfo-only', action='store_true', help='Run only the native LFO register and modulation comparison')
    ap.add_argument('--dsp-writes-only', action='store_true', help='Compare A68K DSP register writes')
    args = ap.parse_args()
    o = Oracle(args.exe)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.run(0x4af337, stops=(0x4af3ce,), count=30000)
    o.put(WRITE + 0x100*16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    o.put(0x5728bc, CHIP)
    with tempfile.TemporaryDirectory(prefix='scsp-slots-') as temp:
        lib = Path(temp) / 'slots.dylib'
        sources = ['port/snd/test/scsp_control_shim.c', 'port/snd/scsp_dsp_original.c',
                   'port/a68k/a68k.c', 'port/a68k/scsp_bus.c']
        cmd = ['clang', '-'+args.optimization, '-std=c11', '-Wall', '-Wextra', '-Werror',
               '-DSCSP_A68K_BIND_TEST', '-dynamiclib', *[str(ROOT/s) for s in sources], '-lm', '-o', str(lib)]
        if args.ubsan:
            resource = subprocess.check_output(['clang','--print-resource-dir'], text=True).strip()
            cmd.extend(['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin'])
        subprocess.run(cmd, check=True)
        dll = C.CDLL(str(lib))
        if args.lfo_only or args.dsp_writes_only:
            result = dsp_register_writes(o, dll) if args.dsp_writes_only else lfo_exchange(o, dll)
            result['original_sha256'] = hashlib.sha256(args.exe.read_bytes()).hexdigest()
            args.output.write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result))
            return
        report = dict(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                      optimization=args.optimization, ubsan=args.ubsan,
                      stores=check_stores(o, dll), envelope=envelope(o, dll), samples=sample_addresses(o, dll),
                      interpolation=interpolation(o, dll), decay2=decay2_boundary(o, dll), loops=loop_traces(o, dll), forward_loop=forward_loop_boundary(o, dll),
                      direct_envelope=direct_envelope(o, dll))
        report['pcm_mixer'] = pcm_mixer(o, dll)
        if args.pitch_survey or args.windows_pitch:
            report['pitch_survey'] = pitch_survey(o, dll, args.windows_pitch)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
