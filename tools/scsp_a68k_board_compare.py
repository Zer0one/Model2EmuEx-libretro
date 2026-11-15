#!/usr/bin/env python3
"""Run guest interrupt routines through the recovered A68K, SCSP and board clock."""
import argparse
import ctypes as C
import hashlib
import json
import runpy
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from a68k_boundary_compare import CTX, RAM, SP, Oracle
from scsp_board_exchange_probe import (ACCUMULATOR, BOARD, BUDGET, guest_words,
                                       init_scsp_exchange, init_sound_cpu)
from scsp_control_compare import CHIP, ROOT
from scsp_slot_write_compare import write
from scsp_write_exchange_probe import bind_test_allocator
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX, UC_X86_REG_EFLAGS, UC_X86_REG_ESI, UC_X86_REG_ESP

U8, U32 = C.c_uint8, C.c_uint32


def configure(lib):
    ptr = C.c_void_p
    lib.scsp_board_test_create.argtypes = [C.POINTER(U8), U32]
    lib.scsp_board_test_cold_state.argtypes = [ptr, C.POINTER(U32), C.POINTER(U8)]
    lib.scsp_board_test_create.restype = ptr
    lib.scsp_board_test_command.argtypes = [ptr, U8]
    lib.scsp_board_test_write.argtypes = [ptr, U32, C.c_uint16]
    lib.scsp_board_test_scanline.argtypes = [ptr, U32, U32, C.POINTER(U32)]
    lib.scsp_board_test_destroy.argtypes = [ptr]
    lib.scsp_board_test_rom.argtypes = [ptr, C.POINTER(U8), U32, C.POINTER(U8), U32]
    lib.scsp_board_test_registers.argtypes = [ptr, C.POINTER(U8)]
    lib.scsp_board_test_code_address.argtypes = [ptr, U32]
    lib.scsp_board_test_boot.argtypes = [ptr]
    lib.scsp_board_test_reset.argtypes = [ptr]


def cold_board(o, lib, ram):
    board = lib.scsp_board_test_create(ram, RAM)
    assert board and lib.scsp_board_test_boot(board) == 0
    context, costs = (U32 * 33)(), (U8 * 256)()
    lib.scsp_board_test_cold_state(board, context, costs)
    assert list(context) == o.get(CTX, 33)
    assert list(costs) == o.cost
    return board


def compare(exe, lib, hz, gate, stop, commands, clear_first, guest_reset=False, mask_timer=False):
    o = Oracle(exe)
    assert o.get(0x1048250, 32) == [0] * 32
    init_sound_cpu(o)
    init_scsp_exchange(o, hz)
    guest_words(o, 0x78, 0, 0x200)
    guest_words(o, 0x6c, 0, 0x240)
    status = (0x4e72, 0x2000) if stop else (0x46fc, 0x2000)
    guest_words(o, 0x100, *((0x4e70,) if guest_reset else ()), 0x207c, 0, 0x2000, *status, 0x60fe)
    guest_words(o, 0x200, 0x30f9, 0x10, 0x404, 0x4e73)
    reload_timer = (0x33fc, 0, 0x10, 0x418)
    clear_timer = (0x33fc, 0x40, 0x10, 0x422)
    updates = clear_timer + reload_timer if clear_first else reload_timer + clear_timer
    guest_words(o, 0x240, 0x30f9, 0x10, 0x420, *updates, 0x4e73)
    ram = (U8 * 0x100000)()
    ram[:0x9000] = bytes(o.u.mem_read(RAM, 0x9000))
    board = cold_board(o, lib, ram)
    digest = hashlib.sha256()
    try:
        # TimA level 3, MIDI level 6. Use actual guest register callbacks.
        for offset, value in ((0x424, 0x40), (0x426, 0x48), (0x428, 8),
                              (0x418, 0xfe), (0x41e, 0 if mask_timer else 0x40)):
            write(o, offset, 2, value)
            lib.scsp_board_test_write(board, offset, value)
        for byte in range(1, commands + 1):
            o.run(0x4c868a, {UC_X86_REG_ECX: byte}, stops=(0x4c86a8,))
            lib.scsp_board_test_command(board, byte)
        o.put(0x10482a4, gate)
        for line in range(18):
            o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=100000)
            out = (U32 * 43)()
            status = lib.scsp_board_test_scanline(board, hz, gate, out)
            assert status == 0, (hz, line, status, hex(out[20]), hex(out[35]))
            expected = o.get(CTX, 33) + o.get(ACCUMULATOR) + o.get(BUDGET)
            assert list(out[:35]) == expected, (hz, gate, stop, commands, clear_first, line,
                [(i,hex(v),hex(e)) for i,(v,e) in enumerate(zip(out,expected)) if v != e])
            # Includes reset vectors, guest code, interrupt stack and all output words.
            native = bytes(o.u.mem_read(RAM, 0x9000))
            assert bytes(ram[:0x9000]) == native, (line, 'guest RAM')
            digest.update(bytes(out)[:35*4])
            digest.update(native)
        count = (out[8] - 0x2000)//2 if out[8] else 0
        assert count == (0 if gate == 0x80 or mask_timer else commands + 1 + int(clear_first)), (count, commands)
        return dict(hz=hz, template_irq=gate, guest_reset=guest_reset, guest_stop=stop, masked_timer=mask_timer, commands=commands, clear_first=clear_first,
                    scanlines=18, guest_words=count, sha256=digest.hexdigest())
    finally:
        lib.scsp_board_test_destroy(board)


