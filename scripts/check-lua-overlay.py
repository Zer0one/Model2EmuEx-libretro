#!/usr/bin/env python3
"""Exercise Lua callbacks, reload, options, fonts and image rendering on macOS."""
import argparse
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile
import zlib


def chunk(name, data):
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))


def run(core, rom, ttf):
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="m2-lua-") as directory:
        work = Path(directory)
        scripts = work / "model2emuex/scripts"
        assets = scripts / "assets"
        assets.mkdir(parents=True)
        (assets / "Probe Bold.ttf").symlink_to(ttf)
        pixel = bytes([13, 187, 229])
        data = (b"\0" + pixel * 16) * 16
        (assets / "probe.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", 16, 16, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b""))
        (scripts / "probe_module.lua").write_text("return { loaded = 1 }\n")
        (scripts / (rom.stem + ".lua")).write_text("""
local module = require('probe_module')
function audit(s)
    local f = assert(io.open(os.getenv("M2_LUA_AUDIT"), "a"))
    f:write(s, "\\n")
    f:close()
end
audit("load " .. module.loaded)
module.loaded = module.loaded + 1
Options = { probe = { name = "Probe", changefunc = function(v) audit("change " .. v) end,
    runfunc = function(v) assert(v == 1) end } }
function Init()
    audit("init")
    surface = assert(Video_CreateSurfaceFromFile("probe.png"))
    font = Video_CreateFont("Probe", 20, 1)
    fallback = Video_CreateFont("Missing", 18, 0)
    frame = 0
end
function Frame()
    frame = frame + 1
    audit("frame " .. frame)
end
function PostDraw()
    audit("draw " .. frame)
    Video_DrawSurface(surface, 64, 64)
    Video_DrawTextWithFont(font, 100, 64, "TTF", 0x19DC90)
    Video_DrawTextWithFont(fallback, 160, 64, "Built-in", 0xCC58F0)
end
function Reset() audit("reset") end
function End() audit("end") end
""")
        harness = work / "frontend-check"
        flags = shlex.split(subprocess.check_output(["pkg-config", "--cflags", "--libs", "sdl2"], text=True))
        subprocess.run(["cc", "-O2", "-Isrc/libretro/include", "scripts/frontend-check.c", *flags,
                        "-framework", "OpenGL", "-lz", "-o", harness], cwd=repo, check=True)
        audit = work / "events"
        env = {k:v for k,v in os.environ.items() if not k.startswith("CHECK_")}
        env.update(CHECK_SYSTEM=str(work), CHECK_LUA_OPTION="model2emuex_lua_" + rom.stem + "_probe",
                   CHECK_STATE="1", M2_LUA_AUDIT=str(audit))
        result = subprocess.run([harness, core, rom, "100", work], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(result.stdout, end="")
        result.check_returncode()
        lines = audit.read_text().splitlines()
        assert lines.count("load 1") == 1 and lines.count("load 2") == 1, lines[:20]
        assert lines.count("init") == 1 and lines.count("end") == 1
        assert "change 1" in lines
        for i, event in enumerate(lines):
            if event.startswith("draw "):
                assert lines[i-1] == "frame " + event.split()[1], lines[i-2:i+2]
        assert lines.count("frame 1") == 1 and "frame 160" in lines
        assert "Missing.ttf" in result.stdout
        assert "Probe Bold.ttf" not in result.stdout and "Lua PostDraw:" not in result.stdout
        pixels = (work / "core.ppm").read_bytes().split(b"\n", 3)[3]
        def colours(x, y, w, h):
            return {pixels[(row*496+col)*3:(row*496+col)*3+3]
                    for row in range(y, y+h) for col in range(x, x+w)}
        assert colours(66, 66, 12, 12) == {pixel}
        assert bytes.fromhex("19dc90") in colours(100,64,54,30)
        assert bytes.fromhex("cc58f0") in colours(160,64,94,30)
        print(json.dumps({"game": rom.stem, "callbacks": len(lines),
                          "same_vm_reload": True, "state_keeps_lua": True,
                          "postdraw_image_and_two_fonts": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--ttf", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"))
    args = parser.parse_args()
    run(*(path.resolve(strict=True) for path in (args.core, args.rom, args.ttf)))
