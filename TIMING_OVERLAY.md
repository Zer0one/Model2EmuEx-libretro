# Timing / FPS Overlay

Date: 2026-10-20. Functional group M20. SM2-Emu is the primary implementation reference; Framework 0.1.42 and the current TGPulse/Supermodel options were checked for naming and measurement contracts.

## Contract

Video → Timing / FPS Overlay: Off (default), Auto, On (11 px), On (12 px), On (13 px), On (14 px). Saved values are `disabled`, `auto`, `11`, `12`, `13`, `14`, matching SM2. Auto uses 13 px; unknown values disable the panel. Changes apply on Resume without resetting the machine. The option remains visible for every game.

The panel shows 61-frame averages for Machine, Video, Audio/pacing and retro_run, the maximum Worst time in that window, Actual frontend callback cadence, Engine cap and Callback cap. The caption uses Model2EmuEx and the selected cadence (60 Hz or the destination-native 58 Hz), not SM2's 57.524 Hz. Font/layout scale with internal resolution. No interactive ImGui window, input polling or configuration file is introduced.

## Reuse And Adaptation

The SM2 panel and its source tests are imported with provenance in `src/libretro/sm2/IMPORT.json`. The panel's only source adaptation is its identity/cadence caption. The existing `port/imgui` sources are compiled into the core; there is no new external dependency or SDL runtime/backend.

`sm2_timing.cpp` adapts SM2's averaging/capacity equations to native frame execution. Machine timing includes board execution and capture. Video timing includes snapshot application, geometry/GPU submission, the diagnostic panel and frontend video callback; skipped draws still contribute their callback work. Audio/pacing includes synthesis, cadence interpolation and frontend delivery. Machine timing runs on the emulation worker when Pipeline is enabled and is consumed only after joining. All frontend/UI/GL calls remain on the frontend thread.

Engine cap is `1000 / (mean machine + mean video)`. Callback cap is `1000 / mean retro_run`. These are estimates, not hardware gameplay benchmarks. Pipeline overlaps machine/video work, so the summed Engine cap is not a prediction of parallel throughput. Wall times include GPU submission but do not query GPU execution; Actual measures callback cadence, not emulation accuracy. A pause can affect the next interval window. The overlay adds rendering overhead, which is included in its Video/run measurements.

The adapter uses the frontend's loaded OpenGL entry points and current framebuffer. It owns a separate shader/buffer and ImGui font textures, handles atlas updates, clips draw commands and bounds temporary vertex batches. Context destruction releases these resources; reset/reload clear stale measurements. CPU teardown does not issue GL calls. An extra layout pass on font/geometry changes settles ImGui's auto-fit before the first visible submission, avoiding clipped text after a resolution change. This does not advance emulation or alter samples.

## Verification

- `bash scripts/check-sm2-common.sh`: known-sample mean/max/cadence/capacity tests, 61-frame warmup, Off/font/reset lifecycle, unchanged full SM2 input tests, imported timing-panel layout/scaling tests and ABI defaults/order pass.
- `audit/timing-overlay-layout-vf2`: actual OpenGL at 60 Hz; Off/Auto/all four sizes/invalid fallback, 4x scaling, frame-skip continuation, context recreation, reset and reload pass. The 4x screenshot was inspected for complete text. The earlier `timing-overlay-vf2` capture retains the first-visible-frame clipping failure that motivated the layout pass.
- At 900 frames, overlay On and Off produce identical main RAM and PCM at 60 Hz. Pixel differences are confined to the panel (x=8–233, y=8–194); game rendering outside that area is pixel-identical. This isolates diagnostic presentation from machine/audio state.
- `audit/timing-overlay-native-vf2`: overlay enabled under Native timing; main RAM and PCM remain byte-identical to same-revision pristine upstream with matched initial NVRAM.
- `make standalone -j4` passes; native machine sources were not changed by this group.
- Real RetroArch and the installed artifact are recorded in VALIDATION.md and the local installation manifest. Do not infer physical-controller, audible-output, other-platform or sustained gameplay qualification from this diagnostic feature.
