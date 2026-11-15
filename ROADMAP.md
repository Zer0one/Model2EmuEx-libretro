# Model2EmuEx Libretro Roadmap

Updated: 2026-11-15. This is the project's sole implementation roadmap. The applicability matrix and option reviews are reference inventories; they do not establish delivery status. Repository: `main`, integrated upstream baseline `25d82be56f339c754cc566f771ca9ffb90b69289`. The user authorized first GitHub publication on 2026-11-02 and the Model 2C commit, push and release delivery on 2026-11-04. Target: `Zer0one/Model2EmuEx-libretro`; this does not authorize later unrelated publication. Version [0.5.0](https://github.com/Zer0one/Model2EmuEx-libretro/releases/tag/v0.5.0) is published from `562d6f8`; all five platform, standalone, source and public-package verification gates pass. The user authorized this delivery on 2026-11-15.

**Legend:** 🟢 Completed · 🟡 Partial · ⚪ Not Started · 🔵 Deferred.

Rows are grouped by status. Stable activity IDs are retained for traceability. Completed source integration does not imply gameplay, physical-device, other-platform or publication acceptance. Evidence belongs in [Validation](VALIDATION.md); current option registration is in [Implemented Options](CORE_OPTIONS_IMPLEMENTED_REVIEW.md).

## Implementation Status