def dsp_start_from_guest(exe, lib, words):
    """Exercise the real register callback from a guest store through DSP Start."""
    o = Oracle(exe)
    init_sound_cpu(o)
    init_scsp_exchange(o, 58)
    code = 0x77000000
    o.u.mem_map(code, 0x10000)
    bind_test_allocator(o, code)
    o.put(CHIP + 0x123c, 0x78000000, 0, 0x8000)
    o.u.mem_write(CHIP + 0x123c + 0x7b4, b'\x01')
    guest_words(o, 0x100, 0x207c, 0x10, 0xbfe, 0x7000, *words, 0x60fe)
    ram = (U8 * 0x100000)()
    ram[:0x9000] = bytes(o.u.mem_read(RAM, 0x9000))
    board = cold_board(o, lib, ram)
    starts = []
    def completed(cpu, address, size, user):
        starts.append((cpu.reg_read(UC_X86_REG_EAX), cpu.reg_read(UC_X86_REG_EFLAGS)))
    o.u.hook_add(UC_HOOK_CODE, completed, begin=0x4aa7ee, end=0x4aa7ee)
    o.u.ctl_flush_tb()
    try:
        lib.scsp_board_test_code_address(board, code)
        out = (U32 * 43)()
        o.run(0x4cc710, {UC_X86_REG_EAX: BOARD}, count=200000)
        status = lib.scsp_board_test_scanline(board, 58, 0, out)
        assert status == 0 and starts == [tuple(out[38:40])] and out[37] == 1, (
            words, status, starts, list(out[35:40]))
        assert list(out[:35]) == o.get(CTX, 33) + o.get(ACCUMULATOR) + o.get(BUDGET)
        assert bytes(ram[:0x9000]) == bytes(o.u.mem_read(RAM, 0x9000))
        return dict(opcode=hex(words[0]), eax=hex(out[38]), eflags=hex(out[39]))
    finally:
        lib.scsp_board_test_destroy(board)


