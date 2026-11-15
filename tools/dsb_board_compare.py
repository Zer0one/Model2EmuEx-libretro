#!/usr/bin/env python3
"""Trace the optional ElSemi digital sound board from its command port to stereo PCM."""
import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from itertools import chain
from collections import Counter

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_FPCW
from a68k_boundary_compare import Oracle, SP
from scsp_a68k_board_compare import sound_regions

# Object fields bound at 004cd3e4..004cd42c.
PROGRAM, MUSIC, OUT = 0x76000000, 0x78000000, 0x75000000
FAMILIES = {1: 'dsbz80', 2: 'dsb2'}


def native_board(exe, archive, kind):
    region = FAMILIES[kind]
    data = sound_regions(archive, {7: region + ':mpegcpu', 8: region + ':mpeg'})
    o = Oracle(exe)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    for addr, name in ((PROGRAM, 'mpegcpu'), (MUSIC, 'mpeg')):
        rom = data[region + ':' + name]
        o.u.mem_map(addr, len(rom))
        o.u.mem_write(addr, bytes(rom))
    o.u.mem_map(OUT, 0x10000)
    o.put(0x107878c, PROGRAM)
    o.put(0x10787b8, MUSIC)
    o.u.mem_write(0x107878b, bytes([kind]))
    o.run(0x4e9de0, count=100000)
    o.run(0x4ea040, count=5000000)
    o.put(0x107877c, OUT)
    o.put(0x1078784, OUT + 0x8000)
    o.put(0x10787b4, 44100)
    return o


def commands(o, sequence):
    for value in sequence:
        o.run(0x4b2bc0, {UC_X86_REG_ECX: value})


def mix(o, stereo, outputs=(OUT, OUT + 0x8000)):
    count = len(stereo) // 4
    words = struct.unpack(f'<{count*2}h', stereo)
    for channel, address in enumerate(outputs):
        o.u.mem_write(address, struct.pack(f'<{count}h', *words[channel::2]))
    o.put(0x1078760, count)
    o.run(0x4b2d10, count=20000000)
    channels = [struct.unpack(f'<{count}h', o.u.mem_read(addr, 2*count)) for addr in outputs]
    return struct.pack(f'<{count*2}h', *chain.from_iterable(zip(*channels)))


