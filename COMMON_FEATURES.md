# Shared SM2 Features

Date: 2026-10-20. Reference: the live SM2-Emu working copy, with hashes in `src/libretro/sm2/IMPORT.json`. Framework edition 0.1.42 and REFERENCE_SOURCES.md supply shared contracts when SM2 has no equivalent or its current code predates a shared decision. Other reference repositories are read-only inputs.

M23 source reconciliation (2026-10-22), template routing and the existing NVRAM
evidence index are in [NVRAM Source Review](NVRAM_SOURCE_REVIEW.md). The shared
SEGA Model 2 workbook is not duplicated. Actual registration matches current
SM2 source; destination persistence qualification remains separate.

## ROM CRC Verification

ROM CRC Verification defaults Enabled and is read at content load, matching SM2. Enabled checks actual uncompressed ROM-chip bytes against declared CRC32, for stored/deflated ZIP entries and loose files. Disabled skips CRC matching while retaining size, archive and decompression validation. Filename-first/CRC-fallback lookup and the existing content/parent/shared search order remain intact. Verification is independent of the MAME metadata alignment itself.

Optional frontend-neutral ROM-policy variants of the loader/board factory expose this behavior. Original standalone entry points retain metadata-only CRC policy. Both policies now reject oversized loose files and malformed archive records/streams rather than reading past declared boundaries. Synthetic fixtures test real corruption with forged CRC metadata, both ZIP methods, loose data, Disabled acceptance and size rejection. Production ROM archives are never modified.

## Input Profiles

The unchanged SM2 input engine and complete 88-game metadata catalogue are embedded. Profiles remain available for future Model 2B/2C backends; current execution and the current 28-set loader are separate constraints. Every current set binds to a recognised profile in ROM-free tests. Selection requires matching main-program CRCs, with two explicit Daytona Turbo control-only aliases validated against native input wiring. This alias does not grant NVRAM template inheritance.

The adapter translates normalized SM2 state into native ports, ADC channels, four-speed gear bits and serial gun counters. VF2 translates Punch/Kick/Guard into the destination's different bit order. Original Model 2 uses its separate digital/DPRAM lanes. Sega Rally IN2 carries its full-byte native handbrake rather than the standalone adapter's synthetic drive readback. Gun counters invert destination serial offsets, preserve X high-byte carry and separate both players' triggers and off-screen flags.

Controller Profile Type is the first Input selector. Normal + Test/Service is the default; L3 = Service and R3 = Test. Normal omits these descriptors and polling without resetting gameplay. Controls names/descriptors refresh while paused through the display callback. Historical controller subclass IDs remain accepted and None disables polling for the port. There is no separate keyboard device or keyboard selector.

Targeted macOS RetroArch Input Tests (2026-11-02) verify 15 Sega Rally and 18 VF2 native responses, including analog pressure and independent P1/P2 controls. Current imported input sources match SM2 and all 28 adapter bindings pass existing tests. The attempted live Normal-profile edit did not complete; adapter gating passes, but no new paused-menu refresh or physical-device acceptance is claimed. See [Validation](VALIDATION.md).

All SM2 families remain in the imported engine. Current bindings cover Fighting Vipers/VF2, Daytona, Desert Tank, Virtua Cop 1/2, Sky Target, Sega Rally, Motor Raid, Manx TT, Over Rev, Ski Super G, Wave Runner and Water Ski, including their current clones. Native execution restrictions still apply.

Framework F09 adds Down as the existing single View alias for Sky Target, Wave Runner and Motor Raid; those directions have no independent native game action. Manx TT and Sega Rally already include both directions in SM2. VR2/VR3/VR4 layouts retain their distinct native actions. The seven current single-view set identities are tested for identical Up/Down native port output.

## Driving And Guns

The shared selectors retain SM2 values/defaults: H-Gate shifting, 100 ms sequential neutral time, Automatic Start Gear enabled, Linear steering, 100% steering/pedal ranges, Standard combined gun input, Relative gun-stick aiming, Off-Screen Reload Shortcut enabled and Mouse Edge Reload disabled. Desert Tank elevation defaults to Relative, 100%, Normal. Range presets use the unchanged SM2 input equations before native translation. Sequential neutral duration is rounded at the destination native board cadence. Automatic Start Gear is latched at content load; other input selectors apply on Resume without a machine reset.

The full input tests from SM2 are imported unchanged and pass against the reused implementation and embedded source metadata. They cover future board profiles, device arbitration, gear transitions, native polarities, independent players and crosshair presentation. Adapter tests additionally verify all current identities and actual destination bit/counter translation. These are callback-level tests, not physical controller/lightgun or paid-gameplay acceptance.

## Gamepad Rumble

The unchanged SM2 drive-command decoder and rumble implementation consume raw native drive writes. An optional frontend-neutral machine hook observes the stream before standalone filtering of zero, 0x83 and repeated commands. The pipeline forwards the raw hook; commands are queued on the worker and consumed after joining. Frontend rumble callbacks run only on the frontend thread.

Gamepad Rumble defaults Enabled. Framework F11 output gating preserves and updates native effect state while muted; re-enabling restores active levels without a new native command. The original source implementation receives its normal active update, with only the frontend output gated. Reset/unload stop motors and clear retained commands/effects. Existing source-specific synthetic effects are reused; no new generic rumble is invented. Startup-disabled, live mute/unmute, release while muted and teardown pass mocked callback tests. Physical motor output is unverified.

## A/V Timing And Audio