def rom_reset(exe, lib, hz):
    o = Oracle(exe)
    assert o.get(0x1048250, 32) == [0] * 32
    init_sound_cpu(o)
    init_scsp_exchange(o, hz)
    program_addr, sample_addr = 0x74000000, 0x75000000
    o.u.mem_map(program_addr, 0x80000)
    o.u.mem_map(sample_addr, 0x2000)
    def rom_words(region, offset, *words):
        o.u.mem_write(region + offset, struct.pack('<' + 'H'*len(words), *words))
    rom_words(program_addr, 0, 0, 0x8400, 0x60, 0x100)
    # Read a sample word, attempt to overwrite program ROM, then jump
    # between two different pages and execute from the sample ROM itself.
    rom_words(program_addr, 0x100, 0x33f9, 0x80, 0, 0, 0x2400,
              0x33fc, 0xbaad, 0x60, 0x180, 0x4ef9, 0x60, 0x1100)
    rom_words(program_addr, 0x180, 0x1234)
    rom_words(program_addr, 0x1100, 0x4ef9, 0x80, 0x1000)
    rom_words(sample_addr, 0, 0xcafe)
    rom_words(sample_addr, 0x1000, 0x46fc, 0x2000, 0x60fe)
    guest_words(o, 0x78, 0, 0x200)
    guest_words(o, 0x200, 0x33f9, 0x10, 0x404, 0, 0x2402, 0x4e73)
    # Run the original board's map installers, including all ROM callbacks.
    device = BOARD + 0x400
    o.put(device+0x28, program_addr, 0x80000, sample_addr, 0x2000)
    # This field is well outside the small fixture board; use a separate object.
    host_board = 0x76000000
    o.u.mem_map(host_board, 0x204000)
    o.put(host_board+4, device)
    o.put(host_board+0x20389c, RAM)
    o.run(0x4cd0f9, {UC_X86_REG_EBP:host_board, UC_X86_REG_EBX:0, UC_X86_REG_ESI:0},
          stops=(0x4cd2d2,), count=1000000)
    buffers = [(U8*size).from_buffer_copy(bytes(o.u.mem_read(addr,size))) for addr,size in
               ((program_addr,0x80000),(sample_addr,0x2000))]
    ram = (U8*0x100000)()
    ram[:0x9000] = bytes(o.u.mem_read(RAM,0x9000))
    board = cold_board(o, lib, ram)
    try:
        assert lib.scsp_board_test_rom(board, buffers[0], len(buffers[0]), buffers[1], len(buffers[1]))
        for offset in (0x426, 0x428):
            write(o,offset,2,8)
            lib.scsp_board_test_write(board,offset,8)
        o.run(0x4c868a,{UC_X86_REG_ECX:0x59},stops=(0x4c86a8,))
        lib.scsp_board_test_command(board,0x59)
        out = (U32*43)()
        # Establish a live IRQ and nonzero clock phase, still in the RAM boot fixture.
        o.put(0x10482a4, 0x80)
        o.run(0x4cc710,{UC_X86_REG_EAX:BOARD},count=100000)
        assert lib.scsp_board_test_scanline(board,hz,0x80,out) == 0
        assert out[21] == 6 and out[33] == o.get(ACCUMULATOR)[0] != 0
        # Only the sound portion of the full board reset is relevant here.
        o.run(0x4cad80, {UC_X86_REG_EDI:host_board}, stops=(0x4cad9b,))
        o.run(0x4b33a0)
        assert lib.scsp_board_test_reset(board) == 0
        o.put(0x10482a4,0)
        for line in range(4):
            o.run(0x4cc710,{UC_X86_REG_EAX:BOARD},count=100000)
            assert lib.scsp_board_test_scanline(board,hz,0,out) == 0, (line,list(out))
            expected = o.get(CTX,33) + o.get(ACCUMULATOR) + o.get(BUDGET)
            assert list(out[:35]) == expected, [(i,hex(v),hex(e)) for i,(v,e) in enumerate(zip(out,expected)) if v!=e]
            assert bytes(ram[:0x9000]) == bytes(o.u.mem_read(RAM,0x9000))
        assert bytes(ram[0x2400:0x2404]) == struct.pack('<HH',0xcafe,0x59)
        assert out[20] == 0x801004
        for buf, addr in zip(buffers,(program_addr,sample_addr)):
            assert bytes(buf) == bytes(o.u.mem_read(addr,len(buf)))
        assert bytes(buffers[0][0x180:0x182]) == bytes.fromhex('3412')
        return dict(fps=hz, final_pc=hex(out[20]), sample_word='cafe', queued_command='59',
                    continuation_scanlines=4, protected_program_word='1234')
    finally:
        lib.scsp_board_test_destroy(board)


