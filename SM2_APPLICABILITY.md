# Complete SM2-Emu Applicability Review

Date: 2026-10-20. Scope: the complete SM2-Emu Libretro implementation and its supporting data, tests, tools and documented machine improvements. This replaces a selective menu-first assessment. The reference is the live SM2 working copy, including its uncommitted changes; HEAD alone does not identify that state.

## Current Integration Update

The matrix below preserves the original applicability assessment. Its initial destination counts and next-step cells are historical, not the current implementation state. The MAME-aligned loader now contains 28 sets, all bound to SM2 profiles in adapter tests. The full SM2 NVRAM engine/catalogue/templates, input/rumble engine and metadata, gun/gear/driving controls, source gains, 60 Hz/Native A/V Timing and crosshair presentation are integrated. Unchanged full SM2 input checks pass, in addition to destination wiring tests. See [Shared Features](COMMON_FEATURES.md), [Implemented Options](CORE_OPTIONS_IMPLEMENTED_REVIEW.md) and [Validation](VALIDATION.md) for current status and limits. Save States are now integrated with native serializers and separate continuation/frontend verification; see [Save States](SAVE_STATES.md). External networking and the coupled ANRS controls are now integrated; see EXTERNAL_LINKED_CABINETS.md for actual frontend/race evidence and the approved all-set local loopback. Compiled/imported code alone does not establish gameplay.

## Scope And Status Rules

**Use SM2 as the full implementation reference.** Reuse delivered code, data, defaults, profiles, samples and tests first. Translate only concrete destination interfaces and preserve the original emulator boundary. Do not recreate an acquisition campaign, checksum engine or control scheme already implemented by SM2.

User clarification, 2026-10-22: the existing workbook is a shared SEGA Model 2 reference, not an emulator-specific deliverable. Do not recreate it for this port. Current SM2 source takes precedence when checking implemented fields, values, defaults, templates and behavior; workbook contents may be out of date. M23 remains a source review and existing-evidence index. Report concrete discrepancies and their impact before resolving target-specific semantic choices.

**Prepare frontend support independently of runtime support.** Model 2B/2C belong in the preparation scope: profiles, NVRAM catalogues/templates, options, metadata, transport/feedback policy and ROM-free tests can be prepared before their machine executes. The current destination catalogue/runtime is a measurement, not an exclusion list. Missing execution prevents gameplay acceptance, not frontend implementation. Prototype-specific new work still requires the user's explicit request.

Distinguish four independent statuses for every transfer: reference available; destination code/data imported; destination interfaces integrated and ROM-free tested; actual game/frontend/hardware verified. A reference module, inventory record or successful source-level probe is not a delivered runtime feature.

The snapshot records **62 files under SM2 src/libretro**, including all checks and ABI/build files. The full reference game catalogue has **88 entries**. The destination currently lists **24 entries**: 23 Model 2/2A and one Model 2B. Twenty names match the reference exactly; exact names alone do not prove identical ROM revisions. All reference catalogue entries are retained in the planning inventory, including those absent from the current destination loader.

See [Machine-Readable Inventory](SM2_REFERENCE_INVENTORY.json) for per-file hashes, dirty reference paths, both catalogues and exact-name joins. Recreate it with:

```sh
python3 scripts/audit-sm2-reference.py \
  --reference /path/to/sm2-emu-libretro --output SM2_REFERENCE_INVENTORY.json
```

## Native Emulator Selectors — First Priority

The complete native-selector inventory and delivered/pending status are in [Native Emulator Selectors](NATIVE_OPTIONS.md). They are the first implementation priority, as the user originally requested. This SM2 applicability matrix supplements that native starting point. Nine native controls are now registered; native execution/presentation controls remain ahead of common additions.

## Applicability Matrix

Paths in the reference column are relative to SM2-Emu unless otherwise stated. **Reuse** identifies existing implementation to carry forward; it does not claim the destination already implements it.

