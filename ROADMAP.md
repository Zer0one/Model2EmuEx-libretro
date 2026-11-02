# Model2EmuEx Libretro Roadmap

Updated: 2026-11-02. This is the project's sole implementation roadmap. The applicability matrix and option reviews are reference inventories; they do not establish delivery status. Repository: `main`, integrated upstream baseline `25d82be56f339c754cc566f771ca9ffb90b69289`. The user authorized first GitHub publication, commit, push and release on 2026-11-02. Target: `Zer0one/Model2EmuEx-libretro`; this does not authorize later unrelated publication.

**Legend:** 🟢 Completed · 🟡 Partial · ⚪ Not Started · 🔵 Deferred.

Rows are grouped by status. Stable activity IDs are retained for traceability. Completed source integration does not imply gameplay, physical-device, other-platform or publication acceptance. Evidence belongs in [Validation](VALIDATION.md); current option registration is in [Implemented Options](CORE_OPTIONS_IMPLEMENTED_REVIEW.md).

## Implementation Status

| Status | Activity | Remaining Work |
| --- | --- | --- |
| 🟢 | M01 — Independent Repository | Baseline history and upstream remote retained; pristine sibling checkout untouched. First public repository preparation is authorized. |
| 🟢 | M02 — Native macOS Build And Frontend Boundary | Native arm64 core and standalone/headless targets build. Neutral loader, raw-drive and source-gain interfaces are documented; no SDL runtime dependency. Other platforms are tracked in M16. |
| 🟢 | M03 — Libretro Lifecycle And SRAM | Frontend GL ownership, callbacks, 64 KiB backup plus EEPROM, reset and reload integration delivered. Broader context-loss/device verification is tracked in M14. |
| 🟢 | M04 — Pristine Comparison Baseline | Historical VF2/Sega Rally 900-frame baseline established. Historical Native-timing VF2 RAM/PCM were pristine-exact after integration; the later SCSP timing correction intentionally changes active audio. This is not all-game accuracy acceptance. |
| 🟢 | M05 — Local RetroArch Delivery | User-authorized local copy passes a bounded VF2 3D run at 60 Hz; installed/source hashes match. Repeat targeted frontend checks when subsequent changes warrant them. |
| 🟢 | M06 — Scripted VF2 Paid Match | Scripted coin/Start/Punch reached a paid match in the ABI frontend. Physical input and sustained frontend gameplay remain in M14. |
| 🟢 | M07 — Native Texture Filtering | Nearest/Bilinear/Trilinear selectors, runtime changes and shader fallback verified. Retain native values rather than advertising absent anisotropic filtering. |
| 🟢 | M09 — Applicable Native Selectors | Delivered under the decisions in [Native Options](NATIVE_OPTIONS.md). Window/scaling stays frontend-owned; separate keyboard/cooperative controls are excluded. |
| 🟢 | M15 — MAME ROM Set Alignment | All 28 Libretro sets checked against the pinned source; `daytona93` canonical, `srallyp` excluded, standalone catalogue retained. New upstream/MAME revisions require their own review. |
| 🟢 | M19 — ROM CRC Verification | Actual stored/deflated/loose payload verification, Enabled default, Disabled bypass and strict size/decompression checks tested. Original standalone API retains metadata-only CRC policy. |
| 🟢 | M20 — Timing / FPS Overlay | SM2 panel/options, 61-frame measurements, font/4x/context/reset/skip tests, exact RAM/PCM comparisons and real RetroArch checks delivered. CPU/GPU interpretation and pipeline estimates are documented in TIMING_OVERLAY.md. |
| 🟢 | M12 — Save States | Complete native machine/sound/geometry serialization, validated 12 MiB container, pointer rebinding, rollback and GPU/audio/rumble recovery delivered. VF2/Daytona exact continuations, fresh-process loads, NVRAM authority and real RetroArch frame/pixel checks pass. Broader device/platform qualification remains in M14/M16. |
| 🟢 | M13 — External Linked Cabinets | Native seam and SM2 Netpacket delivered; two local Daytona instances reach a shared race, Sega Rally links recover after Restart. All-set local loopback matches SM2; native activation/roles remain game-owned and offline Save States retain prior-header read support. Higher totals/platforms, real lobby option-editing coverage and broader gameplay remain M14/M16 qualification. See EXTERNAL_LINKED_CABINETS.md. |
| 🟢 | M21 — Auto Network Role Settings | Delivered with M13 as its required F14 dependency: 14 destination pairs, SM2 mappings/Disabled defaults, independent authority, hidden-field synchronization/handover and one effective-change reset. APIs 2/1/0 and working-family/clone checks pass; future-board gameplay and broader frontend/device qualification remain M14/M16. |
| 🟢 | M23 — NVRAM Source Review And Evidence Index | Current SM2 source/import and actual registration reconciled: 340 fields/56 catalogs, 28 destination routes/19 applicable catalogs, approved template policy and existing evidence indexed. No workbook duplication or acquisition. Initial-template error-reporting omission corrected immediately following SM2; injected failures and normal/disabled/no-template cases pass. Destination persistence coverage remains M11. See NVRAM_SOURCE_REVIEW.md. |
| 🟢 | M24 — Cabinet Audio And Applicable Extensions | Manx TT Twin/Deluxe/selected-set policy, full serial return, additional native M1 board, AMS and guarded Save States integrated following SM2. ROM-free, actual-core policy, OpenGL continuation and real RetroArch checks pass. No other destination set declares a new applicable extra sound board; no prototype controls added. Listening/device qualification remains M14. See MANX_TT_CABINET_AUDIO.md. |
| 🟢 | M25 — Libretro Adapter Error Handling And Recovery | Four documented adapter bugs corrected: pending NVRAM retry/coalescing, error severity/fatal cleanup, GL context abandonment and queued network corrections. ABI, GL replacement, state, network and installed RetroArch checks pass. Raw standalone-compatible SRAM and Model2EmuEx emulation are preserved; physical GPU loss/motors remain M14. See FRONTEND_CONTRACT_REVIEW.md. |
| 🟢 | M10 — Shared Audio Controls And A/V Timing | Existing 60 Hz/Native cadence and delivery checks retained; seven main/auxiliary native source paths pass 98 selector/fallback comparisons and six mixed-source isolation checks through actual adapter readers. Auto/100 preserve native mix, mute preserves synthesis, live resume/reset retain gain semantics. No core change needed. Listening/device and wider sound accuracy remain M14; added SCSP filtering stays excluded. |
| 🟢 | M11 — NVRAM Engine, Templates And Adapter Persistence | Existing SM2 source/registration matched; 526 adapter value cases on 25 sets/18 catalogs pass, preserving checksums and extra RAM. Two raw-save RetroArch sessions verify template precedence and reload; ABI verifies override authority. Turbo no-template policy and prototype metadata-only scope retained. Per-title native Service Menu/gameplay qualification remains M14. See NVRAM_SOURCE_REVIEW.md. |
| 🟢 | M18 — Crosshair Presentation | Unchanged SM2 geometry/artwork/activity module and destination GL overlay integrated. Actual RetroArch Virtua Cop checks cover P1/P2 visibility/movement, live styles, Auto fallback, distinct PNGs, independent timeout, restored aim positions/current style authority and native-menu Restart retaining artwork. No core change needed. Physical aiming and broader qualification remain M14; see VALIDATION.md for the uncompleted supplementary exact-frame PNG probe. |
| 🟡 | M08 — Shared Input Profiles And Native Wiring | Full SM2 engine/metadata and all 28 destination bindings pass source/adapter tests. Actual RetroArch native Input Tests verify 15 Sega Rally and 18 VF2 cases. Live Normal-profile editing was not completed; broader per-title gameplay and actual devices remain unqualified. |
| 🟡 | M17 — Gamepad Rumble | Raw native observation, SM2 decoder and Framework mute/unmute/reset/unload policy pass callback tests. Physical motor response and per-game active-play qualification remain. |
| 🟡 | M26 — Upstream Reconciliation And Source Provenance | Static review completed: 41 import hashes verify, Netpacket donor/adapted identity corrected, missing referenced BSD text retained, component credits recorded. Original port contributions use GPL-3.0-or-later; recovered native-code terms remain unspecified and no overall license is inferred. Future authorized upstream integrations retain semantic review. See LIBRETRO_DESIGN.md. |
| 🟡 | M16 — Additional Platforms And Packaging | Five-platform Linux/macOS/Windows release recipes, corresponding-source packaging and SM2-style branch/PR/tag Actions delivered for 0.1.0; local macOS arm64 checks pass. Remote build outcomes are tracked in Actions; universal builds and wider runtime qualification remain. Publication qualification is recorded in VALIDATION.md. |
| ⚪ | M14 — Runtime And Physical Qualification | Per-title native Service Menu/persistence acceptance beyond existing evidence, sustained gameplay, controllers, lightguns, audible output, motors and actual GPU context loss. Record each game/device/platform independently; absence of runtime evidence does not exclude frontend preparation. |

