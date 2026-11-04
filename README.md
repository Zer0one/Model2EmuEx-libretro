# Model2EmuEx Libretro

[![CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/workflows/libretro-ci.yml/badge.svg)](https://github.com/Zer0one/Model2EmuEx-libretro/actions/workflows/libretro-ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/Zer0one/Model2EmuEx-libretro)](https://github.com/Zer0one/Model2EmuEx-libretro/releases/latest)

An independent Libretro port of [Model2EmuEx](https://github.com/octavioCuatrochio/Model2EmuEx),
the portable emulator derived from ElSemi's Model 2 Emulator. This repository
preserves upstream history and layout; frontend integration lives in
`src/libretro`. Model2EmuEx supplies the emulation. Adapted
[SM2-Emu](https://github.com/dmanlfc/sm2-emu) and
[SM2-Emu Libretro](https://github.com/Zer0one/sm2-emu-libretro) components supply
shared frontend conventions and explicitly integrated functions.

## Download And Installation

Download the package for your platform from
[GitHub Releases](https://github.com/Zer0one/Model2EmuEx-libretro/releases/latest).
Packages target Linux x86_64/ARM64, macOS Apple Silicon/Intel (macOS 13 or later)
and Windows x86_64. A matching-architecture frontend with desktop OpenGL is
required. Actual gameplay evidence is currently concentrated on macOS arm64.

1. Copy `model2emuex_libretro.so`, `.dylib` or `.dll` into the frontend's cores directory.
2. Copy `model2emuex_libretro.info` into its core-information directory.
3. In RetroArch, select the `gl` video driver for this core, then load a supported
   canonical MAME-named ZIP, for example `vf2.zip` or `srallyc.zip`.

The visible name is **Sega - Model 2 (Model2EmuEx)**. The game catalogue and
initial settings templates are embedded; no external `games.xml` is required.
ROMs are not included. Keep parent/shared ROMs beside the selected set or in
the frontend System directory; see [Content And Saves](LIBRETRO.md#content-and-saves).
RetroArch owns Save RAM and Save State paths. Optional custom crosshair PNGs
belong in `<System>/model2emuex/crosshairs`.

Each release includes the core, matching information file, notices, checksums,
source revision and the corresponding complete source archive.

## Features

- Desktop OpenGL rendering at 1x–4x, native Nearest/Bilinear/Trilinear filtering,
  shadows/fences, colour controls and separate aspect/widescreen controls.
- 60 Hz default or native 58 Hz A/V timing; native SCSP output and source gains.
- Game-aware controller profiles, driving/gear/gun controls, Service/Test,
  crosshairs and Libretro rumble callbacks.
- Game-specific NVRAM options and automatic initial setup with existing-save
  precedence; standalone-compatible raw 65,664-byte Save RAM.
- Native Save States with validation/recovery. External linked sessions cannot
  be serialized; offline local loopback remains available.
- Frontend-owned Netpacket linked cabinets and automatic network-role settings.
- In-frame timing/FPS diagnostics.

See the [Core Manual](LIBRETRO.md),
[Implemented Options](CORE_OPTIONS_IMPLEMENTED_REVIEW.md) and
[Roadmap](ROADMAP.md) for controls, defaults and applicability.

## Current Coverage

The macOS arm64 core has actual RetroArch rendering, persistence, Save State
and targeted linked-cabinet evidence. Native Input Tests verify 15 Sega Rally
and 18 VF2 cases. These checks do not certify every game, physical controllers,
lightguns, force feedback or audible output. Model 2/2A execution is available;
distribution builds include the native Model 2B SHARC reconstruction and all
35 Model 2B sets from the pinned MAME driver. Use `SHARC=1` to enable the
same support in a local source build. Version 0.3.0 adds Model
2C with `TGPX4=1`: 13 native records, complete snapshots and representative
macOS/Batocera/Windows-VM evidence. Use `make SHARC=1 TGPX4=1 -j4` for both
reconstructions. The five-platform distribution recipe enables both explicitly. See [Validation](VALIDATION.md)
for measured scope and the remaining physical/audio qualification limits.

Native cooperative layouts, separate core keyboard input, Hide Shot Flash and
an additional SCSP low-pass filter are excluded. Keyboard mapping remains a
frontend function. Linked-cabinet coverage is documented per game in
[External Linked Cabinets](EXTERNAL_LINKED_CABINETS.md).

## Build

Use a C/C++20 compiler, Make, zlib and pthreads (Winpthreads on MinGW).
Apple's command-line toolchain needs no additional core dependencies:

```sh
make SHARC=1 TGPX4=1 release -j4
# Linux: make platform=unix SHARC=1 TGPX4=1 release -j4
# MinGW: make platform=win SHARC=1 TGPX4=1 release -j4
```

Output: `port/build-release-macos/model2emuex_libretro.dylib`.
The existing `make -j4` development target and `make standalone -j4` remain
separate. Building the core does not require SDL; diagnostic/standalone tools
have their own requirements. See [Build And Usage](LIBRETRO.md#build).

## Credits And Terms

ElSemi authored the original emulator; octavioCuatrochio maintains the native
Model2EmuEx project. Daniel Martin (dmanlfc) and SM2 contributors authored the
adapted SM2 components. Imported notices, changes and exact revisions are
retained in [Credits And Source Notices](LIBRETRO.md#credits-and-source-notices),
[NOTICE.md](NOTICE.md) and the source import manifests. The integrated native
baseline is `25d82be56f339c754cc566f771ca9ffb90b69289` (`daytona_decomp`).

Original port contributions use GPL-3.0-or-later; see [LICENSE](LICENSE) and
[the precise scope](NOTICE.md#original-port-contributions). The native baseline
does not declare an overall license for its recovered code.
Component licenses do not establish blanket terms for the combined project;
see the scope described in NOTICE.md. This repository is an independent
modified port and is not the original ElSemi release or an official SM2 build.

## Original Upstream Documentation

The following text is preserved for upstream history. Its standalone platform,
cooperative-mode and gameplay statements describe upstream, not this Libretro
release's supported platforms or qualification.

---

# Sega Model 2 Emulator 1.1a (ElSemi) - Ghidra decompilation

A decompilation of ElSemi's Model 2 Emulator and a portable C port of it
(`port/`), aimed at Linux and Windows PCs and at an Android TV box with an
Allwinner H3 (32-bit ARM Cortex-A7, Mali-400 GPU).

## Branches
- `master`: the decompilation and the portable port, everything on one thread.
- `optimized`: the same port, faster (sound, emulation and drawing on separate threads, less work per frame, same pictures and sound), and building for Windows and desktop OpenGL too.
- `coop`: `optimized` plus two-player linked play of Daytona USA in one window (`--coop`, split screen), and a launcher window (Games and Configuration tabs).

## Games known to work
- Daytona USA (`daytona`): played through races, with sound, controls and gears.
- Virtua Fighter 2 (`vf2`) and Sega Rally Championship (`srallyc`): boot and run their attract mode with 2D, 3D and sound; gameplay not tested in depth.
- The other games in the list may boot but haven't been tried.

## Platforms
- Linux x86 (SDL2; desktop OpenGL, or OpenGL ES 2 with `make GL=gles`): builds and runs; everything above was tested here.
- Windows x86-64 (MinGW-w64: MSYS2 or cross-compiled; desktop OpenGL): builds; tested under Wine, where the emulation, sound and pictures match Linux. Not yet tried on a real Windows PC.
- Android on the Allwinner H3 (TV box, Mali-400): the app (`make apk`, see `port/README.md`; `daytona_y2k`'s `make apk` with Daytona's program recompiled) runs Daytona USA with 3D, sound and widescreen, drawn at 683x384 and scaled to 1080p by the display. Full speed (57.5 fps) in the menus and most of a race, with frame skip covering the frames the drawing can't; the heaviest scenes drop to 30-45 fps (the TGP interpreter), and the box's thermal limit (85 °C) takes a CPU core away after a while.

## Run example
    cd port
    make
    build/m2emu

opens the launcher: choose the ROM folder in the Games tab, set the options
in the Configuration tab, and play.

Straight from the command line, Daytona USA in a 1920x1080 window with the
colour saturation at 1.5, ROMs (MAME-style `daytona.zip`) in `~/Desktop/ROMs`:

    build/m2emu --no-gui -r ~/Desktop/ROMs --size 1920x1080 --saturation 1.5 daytona

Add `--fullscreen` to use the whole screen at its own resolution (1080p on
a 1080p display). On Windows the program is `build\m2emu.exe` (building:
`port/README.md`, "Windows"). Two players linked: add `--coop`. All options
and controls: `port/README.md`; where the ROMs go on each platform: its
section "Where the ROMs go".

Android (TV boxes): `port/android/release.sh` builds the final app,
`port/build-release/m2emu.apk`; the ROMs go in
`/sdcard/Android/data/org.m2emu/files/roms` (`port/README.md`, "Android").

Input: `../M2emulator_1.1a/EMULATOR.EXE` (PE32, MSVC, not packed, no PDB).
`emulator_multicpu.exe` differs by 6 bytes (PE checksum + one constant), so it is not decompiled separately.

Tool: Ghidra 12.1.3 (`~/.local/opt/ghidra_12.1.3_PUBLIC`), headless auto-analysis + a C export script.

## Files
- `ghidra_project/` - the analysed Ghidra project. Open with `~/.local/opt/ghidra_12.1.3_PUBLIC/ghidraRun`
  and rename/retype things there; re-export when done.
- `src/all_functions.c` - decompiled C for all 2041 functions (0 decompile failures).
- `src/prototypes.h`, `src/types.h` - recovered signatures / data types.
- `src/functions.tsv` - address, name, size of every function.
- `src/strings.tsv` - defined strings with addresses (best starting point for naming functions).

## Map of the parts that were ported (by address)
- 0x440000-0x4a0000  A68K 68000 core (x86 assembly; replaced by Musashi in the port)
- 0x4a81c0           TGP (MB86234) interpreter; 0x4aa040 SCSP DSP recompiler
- 0x4ab000-0x4b3000  SCSP, MultiPCM, YM2612/YM3438
- 0x4b6000-0x4bbdd0  3D renderer: display-list parsers 0x4b9f70 / 0x4baa60, object processor 0x4bb400
- SHARC (Model 2B), recovered in opt-in research builds: compute decoder 0x4be800, program predecoder
  0x4bf610, execution loop 0x4be000, reset 0x4c0230. Arithmetic targets also
  occur near 0x460f40; 0x4bbdd0 is renderer initialization, not SHARC.
  See [Native SHARC Reconstruction](SHARC_RECONSTRUCTION.md) for evidence and
  remaining qualification. Default and published builds still exclude Model 2B.
- 0x4c5290-0x4cf960  Model 2 board: copro drivers, I/O handlers, frame loop 0x4cc7a0, init 0x4cd450,
                     per-game input routines (0x4c9080 Daytona, 0x4cb870 Sega Rally, ...)
- 0x451a90-0x453400  tilemap line composer and tile decoder
- 0x4ed5e0-0x4ee200  tilemap layer drawing
- The i960 core's opcode handlers are only reachable through tables (see `i960/`, `tools/I960Label.java`).
- Statically linked: MSVC runtime + STL, Lua 5.1.4, zlib 1.2.2, minizip 0.22.

## The port
`port/` is a portable C rewrite that runs Daytona USA, Virtua Fighter 2 and
Sega Rally with video, sound and input (SDL2 + OpenGL, or OpenGL ES 2 with
`make GL=gles`), on Linux and Windows. The machine, the drawing and the
sound run on separate threads. `--coop` runs two linked Daytona USA
machines in one window for two players (split screen). **Start with
`port/README.md`**: build, options, controls, save data and debugging.
Each subsystem documents the original's bugs and the port's differences in
its own `QUIRKS.md` (`port/i960`, `port/tgp`, `port/m2`, `port/snd`).

## Tools
- `tools/ExportDecomp.java`: whole-program decompile export (headless Ghidra).
- `tools/RegionExport.java`: create functions in an address range (pointer-table
  code) and export their decompiles: `analyzeHeadless ... -postScript RegionExport.java out.c start end [extra entries]`.
- `tools/I960Label.java`, `tools/i960tab.py`, `tools/mnem.py`: i960 opcode table recovery.
- `tools/dump_games.py` + `tools/gen_gamedb.py`: dump the game definitions (ROM lists,
  inputs, hooks) by running the EXE's static initialisers under Unicorn, then
  generate `port/m2/gamedb.inc`.
- `tools/i960dis.py`, `tools/m68kdis.c`: disassemblers for i960 and 68000 dumps.
- `tools/ptrtables.py`: pointer-table finder.

## Status of the raw decompile
Raw decompiler output, **not compilable**: `gcc -m32 -fsyntax-only` reports ~16k errors
(undeclared globals, unknown prototypes, MSVC ABI artefacts like `in_ECX` thiscall params).
Platform layer is Direct3D 9 + D3DX9 (HLSL pixel shaders), DirectInput 8, XInput, Winsock, Win32 GUI.
