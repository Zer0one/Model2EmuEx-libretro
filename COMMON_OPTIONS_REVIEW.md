# Common Core Options Review

Date: 2026-10-20. Status: Mixed — Implemented Items And Remaining Integration Work.

## Complete Reference Scope

Complete the native selectors first as recorded in NATIVE_OPTIONS.md. This document inventories the subsequent common menu controls only. The user subsequently clarified that the **whole SM2 port** is the implementation reference; see [Complete Applicability Review](SM2_APPLICABILITY.md). The implementation groups below are sequencing aids, not approval gates or exclusions. Missing machine execution does not postpone preparation of Model 2B/2C profiles, NVRAM, options, metadata and ROM-free tests. Existing SM2 implementations and data must be reused before proposing new analysis or campaigns.

## Current Delivery Update

The actual registered inventory is [Implemented Core Options Review](CORE_OPTIONS_IMPLEMENTED_REVIEW.md), with lifecycle/evidence in [Shared Features](COMMON_FEATURES.md). Applicable native selectors, the SM2 NVRAM engine/catalogue/templates, complete input profiles and current 28-set wiring, Gamepad Rumble, shifter/driving/gun controls, four source gains, user-approved 60 Hz/Native timing, and user-approved SM2 crosshair styles/defaults are integrated. Rows below retain their original planning/adaptation rationale; they do not supersede the current delivery record. Separate keyboard and native cooperative controls are excluded by user decision.

## Purpose And References

Adopt applicable SM2-Emu common controls alongside Model2EmuEx's native selectors. System NVRAM controls and separate SM2-style Aspect Ratio / Widescreen Mode are now registered. Other rows remain an implementation inventory unless explicitly marked delivered. Existing Internal Resolution and native 3D Texture Filtering remain implemented.

References inspected: current SM2 `src/libretro/core_options.h` (including final presentation-order arrays), shared `FRAMEWORK.md` F04–F14 and its source index, and the actual Model2EmuEx loader, input, drive-command hook, sound mixer, NVRAM and widescreen interfaces. Preserve original machine behavior; isolate frontend policy and add small neutral machine interfaces only where needed.

Classification: **A** = proposed first implementation group; **B** = include after dedicated machine/input evidence; **C** = requires a separate architecture decision. These are implementation groups, not menu sections. Proposed defaults follow SM2 unless the adaptation is explicitly identified. No unsupported placeholder is to be registered.

## System

| ID | Proposed Name | Proposed Values / Default | Group | Destination Work And Lifecycle |
| --- | --- | --- | --- | --- |
| S01 | Automatic Initial NVRAM Setup (Restart Required) | Enabled / Disabled; **Enabled** | A | Reuse SM2 initial_nvram.cpp, initial_nvram_templates.inc and their parent/clone policy; adapt the destination memory view and save container. Seed only missing/invalid saves; preserve valid frontend SRAM. Retain native Standalone/No Link setup. Load-time policy. |
| S02 | NVRAM Settings (Service Menu) | Disabled / Enabled; **Disabled** | A | Port the existing SM2 nvram_settings engine and generated catalogue, including its field masks, value encoding, layout validation, mirrors and checksum handling. Adapt the board-memory interfaces; preserve the Disabled default, authority gate, calibration and one-reset-on-Resume behavior. Do not rebuild this subsystem from scratch. |
| S03 | Per-Game Operator Settings | Existing SM2 values/defaults for matching games and revisions | A, incremental | Reuse SM2 menu labels, values, defaults, data tables, samples and acquisition records for matching supported games. Map destination set IDs/parents and validate the adaptation against the existing samples. New acquisition is only for a demonstrated gap or incompatible revision, not the default starting point. |
| S04 | ROM CRC Verification (Restart Required) | Enabled / Disabled; **Enabled** | B | Current ZIP loader uses name/CRC metadata and declared size; this is not a completed computed-payload CRC verification contract. Implement actual checksum verification before exposing this label; define Disabled behavior while retaining decompression/size validation. Content reload. |
| S05 | Linked Cabinets | **1 Cabinet / Disabled**, then validated per-game totals | C | M13 adapts the native ring through SM2 Netpacket and coalesces topology/operator changes. Native split-screen remains excluded. Per-game limits come from the primary SM2 role/topology table; see EXTERNAL_LINKED_CABINETS.md for runtime limits and the approved all-set local loopback. |
| S06 | Auto Network Role Settings | **Disabled**, native Standalone/Master/Slave and IDs supported per game | C | Independent of Linked Cabinets and the NVRAM gate; use actual native role/identity fields. Follow current Framework ANRS precedence and Disabled default. Apply only validated effective changes, with one reset. |