## Current Functional Group And Stop Point

First release delivery: **0.1.0** is this independent port's version, separate
from its pinned upstream commit. The GitHub workflow follows SM2's build,
matching-source, checked-package and tagged-release stages. This delivery
targets Linux x86_64/ARM64, macOS Apple Silicon/Intel and Windows x86_64. CI/build
receipts and runtime qualification retain separate scope. GitHub page:
https://github.com/Zer0one/Model2EmuEx-libretro.

M08's targeted native Input Test checks are finished: actual RetroArch verifies 15 Sega Rally cases and 18 VF2 cases, including analog pressure and independent players. Current SM2 input sources remain identical to the imported engine; all 28 adapter profiles pass existing source tests. No core fix or binary update was needed. The reusable frontend runner now accepts existing input replays, and a two-title fixture generator reuses SM2's replay format.

M08 remains Partial: the attempted live change to Normal was not completed after UI access lost its window. Adapter gating tests pass, but paused-menu metadata refresh is not newly frontend-qualified. Broader per-title gameplay and physical devices remain separate. That check stopped without retrying; the user subsequently authorized first-release preparation. M18's supplementary exact-frame PNG probe also remains uncompleted; earlier M12 evidence retains its original scope.

User-requested M08/M18 artifact cleanup removed 1,004 task-owned files (496,291,840 allocated bytes, approximately 473 MiB), retaining accepted screenshots, useful state/configuration files, recipes, logs and receipts. Retained evidence hashes and 197 protected source/core/configuration hashes were verified. See VALIDATION.md. No ROM copies or dependency installation occurred in those checks. The subsequent first-release commit/push is explicitly authorized. SM2 remains the interface/approved-common-function reference; emulation remains Model2EmuEx's.

