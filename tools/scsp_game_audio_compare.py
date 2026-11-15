#!/usr/bin/env python3
"""Replay real i960 audio commands in the pinned ElSemi SCSP board and compare native-rate PCM."""
import argparse
from collections import defaultdict
from itertools import chain, zip_longest
import hashlib
import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX,
                               UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_ESP)
from a68k_boundary_compare import Oracle
from scsp_a68k_board_compare import sound_regions
from scsp_board_exchange_probe import BOARD, init_scsp_exchange, initialize_chip
from scsp_control_compare import CHIP
from scsp_write_exchange_probe import bind_test_allocator


def initialize(exe, archive, alternate):
    o = Oracle(exe)
    work = initialize_chip(o)
    program, samples, machine = 0x74000000, 0x75000000, 0x76000000
    ram, code, private = 0x73000000, 0x77000000, 0x78000000
    regions = sound_regions(archive)
    for name, base in [('audiocpu', program), ('samples', samples)]:
        o.u.mem_map(base,len(regions[name]))
        o.u.mem_write(base,bytes(regions[name]))
    for base, size in [(ram,0x100000), (code,0x10000), (private,0x100000),
                       (machine,0x204000)]:
        o.u.mem_map(base,size)
    bind_test_allocator(o,code)
    init_scsp_exchange(o,58)
    device = BOARD+0x400
    o.put(device+0x28, program,len(regions['audiocpu']),samples,len(regions['samples']))
    o.put(BOARD+4,device)
    o.put(BOARD+0x18,BOARD+0x1000)  # Optional machine profiling is off.
    o.put(0x5aa730,BOARD)
    o.put(machine+4,device)
    o.put(machine+0x20389c,ram)
    o.run(0x4cd0f9,{UC_X86_REG_EBP:machine,UC_X86_REG_EBX:0,UC_X86_REG_ESI:0},
          stops=(0x4cd326,),count=1000000)
    o.put(CHIP+0x1234,ram)
    o.put(CHIP+0x123c,private,0,0x8000)
    o.u.mem_write(CHIP+0x123c+0x7b4,b'\x01')
    o.u.mem_write(0x10ed99e,bytes([alternate]))
    o.put(0x10bf558,work+0x70000,work+0x74000)
    o.u.ctl_flush_tb()
    return o,work


def bind_digital_board(o, archive):
    """Run the original optional-board installer against the same output planes as SCSP."""
    kind = {'stcc': 1, 'topskatr': 2}[archive.stem]
    region = 'dsbz80' if kind == 1 else 'dsb2'
    roms = sound_regions(archive, {7: region + ':mpegcpu', 8: region + ':mpeg'})
    device = o.get(BOARD+4)[0]
    # 004cd405 derives its output pointers from one machine output object.
    # The right plane starts 0x2b110 bytes after the left, exactly as on Windows.
    output = 0x7b000000
    o.u.mem_map(output, 0xb0000)
    o.put(BOARD+0x14, output)
    o.put(BOARD+0x28, 760)
    o.put(output+0xac4a8, 44100)
    o.put(device+0x104, kind)
    for address, key, field in ((0x7c000000, 'mpegcpu', 0x38), (0x7d000000, 'mpeg', 0x40)):
        data = roms[region + ':' + key]
        o.u.mem_map(address, len(data))
        o.u.mem_write(address, bytes(data))
        o.put(device+field, address)
    o.run(0x4cd3b2, {UC_X86_REG_EBP: BOARD, UC_X86_REG_EBX: 0}, stops=(0x4cd432,), count=5000000)
    assert o.get(0x107877c)[0] == o.get(0x10bf558)[0] == output+0x68
    assert o.get(0x1078784)[0] == o.get(0x10bf55c)[0] == output+0x2b178
    assert o.get(0x10787b4)[0] == 44100 and o.get(0x1078760)[0] == 760


def mix_block(o, count):
    o.put(0x10bfd60,count)
    o.put(0x1078760,count)
    o.run(0x4cc4a0,{UC_X86_REG_ECX: BOARD},count=20000000)
    channels = [struct.unpack(f'<{count}h',o.u.mem_read(ptr,2*count)) for ptr in o.get(0x10bf558,2)]
    return struct.pack(f'<{2*count}h',*chain.from_iterable(zip(*channels)))