NVRAM starting point is the complete SM2 implementation, not a new campaign. Reuse `nvram_settings.{h,cpp}`, `nvram_settings_data.inc`, `initial_nvram.{h,cpp}`, `initial_nvram_templates.inc`, existing YAML/catalogue, samples, tests and workbook evidence. Carry the existing implementation status into the destination review; mark only actual destination integration/coverage gaps.

Current SM2 source is the primary authority for implemented fields, values, defaults, templates and behavior. The existing workbook is a shared SEGA Model 2 reference and may lag behind that source; do not recreate or duplicate it for Model2EmuEx. Report concrete source/integration discrepancies and their impact, discussing target-specific semantic choices before changing behavior.

One concrete adapter difference is already established: SM2 exposes 16 KiB backup RAM plus 128 EEPROM bytes through a 64-byte-header save container; Model2EmuEx currently exposes 64 KiB backup RAM plus 128 EEPROM bytes without that header. Provide the existing engine with the appropriate native memory view and preserve the destination's extra backup bytes. This is a memory/container adaptation, not a reason to rediscover native fields or checksum algorithms. Existing SM2 samples are inputs for integration tests; do not mistake the whole frontend save container for a directly interchangeable raw file.

## Video

| ID | Proposed Name | Proposed Values / Default | Group | Destination Work And Lifecycle |
| --- | --- | --- | --- | --- |
| V01 | Aspect Ratio | **Auto**, 4:3, 16:9 | A | Frontend-reported aspect, distinct from expanded 3D rendering. Auto uses validated native monitor/cabinet metadata, otherwise 4:3. Apply on Resume without reset. |
| V02 | Widescreen Mode | Disabled; Expand 3D View Only; native 3D + 2D expansion label | B | Wire existing `m2wide_update`, geometry FOV and per-game layer rules. Preserve dependency on Aspect Ratio Auto/16:9; explicit 4:3 suppresses expansion. Default **Disabled**, matching the current SM2 definition (`stretch` is the stored token for the displayed Disabled choice). No reset. |
| V03 | A/V Timing (Restart Required) | **60 Hz (Default)**; Native | A, review default | User approved 60 Hz default; implemented with content-load latching and SM2 interpolation. Native uses the upstream database FPS (e.g. 58 Hz for VF2/Sega Rally), so this changes the initial default. Native must use the destination game's declared cadence, not SM2's fixed 57.524 Hz label. Keep machine cycle counts/native frame count intact and adapt output cadence/audio consistently. Content reload. |
| V04 | Timing / FPS Overlay | **Off**, Auto, On (11/12/13/14 px) | Integrated | Reuses the SM2 panel and 61-frame measurement equations through destination GL. All sizes, scaling and lifecycle tested; CPU submission times/capacity estimates have the limits recorded in TIMING_OVERLAY.md. No machine reset. |

Keep existing Internal Resolution and 3D Texture Filtering first, in reference order; place aspect/widescreen next, then timing/diagnostics. No Renderer selector while only one renderer exists. Upstream mesh transparency, gamma and saturation are separate native-feature candidates, not substitutes for common options.

## Audio

| ID | Proposed Name | Proposed Values / Default | Group | Destination Work And Lifecycle |
| --- | --- | --- | --- | --- |
| A01 | SCSP Gain | **Auto**, Mute, 10–100% in 10% steps | A | Model 2A source. Auto preserves current native output level; mute never stops sound CPU/synthesis. Apply on Resume without reset. |
| A02 | MultiPCM 1 Gain | Same; **Auto** | A | Original Model 2 source; separate contribution before mixing and clipping. Preserve the current native 0.5 mixer coefficient under Auto. |
| A03 | MultiPCM 2 Gain | Same; **Auto** | A | Independent second MultiPCM contribution; preserve native mixing under Auto. |
| A04 | FM (YM3438) Gain | Same; **Auto** | A | Original Model 2 FM contribution; preserve native 0.30 coefficient under Auto. |
| A05 | SCSP Output Low-Pass Filter | Not Exposed; SM2 Reference Defaults Enabled | Excluded By User | Retain native Model2EmuEx output. The user declined the added 8 kHz SCSP filter and its selector on 2026-10-20. |