def compare_chip(o, lib, board, title, line):
    slots = o.u.mem_read(CHIP+0x30, 32*0x8c)
    banks = (
        ('global', o.u.mem_read(CHIP, 0x30)),
        ('slot', b''.join(slots[i*0x8c:i*0x8c+32] for i in range(32))),
        ('ring', o.u.mem_read(CHIP+0x11b0, 128)),
        ('DSP registers', o.u.mem_read(CHIP+0x1248, 128+64+1024)),
        ('MIDI input', o.u.mem_read(0x10c35b0, 128)),
        ('MIDI output', o.u.mem_read(0x10be458, 128)),
        ('output cursor/count', o.u.mem_read(0x10ed99f, 1) + o.u.mem_read(0x107879a, 1)),
        ('voice/DSP base', o.u.mem_read(CHIP+0x1234,4) + o.u.mem_read(CHIP+0x123c,4)),
    )
    actual = (U8 * sum(len(data) for _, data in banks))()
    lib.scsp_board_test_registers(board, actual)
    at = 0
    for name, expected in banks:
        got = bytes(actual[at:at+len(expected)])
        assert got == expected, (title, line, name,
            [(i, v, w) for i, (v,w) in enumerate(zip(got, expected)) if v != w][:8])
        at += len(expected)
    return bytes(actual)


def sound_regions(archive, region_names=None, aliases=None):
    if region_names is None:
        region_names = {5: 'audiocpu', 6: 'samples'}
    catalog = json.loads((ROOT / 'src/libretro/data/mame_model2_catalog.json').read_text())
    game = next(game for game in catalog['games'] if game['name'] == archive.stem)
    # MAME supplies chip identities. The 1.1a descriptors supply the board
    # layout, including empty space. Rail Chase 2 maps its second 2 MiB
    # chip at 0x200000 here, while MAME lists it at 0x400000.
    parse_native = runpy.run_path(str(ROOT / 'scripts/align-mame-romsets.py'))['parse_native']
    for path in ('port/m2/gamedb.inc', 'src/libretro/data/gamedb_model2b_recovered.inc',
                 'src/libretro/data/gamedb_model2c_recovered.inc'):
        arrays, _ = parse_native((ROOT / path).read_text())
        if game['native_name'] in arrays:
            entries = arrays[game['native_name']]
            break
    else:
        raise ValueError(f"No recovered 1.1a ROM descriptor for {archive.stem}")
    aliases = aliases or {}
    expected = {(aliases.get(f['region'],f['region']), f['crc'], f['size']) for f in game['mame_files']
                if aliases.get(f['region'],f['region']) in region_names.values()}
    loaded = set()
    regions = {}
    region = None
    with zipfile.ZipFile(archive) as roms:
        for kind, _, arg, offset, size, crc, flags in entries:
            if kind == 0:
                region = region_names.get(arg & 255)
                if region:
                    regions[region] = bytearray(offset)
            elif region and kind == 1:
                if (region, crc, size) not in expected or flags & 0xff00:
                    raise ValueError(f"Unsupported {region} chip layout in {archive.stem}")
                if offset + size > len(regions[region]):
                    raise ValueError(f"{region} chip exceeds the original region")
                member = next(i for i in roms.infolist() if (i.CRC, i.file_size) == (crc, size))
                regions[region][offset:offset+size] = roms.read(member)
                loaded.add((region, crc, size))
            elif region and kind == 5 and arg == 0x4f77b0:
                # The original descriptor invokes a word swap on the whole
                # current region. A trailing odd byte is outside the loop.
                data = regions[region]
                stop = len(data) & ~1
                data[:stop:2], data[1:stop:2] = data[1:stop:2], data[:stop:2]
            elif region and kind not in (-1, 4):
                raise ValueError(f"Unsupported original audio region operation {kind}")
    if loaded != expected or set(regions) != set(region_names.values()):
        raise ValueError(f"Incomplete original audio regions for {archive.stem}")
    return regions