| ID | Subsystem | Existing SM2 Reference | Reuse And Concrete Destination Adaptation | Current Verification / Next Integration |
| --- | --- | --- | --- | --- |
| R01 | Core ABI / lifecycle | `src/libretro/core.cpp`, ABI headers | Reuse callback/lifecycle/reset/error-handling contracts. Bind `m2_board` rather than the SM2 machine factory. Retain existing destination GL core. | Initial destination ABI exists; full lifecycle contracts remain to integrate. |
| R02 | Full Core Options catalogue | `core_options.h` | Reuse category order, names/help, raw tokens/defaults, parsing, applicability and legacy registration. Native renderer selectors retain the user's approved destination values. | Seven native Video options and two native Input options delivered. Complete reference registration is the baseline for remaining work. |
| R03 | Game identification / clone inheritance | `rom/game_db.*`, `data/games.xml` | Reuse reviewed metadata and inheritance as adaptation inputs. Keep original loader identities; map aliases explicitly and verify revisions through ROM metadata. Do not assume destination parent chains equal SM2 chains. | 20 exact-name joins and 4 unresolved identities recorded; full 88-entry reference retained for future backend preparation. |
| R04 | Control-profile recognition | `input.h`, `input.cpp`, `CONTROL_PROFILES.md` | Reuse the complete enum, profile names, action catalogue and recognition contracts. Translate GameSpec/input metadata into the destination's native ports/axes. Keep profiles for 2B/2C ready even before runtime. | Current destination only has a VF2 adaptation and generic fallback; whole profile engine needs integration. |
| R05 | RetroPad layouts / descriptors | `input.cpp`, `checks/input.cpp` | Reuse physical layouts, labels, controller subclasses, player counts, remapping and unplugged-port handling. Translate final writes into `m2_board.port`, `analog` and gun state. | Source-defined behavior available; preserve up to four-player profile support even though initial adapter polls two ports. |
| R06 | Controller Profile Type / Test/Service | `configure_controllers`, `profile_devices`, paused refresh in `core.cpp` | Reuse Normal / Normal + Test/Service and its global default, descriptor refresh and supplemental actions. Use destination native Test/Service masks, not invented new profiles. | Current F1/F2 keyboard handling is not equivalent to the full feature. |
| R07 | View actions / VR1 aliases | `input.cpp`, current VR1 integration records | Reuse reviewed VR1/VR2/VR4 layouts and supplemental D-Pad Up where appropriate. Preserve native Start/View sharing and real action conflicts. | Apply by matching game/revision, including future games. |
| R08 | Driving and gear controls | `InputRuntime`, driving options, four-speed/neutral/start-gear code | Reuse H-gate, sequential edge handling, neutral delay, start gear, response curves and output-range controls. Bind destination gear encoding and analog ranges once. | Destination generic driving code supplies native board conversion; it does not yet supply the complete reference controls. |
| R09 | Gun source arbitration / aiming | `input.cpp`, gun runtime/options, reference input checks | Reuse lightgun/mouse/stick arbitration, Standard/dedicated modes, relative/absolute sticks, off-screen semantics and per-player ownership. Translate final coordinates/native calibration access. | Prepare for all matching gun profiles, regardless of current backend availability. |
| R10 | Crosshair artwork / timeout | `crosshair.h/.cpp` | Reuse PNG loading/fallback, per-player activity, clipping and rectangle generation. Adapt metadata and image directory/core identity; draw through destination GL. | Reuse presentation logic; renderer hookup and path choice remain. |
| R11 | Gun-flash suppression/history | `gun_flash_state.h`, `core.cpp`, `hw/model2_video.*`, `checks/gun_flash.cpp` | Reference inventory only. Hide Shot Flash and its selector are excluded by explicit user decision on 2026-10-20. | Excluded from implementation scope; not pending or deferred. |
| R12 | NVRAM option engine | `nvram_settings.h/.cpp`, `nvram_settings_data.inc` | Reuse complete catalogue, value patches/masks, layout checks, mirrors and checksum algorithms. Provide first-16-KiB native backup view and EEPROM view while preserving extra destination bytes. | Unchanged SM2 code compiled and applied successfully in the probe below. |
| R13 | Initial NVRAM templates | `initial_nvram.h/.cpp`, `initial_nvram_templates.inc` | Reuse compressed templates, validation and parent/clone policy, approved region/standalone/calibration setup. Preserve valid existing destination saves. | Reference VF2/Sega Rally templates pass destination-memory-view probe. Extend to the complete matching catalogue, including future backends. |
| R14 | NVRAM gate / apply / notification | `core.cpp`, `core_options.h`, `checks/save_ram.cpp` | Reuse Disabled default, authoritative overrides, detection of effective changes, one reset, paused option-update retention and unchanged-value behavior. Bind destination reset/sound/GL invalidation and frontend SRAM bridge. | Initial destination bridge exists; complete option/reset policy remains to integrate. |
| R15 | NVRAM evidence / samples / workbooks | `GAME_SETTINGS_CATALOG.md`, YAML, `scripts/NVRAM_CAMPAIGNS.md`, existing samples/workbooks | Carry forward the existing fields, samples, defaults, status and tests. Adapt format boundaries and validate imported implementation. New acquisition only for demonstrated gaps. | No new inventory campaign is needed as the default starting point. |
| R16 | SRAM container / import/export | `save_ram.h/.cpp`, `core.cpp` | Reuse validation/precedence/error-reporting logic. SM2's 64-byte header + 16-KiB payload is a different frontend container from destination raw 64-KiB backup + EEPROM; keep their formats explicit and preserve destination tail. | Container compatibility policy needs a concrete migration design before changing existing raw destination SRAM. Native field reuse does not require adopting SM2's whole file container. |
| R17 | ANRS native role policy | `automatic_network.h/.cpp`, NVRAM catalogue | Reuse choices, managed fields, native identities, Disabled default and independence from Linked Cabinets/NVRAM gate. It is largely frontend-neutral policy. | Integrate with the reused NVRAM engine; can be prepared for 2B/2C now. |
| R18 | Linked Cabinets / Netpacket | `netpacket.h/.cpp`, `hw/comm_transport.h`, `hw/m2comm.*`, checks | Reuse Libretro callback ownership, roster/readiness, packets, routing and teardown. Destination `m2net` currently owns an in-process lockstep ring; add a neutral transport boundary rather than copying the SM2 machine. | Protocol/adapter work is needed. Current lack of external transport is an adaptation task, not an exclusion. |
| R19 | Native drive feedback / rumble | `rumble.h/.cpp`, `osd/drive_command.h/.cpp`, checks | Reuse native protocol decoder and mixing/output policy, including mute/unmute/startup/reset/unload. Bind destination raw drive writes and reviewed protocol metadata. | Destination hook currently filters some writes (zero, 0x83, duplicates); verify/preserve the raw stream needed by the reference decoder with a neutral hook. |
| R20 | Synthetic feedback | Existing synthetic paths in `rumble.cpp`, input metadata | Reuse only the existing reviewed game/protocol-specific synthetic effects and frontend-axis threshold. Do not invent additional generic vibration. | Prepare matching source behavior, keeping native and synthetic effects independent. |
| R21 | Audio source gains / balance | `SoundBoard` source controls, options, `checks/audio*` | Reuse Auto/Mute/manual contracts and native source coefficients where equivalent. Expose each destination source before mixing/clipping, with muted synthesis still advancing. | Destination has SCSP, two MultiPCM and YM3438; neutral gain/mixer interfaces needed. DSB/extra-board controls can be prepared with explicit absent-source no-ops. |
| R22 | Audio output filtering / timing | `audio_output.h`, core output path, native SCSP low-pass code and sound-timing checks | Reuse implemented algorithms where their input/output contracts match; bind destination sample cadence and filter state. Any synthesis/response change is separately tracked and compared against native baseline. | Native Auto-gain PCM baseline is exact to destination upstream. The user explicitly excluded the added 8 kHz SCSP low-pass filter and its selector on 2026-10-20; retain native output. Approved A/V Timing remains integrated. |
| R23 | 60 Hz / Native presentation | SM2 A/V timing path and checks | Reuse the complete cadence/audio policy and 60hz/native selectors. Destination Native uses its own per-game FPS. Keep CPU/game frame progression separate from presentation. | Current destination always reports native. Transfer SM2 behavior rather than relabelling 58 as SM2's 57.524. |
| R24 | Aspect ratio / widescreen | Current options/core presentation, SM2 geometry policy | Reuse Auto/4:3/16:9 and Widescreen dependency/default Disabled. Bind destination `m2wide_update` and native geometry/layer rules. | Existing destination native API supports adaptation; preserve per-game behavior. |
| R25 | Timing/FPS overlay | `timing_overlay.h/.cpp`, checks | Reuse measurements, layout and font-size options. Adapt geometry submission to destination GL and reuse existing rendering dependencies only when needed. | Not tied to SM2 emulation. |
| R26 | GL context ownership / loss | `opengl_renderer.cpp`, `gpu.h`, `core.cpp` | Reuse reset/destroy/abandonment and authoritative-state restoration patterns, not SM2 render-pass objects. Preserve destination shaders and final-FBO translation. | Destination initial GL tests exist; true context-loss/restoration campaign remains. |
| R27 | Vulkan / software / image enhancements | `vulkan_renderer.cpp`, negotiation/dispatch, SM2 render backend and shaders | Reuse frontend negotiation, ownership and lifecycle contracts. Actual SM2 pass/shader code depends on its geometry/texture structures; adapt only through a deliberate destination renderer integration. | Future backend work; not directly linkable as another destination renderer merely by adding menu values. |
| R28 | Save States | `core.cpp` container/validation, `core/archive.h`, machine serializers, checks | Reuse frontend wrapper semantics, errors, lifecycle and test procedures. Serialize destination CPU/TGP/audio/device/memory state through its own neutral machine interfaces; exclude pointers and rebuild derived renderer state. | Delivered for executable Model 2/2A through native serializers, a validated 12 MiB container and SM2-style continuation/recovery. See SAVE_STATES.md and VALIDATION.md; other-board runtime qualification remains dependent on execution support. |
| R29 | Manx TT cabinet audio | `manxtt_audio.h/.cpp`, native sound/drive code and checks | Reuse cabinet-selection policy, donor precedence, Twin/Deluxe rules and acknowledgement behavior. Destination contains Manx TT sets; bind additional sound-board/ROM facilities. | Integrated cabinet policy, extra native M1 board, full I8251 return, AMS and guarded states; see MANX_TT_CABINET_AUDIO.md for source/test/runtime evidence and limits. |
| R30 | Power Sled extensions | `power_sled_*`, native protocol/render/audio integrations | Reuse native roles, lever layouts, extra audio policy, commands, captions and existing verified limitations. Preserve experimental status. | Prepare frontend metadata/options/policy for Model 2B now. Actual machine/audio/render execution remains future verification. |
| R31 | Other specialised cabinets | `input.cpp`, game metadata, native I/O/drive helpers | Reuse Ski Super G, Top Skater, Wave Runner, Air Walkers, Royal Ascot and other source-defined profiles and cabinet conventions. | Retain preparation scope even if absent from current destination game database. Translate native hooks when their backends arrive. |
| R32 | ROM validation / BIOS/device lookup | SM2 loader parameters and device-directory policy | Reuse explicit CRC validation behavior, parent/device precedence and clear missing-set diagnostics. Translate into existing destination ZIP/loose loader, with minimal neutral changes. | Existing CRC metadata matching is not computed-payload verification. Source-level loader adaptation required. |
| R33 | Game-specific protection / fixes | SM2 DOA, Daytona GTX, native I/O/tile/device fixes and checks | Review each delivered fix against destination implementation and ROM revision; reuse algorithms/evidence where the same defect exists. Keep machine fixes separate from frontend import. | GTX is listed but its hook is unknown; DOA is absent from current catalogue. Prepare support rather than excluding it solely for absence. No blind wholesale replacement of destination CPUs/devices. |
| R34 | Core packaging / symbol exports | Libretro CMake target, exports files, info, CI/release scripts | Reuse ABI-only exports, development naming, dependency audits and platform checks, adapting root Make build. Keep source provenance/notices. | Destination macOS development dylib exists. Future platform work can prepare frontend code now. |
| R35 | Launchers / frontend runners | `scripts/launch-linked-cabinets.py`, network/RetroArch runners | Reuse process ownership, config/save/port isolation, gamepad assignment and result evidence; parameterize destination core/options/formats. | Current destination isolated runner exists; import reference functionality rather than reinventing it. |
| R36 | Regression / sample tooling | `src/libretro/checks/*`, smoke/compare/NVRAM scripts, remote skills | Port equivalent assertions, fixtures and acceptance semantics along with each module. Machine-specific fixture construction is adapted, not used as a reason to omit the test. | Destination comparison harness exists; complete reference tests remain to carry forward. |
| R37 | Roadmaps / documentation / release provenance | Manifesto, design/manual, settings/profile workbooks, CI/version conventions | Reuse working method and document structure, replacing destination facts and measured status. Preserve existing reference evidence and distinguish imported, integrated and runtime-tested. | This review and inventory record actual current source state, including dirty reference files. |

