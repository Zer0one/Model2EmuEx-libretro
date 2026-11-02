#!/bin/sh
# Compare an isolated core run with the pristine SAME-REVISION upstream runner.
set -eu
if [ "$#" -ne 3 ]; then
    echo 'Usage: scripts/check-macos.sh /path/upstream /path/game.zip /path/new-output-dir' >&2
    exit 2
fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
upstream=$1
content=$2
out=$3
[ ! -e "$out" ] || { echo 'Output directory must not exist.' >&2; exit 2; }
[ "$(git -C "$upstream" rev-parse HEAD)" = 25d82be56f339c754cc566f771ca9ffb90b69289 ] || {
    echo 'Upstream revision differs from the recorded baseline.' >&2; exit 2;
}
[ -z "$(git -C "$upstream" diff --name-only -- port)" ] || {
    echo 'Upstream port sources have local changes.' >&2; exit 2;
}
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
cd "$root"
make -j4 > "$out/build.log" 2>&1
cc -O2 -g -Isrc/libretro/include $(pkg-config --cflags sdl2) scripts/frontend-check.c \
    $(pkg-config --libs sdl2) -framework OpenGL -lz -o port/build-libretro-macos/frontend-check
CHECK_TIMING=native port/build-libretro-macos/frontend-check "$root/port/build-libretro-macos/model2emuex_dev_libretro.dylib" \
    "$content" 900 "$out" > "$out/frontend.log" 2>&1
name=$(basename "$content" .zip)
cp "$out/core.initial-nvram" "$out/reference-start.nvram"
M2_NVRAM="$out/reference-start.nvram" M2_KEYS='' M2_RAM="$out/upstream.ram" M2_WAV="$out/upstream.wav" \
    "$upstream/port/build-macos/m2run" "$name" 900 "$(dirname "$content")" > "$out/upstream.log" 2>&1
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib, json, sys, wave
p = Path(sys.argv[1])
with wave.open(str(p / 'upstream.wav'), 'rb') as w:
    pcm = w.readframes(w.getnframes())
checks = [('RAM', (p/'core.ram').read_bytes(), (p/'upstream.ram').read_bytes()),
          ('PCM', (p/'core.pcm').read_bytes(), pcm)]
result = {}
for name, core, upstream in checks:
    result[name] = dict(equal=core == upstream, bytes=len(core), sha256=hashlib.sha256(core).hexdigest())
(p/'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
assert all(v['equal'] for v in result.values()), 'Upstream comparison failed'
PY
