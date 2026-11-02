#!/usr/bin/env python3
"""Check native continuation, rejection and fresh-process pointer rebinding in GL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='New isolated directory')
parser.add_argument('--frames', type=int, default=900)
parser.add_argument('--timing', choices=('60hz', 'native'), default='60hz')
parser.add_argument('--pipeline', choices=('enabled', 'disabled'), default='enabled')
parser.add_argument('--play', action='store_true', help='VF2 paid-match input sequence; use at least 1800 frames')
parser.add_argument('--network-role', help='Explicit ANRS value for isolated local-board state coverage')
parser.add_argument('--manxtt-cabinet', choices=('twin','deluxe'), help='Apply the existing Manx TT operator cabinet setting')
parser.add_argument('--load-state', type=Path, help='Optional pre-existing raw core state; read only')
parser.add_argument('--input-frame', type=int, default=0, help='Input replay frame corresponding to the initial loaded state')
args = parser.parse_args()
if not 1 <= args.frames <= 7200:
    parser.error('--frames must be between 1 and 7200')
root = Path(__file__).resolve().parent.parent
rom = args.rom.resolve(strict=True)
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
core = root / 'port/build-libretro-macos/model2emuex_dev_libretro.dylib'
harness = out / 'frontend-check'
with (out/'build.log').open('w') as build_log:
    subprocess.run(['make', '-j4'], cwd=root, check=True, stdout=build_log, stderr=subprocess.STDOUT)
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'sdl2'], text=True))
subprocess.run(['cc', '-O2', '-g', '-Isrc/libretro/include', 'scripts/frontend-check.c', *flags,
                '-framework', 'OpenGL', '-lz', '-o', str(harness)], cwd=root, check=True)
environment = os.environ.copy()
# Prevent previous harness overrides from leaking into this run.
for key in list(environment):
    if key.startswith('CHECK_'):
        del environment[key]
environment.update(CHECK_STATE='1', CHECK_STATE_COLD='1', CHECK_TIMING=args.timing,
                   CHECK_OPTION_KEY='model2emuex_pipeline', CHECK_OPTION_VALUE=args.pipeline)
if args.play:
    environment['CHECK_PLAY'] = '1'
if args.network_role:
    environment['CHECK_NETWORK_ROLE'] = args.network_role
if args.manxtt_cabinet:
    environment['CHECK_MANX_CABINET'] = args.manxtt_cabinet
if args.load_state:
    environment['CHECK_LOAD_STATE'] = str(args.load_state.resolve(strict=True))
    environment['CHECK_LOAD_INPUT_FRAME'] = str(args.input_frame)
commands = []
for name, frames in [('same-process', args.frames), ('fresh-process', 12)]:
    work = out/name
    work.mkdir()
    if name == 'fresh-process':
        environment['CHECK_LOAD_STATE'] = str(out/'same-process/core.state')
        environment['CHECK_LOAD_INPUT_FRAME'] = str(args.input_frame + args.frames)
    command = [str(harness), str(core), str(rom), str(frames), str(work)]
    commands.append(command)
    with (work/'run.log').open('w') as log:
        subprocess.run(command, cwd=root, env=environment, check=True, stdout=log, stderr=subprocess.STDOUT)
baseline = (out/'same-process/continued.state').read_bytes()
restored = (out/'fresh-process/core.state').read_bytes()
result = {'game': rom.stem, 'timing': args.timing, 'pipeline': args.pipeline,
          'input': 'scripted' if args.play else 'none', 'frames_before_save': args.frames,
          'continuation_frames': 12, 'same_process_replays': 4,
          'invalid_state_rejection': True, 'nvram_authority_checked': rom.stem == 'vf2', 'cold_save_load': True,
          'context_recreation_continuation': True,
          'fresh_process_continuation_exact': baseline == restored,
          'state_capacity': len(baseline), 'state_sha256': hashlib.sha256(baseline).hexdigest(),
          'core_sha256': hashlib.sha256(core.read_bytes()).hexdigest(), 'commands': commands}
result['initial_state'] = str(args.load_state) if args.load_state else None
result['network_role'] = args.network_role
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
assert result['fresh_process_continuation_exact'], 'Fresh-process continuation differs'