## Control-Profile Catalogue Mapping

The entire reference enum/catalogue is in scope, not only games that boot today. The following current-destination groups provide the first concrete bindings; matching frontend profiles for the rest of the reference catalogue must remain prepared independently of backend execution.

| Destination Sets | SM2 Profile / Source To Reuse | Adapter Binding |
| --- | --- | --- |
| daytona, daytona93, daytonat, daytonata, daytonase, daytonam, daytonas, daytonagtx | Driving4SpeedVR4; Daytona special identity/protection metadata where applicable | Native input_fn 0x4c9080, encoded gear/ports and steering ranges; resolve ROM aliases before selecting clone-specific catalogues. |
| desert | SpecialDesertTank / Joystick (Analog): Desert Tank + VR3 | Separate steering, acceleration, elevation, toggled shift and view actions; map native 0x4c9550 routine rather than treating it as a car. |
| vcop, vcopa, vcop2 | Gun | Reuse combined inputs, reload, per-player aiming and crosshair policies; bind serial gun words/mux and native calibration. |
| skytargt | JoystickAnalogSkyTarget | Reuse axis/button/view naming and physical layout; bind actual channels. |
| vf2, vf2a, vf2b, vf2o | Fighting | Reuse all actions and Test/Service profiles. Native Button 1/2/3 map to Guard/Punch/Kick; keep clone catalogue policy. |
| srallyc, srallycb | Driving4SpeedVR1Handbrake | Reuse gear/handbrake/view layouts; the non-MAME Pro Drivin' set is excluded by user decision. |
| motoraid | DrivingSequentialMotorRaid | Reuse motorcycle controls and supplemental actions; do not reinterpret handle/lean axes as a generic car wheel. |
| manxtt, manxttc | DrivingSequentialManxTT | Reuse motorcycle layout, cabinet metadata and native sound integration together. |
| overrevb | DrivingSequentialVR2 | Prepare full profile, options and NVRAM now; Model 2B execution is a separate status. |
| Other SM2 catalogue entries (including Model 2B/2C) | All remaining delivered reference profiles | Preserve full profile definitions, metadata, NVRAM/templates, options and unit fixtures. Backend/catalogue integration and game execution tracked independently. |

