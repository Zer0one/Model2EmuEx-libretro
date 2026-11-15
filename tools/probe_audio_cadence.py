#!/usr/bin/env python3
"""Build a temporary macOS comparison core with the native ElSemi audio block size."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def diagnostic_source():
    # Tap the board before cabinet mixing or frontend conversion. Audio clocks
    # and all emulated objects come from the production core.
    source = (ROOT / 'src/libretro/libretro.c').read_text()
    start = source.index('    int16_t cabinet_samples[4096];')
    publish = '    if (!send_audio(mixed, mixed_frames, count)) return;'
    end = source.index(publish, start) + len(publish)
    return source[:start] + '    if (!send_audio(samples, board_frames, board_frames)) return;' + source[end:]


def compare_transport(raw, transport, timing):
    """Check every frontend stereo sample against the captured native board PCM."""
    digest = hashlib.sha256()
    frames = samples = 0
    debt = 0.0
    with raw.open('rb') as source, transport.open('rb') as frontend:
        while block := source.read(760 * 4):
            if len(block) != 760 * 4:
                raise ValueError(f'Incomplete board block at frame {frames + 1}')
            debt += 44100 / 58
            native_count = int(debt)
            debt -= native_count
            count = native_count if timing == 'native' else 735
            expected = block
            if count != 760:
                values = list(struct.iter_unpack('<hh', block))
                expected = bytearray()
                denominator = count - 1
                for index in range(count):
                    left, fraction = divmod(index * 759, denominator)
                    right = min(left + 1, 759)
                    for a, b in zip(values[left], values[right]):
                        mixed = a * (denominator - fraction) + b * fraction
                        magnitude = abs(mixed) // denominator
                        expected.extend(struct.pack('<h', -magnitude if mixed < 0 else magnitude))
            actual = frontend.read(4 * count)
            if actual != expected:
                raise ValueError(f'Transport PCM mismatch at machine frame {frames + 1}')
            digest.update(actual)
            frames += 1
            samples += count
        if not frames or frontend.read(1):
            raise ValueError('Empty board capture or excess transport samples')
    return dict(machine_frames=frames, stereo_samples=samples, sha256=digest.hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    for mode in ('raw', 'transport'):
        build_mode = modes.add_parser(mode)
        build_mode.add_argument('--output', type=Path, required=True, help='New directory for diagnostic artifacts')
        build_mode.add_argument('--build', type=Path, required=True, help='Qualified SHARC/TGPX4/A68K macOS build directory')
    compare = modes.add_parser('compare', help='Verify transported PCM against a fixed-block board capture')
    compare.add_argument('raw', type=Path)
    compare.add_argument('transport', type=Path)
    compare.add_argument('--timing', choices=('native', '60hz'), required=True)
    args = parser.parse_args()
    if args.mode == 'compare':
        print(json.dumps(compare_transport(args.raw, args.transport, args.timing), indent=2))
        return
    build = args.build.resolve(strict=True)
    if not (build / '.features-1-1-1').is_file():
        parser.error('Expected an existing SHARC/TGPX4/A68K build')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if args.mode == 'transport':
        # The production core now implements the qualified transport.
        shutil.copy2(build / 'model2emuex_libretro.dylib', out / 'model2emuex_libretro.dylib')
        return
    (out / 'adapter.c').write_text(diagnostic_source())
    makefile = out / 'probe.mk'
    makefile.write_text('''include Makefile
.PHONY: cadence-probe
cadence-probe: $(OBJ)
\t$(CC) $(CPPFLAGS) $(CFLAGS) -Isrc/libretro -c "$(PROBE_DIR)/adapter.c" -o "$(PROBE_DIR)/adapter.o"
\t$(CXX) $(SHARED) -o "$(PROBE_DIR)/model2emuex_libretro.$(EXT)" $(filter-out $(BUILD)/adapter.o,$(OBJ)) "$(PROBE_DIR)/adapter.o" $(LIBS)
''')
    subprocess.run(['make', '-f', str(makefile), 'cadence-probe', 'platform=osx', 'SHARC=1',
                    'TGPX4=1', 'A68K=1', f'BUILD={build}', f'PROBE_DIR={out}'], cwd=ROOT,
                   env=dict(os.environ, MACOSX_DEPLOYMENT_TARGET='13.0'), check=True)


if __name__ == '__main__':
    main()