User decision: **60 Hz (Default)**, with **58 Hz (Native Model2EmuEx)**, using SM2 raw tokens `60hz` / `native`. The setting is latched at content load and requires closing/reloading content; machine reset does not adopt a pending choice. Each callback executes one native board frame with unchanged CPU/device cycles. Native synthesis remains 44,100 Hz at the board's declared 58 Hz cadence, before the next board frame queues sound commands.

At 60 Hz the adapter uses SM2's endpoint linear interpolation to produce the corresponding 44,100/60 output slice. Native mode bypasses interpolation. Unaccepted batch samples are retained; an audio sink stalled for more than one second requests shutdown with a diagnostic rather than growing memory indefinitely. Reset/unload clear pending audio. At 900 frames VF2 produces 684,310 stereo frames in Native mode or 661,500 at 60 Hz, with identical main RAM. Original pristine PCM parity predates the documented SCSP scheduling correction; Auto preserves the current native mix, not a promise of pristine pre-correction PCM equality. Partial frontend acceptance was exercised at 60 Hz.

SCSP Gain, MultiPCM 1 Gain, MultiPCM 2 Gain and FM (YM3438) Gain retain SM2's Auto/Mute/10–100% choices, Auto default and Resume-without-reset lifecycle. Auto and 100% preserve destination mix coefficients (0.5 per MultiPCM, 0.30 FM). Muting never stops CPUs/chips. Gains survive native sound reset, and absent sources are documented no-ops. SCSP mute produced zero PCM while preserving machine RAM; the original Model 2 sound board was also tested: all MultiPCM/YM3438 sources muted produce zero PCM with unchanged main RAM. Individual source isolation now passes through the actual adapter option readers and both native sound-board families plus the auxiliary M1 scheduler. `make check-sound` covers all gain levels, native-default/Auto/100% equality, unchanged synthesis state, other-source independence, live mute/resume and gain retention at reset. See VALIDATION.md for synthetic-fixture scope and remaining audible/device limits. DSB controls and enhanced-balance profiles are not exposed before their corresponding sound hardware/profile integration.

User decision — 2026-10-20: retain Model2EmuEx's native SCSP output. Do not add SM2's 8 kHz output low-pass filter or its Core Option. This exclusion concerns the additional SCSP filter; the previously approved source gains and 60 Hz/Native A/V Timing remain in place.

## Crosshairs

User decision: reuse all SM2 styles and defaults. Show Crosshair defaults Automatic, Crosshair Style defaults SM2-Emu, and Crosshair Inactivity Timeout defaults Disabled. Other visibility, style and timeout values are unchanged. The style label describes the graphic; the core name remains Model2EmuEx.

The unchanged SM2 module supplies geometry, source activity, per-player hiding, PNG decoding/fallback and clipping. Custom artwork uses `system/model2emuex/crosshairs`: game-p1.png / game-p2.png / game.png, then parent, then default. PNGs are limited to 1024 × 1024 and content reload is required after changing files. Auto falls back to SM2-Emu; Custom reports missing/invalid artwork and substitutes no reticle. Notice wording translates only the destination directory.

The adapter batches coloured/alpha-blended rectangles into a separate OpenGL overlay, uses the frontend FBO, and owns its buffers/shaders across context reset/destroy. Pipeline display uses the aim snapshot matching the presented machine frame. Timers advance at the selected presentation cadence even when drawing is skipped. Source tests cover both colours/styles, PNG alpha/fallback and independent timeouts. Actual RetroArch Virtua Cop checks additionally cover independent P1/P2 movement and visibility, live SM2-Emu/Supermodel styles, Auto's no-artwork fallback, distinct player PNGs, independent inactivity, restored aim positions with current style authority, and native-menu Restart retaining artwork. See VALIDATION.md for receipts and the supplementary exact-frame PNG round-trip limitation. Physical aiming remains unverified and belongs to M14.

## Timing / FPS Overlay

The SM2 panel, Off/Auto/11–14 px choices and 61-frame measurement equations are integrated, with destination-native cadence in the caption and a frontend-owned GL submission path. The existing bundled ImGui sources supply the panel; no external dependency is installed. Measurements, lifecycle and source/frontend evidence are documented in [Timing Overlay](TIMING_OVERLAY.md). Diagnostic estimates do not establish sustained gameplay performance.

## Remaining Integration

Save States are integrated through native machine serialization and SM2-style frontend continuation; see [Save States](SAVE_STATES.md). External Linked Cabinets/Netpacket and ANRS are integrated; see [External Linked Cabinets](EXTERNAL_LINKED_CABINETS.md) for the approved all-set local loopback, state compatibility and evidence limits. Manx TT cabinet audio, its additional native sound board, full serial return and AMS are integrated following SM2; see [Manx TT Cabinet Audio](MANX_TT_CABINET_AUDIO.md). Hide Shot Flash and its selector, the added SCSP output low-pass filter, and native cooperative play are excluded by user decision. Keep those distinctions explicit and expose no nonfunctional placeholders.


## Manx TT Cabinet Audio

The Audio selector matches SM2's label/help, Enabled/Disabled values and Enabled
default. Valid NVRAM Cabinet Type selects Twin/Deluxe SCSP ROMs; Disabled retains
selected-set ROMs while keeping required Deluxe hardware, exactly as SM2.
Optional sound-only donors, notices, no NVRAM writes, native source gains,
serial replies and guarded Save States are covered in
[Manx TT Cabinet Audio](MANX_TT_CABINET_AUDIO.md). Other games retain their
native audio path; audible output and devices remain separately qualified.