def replay(o, trace, pcm, frames, primary_muted=False):
    # Input is the port's unresampled SCSP capture. Mix before the following
    # 210 scanlines, as in the original machine frame service.
    events = {}
    for line in trace.read_text().splitlines():
        if line.startswith(('A68K_COMMAND ', 'A68K_IRQ ')):
            kind, at, val = line.split()
            at = int(at)
            if at > frames * 210:
                break
            if kind == 'A68K_COMMAND':
                events.setdefault((at - 1) // 210, []).append((at, int(val)))
    if not events:
        raise ValueError('Expected a cold-boot command trace')
    first = None
    count_diff = 0
    transitions = []
    before, after = hashlib.sha256(), hashlib.sha256()
    debt = 0.0
    with pcm.open('rb') as stream:
        for frame in range(frames):
            debt += 44100 / 58
            n = int(debt)
            debt -= n
            captured = stream.read(n*4)
            if len(captured) != n*4:
                raise ValueError('Incomplete SCSP capture')
            block = bytes(n*4) if primary_muted else captured
            mixed = mix(o, block) if o.get(0x1078790)[0] else block
            if primary_muted and mixed != captured:
                raise ValueError(f'Isolated digital-board output differs at frame {frame + 1}')
            before.update(block)
            after.update(mixed)
            if mixed != block:
                for i,(a,b) in enumerate(zip(struct.iter_unpack('<hh',block),struct.iter_unpack('<hh',mixed))):
                    if a != b:
                        count_diff += 1
                        if first is None:
                            first = dict(frame=frame+1, index=i, scsp=a, combined=b)
            for at, value in events.get(frame, ()):
                active = o.get(0x1078790)[0]
                commands(o, [value])
                if o.get(0x1078790)[0] != active:
                    transitions.append(dict(scanline=at, active=not bool(active)))
    return dict(frames=frames, policy='matched port block lengths', primary_muted=primary_muted, transitions=transitions,
                first_difference=first, different_stereo_frames=count_diff,
                scsp_sha256=before.hexdigest(), combined_sha256=after.hexdigest())


def track_inventory(o, kind):
    # Ask the native command routine for every track descriptor. Keep the
    # original's signed DSB1 segment index and DSB2 loop address decoding.
    total_at = 0x1004 if kind==1 else 0x800a
    total = struct.unpack('<H',o.u.mem_read(PROGRAM+total_at,2))[0]
    music_size = next(b-a+1 for a,b,_ in o.u.mem_regions() if a==MUSIC)
    seq=[0xaf,0x6f] if kind==1 else [0xae,0x10]
    segments={}
    forced_headers=set()
    tracks=[]
    for track in range(1,min(total,256)):
        if track & 0xf0 == 0xa0 or track==255:
            continue  # This byte resynchronizes the native packet.
        commands(o,seq+[track])
        if not o.get(0x1078790)[0]:
            continue
        seen=set()
        while o.get(0x1078790)[0]:
            pos,end=o.get(0x1078758)[0],o.get(0x1078780)[0]
            idx=o.u.mem_read(0x1078798,1)[0]
            if (pos,end,idx) in seen:
                break
            seen.add((pos,end,idx))
            segments.setdefault((pos,end),set()).add(track)
            # Advance the controller to the segment boundary. Stop before
            # decoding: the separate audio replay covers actual playback.
            o.put(0x1078758,end)
            o.put(0x10787a0,1152<<8)
            o.put(0x1078760,1)
            o.run(0x4b2d10,stops=(0x4e9e50,),count=5000)
            if o.stop:
                target=o.get(o.u.reg_read(UC_X86_REG_ESP)+4)[0]-MUSIC
                assert target==o.get(0x1078758)[0]
                if target>=o.get(0x1078780)[0]:
                    forced_headers.add((target,o.get(0x1078780)[0]))
        tracks.append((track,len(seen)))
        commands(o,[seq[0],3,0])
    formats=Counter()
    stops=[]
    headers={}
    visited=set()
    rom=bytes(o.u.mem_read(MUSIC,music_size))
    for begin,end in sorted(segments):
        off=begin
        # After a segment transition the native caller dispatches once even
        # if the new end is below its start. At track start it checks end first.
        while off<end or (off==begin and (begin,end) in forced_headers):
            if off+4>music_size:
                stops.append(dict(start=begin, offset=off, end=end, reason='outside music region',
                                  command_track_ids=sorted(segments[begin,end])))
                break
            raw=rom[off:off+4]
            if raw not in headers:
                # Stop at the real decoder dispatch. The parsed fields and
                # signed length are independent of previous synthesis state.
                o.put(SP+4,MUSIC+off,0x1078768)
                o.run(0x4e9e50,stops=(0x4e9fd0,))
                if o.stop:
                    esp=o.u.reg_read(UC_X86_REG_ESP)
                    headers[raw]=(o.get(esp+0x1c)[0],o.u.reg_read(UC_X86_REG_EBP),
                                  raw[3]>>6,o.get(esp+0x30)[0])
                else:
                    assert o.u.reg_read(UC_X86_REG_EAX)==0xffffffff
                    headers[raw]=None
            decoded=headers[raw]
            if decoded is None:
                # Observe the caller after an invalid header, before it reads
                # either PCM pointer. A zero step prevents another refill.
                o.put(0x1078790,1)
                o.put(0x1078758,off)
                # Isolate the observed post-transition decode, bypassing a
                # second segment check on re-entry to the native routine.
                o.put(0x1078780,max(off+1,end))
                o.put(0x10787a0,1152<<8)
                o.put(0x1078760,1)
                o.run(0x4b2d10,stops=(0x4b2e12,))
                position=o.get(0x1078758)[0]
                step=o.get(0x10787a8)[0]
                assert o.stop and position==(off-1)&0xffffffff and step==0
                stops.append(dict(start=begin,end=end,offset=off,header=raw.hex(),
                                  next_position=position,source_step=step,
                                  command_track_ids=sorted(segments[begin,end])))
                break
            layer,rate,mode,length=decoded
            if layer!=2 or length==0 or length>music_size:
                raise ValueError(('inspect native decoder progression',off,decoded))
            if off not in visited:
                visited.add(off)
                formats[(layer,mode,rate,length)]+=1
            off+=length
    return dict(command_track_count=len(tracks),raw_track_limit=total,unique_segments=len(segments),
                unique_headers_checked_in_x86=len(headers),
                frames_by_layer_mode_rate_bytes={str(k):n for k,n in sorted(formats.items())},
                valid_frame_positions=len(visited),terminal_boundaries=stops,
                empty_or_reversed_segments=sum(begin>=end for begin,end in segments),
                forced_fetches_after_reversed_transition=len(forced_headers))


def capture(o, frames, samples, play, stop):
    commands(o, play)
    begin, end = o.get(0x1078758)[0], o.get(0x1078780)[0]
    assert begin < end and o.get(0x1078790)[0] == 1
    source_header = bytes(o.u.mem_read(MUSIC + begin, 4))
    output = hashlib.sha256()
    first = None
    # Keep each capture downstream of actual SCSP output; zeros isolate the
    # digital board's contribution. No compressed or decoded music is retained.
    silence = bytes(samples * 4)
    for frame in range(frames):
        block = mix(o, silence)
        output.update(block)
        for i, (l, r) in enumerate(struct.iter_unpack('<hh', block)):
            if first is None and (l or r):
                first = dict(frame=frame, sample=i, stereo=[l, r])
    assert first is not None
    commands(o, stop)
    assert o.get(0x1078790)[0] == 0
    return dict(command=list(play), track_start=begin, track_end=end, mpeg_header=source_header.hex(),
                decoded_rate=o.get(0x1078774)[0], decoded_frame_size=o.get(0x1078770)[0],
                first_active=first, stereo_frames=frames*samples, pcm_sha256=output.hexdigest())


def compare_machine_reset(exe, archive, kind):
    """Compare the next digital-board blocks and pending command across a warm machine reset."""
    from scsp_game_audio_compare import initialize, bind_digital_board
    from unicorn import UC_HOOK_CODE

    prefix, track = (0xaf, 0x6f) if kind == 1 else (0xae, 0x10)
    reference = None
    for reset in (False, True):
        o, _ = initialize(exe, archive, False)
        bind_digital_board(o, archive)
        outputs = o.get(0x107877c)[0], o.get(0x1078784)[0]
        silence = bytes(760 * 4)
        commands(o, [prefix, track, 1])
        for _ in range(16):
            mix(o, silence, outputs)
        commands(o, [prefix, 3])
        if reset:
            # initialize() binds the real sound vectors on this machine object.
            machine, main_ram = 0x76000000, 0x68000000
            o.u.mem_map(main_ram, 0x140000)
            o.put(machine + 0x203850, main_ram)
            o.put(machine + 0x203858, main_ram + 0x100000)
            o.u.hook_add(UC_HOOK_CODE, lambda *_: o.ret(), begin=0x4c3570, end=0x4c3570)
            o.u.ctl_flush_tb()
            o.run(0x4cad60, {UC_X86_REG_ECX: machine}, count=3000000)
        assert o.get(0x1078790)[0] and o.u.mem_read(0x10ed99d, 1)[0] == 2
        pcm = b''.join(mix(o, silence, outputs) for _ in range(8))
        assert any(pcm)
        commands(o, [0])
        assert not o.get(0x1078790)[0]
        if reset and reference != pcm:
            raise ValueError('Warm machine reset changed the digital-board continuation')
        reference = pcm
    return dict(stereo_frames=len(reference)//4, pcm_sha256=hashlib.sha256(reference).hexdigest(),
                pending_stop_completed=True)


def compare_portable_archive(archive, kind, architectures, track, continuation):
    """Build each requested local ABI and compare PCM with both original traces."""
    root = Path(__file__).resolve().parents[1]
    region = FAMILIES[kind]
    roms = sound_regions(archive, {7: region + ':mpegcpu', 8: region + ':mpeg'})
    data = bytearray()
    for key in ('mpegcpu', 'mpeg'):
        rom = roms[region + ':' + key]
        data.extend(struct.pack('<I', len(rom)))
        data.extend(rom)
    result = {}
    with tempfile.TemporaryDirectory() as directory:
        runner = Path(directory) / 'dsb-replay'
        for arch in architectures:
            flags = [] if arch == 'native' else ['-arch', arch]
            snd = root / 'port/snd'
            subprocess.run(['cc', *flags, '-O2', '-ffp-contract=off', '-std=c11',
                            '-Wall', '-Wextra', '-Werror', snd/'test/dsb_board_replay.c',
                            snd/'dsb_board.c', snd/'dsb_original.c', snd/'dsb_mpeg.c',
                            snd/'dsb_synthesis.c', '-lm', '-o', runner], check=True)
            pcm = subprocess.check_output([runner, str(kind)], input=data)
            split = 4 * track['stereo_frames']
            cold = hashlib.sha256(pcm[:split]).hexdigest()
            fresh = hashlib.sha256(pcm[split:]).hexdigest()
            if (len(pcm) != split + 4 * continuation['stereo_frames'] or
                    cold != track['pcm_sha256'] or fresh != continuation['pcm_sha256']):
                raise ValueError((archive.stem, arch, cold, fresh))
            result[arch] = dict(cold_pcm_sha256=cold, fresh_pcm_sha256=fresh)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trace', type=Path)
    parser.add_argument('--scsp-pcm', type=Path)
    parser.add_argument('--primary-muted', action='store_true', help='Compare the supplied muted-primary capture directly with the native DSB output')
    parser.add_argument('--frames', type=int, default=1000)
    parser.add_argument('--machine-reset', action='store_true', help='Check active playback and a partial packet across warm reset')
    parser.add_argument('--portable-arch', action='append', choices=('native', 'arm64', 'x86_64'),
                        help='Compare cold and fresh-load PCM on this ABI (named architectures require macOS)')
    args = parser.parse_args()
    if bool(args.trace) != bool(args.scsp_pcm) or args.frames < 1 or (args.primary_muted and not args.trace):
        parser.error('Supply both --trace and --scsp-pcm and a positive frame count')
    if args.archive.stem not in ('stcc', 'topskatr'):
        parser.error('Use the existing parent archive stcc.zip or topskatr.zip')
    kind = 1 if args.archive.stem == 'stcc' else 2
    o = native_board(args.exe, args.archive, kind)
    prefix = [0xaf, 0x6f] if kind == 1 else [0xae, 0x10]
    stop = [prefix[0], 0x03, 0]
    result = dict(game=args.archive.stem, type=kind, original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                  track=capture(o, 16, 760, [*prefix, 1], stop))
    result['track_inventory'] = track_inventory(o, kind)
    if args.machine_reset or args.portable_arch:
        result['warm_reset'] = compare_machine_reset(args.exe, args.archive, kind)
    if args.portable_arch:
        result['portable'] = compare_portable_archive(args.archive, kind, args.portable_arch,
                                                      result['track'], result['warm_reset'])
    if args.trace:
        fresh = native_board(args.exe, args.archive, kind)
        result['command_replay'] = replay(fresh, args.trace, args.scsp_pcm, args.frames, args.primary_muted)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(args.archive.stem, result['track_inventory'], result['track']['pcm_sha256'])
