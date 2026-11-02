# Model2EmuEx Libretro

An independent Libretro port of Model2EmuEx, initially targeting macOS Apple Silicon. The original Git history and source layout are retained. Upstream source: <https://github.com/octavioCuatrochio/Model2EmuEx>, branch `daytona_decomp`, revision `25d82be56f339c754cc566f771ca9ffb90b69289`.

## Current Status

The core builds natively on macOS arm64 and renders in RetroArch 1.22.2 using desktop OpenGL. It delivers stereo PCM, SM2 controller profiles, gun inputs, rumble callbacks, source gains, A/V Timing, crosshair presentation, Save States and persistent backup RAM plus EEPROM. Model 2B/2C execution remains limited by the upstream machine implementation; their frontend profiles/data are retained. External Linked Cabinets and ANRS are integrated, with two-instance local Daytona race startup and Sega Rally restart recovery verified. Every set retains a local loopback board when external linking is disabled, following SM2. Native enable/role settings and external-link support remain separate; offline Save States are supported. see [External Linked Cabinets](EXTERNAL_LINKED_CABINETS.md). Broader qualification remains in the roadmap.

The complete SM2 implementation applicability assessment, including future Model 2B/2C frontend preparation, is in [SM2 Applicability](SM2_APPLICABILITY.md).

See [Validation](VALIDATION.md) for measured results and limitations, [Design](LIBRETRO_DESIGN.md) for interfaces, and [Roadmap](ROADMAP.md) for follow-up work and discussion items. The upstream documentation remains below the Libretro notice in the root README.

## Build