def compare(args):
    o,_ = initialize(args.exe,args.archive,args.interleaved)
    if args.include_dsb:
        bind_digital_board(o, args.archive)
    o.u.hook_del(o.code_hook)
    dsb_frames = 0
    commands = defaultdict(list)
    expected_irq = []
    # State-test logs continue with replay and resets after the initial run.
    for line in args.trace.read_text().splitlines():
        if line.startswith('A68K_'):
            event, at, value = line.split()
            if int(at) > args.frames * 210:
                break
            if event == 'A68K_COMMAND':
                commands[int(at)].append(int(value))
            elif event == 'A68K_IRQ':
                expected_irq.append((int(at),int(value)))

    if not expected_irq or not commands:
        raise ValueError("Expected a cold-boot trace with live commands and interrupts")

    actual_irq = []
    def irq(u, at, size, data):
        # Live acknowledge 004b3090 is called with the accepted level on the stack.
        actual_irq.append((scanline,o.get(u.reg_read(UC_X86_REG_ESP)+4)[0]))
    o.u.hook_add(UC_HOOK_CODE,irq,begin=0x4b3090,end=0x4b3090)
    dual_flag = 0x10ed9da
    dual_stores = []
    def record_count_store(u, kind, at, size, value, data):
        if at <= dual_flag < at + size:
            dual_stores.append((at, size, value))
    o.u.hook_add(UC_HOOK_MEM_WRITE, record_count_store, begin=dual_flag-15, end=dual_flag)
    assert not o.u.mem_read(dual_flag, 1)[0]
    o.u.ctl_flush_tb()
    core = args.pcm.read_bytes()
    first = None
    first_native = None
    native_hash = hashlib.sha256()
    offset = 0
    compared_samples = 0
    core_hash = hashlib.sha256()
    debt = 0.0
    differences = 0
    for frame in range(args.frames):
        debt += 44100 / 58
        frontend_count = int(debt)
        debt -= frontend_count
        core_count = 760 if args.capture_fixed else frontend_count
        # Compare corresponding samples inside each machine frame. A capture
        # from the stock adapter may have one extra sample on that frame.
        count = 760 if args.windows_block else core_count
        if frame + 1 == args.split_mixer_frame:
            # Keep the incoming CPU/chip state and command clock identical.
            # Change only the mixer's call size for this one machine frame.
            native = b''.join(mix_block(o, 1) for _ in range(count))
            o.put(0x10bfd60,count)
        else:
            native = mix_block(o, count)
        if args.include_dsb and o.get(0x1078790)[0]:
            dsb_frames += 1
        native_hash.update(native)
        block = core[4*offset:4*(offset+count)]
        if len(block) != len(native):
            raise ValueError("Native-rate PCM capture is shorter than the requested interval")
        core_hash.update(block)
        if block != native or first_native is None:
            for i,(want,got) in enumerate(zip(struct.iter_unpack('<hh',native),struct.iter_unpack('<hh',block))):
                if want != (0,0) and first_native is None:
                    first_native = compared_samples+i
                if want != got:
                    differences += 1
                    if first is None:
                        first = dict(frame=frame+1,sample=compared_samples+i,original=want,core=got)
        compared_samples += count
        offset += core_count
        for scanline in range(frame*210+1,(frame+1)*210+1):
            for command in commands.get(scanline,()):
                o.run(0x4c8660, {UC_X86_REG_ECX: command})
            o.run(0x4cc710,{UC_X86_REG_EAX:BOARD},count=200000)
    irq_diff = next(((a,b) for a,b in zip_longest(actual_irq,expected_irq) if a!=b),None)
    return dict(game=args.archive.stem,frames=args.frames,samples=compared_samples,commands=sum(map(len,commands.values())),
                original_irqs=len(actual_irq),core_irqs=len(expected_irq),irq_exact=actual_irq==expected_irq,
                first_irq_difference=irq_diff,first_native_nonzero=first_native,first_pcm_difference=first,
                different_stereo_samples=differences,interleaved=args.interleaved,
                split_mixer_frame=args.split_mixer_frame, native_block_policy="Windows 760" if args.windows_block else "frontend 760/761",
                dual_flag_guest_stores=dual_stores, frontend_samples=offset, dsb_active_blocks=dsb_frames,
                original_pcm_sha256=native_hash.hexdigest(),core_pcm_sha256=core_hash.hexdigest())


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('exe','archive','trace','pcm'):
        ap.add_argument(name,type=Path)
    ap.add_argument('--frames',type=int,required=True)
    ap.add_argument('--interleaved',action='store_true',help='Use the alternate original mixer')
    ap.add_argument('--include-dsb',action='store_true',help='Mix the original digital board after the original primary SCSP')
    ap.add_argument('--capture-fixed', action='store_true', help='Input capture was generated by a fixed 760-sample diagnostic build')
    ap.add_argument('--windows-block', action='store_true', help='Use the fixed 760-sample ElSemi block measured on Windows at 58 Hz; compare the shared prefix per frame')
    ap.add_argument('--split-mixer-frame',type=int,metavar='N',
                    help='Diagnostic only: mix frame N in one-sample calls, keeping CPU timing fixed')
    args = ap.parse_args()
    if args.archive.stem not in ('srallyc', 'skisuprg', 'vf2', 'rchase2', 'stcc', 'lastbrnx', 'waverunr', 'hotdo', 'manxtt', 'manxttc', 'topskatr'):
        ap.error("Choose a supported ROM set with a single SCSP sound board")
    if args.include_dsb and args.archive.stem not in ('stcc', 'topskatr'):
        ap.error('--include-dsb requires a recovered DSB parent')
    if args.capture_fixed and not args.windows_block:
        ap.error('--capture-fixed requires --windows-block')
    if args.frames <= 0:
        ap.error("frames must be positive")
    if args.split_mixer_frame is not None and not 1 <= args.split_mixer_frame <= args.frames:
        ap.error("split mixer frame must lie within the requested interval")
    print(json.dumps(compare(args),indent=2))
