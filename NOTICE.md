# Model2EmuEx Libretro — Source And Distribution Notices

This is an independent modified Libretro port of
https://github.com/octavioCuatrochio/Model2EmuEx (branch `daytona_decomp`,
revision `25d82be56f339c754cc566f771ca9ffb90b69289`), derived from ElSemi's
Model 2 Emulator 1.1a. Its history and original notices are retained.
The integrated native baseline has no overall LICENSE/COPYING declaration;
this notice does not assign rights or a blanket license to recovered native
code. The native project is distinct from SM2-Emu.

## Original Port Contributions

Original code introduced for this independent Libretro port is licensed under
the GNU General Public License, version 3 or (at your option) any later version.
Copyright (c) 2026 Model2EmuEx Libretro contributors. See LICENSE for the text.
This applies to original adapter/build/test contributions, not a relicensing
of inherited native code or third-party imports. Existing per-file notices
and the SM2 additional terms remain applicable to their respective components.

## Adapted Components

The input, NVRAM, networking, rumble, crosshair, timing and applicable serial-device
components are based on sm2-emu by Daniel Martin (dmanlfc) and its contributors,
through the SM2-Emu Libretro project:

- https://github.com/dmanlfc/sm2-emu
- https://github.com/Zer0one/sm2-emu-libretro

These components have been modified/adapted for Model2EmuEx. Their original
copyright/SPDX headers, GPL text and additional section-7 terms remain in
`src/libretro/sm2/LICENSE.sm2` and `src/libretro/sm2/NOTICE.sm2`. Binary packages
retain these as `licenses/GPL-3.0.txt` and `licenses/NOTICE.sm2`. The donor NOTICE
describes the donor's wider dependency set, not every dependency in this core.
Exact imports/adaptations are recorded in `src/libretro/sm2/IMPORT.json` and
`port/snd/sm2/IMPORT.json`. The core-information file and manual provide
user-accessible attribution; source origins must not be misrepresented.

Other bundled components retain their separate notices: Musashi (Karl Stenerud),
SoftFloat 2b (John R. Hauser/ICSI), ymfm (Aaron Giles), Dear ImGui (Omar Cornut),
pugixml (Arseny Kapoulkine), stb_image (Sean Barrett) and the Libretro API header
(The RetroArch team). Binary packages include the corresponding texts in
`licenses/`; original source files remain authoritative. MAME catalogue metadata
is pinned and attributed in MAME_ROMSET_ALIGNMENT.md.

Release archives provide matching source, build scripts, exact revision and
checksums. No ROM archives, user saves or local audit captures are distributed.
Publication does not imply all-game, all-platform or physical-device validation.
