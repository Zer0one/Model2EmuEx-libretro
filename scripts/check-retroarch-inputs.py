#!/usr/bin/env python3
"""Capture native input tests with SM2-Libretro's RetroArch replay-v1 format.

Reference: SM2 scripts/smoke-retroarch.py and test-manxtt-gameplay.py.
Replays contain only Libretro input records, no ROM or machine-state data.
Capture success requires subsequent visual review; it is not device acceptance.
"""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
import time
from pathlib import Path

from retroarch_savestate_helpers import free_udp_port, take_screenshot


def phases(game):
    if game == 'srallyc':
        return [
            ('idle', {}), ('steer-left', {'axes': {(0, 0, 0): -32768}}),
            ('steer-right', {'axes': {(0, 0, 0): 32767}}),
            ('accelerator-half', {'pressure': {(0, 13): 16384}}),
            ('accelerator-full', {'pressure': {(0, 13): 32767}}),
            ('brake-half', {'pressure': {(0, 12): 16384}}),
            ('brake-full', {'pressure': {(0, 12): 32767}}),
            ('handbrake', {'buttons': {(0, 0)}}),
            *[(f'h-gate-{i+1}', {'axes': {(0, 1, 0): x, (0, 1, 1): y}})
              for i, (x, y) in enumerate(((-32768, -32768), (-32768, 32767),
                                          (32767, -32768), (32767, 32767)))],
            ('neutral', {'buttons': {(0, 1)}}),
            ('view-up', {'buttons': {(0, 4)}}), ('view-down', {'buttons': {(0, 5)}}),
            ('service', {'buttons': {(0, 14)}}), ('start', {'buttons': {(0, 3)}}),
            ('coin', {'buttons': {(0, 2)}}), ('released', {}),
        ]
    return [('idle', {})] + [
        (f'p{port+1}-{name}', {'buttons': {(port, button)}})
        for port in range(2) for name, button in
        [('punch', 8), ('kick', 0), ('guard', 1), ('up', 4), ('down', 5), ('left', 6), ('right', 7)]
    ] + [('service', {'buttons': {(0, 14)}}), ('p1-start', {'buttons': {(0, 3)}}),
         ('p2-start', {'buttons': {(1, 3)}}), ('released', {})]


def make_replay(path, cases):
    # Same 16-byte no-state padding used by the current SM2 1.22 reader fixtures.
    data = bytearray(struct.pack('<6I', 0x42535632, 1, 0, 0, 1, 0) + bytes(16))
    first, duration = 1560, 120
    end = first + duration * len(cases)
    for frame in range(end + 120):
        case = cases[(frame-first)//duration][1] if first <= frame < end else {}
        buttons = set(case.get('buttons', ()))
        # Test enters at EXIT; Service twice selects Input Test; Test opens it.
        for start, button in ((900, 15), (1050, 14), (1170, 14), (1290, 15)):
            if start <= frame < start + 24:
                buttons.add((0, button))
        data += struct.pack('<BH', 0, 96)
        for port in range(2):
            values = [(1, 0, button, int((port, button) in buttons)) for button in range(16)]
            values += [(5, index, axis, case.get('axes', {}).get((port, index, axis), 0))
                       for index in range(2) for axis in range(2)]
            values += [(5, 2, button, case.get('pressure', {}).get((port, button), 0))
                       for button in range(16)]
            values += [(2, 0, button, 0) for button in range(4)]
            values += [(4, 0, button, 0) for button in (2, 3, 6, 7, 13, 14, 15, 16)]
            for device, index, button, value in values:
                data += struct.pack('<4BHh', port, device, index, 0, button, value)
        data += b'f'
    path.write_bytes(data)
    return end, [{'name': name, 'first_frontend_frame': first+i*duration,
                  'end_frontend_frame': first+(i+1)*duration} for i, (name, _) in enumerate(cases)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('retroarch', 'core', 'rom-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--game', choices=('srallyc', 'vf2'), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    replay = out/'inputs.replay'
    frames, recipe = make_replay(replay, phases(args.game))
    port = free_udp_port()
    command = [sys.executable, str(root/'scripts/run-retroarch-macos.py'),
               '--retroarch', str(args.retroarch), '--core', str(args.core),
               '--content', str(args.rom_directory/(args.game+'.zip')),
               '--output', str(out/'frontend'), '--frames', str(frames), '--replay', str(replay)]
    settings = {'network_cmd_enable': 'true', 'network_cmd_port': str(port),
                'notification_show_screenshot': 'false', 'video_font_enable': 'false',
                'confirm_quit': 'false', 'confirm_reset': 'false', 'global_core_options': 'true',
                'user_language': '0', 'video_smooth': 'false'}
    for key, value in settings.items():
        command += ['--frontend-option', key+'='+value]
    (out/'recipe.json').write_text(json.dumps({'game': args.game, 'phases': recipe,
        'replay_sha256': hashlib.sha256(replay.read_bytes()).hexdigest(),
        'reference': 'SM2-Libretro replay-v1 input records, 16-byte no-state padding',
        'command': command}, indent=2)+'\n')
    captures = []
    start = time.monotonic()
    with (out/'runner.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                elapsed = time.monotonic()-start
                if elapsed > frames/40+60:
                    raise TimeoutError('Input capture exceeded its bounded run')
                if elapsed < 15 or not (out/'frontend/session.json').is_file():
                    time.sleep(.1)
                    continue
                try:
                    image = take_screenshot(process, out/'frontend', port, f'input-{len(captures):03}')
                except RuntimeError:
                    if process.poll() is not None:
                        break
                    raise
                captures.append({'file': str(image.relative_to(out)),
                                 'elapsed': round(time.monotonic()-start, 3)})
                time.sleep(.5)
            code = process.wait(timeout=5)
        finally:
            if process.poll() is None:
                # Let the existing runner close only its own RetroArch child.
                process.send_signal(__import__('signal').SIGINT)
                process.wait(timeout=15)
    result = {'game': args.game, 'exit_code': code, 'captures': captures,
              'status': 'captured_requires_visual_review',
              'core_sha256': hashlib.sha256(args.core.read_bytes()).hexdigest(),
              'limits': 'Scripted Libretro callbacks, not physical controllers or sustained gameplay'}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    if code:
        raise SystemExit(code)
    print(json.dumps({'game': args.game, 'captures': len(captures), 'exit_code': code}))


if __name__ == '__main__':
    main()