Name joins requiring explicit mapping: `dayton93`, `daytonat`, `daytonata`, `srallyp`. `dayton93`/`daytona93` is a candidate, not a confirmed ROM-revision equivalence. A shared name also needs revision validation before transplanting clone-specific state/calibration/protection.

## Direct Reuse Probe — NVRAM

The probe **compiles reference SM2 modules unchanged**: `nvram_settings.cpp`, `initial_nvram.cpp`, `save_ram.cpp` and their generated data. It adds no machine emulation and mutates only private memory copies. Source: [probe-sm2-nvram.cpp](scripts/probe-sm2-nvram.cpp).

Provide the first 16 KiB of the destination's 64-KiB backup buffer and the existing 128-byte EEPROM separately. The remaining backup bytes are preserved. This demonstrates that adapting the views is sufficient for the tested catalogue engine; no new checksum implementation or operator-setting acquisition was needed.

| Game | Native Destination Capture Recognised By SM2 | Existing SM2 Template Accepted | Options / Values Applied | Result |
| --- | --- | --- | --- | --- |
| vf2 | Yes | Yes | 8 / 19 | Every value passes existing layout/checksum validation; extra backup bytes unchanged. |
| srallyc | No, for the existing 900-frame capture | Yes | 6 / 21 | Every value applied to the existing SM2 template passes validation; extra backup bytes unchanged. The captured destination memory is not assumed initialized/compatible merely because it has the right size. |

