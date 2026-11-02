# Sega Rally Upper-Sky Backdrop Correction

Date: 2026-10-21. Status: reproduced from the user's state, corrected and installed locally.

## Reproduction

The user reports a black area above the sky in normal gameplay, absent in the first course section, without having loaded Save States. The later state supplied for diagnosis is at machine frame 5,421. The original RetroArch RZIP file is copied into ignored evidence, decompressed and unwrapped into the unchanged 12 MiB Model2EmuEx format-1 buffer. Its SHA-256 is `df8ce8595d5e522488f4e37f5f6469f5e6747ba939f621a1bde8543dec6a5d46`.

Loading that state and advancing one frame reproduces the black upper-sky region at native resolution with no frontend shader. Isolated renders of tiles and polygons identify uncovered background above the 3D sky, rather than a frontend viewport/scaling mask. Save State restoration is the reproduction mechanism, not the reported trigger.

## Cause And Reference

`port/m2/m2gl.c` cleared the emulated framebuffer to hardcoded black. Model 2's backdrop is palette pen 0, shown wherever neither tilemaps nor polygons write a pixel. Some Sega Rally views leave part of the upper raster outside the sky geometry, making the incorrect clear visible.

The current primary reference implements this in SM2 `src/hw/model2_video.h` (`background()` returns `m_pens[0]`) and `src/hw/model2_softrender.cpp` (background fill before tiles/3D). The local MAME reference `src/mame/sega/model2_v.cpp` also fills with `m_palette->pen(0)` in `screen_update`.

The renderer now takes the already converted palette pen 0 from `m2_tilegen::pal` on upload and clears the emulated framebuffer with it. Presentation bars still clear to black. The value is derived GPU state and is refreshed from the authoritative palette after state loads and context recreation; no machine/state format, geometry, texture, timing, option or game-specific patch changed. The corrected native renderer is shared by this core and this repository's standalone. The pristine sibling is untouched.

## Verification

- `make check-render-background`: ROM-free native OpenGL test with transparent tile layers and no polygons. Two colours verify pen-0 fill and live palette changes; black letterbox bars, scale changes, cache invalidation and two contexts verify presentation and resource recreation. An isolated old-clear variant fails; corrected code passes. SDL is a test-only dependency.
- Core and standalone/headless targets build.
- Exact before/after comparison from the user's state changes 2,336 pixels, all previously black, within x=126–375, y=0–14 of the native 496×384 frame. Their corrected RGB is `(42, 92, 200)`, the current palette pen 0. All other pixels, main RAM and PCM match exactly.
- From this same supplied state, the corrected core passes four exact 12-frame RAM/device/PCM/image continuations, invalid-state rejection, context recreation and exact continuation in a fresh process. The input state remains compatible without migration.
- The authorized local RetroArch core was replaced atomically after backup. Installed/build SHA-256: `501d0da93f5bb217689c6f3c41e8aef1c4c65acc4e4296c822f1ed8fdaecbece`. State, SRAM and global configuration hashes were verified unchanged during deployment.

## Evidence And Limits

Ignored evidence: `port/build-libretro-macos/audit/srallyc-sky-state-20261021/`, including `input.json`, `restored/core.png`, `tiles/core.png`, `polys/core.png`, `fixed/core.png`, `pixel-comparison.json`, isolated probe sources and `deployment.json`. State-continuation receipt: `port/build-libretro-macos/audit/srallyc-sky-state-replay-20261021/result.json`.

This is an intentional renderer-accuracy difference from the pristine hardcoded-black baseline. It qualifies the supplied scene and the synthetic backdrop/presentation contract, not all games or every renderer difference. Rendering was verified in the isolated native Libretro/GL harness; no new full RetroArch playback or shader qualification is inferred from the installation. No commit or push.