## Explicit User Decisions

- Keep the project rolling; the visible name is Sega - Model 2 (Model2EmuEx).
- Pre-release development persistence formats have no general backward-compatibility requirement. Preserve native standalone-compatible raw Save RAM (64 KiB backup + 128-byte EEPROM), explicitly selected after checking other cores. No SM2 envelope or format migration is pending.
- Follow SM2/SEGA Model Core menus and defaults where equivalent; add actual native capabilities such as 16:10 and native texture filters.
- Use separate Aspect Ratio and Widescreen Mode controls. RetroArch owns final scaling/fill.
- No native cooperative mode/layouts or separate keyboard input/selectors.
- Every catalog entry retains its board in local loopback with Linked Cabinets disabled, following SM2 and the explicit 2026-10-21 choice; native activation/roles remain independent.
- Use only SM2 exact-template/explicit-compatible-parent initial NVRAM policy; no native Daytona fallback.
- Use current SM2 source as the primary NVRAM reference. The existing workbook is shared across SEGA Model 2 emulators and may be out of date; no per-core workbook recreation. Report concrete discrepancies and their impact.
- Default A/V Timing is 60 Hz; destination Native is 58 Hz. Retain SM2 crosshair styles/defaults and `system/model2emuex/crosshairs` artwork directory.
- Preserve native SCSP output; exclude the added 8 kHz low-pass filter and its selector.
- Exclude Hide Shot Flash (M22) and its selector from this port.
- Stop after each functional group for a summary; publication requires explicit authorization (granted for this first release).

## Reference And Scope Rules

SM2-Emu supplies the independent-port method and primary menu/control reference. Framework edition 0.1.42 was inspected with its source index, SM2's porting manifesto/options/input sources, and Supermodel's live internal-resolution contract. No changes were made to those reference projects. Changes needed in other cores require their own approved scope.

