#!/usr/bin/env python3
"""Trace LFO, MIDI and DSP writes from the original A68K page table into the next opcode."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from unicorn import UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EFLAGS
from a68k_boundary_compare import RAM, WRITE
from a68k_sequence_compare import ChainOracle
from scsp_control_compare import CHIP
from scsp_dsp_compare import STOP, instruction
from scsp_slot_write_compare import WRAPPERS, write

MIDI_CURSOR = 0x10ed99f
MIDI_COUNT = 0x107879a
MIDI_RING = 0x10be458
MPRO = CHIP + 0x1308
CODE_BUFFER = RAM + 0x10000


def arithmetic_flags(result, carry=False, auxiliary=False, overflow=False, bits=8):
    result &= (1 << bits) - 1
    return (int(carry) | (int((result & 255).bit_count() % 2 == 0) << 2) |
            (int(auxiliary) << 4) | (int(result == 0) << 6) |
            (((result >> (bits - 1)) & 1) << 7) | (int(overflow) << 11))


def midi(o):
    # INC count supplies OF/SF/ZF/AF/PF. The preceding cursor mask clears CF.
    cases = 0
    for width, offset in ((1, 0x406), (1, 0x407), (2, 0x406), (4, 0x404), (4, 0x406)):
        for initial in (0, 14, 15, 126, 127, 254, 255):
            for flags in (0x202, 0xed7):
                cursor = initial & 127
                o.u.mem_write(MIDI_CURSOR, bytes([cursor]))
                o.u.mem_write(MIDI_COUNT, bytes([initial]))
                o.put(CHIP + 4, 0x56340000)
                write(o, offset, width, 0x1122a35a, flags)
                expected_byte = {(1, 0x406): 0x34, (1, 0x407): 0x5a, (2, 0x406): 0x5a,
                                 (4, 0x404): 0x5a, (4, 0x406): 0x22}[width, offset]
                assert o.u.mem_read(MIDI_RING + cursor, 1)[0] == expected_byte
                assert o.u.mem_read(MIDI_CURSOR, 1)[0] == (cursor + 1) % 128
                assert o.u.mem_read(MIDI_COUNT, 1)[0] == (initial + 1) % 256
                # A longword starting at 406 ends in the update for 408.
                if (width, offset) != (4, 0x406):
                    assert o.u.reg_read(UC_X86_REG_EAX) == (cursor + 1) % 128
                    expected = arithmetic_flags(initial + 1, auxiliary=initial % 16 == 15,
                                                overflow=initial == 127)
                    assert o.u.reg_read(UC_X86_REG_EFLAGS) == (flags & ~0x8d5) | expected
                else:
                    assert o.u.reg_read(UC_X86_REG_EAX) == 8
                    expected = arithmetic_flags(6 - 0x27, carry=True, auxiliary=True, bits=32)
                    assert o.u.reg_read(UC_X86_REG_EFLAGS) == (flags & ~0x8d5) | expected
                cases += 1
    return cases


def bind_test_allocator(o, allocation):
    # Fixed virtual allocation for the recompiler, as in scsp_dsp_compare.
    # Both stubs lie outside the ChainOracle's synthetic page callbacks.
    for iat, stub, result, pop in ((0x5081d8, STOP+0x200, allocation, 16),
                                   (0x5081e0, STOP+0x220, 1, 12)):
        o.put(iat, stub)
        o.u.mem_write(stub, b'\xb8' + struct.pack('<I', result) + b'\xc2' + struct.pack('<H', pop))


def dsp(o):
    bind_test_allocator(o, CODE_BUFFER)
    # Check the complete register and adjacent TEMP image, including writes
    # that straddle two native arrays. Byte writes in 7c0..7ff are dropped.
    cases = starts = 0
    for address in (0x700, 0x77e, 0x780, 0x7be, 0x7c0, 0x7fe, 0x800, 0xbf0, 0xbfc, 0xbfe):
        for width, offset in ((1, address), (1, address+1), (2, address), (4, address)):
            for value in (0, 0x1122a35a):
                o.u.mem_write(CHIP+0x123c, bytes(0x800))
                base = CHIP + 0x1248
                expected = bytearray(MPRO + 0x404 - base)
                index = offset - 0x700 if offset < 0x800 else MPRO - base + offset - 0x800
                if width == 1:
                    if not 0x7c0 <= offset < 0x800:
                        expected[index ^ 1] = value & 255
                elif width == 2:
                    struct.pack_into('<H', expected, index, value & 65535)
                else:
                    struct.pack_into('<HH', expected, index, value >> 16, value & 65535)
                flags = 0xed7 if value else 0x202
                o.run(WRAPPERS[width], {UC_X86_REG_ECX: 0x100000 + offset, UC_X86_REG_EDX: value,
                                       UC_X86_REG_EFLAGS: flags}, count=100000)
                assert o.u.mem_read(base, len(expected)) == expected, (hex(offset), width, value)
                trigger = 0xbfc if width == 4 else 0xbfe
                started = offset == trigger
                assert o.get(CHIP+0x123c+0x7e8)[0] == (CODE_BUFFER if started else 0)
                eax = o.u.reg_read(UC_X86_REG_EAX)
                if started:
                    steps = 128 if value else 0
                    assert o.get(CHIP+0x123c+0x7b8)[0] == steps
                    assert eax == (steps or CODE_BUFFER)
                    starts += 1
                else:
                    expected_flags = arithmetic_flags(offset-trigger, carry=offset<trigger,
                                                      auxiliary=(offset & 15)<(trigger & 15), bits=32)
                    assert eax == CHIP
                    assert o.u.reg_read(UC_X86_REG_EFLAGS) == (flags & ~0x8d5) | expected_flags
                cases += 1
    return cases, starts


def ring_window(o):
    # The two CPU lanes of a byte store both replace a whole 16-bit slot.
    # Beyond ring item 63 the native callback addresses the next chip fields.
    base = CHIP + 0x11b0
    initial = bytes((i*13 + 17) & 255 for i in range(256))
    cases = 0
    for address in (0x600, 0x67e, 0x680, 0x684, 0x686, 0x688, 0x68c, 0x698, 0x6fe):
        for width, offset in ((1,address), (1,address+1), (2,address), (4,address)):
            for flags in (0x202, 0xed7):
                o.u.mem_write(base, initial)
                write(o, offset, width, 0xa123bcde, flags)
                expected = bytearray(initial)
                if width == 4:
                    eax = 0x4af900
                    af = arithmetic_flags(offset - 0x700, carry=True,
                                          auxiliary=False, bits=32)
                else:
                    struct.pack_into('<H', expected, address-0x600, 0xde if width == 1 else 0xbcde)
                    eax = CHIP
                    index = (offset - 0x600) >> 1
                    af = arithmetic_flags(index, carry=bool(offset & 1), bits=32)
                assert bytes(o.u.mem_read(base, 256)) == expected, (offset, width)
                assert o.u.reg_read(UC_X86_REG_EAX) == eax
                assert o.u.reg_read(UC_X86_REG_EFLAGS) == (flags & ~0x8d5) | af
                cases += 1
    # Portion of the original voice routine that actually dereferences
    # chip+0x1234. Supply two mapped synthetic backing regions with distinct
    # samples and change only the pointer's low 16 bits via the guest CPU.
    old_ram, new_ram = RAM + 0x6000, RAM + 0x7000
    o.u.mem_write(old_ram+1, bytes([0x12]))
    o.u.mem_write(new_ram+1, bytes([0x34]))
    o.put(CHIP+0x1234, old_ram)
    observed = []
    samples = []
    for change in (False, True):
        if change:
            write(o, 0x684, 2, 0x7000)
        observed.append(o.get(CHIP+0x1234)[0])
        o.run(0x4ab901, {UC_X86_REG_EAX:0, UC_X86_REG_ESI:CHIP}, stops=(0x4ab90f,))
        samples.append(o.u.reg_read(UC_X86_REG_EBP))
    assert observed == [old_ram, new_ram] and samples == [0x12, 0x34]
    return dict(cases=cases, sample_pointer_before=hex(old_ram), sample_pointer_after=hex(new_ram), samples=samples)


def dsp_ram_alias(o):
    """Does emitted code retain its original memory base after a CPU store?"""
    dsp = CHIP + 0x123c
    private, voice = 0x78000000, 0x73000000
    for base in (private, voice):
        o.u.mem_map(base, 0x1000)
    accesses = []
    for base in (private, voice):
        o.u.hook_add(UC_HOOK_MEM_READ,
                     lambda u, kind, at, size, val, data: accesses.append((at, size)),
                     begin=base, end=base + 0xfff)
    program = instruction() + instruction(MRD=1,TABLE=1) + instruction(IWT=1,IWA=7)
    bind_test_allocator(o, CODE_BUFFER)
    results = []
    # Chosen markers, then the same words exchanged between the two buffers.
    # The independent read hook establishes the address actually accessed.
    for private_word, voice_word in ((0x1234, 0x5678), (0x5678, 0x1234)):
        o.u.mem_write(private, struct.pack('<H', private_word))
        o.u.mem_write(voice, struct.pack('<H', voice_word))
        o.u.mem_write(dsp, bytes(0x800))
        o.put(dsp, private, 0, 0x8000)
        o.put(CHIP+0x1234, voice)
        o.u.mem_write(MPRO, program)
        samples = []
        for stage in ('start', 'redirect', 'restart'):
            if stage == 'redirect':
                write(o, 0x68e, 2, voice >> 16)
            else:
                write(o, 0xbfe, 2, 0)
                o.u.ctl_remove_cache(CODE_BUFFER, CODE_BUFFER + 0x10000)
            accesses.clear()
            o.run(0x4a9fa0, {UC_X86_REG_EAX:dsp})
            base = voice if stage == 'restart' else private
            value = voice_word if stage == 'restart' else private_word
            assert accesses == [(base, 2)], (stage, accesses)
            assert o.get(dsp)[0] == (private if stage == 'start' else voice)
            mems7 = o.get(dsp+0x6cc+7*4)[0]
            assert mems7 == value << 8
            samples.append(dict(stage=stage, register=hex(o.get(dsp)[0]),
                                read_address=hex(accesses[0][0]), mems7=hex(mems7)))
        results.append(dict(private_marker=hex(private_word), voice_marker=hex(voice_word),
                            observations=samples))
    return results


def dsp_address_registers(o):
    """Trace native DSP reads as the CPU changes ring length, page and MADRS."""
    dsp = CHIP + 0x123c
    private = 0x78000000
    o.u.mem_map(private + 0x1000, 0x2000)
    o.u.mem_write(dsp, bytes(0x800))
    o.put(dsp, private, 0, 2)
    o.u.mem_write(MPRO, instruction() + instruction(MRD=1) + instruction(IWT=1,IWA=7))
    write(o, 0x780, 2, 3)
    reads = []
    o.u.hook_add(UC_HOOK_MEM_READ, lambda u,kind,at,size,val,data: reads.append(at),
                 begin=private, end=private+0x2fff)
    rows = []
    for label, reg, value in (('start',0xbfe,0), ('length',0x694,4),
                              ('page',0x690,1), ('MADRS',0x780,2), ('restart',0xbfe,0)):
        write(o, reg, 2, value)
        if reg == 0xbfe:
            o.u.ctl_remove_cache(CODE_BUFFER, CODE_BUFFER + 0x10000)
        o.put(dsp+0x74c, 0)
        reads.clear()
        o.run(0x4a9fa0, {UC_X86_REG_EAX:dsp})
        assert len(reads) == 1
        rows.append(dict(stage=label, byte_offset=reads[0]-private))
    assert [row['byte_offset'] for row in rows] == [2, 6, 0x2006, 0x2004, 0x2004]
    return rows


def next_opcode(o):
    # MOVE D0,(A0) calls the real board. ST (A1) then passes the high bytes
    # of returned EAX to its write wrapper. Only the final observer is synthetic.
    cases = []
    for width, address, value, expected in ((1, 0x407, 0x5a, 1), (2, 0x780, 0xa35a, CHIP),
                                           (4, 0x7c0, 0x1122a35a, CHIP), (2, 0xbfe, 0, CODE_BUFFER),
                                           (2, 0xbfe, 0xa35a, 128),
                                           (2, 0x012, 0x7c00, 3),   # Both LFOs off.
                                           (2, 0x012, 0x7c20, 256), # Pitch only.
                                           (2, 0x012, 0x7c01, 256), # Amplitude only.
                                           (2, 0x012, 0x7c21, 256)):
        for host_flags in (0x202, 0x602):
            o.u.mem_write(CHIP + 0x123c, bytes(0x800))
            o.u.mem_write(MIDI_CURSOR, bytes(1))
            context = [0]*33
            context[0], context[8], context[9] = value, 0x100000 + address, 0x4321
            context[17], context[18], context[20] = 0x27, 0x202, 0x1000
            program = [{1:0x1080, 2:0x3080, 4:0x2080}[width], 0x50d1]
            trace, writes = o.stream(context, 1000, 0xabcdef01, host_flags, program, False)
            assert trace[1][36] == expected, (width, address, trace[1][36], expected)
            assert trace[1][37] == host_flags
            assert writes == [[0x4321, (expected & 0xffffff00) | 255]]
            cases.append(dict(width=width, offset=hex(address), host_flags=hex(host_flags),
                              value=hex(value), next_eax=hex(expected), st_argument=hex(writes[0][1])))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    oracle = ChainOracle(args.exe)
    oracle.put(0x5728bc, CHIP)
    oracle.put(WRITE+0x100*16, 0, 0x4afb00, 0x4afa20, 0x4af900)
    ring = ring_window(oracle)
    midi_cases = midi(oracle)
    dsp_cases, starts = dsp(oracle)
    redirected = dsp_ram_alias(oracle)
    geometry = dsp_address_registers(oracle)
    chains = next_opcode(oracle)
    result = dict(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                  ring_window=ring, dsp_ram_alias=redirected, dsp_address_registers=geometry, midi_cases=midi_cases, dsp_cases=dsp_cases, dsp_starts=starts,
                  next_instruction=chains, allocator_token=hex(CODE_BUFFER))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Passed {midi_cases} MIDI writes, {dsp_cases} DSP writes ({starts} starts), {len(chains)} MOVE/ST streams.')


if __name__ == '__main__':
    main()