The Sega Rally observation does not establish a need for a new campaign or prove a backend defect. Reuse the existing template and regression evidence first, then inspect the concrete integration if needed. These are memory/engine tests, not proof that a game has accepted every changed value after boot.

Reproduce the probe (existing Apple toolchain only):

```sh
clang++ -std=c++20 -O2 -I/path/to/sm2-emu-libretro/src \
  scripts/probe-sm2-nvram.cpp \
  /path/to/sm2-emu-libretro/src/libretro/nvram_settings.cpp \
  /path/to/sm2-emu-libretro/src/libretro/initial_nvram.cpp \
  /path/to/sm2-emu-libretro/src/libretro/save_ram.cpp -o /tmp/probe-sm2-nvram
/tmp/probe-sm2-nvram vf2 /path/to/destination-core.nvram
```

The reference implementation requires C++20. The successful probe verifies that the current installed toolchain supports it. The C destination machine need not be rewritten in C++; the reusable helper can remain an isolated C++ translation unit behind a small C-facing adapter.

## Integration Order And Review Boundary

First complete the applicable native selector work in NATIVE_OPTIONS.md. Then carry forward the full SM2 reference scope, starting with data/options, NVRAM engine/templates, full control-profile representation and their existing tests; integrate native field writes through a thin bridge. Next bind feedback/audio/presentation and lifecycle; prepare networking and full state schemas alongside their destination machine hooks. Keep 2B/2C frontend preparation active throughout rather than waiting for gameplay.

Use SM2's existing semantics and defaults on clear equivalents. Present only a concrete unresolved collision, such as SRAM container migration or a true native protocol mismatch. Do not ask the user to redesign features already delivered in SM2. Neither this matrix nor stored reference metadata is a claim that the pending frontend modules have already been integrated into the destination core.

## MAME Identity Alignment Update

The current Libretro loader now uses the 28-set pinned MAME overlay documented in MAME_ROMSET_ALIGNMENT.md. The historical `dayton93` / `daytona93` program size/CRC identity is confirmed and the canonical name selects the exact existing reference catalogue. Its sound-program revision was corrected to MAME. `srallyp` is excluded by user decision. Older audit counts/name-join notes above describe the pre-alignment snapshot; the current loader manifest is authoritative. No broader SM2 or upstream checkout was edited.