Keep all delivered source-gain options visible; a source absent from the current board is a documented no-op. Auto means the existing destination mix, not a new SM2 equalization profile. Numeric 100% must agree with that reference level. Do not add DSB (MPEG) Gain/Music Volume while no separate MPEG board is integrated. Prepare the corresponding reference policy and metadata for future hardware without exposing a nonfunctional placeholder. Enhanced Audio Balance needs a validated destination profile before it is meaningful.

## Input

| ID | Proposed Name | Proposed Values / Default | Group | Destination Work And Lifecycle |
| --- | --- | --- | --- | --- |
| I01 | Controller Profile Type | Normal; **Normal + Test/Service** | A | Build reviewed per-game profiles and supplemental Service/Test actions, preserving gameplay/remapping and SM2 physical layouts. Direct keyboard polling is excluded; the complete shared controller-profile selector is now integrated. Update descriptors correctly; no machine reset. |
| I02 | Gamepad Rumble | **Enabled** / Disabled | A | Decode native `drive_command` effects and route through Libretro rumble. Verify per-game command semantics and motor mapping. Disable stops motors while retaining/updating native effects; re-enable restores active output. Reset/unload clear effects and silence motors. Do not invent synthetic effects. |
| I03 | 4-Speed Shifter | **H-Gate Mode**; Standard | B | Adapt SM2 direct directional/diagonal H-gate convention to destination gear encoding; upstream sequential RB/LB remains available. Validate Daytona/Sega Rally separately. No reset for live mapping. |
| I04 | Gear Shift Neutral Time | 0–500 ms in 10 ms steps; **100 ms** | B | Apply only to sequential shifts of reviewed four-speed games; direct gear selection bypasses delay. 0 disables/cancels pending delay. No reset. |
| I05 | Automatic Start Gear (Restart Required) | **Enabled** / Disabled | B | Requires per-game start-gear evidence; do not infer it from current unconditional first-gear initialization. Content reload. |
| I06 | Driving Steering Response | **Linear**; Progressive (Fine Center); FBNeo Logarithmic (Fine Center) | A | Adapter-side response before native game encoding; retain full travel and avoid applying deadzones twice. Resume, no reset. |
| I07 | Driving Steering Output Range | Reference 50–150% list, including validated 63% preset; **100%** | A | Scale about center before native encoding. The SM2 30-80-D0 preset label requires destination raw-range verification. Resume, no reset. |
| I08 | Driving Accelerator Output Range | Reference 50–150% list, including validated 75.3% preset; **100%** | A | Scale from released pedal position; verify native input-test output before reusing 00-C0 label. Resume, no reset. |
| I09 | Driving Brake Output Range | Same as accelerator; **100%** | A | Independent scaling with the same validation requirement. Resume, no reset. |
| I10 | Gun Input Mode | **Standard**, Lightgun Only, Mouse + Analog Stick, Mouse Only, Analog Stick Only | B | Implement verified frontend lightgun/mouse/stick ownership and native coordinates for supported gun games. Current generic pad translation is insufficient. Resume, no reset. |
| I11 | Gun Analog Stick Control | **Relative** / Absolute | B | Correct cursor accumulation/recentering and source arbitration; preserve other allowed devices in combined modes. No reset. |
| I12 | Show Crosshair | **Automatic**, Disabled, Player 1 Only, Player 2 Only, Players 1 & 2 | B | Separate external overlay from native reticle behavior; preserve the reference per-player values. No reset. |
| I13 | Crosshair Style | Native reference style plus supported custom artwork; final list to review | B | Do not expose the SM2-Emu artwork as this core's identity. Decide destination default style and artwork path after reviewing the renderer/overlay capability. No reset except explicit artwork reload requirement. |
| I14 | Crosshair Inactivity Timeout | **Disabled**, 1/2/3/4/5/6/7/8/10/15/30/60 seconds | B | Independent timers; hide external overlays only, not native reticles. No reset. |
| I15 | Off-Screen Reload Shortcut | **Enabled** / Disabled | B | Only games with a verified reload action; retain native off-screen firing and explicit shortcut semantics. No reset. |
| I16 | Mouse Edge Off-Screen Reload | **Disabled** / Enabled | B | Preserve distinction between mouse-edge shortcut and actual lightgun off-screen status. No reset. |
| I17 | Hide Shot Flash | Not Exposed | Excluded | Explicitly excluded by user decision on 2026-10-20. Retained only as a reference inventory entry; no implementation or selector is planned. |

