#!/usr/bin/env python3
"""Compare independently executing Model 1 sound boards from reset, through MIDI and PCM."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from model1_board_compare import AUDIO_RAM, BOARD, CTX, OUTPUT, initialize
from model1_mix_compare import ROOT, regions
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX


def bind(directory):
    shim = directory / 'shim.c'
    shim.write_text('#include "model1_board.c"\n'
                    'const void *context(const a68k_m1_board *b) { return &b->cpu.r; }\n')
    library = directory / 'board.so'
    files = ['a68k/a68k.c', 'a68k/model1_bus.c', 'a68k/divs_error_policy.c',
             'snd/model1_original.c', 'snd/fm_original.c', 'snd/multipcm_original.c']
    subprocess.run(['cc', '-std=c11', '-O2', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(ROOT/'port/a68k'), str(shim),
                    *(str(ROOT/'port'/f) for f in files), '-o', str(library)], check=True)
    lib = C.CDLL(str(library))
    ptr = C.c_void_p
    for name, params, result in [
            ('a68k_m1_create', [ptr, ptr, C.c_size_t, ptr, C.c_size_t, C.c_int], ptr),
            ('a68k_m1_free', [ptr], None), ('a68k_m1_reset', [ptr], None), ('context', [ptr], ptr),
            ('a68k_m1_begin', [ptr, C.c_uint], C.c_int), ('a68k_m1_scanline', [ptr], None),
            ('a68k_m1_command', [ptr, C.c_uint8], None),
            ('a68k_m1_error', [ptr, ptr, C.c_size_t], C.c_int),
            ('a68k_m1_finish', [ptr, ptr, ptr], None)]:
        func = getattr(lib, name)
        func.argtypes, func.restype = params, result
    return lib


def compare(exe, archive, frames, commands, resets):
    blobs = regions(archive)
    program = blobs['M1AUDIO_CPU_REGION']
    samples = blobs['M1AUDIO_MPCM1_REGION']
    native = initialize(exe, samples, program)
    if resets:
        # Execute the board's actual warm-reset wrapper. Only the main i960
        # reset is an external boundary here. Its two work buffers are separate
        # from the audio CPU RAM in this machine fixture.
        main_ram = 0x79000000
        native.u.mem_map(main_ram,0x140000)
        native.put(BOARD+0x203850,main_ram)
        native.put(BOARD+0x203858,main_ram+0x100000)
        native.u.hook_add(UC_HOOK_CODE,lambda *_:native.ret(),begin=0x4c3570,end=0x4c3570)
        native.u.ctl_flush_tb()
    width = 760
    with tempfile.TemporaryDirectory() as td:
        lib = bind(Path(td))
        ram = (C.c_uint8 * 65536)()
        board = lib.a68k_m1_create(ram, (C.c_uint8 * len(program)).from_buffer(program),
                                   len(program), (C.c_uint8 * len(samples)).from_buffer(samples),
                                   len(samples), 0)
        assert board
        context = lib.context(board)
        def check_context(frame, line):
            expected = native.get(CTX, 33)
            actual = struct.unpack('<33I', C.string_at(context, 132))
            if tuple(expected) != actual:
                raise ValueError((frame, line, [(i, hex(x), hex(y)) for i, (x, y)
                                                in enumerate(zip(expected, actual)) if x != y]))
        pcm = (C.c_int16 * (2*width))()
        gains = (C.c_uint * 4)(100, 100, 100, 100)
        error = C.create_string_buffer(256)
        digest = hashlib.sha256()
        active = 0
        try:
            check_context(-1, -1)
            for frame in range(frames):
                assert lib.a68k_m1_begin(board, width)
                if frame in resets:
                    native.run(0x4cad60,{UC_X86_REG_ECX:BOARD},count=3000000)
                    lib.a68k_m1_reset(board)
                    check_context(frame, -1)
                    assert bytes(ram) == native.u.mem_read(AUDIO_RAM, len(ram))
                for value in commands.get(frame, []):
                    native.run(0x4c8660, {UC_X86_REG_ECX: value})
                    lib.a68k_m1_command(board, value)
                for line in range(210):
                    native.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
                    lib.a68k_m1_scanline(board)
                    assert not lib.a68k_m1_error(board, error, len(error)), (frame, line, error.value)
                    check_context(frame, line)
                assert native.u.mem_read(AUDIO_RAM, len(ram)) == bytes(ram), ('sound RAM', frame)
                native.run(0x4a9d70, count=10000000)
                for chip in range(2):
                    native.run(0x4affb0, {UC_X86_REG_EAX: chip}, count=10000000)
                lib.a68k_m1_finish(board, pcm, gains)
                assert not lib.a68k_m1_error(board, error, len(error)), (frame, error.value)
                for channel, offset in enumerate((0x68, 0x2b178)):
                    plane = struct.unpack('<' + 'h'*width, native.u.mem_read(OUTPUT+offset, 2*width))
                    assert tuple(pcm[channel::2]) == plane, ('PCM', frame, channel)
                digest.update(bytes(pcm))
                active += sum(bool(left or right) for left, right in zip(pcm[::2], pcm[1::2]))
        finally:
            lib.a68k_m1_free(board)
    return dict(title=archive.stem, frames=frames, scanline_contexts=frames*210,
                stereo_frames=frames*width, active_stereo_frames=active, commands=commands, resets=resets,
                reset_witness='original board vtable +0x14' if resets else None,
                pcm_sha256=digest.hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--frames', type=int, required=True)
    parser.add_argument('--command', action='append', default=[], help='frame:hex-byte,hex-byte')
    parser.add_argument('--reset', type=int, action='append', default=[])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    commands = {}
    for event in args.command:
        frame, values = event.split(':')
        commands.setdefault(int(frame), []).extend(int(v, 16) for v in values.split(','))
    report = json.dumps(compare(args.exe, args.archive, args.frames, commands, args.reset), indent=2)
    if args.output:
        args.output.write_text(report + '\n')
    print(report)
