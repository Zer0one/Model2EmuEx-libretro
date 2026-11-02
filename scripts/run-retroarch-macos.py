#!/usr/bin/env python3
"""Run an installed RetroArch against the local core with isolated test files."""
import argparse
from pathlib import Path
import json
import shutil
import socket
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--retroarch', type=Path, required=True)
parser.add_argument('--content', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='New directory only')
parser.add_argument('--frames', type=int, default=1800)
parser.add_argument('--core', type=Path, help='Core to verify; defaults to the local development build')
parser.add_argument('--save-ram', type=Path, help='Read an existing raw test SRAM into the isolated saves directory')
parser.add_argument('--system', type=Path, help='Existing frontend System resources; no files are copied or written there')
parser.add_argument('--replay', type=Path, help='Existing RetroArch input replay (input data only)')
parser.add_argument('--video-driver', choices=('gl','vulkan'), default='gl')
parser.add_argument('--core-video-driver', choices=('gl','vulkan'), help='Test a core-specific driver override')
parser.add_argument('--core-option', action='append', default=[], metavar='KEY=VALUE', help='Isolated core option override; repeatable')
parser.add_argument('--frontend-option', action='append', default=[], metavar='KEY=VALUE', help='Isolated frontend setting override; repeatable')
parser.add_argument('--interactive-seconds', type=int, help='Bounded interactive run instead of a frame-limited capture (30–900 seconds)')
args = parser.parse_args()
if not 1 <= args.frames <= 7200:
    parser.error('--frames must be between 1 and 7200')
if args.interactive_seconds is not None and not 30 <= args.interactive_seconds <= 900:
    parser.error('--interactive-seconds must be between 30 and 900')
root = Path(__file__).resolve().parent.parent
core = (args.core or root / 'port/build-libretro-macos/model2emuex_dev_libretro.dylib').resolve()
for path in (args.retroarch, args.content, core):
    if not path.is_file():
        parser.error(f'File not found: {path}')
if args.system and not args.system.is_dir():
    parser.error(f'System directory not found: {args.system}')
if args.replay and not args.replay.is_file():
    parser.error(f'Replay not found: {args.replay}')
option_values={}
for item in args.core_option:
    key,separator,value=item.partition('=')
    if not separator or not key.startswith('model2emuex_') or any(ord(ch)<32 or ch in (chr(34),chr(92)) for ch in key+value):
        parser.error('Invalid --core-option; use model2emuex_key=value')
    option_values[key]=value
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
for name in ('saves', 'states', 'screenshots', 'config', 'system', 'info', 'logs', 'playlists'):
    (out/name).mkdir()
if args.save_ram:
    seed = args.save_ram.resolve(strict=True).read_bytes()
    if len(seed) != 65664:
        parser.error('--save-ram must contain the native 65,664-byte raw buffer')
    (out/'saves'/(args.content.stem+'.srm')).write_bytes(seed)
shutil.copy2(root/'src/libretro/model2emuex_dev_libretro.info', out/'info/model2emuex_dev_libretro.info')
if args.core_video_driver:
    override = out/'config/Model2EmuEx/Model2EmuEx.cfg'
    override.parent.mkdir()
    override.write_text(f'video_driver = "{args.core_video_driver}"\n')
settings = {
    'video_driver': args.video_driver, 'driver_switch_enable': 'true',
    'audio_driver': 'coreaudio', 'menu_driver': 'ozone',
    'video_fullscreen': 'false', 'video_windowed_fullscreen': 'false',
    'video_scale': '2', 'video_threaded': 'false', 'video_vsync': 'true',
    'video_shader_enable': 'false', 'config_save_on_exit': 'false',
    'content_runtime_log': 'false', 'content_runtime_log_aggregate': 'false',
    'runtime_log_directory': str(out/'logs'), 'playlist_directory': str(out/'playlists'),
    'auto_overrides_enable': 'true' if args.core_video_driver else 'false', 'auto_remaps_enable': 'false',
    'auto_shaders_enable': 'false', 'savestate_auto_load': 'false',
    'savestate_auto_save': 'false', 'rewind_enable': 'false',
    'save_file_compression': 'false', 'sort_savefiles_enable': 'false',
    'sort_savefiles_by_content_enable': 'false',
    'run_ahead_enabled': 'false', 'input_autodetect_enable': 'false',
    'pause_nonactive': 'false', 'menu_pause_libretro': 'true',
    'input_player1_start': 'enter', 'input_player1_select': 'rshift',
    'input_player1_a': 'x', 'input_player1_b': 'z', 'input_player1_y': 's',
    'core_options_path': str(out/'core-options.cfg'),
    'libretro_info_path': str(out/'info'),
    'libretro_directory': str(core.parent),
    'rgui_config_directory': str(out/'config'),
}
for key, folder in [('savefile_directory', 'saves'), ('savestate_directory', 'states'),
                    ('screenshot_directory', 'screenshots'), ('system_directory', 'system')]:
    settings[key] = str(out/folder)
if args.system:
    settings['system_directory'] = str(args.system.resolve())
for item in args.frontend_option:
    key, separator, value = item.partition('=')
    if not separator or not key.replace('_', '').isalnum() or any(ord(ch)<32 or ch in (chr(34),chr(92)) for ch in value):
        parser.error('Invalid --frontend-option; use KEY=VALUE')
    if key in {'core_options_path', 'libretro_info_path', 'libretro_directory', 'rgui_config_directory',
               'savefile_directory', 'savestate_directory', 'screenshot_directory', 'system_directory',
               'runtime_log_directory', 'playlist_directory', 'config_save_on_exit'}:
        parser.error(f'--frontend-option cannot replace the isolated setting {key}')
    settings[key] = value
command_port = None
if args.interactive_seconds:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1', 0))
        command_port = sock.getsockname()[1]
    settings.update(network_cmd_enable='true', network_cmd_port=str(command_port))
(out/'core-options.cfg').write_text(''.join(f'{key} = "{value}"\n' for key,value in option_values.items()))
config = out/'retroarch.cfg'
config.write_text(''.join(f'{k} = "{v}"\n' for k, v in settings.items()))
command = [str(args.retroarch), '-v', '-c', str(config), '-L', str(core)]
if args.replay:
    command += ['-P', str(args.replay.resolve())]
if not args.interactive_seconds:
    command += [f'--max-frames={args.frames}', '--max-frames-ss', f'--max-frames-ss-path={out}/final.png']
command.append(str(args.content))
start = time.monotonic()
with (out/'run.log').open('w') as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    (out/'session.json').write_text(json.dumps({'pid':process.pid, 'command_port':command_port,
        'command':command, 'interactive_seconds':args.interactive_seconds}, indent=2)+'\n')
    timed_out = False
    try:
        code = process.wait(timeout=args.interactive_seconds or args.frames/40 + 60)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        timed_out = True
        if command_port:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(b'QUIT\n', ('127.0.0.1', command_port))
        else:
            process.terminate()
        try:
            code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
result = {'pid': process.pid, 'exit_code': code, 'timed_out': timed_out,
          'elapsed_seconds': round(time.monotonic()-start, 2), 'command': command,
          'screenshot': (out/'final.png').is_file(),
          'interactive_seconds': args.interactive_seconds,
          'captured_screenshots': len(list((out/'screenshots').glob('*.png')))}
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
raise SystemExit(1 if timed_out or (not args.interactive_seconds and code == 0 and not result['screenshot']) else code)