def title_boot(exe, lib, archive, scanlines, expect_start, code_buffer=0x77000000, midi_at=None):
    """Compare both CPUs from reset with identical ROMs and numeric map bases."""
    regions = sound_regions(archive)
    o = Oracle(exe)
    # Keep the synthetic machine object away from the entire sound RAM.
    native_ram, host_board = 0x73000000, 0x76000000
    program_addr, sample_addr = 0x74000000, 0x75000000
    o.u.mem_map(native_ram, 0x100000)
    o.u.mem_map(host_board, 0x204000)
    buffers = []
    for address, region in ((program_addr, 'audiocpu'), (sample_addr, 'samples')):
        backing = regions[region]
        o.u.mem_map(address, len(backing))
        o.u.mem_write(address, bytes(backing))
        buffers.append((U8 * len(backing)).from_buffer(backing))
    o.u.mem_map(code_buffer, 0x10000)
    bind_test_allocator(o, code_buffer)
    init_scsp_exchange(o, 60)
    device = BOARD + 0x400
    o.put(device + 0x28, program_addr, len(buffers[0]), sample_addr, len(buffers[1]))
    o.put(host_board + 4, device)
    o.put(host_board + 0x20389c, native_ram)
    o.run(0x4cd0f9, {UC_X86_REG_EBP:host_board, UC_X86_REG_EBX:0, UC_X86_REG_ESI:0},
          stops=(0x4cd326,), count=1000000)
    o.put(CHIP + 0x1234, native_ram)
    o.put(CHIP + 0x123c, 0x78000000, 0, 0x8000)
    o.u.mem_write(CHIP + 0x123c + 0x7b4, b'\x01')
    ram = (U8 * 0x100000)()
    ram[:8] = regions['audiocpu'][:8]
    board = lib.scsp_board_test_create(ram, native_ram)
    assert board
    try:
        assert lib.scsp_board_test_rom(board, buffers[0], len(buffers[0]), buffers[1], len(buffers[1]))
        assert lib.scsp_board_test_boot(board) == 0
        context, costs = (U32 * 33)(), (U8 * 256)()
        lib.scsp_board_test_cold_state(board, context, costs)
        assert list(context) == o.get(CTX, 33) and list(costs) == o.cost
        out = (U32 * 43)()
        # Guest execution now uses only native callbacks and full scanlines.
        o.u.hook_del(o.code_hook)
        starts = []
        pointer_writes = [0,0]
        def observe_pointer(u, kind, at, size, value, index):
            pointer_writes[index] += 1
        for index, field in enumerate((0x1234, 0x123c)):
            o.u.hook_add(UC_HOOK_MEM_WRITE, observe_pointer, user_data=index,
                         begin=CHIP+field, end=CHIP+field+3)

        if code_buffer != 0x77000000:
            lib.scsp_board_test_code_address(board, code_buffer)
        def observe_start(u, at, size, user):
            starts.append(dict(line=line+1, steps=o.get(CHIP+0x123c+0x7b8)[0],
                               eax=hex(u.reg_read(UC_X86_REG_EAX)),
                               flags=hex(u.reg_read(UC_X86_REG_EFLAGS))))
        o.u.hook_add(UC_HOOK_CODE, observe_start, begin=0x4aa7ee, end=0x4aa7ee)
        o.u.ctl_flush_tb()
        midi = {}
        chip_digest = hashlib.sha256()
        for line in range(scanlines):
            if line+1 == midi_at:
                # Same bounded i960 enqueue fragment used in the board IRQ
                # fixture. It pushes ESI; the next scanline sets its own SP.
                cursor = o.u.mem_read(0x10ed9d8, 2)
                assert cursor[0] == cursor[1], (archive.stem, 'queue not empty', cursor)
                o.u.reg_write(UC_X86_REG_ESP, SP)
                o.u.reg_write(UC_X86_REG_ECX, 0x59)
                o.u.emu_start(0x4c868a, 0x4c86a8)
                lib.scsp_board_test_command(board, 0x59)
                midi = dict(value=0x59, sent=line+1, read_cursor_before=cursor[1])
            status = lib.scsp_board_test_scanline(board, 60, 0, out)
            assert not status, (archive.stem, line+1, 'CPU boundary', status, hex(out[35]), hex(out[36]))
            o.run(0x4cc710, {UC_X86_REG_EAX:BOARD}, count=200000)
            assert list(out[41:43]) == pointer_writes, (archive.stem, line+1, 'RAM pointer writes')
            assert out[37] == len(starts), (archive.stem, line+1, 'DSP start count', out[37], starts)
            if starts and starts[-1]['line'] == line+1:
                assert [hex(v) for v in out[38:40]] == [starts[-1]['eax'], starts[-1]['flags']], (
                    archive.stem, starts[-1], [hex(v) for v in out[38:40]])
            expected = o.get(CTX, 33) + o.get(ACCUMULATOR) + o.get(BUDGET)
            assert list(out[:35]) == expected, (archive.stem, line, 'CPU/clock',
                [(i, hex(v), hex(e)) for i, (v, e) in enumerate(zip(out, expected)) if v != e])
            fifo = o.u.mem_read(0x10ed9d8, 2) + o.u.mem_read(0x1078799, 1)
            assert out[40] == int.from_bytes(fifo, 'little'), (archive.stem, line+1, 'MIDI FIFO', out[40], fifo)
            if midi and 'consumed' not in midi:
                cursor = fifo[1]
                if cursor != midi['read_cursor_before']:
                    assert cursor == (midi['read_cursor_before']+1) % 128
                    midi['consumed'] = line+1
            context[:] = out[:33]
            if (line+1) % 210 == 0 or line+1 == scanlines:
                chip_digest.update(compare_chip(o, lib, board, archive.stem, line+1))
                assert bytes(ram) == bytes(o.u.mem_read(native_ram, len(ram))), (archive.stem, line, 'RAM')
        assert starts or not expect_start, "Expected DSP Start was not reached"
        assert midi_at is None or 'consumed' in midi, (archive.stem, midi)
        return dict(title=archive.stem, midi=midi, voice_dsp_pointer_writes=pointer_writes, scanlines=scanlines, hz=60, final_pc=hex(out[20]),
                    original_dsp_start=starts, guest_context=list(context), chip_trace_sha256=chip_digest.hexdigest(),
                    ram_sha256=hashlib.sha256(ram).hexdigest())
    finally:
        lib.scsp_board_test_destroy(board)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path, help='Read a parent sound program and samples directly from its existing ZIP')
    parser.add_argument('--scanlines', type=int, default=210)
    parser.add_argument('--midi-at', type=int, metavar='SCANLINE', help='Inject one test byte (0x59) and require guest consumption')
    parser.add_argument('--expect-dsp-start', action='store_true', help='Require a DSP start and repeat with a second virtual code address')
    args = parser.parse_args()
    if args.expect_dsp_start and not args.archive:
        parser.error('--expect-dsp-start requires --archive')
    if args.midi_at is not None and (not args.archive or not 1 <= args.midi_at <= args.scanlines):
        parser.error('--midi-at requires an archive and a scanline in the requested interval')
    if args.scanlines <= 0:
        parser.error('Expected a positive scanline count')
    sources = ['port/a68k/test/scsp_board_shim.c', 'port/a68k/a68k.c', 'port/a68k/scsp_bus.c',
               'port/snd/scsp_dsp_original.c']
    with tempfile.TemporaryDirectory(prefix='scsp-a68k-board-') as temp:
        path = Path(temp) / 'board.dylib'
        subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
                        *sources, '-lm', '-o', str(path)], cwd=ROOT, check=True)
        lib = C.CDLL(str(path))
        configure(lib)
        rows = [compare(args.exe, lib, hz, gate, stop, commands, clear) for hz in (58,60)
                for gate,stop,commands,clear in ((0,False,0,False),(0,False,0,True),
                    (0,False,40,False),(0,True,3,False),(0x80,False,3,False))]
        rows.extend(compare(args.exe, lib, hz, 0, False, 3, False, True) for hz in (58, 60))
        rows.extend(compare(args.exe, lib, hz, 0, True, 0, False, mask_timer=True) for hz in (58, 60))
        game = title_boot(args.exe, lib, args.archive, args.scanlines, args.expect_dsp_start, midi_at=args.midi_at) if args.archive else None
        if args.expect_dsp_start:
            other = title_boot(args.exe, lib, args.archive, args.scanlines, True, 0x79000000, args.midi_at)
            assert game['ram_sha256'] == other['ram_sha256'] and game['guest_context'] == other['guest_context']
            game['second_allocation'] = other['original_dsp_start']
        # Word stores with distinct emitter frames, including a read/modify/write
        # and a register-list store. Each must return to the actual A68K handler.
        store_starts = [dsp_start_from_guest(args.exe, lib, words) for words in
                        ((0x3080,), (0x4250,), (0x0250, 0), (0x4890, 1), (0xe3d0,))]
        reset = [rom_reset(args.exe, lib, hz) for hz in (58,60)]
    result = dict(title_boot=game, dsp_guest_stores=store_starts, rom_reset=reset, original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(), cases=rows)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Passed {len(rows)} board scenarios, {sum(row["scanlines"] for row in rows)} scanline comparisons, {len(reset)} warm resets.')


if __name__ == '__main__':
    main()