Input ordering follows SM2: Controller Profile Type, Gamepad Rumble, gun blocks, gear blocks, driving-response/range controls, then reviewed game-specific options. All implemented common selectors stay visible by default; help explains no-effect games. Gun and gear blocks remain conditional implementation groups until their full behavior exists.

## Outside This Common-Menu Inventory

- i960 Round-to-Nearest-Even Fix: source-specific fix, not a generic switch to copy between unrelated CPU implementations.
- Software Renderer Threading, Renderer and 2D Layer Upscaling Filter: current core lacks those selectable implementations.
- Manx TT cabinet audio is integrated following SM2; see MANX_TT_CABINET_AUDIO.md. No current destination set declares DSB/MPEG or Power Sled relay hardware. Retain the source routes for future applicable catalog additions, without ineffective selectors.
- Game-specific fixes, calibrated mappings and prototype options: require destination evidence and applicable user scope; not part of this common list automatically.
- Save States: a capability requiring full serialization and frontend validation, not a Core Option.
- Volume, pause, screenshots, final-window scaling and shaders: frontend responsibilities; no duplicate controls.

## Proposed Review Decisions And Sequence

1. Review group A as the first common-options scope. Preserve native machine defaults under Auto, and keep unavailable features absent until implemented.
2. Decide V03: adopt the SM2 **60 Hz default**, retaining Native as a selectable mode, or preserve the current Native default for this core.
3. Preserve V02's **Disabled widescreen default**, matching current SM2; adapt native per-game expansion rules.
4. Accept groups B/C as staged work requiring evidence, not immediate menu placeholders. Networking needs an explicit delivery model; crosshair identity needs a separate choice before implementation.
5. Port the complete existing SM2 NVRAM subsystem and evidence, adapting memory/container interfaces and matching set identities. Use its established samples/tests for integration verification; acquire new data only for a proven gap.

Implementation acceptance: complete V2 and legacy labels/tokens/defaults/help; invalid-value behavior; no-op applicability; paused edits and Resume; unchanged values without repeated resets; memory/save integrity; actual shader/motor/source behavior; same-revision pristine comparisons; real RetroArch checks. Physical controller feedback and audible sound remain separate evidence requirements.

## Approved Integration Updates

- Aspect Ratio / Widescreen Mode: implemented as separate controls following SM2, retaining Model2EmuEx 16:10. Auto + Disabled is the default. Explicit 4:3 suppresses expansion; wide aspect + Disabled stretches the original frame through frontend presentation.
- Automatic Initial NVRAM Setup / NVRAM Settings: imported reference engine, templates and complete 340-option catalogue integrated. The master authority gate defaults Disabled; effective operator changes reset once on Resume. Existing frontend saves take precedence over startup seeding. ROM-free catalogue/checksum tests and a VF2 same-revision comparison pass; full per-game runtime coverage is pending.
- Separate keyboard controls: excluded by user instruction. Keyboard mapping belongs to the frontend; native Keyboard Shifter and Hold Gears are removed.
- Native cooperative mode and its layout selectors: excluded for now by user instruction.
- Overlapping native/common choices must be presented case by case. Prefer shared SM2 / SEGA Model Core semantics and wording, adding applicable native capabilities rather than creating duplicate controls.

## User Review Follow-Up

Existing uncommented selectors are retained. Pipeline help now explains parallel execution, performance and one-frame video latency in plain language. All 340 operator fields mark their default values with (Default), and V2 NVRAM master visibility follows SM2 on games with/without an applicable catalogue. These were integration omissions, not justified emulator-specific exceptions. No option key, stored value or default changed.

User decision — 2026-10-20: retain Model2EmuEx's native SCSP output. Do not add SM2's 8 kHz output low-pass filter or its Core Option. This exclusion concerns the additional SCSP filter; the previously approved source gains and 60 Hz/Native A/V Timing remain in place.