The first working core establishes an integration baseline, not full feature parity. Pending rows are not delivery claims. Unrequested prototype-specific analysis, implementation and testing remain excluded. Machine changes and future upstream imports require matched pristine comparisons. Never infer gameplay, physical input or audible-output proof from a successful build or ABI test.

## Confirmed Option Policy — 2026-10-20

Use the emulator's native selectors for its specific functions. These are additional to common Framework/SM2 options, including Gamepad Rumble and NVRAM Settings. Common controls remain in scope, subject to actual hardware support and source-backed adaptation. This decision does not mark pending common features as implemented. For a genuine semantic conflict, present a concrete proposal before implementation.

## Common Options Review

The common-option review is a menu inventory, not a limit on the transferable implementation scope. The complete source-level assessment is in [SM2 Applicability](SM2_APPLICABILITY.md), with all 62 Libretro reference files and the complete reference game catalogue recorded in [Reference Inventory](SM2_REFERENCE_INVENTORY.json). Model 2B/2C frontend preparation is in scope now; execution is tracked separately. The common-option inventory, defaults and destination prerequisites are in [Common Core Options Review](COMMON_OPTIONS_REVIEW.md). It was prepared for user review on 2026-10-20. It does not register new options or supersede current runtime defaults before the review decisions are resolved.

## Full SM2 Reference Adoption — 2026-10-20

- The complete SM2 implementation is the source: all control profiles, NVRAM engine/catalogue/templates, data, samples, tests, frontend lifecycle and applicable extensions. Existing solutions precede new analysis or acquisition.
- Prepare frontend support for Model 2B/2C before execution is available. Keep backend runtime status separate; it is not an exclusion from metadata, profile, option, NVRAM or ROM-free-test work.
- Source-level applicability audit completed across 37 subsystem rows and all 62 Libretro files; complete 88-entry reference catalogue retained for preparation. This is not a claim that all pending runtime features are implemented.
- Unchanged SM2 NVRAM engine/templates were compiled and probed against destination memory views: VF2 8 options/19 values; Sega Rally 6 options/21 values. Existing VF2 capture recognised directly; Sega Rally source template accepted, while its existing 900-frame capture did not pass the reference layout check. Reuse-first integration follows these results.

## MAME ROM Set Alignment

Delivered by explicit user request: canonical MAME names/parents/file identities in a Libretro-only 28-set overlay, `daytona93` naming and sound-program revision corrected, `srallyp` excluded by user decision, original standalone catalogue preserved. Compiled-catalogue and ROM-free archive tests pass. Daytona/VF2 exact same-revision comparisons and Daytona 1993 rendering checks are recorded in MAME_ROMSET_ALIGNMENT.md. No new Core Options were added; the menu remains under user review.

User decision — 2026-10-20: retain Model2EmuEx's native SCSP output. Do not add SM2's 8 kHz output low-pass filter or its Core Option. This exclusion concerns the additional SCSP filter; the previously approved source gains and 60 Hz/Native A/V Timing remain in place.

### Sega Rally Incident Follow-Up — 2026-10-21

The native EEPROM start-bit correction makes the existing approved Country values effective in the game (Export at fresh startup, USA override visually verified). No NVRAM policy or template changed. The installed Core Info cache was also stale and advertised no Save States; only that core entry was refreshed. See NVRAM_SAVESTATE_DIAGNOSTIC.md. These are validation/correction notes within existing NVRAM and M12 scope. The subsequently supplied gameplay state reproduced the black upper sky. The native renderer now clears to palette pen 0, matching SM2/MAME; pixel isolation and same/fresh-process state continuation pass. See SKY_SRALLYC_DIAGNOSTIC.md.

### External Linked Cabinets — 2026-10-21

SM2 is the primary source for M13 transport, controls and lifecycle. The user explicitly approved next-running-frame application in non-pausing Netplay menus; this is also the current SM2 implementation. Exactly one per-game Linked Cabinets/Auto Network Role Settings pair is visible. Defaults are Disabled; native role and topology remain independent. The user approved local loopback for every set with the external link disabled. A shared unconditional path applies this policy; targeted tests cover integration and offline Save States without claiming whole-catalog gameplay verification. Synthetic transport, ABI, real frontend roster/native-link and race-start evidence are tracked separately in EXTERNAL_LINKED_CABINETS.md.
