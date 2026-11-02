# Libretro Design

## Baseline And Ownership

Baseline: Model2EmuEx `25d82be56f339c754cc566f771ca9ffb90b69289`. Machine/loader adaptations include the MAME catalogue boundary, optional raw drive observation, neutral per-source sound gains, frontend-neutral machine serialization and the documented native audio/rendering corrections below. The root Makefile builds a separate dynamic library from the existing CPU, device, sound, loader, input, tile and GL modules plus `src/libretro/libretro.c`. Only Libretro ABI symbols have default visibility. The original `port/Makefile` remains usable.

The independent repository retains all 34 baseline commits. The independent branch is `main`; `upstream` references the original repository. The user authorized first GitHub publication to `Zer0one/Model2EmuEx-libretro` on 2026-11-02. Future reconciliation must review applicable changes and compare identical-revision pristine baselines.

The official ABI header is vendored unchanged from the existing SM2-Emu reference at `src/libretro/include/libretro.h`; its original notice is retained. No new licensing claim is made for the emulator's decompiled source. The M26 audit below records verified provenance/notices and the publication terms that remain unresolved.

## Upstream References And Integration Review

Adopted from [Framework F02](../libretro-core-framework/FRAMEWORK.md#f02--reconcile-upstream-changes-explicitly), edition 0.1.43 (2026-10-29), and its [source integration policy](../rpcs3-libretro/docs/INTEGRATION_POLICY.md). Apply the method to this project's actual source relationship:

| Reference | Repository And Revision | Role |
| --- | --- | --- |
| Upstream Libretro Port | No independent upstream Libretro port exists for this project. This local repository's `main` starts at `25d82be56f339c754cc566f771ca9ffb90b69289`, retaining Model2EmuEx history; no separate port donor exists. | The adapter is developed here against the native engine. |
| Upstream Standalone Engine | [octavioCuatrochio/Model2EmuEx](https://github.com/octavioCuatrochio/Model2EmuEx), branch `daytona_decomp`, integrated revision `25d82be56f339c754cc566f771ca9ffb90b69289`; local remote `upstream`. | Native machine behavior and pristine comparisons. The separate `../Model2EmuEx` checkout is at this revision when this policy is adopted. |

SM2-Emu is the implementation and frontend-contract reference, not an upstream Model2EmuEx port. Retain its existing per-file provenance in SM2_REFERENCE_INVENTORY.json and the subsystem import metadata, including `port/snd/sm2/IMPORT.json`; recorded hashes identify inspected working-copy content beyond a donor HEAD. Record the exact repositories, old/new revisions and relevant dependency pins when an integration is authorized. Do not treat this adoption-date baseline as a claim about later upstream availability.

User clarification — 2026-11-02: SM2 primarily supplies interface, exposed-option and shared Libretro conventions, plus explicitly approved reusable functions. It is not an emulation target for this core. Preserve Model2EmuEx's machine behavior and native capabilities; differences alone do not justify importing SM2 emulation. M25 transfers four established adapter bug fixes, including GL resource ownership, without replacing CPU, sound synthesis or emulated rendering behavior. See [Frontend Contract Review](FRONTEND_CONTRACT_REVIEW.md#implementation-and-verification--2026-11-02).

For each authorized engine update or shared-reference update, review local adaptations in affected areas and their semantic dependencies, including resource lifetime, configuration, persistence and frontend contracts, even when Git reports no conflicts. If an independent port upstream is adopted later, identify and review it separately. Classify incoming changes by actual provenance: a donor diff can contain newer engine changes as well as port-specific work, and is not automatically all locally authored.

Preserve each adaptation's benefit by fitting it to the new APIs, structures and formats. Retire it only after verifying equivalent upstream behavior or that its documented need has ended; avoid silent loss and duplicate implementations. Explain the affected area, exact reference, purpose, evidence, limits and retirement condition in existing relevant comments, subsystem documents and Git history. Record the retain/adapt/remove decision in the integration change and update the corresponding explanation and checks when assumptions change. Do not create a parallel patch registry or a manual committed/uncommitted inventory; Git records that state.

For behavioral comparisons, consult the existing local corrections first. [Sega Rally Audio](AUDIO_SRALLYC_DIAGNOSTIC.md#correction-and-regression-checks) documents the SCSP scheduling correction and PCM/state evidence; [Upper-Sky Backdrop](SKY_SRALLYC_DIAGNOSTIC.md) documents palette-pen-0 clearing and its scene-specific pixel evidence. Both differ intentionally from the pristine engine baseline and also affect standalone targets built from this port's shared native sources. Matching engine revision alone therefore does not imply identical output. Keep the pristine standalone reference, explain the relevant difference and validation limits before attributing a defect to the core or excluding comparison evidence, and compare old/new pristine baselines separately. Future upstream fixes for these paths require equivalence review before removing the local correction.

Local adaptations belong to this core's repository. Do not modify the separate standalone checkout to match the core without an explicit user request. This policy does not authorize merges, engine changes, runtime tests, installation, commits, publication or release; those require their own authorized scope. Existing user-approved behavior and native Save RAM compatibility remain authoritative.

## Source Provenance And Notice Audit — 2026-11-02

M26's static review confirms the 34-commit native baseline and matching pristine
checkout at `25d82be56f339c754cc566f771ca9ffb90b69289`; `upstream` is the native
repository, not a separate port donor. The SM2 working-copy reference remains
`be696244fc425f55e3c0cab9bc43c03d44b621aa`, with file hashes identifying actual
imports beyond the initial snapshot HEAD in the existing manifest. The MAME
catalogue retains revision `b106b9345dc32ab3c99514d6caeeabe0d0a78830` and its
recorded source digest in MAME_ROMSET_ALIGNMENT.md.

All 40 existing SM2 import entries were present. Thirty-eight destination hashes
matched; the two adapted Netpacket entries still contained donor hashes. Their
metadata now distinguishes donor revision/hash and actual destination hash,
without changing source. All 35 entries declared unchanged match the live donor,
as do both pinned I8251 files. The API header and copied SM2 LICENSE/NOTICE match
the donor byte-for-byte. The BSD text referenced by those notices was missing
and is now retained unchanged from the same donor with an additional import
entry. All 41 resulting destination hashes verify.

Netpacket's local topology/disconnect/reset queue corrections are now explained
in EXTERNAL_LINKED_CABINETS.md, with their existing bounded evidence and retirement
condition. Native SCSP scheduling, palette-pen-0 clearing, EEPROM and state-format
changes remain explained by the existing subsystem diagnostics rather than a
new patch register. The review did not import or retire any implementation.

Original permission/copyright notices remain in the native third-party modules;
in particular SoftFloat 2b has a separate notice from Musashi. The project-facing
attribution and links are consolidated in [Credits And Source Notices](LIBRETRO.md#credits-and-source-notices),
with SM2 author/origin attribution added to the existing Core Information file.
No global license field is inferred from those component notices.

M26 remains partial: the native baseline has no root license statement, and the
recovered ElSemi code lacks explicit project-level publication terms. Original
port contributions now use GPL-3.0-or-later; scope is defined in NOTICE.md. This audit does not resolve native terms. The user subsequently authorized first publication on 2026-11-02; component and distribution scope are retained in NOTICE.md.
Future authorized engine/reference updates still require the semantic review
above. No engine/adapter implementation, imported executable source, ROM, save,
runtime binary or reference checkout was changed. Reproduction and hash results
are in ignored `audit/m26-source-review-20261102/result.json`.

## Video

Request `RETRO_HW_CONTEXT_OPENGL` 2.1 compatibility, bottom-left origin, and obtain all GL entry points through the frontend. Preserve upstream shaders, geometry and tile compositing. Expose upstream Nearest/Bilinear/Trilinear filtering, defaulting to Nearest. No SDL or native OpenGL framework is linked into the core.

Upstream's renderer binds framebuffer zero for its final pass. The adapter wraps its loaded `glBindFramebuffer` entry point, translating zero into `get_current_framebuffer()` on every such binding. Internal nonzero FBOs remain unchanged. This leaves imported renderer code untouched and supports a frontend FBO whose identifier changes. The harness explicitly uses a nonzero FBO.

Context reset abandons obsolete GL names without issuing deletes, then reloads entry points and recreates GPU resources. Context destroy frees them while the frontend's context is current. Unload/deinit release machine/CPU-side resources without issuing GL calls; the frontend owns context destruction. The harness covers announced recreation and controlled replacement without a destroy callback, including overlay resources and visible rendering recovery; physical device loss is not yet tested.

Native output is 496 × 384 at 4:3; the frontend handles pixel-aspect correction and final window scaling. Internal resolution scales native geometry and the GPU target, with maximum advertised output 1984 × 1536. The adapter's final pass fills this target to avoid applying square-pixel letterboxing before frontend aspect correction. Native widescreen expansion is integrated through separate Aspect Ratio and Widescreen Mode controls, including 16:10; maximum width includes the expanded raster.

## Timing And Audio

A/V Timing defaults to 60 Hz by user decision; Native reports the destination catalogue's 58 Hz. Timing is latched at content load, independently of reset. One complete native board frame executes per callback. Native synthesis follows original command ordering and retains its fractional sample count. SCSP advances in one-sample slices to prevent premature streamed-PCM termination; the Model 1 sound board retains 16-sample slices. See [Sega Rally Audio Diagnostic](AUDIO_SRALLYC_DIAGNOSTIC.md). SM2 endpoint interpolation adapts output slices to 60 Hz; Native bypasses interpolation. Pending batch samples are retained up to a bounded one-second queue. Source gains preserve native Auto/100% mixing, continue synthesis while muted and survive sound reset. See [Shared Features](COMMON_FEATURES.md).

## Input And Presentation

The unchanged SM2 engine, full metadata, controller subclasses and descriptors are integrated through `sm2_input_bridge.cpp`. All 28 current identities bind in ROM-free tests; original Model 2 ports, VF2 bits, gear encodings and gun serial counters are translated at the adapter boundary. None and frontend remapping remain available. Normal + Test/Service defaults enabled; modern display callbacks refresh paused Controls descriptors while preserving option-update notifications. No keyboard device is polled.

Raw drive commands are queued on the worker and consumed after joining. Only the frontend thread invokes rumble callbacks. Framework output gating retains native state while muted and clears it at reset/unload. Crosshair presentation reuses the SM2 implementation and selected defaults, with the approved destination PNG directory. A separate GL overlay draws source geometry and matches pipeline aim snapshots to the rendered frame. No native game-reticle or flash-removal capability is inferred from the overlay.

## Persistence And Reset

Expose a stable 0x10080-byte Save RAM bridge: backup RAM followed by EEPROM. Seed using only SM2 templates and explicitly compatible parents during load, allow the frontend to overwrite it before first run, import it once, and export it after each board frame. No direct filesystem saves bypass Libretro. Frontend resets preserve backup/EEPROM, reset the board/sound/input/tile state and invalidate all GPU texture bands. ROM-loading errors release partial allocations and return failure.

Pending operator overrides retry before/after frames until the native layout is ready, coalescing effective settings/topology changes into one reset. New option requests refresh the pending selection; disabling overrides cancels it. After 600 unsuccessful frames emit one warning and stop retrying, following the existing SM2 adapter solution. Invalid network values queue canonical corrections and publish outside readers. Fatal runtime/GPU errors notify with severity, stop rumble and prevent further execution; recoverable state rejection remains nonfatal.

Main RAM is exposed read-only in intent through the standard SYSTEM_RAM inspection interface. Save States use the complete native machine/sound/geometry archive plus frontend continuation, with a fixed 12 MiB buffer, format/identity/integrity validation, process-local pointer rebinding and rollback on failure. Current enabled operator overrides are reapplied on Resume with one reset only if effective values change. See [Save States](SAVE_STATES.md) for coverage, format and verification.

## Initial Option Contract

| Field | Contract |
| --- | --- |
| Key | `model2emuex_internal_resolution` |
| Category / Name | Video / Internal Resolution |
| Values / Default | Numeric strings `1`, `2`, `3`, `4`; default `1` |
| Scope / Visibility | All supported games; always visible |
| Effect | GPU target and output resolution |
| Lifecycle | Resume / next executed frame; no machine reset |
| Persistence | Frontend Core Options; no NVRAM changes |
| Invalid Values | Fall back to `1` |
| Legacy | Same numeric tokens and default through SET_VARIABLES |
| Evidence | GL harness at 1x/2x and actual RetroArch paused menu edit followed by Resume |

Retain GET_VARIABLE_UPDATE before other option reads, including paused display callbacks. Register System, Video, Audio and Input in reference category order; do not add empty categories. Use current SM2 wording/defaults for clear equivalents and adapt only actual destination semantics.

## Native Texture Filtering Contract

Approved user decision (2026-10-20): expose the emulator's own selectors for native features, in addition to applicable shared options such as Gamepad Rumble and NVRAM Settings. Do not translate unavailable anisotropic modes into this core's values.

| Field | Contract |
| --- | --- |
| Key | `model2emuex_texture_filter` |
| Category / Name / Order | Video / 3D Texture Filtering / immediately after Internal Resolution, following SM2 |
| Values / Labels | `nearest` / Nearest; `bilinear` / Bilinear; `trilinear` / Trilinear |
| Default / Invalid Value | `nearest` |
| Scope / Visibility | All supported games; always visible; affects 3D texture sampling |
| Effect | Pass the corresponding native M2_TEX enum to the existing renderer |
| Lifecycle | Resume / next executed frame; no machine reset |
| Persistence | Frontend Core Options only; no NVRAM changes |
| Legacy | Same raw tokens, order and effective default through SET_VARIABLES |
| Capability Fallback | Upstream tries the next simpler shader if the selected filter program is unavailable |
| Evidence | All three native modes render textured VF2 scenes; distinct images at the same frame with identical main RAM/PCM; runtime changes and invalid-value fallback complete without GL errors |

The common description uses SM2's texture-sampling wording. The capability and lifecycle sentences describe this renderer's native filters and shader fallback. No shared wording or implementation in another core was modified.

## MAME Content Metadata Overlay

The Libretro Makefile enables `M2_ROMSET_MAME` and includes `src/libretro/data/gamedb_mame.inc` at the loader boundary. Original machine wiring and the standalone database remain intact. The generated overlay follows pinned official MAME identities, correcting file labels/CRCs and the Daytona 1993 sound-program revision. It removes the unused Model 2A video-table requirements from original Model 2 sets. `daytona93` is the canonical identifier; `srallyp` is excluded by user decision. Additional device ROM metadata is retained in the manifest without claiming new device emulation. See MAME_ROMSET_ALIGNMENT.md for provenance and acceptance checks.

## Initial NVRAM Policy Decision

The user removed the native Daytona setup fallback as overlapping with SM2 automatic initial setup. The adapter calls only `sm2lr_initial_nvram`; an exact template or an explicitly approved compatible parent is required for seeding. Unsupported identities retain machine defaults and follow native game initialization; no parent template is guessed. Existing frontend SRAM still replaces startup data before the first frame. The standalone `m2_nvram_defaults` implementation remains untouched.

## ROM Verification Policy

The shared ROM CRC Verification selector uses the optional `m2_create_with_rom_policy` / `m2_load_roms_with_policy` interfaces. Enabled validates computed payload CRC32; Disabled skips CRC matching while size/decompression checks remain. The unchanged standalone call signatures use their original metadata-only CRC policy. Parser bounds, stored-size/compressed-stream checks and loose-file length validation apply independently of CRC policy. ROM-free fixtures cover corrupt payloads carrying forged archive CRCs and verify both legacy and explicit policies.

## Timing Diagnostics

The optional Timing / FPS Overlay reuses the SM2 panel and 61-frame aggregation equations. Frontend GL pointers submit its own ImGui font textures and bounded vertex batches into the current FBO. Native board timing is captured on the worker and consumed after join; UI rendering stays on the frontend thread. Context destruction releases GL resources, while reset/load/unload clear statistics; CPU teardown makes no GL calls. One layout warmup settles a changed font/internal size before visible submission. See TIMING_OVERLAY.md for CPU/GPU interpretation and parallel-pipeline limits.
