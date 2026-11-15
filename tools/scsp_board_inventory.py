#!/usr/bin/env python3
"""Index native audio board routines, installed callbacks and external boundaries in ElSemi 1.1a."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
from collections import Counter
from pathlib import Path

from original_inventory import OriginalPE

ROOTS = {
    'mixer': [0x4af7f0],
    'chip initialization': [0x4af2c0],
    'CPU reads and writes': [0x4ae870, 0x4ae800, 0x4ab220, 0x4afb00, 0x4afa20, 0x4af900],
    'host PCM submission': [0x4c8190],
    'mixer and MIDI data producers': [0x4aa8d0, 0x4aa8e0, 0x4aa900, 0x4aa920,
                                      0x4aa940, 0x4c6710],
    'board setup and installed bus callbacks': [0x4ccbe0, 0x4c6a90, 0x4c8380,
        0x4cb1f0, 0x4c69e0, 0x4c69d0, 0x4c69c0, 0x4b3070],
    'i960 status and command handlers': [0x4c75f0, 0x4c7620, 0x4c7650,
        0x4cb480, 0x4cb500, 0x4cb570, 0x4c8660],
    'board mix, scanline, reset and post-load': [0x4cc4a0, 0x4cc710, 0x4cad60, 0x4caf00],
    'SCSP scheduler and acknowledge': [0x4aefb0, 0x4aeac0, 0x4b3090],
}
TAIL_SITES = {0x4af7f9, 0x4af7fe, 0x4af98c, 0x4afa77, 0x4afb66,
              0x4afa0d, 0x4afaf9, 0x4afbf1, 0x4af229, 0x4cc75d, 0x4caf1b, 0x4c86b5}
# Each taken branch below tests board + 0x3c. Zero selects the other sound board.
SCSP_BRANCH = {0x4ccbf3, 0x4cc4ce, 0x4cc714, 0x4cb49a, 0x4cb514, 0x4cb584, 0x4c8670}
DYNAMIC = {0x4c81b5: 'host QueryPerformanceCounter', 0x4c8200: 'host QueryPerformanceCounter',
           0x4eebb6: 'host voice vtable +0x64', 0x4eebd4: 'host voice vtable +0x50',
           0x4eebfa: 'host voice vtable +0x4c', 0x4eec17: 'host WaitForSingleObject',
           0x4eec28: 'host voice vtable +0x64', 0x4eecbe: 'host voice vtable +0x54',
           0x4eed59: 'host audio object vtable +0x00',
           0x4eed83: 'host audio object vtable +0x20',
           0x4eee39: 'host audio object vtable +0x40',
           0x4cc4be: 'host QueryPerformanceCounter', 0x4cc521: 'host QueryPerformanceCounter',
           0x4b33bb: 'unbound vector-page long-read fallback', 0x4b33e1: 'unbound vector-page long-read fallback',
           0x4a9fe4: 'generated DSP program', 0x4aa058: 'VirtualFree',
           0x4aa06d: 'VirtualAlloc'}
# Table lengths come from the bounded register fields in the pinned code.
VOICE_CALLS = (0x4aaa31, 0x4aab34)
SWITCHES = {0x454a83: (0x454bb8, 4), 0x4ab39e: (0x4ab47c, 4),
            0x4ab23b: (0x4ab2b8, 6), 0x4ab59d: (0x4ab678, 4),
            0x4ab60d: (0x4ab688, 4), 0x4af066: (0x4af270, 9),
            0x4af839: (0x4af8d0, 5)}
BOUNDARIES = {0x4936f0: 'CRT PCM byte copy', 0x4b2bc0: 'optional DSB command', 0x4b2d10: 'optional DSB mix',
              0x4e9de0: 'optional DSB initialization', 0x4ea040: 'optional DSB initialization',
              0x4c3570: 'machine i960 reset',
              0x462ae0: 'A68K dispatch initialization', 0x4b7c60: 'renderer invalidation',
              0x48cf46: 'CRT fclose', 0x493a60: 'CRT memset', 0x48d12f: 'CRT malloc',
              0x5006a0: 'math power helper', 0x5008f0: 'x87 integer conversion',
              0x4909dc: 'CRT random number', 0x462b1c: 'A68K execution inventory'}
LINE = re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(\S+)\s*(.*)$')


def scsp_counterparts(voice, functions):
    # Group entries sharing one portable implementation. Keep frontend policy
    # and cabinet extensions visible even when a native call has a known owner.
    rows = (
        (voice, 'render_ordinary_voices / UpdateSlot', 'scsp_slot_write_compare, scsp_mixer_block_compare'),
        ([0x4548c0, 0x4aead0], 'render_interleaved_slot / render_block', 'scsp_mixer_block_compare'),
        ([0x4aa950, 0x4af7f0], 'render_ordinary_voices / render_block', 'scsp_mixer_block_compare'),
        ([0x4a9e90, 0x4aa040, 0x4aa7f0, 0x4a9fa0], 'decode / scsp_dsp_original_compile, start and step',
         'scsp_dsp_compare, scsp_dsp_bridge_compare, scsp_mixer_block_compare'),
        ([0x4aa8d0, 0x4c6710], 'scsp_set_interleaved_mixer', 'scsp_game_hook_probe'),
        ([0x4aa8e0, 0x4cc4a0], 'm2snd_render and caller-supplied PCM block', 'scsp_game_audio_compare'),
        ([0x4aa940], 'chip binding at board creation', 'scsp_a68k_board_compare'),
        ([0x4aa900, 0x4aa920, 0x4c8660], 'SCSP input and output MIDI queues', 'scsp_board_exchange_probe'),
        ([0x4ab0e0, 0x4aea40, 0x4ab520], 'scsp_clock_tick / CheckPendingIRQ / DecodeSCI',
         'scsp_board_exchange_probe, scsp_control_compare'),
        ([0x4ab220, 0x4ae800, 0x4ae870, 0x4ab230], 'scsp_cpu_read_observed / UpdateCpuRegR',
         'scsp_control_compare, scsp_callback_provenance'),
        ([0x4af900, 0x4afa20, 0x4afb00, 0x4af050], 'cpu_store / UpdateCpuReg', 'scsp_write_exchange_probe'),
        ([0x4ab340, 0x4ab390, 0x4ae940], 'Step / EG_Update / Compute_EG', 'scsp_slot_write_compare'),
        ([0x4ab550, 0x4ae8e0, 0x4ab6a0], 'LFO_ComputeStep / Compute_LFO / init_tables', 'scsp_slot_write_compare'),
        ([0x4af710, 0x4af810], 'StartSlot / UpdateSlotReg', 'scsp_slot_write_compare'),
        ([0x4af2c0], 'init_tables / scsp_original_power_on', 'scsp_mixer_block_compare'),
        ([0x4aefb0, 0x4cc710], 'a68k_board_scanline / a68k_scsp_scanline', 'scsp_a68k_board_compare'),
        ([0x4b3090, 0x4aeac0], 'live autovector and template IRQ callback', 'scsp_board_exchange_probe'),
        ([0x4b3070], 'bare RESET callback', 'scsp_a68k_board_compare'),
        ([0x4b3280, 0x4b32c0, 0x4ccbe0], 'A68K page maps and audio board setup', 'a68k_board_map_probe, scsp_a68k_board_compare'),
        ([0x4c69c0, 0x4c69d0, 0x4c69e0, 0x4c6a90, 0x4c8380, 0x4cb1f0], 'program/bank ROM write callbacks',
         'a68k_board_map_probe, scsp_a68k_board_compare'),
        ([0x4b33a0, 0x4cad60], 'board reset and CPU reset-vector fetch', 'scsp_board_exchange_probe, scsp_a68k_board_compare'),
        ([0x4caf00], 'renderer invalidation on load, live board state retained by native hook', 'scsp_dsp_state_audit'),
        ([0x4c75f0, 0x4c7620, 0x4c7650, 0x4cb480, 0x4cb500, 0x4cb570],
         'i960 sound port map and command delivery', 'scsp_board_exchange_probe, tgp/test/check_machine'),
        ([0x4c8190, 0x4eeba0], 'host PCM submission; frontend owns playback queue', 'scsp_board_exchange_probe'),
        ([0x4eecf0], 'stream setup and native block length; frontend cadence policy open', 'scsp_board_exchange_probe, scsp_game_audio_compare'),
    )
    result = {}
    for addresses, owner, evidence in rows:
        for address in addresses:
            if address in result:
                raise ValueError(f'Duplicate SCSP counterpart at {address:08x}')
            result[address] = dict(owner=owner, evidence=evidence.split(', '))
    if set(result) != set(functions):
        raise ValueError(f'SCSP counterpart inventory differs from reachable entries: {set(result) ^ set(functions)}')
    return {f'{address:08x}': result[address] for address in sorted(result)}


def board_counterparts(board, functions):
    # Each row names the owner of the linked native entry points. A game
    # replay exercises only its trace; the chip vectors cover other branches.
    if board == 'model1':
        groups = [
            ('004a9c30 004a9ce0 004a9e00 004b1580 004b1600 004b1670 004b2450',
             'FM timer callbacks, mode and CSM in fm_original.c', 'model1_fm_portable_compare'),
            ('004a9d20 004a9d70 004cc4a0', 'FM partial block and board mix in model1_original.c',
             'model1_mix_compare, model1_game_audio_compare'),
            ('004afc50 004afd20 004afed0 004affb0 004b01b0 004b05c0 004b0700 004b08f0',
             'MultiPCM registers, tables, envelope and mix in multipcm_original.c', 'model1_board_compare'),
            ('004b0b30 004b12b0 004b13a0 004b17c0 004b2680 004b2780',
             'FM power-on, table generation and reset in fm_original.c', 'model1_fm_compare, model1_fm_portable_compare'),
            ('004b0c80 004b0cd0 004b1040 004b1060 004b1090 004b11e0 004b1200 004b1890 004b1a30 '
             '004b1a70 004b1aa0 004b1ae0 004b1b50 004b1e30 004b1e60 004b1e80 004b1ed0 004b1ef0 '
             '004b22e0 004b2580', 'FM operators, registers and synthesis in fm_original.c', 'model1_fm_portable_compare'),
            ('004b3070 004b3090 004b3280 004b33a0 004cc710 004ccbe0 004cad60',
             'A68K board setup, callbacks, reset and scanline in model1_board.c / model1_bus.c', 'model1_cpu_compare'),
            ('004caf00', 'Native post-load renderer invalidation; Libretro restores audio in the board serializer',
             'scsp_dsp_state_audit, model1_cpu_compare'),
            ('004c69f0 004c6a10 004c6a20 004c6a30 004c6a40 004c7cf0 004c7d00 004c7d10 004c7d20 '
             '004c7d30 004c7d40 004c8260 004c82a0 004c82b0 004c82c0 004c82d0 004cb110 004cb190 '
             '004cb1a0 004cb1b0 004cb1c0 004cba80 004cbab0 004cc530 004cc5a0 004cc610 004cc630 '
             '004cc650 004cc770 004ccb80', 'CPU-facing reads and writes in model1_bus.c / model1_original.c',
             'model1_bus_compare, model1_cpu_compare'),
            ('004c75f0 004c7620 004c7650 004cb480 004cb500 004cb570 004c8660',
             'i960 sound I/O and command FIFO in m2board.c / model1_original.c',
             'scsp_board_exchange_probe, model1_board_compare, model1_game_audio_compare'),
            ('004c8190 004eeba0 004eecf0', 'Host PCM transport and stream setup; frontend owns playback',
             'scsp_board_exchange_probe, model1_game_audio_compare'),
        ]
    else:
        groups = [
            ('004b28e0 004b2960 004b29d0 004b2a00 004b2a50 004b2aa0 004b2bc0',
             'Track commands, descriptors and segments in dsb_original.c', 'dsb_exchange_compare, dsb_board_compare'),
            ('004b2d10 004e9e50', 'Compressed refill, frame headers and post-SCSP mix in dsb_board.c / dsb_original.c',
             'dsb_exchange_compare, dsb_board_compare'),
            ('004e9de0 004e9a70', 'Synthesis history, PCM and coefficients in dsb_synthesis.c', 'dsb_exchange_compare'),
            ('004ea040 004ea100 004ea310 004ea4d0 004eaa80 004eaf00 004eb0f0 004eb230 004eb350 '
             '004eb680 004eb850 004eb920 004eba50 004ebb90 004ebc20',
             'Layer I/II bit allocation, sample data and decoding tables in dsb_mpeg.c', 'dsb_exchange_compare'),
            ('00493c00', 'CRT stack probe; host compiler owns local stack allocation', 'scsp_board_inventory'),
        ]
    rows = {}
    for entries, owner, evidence in groups:
        for entry in entries.split():
            if entry in rows:
                raise ValueError(f'Duplicate {board} entry {entry}')
            rows[entry] = dict(owner=owner, evidence=evidence.split(', '))
    expected = {f'{entry:08x}' for entry in functions}
    if set(rows) != expected:
        raise ValueError(f'{board} reachable-entry mismatch: {set(rows) ^ expected}')
    return dict(sorted(rows.items()))


def inventory(exe, board='scsp'):
    pe = OriginalPE(exe)
    tool = shutil.which('llvm-objdump')
    command = [tool] if tool else ['xcrun', 'llvm-objdump']
    roots_by_family = ROOTS
    boundaries = BOUNDARIES.copy()
    dynamic = DYNAMIC.copy()
    tails = set(TAIL_SITES)
    switches = SWITCHES.copy()
    callbacks = {}
    if board == 'model1':
        roots_by_family = {
            'setup, mix and scanline': [0x4ccbe0, 0x4cc4a0, 0x4cc710],
            'reset and post-load': [0x4cad60, 0x4caf00],
            'host PCM submission': ROOTS['host PCM submission'],
            'i960 sound ports': ROOTS['i960 status and command handlers'],
        }
        installer = subprocess.check_output(
            command +
            ['-d', '--start-address=0x4ccbe0', '--stop-address=0x4cd0f9', str(exe)], text=True)
        callback_values = re.findall(r'\bmovl\s+\$0x([0-9a-f]+),', installer)
        roots_by_family['installed callbacks'] = sorted({int(v,16) for v in callback_values
                                                        if pe.is_code(int(v,16))})
        boundaries[0x48d0f5] = 'CRT free'
        switches.update({0x4afedc: (0x4aff94,4), 0x4b0710: (0x4b08c4,8),
                         0x4b1f58: (0x4b2218,10), 0x4b22e5: (0x4b2434,7),
                         0x4b2597: (0x4b2668,4), 0x4b10ae: (0x4b11b4,8),
                         0x4b203e: (0x4b22c4,4)})
        # Original FM initialization installs timer/IRQ at +0x730/+0x734.
        # The timer service receives the base of the subobject at chip +8.
        for site in (0x4b15ae,0x4b162e,0x4b17e8,0x4b26bf,0x4b26e3,0x4b16a9,0x4b16d6):
            callbacks[site] = [0x4a9ce0]
        for site in (0x4b15e7,0x4b165e,0x4b1711,0x4b1748,0x4b177a,0x4b17b3):
            callbacks[site] = [0x4a9c30]
        # The four FM operators have a 0x60-byte stride. Their envelope
        # function pointer is written at key-on, transitions and reset.
        for site in (0x4b0df6,0x4b0e3f,0x4b0e96,0x4b0ee8):
            callbacks[site] = [0x4b11e0,0x4b1200,0x4b1ae0,0x4b1e60]
    elif board == 'dsb':
        roots_by_family = {'commands': [0x4b2bc0], 'mix': [0x4b2d10],
                           'decoder initialization': [0x4e9de0, 0x4ea040]}
        for roots in roots_by_family.values():
            for address in roots:
                boundaries.pop(address)
        tails.add(0x4b2bcf)
        switches[0x4eabe8] = (0x4eaee8, 4)


    def pointers(base, count):
        targets = struct.unpack(f'<{count}I', pe.read(base, count * 4))
        if not all(pe.is_code(target) for target in targets):
            raise ValueError(f'Invalid code table at {base:x}')
        return targets

    voice = pointers(0x572980, 32)
    # Decode sequentially only within a run starting on a known boundary.
    # The next branch target starts a separate decode; inline tables are data.
    def instructions(start):
        while True:
            output = subprocess.check_output(command + ['-d', f'--start-address={start}',
                f'--stop-address={start+512}', str(exe)], text=True)
            advanced = False
            for line in output.splitlines():
                match = LINE.fullmatch(line)
                if not match:
                    continue
                address, raw, op, operand = match.groups()
                address = int(address, 16)
                if address != start:
                    raise ValueError(f'Disassembly gap at {start:x}')
                size = len(bytes.fromhex(raw))
                if size == 0 or op in ('<unknown>', 'int3'):
                    raise ValueError(f'Invalid reachable instruction at {address:x}')
                yield address, op, operand
                start += size
                advanced = True
            if not advanced:
                raise ValueError(f'No instruction at {start:x}')

    indirect_sites = {}
    entries = [start for roots in roots_by_family.values() for start in roots]
    functions = {}
    while entries:
        entry = entries.pop()
        if entry in functions:
            continue
        blocks, visited, edges = [entry], set(), []
        while blocks:
            for at, op, operand in instructions(blocks.pop()):
                if at in visited:
                    break
                visited.add(at)
                if op.startswith('ret'):
                    break
                if not op.startswith(('j', 'call', 'loop')):
                    continue
                direct = re.match(r'^0x([0-9a-f]+)\b', operand)
                if not direct:
                    indirect_sites[f'{at:08x}'] = operand
                if direct:
                    targets = [int(direct[1], 16)]
                    if at in SCSP_BRANCH and board == 'scsp':
                        if op != 'jne':
                            raise ValueError(f'Unexpected board selection at {at:x}')
                        blocks.extend(targets)
                        break
                    if at in SCSP_BRANCH and board == 'model1':
                        continue  # Zero board type takes the fallthrough.
                elif at in callbacks:
                    targets = callbacks[at]
                elif at in VOICE_CALLS:
                    targets = voice
                elif at in switches:
                    targets = pointers(*switches[at])
                elif at in dynamic:
                    edges.append(dict(site=f'{at:08x}', kind=dynamic[at], targets=[]))
                    continue
                else:
                    raise ValueError(f'Unclassified indirect transfer {at:x}: {operand}')
                if op.startswith('call') or at in tails:
                    kind = 'call' if op.startswith('call') else 'tail'
                    edges.append(dict(site=f'{at:08x}', kind=kind, targets=[f'{t:08x}' for t in targets]))
                    entries.extend(t for t in targets if t not in boundaries)
                else:
                    blocks.extend(t for t in targets if t not in visited)
                    if at in switches:
                        edges.append(dict(site=f'{at:08x}', kind='local switch',
                                          targets=[f'{t:08x}' for t in targets]))
                if op in ('jmp', 'jmpl'):
                    break
        functions[entry] = dict(instructions=len(visited), transfers=sorted(edges, key=lambda e:e['site']))
    families = {}
    for family, roots in roots_by_family.items():
        pending = list(roots)
        seen = set()
        while pending:
            at = pending.pop()
            if at in seen:
                continue
            seen.add(at)
            for edge in functions[at]['transfers']:
                if edge['kind'] in ('tail', 'call'):
                    pending.extend(int(t, 16) for t in edge['targets'] if int(t, 16) in functions)
        families[family] = sorted(f'{at:08x}' for at in seen)
    report = dict(board=board, families=families, roots={k:[f'{a:08x}' for a in v] for k,v in roots_by_family.items()},
                  indirect_sites=indirect_sites, original_sha256=hashlib.sha256(pe.data).hexdigest(),
                  functions={f'{a:08x}':functions[a] for a in sorted(functions)},
                  external={f'{a:08x}':v for a,v in boundaries.items()})
    if board != 'scsp':
        report['counterparts'] = board_counterparts(board, functions)
        return report
    report['counterparts'] = scsp_counterparts(voice, functions)
    # Verify the producer of each callback separately from reachability of its body.
    vtable = pointers(0x51bbcc, 13)
    board_slots = {0: 0x4cd450, 1: 0x4cc7a0, 5: 0x4cad60, 8: 0x4ccbe0,
                   10: 0x4cc4a0, 11: 0x4c8190, 12: 0x4caf00}
    for slot, address in board_slots.items():
        if vtable[slot] != address:
            raise ValueError(f'Unexpected board vtable slot {slot}')
    # Keys are virtual addresses of immediate operands in the PE.
    installs = {0x4ce02a: 0x4c7650, 0x4ce014: 0x4c7620, 0x4ce01f: 0x4c75f0,
                0x4ce697: 0x4cb570, 0x4ce6a2: 0x4cb500, 0x4ce6ad: 0x4cb480,
                0x4cd1c9: 0x4ae870, 0x4cd1ce: 0x4ae800, 0x4cd1d3: 0x4ab220,
                0x4cd238: 0x4afb00, 0x4cd23d: 0x4afa20, 0x4cd242: 0x4af900,
                0x4cd27e: 0x4c6a90, 0x4cd288: 0x4c8380, 0x4cd292: 0x4cb1f0,
                0x4cd29c: 0x4c69e0, 0x4cd2a1: 0x4c69d0, 0x4cd2a6: 0x4c69c0,
                0x4cd2e9: 0x4b3090, 0x4cd313: 0x4b3070, 0x4cd356: 0x4aeac0}
    for site, target in installs.items():
        if pointers(site, 1)[0] != target or target not in functions:
            raise ValueError(f'Unindexed installed callback at {site:x}')
    # Direct encoded addresses are evidence of references, even for helpers
    # without a recovered caller. This does not detect computed aliases.
    objects = {'mixer mode': 0x10ed99e, 'dual chip': 0x10ed9da,
               'left PCM': 0x10bf558, 'right PCM': 0x10bf55c,
               'block length': 0x10bfd60, 'board binding': 0x10bfd64}
    refs = {}
    for name, address in objects.items():
        needle = struct.pack('<I', address)
        sites = []
        for section in pe.sections:
            data = pe.data[section['offset']:section['offset'] + section['raw_size']]
            index = data.find(needle)
            while index >= 0:
                sites.append(f"{section['address'] + index:08x}")
                index = data.find(needle, index + 1)
        refs[name] = sites
    report.update(direct_data_references=refs,
                board_vtable={f'+{slot*4:02x}':f'{a:08x}' for slot,a in board_slots.items()},
                installed_operands={f'{site:08x}':f'{target:08x}' for site,target in installs.items()})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--board', choices=('scsp', 'model1', 'dsb'), default='scsp')
    args = parser.parse_args()
    report = inventory(args.exe, args.board)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    counts = Counter(edge['kind'] for row in report['functions'].values() for edge in row['transfers'])
    print(len(report['functions']), 'native entries;', dict(counts))