| Status | Activity | Remaining Work |
| --- | --- | --- |
| 🟢 | M01 — Independent Repository | Baseline history and upstream remote retained; pristine sibling checkout untouched. Independent repository and releases through v0.5.0 are published. |
| 🟢 | M02 — Native macOS Build And Frontend Boundary | Native arm64 core and standalone/headless targets build. Neutral loader, raw-drive and source-gain interfaces are documented; no SDL runtime dependency. Other platforms are tracked in M16. |
| 🟢 | M03 — Libretro Lifecycle And SRAM | Frontend GL ownership, callbacks, 64 KiB backup plus EEPROM, reset and reload integration delivered. Controlled GL context replacement is verified; broader physical-device verification is tracked in M14. |
| 🟢 | M04 — Pristine Comparison Baseline | Historical VF2/Sega Rally 900-frame baseline established. Historical Native-timing VF2 RAM/PCM were pristine-exact after integration; the later SCSP timing correction intentionally changes active audio. This is not all-game accuracy acceptance. |
| 🟢 | M05 — Local RetroArch Delivery | User-authorized local copy passes a bounded VF2 3D run at 60 Hz; installed/source hashes match. Repeat targeted frontend checks when subsequent changes warrant them. |
| 🟢 | M06 — Scripted VF2 Paid Match | Scripted coin/Start/Punch reached a paid match in the ABI frontend. Physical input and sustained frontend gameplay remain in M14. |
| 🟢 | M07 — Native Texture Filtering | Nearest/Bilinear/Trilinear selectors, runtime changes and shader fallback verified. Retain native values rather than advertising absent anisotropic filtering. |
| 🟢 | M09 — Applicable Native Selectors | Delivered under the decisions in [Native Options](NATIVE_OPTIONS.md). Window/scaling stays frontend-owned; separate keyboard/cooperative controls are excluded. |
| 🟢 | M19 — ROM CRC Verification | Actual stored/deflated/loose payload verification, Enabled default, Disabled bypass and strict size/decompression checks tested. Original standalone API retains metadata-only CRC policy. |
| 🟢 | M20 — Timing / FPS Overlay | SM2 panel/options, 61-frame measurements, font/4x/context/reset/skip tests, exact RAM/PCM comparisons and real RetroArch checks delivered. CPU/GPU interpretation and pipeline estimates are documented in TIMING_OVERLAY.md. |
| 🟢 | M12 — Save States | Complete native machine/sound/geometry serialization, validated 12 MiB container, pointer rebinding, rollback and GPU/audio/rumble recovery delivered. VF2/Daytona exact continuations, fresh-process loads, NVRAM authority and real RetroArch frame/pixel checks pass. Broader device/platform qualification remains in M14/M16. |
| 🟢 | M13 — External Linked Cabinets | Native seam and SM2 Netpacket delivered; two local Daytona instances reach a shared race, Sega Rally links recover after Restart. All-set local loopback matches SM2; native activation/roles remain game-owned and offline Save States retain prior-header read support. M14 verified a live two-cabinet menu edit and a three-cabinet Sega Rally ring on macOS. Wider platform and gameplay coverage remains in M14/M16. See EXTERNAL_LINKED_CABINETS.md. |
| 🟢 | M21 — Auto Network Role Settings | Delivered with M13 as its required F14 dependency: 14 destination pairs, SM2 mappings/Disabled defaults, independent authority, hidden-field synchronization/handover and one effective-change reset. APIs 2/1/0 and working-family/clone checks pass; future-board gameplay and broader frontend/device qualification remain M14/M16. |
| 🟢 | M23 — NVRAM Source Review And Evidence Index | Current SM2 source/import and actual registration reconciled: 340 fields/56 catalogs, 28 destination routes/19 applicable catalogs, approved template policy and existing evidence indexed. No workbook duplication or acquisition. Initial-template error-reporting omission corrected immediately following SM2; injected failures and normal/disabled/no-template cases pass. Destination persistence coverage remains M11. See NVRAM_SOURCE_REVIEW.md. |
| 🟢 | M24 — Cabinet Audio And Applicable Extensions | Manx TT Twin/Deluxe/selected-set policy, full serial return, additional native M1 board, AMS and guarded Save States integrated following SM2. ROM-free, actual-core policy, OpenGL continuation and real RetroArch checks pass. No other destination set declares a new applicable extra sound board; no prototype controls added. Listening/device qualification remains M14. See MANX_TT_CABINET_AUDIO.md. |
| 🟢 | M25 — Libretro Adapter Error Handling And Recovery | Four documented adapter bugs corrected: pending NVRAM retry/coalescing, error severity/fatal cleanup, GL context abandonment and queued network corrections. ABI, GL replacement, state, network and installed RetroArch checks pass. Raw standalone-compatible SRAM and Model2EmuEx emulation are preserved; physical motor qualification remains M14. See FRONTEND_CONTRACT_REVIEW.md. |
| 🟢 | M10 — Shared Audio Controls And A/V Timing | Existing 60 Hz/Native cadence and delivery checks retained; seven main/auxiliary native source paths pass 98 selector/fallback comparisons and six mixed-source isolation checks through actual adapter readers. Auto/100 preserve native mix, mute preserves synthesis, live resume/reset retain gain semantics. No core change needed. Listening/device and wider sound accuracy remain M14; added SCSP filtering stays excluded. |
| 🟢 | M11 — NVRAM Engine, Templates And Adapter Persistence | Existing SM2 source/registration matched; 526 adapter value cases on 25 sets/18 catalogs pass, preserving checksums and extra RAM. Two raw-save RetroArch sessions verify template precedence and reload; ABI verifies override authority. Turbo no-template policy and prototype metadata-only scope retained. Per-title native Service Menu/gameplay qualification remains M14. See NVRAM_SOURCE_REVIEW.md. |
| 🟢 | M18 — Crosshair Presentation | Unchanged SM2 geometry/artwork/activity module and destination GL overlay integrated. Actual RetroArch Virtua Cop checks cover P1/P2 visibility/movement, live styles, Auto fallback, distinct PNGs, independent timeout, restored aim positions/current style authority and native-menu Restart retaining artwork. No core change needed. Physical aiming and broader qualification remain M14; see VALIDATION.md for the uncompleted supplementary exact-frame PNG probe. |
| 🟢 | M27 — Native Model 2B SHARC Reconstruction | **100% of known recovery targets (208/208)**. 2,015,209 O0/O2 helper cases and 126,892 integration cases. Opt-in native and Libretro bindings pass; Fighting Vipers reaches scripted combat in the ABI/GL harness and 3D attract in RetroArch. Complete SHARC snapshots pass same/fresh-process continuation and exact restoration in RetroArch; VF2 Save State regressions pass. Catalogue definitions cover 35/35 pinned MAME Model 2B sets. The latest qualification reaches 3D attract in Fighting Vipers Revisions A and B and Dynamite Baseball, and the dedicated Relay screen in Virtual-On Relay. Power Sled now passes SHARC bootstrap in all three variants. Main and Relay establish one-node loopback and render 3D attract, and Slave reaches its native network wait screen, also observed in SM2. Main reaches a race with scripted inputs. Three real RetroArch instances render 3D in one Main–Relay–Slave ring with native IDs 1/3/2. Power Sled Main renders on Batocera x86-64. Windows x86-64 research build passes ABI and Fighting Vipers renders 3D attract in RetroArch on Windows 11 ARM. Scene pairs against ElSemi 1.1a include a same-region fight with the same displayed timer. Runtime probes record x87 53-bit round-to-nearest in both original geometry helpers. A binary64 diagnostic matches the x87 oracle in 2,048/2,048 finite cases on both architectures. The binary64 candidate also matches 64/64 original Fighting Vipers transforms on captured live operands. The 53-bit transforms are integrated for Model 2B in the research build. Live/finite arithmetic comparisons, Fighting Vipers clipping and macOS attract, direct/pipeline parity, and VF2 regression pass. Indy 500 and Rail Chase 2 spot checks pass macOS 3D attract, three clipping samples per title, and 3,600-frame direct/pipeline checks. Windows lossless Grace scene comparison passes close visual alignment against ElSemi and yields a byte-identical before/after core PNG at frame 1,800. Daytona and Virtua Cop pass 1,800-frame Model 2 before/after runtime comparisons, and Daytona renders in macOS RetroArch. Fighting Vipers passes 6,000 scripted frames and exact same/fresh-process Save State continuation in the macOS ABI/GL harness. Dead or Alive Rev. C and Virtual-On Twin Export pass exact RetroArch Save State restoration. Linux x86-64 build, ABI and ROM-free machine checks pass. The opt-in build renders Indy 500 in RetroArch on Batocera x86-64 and exits cleanly after 2,400 frames. Raw D3D9/OpenGL geometry and framebuffer dumps are retained. Replaying the exact ElSemi display list gives a core mesh neighbor within one pixel for all 3,381 sampled interior D3D9 vertex occurrences. Replaying the seven captured ElSemi video RAM banks leaves the OpenGL result byte-identical to the display-list-only replay. Renderer comparison accepted at native framebuffer resolution before presentation. Distribution CI and publication are tracked under M16. Broader gameplay, peripherals and platform runtime coverage remain under M14/M16. FP evidence includes independent x87 sequences under Rosetta, with documented Unicorn limitations. |
| 🟢 | M28 — Native Model 2C Reconstruction | **286/286 initial candidate addresses (100%)**, plus 18 helpers. Native CPU/driver, i960/FIFO bindings, complete snapshots and applicable per-game hooks are integrated behind `TGPX4=1`. Original-code comparisons cover the CPU/driver groups, all 22 FP bodies on physical AMD, motion handshake, ROM transform, Top Skater controls, protection and projection-center selection. All 13 native M2C records are MAME-aligned (70 total sets); all destination input bindings and 13 M2C NVRAM routes / 236 value cases pass. Nine title families have bounded rendered evidence; Dynamite Cop reaches scripted play and Continue after 6,000 frames with exact same/fresh-process continuation. Over Rev, Ski Super G, Top Skater and Dynamite Cop pass actual RetroArch state restoration. Linux x86-64 build/ABI/machine/geometry checks and isolated native Batocera samples pass; the Windows x86-64 build/ABI and RetroArch introduction pass in the Windows ARM VM. Native renderer-configuration applicability is reviewed with the approved upstream renderer retained. The subsequent same-list Top Skater comparison against instrumented ElSemi passes: all 2,753 sampled interior vertex occurrences match within 1/16 pixel before D3D/OpenGL, without position adjustment; this is spatial correspondence, not topology/attribute/pixel identity. Known recovery/integration work is complete; this is not all-path or physical-device acceptance. Unrecovered native-memory accesses fail explicitly. Broader qualification remains M14. Explicit CI enablement and machine/geometry gates pass on all five distribution platforms; v0.3.0 is published under M16. The shared Sonic correction is completed separately in M29. See MODEL2C_ANALYSIS.md and VALIDATION.md. |
| 🟢 | M29 — Shared Sonic The Fighters NVRAM Patch Conflict | Native conditional menu callbacks retained; 1,536 transition cases and the complete common/source suite pass. SEGA manual confirms separate single-player/versus vitality. Forty-eight native gameplay-fragment cases distinguish independent selector lookups from the shared Service Menu word. Actual RetroArch commits Hardest/Hard through Service, then a fresh load with overrides enabled restores Hard/Normal; disabled-override persistence is separately verified. No further core change was required. Quick Menu soft reset also restores Hard/Normal in the same RetroArch process. Wider gameplay remains M14. See NVRAM_SOURCE_REVIEW.md and VALIDATION.md. |
| 🟢 | M31 — Selected Original Renderer Options | All five selected controls are implemented. Windows D3D9 sampling, synthetic GL shader and geometry probes, VF2 continuation and earlier tile/FSAA RetroArch tests are recorded in VALIDATION.md. |
| 🟢 | M32 — Original Lua And Script Options | Embedded Lua 5.1.4, script options and reload, sequential callbacks, fonts, PNG overlays and the session-owned Load State contract are integrated. Daytona passed in the installed macOS RetroArch core. |
| 🟢 | M08 — Shared Input Profiles And Native Wiring | SM2 profiles and all 70 destination bindings integrated. Both architectures pass profile lifecycle and input suites. Native Input Tests cover Sega Rally, VF2, Fighting Vipers and Last Bronx; all three Fighting parents match the frontend action labels on both ports, with adapter regressions for all ten revisions. VF2 live Normal-profile editing passes. Broader gameplay and physical controllers are tracked in M14. |
| 🟢 | M15 — MAME ROM Set Alignment | Exact 88-set target, all MAME parents and ROM identities checked; core display strings and standalone preserved. M33 records native execution and bounded startup qualification. |
| 🟢 | M33 — Missing Catalog Sets: Execution And Startup | All 20 added sets execute and pass bounded rendered startup; native protection/installers, Air Walkers four-player I/O, 88 profiles, NVRAM and selected state continuations are qualified. hotdp remains on its native warning screen, also reproduced in SM2; playable prototype status is not claimed. Wider gameplay/devices remain M14. See the scope and results below. |
| 🟡 | M17 — Gamepad Rumble | Raw native observation, SM2 decoder and Framework mute/unmute/reset/unload policy pass callback tests. Physical motor response and per-game active-play qualification remain. |
| 🟡 | M26 — Upstream Reconciliation And Source Provenance | Static review completed: 41 import hashes verify, Netpacket donor/adapted identity corrected, missing referenced BSD text retained, component credits recorded. Original port contributions use GPL-3.0-or-later; recovered native-code terms remain unspecified and no overall license is inferred. Future authorized upstream integrations retain semantic review. See LIBRETRO_DESIGN.md. |
| 🟡 | M16 — Cross-Platform Qualification | Release 0.5.0 passes build, architecture, ABI, dependency, exact-source/package, native machine/geometry and protection/Air I/O/88-profile/NVRAM checks on Linux x86_64/ARM64, macOS arm64/x86_64 and Windows x86_64, on main and tag. Standalone Linux GL/GLES, Windows and Android builds also pass. All seven public assets are verified. Local universal macOS qualification is retained; wider platform runtime and native Intel hardware checks remain explicitly outside these CI claims. |
| 🟡 | M14 — Runtime And Physical Qualification | Current universal core passes 7,200-frame scripted VF2 play with exact same/fresh-process continuation and Fighting Vipers Save State restoration/resume. Fresh RetroArch launches preserve native Service Menu edits in Fighting Vipers (Advertise Sound, backup RAM) and Dead or Alive (Demo Sound, mirrored EEPROM). The SM2 control-route review covers 70 sets. Virtua Cop publication and Water Ski pitch polarity are corrected and qualified against ElSemi. Super GT 24h pedal polarity also matches the live SM2 operator setting. All recorded protocol differences are classified; board-specific 32-bit I/O reads and effective-scene gun aiming are corrected and qualified. The bounded control-route group is complete. Sega Rally passes a live topology edit and a three-cabinet link. Wider gameplay and physical-device checks remain. |
| 🔵 | M30 — Original Emulator Fidelity Inventory | Whole-source evidence index, inherited M2/2A qualification and i960 NaN correction are complete; see RE_INVENTORY.md and M2A_RE_QUALIFICATION.md. Reconstructed SCSP DSP, native mixer boundaries, explicit fault handling, backend selector and local fresh-process/frontend state/PCM continuation are qualified; original Save State DSP omissions are documented. A68K context, bus/maps, reset, exceptions/IRQ and successive instruction groups are reconstructed and compared with the original at O0/O2/UBSan. Current coverage is reported below and in AUDIO_RE_ANALYSIS.md / VALIDATION.md, without equating dispatch coverage to CPU completion. The A68K-enabled build integrates the scanline scheduler, warm reset, sound CPU selector and fresh-session Save States. The user accepted both Sega Rally clips and the Daytona USA excerpt. All eight [audio adoption groups](#overall-elsemi-audio-adoption--2026-11-14) are closed. Retain the matching PCM traces as integration regressions. Preserve original behavior; corrections require separate evidence and a decision. The Audio Subsystem selector defaults to the ElSemi reconstruction. The Model2EmuEx profile selects the standalone board. The current reconstructed PCM path is installed locally. The two remaining original-memory and reachability questions are optional follow-up research, deferred by user decision on 2026-11-15. Reopen only on new evidence reaching those paths; they do not block delivery of the completed scope. See Current Functional Group And Stop Point. |

## M33 — Missing Catalog Sets: Execution Scope

User authorization — 2026-11-15: extend execution, rather than register the
missing sets as non-executable metadata. Keep original ElSemi machine semantics,
existing core descriptions, MAME identity/parents and the two Daytona exclusions.
The user authorized the 0.5.0 commit, push and release on 2026-11-15, conditional on passing all five platform gates.

| Block | Exact Scope | Closure Evidence |
| --- | --- | --- |
| Native Model 2A Records | `doaa`, `pltkidsa`, `dyndeka2`, `dynamcop`, `zerogunaj`, `zeroguna`. Recover initialized records, ROM operations, inputs and hook installers from 1.1a. | Source/ROM identity, original installer/protection comparisons, actual board execution, frontend binding and complete state continuation. |
| Existing-Family Revisions | `doaab`, `doaae`, `hotd`, `hotdp`, `manxttdx`, `motoraiddx`, `srallycc`, `srallycdx`, `srallycdxa`, `stcco`, `topskatruo`. | Reviewed ROM layouts and cabinet differences, explicit donor provenance, no borrowed revision-specific hooks, targeted execution of each variant and family state regressions. |
| Additional Titles | `airwlkrs`, `hpyagu98`, `rascot2`. No initialized 1.1a record identified in the reviewed game-record span. | Identify required native board paths and additional hardware; implement only evidenced behavior, then qualify rendered startup or document the concrete remaining blocker. Metadata alone does not close execution. |
| Catalog And Frontend Closure | Exact 88-set target from current 90-set XML minus `daytonat`/`daytonata`; preserve existing display strings and standalone. | Compiled set/parent/ROM checks, all-profile binding, NVRAM/cabinet applicability, relevant state tests and bounded frontend evidence. Physical devices and exhaustive gameplay remain separate. |

Completed checkpoint — 2026-11-15: 88/88 catalog definitions and 20/20
bounded startup witnesses; this is 100% of M33's defined integration/startup
scope, not a gameplay or whole-emulator reverse completion percentage.
The six recovered 2A records, four native installers, bounded protection
aliases and Air Walkers I/O are integrated. All 88 input bindings and NVRAM
routes are considered. Nine state witnesses and four fresh-process tests pass.
Universal macOS and both architecture fixture suites pass. Actual RetroArch
renders Air Walkers and hotdp's warning. The latter also remains on the same
warning in current SM2 after 2,700 frames; wider prototype gameplay is not
qualified. Royal Ascot II's native Shot 1 standalone entry reaches the title.
Tools, images and compact results are retained in `port/build-catalog-reconcile`.
No source from the standalone checkout, ROMs or production saves was changed.
The user authorized the 0.5.0 commit, push and release on 2026-11-15, conditional on passing all five platform gates.

## NVRAM Campaign Shared-Field Follow-Up

User scope clarification — 2026-11-15: corrections apply only to options already
implemented in NVRAM Settings. Do not add excluded settings as a consequence of
this audit. Excluded-setting sample comparisons remain documentary evidence.
The name-filter handling rule below is subject to this implementation boundary.

User decision — 2026-11-15: where settings matching the common-prefix / varying-
suffix name filter write shared bits, use the already approved Sonic Energy
handling. Only shared-bit pairs outside that filter require individual review.
Disjoint bits and different memory banks are excluded. No new acquisitions.

The initial source/YAML-only empty list was insufficient for excluded settings
and is superseded by the completed existing-sample comparison. The read-only
audit identifies 98 excluded menu rows; retained value series permit comparison
of 80, reading 1,309 raw files. Six of those 80 have identical persistent
payloads across the collected values; no transient-write conclusion follows.
The other 18 have no comparable dedicated series: three Power Sled Country rows
have only one documented label, Motor Raid DX Engine Volume is informational,
and 14 other rows have no retained per-value series at the indexed locations.
No parent series is silently counted as a dedicated clone acquisition.

The raw comparison finds 351 pairs with shared varying bits after known checksum
and documented update-counter exclusion. Twenty-four meet the name filter;
327 outside-filter pairs are grouped into **19 game entries** in the requested
review list. Their common locations do not coincide with declared operator-value
addresses: save-header/runtime/unassigned changes remain observations for review,
not proven option conflicts or proposed fixes. Each shared bit has two real
value-file witnesses on both sides; full masks and hashes are retained.

This group has completed comparison of the available collected samples and
produced the requested list. Purpose/causal classification of the 19 entries is
a subsequent review, not claimed complete or implemented. No further acquisition
is scheduled. Tools: `scripts/audit-nvram-excluded-samples.py` and
`scripts/audit-nvram-shared-fields.py`. Results and review list:
`port/build-nvram-shared-fields/completed/review.md`, `report.json`, `result.json`.
See NVRAM_SOURCE_REVIEW.md. No behavior change, commit, push or release.

## Current Functional Group And Stop Point

### M14 Runtime Test Scope

The control-route group closes when every recorded discrepancy has a documented
classification and each applied correction passes its targeted regression.

| Block | Scope And Acceptance |
| --- | --- |
| Catalog Route Comparison | Completed for all 70 sets. Follow profiles through board readers and record the actual guest addresses. |
| Virtua Cop | Completed. The original 004cb9b0 hook confirms the omitted byte-lane publication. Both revisions pass 288 original comparisons, 288 release cases and 19,102 actual guest reads. Arm64/x86_64 input checks and the 900-frame RetroArch run pass. |
| Sega Water Ski | Completed. Native kind-0 Pitch switches are momentary active-high. Destination polarity conversion passes 128 original-decoder cases, 750 actual guest reads, both architecture input suites and a 900-frame RetroArch launch. |
| Super GT 24h | Completed. The adapter follows SM2 pedal conversion for the live I/O Type. 3,696 reference cases, 4,286 actual guest ADC reads across A/B/C/A and both architecture suites pass. Original host limits are documented separately. The universal core renders 3D attract in RetroArch and is installed locally. |
| Remaining Recorded Protocol Differences | Serial selectors, drive/motion replies, motorcycle P2 Start and ADC sequencing are classified against native behavior. The board-specific upper bytes of 32-bit I/O reads are corrected and pass 22,368 original comparisons plus both architecture I/O suites. Expanded-view aim follows the last presented scene under the approved Lua policy. Both architecture view tests, 1,944 profile cases, exact state continuations and a 900-frame RetroArch run pass. This bounded control-route group is complete. See the protocol classification in VALIDATION.md. |

The SM2 input-route review covers all 70 catalog bindings and 22 profile
labels. Two reference suites, 2,240 digital input cases, 4,284 analog
readbacks and targeted guest-bus probes are complete. The original Model 2
firmware comparison locates the controls in Daytona USA, Desert Tank and
Virtua Cop. The Virtua Cop gun/trigger publication omission is corrected and qualified
against the original hook. Water Ski pitch polarity is also corrected
against the native input decoder. Super GT 24h pedal polarity now matches
the SM2 frontend contract for the live operator setting. The
serial gun and drive/motion differences are classified against native behavior.
The bounded control-route review and its approved fixes are complete.
Physical devices and wider gameplay retain the M14 scope below. [Control routes and evidence](VALIDATION.md#m14-control-routes-against-sm2--2026-11-15)

Sega Rally recovered its two-cabinet link after a live host menu edit and
formed a separate three-cabinet ring on macOS. [Observed topology changes](VALIDATION.md#m14-sega-rally-live-cabinet-count--2026-11-15)

The bounded `schamp` warm Restart check passed on November 14. With overrides
enabled, a confirmed Quick Menu soft reset restored Hard/Normal after a native
Hardest/Hard edit. Game Assignments showed the restored values in the same
process. The full raw save matched the fresh-launch control (selectors 2/1,
shared word 200). [Warm Restart evidence](VALIDATION.md#m14-sonic-championship-warm-restart--2026-11-14)

The VF2 gameplay, Fighting Vipers backup RAM and Dead or Alive EEPROM samples
already have recorded results. Wider per-title Service Menu and sustained
gameplay coverage still lack an agreed title list, duration and acceptance
criteria. A further driving session has not been scheduled. Remote-host network play, physical controllers, lightguns and rumble retain their separate evidence requirements.

GPU context recovery is closed by user decision on 2026-11-15 on the basis
of the successful controlled GL context replacement test. No additional
manual sleep/wake or window-mode campaign is required. This does not claim
that every macOS or RetroArch event was exercised.

Current reconciliation — 2026-11-14: all eight ElSemi audio adoption groups
are closed. By user decision on 2026-11-15, the two remaining M30
original-memory and reachability questions below are optional follow-up
research and Deferred. They do not block delivery of the completed scope.
Reopen only on new evidence reaching those paths. Historical dated research
sections retain their original checkpoint status.

| Optional M30 Follow-Up | Existing Evidence And Reopening Condition |
| --- | --- |
| Dynamite Cop protection selectors beyond 5 | Both direct callers in the USA Model 2C main program pass selector zero and use fixed responses. Their nine reads per call account for both runtime traces. Direct-caller review is complete. Reopen guest investigation on evidence of an indirect or additional code path. Ownership of adjacent original data remains unknown. |
| Model 2C TGPx4 shared-memory window | In both 7,200-frame Ski Super G traces the same 36 decoded program indices issued all 7,382,896 ROM reads, within the coprocessor ROM bounds. Neither trace entered the shared window. Revisit on a guest trace entering that window. Original-process allocation ownership remains open. |

The second-SCSP catalog investigation is closed. All 55 original SCSP
records use one of five setup configurations. The original installer binds
only chip 0 in all five, including the two optional DSB paths. The paired
mixer remains qualified on synthetic vectors. Reopen on a title-specific
trace showing activation after setup.
[Original catalog and installer evidence](RE_INVENTORY.md#second-scsp-activation-in-the-original-catalog)

Geometry sorting, clipping, attributes and rasterization retain the limits
recorded in RE_INVENTORY.md. The accepted renderer comparison stays closed.
These limits do not reopen the completed audio adoption groups. Runtime,
physical-device and platform acceptance remain in M14/M16/M17.

Latest completed A68K integration groups — 2026-11-12: source-guided bus
observations and all remaining instruction/control connections are wired in
the research executor. The observed switch covers **1,667/1,667 targets** and
**65,536/65,536 encodings**. Targeted O0/O2/UBSan native comparisons pass; see
VALIDATION.md for group counts, guards, snapshots and limitations.

This is **100% of the internal target inventory**, not overall CPU completion
or proof of every input/path. Historical-source instruction semantics are
reused; tests target native differences, portable adaptations and new
connections. No whole arithmetic matrix was rerun in this increment.

### SCSP Sound Board Reconstruction

**Scope.** Reproduce the Model 2 Emulator 1.1a sound-board path from the i960
command/status ports through the A68K, SCSP voices and DSP to the signed
stereo output delivered to the host. Include cold start, warm reset, the
observable board state, both original mixer routes, and the single- and
dual-chip branches in those routines. Follow direct calls, indirect targets
and observable data exchanges inside this boundary even when no sampled game
exercises them. The pinned reference and existing evidence index are in
[RE_INVENTORY.md](RE_INVENTORY.md).

**Boundaries.** The i960 interface ends at the board ports. Cabinet wiring
ends at the SCSP board's inputs and outputs, including MIDI. In the wider
audio RE inventory, track the Model 1-style sound board (68000, MultiPCM and
FM) and the DSB MPEG board separately. For each, identify its native routines,
shared code, command interface and contribution to the final mix. SCSP closure
does not qualify either board. The host boundary is delivery of PCM to
Libretro. Include any original buffering, timing or mixing that affects the
samples or emulated machine before delivery. Playback on the physical device
belongs to the frontend. Auxiliary cabinet firmware and geometry have their
own subsystem boundaries. Preserve frontend gain and the port's Save State contract.
Original quirks and approved host-safety policies apply throughout. A proposed
correction or a newly discovered difference requiring a policy decision goes
to the user before implementation.

| Order | Code To Reconstruct Or Reconcile | Deliverable And Closure Condition |
| --- | --- | --- |
| 1 | **Inventory and ownership.** Start at board initialization, scanline service, both directions of the CPU bus, reset, state callbacks and mixer dispatch at `004af7f0`. Follow data-driven tables, calls through registers and generated DSP entry points. | In the existing RE evidence index, record each routine or source-equivalent family, its callers, targets, observable state, portable counterpart and evidence. Resolve unknown targets or identify an explicit external boundary. Newly found internal targets belong to their parent block. |
| 2 | **A68K and board exchanges.** Reconcile the historical A68K source with ElSemi's dispatch and callback ABI. Cover flags carried between instructions, fetch, exceptions, command and reply queues, scanline scheduling, timer/IRQ acknowledgement, RAM, and byte/word/long register mappings including aliases and crossing writes. | Reuse evidence for source-identical handlers. Exercise ElSemi differences and producers/consumers with synthetic instruction streams, including return values, side effects, timing and approved faults. Account for each guarded bus range. |
| 3 | **SCSP voice engine.** Inventory the 32 ordinary voice handlers selected at `00572980` and the interleaved voice routine at `004548c0`. Follow source selection, sample width, interpolation, all loop modes, envelope, pitch/amplitude LFO, modulation and voice termination. | Map each handler to its implementation or proven shared body. Compare per-voice state, sample addresses and output with ROM-free vectors for selector combinations, transitions and edge cases. |
| 4 | **Mixer, ring and DSP.** Reconstruct selection and block order at `004af7f0`, `004aa950` and `004aead0`. Follow ring cursor/master fields, one/two-chip branches, first/last sample, DSP Start, program decode, RAM access, effect returns, clipping and gain order. | Compare ring writes, DSP inputs, effect returns and stereo output for both routes. Account for each DSP selector and both valid and escaped addresses under the approved policy. Preserve the original timing when a voice stops within a block. |
| 5 | **Lifecycle and port integration.** Carry the reconstructed state through board initialization, reset and a fresh-session Libretro restore. Select the complete audio subsystem at content load and bind its board state and callbacks together. | Compare state transitions with the original where its callbacks apply. Verify that pending commands, interrupts, RAM bindings, voice history and DSP state continue under the port's Save State conventions. Check frontend gain after signed saturation. |
| 6 | **End-to-end qualification.** Replay the existing command traces and PCM witnesses, including the differing ordinary and interleaved cases, after qualifying their code paths. | Record the first internal divergence for any failing replay and return it to the owning block. Use the existing listening and frontend fixtures for final qualification. |

**Definition of done.** Every internal target in the inventory has an
accounted-for implementation and evidence for its observable branches and
exchanges, or an explicitly approved exception with its consequence.
Unexplained PCM differences and unresolved indirect targets keep the scope
open. The default **Model2Emu (ElSemi)** selection is a deployment decision.

**Acceptance for the complete ElSemi audio subsystem.** The pinned Model 2
Emulator 1.1a binary defines observable behavior for SCSP, the Model 1-style
board and the optional digital board, including the links between them.
An upstream implementation can serve as the final implementation of a block
only when its behavior agrees with the original throughout that block's
defined scope. Record the corresponding native routine, the upstream code
retained, and the source or differential evidence. A matching game capture
qualifies its exercised interval. Untested branches, substituted components
and outstanding discrepancies remain open. Identify approved safety and
Libretro lifecycle adaptations individually.

#### Audio Subsystem Selection

The implemented **Audio Subsystem (Restart Required)** selector has two values, **Model2Emu (ElSemi)** (default) and **Model2EmuEx**. It selects the primary Model 1-style or SCSP board, including the optional ElSemi digital music board, at content load. Bind each board's render routine during setup. Keep its CPU scheduling and synthesis together. Shared frontend gain and PCM publication happen at the boundary. CPU bus adapters and lifecycle dispatch in `m2snd.c` still contain profile-specific branches. Keep further reconstruction in the owning implementation. The first choice uses the qualified ElSemi audio reconstruction. The second restores the standalone CPU, memory map, chip, DSP, schedule and mix. Model 1-style and DSB paths have separate inventories.

Both profiles passed same-process and fresh-process Save States and reject each other's states. For Sega Rally (SCSP) and Daytona USA (primary Model 1-style board), the standalone board and Model2EmuEx produced byte-identical PCM from the same command sequence. See [validation](VALIDATION.md#audio-subsystem-selection).

#### Overall ElSemi Audio Adoption — 2026-11-14

**All eight functional groups closed (100%).** Count each of the six SCSP roadmap groups below, the primary Model 1-style board, and the optional digital music board once. A group earns one point when its defined behavior is implemented and qualified or its exception approved. The percentage measures closed functional groups, independently of the number of native instructions or game captures.

The closed groups cover inventory and ownership, A68K and board exchanges, SCSP voices, mixer/ring/DSP, lifecycle and port integration, the primary Model 1-style board, the optional digital music board, and end-to-end qualification.

The optional two-chip SCSP path is qualified with explicit synthetic inputs. None of the reviewed native game hooks selects it. The Manx TT auxiliary cabinet has its own accepted scope. Account usage and this functional completion figure are reported separately at each tranche boundary. Earlier tranche boundaries lack a recorded eight-group count.

| Weekly Usage | Overall Audio Groups Closed | Evidence At The Checkpoint |
| --- | --- | --- |
| 60% | Not recorded | Ring register behavior and seven primary SCSP captures matched. The chip clock remained open. |
| 65% | Not recorded | Two SCSP + DSB captures matched at the same cadence. Four FM samples still differed in the historical-source comparison. |
| 70% | Not recorded | The primary Model 1 board passed warm reset during music. The A68K bus comparison covered 986 writes. |
| 71% | 6/8 (75%) | First explicit count over the entire audio scope. Fixed-clock diagnostic captures matched the Windows routines for 2,485,200 stereo frames. |
| 75% (cap) | 6/8 (75%) | Both DSB variants retained playback and the partial command across native reset and portable fresh load. Fixed-clock frontend transport qualified at both timings. The production clock choice, DSB stall policy and final listening review remain open. |
| 75% (latest weekly reading, 80% cap) | 7/8 (87.5%) | Both approved policies integrated. The four raw captures match 2,903,200 original stereo frames; transport, cabinet and installed RetroArch checks passed. Daytona listening was pending at this checkpoint. |
| User listening review | 8/8 (100%) | The user reported regular audio in the six-second Daytona USA excerpt from the installed core. |

#### SCSP Progress Baseline — 2026-11-14

The nine reviewed SCSP root families now have a routine-by-routine map. The table tracks code ownership and remaining validation. Game replays qualify only the board contributions and clock policy actually captured.

| Group | Status | Measured Coverage | Remaining Work |
| --- | --- | --- | --- |
| 1. Inventory | Mapped for the reviewed roots | 94/94 native entries have a portable counterpart or external boundary. All 27 indirect sites are classified. The scan covers 67 descriptors and 21 distinct setup hooks. | Reopen the inventory if another internal target is found. Both mixer branches are included regardless of guest use. |
| 2. A68K and board exchanges | Integrated, with differential checks | 1,667 CPU targets classified. Native and portable callbacks agree on 4,528 reads, 4,370 global write/IRQ cases and 768 ring stores. The i960 command ports have 72 width, offset, alias and board-type cases. All 976 direct-store instruction targets and the exception/IRQ entry paths match the original caller stack at 986 observed writes. | The optional DSB receives the same command byte in the i960 callback. |
| 3. Voice engine | Integrated for both mixers | 256 dispatch/source combinations, 448 PCM fetch cases, 5,120 envelope/LFO gain entries and 134 coupled-voice cases covering all modulation depths and ring indices. | Preserve these witnesses when changing block cadence. |
| 4. Mixer, ring and DSP | Single- and dual-chip routes qualified on vectors | Both mixer paths have block/cursor, active DSP sends/returns and coupled-voice tests. The two-chip path has 12 coupled-voice cases. | Two-chip coverage is synthetic. An activating title has not been identified. |
| 5. Lifecycle | Integrated, with fresh-process checks | Power-on key scans cover 32 voices. Eight title/cabinet fixtures resume exactly, including both Manx TT cabinets. The subsequent i960 latch build also passes House of the Dead cold and fresh restore. | Eight production configurations passed four same-process replays and exact fresh-process continuation with the approved clock. |
| 6. End-to-end qualification | Closed | Seven primary-board comparisons match across 8,591,892 stereo frames, including the isolated Manx TT Deluxe SCSP contribution. Native host queue tests cover both channels. Production uses the fixed original clock. The installed core passed the frontend check and the user accepted the Daytona USA listening excerpt. | None. |

The separate Model 1-style and DSB walks index 92 and 27 native entries respectively. All 39 Model 1-style and one DSB indirect sites encountered are classified. The three walks share code and contain 194 distinct entry addresses in total. This is a static inventory of the reviewed roots. Both DSB variants run from the original ROM descriptors in the ElSemi profile. Layer I/II decode and synthesis have native differential coverage. Active tracks in Sega Touring Car and Top Skater resume exactly in a fresh process. Both titles match the original combined stereo mix over 1,010 machine frames each at the adapter cadence and at the fixed Windows cadence. The fixed comparison executes the original mix and command callbacks with SCSP and DSB in the same machine. The approved decoder stall handling stops the content and reports the compressed stream offset. The Model 1-style board has native FIFO, bank and scanline observations, plus two portable MultiPCM chips and a YM2612 with chip-level PCM comparisons. The primary Model 1 board now has its own A68K bus, ten-dispatch scanline scheduler, incremental FM block rendering, reset and Save State. Three integrated machine traces agree with the original at matched cadence. A separate board comparison checks CPU context after every scanline and all RAM after every frame, including a warm reset during playback. See the [Model 1 results](VALIDATION.md#primary-model-1-audio-board). The common Manx TT auxiliary board remains the SM2 cabinet extension.

The production ElSemi boards synthesize 760 stereo frames per 58 Hz machine frame. The adapter converts their output for the frontend and preserves the separate Manx TT auxiliary cabinet clock. The Model2EmuEx profile retains the standalone cadence. The 40,748 valid digital track positions reviewed use ordinary stereo. A synthetic grouped joint-stereo vector exercises the approved error path. See [production clock and decoder results](VALIDATION.md#production-elsemi-audio-clock).

### Prior Implementation And Validation Evidence

Account usage is tracked separately from implementation coverage.

User approved original 1 MiB linear SCSP-board CPU RAM shared by both CPU
backends, then original ElSemi/A68K word-swapped storage. Musashi and SCSP
accessors are adapted; chip sample masking remains independent and unchanged.
Synthetic bus/archive/DMA/PCM checks and the MAME baseline comparison pass.
Full-core state verification passes: VF2 with both DSPs and Daytona Model 1.
The first native SCSP CPU-read group passes 21/21 cases and VF2 continuation.
The native 128-byte FIFO, ordinary global CPU reads/writes, timer and IRQ
control group now passes 999/999 original-code cases at O0/O2/UBSan. A real
Musashi interrupt-consumer fixture preserves 40 queued commands and exact
cold-state continuation. Final-core VF2 (original DSP) and Sega Rally (MAME
DSP) pass 900-frame GL/ABI Save State checks, including fresh processes.
The research read observer additionally passes 664 native EAX/EDX/flag
comparisons and 24 nonmutating alias guards at O0/O2/UBSan. It is not yet
connected to the active CPU. The next research binding now routes actual A68K
DATA/WRITE pages to the recovered SCSP observers: 664 reads, 1,760 global writes
and 576 acknowledgements match the original at O0/O2/UBSan, with 1,080 guarded
unsupported accesses. This is callback wiring, not complete sound CPU execution.
Remaining: slot/DSP/output-MIDI writes, raw-object aliases, allocation-token
provenance and full scheduler/lifecycle/state integration. The user approved native CPU DMA
register stores without transfers. Both CPU paths now preserve that behavior;
chip-internal DMA stays separate. Original-code, real-board bus and VF2/original
DSP plus Sega Rally/MAME DSP fresh-process state checks pass. Astra with high effort remains appropriate.
The CPU ring control at 0x100402 now passes all 512 base/length combinations.
Musashi and the research A68K bus deliver the seven-bit base. The original
DSP reaches the upper address range in a synthetic Musashi bus test.
The A68K bus now accepts 15 of the 16 words per voice, including key-on.
Both CPU paths use a latched sample base and bounded 1 MiB reads. The shared
ordinary 8-bit and 16-bit PCM interpolators use ElSemi history. All 24 signed sample
and history comparisons pass against the x86 routines. The current schema restores active
history across a fresh load. Sega Rally passes 900 frames and exact GL/ABI
continuation with the original DSP.

The shared PCM engine implements all four ElSemi loop modes. The 32 x86
dispatch entries agree with the portable core on 2,080 sample steps across
288 sequences. A one-sample forward loop at the end of RAM reports the real
second fetch at 0x100001. Cold PCM continuation passes in every mode on both
DSP backends, including a save while moving backward.

**Pitch calculation complete.** The Fighting Vipers startup probe on Windows
measured x87 control word 0x007f. All 1,024 table entries and all 16,384
octave/fine settings match the original on key-on and live writes.
The pitch group qualified the thirteenth slot register word. See VALIDATION.md for the Sega Rally run.

**Shared envelope.** The four phase updates, all 128 rate table entries
and 4,096 transitions match ElSemi. Live updates preserve volume and
phase, with original scratch on the A68K bus. Coverage is 15/16 slot
register words (93.75%) on the research bus. All 16 word handlers have
now been observed in the original, including the LFO control. SCP6 records native
eight-fractional-bit levels. Cold sample continuation passed on both DSPs.

The shared pitch LFO now uses the approved ElSemi saw for both CPUs.
All 256 phase steps match the native voice at maximum depth. The original noise table and all 3,584 pitch/amplitude phase gains are
also qualified and integrated. The research callback now handles pitch-only
LFO control and long stores whose second update replaces the LFO return.
Amplitude-enabled final updates still need the original caller stack flags.

**PCM mixer partially reconstructed.** The PCM path
applies amplitude modulation and envelope with SDIR on. Steady-state TL,
left/right gains and the signed DSP input match the x86 mixer fragment in
4,096 cases. The 8-bit direct-mode cutoff witness passes. Both native mixer routes have now been traced through ring writes and DSP entry
with four synthetic inputs each. They differ on interpolation, ring timing
and the final DSP send when a voice stops within a block. Both portable DSP
backends agree on the measured input, but the voice engine has yet to reproduce
the two native routes. See VALIDATION.md for the isolated cases. Sega Rally
passed the 900-frame GL/ABI continuation check on the final gain build.

**Sound-board exchange RE.** The original A68K/timer/IRQ order, mixer block
length calculation and live versus configured acknowledge callbacks are
traced. The two native mixers now have 24 active DSP send/return cases,
including the effect output to stereo. The 40-command guest IRQ program
exposes one extra empty read with the configured callback forced into
the live CPU. The port now uses the live autovector on Musashi and the
A68K research bus. Guest service of timers A/B/C is now traced through
RTE at 58 and 60 Hz. Clearing before reload causes a second acknowledge in
the same tick. See [Timer Service Across Interrupt Returns](VALIDATION.md#scsp-timer-service-across-a68k-interrupt-returns).
The production Musashi scheduler still differs. The research board now runs the
original scanline clock against the reconstructed A68K and SCSP. Cold CPU setup,
guest interrupt service, a warm reset with a pending MIDI command, ROM execution
and program write protection match the original on synthetic inputs at both rates.
See [A68K Board Startup And Scheduling](VALIDATION.md#a68k-board-startup-and-scheduling).
The five IRQ/lifecycle RE groups are qualified on the original: timer
service, MIDI/timer handoff, guest STOP, board reset and original state
load. Reset retains pending sound state. The original state load retains
live audio CPU and board state while restoring the lower 64 KiB of audio RAM.
See [reset and load evidence](VALIDATION.md#board-reset-and-original-state-load-with-pending-sound).
Windows confirmed the active IRQ pointer on 48 samples across Fighting
Vipers, Sega Rally and House of the Dead. Only House selected the interleaved
mixer in those samples. Ring-to-voice reads and native MIDI output enqueue
are now traced. Across 48 reads, the two original i960 sound ports returned
status or 0xff without consuming the SCSP output queue. Native MIDI/DSP
write returns are now traced through the following A68K instruction.
The ElSemi MIDI output producer is now shared by Musashi and the A68K
research bus, including its queue state. The Manx TT wire is independent.
CPU DSP writes now implement the original upper MADRS alias and the
MPRO/TEMP boundary. The research bus also completes ignored writes to 0x430–0x5ff and
0xc00–0xffff with the original EAX/flags (72 comparisons). It binds
ordinary DSP writes and Start, including the empty-program allocation address.
The research board uses stable 32-bit virtual addresses for RAM, both ROM
regions, the original write stack and the DSP code buffer. Recovered MOVE
stores carry their wrapper frame through DSP Start and amplitude LFO updates.
Sega Rally and Virtua Fighter 2 match across the first 12,600 sound scanlines,
including their first DSP Start. See [DSP Start And Virtual Write Frames](VALIDATION.md#dsp-start-and-virtual-write-frames).
A test command sent to each real sound program was consumed on the same
scanline as the original. Registers, both MIDI queues and sound RAM match
through 14,700 scanlines in Sega Rally and 63,000 in Virtua Fighter 2.
The ring window binds the 64 mixer cells, both audio RAM addresses and the
first 52 DSP coefficients. CPU reads also expose the first two voice register
banks and their latched sample offsets, cursors and pitch steps. The original
DSP now captures the selected audio RAM address at Start and preserves pending
changes across a fresh board restore. Voices resolve their base on each fetch.
Both can address either mapped audio allocation. The ring base page and length are live on the original DSP. The CPU-written
ring cursor can direct the next mixer write into adjacent fields. Its bounded
binding and the master flag remain open. See
[Sound RAM Address Captured At DSP Start](VALIDATION.md#sound-ram-address-captured-at-dsp-start)
and [Live PCM Voice RAM Selection](VALIDATION.md#live-pcm-voice-ram-selection).
At the preceding research checkpoint, adoption stood at 4/8. See [Native MIDI And DSP Write Returns](VALIDATION.md#native-midi-and-dsp-write-returns).

**Sega Rally race qualification.** RetroArch save/load and listening were
checked separately on the local A68K-enabled build.
The A68K-enabled core now runs the real i960 commands on each of the 210
machine slices. The original Sega Rally program and the core acknowledge all
5,908 interrupts at the same level and scanline in a 420-frame capture.
A fresh process restores the sound CPU and PCM exactly. The two sound CPU
choices reject each other's snapshots. See [Sega Rally Live A68K And PCM](VALIDATION.md#sega-rally-live-a68k-and-pcm).
The integrated build matches all 319,344 stereo frames over that interval
using the approved ElSemi output stage. Both CPU choices reached the same
Sega Rally race checkpoint in third gear at 128 km/h. RetroArch saved and
loaded each backend at machine frame 2650 and reproduced its reference
image at frame 2653. A longer original-binary replay covers 3,550 frames
from cold boot into the race. All 2,699,224 stereo frames match, including
the segment extracted after restoring the A68K checkpoint. The user listened
to both clips and reported that both sounded OK. Each spans three seconds
before the checkpoint and 15.5 seconds after restore. Both are available in the local
`port/build-a68k-board/live-srallyc/` evidence directory.

### Preceding Scratch Group

Latest A68K execution group — 2026-11-04: continuous original-dispatch
comparisons now qualify next-handler scratch for **339/1,667 targets (20.34%)**,
covering **13,417/65,536 encodings (20.47%)**. These include register arithmetic,
transfers/immediates/quick, bit/BCD/MUL, shifts/rotates and Scc memory writes.
**74,548 streams / 206,533 executed steps** pass at O0/O2/UBSan with identical
results, plus 144 write-wrapper comparisons and 17 separate guards. The full
single-handler O2 regression passes 3,424,140 comparisons with unchanged prior
result digests and 16 host-binding guards.

Single-handler dispatch coverage remains **65,536/65,536 entries and
1,667/1,667 native targets (100%)**. Sequence coverage is a separate measure,
not weighted CPU completion. Original streams run continuously without
per-instruction scratch reinjection. Write callbacks are synthetic observed
bindings; real board callbacks, remaining scratch targets, full execution,
scheduling, Save States and audio/frontend qualification remain open.

The historical Make68K/A68K source guides implementation and cross-checks;
the ElSemi executable remains authoritative. See `port/a68k/PROVENANCE.md`
for source-explained behavior, original caller EAX origins and native differences.
Accepted IRQ callbacks and host control/trap bits outside the qualified
arithmetic/IF/DF domain remain explicitly unrecovered.

The Windows filter audit passes 11 checks; the original Windows process confirms
unhandled c0000095 and termination for injected INT32_MIN/-1. Game reachability
remains unknown. The approved selector policy is Stop Content (Default) /
Original, without guest arithmetic correction. Its isolated host implementation
is qualified; actual frontend registration awaits A68K board integration.
A68K remains unlinked and Musashi operational. Completed A68K will be default
with MAME (Musashi) alternative. Installed core unchanged, no commit/push.

Results and reusable tools are retained; temporary compiled test libraries
are automatically removed. See AUDIO_RE_ANALYSIS.md and VALIDATION.md.

Latest Model 2B group — 2026-11-03: recovered 22 additional original game records and matched their main program to pinned MAME. That group brought the Libretro catalogue to 54 sets, including four donor-verified MAME revisions. The initial 26 Model 2B sets pass archive payload CRC checks. Dead or Alive Revision C and Virtual-On Twin Export pass strict load and 3D attract in isolated macOS RetroArch. Fighting Vipers and Over Rev pass bounded gameplay and Save State checks. Rail Chase 2 now passes the motion-board check in both revisions and reaches 3D attract; the parent also reaches scripted gameplay and passes exact Save State continuation. See MAME_ROMSET_ALIGNMENT.md for the final seven Model 2B entries and verification limits.

Model 2C (M28) is complete for the known reconstruction and integration scope:
286/286 initial addresses plus 18 additional helpers, native board/per-game
bindings, 13 MAME-aligned records, SM2 frontend preparation and complete states.
Representative macOS, native Batocera and Windows ARM-VM frontend checks pass;
Dynamite Cop also reaches scripted gameplay and exact state continuation.
The renderer applicability review preserves the approved upstream backend.
The additional Top Skater original/core same-list comparison passes spatial
correspondence for all 2,753 sampled interior vertex occurrences; no core fix
was required. It does not claim pixel or full-mesh equivalence.
The completion group published v0.3.0 from `b7776e2`, with explicit
`SHARC=1 TGPX4=1` distribution recipes and ROM-free machine/geometry gates.
Main and tag CI pass on all five platforms, and all seven public assets pass
checksum/provenance verification. Installed core and pristine standalone
files are unchanged. Results and reusable tools are retained; raw comparison
captures and replay inputs were removed at the user's request.

M29 is complete in this port: the original Sonic shared-word semantics are
preserved, the unrestricted common suite passes, and real frontend persistence
is verified, including reapplication after committed native Service Menu edits.
The manual and native gameplay consumers confirm separate 1P/VS semantics.
Wider gameplay/audio/device coverage remains M14; the v0.3.0 distribution
delivery is complete, with broader platform qualification retained under M16. See MODEL2C_ANALYSIS.md for the explicit native-memory
boundary and VALIDATION.md for accepted versus failed historical evidence.

### Historical M27 Reconstruction Evidence

The following records earlier stages; completion and publication above supersede
the intermediate pending/installed-build statements and historical budgets.

M27 was explicitly opened on 2026-11-02 after the first release. Its first
bounded activity maps the original SHARC implementation and prepares a single
binary-verified helper. Source review identified 116 indirect-code recovery
candidates absent from the existing decompile bodies. The user-authorized 1.1a
download is retained outside Git, with provenance and static address checks.
Authorized isolated Unicorn setup and related helper recovery groups are complete:
2,015,209 cases across 208 original addresses are checked with O0/O2 native
builds. The FP subset uses an additional x87 sequence oracle under Rosetta,
with bounded Unicorn discrepancies documented in SHARC_RECONSTRUCTION.md.
Current consecutive groups add nine conditional
single-transfer wrappers, 15 branch/call/return/loop handlers, ten simple
transfers and 15 mode/bank/stack helpers. Delayed record re-resolution, call/pop
ordering and native queued bank swaps are covered. The known inventory grew
from 172 to 185 after 13 additional direct helper entries were identified.
Six auxiliary integer and 34 FP entries are also recovered. Compute
and whole-program decoders pass, including 207 program calls with controlled CRT
allocation boundaries. The condition binder and NOP expand the inventory to 187.
Native save/restore, state getter, setup, NOP and diagnostic handlers pass another
6,144 cases; three discovered callbacks expand the inventory to 190.
Ten compound FP entries also pass, preserving extended temporaries, conversion
spills and unsigned interpretation of conversion result bits.
Native bus, reset, serializer registration and board initialization also pass.
A decode-to-compute bridge now reaches all 76 compute helpers through the
original record layout. Additional integration evidence totals **126,892 cases**,
counted separately: compute dispatch, memory/control wrappers with the complete
backend, bounded execution of real decoded compute instructions, and memory
wrappers calling the real board bus. Raw-record binding is qualified for 17 memory,
15 control and 10 transfer handlers, with rebinding after delay slots. The bounded
programs execute 9,604 instructions. Legacy memory/control regressions still pass.
The complete dispatcher covers 47 instruction forms and real bank events:
12,032 direct cases plus 512 bounded/continuous mixed programs (8,252 instructions)
pass with real delay slots and FIFO stopping. The native driver table adds 17
host-side addresses, now recovered. A composed device passes 44 scenarios / 1,892
operations from power-on through uploads and host/FIFO execution.
The opt-in `SHARC=1` standalone/headless build now connects the device through
the real i960 memory map. Synthetic uploads, FIFO execution, shared-memory writes,
reset and teardown pass. Fighting Vipers reaches 3D attract in a 2,400-frame
SDL/OpenGL capture; headless audio is non-silent. Direct and pipeline geometry
hashes, tile output and PCM match. A separate scripted-input run reaches a fight;
VF2's default/SHARC-build regression is identical. CPU/geometry sanitizer checks
pass; the audio path reports existing signed-shift UB in Musashi/SCSP, without
ASan errors. SHARC Save State requests are explicitly rejected pending complete
state/validation integration. ARM64/x86-64 machine-state fingerprints match for
1,200 frames; renderer FMA rounding differences were isolated. The user retained
upstream rendering and requested its original-Windows comparison separately.
The shared upload controller adds 32,768 original-binary checks. The opt-in
Libretro build now passes Fighting Vipers scripted combat through the existing
ABI/GL harness and real RetroArch attract, plus VF2's existing Save State suite.
The original Windows Save State path already exists: its recovered SHARC
callbacks copy 0x2a4 CPU bytes and rebind the saved PC against the existing
decoded program. After reviewing that session dependency, the user's latest
instruction selects this port's existing Model 2A complete-snapshot conventions.
The research build now supplies the additional context around those native
callbacks. Fighting Vipers passes four exact continuations and fresh-process
loading; VF2 retains its 12 MiB contract and passes its regression suite.
The actual RetroArch state round-trip also passes: advancement, exact restored
frame/image, resumed advancement and normal process exit are verified.
Linux x86-64 compilation, ABI loading and ROM-free mapped-machine/state checks
pass using the existing SM2 builder image; Linux frontend execution is untested.
Over Rev Model 2B, the other SHARC set in the current Libretro catalog, also
reaches 3D attract in RetroArch and passes exact same/fresh-process Save State
continuation. This does not expand the catalog or enable Model 2C.
A separate 6,144-case finite transform diagnostic compares two original x87
routines, an independent x87 oracle, and the actual portable geometry helpers.
With 24-bit x87 precision, x86-64 and diagnostic ARM64 without FMA match; the
normal ARM64 build differs in 964/2,048 vectors/points. Other x87 precision
modes change the comparison. The runtime Windows FPU mode and full rendering
path remain unqualified; production renderer source/flags are unchanged.
Original-renderer equivalence,
sustained gameplay and other-platform execution remain unverified.
No production or installed core includes this work yet.
Work stopped on 2026-11-03 at the authorized **50% account-wide consumption
ceiling**, starting at 40%. The reported reset is 2026-11-08 13:59 CET.
The user subsequently authorized another five percentage points: work resumed
with a **55% account-wide ceiling**, without commit/push authorization.
On 2026-11-03 the user added another five percentage points, raising the current
ceiling to **60%**. Latest boundary reading: **58%**; the ceiling has not been
reached. The SHARC persistence policy is resolved by the Model 2A convention.
At each group boundary, report recovery completion against the current known
address inventory and account usage separately. Current recovery coverage is
**208/208 = 100%**; new discoveries may expand the denominator. This metric does
not treat all routines as equal effort or include unquantified integration and
gameplay acceptance. See SHARC_RECONSTRUCTION.md for the inventory derivation.
No further commit, push or release is authorized.

First release delivery: **0.1.0** is this independent port's version, separate
from its pinned upstream commit. The GitHub workflow follows SM2's build,
matching-source, checked-package and tagged-release stages. This delivery
targets Linux x86_64/ARM64, macOS Apple Silicon/Intel and Windows x86_64. CI/build
receipts and runtime qualification retain separate scope. GitHub page:
https://github.com/Zer0one/Model2EmuEx-libretro.

M08's targeted native Input Test checks are finished: actual RetroArch verifies 15 Sega Rally cases and 18 VF2 cases, including analog pressure and independent players. Current SM2 input sources remain identical to the imported engine; all 28 adapter profiles pass existing source tests. No core fix or binary update was needed. The reusable frontend runner now accepts existing input replays, and a two-title fixture generator reuses SM2's replay format.

On November 14, VF2 completed the paused change to Normal in RetroArch. The native Service switch released on resume with the gameplay contact still held. Fixed-frame tests also identified a destination bit rotation that assigned the wrong action to every face button in VF2. The VF2 family now uses the SM2 action bits directly. M08 implementation is now complete after the Fighting Vipers/Last Bronx follow-up. Broader per-title gameplay and physical devices remain in M14. M18's supplementary exact-frame PNG probe also remains uncompleted; earlier M12 evidence retains its original scope.

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
- Related recovery blocks may be grouped at the agent's discretion; summarize completed groups and ask about concrete semantic choices. Publication requires explicit authorization (granted separately for the completed v0.3.0 delivery; later unrelated publication remains unauthorized).

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

## Version 0.5.0 Publication Preflight — 2026-11-15

The user authorizes commit, push and release after five-platform verification.
Runtime and Core Info versions are 0.5.0. The release includes M33 native catalog
integration and the retained NVRAM audit tools/results documentation; excluded
operator settings remain excluded. CI now runs native-protection, Air I/O,
88-profile and NVRAM fixtures before packaging on all five supported platforms.
The previous local startup/state evidence retains its stated scope. Main CI
must pass before tagging; tag CI and asset verification gate publication.

### Version 0.5.0 Public Release Receipt

Published from `562d6f864b2b9838d70be6c594c83a700c962f07` after all five main
platform gates passed. The tag reran all five successfully before publication.

- [Main core CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/43720227068)
  and [tag core CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/43720678960)
  pass native machine/geometry, four new integration groups, ABI, architecture,
  dependency, corresponding-source and package checks on all five platforms.
- [Main standalone CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/43720227081)
  and [tag standalone CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/43720678891)
  pass Linux desktop GL/GLES, Windows and Android builds.
- Seven published assets pass outer/inner SHA-256, ZIP integrity, Core Info
  version/provenance and exact committed-source equality. Full job logs confirm
  all four new fixture PASS receipts on every platform, on main and tag.
- The configured local universal core and matching info are updated to 0.5.0.
  SHA-256: `58378e3c7767d4e11efa1005d0d4f5f224beabb50c838b25aad9ee91efd29b37`.

Compact receipts and the reusable public-asset verifier remain in
`port/build-publish-v050/`. The post-release documentation commit does not
change the qualified code/tag or create another release. No further gameplay
or physical-device acceptance is inferred from publication.