Source attribution and the current publication limits are recorded under
[Credits And Source Notices](#credits-and-source-notices).

Requirements: Apple's command-line C/C++ toolchain, Make and system zlib. These were already installed for the initial build. The core does not require SDL, Homebrew runtime libraries, Rosetta or a separate window. The diagnostic panel compiles the already bundled Dear ImGui sources directly into the core.

```sh
make -j4
```

Output: `port/build-libretro-macos/model2emuex_dev_libretro.dylib`.

The build currently targets the host architecture. Apple Silicon arm64 is verified; Intel and universal distribution are not yet verified. The matching development info file is `src/libretro/model2emuex_dev_libretro.info`. The build itself does not install files. By explicit user request, the current development core and matching info file were copied to the configured local RetroArch directories on 2026-10-20; see Local Development Installation below.

The original programs remain available:

```sh
make standalone -j4
```

Their separate build uses the original SDL/pkg-config requirements from `port/README.md`.

## Content And Saves

Load a ZIP using its canonical MAME set name, such as `vf2.zip`, `srallyc.zip` or `daytona93.zip`. The Libretro build uses a pinned MAME-aligned 28-entry catalogue; `srallyp` is excluded by user decision. The loader searches the content directory and frontend system directory for the selected set, its MAME parent and the legacy shared `model2.zip` compatibility location. A separate `model2.zip` is unnecessary when all consumed files are already available in the MAME set/parent archives. It does not search arbitrary game ZIPs. ROMs are neither bundled nor extracted/repacked by the core. See [MAME ROM Set Alignment](MAME_ROMSET_ALIGNMENT.md) for the complete mapping and payload differences.

RetroArch owns the `.srm` file. Its payload is 65,536 bytes of backup RAM followed by 128 bytes of EEPROM, matching the upstream DAT payload. The adapter initializes fresh storage using only SM2 templates and their explicit compatible-parent policy, and imports frontend Save RAM before the first emulated frame. Without an applicable template, machine defaults remain; the native Daytona setup fallback is not used. Reset preserves that storage. Keep existing production saves separate until broader compatibility verification is complete.

## Save States

Use RetroArch’s normal Save State / Load State commands. The core restores native CPU/TGP/audio/device/geometry and relevant input continuation state. Current Core Options remain active; enabled operator overrides are reapplied on Resume and reset once if needed. The format is specific to this core and is currently qualified on macOS arm64. Save/load are refused with a notification while Linked Cabinets is configured above one, matching SM2. See [Save States](SAVE_STATES.md) for compatibility and tests.

## Controls

The unchanged SM2 input engine and embedded metadata supply game-specific profiles and descriptors for all 28 current set identities. VF2-family A/B/Y map to Punch/Kick/Guard. L3 = Service, R3 = Test; Controller Profile Type defaults Normal + Test/Service and can omit these supplemental inputs. Driving, gear, gun and special-cabinet selectors follow SM2 conventions through native port/ADC translation. Keyboard mappings belong to the frontend; the core does not poll keyboard devices. Physical controller, gun and motor output remain unverified. See [Shared Features](COMMON_FEATURES.md).

## Core Options

See [Native Emulator Selectors](NATIVE_OPTIONS.md) for the full native inventory, priorities, defaults and pending controls.

Video → **Internal Resolution**: 1x, 2x, 3x or 4x; default 1x. Native rendering is 496 × 384 with a 4:3 display aspect. Changes apply on return to the game without resetting the machine. The current upstream implementation reallocates its rendering target dynamically, so SM2's restart-required wording would be inaccurate here. Legacy registration retains the same numeric values and default.

Video → **3D Texture Filtering**: Nearest, Bilinear or Trilinear; default Nearest. These are the emulator's native filters, as approved on 2026-10-20. Changes apply on return to the game without a reset. If a filter shader is unavailable, upstream falls back to the next supported filter. This controls 3D textures, not the frontend's final display scaling.

Native emulator selectors complement the common SM2-style options. Gamepad Rumble, NVRAM Settings and the other applicable shared contracts remain in scope and must be adapted to this emulator's machine capabilities. Their presence in the roadmap is not an implementation claim. Native Shadows And Fences, Saturation and Gamma Red/Green/Blue selectors are implemented. Separate keyboard selectors are excluded by user decision. Colour settings apply without reset. No placeholder settings are exposed. System → ROM CRC Verification defaults Enabled, computes checksums from actual loaded payload bytes and applies on content reload.

[Implemented Core Options Review](CORE_OPTIONS_IMPLEMENTED_REVIEW.md) lists the actual registered options, defaults, SM2 equivalents and native adaptations. [Shared Features](COMMON_FEATURES.md) records input/rumble/audio/crosshair lifecycle and validation limits. A/V Timing now defaults to 60 Hz by user decision; Native selects the 58 Hz declared by this emulator. Timing changes require content reload.

The user chose native SCSP output: no added 8 kHz low-pass filter or corresponding selector. Source gains and the approved A/V Timing choices retain their documented behavior.

Video → Timing / FPS Overlay defaults Off and offers Auto plus 11–14 px text. It reuses the SM2 panel with real destination timing measurements. See [Timing Overlay](TIMING_OVERLAY.md) for measurements and limits.

## Repeatable Checks

ROM-free smoke check: `python3 scripts/check-abi.py port/build-libretro-macos/model2emuex_dev_libretro.dylib`.

The GL harness requires the existing SDL2 development environment only for testing. First build pristine upstream's `port/build-macos/m2run` using its documented command. Then:

```sh
scripts/check-macos.sh /path/to/Model2EmuEx /path/to/vf2.zip /path/to/new-audit-directory
```

The output directory must be new. The script explicitly selects Native A/V Timing, verifies the pristine upstream revision, runs 900 frames, and compares main RAM and raw PCM. It also checks nonzero frontend framebuffers, resolution updates, graphics-resource recreation, reset, SRAM import and unload/reload. Run it with access to the macOS display; a restricted execution sandbox can prevent SDL from enumerating displays.

For a bounded real frontend test:

```sh
python3 scripts/run-retroarch-macos.py \
  --retroarch '/path/to/RetroArch.app/Contents/MacOS/RetroArch' \
  --content /path/to/vf2.zip \
  --output /path/to/new-retroarch-audit-directory
```

The runner uses desktop `gl`, a new config/options/save hierarchy and a final screenshot. It records the owned PID and outcome and bounds execution with a timeout. It does not modify the installed core or normal frontend configuration. The selected A/V cadence is reported; frontend refresh-rate/audio synchronization can alter wall-clock pacing.

## Local Development Installation

Installed by explicit user request on 2026-10-20:

- `~/Library/Application Support/RetroArch/cores/model2emuex_dev_libretro.dylib`
- `~/Library/Application Support/RetroArch/info/model2emuex_dev_libretro.info`
- `~/Library/Application Support/RetroArch/config/Model2EmuEx/Model2EmuEx.cfg`, containing only `video_driver = "gl"`.

The core appears as **Sega - Model 2 (Model2EmuEx)**. The scoped video override is required with the current local RetroArch 1.22.2: starting from global Vulkan without it selected glcore, which failed to initialize this OpenGL 2.1 renderer. The tested core-specific override selects gl successfully. The global RetroArch configuration retains Vulkan. No release/updater core was replaced.

The installed core was exercised for 900 frames in local RetroArch with isolated settings/saves and a 3D VF2 attract screenshot. Hashes, destinations and source paths are in `port/build-libretro-macos/audit/local-retroarch-install/installation.json`. Installation does not mark the remaining roadmap items complete. The manifest identifies the installed build; see VALIDATION.md for the latest evidence.

## SCSP Streaming Timing

The local SCSP scheduling correction prevents reproduced Sega Rally stream truncation and applies to both the core and this repository’s standalone. Run `make check-sound` for the ROM-free scheduling regression. Active SCSP PCM intentionally differs from the historical pristine baseline; complete sound accuracy and listening confirmation remain open. See [Sega Rally Audio Diagnostic](AUDIO_SRALLYC_DIAGNOSTIC.md).


## Manx TT Cabinet Audio

Audio → **Manx TT: Cabinet Audio** follows SM2, defaults Enabled and uses the
existing NVRAM Cabinet Type. Twin selects Twin sound ROMs; Deluxe selects its
sound ROMs and optional additional Model 1 board. Disabled retains selected-set
sound ROMs while preserving required Deluxe hardware. Missing optional donors
produce SM2's fallback notices. No new save or ROM paths are created.

See [Manx TT Cabinet Audio](MANX_TT_CABINET_AUDIO.md) for sources, native
integration, guarded Save State compatibility and verification limits.


M24 local delivery (2026-10-22): source/installed hash
`234d6b9c01c88f953bcbf7f9da1a79687e8262878fdc7acacb5468c1b6452949`; matching info and scoped/global
configuration preservation are recorded in
`port/build-libretro-macos/audit/m24-manxtt/final-install/deployment.json`.
The installed core completed an isolated 900-frame `manxttc` Deluxe-audio run
in RetroArch, and the same binary passed exact Deluxe Save State continuation.
See VALIDATION.md for evidence levels and limits.

## Credits And Source Notices

Model2EmuEx Libretro is an independent adaptation of
[octavioCuatrochio/Model2EmuEx](https://github.com/octavioCuatrochio/Model2EmuEx),
branch `daytona_decomp`, based on revision
`25d82be56f339c754cc566f771ca9ffb90b69289`. The native project's README identifies
its origin in ElSemi's Model 2 Emulator 1.1a and the recovered/portable code.
This port preserves that attribution; it is not the original ElSemi release.

The core incorporates adapted components from
[sm2-emu](https://github.com/dmanlfc/sm2-emu) by Daniel Martin (dmanlfc) and its
contributors, through [SM2-Emu Libretro](https://github.com/Zer0one/sm2-emu-libretro).
Those components support approved frontend/input/persistence/network functions
and the Manx TT serial device. Model2EmuEx remains the emulation engine. The
adapted source, changed components and donor hashes are identified by the
existing [import metadata](src/libretro/sm2/IMPORT.json) and
[serial-device import metadata](port/snd/sm2/IMPORT.json). The matching Core
Information metadata also credits the SM2 authors and links to both origins.

| Component | Retained Source Notice And Scope |
| --- | --- |
| SM2 components | Original per-file SPDX/copyright headers, [LICENSE.sm2](src/libretro/sm2/LICENSE.sm2), [NOTICE.sm2](src/libretro/sm2/NOTICE.sm2) and the referenced [BSD-3-Clause text](src/libretro/sm2/licenses/BSD-3-Clause.txt). The unchanged donor NOTICE describes the larger donor project; it does not mean every listed donor dependency is present here. |
| Libretro API header | The API header's own permission/copyright notice is retained in [libretro.h](src/libretro/include/libretro.h), byte-identical to the inspected donor copy. Its notice expressly applies to that header. |
| Musashi | Karl Stenerud's permission/copyright text is retained in [m68k.h](port/m68k/m68k.h). |
| SoftFloat 2b | John R. Hauser/ICSI's distinct four-paragraph notice remains in [softfloat.c](port/m68k/softfloat/softfloat.c) and related files. Do not describe the entire m68k directory solely by Musashi's notice. |
| ymfm | Aaron Giles's BSD-3-Clause text and source headers remain in [LICENSE](port/ymfm/LICENSE). |
| Dear ImGui | Omar Cornut's MIT text remains in [LICENSE.txt](port/imgui/LICENSE.txt). The core uses its existing timing-panel integration. |
| pugixml / stb_image | Full notices are retained in the vendored sources: [pugixml.cpp](src/libretro/sm2/pugixml/pugixml.cpp) and [stb_image.h](src/libretro/sm2/include/stb_image.h). |
| MAME catalogue metadata | The generated overlay retains the pinned source revision and MAME authors in its header; [MAME ROM Set Alignment](MAME_ROMSET_ALIGNMENT.md) records its provenance. These are ROM identities, not copied ROM archives. |

### Publication Status

The 2026-11-02 audit found no overall license declaration in the integrated
Model2EmuEx baseline. The user authorized first GitHub publication, commit,
push and release on 2026-11-02. Existing native/component notices remain
unchanged; no blanket license for recovered native code is inferred.
See [Distribution Notices](NOTICE.md) for component and attribution scope.

## Release Build And Packaging

Release Actions target Linux x86_64/ARM64, macOS arm64/x86_64 and Windows
x86_64, matching the SM2 matrix. macOS uses a 13.0 deployment target; this is a
build minimum, not an actual macOS 13 runtime test. Broader platform gameplay
and physical-device qualification remain separate.

```sh
make release -j4
python3 scripts/package-libretro-source.py --output port/build-source
python3 scripts/package-libretro.py \
  --platform macos-arm64 --source-archive port/build-source/*.tar.gz \
  --core port/build-release-macos/model2emuex_libretro.dylib \
  --output port/build-release-macos/dist
```

Packaging requires a clean committed checkout and a new output directory.
It verifies the selected architecture, dependencies, Libretro-only exports,
ABI/runtime version against Core Info, rejected-content cleanup, source revision
and ZIP hashes. Output contains a canonical `model2emuex_libretro` core/info pair,
notices, source provenance, complete matching Git source archive and checksums.
The embedded catalogue/templates do not require an external game database.
The existing development target/installed copy remain separate.

GitHub CI uses the same build/package commands without installing dependencies.
A version tag publishes the checked archives only after the macOS job succeeds.
CI does not supply ROMs or prove gameplay, physical input or audible output.
The public repository page is the root README; no separate website is required.
