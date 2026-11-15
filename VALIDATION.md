# macOS Validation

Initial validation: 2026-10-20. Host: native Apple Silicon macOS. Upstream baseline: `25d82be56f339c754cc566f771ca9ffb90b69289` (`daytona_decomp`). The pristine reference checkout is `/Users/andrea/dev/Model2EmuEx`; the original baseline remains pristine in the sibling checkout. Later sections document the native audio/backdrop corrections and adapter lifecycle fixes beyond the initial MAME loader, drive observation, source gains, ROM verification and serialization work. See LIBRETRO_DESIGN.md for current ownership and scope.

## M28 Research Model 2C Machine And Save States — 2026-11-04

The explicit `TGPX4=1` build composes the recovered native CPU and driver on
the existing i960 map. The original-entry recovery inventory is 286/286 plus
18 additional helpers; that count alone is not a full M28 completion percentage. The
later integration/platform sections below close the bounded M28 group. See
MODEL2C_ANALYSIS.md for original-binary, native AMD FP and composed-program
counts, provenance and limitations.

| Check | Evidence | Result And Scope |
|---|---|---|
| ROM-Free Machine | `port/build-sharc-machine/model2c-combined-machine.log` | Both SHARC and TGPX4 fixtures pass in a combined build; TGPX4 covers three resets, uploads, FIFO/shared memory, replacement/rebound snapshots, malformed/truncated rejection and maximum upload size |
| Default Build And SHARC Regression | `model2c-default-build.log`, `model2c-sharc-regression.log` under `port/build-sharc-machine` | Default macOS core builds; SHARC machine/state regression passes independently |
| Over Rev Headless | `port/build-tgpx4-machine/run-overrev/result-1800.json` | 1,800 frames, exit 0, native program upload and FIFO stopping; no rendering claim from headless execution |
| Over Rev And Wave Runner Frontend | `overrev-retroarch-1800/result.json`, `waverunr-retroarch-1800/result.json` under `port/build-tgpx4-machine` | 1,800 frames each, clean exit, inspected screenshots show 3D attract |
| Over Rev ABI/GL States | `overrev-abi-states/result.json` under the same root | Cold save/load, four exact continuations, context recreation, invalid-state rejection, fresh-process 12-frame exact continuation; 16 MiB capacity |
| Over Rev RetroArch States | `overrev-retroarch-states-confirm-disabled/result.json` | Exact restored game-region PNG at machine frame 1,800; scene advances before and after load, save/load logs confirmed, exit 0 without forced termination |
| Ski Super G And Sega Water Ski Headless | `run-skisuprg/result-1800.json`, `run-segawski/result-1800.json` | 1,800 frames each, exit 0 and 32 KiB TGPX4 program upload; this alone does not establish progression beyond native startup checks |
| Ski Super G Frontend | `skisuprg-retroarch-1800/result.json` | 1,800 frames, clean exit; inspected screenshot shows `DRIVE BOARD TROUBLE / CODE: FF`, not attract/gameplay acceptance |
| Ski Super G Native Handshake Fragment | `port/build-sharc-machine/model2c-motion.json` | 7,825 original executions and 15,650 portable comparisons pass; subsequent board/frame/state integration is recorded below |
| Sega Water Ski Frontend | `segawski-retroarch-1800/result.json` | 1,800 frames, clean exit; inspected screenshot shows the water-ski attract scene |

The Save State core SHA-256 is
`6417f1118c8909ede2003a8c0bae5e2e26aef817e2b1c3af3d56f9d4792d392e`.
The accepted RetroArch restored game-region SHA-256 is
`d5f1c76cdd46ab3ce237f9f8a694b1593b44b6e75babb123d13d8f127bc42f86`.
The initial frontend state attempt also restored exactly but required forced
termination because the test profile retained the frontend quit-confirmation
setting. It is not a clean-exit pass. The existing runner now disables quit/close
confirmation only in its generated isolated configuration, matching the input
runner convention; the repeated complete run passes without force.

ROM archives were read directly from existing storage. Configurations, saves,
states and screenshots were isolated. No installed core, global configuration,
production CI flag or pristine standalone file changed. At this initial
checkpoint, native per-game geometry, remaining catalog entries and other-platform
full-machine behavior were not yet qualified. Later sections record those
follow-ups. CPU FP evidence alone does not establish a Batocera frontend run;
the subsequent native frontend samples are recorded separately below.

### Ski Super G Motion-Board Integration

The native handshake is integrated without the simplified SM2 acknowledgement
stub. Both machine fixtures pass with SHARC and TGPX4 enabled; the TGPX4 fixture
checks CE/FF/echo and pending-countdown restoration after device recreation.
The board archive maximum is now 11,919,036 bytes. Its research schema is TGX2.

New receipts under `port/build-tgpx4-machine`:

- `skisuprg-motion-retroarch-1800/result.json`: 1,800 frames, inspected 3D attract
  screenshot, normal exit (50.95 seconds), replacing the earlier drive-board error.
- `skisuprg-motion-abi-states/result.json`: cold save/load, four exact replays,
  context recreation, rejected invalid states and exact 12-frame fresh-process continuation.
- `skisuprg-motion-retroarch-states/result.json`: exact visual restoration at
  native frame 1,839, advancement before/after load, exit 0 without force.

Core SHA-256: `7f07f160eb389a6f5ab92703c52abadd133aa59a65e1be7b60ba733f271739fa`.
Restored game-region PNG: `c43f39eb2e51bf04a3cc70c63d64ff6c64a881ce31db8753bf11d7611e540905`.
This confirms the bounded attract and state paths, not physical motion or full gameplay.

### Native Catalog And ROM Transform

The 70-set compiled metadata/archive suite passes with 13 M2C definitions.
`port/build-sharc-machine/model2c-mame-check.log` records the result;
`model2c-record-inventory.json` records recovered addresses and main-program
matches, and `model2c-rom-transform.json` records 263 original executions /
526 O0/O2 comparisons of the full-region Top Skater sample byte swap.
The research core build passes (`model2c-catalog-core-build.log`).

| Sample | Receipt Under `port/build-tgpx4-machine` | Observed Result |
|---|---|---|
| STCC | `stcc-catalog-retroarch-1800/result.json` | 1,800 frames, 33.96 seconds, exit 0; inspected screenshot shows 3D race attract |
| Top Skater | `topskatr-catalog-retroarch-1800/result.json` | 1,800 frames, 33.43 seconds, exit 0; inspected screenshot shows corrupt geometry, visual qualification failed |

The initial Top Skater failure exposed its unintegrated native special
object/matrix path; the subsequent accepted run is recorded below. No full-gameplay, physical input or audible-fidelity
acceptance follows from these samples. No ROM was copied or modified.

### Top Skater Native Geometry And Pipeline

Six original control overrides pass 1,536 original executions and 3,072 O0/O2
comparisons (`port/build-sharc-machine/model2c-geometry-control.json`). The
special object wrapper is checked only up to its common-handler tail transfer.

`make -C port TGPX4=1 SHARC=1 BUILD=build-tgpx4-combined check-tgpx4-geometry`
passes a synthetic mixed display list, dual-matrix selection/restoration,
compact triangle/quad strides, ordinary objects, archived matrix continuation,
face winding and two-slot renderer snapshot isolation. Sanitized execution
also passes. Default core and combined SHARC/TGPX4 machine regressions pass.
The default Model 2B generator still reproduces all 22 original records exactly.

Receipts under `port/build-tgpx4-machine`:

- `topskatr-native-geometry-retroarch-1800`: geometry still corrupt because the
  render-side snapshot omitted the native dual-matrix flag; not accepted.
- `topskatr-native-pipeline-retroarch-1800`: scene/skater visible after flag
  transfer, but missing faces; not final visual acceptance.
- `topskatr-native-winding-retroarch-1800`: 1,800 frames, 33.69 seconds, exit 0;
  inspected screenshot shows the complete scene after native winding correction.
- `topskatr-native-pipeline-abi-states`: cold load, four exact continuations,
  context recreation, malformed-state rejection and exact fresh-process replay.
  This precedes the final face-winding change; its core SHA is recorded in JSON.
- `topskatr-native-final-retroarch-states`: final core passes actual RetroArch
  Save/Load with exact restored game-region pixels at native frame 1,922,
  advancement before/after load and normal exit without force. Core SHA-256:
  `1039352a392b5380b7f0f1b3e853f400dc82cfd06534ec281a480b6c9af678c4`.
- `bel-catalog-retroarch-1800`: 1,800 frames, 33.34 seconds, exit 0; inspected
  screenshot shows the attract mission briefing and weapons crate. No gameplay claim.

The matrix extension is M2C-only; other board payloads and compiler FP flags
are preserved. No cross-GPU pixel identity, physical-control or audible-output
claim follows from these checks.

## Current Shared-Feature Verification

### M27 Native SHARC Helper — 2026-11-02

The first recovered SHARC decoder helper (`0x004bcd10`) passes 34,496
differential cases against the original ElSemi 1.1a x86 image under Unicorn
2.1.4. Native arm64 C99 builds at O0 and O2 both match, with zero mismatches or
skipped cases. All 256 encoded widths, bit/sign boundaries and deterministic
random inputs are covered; return, stack, preserved registers and write bounds
are checked on the original. The first sandboxed attempt failed during Unicorn
host initialization before guest execution; the authorized unsandboxed run
passed. See [Native SHARC Reconstruction](SHARC_RECONSTRUCTION.md) for pinned
image provenance, build recipe, scope and the ignored result receipt.

This is isolated helper evidence only. The helper is not linked into the core;
no Model 2B/2C game, board timing or frontend support is newly qualified.

The next combined group adds six field-helper entries and the register
selector: 149,184 field cases (1,728 with operand/status aliasing) and 1,024
selector cases pass against ElSemi at both O0 and O2. All 4,096 position/width
controls and all 256 register encodings are exercised. The complete synthetic
data arena, preserved registers, return/stack and allowed writes are checked.
The original immediate helper was rerun on the final bit-helper libraries:
34,496 passes. Coverage after that group was 184,704 inputs across eight original
entry points, zero mismatches/skips. Receipts and exact per-entry counts are in
SHARC_RECONSTRUCTION.md. No full-core build or frontend run was needed: these
modules are not yet in production build targets.

The integer group adds 19 ALU entries (148,960 cases) and nine shift/bit entries
(68,020 cases, including 700 aliases), with zero mismatches/skips against the
original at O0/O2. Coverage after that group was 401,684 inputs across 36 entries.
Incoming x86 flags are varied explicitly; preserved original INC/DEC/NOT
dependencies have small recorded witnesses, not assumptions about hardware.
See `port/build-sharc/integer-differential.json`, `shift-differential.json` and
SHARC_RECONSTRUCTION.md for per-entry results and remaining decoder,
floating-point, multiplier and board boundaries.

The condition/dispatch group adds all 64 condition-table slots (34 distinct
original functions, 38,400 cases) and two complete integer dispatch wrappers
(109,442 cases). Both O0/O2 libraries match the original, including raw return
masks, sticky stop effects, false conditions with inaccessible operands, ASTAT
aliases, and compute-before-move stores. The test observes actual EFLAGS at
helper entry. Another 256 original-only prefix probes distinguish false-branch
TEST flags from inherited flags on eight other handlers; execution stops before
compute/memory effects and does not qualify those full handlers. The existing
148,960-case ALU suite also passes after adding the supported-selector predicate.
Cumulative differential coverage is **549,526 inputs across 72 entries**, zero
mismatches/skips, excluding prefix-only probes and repeated ALU verification.
The new receipt is `port/build-sharc/condition-dispatch-differential.json`.
The modules remain outside production builds; no installed core, ROM, NVRAM,
Save State format or Model 2B/2C execution gate changed.

The next memory/branch group adds eight complete integer wrappers, with
97,280 original-vs-C cases at O0/O2, zero mismatches/skips. Synthetic callbacks
check read/write order, arguments, callback mutations, address post-modifiers,
register/status aliases, mirroring and wrapping branch targets. The callbacks
are a controlled bus fixture, not reconstructed board handlers. The cumulative
full-entry count after that group was **646,806 inputs across 80 addresses**.

Separately, six original outer-loop/delay flag-producing sites match the
portable flag helpers in 6,402 fragment cases. Eight bounded original-loop
traces execute NOT through its original unconditional dispatcher and verify
first-entry/subsequent-entry flags and resulting ASTAT. The trace returns from
the dispatcher after compute, before memory transfer, so it is not a complete
instruction-stream or loop acceptance test. See `memory-differential.json` and
`flow-differential.json` in `port/build-sharc/`. Recovery coverage is **46.5% of
the known address inventory (80/172)**; full integration remains unqualified.

The execution-scheduler group adds four entries: `0x004bcf70` events (80
cases), `0x004bdfa0` delay slots (160), `0x004bd000` bounded execution (972)
and `0x004be000` continuous execution (973). All **2,185 cases** pass against
the original at O0/O2, including complete return, state, callback sequence and
entry flags, preserved registers, stack and write bounds. Native execution is
not stopped at a prefix in this suite. Decoded handlers/events remain identical
synthetic boundary fixtures on both sides, so no decoder or board is qualified.

The suite exercises all loop-condition slots, counted-loop types, stack restore
including wrapped -1 indices, live event-count growth/shrinkage, event side
effects, zero/wrapping budgets, nested slots, pre-existing stop and stop during
slots. One case executes 100,001 original dispatches to verify a real continuous
batch refill. Additional cases change configured program/bus bindings during
execution. x87 control is retained as guest metadata; no host fenv or floating-
point result is claimed. Receipt: `port/build-sharc/execute-differential.json`.
Cumulative full-entry evidence is **648,991 inputs across 84 addresses**;
recovery coverage is **84/172 = 48.8%**. Production builds and installed cores
remain unchanged.

Consecutive transfer/control/mode groups add 49 verified entries: nine new
conditional compute transfers (175,104 new cases; 272,384 memory cases total),
15 control/loop handlers (30,720), ten simple transfers (2,560), and 15 mode/
bank/stack helpers (15,360, including 512 queued-bank integration sequences).
All pass original x86 comparisons at O0/O2 with zero mismatches/skips. Delayed
record redirects, operand/stack aliases, callback mutation, changed-bit-only
bank queuing and high-before-low bank order are included. The original x86 ABI
assumes DF clear for bank copies. The inventory expands by 13 directly identified
helpers: cumulative **872,735 full-entry cases, 133/185 targets (71.9%)**.
See SHARC_RECONSTRUCTION.md and the ignored per-suite receipts. No production
core or gameplay support is implied.

Auxiliary integer helpers add six entries and 65,804 cases, retaining native
low-word multiply, signed clipping corner cases and simultaneous-result aliases.
Four initial FP helpers add 46,224 cases. Unicorn omits SNaN quieting, exception
flags and C1 clearing, so the FP suite additionally compares complete results
with independently transcribed x87 sequences under Rosetta. The original still
runs to return in every case, with only those bounded oracle discrepancies
permitted. This is not physical-x86 qualification. Current cumulative coverage:
**984,763 cases, 143/185 entries (77.3%)**. See the detailed evidence and oracle
limitations in SHARC_RECONSTRUCTION.md. The production core remains unchanged.

Five further unary/clipping FP entries expand that suite to 104,004 cases.
The complete compute decoder passes 77,824 inputs; the program decoder passes
207 whole calls covering 262,180 synthetic instructions, plus 512 direct
condition-binding calls. Controlled CRT callbacks verify free-before-allocate,
sizes, untouched record words and the final binding. Register selection passes
its 1,024-case regression after sharing offset resolution with token binding.
Current coverage is **1,121,086 cases, 151/187 entries (80.7%)**. The two added
inventory entries are the condition binder and NOP; NOP is not yet recovered.

Comparison/conversion expands the simple FP suite to 12 entries / 138,672 cases.
Eight arithmetic entries add 93,600 cases: add/subtract, absolute variants,
average, multiply, reciprocal and reciprocal square root. Precision is the
original scheduler's PC=24 with all RC modes; temporary exponents remain extended
until FSTPS. The same qualified dual-oracle method applies, including narrowly
bounded SNaN propagation differences. Integer ALU regression passes 148,960
cases, not counted twice. Current total: **1,957,865 cases, 190/190 entries (100%)**.

### M27 Recovered Component Integration — 2026-11-03

Helper coverage is **1,982,441 cases / 207 known entries**, including 24,320
host-driver and 256 upload-completion cases added after reviewing the native
driver table. Separately, **126,892 integration cases** pass with O0/O2 builds:

- Decode-to-compute: 24,576 cases, all 76 compute targets.
- Memory wrappers with the complete backend: 59,520 cases.
- Control wrappers with the complete backend: 21,360 cases.
- Bounded scheduler plus real decoded compute handlers: 768 programs, 9,604
  executed instructions, including counted loops and preexisting stop.
- Memory wrappers plus real board bus: 3,672 cases, synthetic RAM/ROM/FIFOs,
  ASTAT aliases and native full/empty/wrapping behavior.
- Raw-record transfer bindings: 2,560 cases for ten handlers. The memory/control
  integration suites above were also rerun through raw-record bindings, including
  rebinding after delay slots; their cases are not counted twice.
- Complete instruction dispatcher: 12,032 cases for all 47 forms, actual delayed
  instructions and queued bank events. Bounded/continuous mixed programs add
  512 cases / 8,252 instructions, including delayed calls/returns and FIFO stop.
- Composed native device: 44 scenarios / 1,892 operations from power-on/reset
  through synthetic 48-bit uploads, host FIFO commands and execution/resumption.
  Actual SHARC bodies execute; CRT memory ownership and shared rendering remain
  explicit boundaries. No i960 or game integration is inferred.

The original EXE executes the actual helper and bus bodies. Explicit callbacks
on the portable side compose separately recovered components. Detailed FP
exception/NaN qualification remains in the dual-oracle helper suites; integration
tests isolate wiring with finite operands. Existing integer-only memory and
control suites still pass 272,384 and 30,720 cases, not counted again. These
checks do not qualify production bindings, physical x86 hardware or games.
Ignored receipts use `*-integration.json`; `tools/sharc_progress.py` reports
integration separately from recovered addresses.

### M27 Opt-In Machine And Fighting Vipers — 2026-11-03

`SHARC=1 BUILD=build-sharc-machine` builds the headless and SDL frontends with
the recovered device connected to the real i960 map. `check-sharc-machine`
passes synthetic program/data uploads, FIFO execution/status, packed shared
writes and dirty tracking, reset and teardown. Default Libretro compilation also
passes; its capability gate and the installed binary are unchanged.

Fighting Vipers runs directly from the archive for 2,400 headless frames with
geometry and audio: no invalid i960 instruction, 1,083 final-frame polygons,
non-silent PCM. The pipeline path matches accumulated geometry hashes, final
tile image and the full PCM stream. A separate bounded SDL/OpenGL run captures
3D attract with a character, textured environment and HUD. It uses private
configuration/NVRAM and dummy audio; it is not audible-output or gameplay proof.
The initial restricted display attempt failed before video initialization; the
display-enabled run exits normally with a screenshot. Evidence is ignored under
`port/build-sharc-machine/fvipers-*`; details and PCM hash are in
SHARC_RECONSTRUCTION.md. Model 2B Save States remain explicitly rejected before
archive mutation. Original-renderer comparison and production integration remain
open; Model 2C is not enabled.

The subsequent isolated GL input run reaches Stage 1 Grace versus Bahn after
scripted Coin/Start/selection/movement/attacks. This is short scripted gameplay,
not physical controls or sustained acceptance. VF2's 900-frame default and
SHARC-enabled runs have identical full logs, RAM/geometric hashes and PCM.
AddressSanitizer/UBSan pass the synthetic machine test and Fighting Vipers
CPU/geometry for 2,400 frames. The audio-enabled check reports seven existing
signed-shift sites in Musashi/SCSP; a reporting run completes with no ASan error
and matching geometry hashes. Do not describe whole-audio UBSan as passing.
These findings and exact ignored evidence paths are in SHARC_RECONSTRUCTION.md.

### M27 Upload Controller, Architecture And Libretro — 2026-11-03

The shared original upload controller `0x004c79c0` adds 32,768 O0/O2 cases,
including callback mutation/latch ordering. Current known helper coverage is
**208/208 entries, 2,015,209 cases**; integration remains **126,892 cases**.
ARM64 and x86-64 via Rosetta match final tiles and PCM over 2,400 Fighting Vipers
frames. At 1,200 frames, every SHARC/native-buffer fingerprint and main-RAM hash
matches. Geometry hashes differ with ordinary compiler flags; changing only
the ARM64 geometrizer object to disable FP contraction makes those hashes match
as well. The user chose to retain upstream renderer behavior and compare against
the original Windows renderer separately. No ordinary rendering flags changed.

The opt-in Libretro build passes the existing 2,400-frame Fighting Vipers
ABI/GL harness: scripted combat, video/PCM, options, Pipeline, frame skip,
resolution/context recreation, reset, Save RAM and unload/reload. Zero SHARC
state capacity and refusal without caller-buffer mutation are verified.
The same binary passes VF2's existing 900-frame/cold Save State suite, including
four exact 12-frame continuations and malformed-input rejection. EEPROM checks
also pass. A real RetroArch run exits normally after 1,800 frames and captures
textured 3D attract, with isolated settings/saves and muted audio. The installed
core and default build capability are unchanged. Receipts are under
`port/build-sharc-machine/{fvipers-libretro-2400,vf2-libretro-states,fvipers-retroarch-1800}`.
This does not qualify SHARC Save States, sustained/physical gameplay or Windows
and Linux execution. Full provenance and architecture evidence paths are in
SHARC_RECONSTRUCTION.md.

### M27 SHARC Save States Following Model 2A — 2026-11-03

The original Windows CPU callbacks already existed and remain the basis of
SHARC save/restore. After the native session dependency was explained, the
user's latest instruction selected this port's complete Model 2A convention.
The research archive adds the program/cache and execution context, with a
16 MiB capacity and explicit SHARC ABI bit; Model 2/2A remain 12 MiB.

The mapped-machine test covers changed program RAM with a warm cache,
replacement/reset, callback/FIFO rebinding, exact continuation, structural
corruption and every subarchive truncation boundary. ASan/UBSan pass. The
maximum native program upload is exercised. Refreshed original-executable
decoder and CPU lifecycle tests pass O0/O2 (719 and 6,144 cases).

Fighting Vipers passes cold save/load and four exact 12-frame state/PCM/image
continuations after 2,400 scripted frames. A new process loads before its first
game frame and produces identical continued state and image. VF2's regression
retains exact continuation and current NVRAM authority. Final-core fresh-process
revalidation also passes after the cache-allocation rollback refinement.

The real RetroArch runner passes save, advancement, load at the same machine
frame (2,281), exact full screenshot/game-region restoration, resumed advancement
and clean exit, with no forced termination. The first attempt had successfully
saved but could not observe the buffered frame trace live; that diagnostic-only
flush defect was corrected before the successful repeat. The frontend evidence
is attract restoration, not physical-input or listening qualification.

Receipts are under `port/build-sharc-machine/`:
`fvipers-sharc-states`, `fvipers-sharc-fresh`, `fvipers-sharc-final`,
`vf2-sharc-regression`, `fvipers-retroarch-state-trace/result.json`,
`state-build.log`, `state-sanitized.log`, and the refreshed differential logs.
Tested final core SHA-256:
`968bb3739807374d04a9bc1ce8ceb9b0cad5da7005031a324fa9e4d15b57521a`.
The installed development core still has SHA-256
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.
No default/release Model 2B enablement, installation, commit or push occurred.

### M27 Linux x86-64 Research Build — 2026-11-03

The existing Colima/Rosetta amd64 builder and SM2 GCC 15.2.0 image compile the
research core with `platform=unix SHARC=1`. The core loads and passes
`scripts/check-abi.py`; mapped-machine SHARC/state tests pass. `file` confirms
ELF x86-64 and `ldd` reports no missing dependencies. No ROM or original EXE
entered the source snapshot/container, and no dependencies were installed.
See `port/build-sharc-machine/linux-artifact/result.json`, its adjacent core,
`linux-source-manifest.json` and `linux-gcc15-validation.log`. This is build,
load and ROM-free execution evidence, not Linux frontend/gameplay acceptance.
The synthetic state checks also pass in the macOS x86-64 Rosetta build.

### M27 Over Rev And Original Geometry Diagnostic — 2026-11-03

`overrevb-retroarch-1800/result.json` records a bounded actual RetroArch run:
1,800 frames, 33.85 seconds, exit zero, no timeout. The retained screenshot
shows 3D cars, track and scenery in attract. This is not gameplay or audible
output qualification. The research core is the same SHA-256 recorded above.

The existing `check-savestates-macos.py` runner now accepts an explicit research
core (`--core ... --sharc`) without rebuilding the default core. Its Over Rev
receipt `overrevb-states/result.json` passes cold save/load, four exact 12-frame
continuations after frame 1,200, invalid-state rejection, graphics context
recreation and fresh-process restoration. State capacity is 16 MiB. The PCM
continuation is 8,820 stereo frames, CRC `f1d61346`. No NVRAM-authority claim is
made for this title; the existing VF2 case covers that contract.

`geometry-original-comparison.json` contains 6,144 finite transform cases,
original EXE/source/binary hashes and first numerical mismatch witnesses.
Original entries `004b9cb0` and `004b9df0` run under Unicorn and match the
independent x87-sequence oracle under Rosetta for all cases. Each of three x87
precision modes covers 1,024 points and 1,024 vectors. At 24-bit precision,
current x86-64 and diagnostic ARM64 `-ffp-contract=off` match every result;
normal ARM64 differs in 416 points and 548 vectors. At 53/64-bit precision,
neither portable variant matches every result. This establishes a bounded
arithmetic difference, not the original application's active renderer FPU mode,
whole-frame equivalence or physical x86 behavior. No production rendering
source or flags changed. Reproduction commands and limits are in
SHARC_RECONSTRUCTION.md. These diagnostic calls do not increase SHARC recovery
coverage, which remains 208/208 original addresses.

### Earlier Shared-Feature Checks

The earlier results below retain their original integration-stage evidence. Current native mode is selected explicitly in pristine comparisons; 60 Hz is now the user-approved default. Historical generic-input or keyboard descriptions do not describe the current SM2 bridge. Source changes and installed-copy status are listed explicitly rather than inferred from early results.

- `bash scripts/check-sm2-common.sh`: complete 340-field NVRAM bridge checks, all 28 current set profile/wiring tests, paused Service/Test refresh, None, native gears/ADC/gun counters, rumble lifecycle, unchanged full SM2 input/profile/crosshair tests, and V2-to-legacy ABI registration checks pass.
- `audit/sm2-audio-native-vf2-display`: 900-frame Native VF2 main RAM SHA-256 `c213a5cba382d13e08a75a079ece268ddc8e175d79e9e2d3ebfe84c4bc1e9993` and PCM `ff48a0eb0bbdb607ba9844551a65edf41152c273c42ba61b50646de3860f8753`, byte-identical to same-revision pristine upstream with matched startup NVRAM. The first restricted attempt could not initialize the display; the display-enabled run passed.
- `audit/sm2-audio-60-vf2`: 900 machine frames, 60 Hz, 661,500 stereo PCM frames and identical main RAM. Deliberately refused every seventh audio batch; retained samples were subsequently delivered. Timing remained latched across option changes/reset and adopted the pending value on reload.
- `audit/sm2-audio-muted-vf2`: SCSP Gain Mute produced zero PCM while main RAM matched normal 60 Hz output; normal audio was non-silent. This proves delivery/synthesis progression, not audible speaker output.
- `audit/sm2-input-srallyc`: 900-frame callback/GL/lifecycle run passed with the new shared input bridge. Capture shows the game's initial legal screen; this is not a race/gameplay claim.
- `audit/sm2-crosshair-vcop`, `sm2-crosshair-custom-vcop`, `sm2-crosshair-disabled-vcop`: 900-frame actual GL runs pass, including reset/context recreation/reload. The default SM2 crosshair changes 160 pixels within its expected bounds; a synthetic half-alpha red PNG changes 16 pixels near the aim center. Main RAM is unchanged across these presentation modes. The unchanged source tests separately cover both styles/colours, per-player visibility, missing/invalid PNG fallback, alpha and inactivity timers.
- `scripts/check-mame-romsets.py --source /tmp/model2emuex-mame-reference/model2.cpp`: all 28 MAME identities plus actual stored/deflated/loose CRC verification pass. Forged ZIP metadata cannot bypass Enabled. Disabled accepts explicitly requested mismatching payloads but still rejects wrong sizes. All fixtures are synthetic.
- `audit/sm2-audio-sources-daytona` and `sm2-audio-muted-daytona`: original Model 2 MultiPCM/YM3438 normal output is non-silent; all-source Mute yields zero PCM with identical main RAM. This does not yet isolate each chip independently.
- `make standalone -j4` succeeds after the neutral hook/gain/ROM-policy changes. No reference checkout or production ROM archive was modified.

Physical controllers/lightguns/rumble, audible playback, completed gun/driving gameplay, true GPU context loss and external linked-cabinet frontend behavior remain outside these verification claims. Save States have their separate M12 evidence below.

## Results

| Check | Result | Evidence / Limits |
| --- | --- | --- |
| Independent repository | Passed | `main`, no tracking branch, original 34 commits retained, only `upstream` configured; no commit or push. |
| Native core build | Passed | arm64 Mach-O dylib, Libretro ABI exports only; system zlib/libSystem/libc++ dependencies; no SDL, ImGui or Homebrew runtime dependency. |
| Original standalone/headless build | Passed | `make standalone -j4`; original Makefile retained; native defaults preserved with optional frontend-neutral serialization APIs. |
| ROM-free ABI check | Passed | Metadata, legacy option tokens/default, unsupported/missing content rejection, empty memory and cleanup. |
| VF2 comparison | Exact | 900 board frames; 1,048,576-byte main RAM and 2,737,240-byte raw stereo PCM identical to pristine upstream `m2run`. |
| Sega Rally comparison | Exact | Same 900-frame comparison; main RAM and PCM identical. This tests Model 2A, not a completed race. |
| GL harness | Passed | Nonzero frontend-owned FBO, video/audio callbacks, 1x→2x update, GL resource recreation, reset, SRAM import before first frame, unload/reload. |
| VF2 scripted paid match | Passed | Two simulated Libretro coin pulses, Start and repeated Punch; 2200-frame screenshot shows paid Akira vs Lau match, round timer and changed health. This is not a physical controller or real RetroArch input test. |
| Real RetroArch 1x | Passed | RetroArch 1.22.2 (`9be7ec92`), desktop `gl`, 1800-frame bounded run; screenshot shows 3D attract fight; CoreAudio initialized; `.srm` saved as 65,664 bytes; normal exit 0. |
| Real Core Options / Resume | Passed | CUA native Command → Menu Toggle → Core Options → Video → Internal Resolution; selected 2x (992 x 768), resumed and observed rendering. Runner exited 0, option file contains `2`, final screenshot retained. |
| Physical input / audible playback | Unverified | No physical controller operation or independent audio monitoring was performed. PCM equality is evidence of synthesis/delivery, not speaker output. |
| Daytona Initial Standalone Attempt | Content Blocked (Historical) | The prior standalone audit found three missing shared ROMs in daytona.zip and no shared model2.zip. Archives were not modified and no gameplay claim is made. |
| Model 2B/2C | Unsupported | Existing upstream machine limitation. |
| Save States | Passed For M12 | Native and fresh-process continuation plus real RetroArch round-trips; see the separate M12 record below. |
| Linked cabinets | Unimplemented | No linked-cabinet frontend claim. |
| Intel / universal / other OSes | Unverified | Initial port targets this arm64 Mac only. |

## Comparison Hashes

SHA-256 of core output, equal to the corresponding pristine upstream output:

| Game | Main RAM | Raw PCM |
| --- | --- | --- |
| VF2 | `5950657437cc639a237bc4361a27584666dfbd2da737ac4fa19d138852532c06` | `d7913d939c28e0fb147fa87ab5d4fa36e25c10456d359c48311867b1b4eeae07` |
| Sega Rally | `b0a95ddad912d94cae14cf508f2f073ea30e90cae7a0759959c063de7590f473` | `70281705aa8bac073eedf7cf39fa359e0b7e37c049075dcda0095d25b597e7b2` |

The first PCM comparison revealed a one-frame phase difference: upstream's runner synthesizes the pending sound slice before running the next board frame. Matching that ordering in the adapter produced exact PCM equality. No sound-device code or machine emulation was changed.

## Local Evidence

Ignored output under `port/build-libretro-macos/audit/`:

- `final-vf2/` (final binary), `vf2-verified/` and `srallyc-verified/`: reproducible comparison manifests, core/upstream RAM and PCM, harness logs and frame captures.
- `vf2-play/core.png`: paid-match screenshot from the scripted ABI frontend; `check.log` records 2204 successful video callbacks including lifecycle checks.
- `retroarch/vf2.png`, `retroarch/run.log`: real frontend 1800-frame attract test, SRAM save and shutdown.
- `retroarch-menu/final.png`, `result.json`, `run.log`, and `config/Model2EmuEx/Model2EmuEx.opt`: real menu/Resume test, owned PID 57025, normal exit, saved 2x option. CUA menu screenshots were observed inline; no separate local menu capture is claimed.
- `abi.log`: rejected-content and ABI smoke check.

These original tests loaded the core directly from the build directory and left installed files unchanged at that stage. A later user-authorized local installation is recorded below. Normal production options/saves, the standalone checkout and original ROM archives remain untouched. All launched test processes have exited. No dependencies were installed.

### Historical Raw Output Retention — 2026-11-01

The authorized cleanup removed 246 disposable outputs from evaluated, closed
build/lifecycle, native-option, timing-overlay, Save State and linking checks:
73 PCM captures, 88 main-RAM dumps, 72 raw RGB comparisons and 13 PPM images
with retained PNG counterparts. References above describe the original runs;
their raw files are no longer all retained. Existing result/comparison JSON,
hashes, logs and documentary screenshots remain the historical receipts.
Scripts regenerate comparison data in new isolated directories when a future
authorized test needs it; no test was rerun for cleanup.

Save States, SRAM/NVRAM, Service Menu material, M25's open analysis, ongoing
audio/input/crosshair qualification material, useful builds and historical
reference binaries were preserved. ROMs and the separate standalone checkout
were untouched. SHA256 verification covered all 2,011 retained non-Git files
before this documentation note. Deletion identities and measurements are in
ignored `audit/cleanup-20261101/result.json`; earlier cleanup receipts remain.

## Diagnostics And Boundaries

Restricted execution cannot enumerate macOS displays; display-enabled execution was needed for the test harness and real RetroArch. The linker reports the same common-section 0x8000→0x4000 alignment reduction seen in the pristine standalone baseline. The imported Musashi/softfloat code also produces existing compiler warnings; the adapter builds without compiler warnings.

The resource recreation check destroys/recreates renderer objects in a live GL context. It does not simulate GPU device loss. The reset check verifies persistence/lifecycle and continued output, not a complete reset-image equivalence campaign. Native FPS is reported by the core; real frontend refresh/audio synchronization affects wall-clock speed. Sustained performance and gameplay accuracy need separate measurements.

## Native Texture Filtering Follow-Up — 2026-10-20

Implemented the approved Nearest/Bilinear/Trilinear selector with Nearest as default, matching both modern and legacy raw-value/default registration. The existing renderer sources remain unchanged.

- ROM-free ABI/legacy registration check passed (`audit/filter-abi.log`).
- Default-mode VF2 RAM and PCM remain exactly equal to pristine upstream at 900 frames (`audit/native-filter-default/comparison.json`).
- Three independent 1800-frame VF2 runs produced distinct scene images for Nearest, Bilinear and Trilinear, with identical main RAM and PCM across all three (`audit/native-filter-comparison.json` and `audit/filter-*/`).
- Each run also exercised live Bilinear/Trilinear changes, invalid-value fallback, resolution change, graphics-resource recreation, reset and reload without GL errors.

These are graphics-harness and ABI results. The real RetroArch menu checks above predate this added selector; no additional native menu observation or physical controller test is claimed for this follow-up. Shared controls such as Gamepad Rumble and NVRAM Settings remain explicitly pending in the roadmap.

## Complete SM2 Applicability Probe — 2026-10-20

An unchanged-source compile/link probe reused the live reference `nvram_settings.cpp`, `initial_nvram.cpp` and `save_ram.cpp`, with their existing generated catalogues/templates. The test uses a 16-KiB view of destination backup RAM plus its 128-byte EEPROM and preserves the remaining 48 KiB. No source-core code or user saves were changed.

VF2: native destination capture accepted; existing template accepted; 8 reference options / 19 values applied with valid checksums/layout and preserved tail. Sega Rally: the existing 900-frame capture was not accepted by SM2's layout validator, but the existing reference template and all 6 options / 21 values were accepted. No cause is assigned to the rejected capture and no new acquisition campaign is inferred.

Evidence: `port/build-libretro-macos/audit/sm2-applicability/{build.log,vf2.json,srallyc.json}`. Probe source: `scripts/probe-sm2-nvram.cpp`. Complete source applicability and catalogue inventory are in `SM2_APPLICABILITY.md` and `SM2_REFERENCE_INVENTORY.json`. These checks establish reusable NVRAM logic at the memory-view boundary; no new core-option runtime delivery or game acceptance is claimed.

## Native Image And Keyboard Selectors — 2026-10-20

Seven additional native selectors are integrated: Shadows And Fences, Saturation, Gamma Red/Green/Blue, Keyboard Shifter and Hold Gears. V2/legacy registration now contains nine options; numeric colour selectors retain the native 0.50–2.00 range with 0.05 steps and default 1.00. Shadows now defaults to the actual standalone Blend mode, correcting the initial adapter's implicit Checker value.

The default-mode 900-frame VF2 RAM and PCM match pristine upstream exactly (`audit/native-options-default/comparison.json`). Independent 1800-frame captures for saturation and each gamma channel differ from baseline while RAM/PCM remain identical. The selected scene shows no Blend/Checker pixel difference; an OpenGL observer verifies that the actual meshblend uniform receives the selected mode during polygon drawing (`audit/native-mesh-gpu-default/check.log`, `audit/native-mesh-gpu-checker/check.log`). Live filter/colour/mesh changes, invalid colour fallback, reset, GL recreation and reload pass. This does not establish physical keyboard driving behavior or real-frontend menu validation for these new selectors.

The full native inventory, frontend-owned controls and pending native implementation are recorded in NATIVE_OPTIONS.md. Native completion is the active priority before additional common SM2 features.

## SM2-Style Video And Keyboard Policy Update

`port/build-libretro-macos/audit/sm2-video-style-vf2/comparison.json` records exact 900-frame RAM/PCM equality against pristine same-revision upstream with identical initial NVRAM. The OpenGL harness covers separate Aspect Ratio and Widescreen Mode, including 16:10, explicit 4:3 suppression, wide-aspect stretch without expansion, Auto selection and invalid-token defaults. Direct keyboard device polling is rejected by the harness. ABI legacy registration passes with eleven video controls and two system gates before content selection. Physical controller testing and audible verification remain separate.

## MAME ROM Set Alignment

The compiled catalogue check validates 28 canonical MAME entries against pinned driver source, every consumed filename/size/CRC tuple, main-program identities, unchanged native input/hook wiring and independent 29-entry standalone behavior. ROM-free stored/deflated ZIP fixtures exercise canonical-parent and merged-path lookup. `audit/mame-aligned-daytona` and `audit/mame-aligned-vf2` both pass 900-frame exact RAM/PCM comparisons against pristine upstream with identical initial NVRAM. `audit/mame-aligned-daytona93` loads the canonical MAME set with its corrected audio revision and displays the 3D attract scene. The latter is not an old-audio equivalence test. Full evidence boundaries and source provenance are in MAME_ROMSET_ALIGNMENT.md.

## SM2 NVRAM Menu Conformance

The ROM-free bridge check verifies exactly one correctly marked (Default) value for each of the 340 operator definitions, master hidden before content/without a catalogue/after unload, master visible with a catalogue, operator fields gated by Enabled and the active catalogue, and unchanged display state returning no refresh request. Existing paused-edit retention, apply-once, checksum/template and backup-tail preservation checks still pass. The exported 353-definition registry preserves every previous key, raw value and default token. Pipeline changes only its explanatory help text.

## SM2-Only Initial NVRAM Setup

The native Daytona fallback call was removed from the Libretro load path by user decision. The bridge check verifies exact `daytona93` seeding, explicitly compatible `daytonam` parent seeding, and unchanged backup/EEPROM for `daytonat` and `daytonata`, whose identities have no approved SM2 template. Existing Disabled-gate, checksum, paused-edit and backup-tail checks remain covered. The standalone helper is unchanged.

## Installed Development Core In Local RetroArch

By explicit user request, the development dylib and matching info were copied into the active configured RetroArch directories; source and installed SHA-256 match. A third file, the core-specific `config/Model2EmuEx/Model2EmuEx.cfg`, sets only `video_driver = "gl"`; the global configuration remains unchanged. Initial isolated launch from Vulkan without an override selected glcore and failed, even though RetroArch returned exit 0. The runner now rejects a missing required final screenshot and isolates the info cache as well as options/saves. `audit/installed-core-retroarch-override-vf2` passes 900 frames from a Vulkan base configuration with the gl core override, exits normally, and produces an inspected 3D VF2 attract screenshot. This is actual frontend rendering from the installed binary, not physical-controller or audible-output proof. The installation manifest records hashes and destinations.

## Updated Local Copy And Runner Isolation

The user-authorized local core was updated with shared input, rumble, gains, 60 Hz/Native timing and crosshairs, with a backup of the previous copy. `audit/shared-features-installed-retroarch-vf2` passes 900 real RetroArch frames, 60.00 Hz / 44,100 Hz metadata, 3D attract rendering, isolated SRAM and exit 0. Core Options persisted the expected `60hz`, `sm2`, `enabled` rumble and `auto` gain values. The global config hash remained `3f6734f47d8d6eeb9e94472906a1c7464e1b6356c8ae70f375a90c119d788f3b`.

That run revealed frontend runtime-log entries outside the isolated output directory. The runner now disables both runtime-log modes and explicitly scopes runtime/playlist directories. Existing external runtime records were not deleted or rewritten to conceal the earlier entry. Source tests, ROM-free CRC fixtures and the final installed-copy frontend result are separate records; see the installation manifest for binary hashes/backups.

Final installed-copy verification: `audit/shared-crc-installed-retroarch-vf2` passes 900 frames with the final CRC/menu build, normal exit, 60.00 Hz / 44,100 Hz metadata and a captured 3D attract image. No runtime-log save is emitted by the corrected runner. Installed/source dylib SHA-256 is `e2c025361f7a5b7e4980c2753227bab2c089ed0f558c1e15ef6ea5afe726bd2d`; global configuration hash is unchanged. `audit/shared-crc-native-vf2` again matches pristine RAM/PCM exactly.

## Timing / FPS Overlay And Roadmap Update — 2026-10-20

M20 is delivered locally. The SM2 panel and 61-frame aggregation policy are adapted to native machine/video/audio work and the current 60/58 Hz caption; the existing bundled ImGui is compiled into the core. No native machine source or external dependency changes were needed. See TIMING_OVERLAY.md for the measurement definitions and limits.

- Full bridge/input tests, known-sample timing mean/max/capacity/lifecycle checks, imported SM2 panel/scaling tests, legacy/V2 option defaults/order and standalone build pass. The registered inventory is 39 general selectors plus 340 operator fields.
- `audit/timing-overlay-layout-vf2`: Off/Auto/11–14 px/invalid values, 4x layout, frame skips, context recreation, reset and reload pass the actual GL harness. Warmup resolves the initial auto-fit clipping retained in `audit/timing-overlay-vf2`. Inspected screenshots show complete text at 1x and 4x.
- Overlay On/Off main RAM and PCM are identical at 900 frames/60 Hz. `audit/timing-overlay-native-vf2` remains byte-identical to pristine upstream for RAM and PCM under Native timing.
- `audit/timing-overlay-retroarch-vf2` and `timing-overlay-installed-retroarch-vf2`: 900 real RetroArch frames with isolated Auto selection, sampled timing logs, complete overlay in the final 3D attract screenshot and exit 0. Installed/source SHA-256 is `6ee60103f4482ad9c93f71a3323b77a4326a9f3d50e91d09787177a959be9cae`; the production configuration hash is unchanged. No runtime-log save is emitted and the normal Core Options file is not edited.
- ABI exports remain Libretro-only; linked dependencies remain system zlib/libSystem/libc++. GPU execution, physical devices, other platforms and sustained performance are not inferred from these diagnostic checks.

ROADMAP.md now follows the common presentation: legend, icon-only status cells, Activity/Remaining Work columns, status grouping and stable IDs. It is the sole implementation roadmap; the separate inventories retain their reference role. The current group is complete, and work stops for the requested summary. M22 Hide Shot Flash was initially listed next, without claiming implementation or beginning another group; the subsequent explicit exclusion below supersedes that selection. No commit or push was performed.


## Hide Shot Flash Scope Exclusion — 2026-10-20

By explicit user instruction, Hide Shot Flash and its selector are excluded from the port. M22 was removed from the operational roadmap, its ID remains reserved, and the option/applicability inventories and workspace guidance now record the exclusion. No source code or registered option changed; no build or runtime retest was required. No new functional group was started, and no commit or push was performed.

## M12 — Save States — 2026-10-20

SM2's native/frontend separation, state validation/rollback and recovery conventions plus Framework F12 were used as references. The complete destination implementation and format are documented in SAVE_STATES.md. No Core Option was added; the `.info` now advertises Save States.

Final core SHA-256: `742192cec335c3e02026280378f4313066dca26eb8775bcdef39b893a8cfd848`. Only Libretro ABI symbols are exported; dynamic dependencies remain system zlib/libSystem/libc++. The standalone/headless build and complete common input/NVRAM/rumble/timing/ABI checks pass. The new ROM-free native regression verifies writable i960 cached displacements against changed backing RAM, rebound operands and identical cycle charge.

| Evidence Directory Under `port/build-libretro-macos/audit` | Result |
| --- | --- |
| `states-accepted-vf2` | 1,800 scripted paid-match frames at 60 Hz/Pipeline Enabled, four exact 12-frame state/PCM/image continuations, reverse-order restoration, cold save/load, GL context recreation and fresh-process full-state equality. Current enabled NVRAM overrides trigger one effective reset; Disabled preserves the snapshot. |
| `states-accepted-daytona` | 1,800 frames under Native timing/Pipeline Disabled; equivalent exact continuation and fresh-process tests cover the original Model 2 MultiPCM/YM3438 sound board. This is attract-mode verification, not driving gameplay. |
| Both Native Harness Runs | Null/undersized/truncated/corrupt data, wrong game/board/ROM/version/ABI, a well-checksummed invalid i960 frame-cache index and a well-checksummed header/payload frame-counter mismatch are refused without changing the serialized machine. The last case exercises actual rollback after the commit pass. |
| `states-accepted-pristine` | VF2 at 900 Native frames remains byte-identical to same-revision pristine upstream: RAM `c213a5cba382d13e08a75a079ece268ddc8e175d79e9e2d3ebfe84c4bc1e9993`, PCM `ff48a0eb0bbdb607ba9844551a65edf41152c273c42ba61b50646de3860f8753`. |
| `states-frame4-retroarch-daytona` | Final build, RetroArch 1.22.2, default 60 Hz/Pipeline Enabled. Slot file 12,582,936 bytes includes the 12,582,912-byte core MEM chunk. Save/load log messages, changing attract scene, exactly restored OSD-free game region at verified machine frame 1,156, resumed scene advancement, exit 0 and no forced termination. |

The normal installed development core and matching info were updated under the user's existing local-copy authorization; its backup and installation receipt remain in `audit/local-retroarch-install`. Global configuration and normal saves/options are not modified. The installed-core VF2 frontend receipt is `states-accepted-retroarch-vf2/result.json`: both paths reach verified machine frame 1,156; the game-region pixels match exactly, the scene advances before and after restoration, both log confirmations are present, exit is 0 and no forced termination is needed. The same final core hash is used in both native and both frontend receipts. `save-states-acceptance.json` consolidates the checks, installed hashes and normal exit of the owned frontend processes.

### Retained Diagnostics And Correction

`states-first-vf2` retains the restricted SDL display failure; the display-enabled rerun passes. Early format-development runs remain local diagnostics, not a compatibility promise. `states-closure-retroarch-daytona` retains a failed screenshot comparison based on unverified simulated-key advancement. `states-frame-retroarch-daytona`, `states-frame2-retroarch-daytona` and `states-frame3-retroarch-daytona` retain failed diagnostic-slot probes: this installed frontend lacks the newer `SAVE_STATE_SLOT` command, and the alternate paused-slot/key probes did not create the requested diagnostic save. None is counted as a pass.

The accepted runner uses `FRAMEADVANCE`, a bounded optional native frame trace and matching actual machine counters. It requires the reference to advance by exactly three machine frames, adjusts the restored path to that same counter, then checks pixels and subsequent advancement. Separately, source review found that CPU-side tile/palette version counters could equal old GPU versions after rebuilding tile state; `m2gl_invalidate` now forces complete derived uploads without GL calls during restoration. Accepted native and frontend results cover that final build.

Cross-cadence loading was separately exercised in `states-cross-timing-vf2`: a 60 Hz snapshot runs under the current Native selection with native scheduling preserved. That diagnostic predates the final metadata/video-cache changes and is not presented as a final-artifact replay receipt.

No cross-platform or SM2/legacy-state compatibility, all-game gameplay, physical devices, audible fidelity, actual GPU loss or synchronized linked-session restoration is claimed. Repeated ABI restores do not establish the frontend's rewind/run-ahead UI behavior. No commit or push.

## Sega Rally Audio Stream-Termination Correction — 2026-10-21

See [Sega Rally Audio Diagnostic](AUDIO_SRALLYC_DIAGNOSTIC.md). The initial 3,600-frame Native PCM matched pristine, establishing the old baseline. Slot-level traces subsequently reproduce premature stream stops with the native 16-sample SCSP schedule. A credit-associated stream lasts 86.85 ms versus SM2's 458.32 ms; the corrected one-sample SCSP schedule restores 458.32 ms. Three other traced stream durations also match SM2 after correction. The Model 1 sound-board schedule is unchanged.

`make check-sound` proves callback-size-invariant PCM for a ROM-free delayed-key-on program; the old scheduler fails. Core and adapted standalone builds pass and their corrected 3,600-frame Native PCM is identical. Save State restore reproduces 12 subsequent frames of active SCSP PCM exactly. Source/installed core SHA-256: `ed28974be3fc383e2b3784fd201ae6ad838e7b8adf8df76a049f31f2d091d943`; the prior installed binary is backed up in the ignored diagnostic directory. Pristine is untouched. Active SCSP PCM intentionally differs from the historical pristine baseline.

Evidence: `port/build-libretro-macos/audit/srallyc-audio-quick-20261021/`, especially `streaming-comparison.json`, `trace-fixed.log`, `sm2-replay.log`, `state-fixed.log` and `deployment.json`. Complete SM2 sound timing, subjective listening, paid gameplay and real audio-device playback remain unqualified. No commit or push.

## Sega Rally EEPROM And Cached Save State Availability — 2026-10-21

See [NVRAM And Save State Diagnostic](NVRAM_SAVESTATE_DIAGNOSTIC.md). A valid Export EEPROM was present but native 93C46 framing rejected leading idle zeroes. The frontend-neutral start-bit correction now shows Export on a fresh core Service Menu run and USA under the explicit NVRAM override. A pin-level ROM-free regression fails before and passes after the correction. Existing user save and global configuration hashes are unchanged.

The global Core Info cache retained the original Development/no-Save-States entry with support level 0. The target entry and installed `.info` were refreshed to the implemented serialized capability, preserving other core entries. The serializer itself passed actual installed-core RetroArch save/load before that refresh. The corrected build passes exact same/fresh-process and context-recreation continuation. Final installed SHA-256: `29b2fd66531019d0241579998e7bd574b8edf54e3adca22ef09d312f01115518`.

The navigator voice is user-confirmed correct. Upper-sky black geometry remains an open normal-gameplay report, independently of Save State loading. No fix for that image artifact is claimed here.

Final installed-core frontend receipt: `audit/srallyc-eeprom-cached-retroarch-20261021/result.json`. RetroArch used a copy of the refreshed global cache (serialized support level 2); save/load, exact restored pixels after three controlled machine steps, resumed advancement and clean exit all pass. This qualifies the corrected artifact and catalogue together.

## Sega Rally Upper-Sky Backdrop — 2026-10-21

The supplied state (frame 5,421) reproduces the upper black region without shaders. The renderer incorrectly cleared to black instead of the hardware palette pen 0, as implemented in current SM2 and MAME. Corrected in the shared native renderer; presentation bars stay black. See [Sky Diagnostic](SKY_SRALLYC_DIAGNOSTIC.md).

The ROM-free `make check-render-background` regression fails for the old clear and passes for palette updates, black bars, scale/cache/context recreation. Before/after images differ only at 2,336 previously black upper pixels; RAM and PCM remain exact. Four same-process state continuations and fresh-process/context-recreation continuation pass from the user's supplied state. Core and standalone builds pass. Installed/build SHA-256: `501d0da93f5bb217689c6f3c41e8aef1c4c65acc4e4296c822f1ed8fdaecbece`; user state/SRAM/configuration remain untouched. Evidence: `audit/srallyc-sky-state-20261021/` and `audit/srallyc-sky-state-replay-20261021/result.json`. No commit or push.

## M13 — External Linked Cabinets (2026-10-21)

See [External Linked Cabinets](EXTERNAL_LINKED_CABINETS.md) for reference pins, the evidence ledger and the all-set local loopback policy (the earlier Rally-specific acceptance is retained below as historical evidence). ROM-free native ring/SM2 transport checks and ASan/UBSan pass; existing common checks and validated Daytona I/O lane synchronization pass. Four working-family core ABI checks cover independent ANRS authority, re-entrant publication, combined reset, handover, frontend-client retention and linked state rejection. APIs 2/1/0 are exercised.

Two isolated RetroArch instances form native Daytona IDs 1/2, show UP TO 2 RACERS WANTED and reach a common two-player race (host 2nd/2, client 1st/2). Sega Rally rebuilds its native ring after staggered RESET commands with no new lobby. All owned instances exit 0 without forced kill. Higher totals, remote hosts/other platforms, relays, completed races and physical controls are unqualified. These are not whole-catalogue multiplayer claims.

VF2 offline Save States pass the same/fresh-process GL continuation, context reconstruction, invalid-state rejection/rollback and enabled-NVRAM-authority regression after this integration (`audit/m13-state-vf2-final/result.json`). The first attempt only failed its reset-message counter after the notification was renamed; the established NVRAM notification was restored and the unchanged behavioral checks pass. The native state format and capacity remain unchanged.

### M13 Local Loopback Completion — 2026-10-21

The approved srallyc/srallycb local board is integrated. Both revisions pass extended offline Master/Slave persistence, Restart/reload, manual handover and local state continuation through the actual core ABI. The matched before/after result reproduces the old Notlink rewrite and its correction; unrelated VF2 900-frame RAM/PCM/NVRAM are unchanged. Native/SM2 transport checks and ASan/UBSan pass, including local data/heartbeat and no Slave promotion. Standalone/headless and all existing common checks pass.

The active Master local-board GL test passes four exact continuations, corruption/rollback, context recreation and fresh-process replay. The user's pre-loopback state also loads and resumes exactly. Actual RetroArch with the final installed core creates the state, advances, restores the exact frame 1447 image, resumes and exits 0 without forced kill. The 12 MiB buffer and payload layout remain; new local states have a checked LNK1/ABI-feature header extension which older readers reject. Audit roots: m13-loopback-abi-persistent, m13-loopback-clone-abi, m13-loopback-state-master, m13-loopback-legacy-user-state, m13-loopback-retroarch-state, m13-loopback-comparison and m13-loopback-install. This completes the group; larger/remote rings, live lobby option editing and physical-device qualification remain in M14/M16.

### M13 All-Set Local Fitting Alignment — 2026-10-21

The later user decision extends SM2's fitted local-board policy to every catalog entry. `configure_network` now unconditionally selects `M2_NET_LOOPBACK` for one cabinet; the native enable bit still controls operation. Source review covers all 28 entries through that shared path, including preparation for Model 2B/2C. This does not add external support or alter roles, defaults or the external branch. The initial exhaustive runtime campaign was stopped at the user's direction; it is not required to establish this shared source policy and is not claimed as whole-catalog qualification.

Existing native/network/I/O, common ABI/input/NVRAM/timing/state checks and standalone builds pass. F05 APIs 2/1/0 and four-family F14 authority/lifecycle regressions pass. A targeted VF2 GL test with Pipeline enabled passes exact state continuation, invalid-state rejection/rollback, context recreation, NVRAM authority and fresh-process replay. The installed core also passes a real RetroArch 1.22.2 VF2 Save/Load: advancement, exact restored image at matched machine frame 1461, resumed execution, exit 0, no forced termination.

Current build/installed SHA256: `7d113892c9f24bc7b3fa1eb11e904b3e4e2a703fdfb36d808ccddb17dec4c684`. Evidence, old-core backup and installation receipt are under `audit/m13-catalog-loopback/`; the global frontend configuration was hash-checked unchanged. See [External Linked Cabinets](EXTERNAL_LINKED_CABINETS.md) for individual receipts and state-header compatibility. No commit or push.


## M23 — NVRAM Source Review And Evidence Index (2026-10-22)

See [NVRAM Source Review](NVRAM_SOURCE_REVIEW.md). Current SM2 source, not the
shared workbook, defines this implementation comparison. All 13 inspected
imported modules/data files match current source and recorded import hashes;
extracted label/help functions are unchanged. Actual Core Options V2
registration and the exported inventory match all 340 fields/56 catalogs in
keys, labels, ordered values and defaults. The 28 destination sets resolve to
19 applicable catalogs/117 distinct fields, 22 exact templates and four
explicitly compatible parent routes. The two Turbo sets retain no approved
initial template.

ROM-free checks validate decoding, layout/integrity, initial policy and extra
backup-tail preservation for 25 non-prototype entries with templates, including
prepared Model 2B/2C data. Daytona93 metadata remains indexed without new
prototype qualification. No ROM, game execution, new sample campaign or
workbook recreation was required. Existing SM2 sample/recipe/YAML evidence and
actual destination ABI/frontend receipts are indexed separately. All 120 VF2
artifacts referenced through historical temporary paths were located in the
permanent campaign directories without modifying that campaign.

Evidence: `audit/m23-source-review-20261022-complete/report.json` and repeatable
`scripts/audit-nvram-source.py` / `scripts/audit-nvram-source.cpp`. The first
registration comparison needed SM2's Title Case formatter rather than raw
native uppercase labels; that audit comparison was corrected, not core data.
The final report passes. Source review found a separate robustness gap:
initial-template seed errors can be silent and post-seed policy errors are
ignored in the adapter, whereas SM2 rejects them. Checked current templates
are valid; the error-handling follow-up is recorded in M25.

Only audit tools/documentation changed. Core hash remains
`7d113892c9f24bc7b3fa1eb11e904b3e4e2a703fdfb36d808ccddb17dec4c684`;
no local core replacement or new runtime acceptance is claimed. No commit or push.


### Immediate Initial NVRAM Error Alignment — 2026-10-22

The source-review finding above was corrected immediately, superseding its M25
deferral. `sm2lr_initial_nvram` preserves distinct no-op, loaded, invalid-template
and invalid-layout results. The caller reports SM2's error text and rejects and
cleans up content on invalid initialization; it synchronizes native I/O only
on a successful seed. Current SM2 seed/apply guards are preserved, including
an empty operator catalog. Standalone helpers, imported templates, valid-save
precedence, raw SRAM format, selectors and defaults are unchanged.

The actual-core fixture test corrupts only isolated copies: invalid template
CRC and post-decode native-layout mismatch both reject load with the expected
frontend message and released Save RAM. Disabled setup loads in both cases;
normal enabled setup loads with production data. These are five targeted load
checks, with zero native frames and no mutation of production templates, ROMs
or saves. Existing common bridge/input/timing/native-state/ABI checks pass.

Evidence: `audit/nvram-initial-errors-20261022/{fixtures-final/result.json,common-final.log}`.
Build/installed core hash:
`80670ced8e9fba92e8f459d6961cc053086d1a95b2e83b84127a9da3fda51091`.
Atomic installation backup/receipt: `install-final/deployment.json` under the same
root. Global RetroArch configuration is hash-checked unchanged. The isolated
900-frame installed-core VF2 frontend receipt is `retroarch-vf2-final/result.json`.
No new all-game, physical-device or audible-fidelity claim. No commit or push.


## M24 — Cabinet Audio And Applicable Extensions (2026-10-22)

Current SM2 Manx TT policy, menu, donor precedence, optional-chip fallback,
additional native M1 board, full bidirectional I8251, SCSP return wire, AMS and
Save State continuation are integrated. Other destination sets retain native
sound behavior. No current catalog entry declares a further DSB/DSB2 or Power
Sled sound extension. Details and source hashes are in
[Manx TT Cabinet Audio](MANX_TT_CABINET_AUDIO.md) and `port/snd/sm2/IMPORT.json`.

The ignored evidence index is `audit/m24-manxtt/result.json`:

- Synthetic chips prove bank changes, incomplete EEPROM handling, no NVRAM
  writes, extra PCM contribution, source mute, serial round trips, mixer/state
  continuation, ROM identity checks and fallback notices.
- `frontend-final/result.json` checks real-core options and lifecycle, legacy
  state reading/new-state rejection by the old core, and successful loading
  with auxiliary chips removed from an isolated archive copy. Production
  archives are unchanged. VF2 RAM, SRAM and PCM match the pre-M24 core for
  900 frames.
- Twin and active Deluxe OpenGL runs pass four exact 12-frame continuations,
  damage/identity rejection and fresh-process recovery after 900 boot frames.
  The final installed binary additionally passes the same state suite after
  60 Deluxe boot frames (`state-final/result.json`), including both sound
  boards, pointer rebinding and context recreation.
- Real RetroArch: `retroarch-deluxe` reaches a visually inspected 3D attract
  scene after 1,200 frames. `installed-final` loads `manxttc` with Deluxe sound
  donors for 900 frames, reports the additional board connected, renders an
  inspected attract title screen and exits 0. These are attract/rendering and
  execution evidence, not physical controls, audible accuracy or gameplay.
- Native/core/standalone builds, sound scheduling, EEPROM/AMS I/O, network,
  common SM2 checks and initial-template error regressions pass. No dependency
  was installed. The core links libz, libc++ and libSystem, with no SDL runtime.

Final installed/source SHA256: `234d6b9c01c88f953bcbf7f9da1a79687e8262878fdc7acacb5468c1b6452949`.
The matching `.info` remains `007cdcfa819eb3aa63a287f7ed2325d5627b41e1cf44b50637788ca1530dbd8b`.
`audit/m24-manxtt/final-install/deployment.json` records backups and exact
paths; the first installation receipt retains the pre-M24 core. Global
RetroArch configuration and the scoped GL override hashes remain unchanged.
Listening, physical controls and extended gameplay remain M14 qualification.


## M25 — Analysis Of Frontend Error Handling And Recovery (2026-10-22)

Analysis only; the source and installed core remain unchanged at SHA256
`234d6b9c01c88f953bcbf7f9da1a79687e8262878fdc7acacb5468c1b6452949`.
No implementation, build, deployment, commit or push occurred in this review.
See [Frontend Contract Review](FRONTEND_CONTRACT_REVIEW.md) for exact source
comparisons, findings and compatibility decisions.

The ignored `audit/m25-analysis/result.json` records actual-core ABI probes:
unknown content has no core OSD detail; missing GL procedures do not request
shutdown and another callback still delivers 735 PCM frames; invalid audio
acceptance requests shutdown without OSD detail; invalid network values remain
stored with no correction writes; a raw all-A5 SRAM buffer is accepted intact.
These are injected frontend conditions, not actual RetroArch rendering or a
physical GPU-loss test.

One targeted VF2 run reproduces the lost pending override: automatic seeding
Disabled, NVRAM Settings Enabled, Difficulty Hard, 600 frames. The resulting
layout is valid but still Normal. A copy passed to the unchanged reference
engine changes to Hard; changing unrelated Pipeline then causes the actual
core to apply Hard and reset once. This is separate from M23's already-fixed
initial-template fatal-result handling. No new NVRAM campaign or catalog-wide
launches were performed.

The companion probe includes live SM2 option readers and verifies two queued
network corrections/warnings. Its unchanged imported Save RAM implementation
accepts a valid SM2 container and rejects wrong-game and corrupted payload
fixtures. Source equality and working-copy hashes are recorded in
`audit/m25-analysis/sources.json`. Lost-context abandonment and immediate fatal
rumble cleanup differences are source findings; physical effects were not
qualified. Existing announced-recreation and M12/M24 state evidence remains
valid for its stated scope. The review identifies required fixes; it does not
claim that they have been delivered.


### M25 Save RAM Policy Resolution — 2026-10-22

The user selected native standalone-compatible raw Save RAM, conditional on
established use in other cores. Snes9x directly exposes Memory.SRAM and Genesis
Plus GX directly exposes sram.sram via RETRO_MEMORY_SAVE_RAM; source links are
recorded in FRONTEND_CONTRACT_REVIEW.md. Keep the existing 65,664-byte backup
RAM/EEPROM layout, matching native DAT content. The all-A5 diagnostic documents
raw storage rather than a defective container. No SM2 envelope, new checksum,
format selector or migration is pending. Native checks and the independently
reproduced late-override defect remain separate. No source/binary/deployment
change was needed to retain this format.

## M25 — Libretro Adapter Bug Fixes (2026-11-02)

The four adapter omissions from the earlier analysis are corrected; they do not
replace Model2EmuEx emulation with SM2. Existing raw Save RAM, selectors/defaults,
sound synthesis and emulated rendering are preserved. Full implementation,
reference behavior and limits are in FRONTEND_CONTRACT_REVIEW.md.

- `audit/m25-contracts-accepted-20261102/result.json` and
  `audit/m25-contracts-pipeline-20261102/result.json`: extended/legacy error
  notifications, fatal GPU/audio stop, reentrant deferred network corrections,
  late NVRAM retry with one reset, live changes and cancellation pass with
  synchronous execution and native Pipeline Enabled. The 600-frame warning
  timeout is source-reviewed, not forced by this probe.
- `audit/m25-gl-accepted-20261102/run.log`: replacement GL context without a
  destroy callback, no stale texture/buffer/FBO/program deletes, active overlay
  resources and visible rendering recovery pass. Physical device loss remains
  unqualified.
- `audit/m25-state-vf2-20261102/result.json`: four exact same-process
  continuations, cold and fresh-process loads, invalid-state rejection,
  announced context recreation and current NVRAM authority pass.
  `audit/m25-state-manxtt-20261102/result.json` confirms the final core also
  preserves guarded Deluxe cabinet-audio state continuation.
- `audit/m25-network-20261102/results.json`: existing F05/F14 checks pass for
  Daytona, Sega Rally and Manx TT; no catalogue-wide gameplay claim.
- Common/reference input, timing, bridge and ABI checks, native EEPROM/AMS,
  SCSP callback-size invariance and transport regressions pass. Both core and
  preserved standalone targets build. Final common receipt:
  `audit/m25-contracts-accepted-20261102/common.log`.
- `audit/m25-local-install-20261102/deployment.json`: atomic update of the
  already authorized development core, previous binary retained, matching info
  and current user configuration/GL override hashes unchanged.
  `audit/m25-installed-retroarch-20261102/result.json`: final installed core
  renders inspected VF2 3D attract output for 900 frames in real RetroArch,
  exits normally and uses isolated settings/saves. This is not paid gameplay,
  audible-output or physical-device proof.

Final build/installed SHA256:
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.


No ROM copies, production save writes, reference-checkout changes, commit or
push were performed. M25 closes at this scope; wider device/platform and
destination NVRAM qualification remain separate roadmap activities.

## M26 — Static Source Provenance And Notices (2026-11-02)

The static review used existing import metadata, source headers, Git objects,
local donor files and component notices. All 40 prior import files were present;
38 destination hashes matched and two adapted Netpacket entries retained their
donor digests. Their metadata now records exact donor and destination identities
separately. The referenced BSD notice was absent and is retained unchanged from
the existing SM2 donor; all 41 resulting imports verify. All 36 entries now
declared unchanged, both pinned I8251 files and the API header match their donor.
The Netpacket donor hashes also match committed SM2 revision
`be696244fc425f55e3c0cab9bc43c03d44b621aa`.

Executable source hashes, native Git HEAD/status and the installed M25 binary
are unchanged. The only protected-tree modifications are the existing import
metadata and Core Information attribution, plus the newly retained license text.
The installed matching `.info` was updated atomically after preserving its old
copy; current frontend config/GL override and core binary hashes remain intact.
No frontend cache refresh or runtime-visibility claim is made.

Receipts: `audit/m26-source-review-20261102/{result.json,info-update.json}`.
Current attribution and publication limits are in LIBRETRO.md and
LIBRETRO_DESIGN.md. The native baseline has no root license file, so project-level
terms for recovered ElSemi code and original adapter remain unresolved. No
blanket license was added. M26 stays partial for that publication prerequisite.
No merge, build, game run, ROM/save change, commit or push was performed.

## M11 — NVRAM Adapter And Frontend Persistence (2026-11-02)

`audit/m11-persistence-20261102/result.json` consolidates these checks:

- Current SM2 source/import and actual registration match: 340 fields and 56
  catalogs, using the existing source audit and evidence index.
- The destination bridge matches explicit calls to the unchanged SM2 engine
  for 526 value cases on 25 eligible sets/18 catalogs. Checksums/layout,
  disabled/no-op behavior and the additional 48 KiB backup tail are preserved.
  Two Turbo sets retain no-template preservation; Daytona93 remains metadata
  only. This catalogue-wide check runs no ROMs or native games.
- Actual-core ABI checks preserve an entire 65,664-byte raw fixture on fresh
  load with automatic setup enabled and disabled. Operator overrides retain
  authority, tail/EEPROM preservation and one live reset.
- Two fresh real RetroArch sessions run VF2 for 900 frames each. Existing raw
  Save RAM wins over automatic setup; Hard, native size and the extra-RAM marker
  survive both sessions. The second reads the first session's persisted file.
  `frontend-persistence.json` records isolated save hashes and normal exits.

These establish M11's adapter and representative frontend persistence contract.
Per-title native Service Menu/sample acceptance, gameplay and future-board
execution remain M14 qualification. Photographic/native campaign acceptance
is not inferred from a matching memory image. The SM2 implementation and
existing accepted samples/templates are reused unchanged.

Only reusable test tools and documentation changed; no core fix, binary
replacement, new ROM copy, production save/configuration write, commit or push.
Source/installed core SHA256 remains
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.

## M10 — Independent Native Audio Gains (2026-11-02)

`make check-sound` now includes `scripts/check-audio-gains.c`, a synthetic-signal
test using the actual adapter option readers and existing native sound code.
No game ROM, frontend session or audio device is used. The adapter is included
in the test executable to inspect its real readers without adding a diagnostic
ABI to the core. Only the test target/tools and documentation changed.

Receipt: `audit/m10-audio-gains-20261102/{result.json,check-sound.log}`.
Four main-board source paths (SCSP, MultiPCM 1/2, YM3438) and three auxiliary M1
source paths pass 98 gain/fallback comparisons and six mixed-source isolation
checks. Native constructor output is the reference, before option reads; each
variant restores an identical native snapshot so undefined 68000 power-on
register values do not contaminate synthesis-state comparison.

- Auto, 100%, missing and invalid values preserve native output exactly.
- Mute yields zero; every 10–100% selection scales its own signal with at most
  one integer sample unit of native rounding. Fixture peaks stay below clipping.
- CPU/chip state after each gain variant equals the unmuted state. Muting and
  later re-enabling output resumes the exact expected PCM continuation.
- Other-source controls do not alter the active source; with all original-board
  sources active, removing each contribution affects only that source, within
  the native mix's single-unit rounding bound.
- Sound reset retains the selected gain. The auxiliary test uses the real
  `m2snd_run_aux` scheduler and extended native sound-state archive.
- Existing SCSP callback-size invariance still passes.

M10's implemented Gain/Mute and A/V Timing contract is complete; existing cadence,
partial-batch and frontend evidence remains valid for its recorded scope.
Speaker/device playback, additional per-game listening and complete native
sound-timing accuracy are not inferred from these synthetic signals. No SM2
synthesis/filtering behavior was imported. The core implementation and installed
binary remain unchanged; no game run, production data write, commit or push.

## M18 — Representative RetroArch Crosshair Checks (2026-11-02)

Evidence: `audit/m18-crosshairs-20261102/result.json`, session manifests/logs,
`auto-fallback.json`, screenshots, timed capture indexes and pixel reports.
RetroArch 1.22.2 (`fce35fc7`), Cocoa/OpenGL, installed arm64 core SHA-256
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.
Only Virtua Cop was used; its ROM archive was read directly from external
storage. No ROM copies were made. Keyboard events were mapped by the isolated
frontend to controller inputs; the core still polls no keyboard device.

The imported `crosshair.cpp` and `crosshair.h` remain byte-identical to current
SM2-Libretro. No renderer, input implementation, menu option or native emulation
code changed. The existing runner gained optional bounded interactive runs,
frontend settings and a read-only existing System resources path. Saves,
states, options, info/cache, logs and screenshots remained in new test folders.

| Check | Evidence And Result |
| --- | --- |
| Independent Aiming And Visibility | Frontend analog bindings moved P1 and P2 separately. `retroarch/screenshots/menu-input.png`, `player1-only.png`, `player2-only.png` and `disabled.png` show both masks, each individual mask and complete external-reticle hiding. P1-only contains 2,712 green pixels and no cyan; P2-only contains 2,632 cyan pixels and no green; Disabled contains neither. |
| Live Style | The real Core Options menu changed SM2-Emu to Supermodel without restarting content. `supermodel-both.png` shows the red P1 and green P2 vector reticles instead of SM2's green/cyan rings. |
| Auto Without Artwork | Two bounded 900-frame runs exited 0. In the 96 × 96 centre region, the green reticle masks contain the same 2,600 pixels and have identical SHA-256 `708ef1226d96078283dc996ebd96544722b8b4cc1030fffe782e0aaf9bab7ef9`. Whole game images differ between the independent boots; no whole-frame or machine-frame parity is inferred from RetroArch's frame limit. |
| Independent Inactivity | With the real `2`-second selector, timed captures show the reactivated P1 marker in `lifecycle/timeout/22.png`, absent again in `24.png`. The separate retained P2 pair is `timeout-p2/22.png` and `24.png`; cyan appears only after P2 activity, while P1 remains hidden. These are approximately one-second samples, not a sub-frame timing measurement. |
| Save State Aim And Option Authority | The first session saved Supermodel-style content with separated aims. After the second session had moved both aims to opposite edges, loading that state restored the original aim centres: P1 `(528, 287.5)` and P2 `(1469, 1055.5)` in the 2048 × 1536 screenshot. The retained `lifecycle/state-restored/25.png` shows current SM2 green/cyan styles and the current timeout, rather than the style used at save time. This proves aim restoration/current presentation authority, not an exact full-game-image round-trip. |
| Player PNGs | Synthetic 5 × 5 RGBA fixtures in the task-owned System directory produce distinct P1/P2 images. `custom/screenshots/custom-saved.png` contains 64 P1 fixture-colour pixels and 72 P2 fixture-colour pixels at separate positions. Existing source/GL alpha and fallback tests retain their original scope. |
| Actual Restart | The earlier `lifecycle/restart` remote-command capture did **not** execute Restart while frontend confirmation was enabled and is not acceptance evidence. In the Custom session, native Command → Reset with isolated `confirm_reset=false` logged `[Core] Reset` and reset aim. `custom-restart.png` shows the retained P2 image centred at `(1023.5, 767.5)`; P2 covers P1 when both solid fixtures overlap. |

### Probe And Session Limits

A supplementary exact-frame PNG Save State probe was not completed: the live
native-frame log remained buffered while paused, and a replacement repeated
remote-save probe did not receive a new state file. Native-menu Save State
succeeded and produced a 12,582,936-byte RetroArch container. This attempt is not
an exact-image Save State pass and does not replace earlier M12 continuation
receipts. The narrower aim/style restoration above is independently supported
by the second session's visible positions and pixel reports.

The first interactive session reached its 900-second bound and required
SIGTERM; the second session quit normally through the native app menu (exit 0,
no timeout). The Custom session reached its 600-second bound and exited 0 after
the runner's QUIT, so its manifest still correctly records a timeout. The two
Auto/SM2 batch runs each exited 0 within their bounds. Only owned processes were
closed. A key in the second isolated configuration also selected a frontend
bilinear shader; that session supplies position/visibility evidence, not pixel
parity with the first session. The Custom and Auto/SM2 checks disabled those
conflicting frontend hotkeys.

All 197 protected file hashes, including machine/adapter sources, built and
installed core, installed info, global RetroArch configuration and scoped GL
override, remained unchanged. The pristine standalone checkout's HEAD and
working-tree status were unchanged. No dependency was installed and no commit
or push was made. Physical lightgun/controller precision, other games/frontends
and broader runtime qualification remain M14; no new native emulation fix is
justified by these presentation checks or by the probe limitations.


## M08 — Native Input Test Checks (2026-11-02)

The installed, unchanged arm64 core (`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`) ran in RetroArch 1.22.2 `fce35fc7`, Cocoa/OpenGL. ROMs were read directly from the existing external archive. Current SM2 `input.cpp`/`input.h` match the imported files byte-for-byte. Existing input-reference and adapter executables pass, including all 28 destination profiles, native VF2 wiring, profile gating and paused refresh at the adapter level.

`scripts/check-retroarch-inputs.py` reuses SM2's replay-v1 record layout and reader padding, feeding actual frontend input callbacks through `scripts/run-retroarch-macos.py --replay`. Two bounded automated runs exited 0 without timeout. Captured native Test Menu glyphs were reviewed against their rendered templates; process exit alone is not input acceptance. Receipts are under ignored `port/build-libretro-macos/audit/m08-inputs-20261102/` (`result.json`, each replay's `accepted.json`, screenshots and native-value readings).

| Native Input Test | Verified Responses |
| --- | --- |
| Sega Rally (`srallyc`), 15 Cases | Steering 00H/80H/FFH; accelerator and brake 00H/80H/FFH; handbrake lane literally labelled HANDLE(DRIVE), 00H/FFH; four separate gear contacts, Neutral, VR, Service and analog return to idle. Gear latching is independent of analog release. |
| Virtua Fighter 2 (`vf2`), 18 Cases | Each player's Punch, Kick, Guard and four directions independently ON with other gameplay contacts OFF; independent P1/P2 Start; Service and release. |

Current source and observed native menu entry use L3 = Service, R3 = Test. Historical diagnostic YAML labels reverse these names and are not authoritative. Test keyboard events used frontend controller remapping; no core keyboard device was added. Keyboard remapping did not supply analog trigger pressure, so replay callbacks supplied the tested half/full pressure values. These are scripted frontend checks, not physical-controller, calibration, sustained-gameplay or whole-catalog acceptance. Sega Rally Start/Coin are not newly qualified by these receipts.

The exploratory Sega Rally session reached its 900-second bound and exited 0 after the watchdog QUIT; its timeout remains recorded. A separate VF2 profile session entered the native Input Test and opened the frontend menu, but UI access lost its window before the Normal selector was changed. It was closed normally (exit 0, no timeout). That attempt ended before the live change and paused-menu metadata refresh. The November 14 follow-up below completed the frontend check. No core implementation change was justified; only reusable test tooling and documentation changed.

### Post-Test Artifact Retention

At the user's request, cleanup covered only this M08 audit and the preceding M18 audit plus explicitly named task-owned temporary files. It removed 1,004 files and 496,291,840 allocated bytes (approximately 473 MiB). `m08-inputs-20261102/cleanup.json` records every removal and 154 retained-file hashes, verified after cleanup. All 197 protected source/core/configuration hashes and the pristine sibling checkout remained unchanged.

Retained evidence includes the accepted M08 screenshots, recipes, native-value receipts and logs; M18 visibility/style keyframes, timeout pairs (22/24), restored-aim frame 25, custom artwork/restart and Auto fallback images; and one useful `vcop.state`. Redundant raw screenshot sequences, duplicate/failed state probes, regenerable replay files and temporary OCR/compiler outputs were removed. Earlier capture counts describe acquisition, not retained file counts. No ROM, user save, unrelated process, core binary or global frontend setting was removed or changed. No commit or push was made.


### VF2 Live Profile Change And Face Buttons — 2026-11-14

RetroArch 1.22.2 on Apple Silicon ran VF2 Version 2.1 from the archive with isolated settings. A replay held P1 RetroPad A and L3 throughout the change. With **Normal + Test/Service**, the native Input Test displayed KICK ON and SERVICE SW ON. While the content was paused, changing **Core Options → Input → Controller Profile Type** to **Normal** updated **Controls → Port 1 Controls → Device Type** to **Joystick (Standard): Fighting**. The log records renewed controller and descriptor registrations. On resume, KICK remained ON and SERVICE SW went OFF. The frontend saved `normal` and exited normally. This run used the pre-correction installed core.

The gameplay contact also exposed a wiring error. The earlier screenshots showed that all three contacts could activate, but did not verify the correspondence between each replay button and the native row at a known frame. The following pairs were held from frontend frame 1560 and captured at frame 2050. Each entry gives the ON action for P1 and P2 respectively.

| RetroPad P1 / P2 | Before | Corrected |
| --- | --- | --- |
| A / B | Kick / Guard | Punch / Kick |
| Y / A | Punch / Kick | Guard / Punch |
| B / Y | Guard / Punch | Kick / Guard |

VF2 needs no rotation after SM2 polling. The destination adapter now keeps bits 0/1/2 for Punch/Kick/Guard for the parent and its three revisions. The adapter regression checks all three buttons on both ports for all four sets. Frontend evidence covers the parent with scripted inputs. Small before/after PNGs and the run receipts are retained in `port/build-libretro-macos/audit/m08-live-profile-20261114/`.

## First Release Build And Packaging — 2026-11-02

The user authorized repository creation, commit, push and first release. Version
0.1.0 identifies the independent port, not an inferred upstream release. Runtime
identity and Core Info agree. The macOS release uses the existing native source
and a 13.0 deployment target; architecture is arm64 and all runtime dependencies
are system libraries. Only the 25 Libretro ABI symbols are exported. The ROM-free
ABI/options/rejected-content check passes. No new emulation behavior is added by
the release version/build metadata; prior frontend evidence retains its scope.

The SM2-style five-platform Linux/macOS/Windows Actions workflow builds on
main/PR/manual/tag events, verifies
architecture, ABI, version, dependencies and package hashes, retains the exact
committed source archive and publishes version-tag assets only after successful
checks. Local and CI use the same Makefile and package script. CI does not run
ROMs or establish physical-device/gameplay acceptance. See the public
[workflow runs](https://github.com/Zer0one/Model2EmuEx-libretro/actions/workflows/libretro-ci.yml)
for actual remote results; prepared automation alone is not a successful run.
The locally installed development core/configuration are not replaced by this
release operation. Generated archives remain under ignored build directories.

First public preflight run `41422257254` built all five targets. Linux x86_64,
Linux ARM64 and macOS arm64 completed package checks. Two packaging-boundary
issues were retained as failures: Intel libc++ emitted public RTTI symbols,
and newer Windows objdump output included an additional ordinal field. The
macOS link now uses the explicit 25-symbol ABI list, and PE export inspection
reads the actual name column. Neither change alters emulation. The subsequent
Actions run must pass before the first version tag is created. Inherited native
standalone Actions remain separate from the new Libretro release workflow.

### M27 Model 2B Catalogue And Gameplay — 2026-11-03

The 52-set Libretro catalogue passes the compiled metadata and archive tests
against the pinned MAME driver. Model 2B coverage is 26/35 set definitions:
two existing sets, 22 original records recovered outside the exported game
list, and two MAME revisions with checked donor layouts. See
[MAME ROM Set Alignment](MAME_ROMSET_ALIGNMENT.md) for the remaining sets and
their scope. The 29-set standalone table still matches the pristine checkout.

Using the opt-in macOS research core and ROMs read directly from the archive:
Indy 500 reaches 3D attract in actual RetroArch at frame 1,800 with normal exit.
Its ABI/GL Save State test and Fighting Vipers' scripted 4,800-frame combat
test both pass exact fresh-process continuation. Over Rev Revision B reaches
a race with analog pedal input; at frame 3,600 the capture shows 149 km/h and
lap 1/3. Its same-process state test reproduces four 12-frame continuations
exactly. These are bounded gameplay and state checks with synthetic input.
Receipts are in the ignored `port/build-sharc-machine/model2b-catalog/`.

All 26 catalogue Model 2B sets load their required files directly from the
archive with computed payload CRC verification. In isolated RetroArch runs
of the two donor-based revisions, Over Rev Revision A reaches 3D attract;
Rail Chase 2 `rchase2a` reaches the motion-board network check at frame 1,500.
The SM2 machine source confirms that the game requires motion-board responses
on ports D/E. This set is catalogued but gameplay is not qualified.

macOS Apple Silicon and Intel (Rosetta) and Linux x86-64 builds pass the
Libretro ABI check. The Linux x86-64 mapped-machine state test also passes.
Windows x86-64 and Linux ARM64 builds remain open: no toolchains for those
targets were found in the current local builder. No dependencies were installed.

### M27 Rail Chase 2 Motion Board — 2026-11-03

Both revisions previously remained at the drive-board network check. The
original `004c8b30` routine identifies four command/reply pairs; SM2 confirms
the port D read and port E command mapping. The machine returns those four
acknowledgements using the existing serialized command latch. No Save State
field was added. The reply is scoped to the two Model 2B Rail Chase 2 sets.

Both sets reach 3D attract in isolated macOS RetroArch after 1,800 frames
and exit normally. The parent also reaches a paid game with scripted input
in the GL harness. A state taken after 2,400 frames passes four exact 12-frame
continuations and exact continuation in a fresh process; stereo PCM CRC
`0e701e3f` for 8,820 frames. macOS default/research builds, research ABI and
the ROM-free SHARC machine test pass. Evidence: `rchase2-motion-v2`,
`rchase2a-motion-v2` and `rchase2-motion-state` in the catalogue test directory.
No physical motion base or lightgun was tested.


### M28 Dynamite Cop Protection And Projection Centers

- `port/build-sharc-machine/model2c-protection.json`: 67,120 original executions,
  134,240 portable comparisons and 1,306 constant comparisons. Commands include
  the entire 16-bit domain; scope is physical-width results and mutable globals.
- `port/build-tgpx4-machine/model2c-protection-check.log`: real i960 pages/widths,
  response aliases, native reset persistence and fresh-device state continuation.
  Maximum synthetic M2C machine payload is 11,919,304 bytes within 16 MiB.
- `dynamcopc-catalog-retroarch-1800` and `-3600`: pre-fix advisory screen, not
  successful attract evidence. `dynamcopc-native-protection-gpu-1800`: accepted
  3D introduction, 1,800 frames, 34.62 s, exit 0. The first sandbox-only attempt
  (`dynamcopc-native-protection-retroarch-1800`) exited before logs/rendering;
  it is not a core qualification result.
- `dynamcopc-native-protection-abi-states/result.json`: four exact replays,
  cold load, context recreation, rejection and fresh-process continuation pass.
- `dynamcopc-native-protection-retroarch-states/result.json`: exact restored
  region at frame 1,888, advancement before/after, Save/Load logs and clean exit.
  Region SHA-256 `5693c829678dc05010fc86cbe440585104be570f571ad8fc9d89f81204f3136b`.
  These protection receipts use core
  `d4a4ce5b396e809fbed0863fcd95f2594ad9f4250d5cf04a3644feef0ed0cc60`, before
  the following projection-center change.
- `hotdo-catalog-retroarch-1800`: separate House Of The Dead 3D attract,
  1,800 frames, 33.68 s, exit 0. No gameplay/audio claim.
- `port/build-sharc-machine/model2c-geometry-center.json`: 6,252 native fragment
  executions / 12,504 O0/O2 comparisons. `model2c-center-check.log`: low/high
  selector integration and frame-snapshot isolation pass alongside machine tests.

All named frontend receipt directories above are under
`port/build-tgpx4-machine`. The original protection arithmetic can read outside
its identified table; pure-helper tests and machine mapping coverage are distinct.
See MODEL2C_ANALYSIS.md for the explicit unrecovered-memory boundary. No ROMs
were copied and no installed core or user state was changed.


### M28 Linux x86-64 And Native Batocera Samples

The opt-in `SHARC=1 TGPX4=1` core builds with the existing GCC 15/Bookworm
builder and the normal project optimization flags. ABI loading, machine-state
and geometry fixtures pass on Linux x86-64. ELF architecture/dependencies are
recorded in `port/build-tgpx4-machine/linux-build.log`; no missing dependency is
reported. `linux-source-manifest.json` identifies the explicit 489-file source
snapshot, which excludes ROMs, original binaries and local test outputs.

The exported core SHA-256 is
`6ea7ecf38cbb58b0fa4ec844e04111644a4c28da21663e280143b3fefb319608`.
Two isolated native Batocera runs reuse existing read-only content:

- `batocera-dynamcopc`: 2,400 frames, 59.68 s, 3D ship/helicopter introduction,
  exit 0 and an isolated 65,664-byte Save RAM file.
- `batocera-topskatr`: 2,400 frames, 67.20 s, textured skateboard attract shot,
  exit 0 and an isolated 65,664-byte Save RAM file.

Both reports retain identical before/after hashes for the ROM, installed
configuration and shared-save sentinels. They do not qualify physical controls,
audible output or full gameplay. The macOS projection-center follow-up also
renders the Dynamite Cop introduction and exits after 1,800 frames (34.63 s),
using core `762d82fb7214e71d2eaf10fe973e76dfd1afe9b946fa30ae7bce5e4c5f5dfef2`.


### M28 Windows And Shared Frontend Review

The Windows x86-64 opt-in core builds with the existing MSYS2/MinGW toolchain
in the isolated Windows 11 ARM Fusion VM and passes ABI loading. Dynamite Cop
renders its 3D introduction for 1,800 frames and exits with code 0. The ROM is
read directly from `K:/Retro/_Media/_Multi (MAME)/roms/dynamcopc.zip`; no ROM copy
was made. Audio is disabled for this visual test. Evidence is in
`port/build-tgpx4-machine/windows-results`, including the build log, core hash,
selected path and final screenshot. DLL SHA-256:
`06ba579482fa3a1946f405bade3c8d6778c5886c4049a8b5ba04080f23b74935`.
This is Windows x86-64 execution under Windows ARM translation, not physical
x86 Windows hardware evidence.

The destination input fixture now checks the current **70-set** catalog and
identifies actual M2C boards correctly. All profiles bind to the unchanged SM2
implementation and the existing input-wiring checks pass. The dedicated
`check-sm2-bridge --model2c` run passes **13 template routes / 236 value cases**,
including parent/revision routing, checksum validation, repeated application,
disabled gates and preservation of the extra backup RAM. Logs:
`model2c-input-profiles.log` and `model2c-nvram-profiles.log`.

At that checkpoint the unrestricted common suite was **not passing**: it exposed a shared SM2
catalog conflict on `sfight`, ENERGY(1P)=Hard with ENERGY(VS)=Normal. Both
reference and adapter report Changed on repeated application. The source engine
is byte-identical to the current SM2 source; patches 26 and 27 overlap at backup
byte 0x3354 (masks 0x30 and 0x7c). The failing assertion is retained and now logs
the game/field/reference result. No NVRAM behavior was changed. By user decision
on 2026-11-04, this was investigated separately after M2C (M29), with the
correction and complete-suite repeat recorded below. The historical M2C-scoped
pass must not be presented as a full-suite pass.

### M28 Scripted Gameplay And Completion Review

`port/build-tgpx4-machine/dynamcopc-native-play-states/result.json` records
6,000 frames with the established coin/Start/action replay. The inspected
`same-process/core.png` shows the defeated player in a rendered room and the
Continue countdown: the test advanced into actual play beyond the introduction.
Four same-process continuations and a fresh-process 12-frame continuation match
RAM, device state, PCM and rendered output exactly. Cold load, context recreation
and invalid-state rejection also pass. This is scripted gameplay evidence;
physical controls, audible fidelity and completion of the game are not tested.

Core SHA-256:
`762d82fb7214e71d2eaf10fe973e76dfd1afe9b946fa30ae7bce5e4c5f5dfef2`.
State SHA-256:
`55f8a80ac4837688631bb8109408233c65ec1bb3a90b5f56460db83a098fb08d`.
No unrecovered protection or shared-memory read was encountered. This does not
remove the explicit unmapped-memory boundary described in MODEL2C_ANALYSIS.md.

The final native configuration review distinguishes D3D depth/presentation
controls from recovered machine/display-list behavior. Existing upstream GL
depth/sort, CRTC offsets and SCSP sample scheduling remain unchanged. The
reviewed hooks, consumers and limits are tabulated in MODEL2C_ANALYSIS.md.
Known M28 reconstruction/integration work is complete; broader M14 qualification,
M16 distribution enablement and the user-separated M29 NVRAM issue remain distinct.

Completion cleanup removed 39 generated replay-state/full-run PCM files
(474.3 MiB) from the isolated M28 test directories. Results, logs, screenshots,
continuation fingerprints and PCM, configurations and synthetic Save RAM remain.
The final Dynamite Cop gameplay state and Top Skater RetroArch state are retained
for reproduction. `port/build-tgpx4-machine/cleanup-result.json` records the
removed-file hashes and the two retained-state hashes. No production/user save,
ROM, original executable or source file was removed. Historical commands in the
receipts refer to these now-pruned generated files; rerunning recreates them.

### M29 Correction And M2C Integration Completion — 2026-11-04

Existing SM2 Sonic samples and Service Menu screenshots were reused read-only.
The original game lookup/store fragments were executed under the existing i960
interpreter for all eight values in each of `schamp` and `sfight`; both native
callbacks share backup word 0x3354. This is game-code execution, not an x86
Windows-emulator oracle. The user approved preserving that quirk with updates
only on selector changes, in native menu order. See NVRAM_SOURCE_REVIEW.md.

The corrected complete common suite passes: 67 destination NVRAM routes / 3,035
value cases, all 70 input bindings, timing, native state and ABI checks. The
new Sonic regression covers 1,536 transition/partial-selection cases and proves
repeat idempotence, full-word updates, integrity and unrelated-byte preservation.
The source/registration audit passes 340 fields / 56 catalogs, with the two
local corrections recorded and pinned rather than claimed identical to SM2.
Logs: `port/build-m29-nvram/common-suite-final.log`, `source-review/report.json`.

Real macOS RetroArch tests use the canonical release-build core, isolated files
and the original archive ROM path:

| Run Under `port/build-m29-nvram` | Result |
|---|---|
| `schamp-hard-normal` | 2,100 frames, 39.48 seconds, normal exit; Service Menu shows ENERGY(1P)=Hard and ENERGY(VS)=Normal, raw save has selectors 2/1 and derived word 144 |
| `schamp-reload-disabled` | Fresh process from that isolated save, NVRAM overrides disabled; 2,100 frames, 38.65 seconds, normal exit; same visible values and derived word 144 |
| `m2c-release-frontend` | Dynamite Cop 1,800 frames, 34.08 seconds, normal exit; inspected screenshot shows the rendered 3D introduction |

The native raw save remains 65,664 bytes. `frontend-verification.json` records
Sonic save/image hashes. These runs do not qualify physical input or audible
output. No ROM or campaign artifact was copied or modified; the baseline's
extracted NVRAM was converted only into a new isolated test save.

The macOS release build (`make SHARC=1 TGPX4=1 release -j4`) and release ABI check
pass. Core SHA-256:
`7d25037ff2e9e8053fee95a041aad4f0787f01f65f7c4f5f0e669ea3e94cb0b4`.
The three ROM-free gates newly added to the distribution recipe also pass on
macOS: SHARC machine, TGPX4 machine and TGPX4 geometry, all in a combined build.
Logs: `release-build.log`, `release-abi.log`, `ci-machine.log` under the same root.

The pending five-platform CI recipe enables `SHARC=1 TGPX4=1` explicitly;
metadata/manuals now describe the available Model 2C implementation. Ordinary
local defaults remain opt-in. No workflow run, commit, push, release or installed
core replacement occurred. Matching-source release packaging still requires a
clean committed tree by its established design; that gate has not been bypassed.
The earlier Linux/Batocera/Windows results qualify the M2C machine implementation;
they do not claim execution of the newly edited CI workflow or the Sonic
correction on every platform.

### Override Reapplication After Native Service Edits

The follow-up used the same unmodified release-build core and isolated macOS
RetroArch sessions. Starting from Hard/Normal with overrides enabled, scripted
native Service/Test input changed both selectors to Hardest/Hard, exited Game
Assignments and exited Test Mode. The process ran 3,835 frames (68.04 seconds),
returned to attract, and exited normally. Its raw save contains selectors 3/2
and shared word 180, proving that native edits were committed.

A fresh process loaded that exact isolated save with NVRAM Settings still
enabled and frontend selections Hard/Normal. After 2,100 frames (38.85 seconds,
normal exit), the inspected Service Menu shows Hard/Normal and the saved
selectors are 2/1. The shared word is 200: both selectors changed during
reapplication, so the approved menu-order policy runs 1P then VS. This differs
from the earlier 144 without contradicting the independent gameplay lookup
path. Both raw saves are 65,664 bytes.

Evidence: `port/build-m29-nvram/schamp-native-edit`,
`schamp-reassert-overrides` and `override-reassertion.json`. This closes the
reported next-load authority concern for the tested `schamp` path. Restart also
marks NVRAM pending in source, but no new warm-Restart frontend run is claimed.
The earlier disabled-override reload is retained as a separate persistence test.
No additional core change was required. M29's targeted correction/acceptance is
complete; broader per-game gameplay qualification remains M14.

### Top Skater Same-Input Pre-Backend Geometry Comparison — 2026-11-04

The user requested the M2B-style renderer-integration check after the CPU/driver
qualification. The existing M2B capture hooks were reused in an isolated copy
of pinned ElSemi 1.1a on the Windows 11 ARM VMware guest. They capture the list
at `0x4baa60` and the four existing DrawPrimitiveUP call sites before D3D9
consumes vertices. A single native screenshot gate identifies the corresponding
completed geometry slot (gate 1795, slot 7). No batches were dropped. ROMs were
read directly from the existing `K:` archive; no ROMs were copied.

The first diagnostic preparation used Windows resource updating for an app-local
XAudio2 manifest and produced an invalid diagnostic PE, before emulation began.
The accepted second preparation keeps the original PE section layout and stores
the manifest in unused diagnostic-section bytes; it does not modify rendering
instructions. XAudio2 is activated through the local manifest without registry
writes. Exact pinned-original-to-probe byte changes and hashes are retained in
`original-probe-patch.json`. This is an instrumented original executable, not an
unmodified-file claim; original rendering algorithms remain unchanged.

A diagnostic copy of the current macOS release adapter replays that exact 512 KiB
list, its start offset, and seven captured video RAM banks into a shadow board at
OpenGL draw 1792. Existing native Model 2C flags and the normal upstream compiler
options are retained. The production adapter, renderer and installed core are
unchanged. The captured replay list matches the original input byte for byte.
The two isolated local runs complete 1,800 frames and exit normally.

| Spatial Correspondence Metric | Free-Running Core | Exact-List Replay |
|---|---:|---:|
| Original Interior Vertex Occurrences | 2,753 | 2,753 |
| Within 1 Pixel, No Position Adjustment | 1,115 | 2,753 |
| Within 1/16 Pixel, No Position Adjustment | 3 | 2,753 |
| Replay RMS Error | — | 0.0000184831 px |
| Replay Maximum Error | — | 0.0001012343 px |

The original submits 2,815 triangles; the replayed core submits 1,571, reflecting
separate clipping/tessellation boundaries. As in the accepted M2B comparison,
this is a screen-space nearest-neighbor check of original vertex occurrences
strictly inside the native 496x384 viewport, using vertex data collected before
the graphics backends. Repeated occurrences count separately. It does not prove
matching topology, UV/color attributes, sort order, border clipping, full
persistent geometrizer state or pixel identity. No pixel-equivalence gate was
reintroduced. The retained images are contextual evidence, not the pass metric.

The targeted M2C geometry-integration check passes without a production code
change. This closes the additional comparison requested by the user; general
M14 qualification and M16 distribution gates retain their previous scope.
Evidence: `port/build-m2c-geometry/comparison.json`, `capture.json`,
`probe-provenance.json`, original batch/list/video inputs, core meshes, isolated
run receipts and diagnostic sources. No commit, push, release or installed-core
replacement occurred.

Completion cleanup removed 32,097,408 bytes of task-owned generated binaries,
duplicate captures and unused geometry slots locally, retaining the selected
input/batch data, comparison meshes, screenshots, logs, source and exact PE patch
recipe. `port/build-m2c-geometry/cleanup.json` records hashes and reproduction
limits. The two task-owned Windows test directories were removed with the
standard runner after evidence retrieval. The canonical release-core SHA-256
remains `7d25037ff2e9e8053fee95a041aad4f0787f01f65f7c4f5f0e669ea3e94cb0b4`.

User-directed retention update, 2026-11-04: retain only results and reusable
verification tools for the Top Skater comparison. Raw captures, replay inputs
and generated test saves have now been removed; numerical results, contextual
images, logs, diagnostic source and the executable patch recipe remain. The
receipt is `port/build-m2c-geometry/results-tools-only-cleanup.json`. Repeating
the comparison requires a new acquisition; the previous retained-input rerun
is historical evidence, not a claim that those inputs remain available.


## Model 2C Release Delivery — v0.3.0, 2026-11-04

The authorized delivery is published as
[v0.3.0](https://github.com/Zer0one/Model2EmuEx-libretro/releases/tag/v0.3.0),
from commit `b7776e215ef520cabd775099ea1b1d15373a03b5`.

- [Main Libretro CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/41792231825)
  and [tag Libretro CI](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/41792907701)
  pass for Linux x86-64/ARM64, macOS Apple Silicon/Intel and Windows x86-64.
  Every platform enables `SHARC=1 TGPX4=1` and passes native SHARC machine,
  TGPx4 machine/geometry, ABI and release-package gates.
- Standalone Linux, Windows and Android regression builds pass on
  [main](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/41792231984)
  and [tag](https://github.com/Zer0one/Model2EmuEx-libretro/actions/runs/41792907704).
- All seven public assets were downloaded after publication. Outer checksums,
  every ZIP member checksum, all five platform/version identities, canonical
  core/info names, clean provenance and exact Git source archive pass.
  Corresponding source SHA-256:
  `a940cc7990061fd9681a985469e7c26c841b3a92e66d6efcd58765f79989daf8`.
- The official Linux x86-64 ZIP SHA-256 is
  `52bf0d87fd18a099684a056b29b96a5b7baefad4f1141a62935c85c8a2eb2267`;
  its core SHA-256 is
  `c0eb1a611819cc8624dec61181583e6e7617831be34dc65de9ff41ef457703be`.

Local receipts and the reusable public-asset verifier are in
`port/build-v030-results/`. These are distribution checks, not additional
frontend/gameplay or physical-device evidence. No installed RetroArch core or
pristine standalone file was changed by this delivery. The latest geometry
comparison retains results and reusable tools only, as requested above.


## Original Emulator Inventory And Boundary Probes — 2026-11-04

The user authorized general RE inventory and the two M2C memory investigations
following v0.3.0. [Original Reconstruction Inventory](RE_INVENTORY.md) records
source classification, native addresses, exact domains and reproduction tools.

- The source index covers all 2,048 inherited function-export rows, including
  named exception handlers, plus 319 additional targeted-decompile addresses.
  Lexical references and pointer candidates are explicitly not completion proof.
- Twenty-one focused original executions pass: three geometry-command pointer
  updates, ten protection-selector responses and eight shared-memory boundary
  cases. The complete 65,536-selector domain is enumerated arithmetically.
- One A68K initializer execution matches all 65,536 independently expanded
  opcode pointers. The table has 1,667 distinct executable targets, none listed
  in the inherited function export. This proves dispatch identity only.
- The first boundary probe ended in the sandbox before emitting a receipt;
  accepted Unicorn JIT executions outside the sandbox complete normally.

Evidence: `port/build-re-inventory/` contains JSON receipts and focused
original disassemblies. Tools are `tools/original_inventory.py`,
`tools/check_original_boundaries.py` and `tools/a68k_inventory.py`.
No ROMs, game sessions, VM/production installations or raw memory dumps are
involved. The production change only clarifies the native command-0x0d comment;
no build or gameplay claim follows from this group.


## Inherited Model 2/2A Qualification — 2026-11-04

See [Inherited Model 2/2A Qualification](M2A_RE_QUALIFICATION.md) for exact
scope, reproduction and oracle limitations. Accepted local receipts are in
`port/build-m2a-re/`.

- i960: 47,113 comparisons over six seeds, all 153 opcodes plus interrupt;
  887 exclusions. The inherited ARM64 baseline had 133 NaN-sign mismatches;
  the corrected core has zero, with unchanged seeds/exclusions.
- TGP interpreter: 18,161 comparisons, zero mismatches, 1,839 exclusions,
  using the inherited Unicorn FLD test flag. The actual production library
  exposes four documented SNaN quiet-bit oracle discrepancies in seed 1.
- Production TGP driver: 23,104 calls in 900 sequences, zero failures and no
  unmodelled-access reports.
- Physical AMD executes ten unchanged original i960 FP bodies for 16,317
  vectors. All raw result bytes match corrected ARM64 Clang O0/O2 and native
  x86-64 GCC O2. The prior port had 1,448 NaN-bit mismatches in this edge suite.
- Both Model 2/2A board integration fixtures pass upload, 43 FIFO transfers,
  shared/data RAM and complete fresh-machine restoration. Combined TGP,
  SHARC, TGPx4 and geometry checks pass on macOS; full core build and ABI pass.
- CI now includes the TGP machine gate; remote CI has not run for this tree.
  A supplementary Linux machine build was unavailable in the generic builder
  because zlib headers were absent; no package was installed and no Linux
  machine-pass claim is made. Native Linux FP compilation/execution passed.

No new gameplay, audio or pixel-equivalence claim follows. The pristine
standalone and installed RetroArch core are unchanged. No commit/push/release.


## Original Audio Classification — 2026-11-04

[Original Audio Reconstruction Boundaries](AUDIO_RE_ANALYSIS.md) records the
scope and reproduction. `port/build-audio-re/audio-inventory.json` retains:

- All 65,536 A68K dispatch entries classified against the existing Musashi
  disassembler: 1,667 targets, 120 label categories, 1,635 single-label and
  32 mixed-label targets. DC labels are not hardware-invalid conclusions.
- Eighty original MOVEQ-body executions (40 pairs) confirm identical register,
  selected flag, PC and cycle effects with opcode bit 8 clear/set. The initial
  fixture lacked stack setup for PUSHF; it was corrected before the accepted
  run. No whole CPU, game reachability or audible-impact claim follows.
- 642 original SCSP decoder executions match 25 reviewed fields; six start
  cases match the last nonzero program position, including empty/full edges.
- 69 original DSP generator captures pass with only VirtualAlloc/VirtualFree
  fixtures. Empty output is nine bytes; the 128-step all-fields fixture emits
  28,958 bytes in the original 64 KiB allocation. Generated bodies are hashed,
  not executed or compared with the current DSP interpreter in this group.

The existing disassembler's dump mode and the A68K dispatch refactor are
checked separately. Results, provenance and tools are retained; the temporary
binary and redundant synthetic/disassembler files are removed. No production
emulation changes, installed-core update, ROM copies, commit, push or release.


## SCSP DSP Arithmetic And Writeback — 2026-11-04

`tools/scsp_dsp_compare.py` executes the original generator and emitted x86
under Unicorn and compares persistent state against production `dsp_step`
through the test-only `port/snd/test/scsp_dsp_shim.c`.

- 252 multiply/shift cases, 512 arithmetic-selection cases and 256 eight-step
  feedback chains: **1,020 cases, zero mismatches**, at both Clang O0 and O2.
- 935 cases change TEMP/MEMS/effects; all 252 multiply/shift cases additionally
  pass an independent scalar expectation. Input, generated-code and result
  aggregate hashes coincide between both builds.
- Compared TEMP, MEMS, DEC, MIXS and EFREG. Zero initial scratch, valid
  MEMS/TEMP inputs and zero MIXS/EXTS bound this evidence. No sample RAM,
  cross-sample scratch, final PCM, IRQ/timing or whole-chip equivalence claim.
- Original host allocator imports use the existing fixture; original generator
  and generated instructions are unchanged. This is not native CPU execution.

See [Original Audio Reconstruction Boundaries](AUDIO_RE_ANALYSIS.md) for
reproduction. Receipts/provenance remain in `port/build-scsp-dsp/`; reusable
tools remain, temporary libraries/debug bundles are removed. Production audio,
installed core and ROMs are untouched. No commit/push/release.


## Recovered DSP Memory And Lifecycle — 2026-11-04

The test-only C translation of native generator semantics matches all **1,439
cases** against original emitted x86 under Unicorn at Clang O0, O2 and O2 with
UBSan on the recovered implementation. No sanitizer diagnostics. Persistent
state, native scratch and RAM match; 40 address traces also meet independent
expectations. The suite includes the previous 1,020 arithmetic cases plus
reads/writes, memory chains, sample continuation, raw inputs, combined access,
stopped/program-length edges and compile-time lookahead. See
[AUDIO_RE_ANALYSIS.md](AUDIO_RE_ANALYSIS.md) for counts and scope.

The unchanged portable DSP differs in 359 cases; 20 compare raw input fields
without mixer normalization. These are behavioral observations, not automatic
ElSemi bug diagnoses. Reconstruction intentionally preserves native quirks;
corrections require a separate evidence-backed decision. Out-of-buffer native
addresses fail the research fixture rather than silently acquiring a production
fallback policy. Full input/mixer representation, memory escapes, cached-program
lifecycle, Save States and actual PCM/frontend integration remain open.

The full O2 receipt, matching compact O0/UBSan receipts and provenance remain in
ignored `port/build-scsp-dsp/`. Source tools are retained; generated binaries,
objects and debug bundles are removed. No production audio changes, installed
core update, ROM copies, commit, push or release.


## Recovered DSP Integration Preparation — 2026-11-04

- Extracted `scsp_dsp_original.c/.h`; the oracle shim calls that same module.
  All 1,439 differential cases retain the previous exact hashes.
- `check_dsp_lifecycle.c` passes under ASan/UBSan: native defaults, private RAM,
  cross-sample scratch, cached MPRO despite later backing writes, nonmutating
  preflight, exact fresh-instance continuation, explicit recompilation,
  corrupt/truncated archive rejection, bounds report and reinitialization.
- 18,432 mixer-boundary cases match unchanged original integer fragments:
  16,384 input and 2,048 output cases. The captured integer tables are generated
  by native initialization under Unicorn x87; this is not physical-x86 or
  full-chip PCM evidence.
- Eight native word/byte probes confirm start at BFE, not BF0. A synthetic
  guard proves a native read at byte 1,171,454 beyond the 1 MiB allocation;
  no game reachability claim follows. The user subsequently approved explicit
  address diagnostics and content stop.

Results/log/provenance remain under ignored `port/build-scsp-dsp/`. The working
SCSP path, both Makefiles and frontend fault propagation are now wired. The
macOS SHARC/TGPX4 core builds and `check-sound` passes. The SCSP archive adds ABI
feature bit `0x08000000`; full-core state capacity/continuation and PCM/frontend
verification remain open. No installed-core update, commit, push or ROM copies.

## Original DSP Save State Audit — 2026-11-04

Disassembled native save/load, raw registrations, four CPU callback pairs and
the board post-load hook. `tools/scsp_dsp_state_audit.py` captures 15 raw and
four CPU descriptors from unchanged native registration fragments. Its native
raw-load traversal passes four checks: first sound-RAM 64 KiB restored; remaining
960 KiB untouched; DSP context untouched; private DSP RAM untouched. The original
allocates 1 MiB sound RAM but registers only 64 KiB as `M2SCSP`. The separate
DSP context/private RAM/generated code are not included in the traced archive.
The post-load hook invalidates graphics resources, not DSP state. See
AUDIO_RE_ANALYSIS.md for addresses, callback/disassembly scope and reproduction.

Receipt: `port/build-scsp-dsp/original-state-audit.json`. Synthetic-memory
Unicorn probe; no Windows frontend, game reachability or audible-continuity
claim. Native Save States provide no recovery rule for escaped DSP addresses.

## Recovered DSP Integrated Core Qualification — 2026-11-04

- Integrated oracle: 1,439 cases, zero recovered/original mismatches; previous
  MAME comparator still differs in 359 cases. Receipt `integrated-comparison.json`.
- macOS Libretro SHARC/TGPX4 and standalone `m2emu`/`m2run` builds pass.
- `check-sound` passes, including the new bus/mixer/archive/adapter DSP fixture:
  nonzero DSP-only PCM, BFE/BFF distinction, cached program, fresh sound-instance
  continuation, nonmutating preflight, escaped address `0x01ffc000`, frozen/silent
  fault state, exact frontend diagnostic, shutdown once and reset recovery.
  The first fixture attempt omitted `retro_init`; the corrected lifecycle
  registers the notification sink and passes. No core change was needed for it.
- VF2: 1,800 scripted frames, 8,871,140 used bytes in 12 MiB.
- Indy 500: 900 frames, 9,338,940 used bytes in 16 MiB.
- Top Skater: 900 frames, 9,519,948 used bytes in 16 MiB.
- All three pass cold states, four exact 12-frame RAM/device/PCM/image
  continuations, context recreation, invalid-state rejection and exact
  fresh-process continuation. VF2 also checks current NVRAM authority.
- RetroArch 1.22.2 (`fce35fc7`), macOS ARM64/OpenGL: VF2 saves 12,582,936 bytes,
  advances, restores exact machine frame 2,267 and identical game-region/full
  screenshots, then advances after resume. Clean exit 0, no forced termination.
  Saved image inspected: rendered attract scene. No listening-test claim.

Core SHA-256: `93644c70ce3771ceddfe88c484a9a3d58a961066634135a0917fc6c1a72ae9ee`.
Receipts/logs/screenshots: `port/build-scsp-dsp/integration-result.json`,
`states-{vf2,indy500,topskatr}/result.json`, `retroarch-vf2/result.json`,
`integrated-sound-checks.log`. Retain tools, compact results and frontend images;
remove task-owned states/RAM/PCM dumps, test executables and objects. The tested
candidate core is retained separately; installed core and user saves unchanged.

This qualifies the bounded local DSP integration group, not all A68K audio,
Windows whole-board PCM equivalence, other platforms or whole-catalog gameplay.
No game in the bounded runs reported an escaped DSP address. No commit/push.

## A68K Boundaries And Selectable DSP — 2026-11-04

- `tools/a68k_boundary_compare.py`: 16,154 unchanged-original executions match
  independent Python state-transition models: reset 30, memory wrappers 252,
  exceptions 6,144, interrupts 1,536, MOVEQ 8,192. No mismatch. Research models
  only, not a portable CPU. Even exception targets only; recursive odd-target
  errors, mapping installers and wider dispatch remain outside this group.
  Receipt: `port/build-a68k-boundaries/result.json`; focused disassembly retained.
- `tools/scsp_mame_backend_compare.py`: pinned pre-recovery SCSP source versus
  the selectable MAME path, 64 synthetic cases and 16,384 sample frames. Exact
  observed PCM/shared RAM/common DSP state, fingerprint `eac6fbf56db60264`.
  Receipt: `port/build-scsp-dsp/mame-backend-baseline.json`.
- macOS Libretro SHARC/TGPX4 build and `check-sound` pass. Synthetic archive
  sizes: original 1,580,262 bytes, MAME 530,642 bytes. Both resume exact PCM/state;
  opposite-backend preflight is nonmutating. Reset retains selection. Standalone
  `m2emu` and `m2run` also build; existing Mach-O alignment warnings remain.
- VF2, both DSP choices: 1,800 scripted frames, cold state and four exact
  12-frame RAM/device/PCM/image continuations, GL context recreation, current
  NVRAM authority and exact fresh-process continuation pass. Header backend and
  schema alterations with valid checksums are rejected without mutation. Live
  edits and Reset preserve the backend; unload/reload switches it and rejects
  a genuine state from the other backend. Original continuation PCM CRC
  `354e3923` matches the pre-selector receipt; MAME CRC is `c2f2f062`.
  Receipts: `backend-states-{original,mame}-gl/result.json`.
  Used VF2 payload: original 8,871,144 bytes; MAME 7,821,524 bytes, both within
  the unchanged 12 MiB frontend capacity.
- RetroArch 1.22.2 (`fce35fc7`), ARM64/OpenGL, MAME selected: saved 12,582,936
  bytes; exact restored machine frame 2,276 and full/game-region screenshots;
  scene changes before and after restoration. Exit 0, no forced termination.
  Saved screenshot inspected: VF2 attract, not a blank/boot frame.
  Receipt: `backend-retroarch-mame/result.json` and four screenshots/crops.
- An initial harness launch inside the filesystem sandbox failed at SDL video
  initialization. The authorized graphical-session run passes; this was not
  a DSP or Save State failure.

Candidate SHA-256: `614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`.
The receipts above are under `port/build-scsp-dsp/` unless stated otherwise.
Retain reusable tools, compact results, logs, screenshots and candidate core;
remove task-owned raw states/PCM/RAM, harness executables and build objects.
No listening, whole-board Windows equivalence or other-platform qualification
is implied. The 68000 remains Musashi; A68K is not yet an executable backend.

Cleanup removed 407 task-owned temporary files (179,065,340 bytes), preserving
the candidate, compact evidence, tools and eight frontend screenshots/crops.
See `backend-result.json` for source/build fingerprints and `backend-cleanup.json`
for the removal inventory and verified retained hashes. No installed-core change,
commit or push.

## Portable A68K Primitives — 2026-11-04

`port/a68k/a68k.c` is an isolated recovered C module, not yet linked into the
sound board. `tools/a68k_portable_compare.py` builds it with strict warnings and
compares it against unchanged ElSemi 1.1a x86 under Unicorn and the existing
independent transition models. O0, O2 and O2/UBSan each pass 16,418 cases:
reset 30, memory wrappers 252, exception frames 6,144, IRQ entry 1,536, MOVEQ
8,192, MOVEQ budget exits/wraparound 240 and odd-vector prefixes 24.

The memory checks now compare full EAX: native byte/word reads leave high bits
from the original page-descriptor address. The portable implementation preserves
these as integer tokens; host pointers remain separately bound. Both return
values and memory/callback effects match. Nine additional host-binding guards
pass independently of native-equivalence counts. No UBSan diagnostics.

Receipts: `port/build-a68k-portable/O0.json`, `O2.json`, `ubsan.json`, with source
and original-PE hashes. Common digest:
`4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`.
The runner removes temporary libraries/debug artifacts automatically. Retain
source, shim, tools and compact results; no ROM, game state or installed core
is involved in these tests.

Limits: odd-vector comparison stops before original recursive dispatch at
`00462c89`. Remaining exception tails, map installers, callback mutation
scenarios, other opcodes, scheduling, complete context serialization and sound
integration are not qualified. No runnable A68K backend or audible equivalence
is claimed. Musashi continues to execute current games; user policy is A68K
default / MAME (Musashi) alternative once reconstruction and integration are complete.


## A68K Opcode And Exception Dispatch — 2026-11-04

The portable runner now includes `tools/a68k_flow_compare.py`. O0/O2/UBSan
pass 21,100 original-code opcode-entry comparisons (MOVEQ 4,096, Line-A 4,096,
Line-F 4,096, generic Illegal 8,812), alongside the existing 16,418 primitive
cases: 37,518 comparisons per build. Nine host-binding guards remain separate.
Complete context, callbacks, cycle/boundary behavior, live fetch PC/flags and
Illegal diagnostics are compared. Independent trap models also check PC
adjustments. Unknown targets explicitly return unrecovered without mutation.

Two native-only probes confirm the odd-vector recursive tail's host-stack
problem through actual IRQ entry. One stops before RET would consume saved
ECX as a return address; the other records outstanding frames on fetch.
These are not portable equivalence cases or evidence of game reachability.
The portable boundary was pending a decision at this stage; the approved
sticky fault policy and its subsequent validation are recorded below.
See AUDIO_RE_ANALYSIS.md for addresses and scope.

Receipts: `port/build-a68k-flow/{O0,O2,ubsan}.json`. All three retain the base
digest `4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`
and flow digest `d2951b25963ce8aef76028fc75304863993b0fad46a702b05a4071e876a10954`.
No UBSan findings. Temporary compiled modules/debug files are automatically
removed; retain tools and compact receipts.

Dispatch-entry coverage: 32.20%; distinct-target coverage: 0.24%. Neither is
total CPU completion: 17,004 covered entries route to exceptions. Current
bounded group at this stage: three of four paths complete (75%); the subsequent
approved fault-policy group below completes the fourth path.
No complete execute loop, sound-board integration, archive or frontend CPU
selector is qualified. Production and installed cores remain unchanged.


## A68K Approved Odd-Vector Fault Policy — 2026-11-04

The isolated module now latches a fatal diagnostic at native `00462c89`, before
the unsafe recursive host tail. User approval permits an explicit stop, not
repairing the original stack. The diagnostic retains vector, entry PC, raw
target, cycles, flags and original branch address. All CPU entries refuse
further execution, including native reset and PC rebinding. Fresh CPU creation
is required; future frontend integration must surface the error and stop content.

O0/O2/UBSan each pass **37,608 original-code comparisons**: the preceding
37,518 plus 90 direct/IRQ/Line-A/Line-F/Illegal odd-vector prefixes. Separately,
**1,260 post-fault retries** leave all CPU fields, callback events and fetch
bindings unchanged; a recreated CPU executes normally. Nine existing binding
guards and both original host-stack probes also pass. No UBSan findings.
This does not establish game reachability or frontend content-stop behavior.

Receipts: `port/build-a68k-fault/{O0,O2,ubsan}.json`, with current source hashes.
Primitive digest:
`4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`.
Flow digest (now including zero diagnostic fields):
`a7008360fd69469d5a4b948eba76c46658e64978bb4d6fcf71bab58cc4183b8d`.
Fault-prefix/policy digest:
`ccf9360dd6f84f788acc5fb8a97f09cbc4c8aa3fd2e6b37205e962d46af52e7a`.

Bounded group complete: **4/4 paths (100%)**. Entry coverage remains 32.20%
and target coverage 0.24%; neither measures overall CPU completion. The module
remains unlinked, operational/installed core unchanged, no frontend CPU selector
exposed. Tools and compact receipts retained; task-owned temporary outputs removed.


## A68K Register-Only Instruction Group — 2026-11-04

All 345 encodings for 22 additional SWAP/EXT/EXG/NOP/CLR/NEG/NEGX/NOT/TST
register targets pass **24,840** original-code cases at O0/O2/UBSan. Together
with the preceding suite this is **62,448 original-code comparisons per build**.
Fault guards remain separate. Full context, live/published flags, cycles,
negative-budget exits, zero-budget fetch and PC wrap are compared. The native
NEGX ADC-then-NEG and EXT aliases are preserved. Undefined logical x86 AF
remains outside hardware equivalence. No memory-form or complete-CPU claim.

Receipts: `port/build-a68k-register/{O0,O2,ubsan}.json`, source hashes retained.
Register digest: `079649d7a9e5cfa4f7c66f4f875f060c40307075c6fba908e37d92451cfcf383`.
Group: 100%; dispatch entries 32.72%, distinct targets 1.56%. No core installation,
commit or push. Native code is unmodified and no ROMs are involved.


## A68K Native Map Installers — 2026-11-04

The three native installers (`004b3280`, `004b32c0`, `004b3310`) now have a
bounded host implementation. Fetch mapping clears callbacks; data/write mapping
retains the appropriate width callbacks. All mapped pages use one base relative
to the original start. Native page count is `((end-start)>>12)+1`, deliberately
not the difference of rounded endpoints. Unaligned and full-24-bit ranges match.

O0/O2/UBSan pass 60 whole-table comparisons against untouched native routines,
including sentinel pages. Five malformed host-range checks reject changes before
mutation; these are host guards, not original invalid-pointer emulation. Mapping
is independent configuration and does not clear a CPU fatal diagnostic.
Receipts: `port/build-a68k-maps/{O0,O2,ubsan}.json`; digest:
`c2161d989d70b8f1164ed7f71f50db677e9d7f841d078aca441c7efe4e29e6e3`.
Group **3/3 (100%)**; cumulative comparisons **62,508 per build**. Opcode coverage
unchanged (32.72% entries, 1.56% targets). Board-device wiring remains separate.


## A68K Conditions And Branches — 2026-11-04

Recovered 64 targets: all 16 register Scc and DBcc conditions, plus byte/word
BRA, BSR and Bcc. All 4,352 encodings and all 16 NZVC combinations are exercised;
PC wrap, budgets, counters and extension words vary deterministically. Additional
odd-vector branch cases check the approved halt. **70,144 comparisons** pass
O0/O2/UBSan; **132,652 cumulative per build**, including prior groups. There
are 288 branch cases reaching the explicit fault policy and all retry guards pass.

Original quirks are preserved: signed conditions OR `0x200` into live flags;
DBcc does not mask/rebind or test the branch target's alignment; BSR retains
the prior raw-PC high byte in its stacked return. Taken Bcc/BRA/BSR rebind and
check alignment; a resulting odd exception vector uses the approved fatal stop.
Not-taken word branches skip the extension without reading it. Native cycle
costs, callback order, published versus live PC/flags and counter wrap match.

Receipts: `port/build-a68k-control/{O0,O2,ubsan}.json`; digest:
`fdb5e0aa4797b100cfc707e5d68f1ae8c40f0f90a4925cba5251e9314cdcd337`.
Bounded group **64/64 (100%)**; combined dispatch coverage **25,797/65,536
entries (39.36%)**, **90/1,667 targets (5.40%)**. This is not total CPU completion.
A complete fetch/execute loop, arbitrary callback mutation and board integration
remain unqualified. Tools and compact results retained; no ROMs or core deployment.


## A68K Binary Register Arithmetic — 2026-11-04

Thirty additional original targets implement register OR/AND/EOR, ADD/SUB/CMP,
ADDX/SUBX and ADDA/SUBA/CMPA in applicable widths. The actual dispatch table owns
aliases and Dn/An source selection. Native EOR direction/cycle costs and address
arithmetic cycles are retained. Address word inputs are sign-extended; address
ADD/SUB preserve flags, comparisons preserve X, and ADC/SBB store complete X
before merging sticky Z. Partial-register updates and identical operands match.

All 2,752 encodings with boundary/seeded-random operand pairs and both X inputs
pass **121,088 comparisons** per O0/O2/UBSan build. Existing groups also pass:
**253,740 cumulative original-code comparisons**, host guards separate. These
are not exhaustive operand products or memory forms. Receipts:
`port/build-a68k-binary/{O0,O2,ubsan}.json`; digest:
`fad27ff6ccd39307a84209c65b6218e14454d1d9ec83f9b3f4190f91350a72ff`.
Group **30/30 (100%)**; combined coverage **28,549/65,536 entries (43.56%)**,
**120/1,667 targets (7.20%)**, not overall CPU completion. Operational core unchanged.


## A68K Register Transfers And Immediate Operands — 2026-11-04

Thirty-six additional targets implement register/immediate MOVE/MOVEA,
ORI/ANDI/EORI/ADDI/SUBI/CMPI to Dn and ADDQ/SUBQ to Dn/An. The actual original
aliases are retained, including byte-encoded address quick operations. Native
immediate cycles are not normalized: ANDI.L and CMPI.L charge 14, other covered
long immediate arithmetic/logical operations charge 16; MOVE immediate charges 4.
Extension words use the current fetch binding and native word-swapped long order.
MOVEA sign extension and flag preservation, partial updates and PC wrap match.

O0/O2/UBSan pass **62,088 added cases**, all 1,592 covered encodings, operand
boundaries/patterns and negative/zero/positive remaining budgets. Shared arithmetic
helpers also pass all prior regressions: **315,828 cumulative comparisons** per
build. Receipts: `port/build-a68k-operands/{O0,O2,ubsan}.json`; digest:
`22f683dfb07fab2b782a49873f29b3f05ee761b1599cd712f2e11ce92508b8e3`.
Group **36/36 (100%)**. Combined dispatch coverage: **30,141 entries (45.99%)**,
**156 targets (9.36%)**. No complete CPU/audio integration; memory forms remain open.


## A68K Effective Addresses And MOVE Memory Sources — 2026-11-04

Twenty-nine original targets now cover MOVE byte/word/long from memory to Dn:
indirect, postincrement/predecrement (including byte A7's two-byte step), signed
displacement, brief index, absolute short/long and PC-relative displacement/index.
Brief indexes select all 16 Dn/An registers; native ignored scale/full-format bits
remain ignored. Instruction extensions retain the current fetch binding.

The pinned callback table confirms ordinary operand reads use DATA wrappers
`004b3250/3220/31f0`; PC-relative reads use READ wrappers `004b31c0/3190/3160`.
The tests execute those unchanged original wrappers, not only synthetic handler
replacements. Direct and callback memory paths, masked addresses, boundary
crossing, word order and context observed during callbacks are compared.

O0/O2/UBSan pass **16,896 added cases**, all 1,056 encodings, **332,724 cumulative
comparisons per build**. Receipts: `port/build-a68k-memory/{O0,O2,ubsan}.json`;
digest `553cf90941c20a410398b3209b2ae76447e391c70007b6bfabf6b06d720b3549`.
Group **29/29 (100%)**; combined coverage **31,197 entries (47.60%)**, **185
targets (11.10%)**. This is not total CPU completion. Arbitrary callback mutation,
memory destinations, remaining instructions and full audio integration remain open.


## A68K Arithmetic And Logical Memory Sources — 2026-11-04

O0/O2/UBSan pass 84,480 additional original-code comparisons across 145
OR/AND/ADD/SUB/CMP targets and all 5,280 corresponding encodings. The combined
memory-source suite has 101,376 cases; total is 417,204 comparisons per build.
Native DATA/READ wrappers, effective addresses, cycle exits, flags/X and context
observed by callbacks match. Receipts: `port/build-a68k-memory-binary/*.json`;
matching digest `9a25b78e78245eda173ef382fe6762f361f1365bba610abd4b1d2b447582210e`.
Group 145/145 complete; combined dispatch coverage 36,477/65,536 entries and
330/1,667 targets. No full CPU, audio or frontend integration claim.


## A68K Arithmetic And Logical Memory Destinations — 2026-11-04

OR/AND/EOR/ADD/SUB Dn-to-memory adds **115/115 targets (100%)**, all 5,040
encodings and **161,280 new comparisons** at O0/O2/UBSan. All four combinations
of direct/callback reads and writes match, including callback-visible context,
full narrow-write argument, memory bytes, native costs and cycle exit. ADD/SUB
publish X after the write callback; that ordering is explicitly preserved.

Receipts: `port/build-a68k-memory-dest/{O0,O2,ubsan}.json`; group digest
`cf98896cca36a26843fd850b8433ebbb6640ae04277748a99d23cb4c96b5c0cb`.
Cumulative comparisons: **578,484 per build**. Combined dispatch: **41,517/65,536
entries (63.35%)**, **445/1,667 targets (26.69%)**, not weighted CPU completion.
Other memory destinations, instruction families, arbitrary callback mutation
and full execution/audio integration remain open. Operational core unchanged.


## A68K Immediate And Quick Memory Operands — 2026-11-04

ORI/ANDI/EORI/ADDI/SUBI/CMPI and ADDQ/SUBQ memory forms add **184/184 targets
(100%)**, all 2,772 encodings and **88,704 comparisons** passing O0/O2/UBSan.
Native immediate-before-EA ordering, word-swapped longs, quick zero encoding
as eight, read/write callbacks, CMPI's lack of write, flags/X and cycles match.
All earlier groups also pass: **667,188 comparisons per build**.

Receipts: `port/build-a68k-memory-operands/{O0,O2,ubsan}.json`; group digest
`0bc51ea996680eb9fd29bb0c8aaf18a1b3ffdfdff0e682075402165f1c00a8ca`.
Combined dispatch: **44,289/65,536 entries (67.58%)**, **629/1,667 targets
(37.73%)**. Full CPU/audio integration and other instruction families remain open;
these dispatch metrics are not overall completion. Operational core unchanged.


## A68K Address-Register Memory Sources — 2026-11-04

MOVEA/ADDA/SUBA/CMPA memory forms add **72/72 targets (100%)**, all 2,816
encodings and **45,056 new comparisons** passing O0/O2/UBSan. Native flag
publication before reads and reload afterward, callback-visible context, signed
word operands, same-An address updates and costs match. All earlier groups pass:
**712,244 cumulative comparisons per build**.

Receipts: `port/build-a68k-memory-address/{O0,O2,ubsan}.json`; the combined
146,432-case memory-source digest is
`d48d2e03134ea92f88e9d0bd2ab9c9b9d2ac01f6363e2ff96442b6cb87c57fbf`.
Combined dispatch: **47,105/65,536 entries (71.88%)**, **701/1,667 targets
(42.05%)**; not weighted CPU completion. Other instructions, full execution and
sound integration remain open. Operational core unchanged.


## A68K CLR/TST/TAS/NEGX Memory Group — 2026-11-04

**78/78 targets (100%)**, all 420 encodings and **26,880 new comparisons** pass
O0/O2/UBSan. All four direct/callback combinations, both prior Z states, X,
callback-visible context and native costs match. CLR performs no dummy read;
TST performs no write; TAS derives flags before setting bit 7. NEGX retains
ADC-width then NEG-width and publishes X/merged flags before the write, reloading
flags afterward. Shared register NEG/NEGX regressions also pass after factoring
the exact arithmetic helper. NEG/NOT memory scratch dependencies remain separate.

Receipts: `port/build-a68k-memory-unary/{O0,O2,ubsan}.json`; group digest
`0cb8d91db3799f4a7ac83ed6e8755f3f3be613719b76b72a89051f75f929b81a`.
Cumulative comparisons: **739,124 per build**. Combined dispatch: **47,525/65,536
entries (72.52%)**, **779/1,667 targets (46.73%)**; not weighted CPU completion.
Remaining instructions and full execution/audio integration are open.


## A68K Effective Addresses And Stack Frames — 2026-11-04

LEA/PEA/LINK/UNLK: **16/16 targets (100%)**, all 268 encodings and **8,576
new comparisons** pass O0/O2/UBSan. Native costs, unmasked address results,
flags/publication, direct/callback stack access and aliasing match. LINK A7
reads the already-decremented stack pointer; displacement is fetched only after
the write. UNLK A7 retains the original final address-plus-four ordering.

Receipts: `port/build-a68k-address/{O0,O2,ubsan}.json`; group digest
`a16891f53c3596c30328d04e684270ee5e029244e6fae81c28b8b2dd4a836a55`.
Cumulative comparisons: **747,700 per build**. Combined dispatch: **47,793/65,536
entries (72.93%)**, **795/1,667 targets (47.69%)**, not weighted CPU completion.
Remaining instructions and full execution/audio integration are open.


## A68K Bit Operations — 2026-11-04

BTST/BCHG/BCLR/BSET register and memory forms: **84/84 targets (100%)**, all
1,818 encodings and **116,352 new comparisons** pass O0/O2/UBSan. Register and
immediate counts, modulo-32/modulo-8 selection, register aliases, prior flags,
PC-relative reads, direct/callback accesses and publication timing match. Only
Z changes; X and other saved flag bits remain intact. The original immediate
count fetch shares the opcode-fetch byte sequence: the harness now explicitly
uses the final fetch as its boundary, and all previous groups pass unchanged.

Receipts: `port/build-a68k-bit/{O0,O2,ubsan}.json`; group digest
`f23627e7851875d4682ae1b8f9436fd32fe3c0deb1f1c6f36ab517ba9136203d`.
Cumulative comparisons: **864,052 per build**. Combined dispatch: **49,611/65,536
entries (75.70%)**, **879/1,667 targets (52.73%)**, not weighted CPU completion.
The harness also rejects overlapping group target sets before reporting coverage.
Remaining instructions and full execution/audio integration are open.


## A68K MOVE Register/Immediate To Memory — 2026-11-04

**46/46 targets (100%)**, all 2,142 encodings and **68,544 new comparisons** pass
O0/O2/UBSan. Original An aliases, full byte/word callback arguments, source capture
before destination address updates, immediate/EA extension ordering, flags and
native costs match. Direct writes and callback-observed contexts are compared.

Receipts: `port/build-a68k-move-dest/{O0,O2,ubsan}.json`; group digest
`2374935c493a0fb657a701a64d729665fe44294a2e44f6768583637e45341667`.
Cumulative comparisons: **932,596 per build**. Combined dispatch: **51,753/65,536
entries (78.97%)**, **925/1,667 targets (55.49%)**, not weighted CPU completion.
Memory-to-memory MOVE, remaining instructions and full integration remain open.

## A68K MOVE Memory To Memory — 2026-11-04

**225/225 targets (100%)**, all 5,544 encodings and **177,408 new comparisons**
pass O0/O2/UBSan. The tests cover all four direct/callback combinations,
source/destination extension ordering, 22,272 same-register cases and 34,536
same-address cases. Source reads precede destination address calculation; the
latter observes source-side address-register updates. Full callback values,
publication timing, flags, writes and native costs match.

Receipts: `port/build-a68k-move-memory/{O0,O2,ubsan}.json`; group digest
`5c793ad331fbb5a3a293d60ac74b93c205bc37f5b39eaf043024dfaaab9728c6`.
Cumulative comparisons: **1,110,004 per build**. Combined dispatch: **57,297/65,536
entries (87.43%)**, **1,150/1,667 targets (68.99%)**, not weighted CPU completion.
Independent read/write maps and exact-address aliases are tested; complete sound
board mapping, remaining instructions and execution/audio integration stay open.

## A68K MULU/MULS — 2026-11-04

**22/22 targets (100%)**, all 848 encodings and **27,136 new comparisons** pass
O0/O2/UBSan together with previous groups. Register, immediate and memory sources,
signed/unsigned edge operands, aliasing, PC-relative space, publication timing,
full products and native fixed costs match. Historical Make68K `mul()` guides
structure/comments; original EXE remains the behavioral authority.

Receipts: `port/build-a68k-multiply/{O0,O2,ubsan}.json`; group digest
`a3a4cf923b175f7b5f620e95079455876207b29a43f44e3bda637198f23281f3`.
Cumulative comparisons: **1,137,140 per build**. Dispatch: **58,145/65,536 entries
(88.72%)**, **1,172/1,667 targets (70.31%)**, not weighted CPU completion.
A68K remains unlinked; other instructions and full integration are still open.

## A68K Register Rotations And Memory Shifts — 2026-11-04

**80/80 targets (100%)**: 24 register ROR/ROL/ROXR/ROXL targets (1,536 encodings,
92,160 comparisons) and 56 word memory shift/rotate targets (336 encodings,
21,504 comparisons). O0/O2/UBSan and previous groups pass. Preserve the original
count masking, cycle-subtraction carry for ROR/ROL count 32, byte-only X updates
in register ROX, and distinct publication order for memory families. Logical
memory shifts save full X before clearing saved DH, not merely the V bit.

Receipts: `port/build-a68k-rotate-shift/{O0,O2,ubsan}.json`. Digests:
- Register rotations: `2972d2088ebb8ed1d58e3bbad69b37bd4e8e9e64ae0ee002a4f785ebae7043f8`.
- Memory shifts: `c4910e41ed72baaaaa0e9ac0c545ce7c69674b81e7c9e3c2c20705ac759abca6`.

Cumulative comparisons: **1,250,804 per build**. Dispatch: **60,017/65,536 entries
(91.58%)**, **1,252/1,667 targets (75.10%)**, not weighted CPU completion.

Supplementary `tools/a68k_host_shift_compare.py` executes 6,912 isolated x86
SHR/SHL/SAR cases under Rosetta and Unicorn. Results and NZPC/AF agree in every
case; 900 cases differ only in multi-bit overflow. The pending original register
shift paths discard/recompute that overflow rather than consuming it directly.
Single-bit overflow agrees. This is host-instruction evidence, not execution of
the Windows binary under Rosetta or a guarantee for ISA-undefined flags on all
physical CPUs. Receipt: `port/build-a68k-host-shift/result.json`. Historical
source structure guides recovery; original executable remains authoritative.

## A68K Register Arithmetic/Logical Shifts — 2026-11-04

**27/27 targets (100%)**, 1,536 encodings and **92,160 new comparisons** pass
O0/O2/UBSan with previous groups. Native zero-count behavior, partial-register
writes, special ASL #1 timing, narrow count-32 flag behavior, and the long ASL
big-shift tail that leaves X untouched are retained. ASR uses the original LAHF
subset; logical shifts clear saved DH. Source comments link these choices to
Make68K while native code fixes the final behavior.

Receipts: `port/build-a68k-register-shift/{O0,O2,ubsan}.json`; group digest
`44f50de31e7d701de2b7f3f66ec7c922ad2835f1572c4edfc55f08bde2973540`.
Cumulative comparisons: **1,342,964 per build**. Dispatch: **61,553/65,536 entries
(93.92%)**, **1,279/1,667 targets (76.72%)**, not weighted CPU completion.
Other instructions and full CPU/audio integration remain open.


### A68K JMP/JSR And Windows Fault-Handling Audit — 2026-11-04

JMP/JSR: **14/14 targets**, 56 encodings and **14,336 added original-code
comparisons per build** pass O0/O2/UBSan, including 4,221 approved odd-vector
fatal-prefix cases. Existing branch digest is unchanged. Group digest:
`02026ba28687a5e51892cfa5a011849f9dbd7fd6ab999f8995196490fa0e42a5`.
Receipts: `port/build-a68k-jump/{O0,O2,ubsan}.json`; redundant stdout copies
removed only after comparison with those receipts. Cumulative: **1,357,300**;
dispatch **61,609/65,536 entries (94.01%)**, **1,293/1,667 targets (77.56%)**.

Windows exception audit: **11/11 checks pass** using unchanged native CRT,
C++ top-level and main-loop frame filters under Unicorn. Neither integer divide
status is handled; positive action-table controls verify the filter test. The
call-site, scope-table, C++ metadata and filter-registration audit is recorded in
AUDIO_RE_ANALYSIS.md and `port/build-a68k-windows-exception/result.json`.
This is not an actual Windows process crash or proof that game code reaches the
fault. The later Windows-process probe and approved selectable policy below
supersede that evidence/policy limit. No installed-core change.


### A68K Effective-Address Immediate Arithmetic — 2026-11-04

The 21 remaining ordinary binary immediate-source targets add 168 encodings and
6,552 original-code comparisons per build. O0/O2/UBSan pass, including all
previous groups. The expanded operand group has 68,640 cases; digest
`52b61bc757a2bbc93b443715a5ebb9a93f24e74882ea880a0b28c973fd2c5f20`.
Receipts: `port/build-a68k-immediate-high/{O0,O2,ubsan}.json`; source hashes
checked against the tested tree before cleanup of redundant stdout logs.

Cumulative comparisons: **1,363,852 per build**; dispatch **61,777/65,536 entries
(94.26%)**, **1,314/1,667 targets (78.82%)**. These remain isolated CPU-boundary
checks, not complete CPU execution or audio qualification. Core candidate hash
remains `614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`;
no installed-core change, commit or push.


### A68K DIVS Native Windows Process And Prepared Policy — 2026-11-04

The original process reaches a normal guest-overflow control and produces
unhandled c0000095 at native IDIV 0048198c for INT32_MIN/-1: first chance,
second chance, then process exit c0000095. Synthetic operands were injected
only after the real main-loop SEH registration; no ROMs. See
`port/build-a68k-windows-process/results-c/{windows-divs,provenance,dependency}.json`
and AUDIO_RE_ANALYSIS.md for method and limits.

Default Stop Content / alternative Original policy passes O0/O2/UBSan on macOS;
Original SIGFPE is confined to an owned subprocess. The selector contract and
policy are prepared but not registered in the operational core, since A68K is
still unlinked. A separate Windows MinGW child also passes: default preserves the process,
Original exits c0000095, matching the native original. Windows receipt:
`port/build-a68k-windows-policy/results-b/{policy,provenance}.json`.
Real frontend integration remains unqualified. Receipt: `port/build-a68k-divs-policy/result.json`.


### A68K Register/Immediate DIVU/DIVS — 2026-11-04

O0/O2/UBSan pass the four native targets / 144 encodings / 60,480 new cases,
including 192 original host-overflow prefixes, 3,408 odd-vector prefixes and
50,400 post-fault retry guards. Group digest:
`b1f4fbcba00b7adee4642cad9440b79ad02d310ce8e2951c5bcc248b02f03440`.
The complete prior suite also passes: **1,424,332 cumulative comparisons per
build**. Receipts: `port/build-a68k-divide-full/{O0,O2,ubsan}.json`; current source
hashes and receipt/stdout identity checked before removing redundant logs.
Coverage: **61,921/65,536 entries (94.48%)**, **1,318/1,667 targets (79.06%)**.
Memory DIV scratch-register dependencies, complete execution, sound-board and
frontend error-policy integration remain open; this is not audio qualification.


### A68K TAS, TST An And Software Traps — 2026-11-04

Five native targets and 41 encodings add **14,784 original-code comparisons**:
1,728 TAS/TST An cases and 13,056 TRAP/TRAPV cases. O0/O2/UBSan and all previous
groups pass. TAS retains flags from the original byte before setting bit 7;
TST An follows the native dispatch aliases without changing An. TRAP stores the
next PC and exits at zero budget; TRAPV with V set stores the instruction PC,
then charges four cycles with JS (zero continues). The 3,168 odd-vector trap
prefixes preserve the approved diagnostic boundary.

Expanded register-group digest:
`5f325536f3354e5d4e7b83c51be04bfff9922c79ceb5ce0151b716e2918c8aa0`.
Software-trap digest:
`2e5b468bab8bec108f39b19f113772f79e612a39cd67fc7b91a52cf713903ac6`.
Receipts: `port/build-a68k-software-trap/{O0,O2,ubsan}.json`; current source hashes
and redundant stdout equality verified before cleanup. Cumulative:
**1,439,116 comparisons per build**. Dispatch: **61,962/65,536 entries (94.55%)**,
**1,323/1,667 targets (79.36%)**, not weighted CPU completion. Still unlinked;
no audio/game execution claim or installed-core change.


### A68K USP Transfers And Native BTST Immediate — 2026-11-04

**3/3 targets (100%)**, 24 encodings and **12,800 new comparisons** pass
O0/O2/UBSan with prior groups. MOVE An,USP / MOVE USP,An retain all eight register
aliases, privilege-exception PC, callback publication and the native four-cycle
charge; 1,536 odd-vector prefixes match. The original BTST Dn,#word dispatch
entry tests only the low byte, masks the bit count to 0..7 and updates only Z.
No independent decoder rejects or normalizes this original capability.

USP digest: `5861c01c87109a40da08b4d69707b0cd57029688f7ded7ed5857256e950e5d2b`.
Expanded bit-group digest:
`ea7aecabd92de6b3b96c5ea33c511a7c81acb3a2630000410029b1f2763faf7b`.
Receipts: `port/build-a68k-usp-bit/{O0,O2,ubsan}.json`; current source hashes and
redundant stdout identity checked before cleanup. Cumulative:
**1,451,916 comparisons per build**. Dispatch: **61,986/65,536 entries (94.58%)**,
**1,326/1,667 targets (79.54%)**, not weighted CPU completion. A68K remains
unlinked; no installed-core change or gameplay/audio qualification.


### A68K RTS — 2026-11-04

The native RTS target / single encoding passes **27,648 new comparisons** in
O0/O2/UBSan, with all prior groups. Tests cover stack wrap/unaligned/cross-page
starts, direct and callback reads, all guest CCR combinations, user/supervisor
mode, raw-PC high bits, even/odd return targets and cycle boundaries. The native
order increments A7 before reading and publishes the current instruction PC
without adding two. Return rebinding reuses the already qualified JMP/JSR
helper; 6,912 odd-vector prefixes preserve the approved fatal boundary.

The native oracle uses the actual stack read wrapper and the established
synthetic vector service independently. This does not qualify aliasing between
stack and vector storage or the complete sound-board address map.
Digest: `fc95d43a4137c5c84b45a61ebfdf69728d078a8612f5b5dbedc3bf6ca1520930`.
Receipts: `port/build-a68k-rts/{O0,O2,ubsan}.json`; source hashes and redundant
stdout checked before cleanup. Cumulative: **1,479,564 comparisons per build**.
Dispatch: **61,987/65,536 entries (94.58%)**, **1,327/1,667 targets (79.60%)**,
not weighted CPU completion. RTR/RTE and full integration remain open.


### A68K ABCD/SBCD Register Forms — 2026-11-04

**2/2 targets (100%)**, 128 encodings and **483,328 new comparisons** pass
O0/O2/UBSan with all previous groups. This includes **262,144 exhaustive byte
pair/X cases**, including non-BCD digits, plus all register aliases, sticky-Z
states and cycle tails. Original ADC/DAA or SBB/DAS behavior is retained,
including the explicit saved-flag merge: C is copied into N, high flag bytes
(including V) remain unchanged, Z is sticky and full saved flags are copied to X.
The historical Make68K `abcd_sbcd()` emitter explains the same sequence.

Digest: `e2aa79c053e76b67c364530d2e250e7835d26290b94ed0df6451d37ec989f43a`.
Receipts: `port/build-a68k-bcd-register/{O0,O2,ubsan}.json`; current source hashes
and redundant stdout identity checked before cleanup. Cumulative:
**1,962,892 comparisons per build**. Dispatch: **62,115/65,536 entries (94.78%)**,
**1,329/1,667 targets (79.72%)**, not weighted CPU completion.

`tools/a68k_remaining_inventory.py` reuses the existing ISA-label acquisition and
qualified dispatch receipts to index remaining native targets. Labels identify
work, not semantic authority; disassembler pseudo-ops do not imply native
illegality. The post-ABCD/SBCD inventory has 338 targets / 3,421 entries left.
Complete execution, scheduling, state and frontend integration are additional
work, not included in these instruction coverage counts.


### A68K NBCD And Consumption Stop — 2026-11-04

**1/1 target (100%)**, eight encodings and **24,576 new portable comparisons**
pass O0/O2/UBSan with all prior groups. Unlike ABCD/SBCD, NBCD imports full
PUSHFD after DAS, replaces Z rather than keeping it sticky, and copies those
flags into full X. All 512 byte/X pairs were first acquired from the original
Windows 11 ARM64 process after native SEH registration and compared with the
same native body under Unicorn: **512/512 match**, including OF=0. This is
observed behavior on that host, not a guarantee for undefined OF on every x86
processor. No ROMs were copied or loaded.

Windows acquisition/comparison: `port/build-a68k-nbcd-windows/`.
Reusable tools: `port/a68k/test/windows_exception_probe.cs` (`RunNbcd`),
`windows_nbcd_probe.ps1`, and `tools/a68k_nbcd_probe.py`. The owned remote root
and duplicate local staging were removed after hash verification; results and
tools remain. Portable receipts: `port/build-a68k-nbcd/{O0,O2,ubsan}.json`;
digest `d72c1a8d396bf7ec01b758c8498041b9a2a207230729139738e4c2e3f911fbab`.
The preceding ABCD/SBCD digest is unchanged. Source hashes and redundant stdout
identity were checked before cleanup.

Cumulative: **1,987,468 comparisons per build**, plus separate host/policy guards.
Dispatch: **62,123/65,536 entries (94.79%)**, **1,330/1,667 targets (79.78%)**;
not weighted total CPU completion. The current qualified inventory leaves
337 targets / 3,413 entries. It is indexed in
`port/build-a68k-nbcd/remaining.json`, reusing the existing ISA-label acquisition.
Remaining families include memory conditional stores, SR/CCR moves, MOVEM/MOVEP,
CHK, memory NEG/NOT/division/BCD, extended arithmetic, CMPM, RTR/RTE/RESET/STOP
and native entries needing label review. Complete execution, sound scheduling,
Save States and frontend registration remain separate integration work.

Work stops at the user-authorized **50% total account usage**; reported reset
2026-11-11 06:21 CET. No further implementation group started. A68K and its
prepared DIVS selector policy remain unlinked; operational Musashi and the
installed core are unchanged. No commit or push. Astra / High remains suitable
for the remaining original-code reconstruction.

### A68K Memory NBCD And State-Restoring Returns — 2026-11-04

The renewed cap is 55% total account usage. Memory NBCD recovers **9/9 native
bodies (100%)**, 42 dispatch encodings and **2,688 added cases**. The existing
memory-unary suite now has 29,568 cases and the register NBCD regression retains
24,576 cases. Native memory forms preserve flags/X until after the write and
pass the zero-extended byte result, unlike the retained high bits of several
other native writes. The arithmetic reuses the previous Windows-qualified DAS
result. Receipts: `port/build-a68k-nbcd-memory/{O0,O2,ubsan}.json`.

RTR/RTE recover **2/2 native bodies (100%)** and two encodings with **36,864
comparisons**. A reusable scripted bus fixture verifies every read's published
CPU context through the actual original wrappers. Both increment A7 before
reading and publish the full status-read return as PC before the second read.
The native CCR lookup writes its whole high byte into low X, preserving the
upper three X bytes. RTE restores the low SR-high byte, switches to USP when
requested and rechecks IRQ using live PC/flags after its own cycle charge.
RTR retains supervisor state and does not recheck IRQ. The suite covers all
32 CCR values, privilege and stack switching, masked/accepted level 3 and level
7 IRQs, automatic/explicit vectors, odd return addresses, odd-vector guarded
prefixes and cycle boundaries. Scripted callbacks are not full-board/direct-map
aliasing or arbitrary callback mutation qualification.

The full suite passes O0/O2/UBSan: **2,027,020 comparisons per build** plus
separate host guards. Dispatch coverage is **62,167/65,536 (94.86%)** and
**1,341/1,667 native targets (80.44%)**, not weighted CPU completion.
Receipts: `port/build-a68k-restore/{O0,O2,ubsan}.json`; all recorded source hashes
verified before the next group. Restore digest:
`4883836e73263b9aff038569691efaca259dfc9c696e04a846353609149b6399`.
The research CPU remains unlinked. No operational core, ROM or user-save changes.

### A68K MOVEP And CMPM — 2026-11-04

**10/10 native targets (100%)**, 448 encodings and **30,720 new comparisons**
pass focused O0/O2/UBSan runs: 12,288 MOVEP and 18,432 CMPM cases. MOVEP retains
full rotated write arguments, two-byte address spacing and the captured flag
word. CMPM retains ordered postincrements, A7 byte increments, same-register
aliasing and full native comparison flags without changing X. The scripted
fixture checks every callback's context and full write argument through the
unchanged original bus wrappers, with odd/wrapping addresses and budget edges.
No direct-map or arbitrary callback-mutation claim is added.

Receipts: `port/build-a68k-sequence/{O0,O2,ubsan}.json`; source hashes verified.
MOVEP digest `5d47bbf709e80ccfa2fb94ce583db53d049b613b50a19a1627e60d88b996bda9`;
CMPM digest `bb522109281ac4a7f712e3f4e2b3385404313022932165ce3d035a5b62e48b17`.
Qualified groups now cover **62,615/65,536 entries (95.54%)** and
**1,351/1,667 targets (81.04%)**. The complete suite will be rerun after the
related memory-transfer batch. A68K remains unlinked and the installed core is
unchanged.

### A68K MOVEM And STOP Qualification — 2026-11-04

The complete suite passes O0/O2/UBSan after MOVEP/CMPM, MOVEM, STOP and the shared
status-import refactoring: **2,149,516 comparisons per build** plus host guards.
MOVEM adds **28/28 native targets (100%)**, 140 encodings and 67,200 cases. Tests
cover empty/full/alternating register lists, each individual register, every
encoding/address mode, callback-visible state and cycle boundaries. Retained
quirks include mask publication through saved flags, original-base stores in
predecrement mode, delayed final writeback, the initial four-byte postincrement
even for word transfers and exit at zero cycles in postincrement mode.
STOP adds **1/1 target (100%)**, one encoding and 24,576 cases. Its accepted IRQ
path precedes the ordinary four-cycle charge; otherwise it discards the budget,
marks bit 7 of IRQ and exits at -4. Wakeup in the future scheduler is not yet
qualified.

Full receipts: `port/build-a68k-transfers/{O0,O2,ubsan}.json`; source hashes were
verified before the next implementation group. Dispatch coverage at this stage:
**62,756/65,536 entries (95.76%)**, **1,380/1,667 targets (82.78%)**. These are
coverage measures, not weighted overall CPU completion.

### A68K Status, Decimal Memory And Gated Control Entries — 2026-11-04

The full original-code suite passes O0/O2/UBSan: **2,824,332 comparisons per
build**, plus ten separate host-binding guards. Source hashes and unchanged
digests for the prior BCD, return, MOVEP/CMPM, MOVEM and STOP groups were checked
before continuing. Receipts: `port/build-a68k-status-control/{O0,O2,ubsan}.json`.

| Added Group | Native Targets | Encodings | Comparisons Per Build |
| --- | --- | --- | --- |
| SR/CCR Moves | 38/38 | 206 | 158,208 |
| SR/CCR Logical Immediates | 6/6 | 6 | 147,456 |
| ABCD/SBCD Memory | 8/8 | 128 | 221,184 |
| Gated RTD/MOVEC | 3/3 | 3 | 136,448 |
| RESET Instruction | 1/1 | 1 | 11,520 |

Preserved behavior includes the context+0x7c CCR-export gate; differing IRQ
recheck tails after MOVE-to-SR versus logical-immediate privilege faults;
full byte-write arguments and pre-write X publication in memory BCD; RTD's
opcode-address displacement read; all MOVEC selector aliases; and RESET's
callback slot and prefetched successor even after a negative cycle budget.
The test instruction binding now includes the actual opcode word as well as
extensions, allowing the RTD behavior to be compared directly.

RESET uses a distinct `A68K_PREFETCHED` result with `prefetched_opcode`, requiring
the future execution loop to dispatch that saved opcode without another fetch
or budget test. Tests include absent/present output callbacks and callbacks
that change PC, flags and the already-fetched instruction bytes. Native callback
tokens remain integers: a nonzero token without a host binding is a separate
binding error, not a fabricated guest response.

Dispatch coverage: **63,100/65,536 entries (96.28%)**, **1,436/1,667 targets
(86.14%)**. Each listed group is 100% of its selected native targets; neither
metric is weighted CPU completion. The qualified remaining inventory contains
231 targets / 2,436 encodings: conditional stores, NEG/NOT, memory DIVU/DIVS,
ADDX/SUBX and CHK. Several consume native read-wrapper scratch state. Full CPU
execution, board/scheduler/state integration and frontend qualification remain.
All new runtime comparisons are ROM-free native x86 bodies under Unicorn, not
additional original-Windows gameplay evidence. A68K remains unlinked; the
operational core checksum is unchanged. The user renewed the cap to 60% total
account usage during verification; work continues, with no commit or push.

### A68K CHK And Explicit Read Scratch — 2026-11-04

All 11 CHK targets / 424 encodings are qualified: 55,296 register/immediate
and 270,336 memory comparisons. The full suite passes O0/O2/UBSan with
**3,149,964 comparisons per build**, plus 15 separate host-binding guards.
Source hashes were verified before further edits. Every prior group's result
digest is unchanged, including the scripted-map fixture optimization.
Receipts: `port/build-a68k-chk/{O0,O2,ubsan}.json`.

Memory CHK retains read-wrapper/callback EDX as live flags even on the
non-trapping path. Tests vary direct allocation tokens, callback-return EDX,
all addressing forms, signed bounds, privilege state, zero-cycle boundaries
and odd exception vectors. The known upper-bound mask clears bits above bit 6;
the negative-value path only sets N. Both original behaviors are retained.
The observation binding carries EAX and EDX separately and rejects missing
provenance rather than assuming guest flags or zero. Real sound-board base
allocation and callback register origins remain integration work.

Dispatch coverage: **63,524/65,536 entries (96.93%)**, **1,447/1,667 targets
(86.80%)**. This is not weighted CPU completion. A68K stays unlinked, with no
new frontend, audio or original-Windows gameplay claim. The shared immutable
script maps remove redundant table initialization only; test cases and result
digests are unchanged. Duplicate stdout receipts were removed only after JSON
equality with the retained results. No commit, push or installed-core change.

### A68K Memory Arithmetic Qualification — 2026-11-04

The next related group passes the full O0/O2/UBSan comparison:
**3,338,124 comparisons per build**, plus 15 host-binding guards. All prior
result digests and source hashes were checked before the next edits.
Receipts: `port/build-a68k-memory-arithmetic/{O0,O2,ubsan}.json`.

| Added Group | Native Targets | Encodings | Comparisons Per Build |
| --- | --- | --- | --- |
| NEG/NOT Memory | 46/46 | 252 | 48,384 |
| ADDX/SUBX Memory | 12/12 | 384 | 55,296 |
| DIVU/DIVS Memory | 18/18 | 704 | 84,480 |

NEG/NOT retain the read-return EDX in the context observed by the write callback;
NEG publishes X after that write. ADDX/SUBX preserve both predecrements, A7 byte
steps and same-An aliasing; sticky Z comes from the second read's EDX, while X
receives the pre-merge flags. DIV preserves the read-return EDX at vector 5,
original timing refunds, quotient overflow and the already-approved host-IDIV
fault guard. The memory DIV suite includes 2,112 host-overflow prefix cases,
8,448 odd-vector cases and 147,840 retry-guard checks. It is not a new Windows
crash test or a correction to guest arithmetic.

Dispatch coverage: **64,864/65,536 entries (98.97%)**, **1,523/1,667 targets
(91.36%)**. Only memory Scc remains in the target inventory (144 targets / 672
encodings). Full execution and real board scratch provenance are separate work.
The original executable, reusable tools and compact receipts remain; task-owned
temporary focused libraries and duplicate stdout receipts were removed. No ROM,
save, installed-core, commit or push changes.

### A68K Complete Dispatch Inventory Qualification — 2026-11-04

Memory Scc adds **144/144 targets**, 672 encodings and 86,016 comparisons.
The complete suite passes **3,424,140 comparisons per build at O0, O2 and
UBSan**, plus 16 separate host-binding guards and the existing fault-retry
checks. Every prior result digest is unchanged; all source hashes were verified.
Receipts: `port/build-a68k-scc-memory/{O0,O2,ubsan}.json`. The remaining-target
inventory is empty: **1,667/1,667 targets and 65,536/65,536 entries (100%)**.

This is complete dispatch-inventory coverage, NOT a completed executable CPU.
Scc tests supply original entry EAX explicitly. Some forms retain its high bytes;
displacement/index forms derive them from addressing, SHI/SLS replace AH from
flags, SF clears EAX, and signed conditions publish IF. Missing required entry
scratch is a binding error. Propagating predecessor/callback EAX and recovering
real board read-return EDX/direct-base tokens remain execution/integration work.
Do not substitute a constant or portable host pointer for those original values.

The flow fixture previously assumed at least one known target was unrecovered;
its StopIteration at full coverage was corrected to always test an unknown token
and additionally test a known unrecovered target only while one exists. No
instruction behavior changed to satisfy this test. The compact failure record
is retained alongside successful results. Temporary focused libraries and
verified duplicate include/stdout files were removed; tools and compact receipts
remain. The operational build SHA-256 remains
`614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`.

Work stopped at the authorized **60% total account-usage cap** after collecting
already-running verification. Reported reset: **2026-11-11 06:21 CET**. Next:
complete execution-loop and native scratch propagation, board/scheduling,
Save States, then audio/frontend qualification. A68K remains unlinked and
Musashi operational. No installed-core change, commit or push.

### A68K Continuous Scratch Qualification — 2026-11-04

The user renewed the total account-usage cap to 65%. The new observed entry
and step APIs qualify **339/1,667 native targets (20.34%)**, or **13,417/65,536
encodings (20.47%)**, separately from the already-complete single-handler
inventory. The original sequence oracle enters `00462b1c`, uses the original
dispatch table, and executes continuously without restoring synthetic scratch
between instructions. It compares context, PC, live/published flags, cycles,
next-entry EAX, host control flags and full callback write arguments.

O0/O2/UBSan pass **74,548 streams / 206,533 executed steps** with identical
digest `4d55003eecd967688ad0d6c0965c6e9dc24e48120411ae0b4cd2116b9e5a5163`.
The 144 observed-write wrapper cases also agree at every build; their digest is
`2b98a18d395442aa64df3793571525cbd9bc41e013ba0c1eeb9eb460172ba918`.
Seven sequence guards and ten write-binding guards pass separately. Receipts:
`port/build-a68k-sequence/{O0,O2,ubsan}.json`; tools:
`tools/a68k_sequence_compare.py` and `port/a68k/test/sequence_shim.c`.
The full O2 single-handler regression passes 3,424,140 comparisons with all
prior result digests unchanged and 16 separate host-binding guards. Source
hashes were verified; `regression-O2.json` is retained and its identical stdout
duplicate was removed with a compact cleanup receipt.

Historical Make68K `moveq`, `opcode5`, `movecodes`, `addx_subx`, `asl_asr`,
`mul`, `abcd_sbcd`, `nbcd` and `Memory_Write` explain the recovered structure.
The original binary remains the final authority. Notable sequence effects:
register Scc leaves 4/6 in EAX; signed Scc restores DF through POPFD; ASR/ASL
can overwrite AH after writing Dn; word MUL keeps source high EAX bits; direct
byte/word write wrappers return descriptor tokens whereas long writes return
the native base. No native token is converted to a portable pointer.

The first callback fixture failure was a test-map omission: EXG changed the
address register before Scc, so a map installed only for the original address
was insufficient. The reusable fixture now maps the synthetic write callback
for all pages; no emulator behavior was changed to make the test pass.

Limits: real sound-board callback return provenance is still open. The observed
entry/step APIs reject accepted IRQ callbacks, unqualified targets and other
host control/trap bits before execution. Missing write provenance has no
ordinary-callback fallback. The full dispatcher, scheduler, Save States and
frontend integration are unfinished; A68K remains unlinked. No installed core,
ROM, user save, standalone, commit or push changes.


## A68K Source-Led Loop And MOVE Connections — 2026-11-04

The new portable execution connections follow historical Make68K
`CodeSegmentBegin`, `Completed`, `movecodes` and `Memory_Write`, with the ElSemi
binary authoritative for its actual table and behavior. Validation is targeted
at the changes; the general arithmetic/single-handler matrices were not rerun.

- Live loop: 56 original streams, 168 portable comparisons and nine guards at
  O0/O2/UBSan; no differences. Covers budget entry/exit, live versus published
  state, one/multiple-step continuation, extension fetch and callback EAX/DF.
- Original RLE table: all 65,536 entries match, decoded SHA-256
  `8398b07505414aa655a011dc6cf96f0ef879a4a3ab432e48a1bf41cf541c3d20`.
- MOVE write-return connections: 46 additional targets / 2,142 encodings,
  184 original streams and 368 portable comparisons at O0/O2/UBSan; no
  differences. Result SHA-256
  `f20172ab5aba62452249564208ad5af5a79f67259fd57b762b05ae8d4eed8a88`.
- Loop result SHA-256:
  `5bcf9404e093b67448c71e3c4c91cefaae57a9939ad6bbb5613318c842bc2c0d`.

Reusable tool: `tools/a68k_loop_compare.py`, optional `--move-writes`, using
`port/a68k/test/sequence_shim.c`. Receipts are in `port/build-a68k-loop` and
identify their exact source snapshots. Temporary test libraries are removed by
the runner. No ROM, installed core, production sound backend or standalone
checkout was changed. UBSan emitted only the existing duplicate-rpath linker
warning, with no runtime diagnostic.

Cumulative next-handler connection coverage is 385 targets / 15,559 encodings.
This is not overall CPU progress or historical-source acquisition coverage.
Unchanged source-derived bodies retain prior evidence. Native differences and
new portable connections require focused checks; complete sound-board,
scheduler, accepted-IRQ and Save State/frontend integration remain open.
Work stopped at the authorized 65% account-usage ceiling.


## A68K Source-Led Bus And Control Connections — 2026-11-04

The +5-point increment continues only new integration seams; unchanged
historical-source instruction semantics and prior native comparisons are reused.
Each group below passes O0, O2 and UBSan with zero differences. Counts are per
build configuration, not multiplied by three.

| Connection Group | Original Streams | Portable Comparisons | New Targets | New Encodings |
| --- | ---: | ---: | ---: | ---: |
| Read/MOVE/MUL returns | 978 | 1956 | 489 | 15400 |
| RMW/unary memory | 864 | 1728 | 432 | 8526 |
| Bit/shift/paired operations | 306 | 612 | 153 | 2386 |
| MOVEP/CMPM/MOVEM | 244 | 488 | 38 | 588 |
| Address/stack/DBcc | 160 | 320 | 32 | 396 |
| Even branches/calls/jumps | 148 | 296 | 46 | 4152 |
| Accepted IRQ | 96 | 192 | 0 | 0 |
| Software exceptions/USP | 168 | 336 | 7 | 17037 |
| Odd branch/jump vector-3 paths | 148 | 296 | 0 | 0 |

Read wrappers additionally pass 24 direct/callback cases and 27 guards,
including DATA versus READ, width/high-bit preservation, odd/cross-page
addresses and explicit missing/invalid-provenance failures. Seven entry guards
and two branch-binding guards pass in their respective groups. One initial
wrapper-fixture mismatch was an inverted test enum (DATA/READ), corrected in
the fixture; no emulator behavior was changed for that mismatch.

The source structure comes from Make68K `Memory_Read`, `Memory_Write`,
`movecodes`, `mul`, unary/bit/shift generators, `movep`, MOVEM generators,
`MemoryBanking`, `moveusp`, `trapv`, `Exception` and the interrupt emitter.
The original binary remains authoritative. In particular its IRQ clear mask
is 0x78, while the pinned historical source uses 0x7f with the older 0x78
commented out. The reconstruction retains the binary's 0x78. Accepted IRQ
restores the saved level in EAX after the exception; no C ABI register value is
assumed. Exception vectors use DATA-long, and callbacks see the original PC
publication order. JS/JLE exit distinctions and original saved-PC adjustments
remain unchanged. Odd jump destinations now reach vector 3; an odd vector
result still uses the previously approved explicit fatal-prefix policy.

Read/write/binder/ack callbacks expose original scratch provenance explicitly.
The fixture changes DF to prove propagation into subsequent instructions and
compares uninterrupted native dispatch with portable one-step and full-chunk
continuation. MOVEP restores EAX around writes; MOVEM empty masks retain EA
scratch. Existing single-handler APIs remain available separately.

Cumulative observed connections: **1,582/1,667 targets, 64,044/65,536 encodings**.
The seven trap-related targets account for 17,037 encodings because many
invalid/Line A/F opcodes share handlers. This is not total CPU completion or
proof that every historical-library body is identical. Still open: remaining
CHK/divide/status/return/RESET/STOP connections, real board callback provenance,
scheduler, complete CPU lifecycle, Save States and frontend integration.

Reusable tools are `tools/a68k_loop_compare.py`,
`tools/a68k_read_chain_compare.py` and `port/a68k/test/sequence_shim.c`.
Results and exact source-snapshot hashes are retained in the receipts below;
earlier receipts remain historical evidence after subsequent shared edits.
Temporary test libraries are removed automatically. Tests use synthetic guest
programs, not game ROMs. No installed core, active sound backend, standalone
checkout, user save, commit or push changed.

- `port/build-a68k-read-chain/{O0,O2,ubsan}.json`: `cb7a1d901673b3baa99ecd6240c4a8a747d2884a06aa5b6e7950d437dc13055a`.
- `port/build-a68k-rmw-chain/{O0,O2,ubsan}.json`: `9bbcbb7a6b82f2b92ea4d1597c9ea212fb96eb375b1aad140ed0e21da03f8cf1`.
- `port/build-a68k-misc-chain/{O0,O2,ubsan}.json`: `04e97dc9ce6acefe6f811bd52900698e741e99139044fb629a01cd9e35c11adb`.
- `port/build-a68k-bulk-chain/{O0,O2,ubsan}.json`: `ebbe1195cb2b407b676a55bb21fa847e4527050e0cbc0624348b4fb3337ac79b`.
- `port/build-a68k-control-chain/{O0,O2,ubsan}.json`: `d375f8ce70d87fc8ed6026e7a567a47e8ba8c35513c674cb26f5fef278d9c2fa`.
- `port/build-a68k-flow-chain/{O0,O2,ubsan}.json`: `b9b7769d3d3fbc64623eec17992fc0acc269e1c1c87870bc0c07f43bbc71829e`.
- `port/build-a68k-irq-chain/{O0,O2,ubsan}.json`: `4dda2e3537ec78819385abf2b68ba38fe4e44cde885353a6cb0542c21b1f3abc`.
- `port/build-a68k-trap-chain/{O0,O2,ubsan}.json`: `772684bde60dd0db13fe9bf13a752b410b4f36edc7272542109339f43739e524`.
- `port/build-a68k-odd-flow/{O0,O2,ubsan}.json`: `bca5508bfd7587a8681fb79427d4d5b2c71c34c67d2947260e9ed5ab2781f838`.


## A68K Remaining Internal Connections — 2026-11-04

The same authorized +5-point increment connects the remaining instruction
families. O0/O2/UBSan agree, with zero differences for each group below; counts
are per configuration. Existing arithmetic/status semantics are reused, with
focused cases covering only newly exposed bus, exception and scratch paths.

| Connection Group | Original Streams | Portable Comparisons | New Targets | New Encodings |
| --- | ---: | ---: | ---: | ---: |
| RTS/RTR/RTE/RTD | 120 | 240 | 4 | 4 |
| SR/CCR | 160 | 320 | 44 | 212 |
| CHK/DIV | 220 | 440 | 33 | 1272 |
| MOVEC/STOP/RESET | 96 | 192 | 4 | 4 |

RTS/RTR/RTE/RTD cover stack publication, user/supervisor restoration, masked and
accepted IRQ after RTE, odd return addresses and RTD's CPU gate. RTD's native
displacement-at-opcode behavior remains unchanged. The first fixture counted
the internal RTD-to-ILLEGAL tail as another guest instruction; that hook was
corrected without changing the emulator. SR/CCR retains `ReadCCR`/`WriteCCR`
structure and the native EAX=low-five-status-bits result. CHK memory read-return
EDX and DIV zero-divisor/quotient-overflow paths propagate their existing
native semantics; the approved host-IDIV fatal policy remains unchanged.

RESET now carries a pending prefetched successor across research step-limit
pauses. It executes that saved opcode even when its callback changes PC, flags
or instruction bytes, and despite a negative cycle budget. This mirrors native
00486e7d..00486eba. Its callback explicitly returns EAX/control provenance.
MOVEC retains native selector aliases and masking; STOP retains the original
idle/interrupt timing. Seven entry guards plus five new prefetch/binding guards
pass. The prefetched value is checked before dispatch; failed binding preserves
it for an explicit caller decision rather than silently consuming it.

The preprocessed observed-dispatch switch matches all **1,667 native targets
and 65,536 encodings**, with no missing or extra target tokens. Receipt:
`port/build-a68k-final-control/inventory.json`. This closes the target inventory
for internal connections, not every possible path or the sound CPU project.
Real native callback provenance, sound-board maps/scheduler, CPU lifecycle,
Save State integration and frontend operation remain open. Earlier group
receipts refer to their own exact source snapshots, not the latest source.
No general arithmetic regression or Windows fault audit was repeated.

- `port/build-a68k-return-chain/{O0,O2,ubsan}.json`: `87faba089d8d5aa704936c91557ef1f34c6ab44b3a27f978d5a61799b6baeabe`.
- `port/build-a68k-status-chain/{O0,O2,ubsan}.json`: `c54aa5a9600a84c62ad2354e97f4ed7f5236cc0e24050a1133b9a73a4c4e204a`.
- `port/build-a68k-checked-chain/{O0,O2,ubsan}.json`: `67e53d142b9a3987fd6323f7a5a85eacd8e77bdeb5b92cf58cf57b99a2d5de3e`.
- `port/build-a68k-final-control/{O0,O2,ubsan}.json`: `61ce6b1b5f7c27cc281f627137b6b6a6028f774fbca8a0f6ab523b13536e5e4d`.


The focused ordinary-loop regression after adding RESET prefetch passes its
56 native streams / 168 portable comparisons and nine guards at O2, retaining
result digest `5bcf9404e093b67448c71e3c4c91cefaae57a9939ad6bbb5613318c842bc2c0d`.
Receipt: `port/build-a68k-final-control/ordinary-loop-O2.json`. Its old unknown
handler guard used Line A; since Line A is now implemented, the fixture now
injects an unknown token explicitly. This was a stale test expectation, not an
emulation mismatch. The production-core artifact remains SHA-256
`614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`.

## Original SCSP-Board CPU RAM Map — 2026-11-04

`tools/a68k_board_map_probe.py` executes the original DATA-map loop at
004cd136..004cd162 and native word-read wrapper 004b3220 with synthetic RAM.
All 256 pages retain the same native base, covering a linear 1 MiB window.
Distinct words at 0x000000 and 0x080000 read back as 0x1122 and 0x3344.
The original allocation immediate at 004cdaff is also 0x100000; its returned
pointer is assigned to board+0x20389c at 004cdb0c. This checks the actual binary
ABI rather than relying on Ghidra's incomplete allocator argument recovery.

The inherited portable board uses `M2A_RAM_SIZE=0x80000` and masks CPU RAM
addresses with 0x7ffff; those two addresses therefore alias. This is a concrete
board semantic difference, not an A68K instruction failure or a proven
hardware-correctness bug. No game reachability is claimed. SCSP sample-address
masking is a separate matter. Result: `port/build-a68k-board/map.json`, with
original/source hashes. No ROM or production-board modification was involved.

User decision requested before changing the shared map: original 1 MiB linear
for both CPUs (proposed), retain the inherited mirror, or use per-backend maps.
The shared choice also affects Musashi and Save State payloads. No choice or
migration was implemented while awaiting the reply.


### Approved Native Sound RAM — Completed Group, 2026-11-04

The user approved both the linear 1 MiB CPU map and original ElSemi/A68K
word-swapped storage. The SCSP sample mask stays 0x7ffff; original DSP private
RAM and Model 1 RAM are unchanged. Musashi, reset-vector copies and SCSP
sample/DMA helpers adapt to the backing. The MAME DSP uses those same helpers.
No big-endian adapter remains in A68K.

The initial feature-bit choice overlapped the base ABI. Review caught it before
installation: current bits are 0x00800000 (map) and 0x00400000 (byte order), with
a compile-time non-overlap assertion. Both synthetic and complete-core checks
reject mismatched layouts without mutation. No user-save migration occurs.

Completed checks:

- Real sound-board synthetic fixture: independent lower/upper byte/word/long
  RAM, raw byte order and boot vectors, odd Musashi word access, last word,
  two-way SCSP DMA, unchanged sample wrap, exact cold sound archive/PCM
  continuation with both DSPs, and existing explicit DSP-fault shutdown.
  Original/MAME sound archives occupy 2,104,550 / 1,054,930 bytes.
- MAME baseline comparison: 64 cases, 16,384 sample frames, 8/16-bit samples,
  live DSP edits, start/reset and normalized shared RAM. Both fingerprints
  are `d8ca180c4448e7e5`. Only host byte order is normalized; PCM is exact.
- VF2 GL/ABI: 900 frames before save, four exact 12-frame state/PCM/image
  continuations, context recreation, corrupt/layout rejection and a fresh
  process. Both original and MAME DSPs pass. Before/after storage conversion,
  the captured PCM and rendered continuation are byte-identical; the entire
  payload is identical after pair-swapping only the 1 MiB RAM interval.
  Continuation CRCs: original `712f9ae9`, MAME `105dc853`, 8,820 sample frames.
- Daytona GL/ABI: unchanged Model 1 board passes the same Save State checks,
  including fresh-process continuation.

Results and provenance: `port/build-a68k-board/native-ram-integration.log`,
`native-storage-mame.json`, `storage-conversion-original.json`,
`storage-conversion-mame.json`, `native-storage-full-core.json`,
`native-layout-source-receipt.json`, and each isolated run's `result.json` /
`run.log`. `tools/compare_sound_ram_storage.py` retains the comparison procedure;
it is not a state loader or migration. The first sandboxed GL launch could not
initialize SDL; the isolated graphical rerun passed. No installed core change,
physical-controller check or audible/gameplay qualification is implied.

### SCSP CPU Read Callbacks — First Group, 2026-11-04

Original DATA wrappers plus real SCSP callbacks initially differed from the
inherited board in 13 of 18 synthetic reads. By explicit user decision, recover
the original CPU-facing behavior for both 68000 backends, separately from
chip-internal DMA/DSP access. Integrated byte/word slot/ring/DSP reads and the
native all-ones long read. Odd slot words preserve native byte assembly;
the last register byte reads the following native active byte, identified by
StartSlot 004af713 / StopSlot 004ab331, without exposing a portable C struct.
The SCSP CPU read window is the native 0x100000–0x10ffff range.

The expanded 21-case original-code comparison passes with zero differences.
The synthetic sound/archive/DMA suite still passes, including DMA readback of
coefficients whose CPU read now returns zero. VF2 again passes the 900-frame
GL/ABI same/fresh-process state/PCM/image check after this behavior change.
Tools/results: `tools/a68k_board_callback_probe.py`,
`port/build-a68k-board/scsp-callbacks.json` (pre-change),
`scsp-callbacks-native.json`, and `states-native-reads-vf2-gl/result.json`.

This is not a complete callback reconstruction: global-register aliases, MIDI
side effects, IRQ ownership and the actual A68K scratch binding remain open.
Those existing paths have not been silently replaced by guessed values.
The next ROM-free probe establishes another inherited difference: native SCSP
command storage wraps at 128 bytes; the port wraps at 32. A burst of 40 bytes
returns 1..40 natively but loses the first 32 through the current queue. Native
read bookkeeping and IRQ acknowledgement must be recovered as one group before
changing that lifecycle. See `tools/a68k_board_midi_probe.py` and
`port/build-a68k-board/scsp-midi-capacity.json`.

The user selected Astra with high effort for this next coupled reconstruction
block. Account usage was 71%, below the authorized 75% ceiling; pending work is
not being represented as cap exhaustion. No A68K production activation or
whole-CPU completion claim. The opcode-target inventory remains 1,667/1,667.


Cleanup for this increment removed 138 regenerable files (353,907,552 bytes):
isolated state/RAM/PCM/image captures, generated harness binaries/debug bundles,
and the superseded storage-adapter result. Reusable tools, per-run JSON/logs,
source/core hashes and final comparison results remain. The manifest
`port/build-a68k-board/native-layout-cleanup.json` records each removed hash.
No ROM archive, user save, prior research output or installed core was touched.


## SCSP Native FIFO, Global Registers, Timers And IRQ — 2026-11-04

Original EXE SHA-256 remains
`2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc`.
`tools/scsp_control_compare.py` executes its actual x86 bodies in Unicorn and
compares the real portable paths through `port/snd/test/scsp_control_shim.c`.
Native entries: enqueue 004c868a (stop before Windows notification 004c86a8),
CPU byte/word read 004ae870/004ae800, global read 004ab230, IRQ check 004aea40,
acknowledge 004aeac0, tick 004ab0e0, global update 004af050, and CPU byte/word
write 004afb00/004afa20. A68K request storage is 00528d38; chip is 0109aae8.

| Group | Cases |
| --- | ---: |
| Enqueue | 6 |
| MIDI Read, Including Empty/Wrapped Queue | 48 |
| Live Slot Monitor | 64 |
| IRQ Selection | 288 |
| IRQ Acknowledge | 288 |
| Timer Tick | 80 |
| Timer Write/Fraction Retention | 54 |
| IRQ Reset/Expired Timer Relatch | 72 |
| Actual CPU Global Byte/Word Write And IRQ Level Decode | 99 |
| Total | 999 |

All cases pass at O0/O2/UBSan; result SHA-256
`1fcaccd0d0cdfb3576bcfc567bc27a4352cd499e1fc1ed5babef5f7588131b03`.
Receipts: `port/build-a68k-board/control-levels-{O0,O2,ubsan}.json`.
The preceding 900/972-case receipts remain historical, before full-register
observations, CPU writes and IRQ-level decoding were added. A 40-command board probe now matches
native FIFO output (`scsp-midi-native.json`).

`scripts/check-dsp-integration.c` additionally runs an actual Musashi 68000
IRQ consumer, with SCIEB zero and MIDI level 6. All 40 commands arrive in RAM.
Its final empty read follows native acknowledgement-before-dequeue ownership.
Recreating the board and loading a pending-IRQ snapshot gives exactly the same
complete audio state. Existing sample/DMA/storage, DSP fault and both-backend
archive tests pass. Sound archives are 2,104,655 bytes (original DSP) and
1,055,035 bytes (MAME DSP), including the new SCP2 control schema.

GL-qualified core SHA-256:
`500dbe307099fd393404452402d372b74674dd12015f9e8607660b7b78404f07`.
900-frame GL/ABI runs pass for VF2 with original DSP and Sega Rally with MAME
DSP, four same-process replays each, context recreation, invalid-state
rejection, current NVRAM authority and exact fresh-process state/PCM/image
continuation. Results are in `states-control-final-vf2-gl/result.json` and
`states-control-final-srallyc-mame-gl/result.json` under the same evidence root.
The earlier `states-control-vf2-gl` receipt predates the CPU-write change.
No listening, physical-device, whole-game or actual RetroArch UI claim.

Remaining native callback boundaries: raw global-object aliases outside the
ordinary range, full write widths/edges, chip-internal DMA IRQ, warm reset and
A68K host scratch. These tests do not run the original Windows sound thread or
qualify complete A68K production integration. Internal opcode inventory stays
1,667/1,667, distinct from overall CPU completion. Installed core unchanged;
no commit, push, ROM copies or dependency installation.

Cleanup removed 66 task-owned generated files (176,843,733 bytes), retaining
all nine per-run JSON/log files, reusable tools, final build/integration logs
and source hashes. `port/build-a68k-board/control-cleanup.json` records the
removed capture/harness hashes; `control-source-receipt.json` identifies the
qualified sources. No prior research capture or user data was removed.


### SCSP Read-Callback Register Provenance

`tools/scsp_callback_provenance.py --compare` reuses the control fixtures and
executes original DATA wrappers followed by their actual callbacks. It checks
the new frontend-neutral `scsp_cpu_read_observed` research helper: 664 exact
EAX/EDX/EFLAGS cases and 24 guarded raw-object aliases, each at O0/O2/UBSan.
The 688-row native observation digest is
`89dc4c5d16da137caba0c9a797746a11272448eb6a8f9a69f4483dfb87239e9a`.
Receipts: `port/build-a68k-board/scsp-read-scratch-{O0,O2,ubsan}.json`.
The initial `scsp-read-scratch.json` is native inventory only.

The helper returns explicit integer PE tokens, never host pointers. Unsupported
raw aliases fail before reading/mutating MIDI. Slot, ring, write-only DSP and
ordinary global-register widths preserve their distinct scratch and final
flag-producing instructions. No production A68K page binding is installed.
The original raw 0x444 alias demonstrates separate side-effect and object-byte
address masks; full alias reconstruction remains open.

The research helper's addition builds in the complete core; the synthetic
board/IRQ/DSP/archive suite still passes. It is uncalled by the active Musashi
path, so the preceding GL tests were not repeated solely for its addition.
`control-scratch-build.log`, `control-scratch-integration.log` and the refreshed
`control-source-receipt.json` retain this exact scope and current build hash.
No generated scratch-test shared libraries remain; the tool uses temporary
directories. This adds callback evidence, not another whole-CPU test campaign.


## SCSP Write/Acknowledge Provenance And A68K Page Binding — 2026-11-04

The new research `port/a68k/scsp_bus.c` binds the original SCSP window
0x100000–0x10ffff in caller-owned DATA/WRITE page tables. It preserves unrelated
pages, carries explicit EAX/EDX/control observations for reads and EAX/control
for writes/acknowledgement, and rejects unsupported paths before chip mutation.
There is no value-only callback fallback or portable-pointer substitution.
The installed core and active Musashi CPU are unchanged.

`scsp_cpu_write_observed` covers qualified ordinary global byte/word/long
writes. A long callback stores both words before either register update, as
004af900 does; it is not implemented as two sequential ordinary word callbacks.
Sparse global dispatch preserves its returned selector token and CMP flags.
Timer callbacks return the fractional counter; interrupt clear follows native
IRQ branch scratch; SCILV writes return the MIDI level and byte-OR flags.
`scsp_cpu_ack_observed` preserves 004aeac0's final OR EAX,-1. Write-return EDX
is outside the recovered executor's write observation contract, not qualified.

| Actual Binding Path | Cases | Result |
| --- | ---: | --- |
| DATA Read EAX/EDX/EFLAGS | 664 | Native exact |
| WRITE Global State/EAX/EFLAGS | 960 | Native exact |
| IRQ Acknowledge State/EAX/EFLAGS | 576 | Native exact |
| Unsupported Read Alias Guard | 24 | Rejected without MIDI mutation |
| Unsupported Write/Width Guard | 1,344 | Rejected without control-state mutation |

All pass at O0/O2/UBSan through actual `a68k_read_live` /
`a68k_write_observed` and the new acknowledge binding. The write/ack/guard
digest is `354094e9d9cd3d740e0bdd420499da82929d6c66474ee19ceba5c13b8bcf24f2`;
the read digest remains
`89dc4c5d16da137caba0c9a797746a11272448eb6a8f9a69f4483dfb87239e9a`.
Tools: `tools/scsp_write_scratch_compare.py --bound` and
`tools/scsp_callback_provenance.py --compare --bound`. Receipts:
`port/build-a68k-board/scsp-{write,read}-bound-{O0,O2,ubsan}.json`.
The preliminary direct-observer write result is `scsp-write-scratch-O2.json`.

Complete-core compilation and the existing real-board Musashi IRQ, DSP, RAM,
DMA and cold-archive integration suite pass. These new research APIs are not
called by the active frontend CPU, so no additional game run was needed solely
for their addition. State schema and raw Save RAM are unchanged this increment.
No full A68K scheduler, guest instruction stream through this board, audible
output, physical input or production activation is claimed. Internal opcode
coverage remains 1,667/1,667; complete CPU integration has no closed denominator.

### Native CPU DMA Difference — Initial Probe

The pinned global-update sparse table at 004af294 maps registers 0x12–0x17
to index 2, whose target 004af26c returns without a transfer. The native word
callback still stores those register values. `tools/scsp_dma_write_probe.py`
executes actual writes at 004afa20 and compares the existing CPU-facing port
interface on a synthetic RAM-to-coefficient request. Original coefficient
0x369a and control 0x1002 remain unchanged; the inherited port writes source
0x1122 to the coefficient and clears the start bit (control 0x0002).
Receipt: `port/build-a68k-board/scsp-dma-before-decision.json`.

This proves a callback difference, not game reachability. The user was asked
whether to preserve original CPU behavior or retain the inherited transfer.
At that stage no DMA change was applied and the research write observer
rejected DMA ranges; that rejection was not advertised as native emulation.
The subsequent user decision and implemented result are recorded below. Chip-internal DMA/DSP policy remains separate.

Only reusable tools, small result JSONs, build/integration logs and a source
receipt were added; temporary comparison libraries remove themselves on exit.
No ROM copies, generated game code, installed-core replacement, commit or push.


## Approved ElSemi CPU DMA Behavior — 2026-11-04

The user confirmed original behavior. CPU global DMA stores now pass through
`UpdateCpuReg`, which leaves the register values visible but does not invoke
the inherited DMA update. This is common to the Musashi bus and recovered
A68K write observer, independently of DSP backend. Internal DMA register access
continues through `w16`/`UpdateReg` and is not changed. No new option or snapshot
layout was introduced; native raw Save RAM remains unchanged.

`tools/scsp_dma_write_probe.py --require-match` now matches the actual original
word callback: coefficient 0x369a and control 0x1002 remain after the synthetic
request. A separate internal-interface regression check copies 0x1122 in both
directions and clears its internal start bit. Receipt:
`port/build-a68k-board/scsp-dma-elsemi.json`; the pre-decision receipt is retained.

Expanded actual A68K page-binding tests pass **1,168 writes, 576 acknowledges
and 1,136 nonmutating write guards** at O0/O2/UBSan. DMA byte/word/long writes
now preserve both native state and sparse-table EAX token 2/CMP flags. Result
digest: `a48a948b50552951566ef4fa0bfdb440a300a36bc99b178434c8b62c3e7ae787`.
Receipts: `port/build-a68k-board/scsp-write-dma-{O0,O2,ubsan}.json`. The 664
qualified read observations and 24 read guards are unaffected. These figures
are callback coverage, not a complete A68K sound CPU or all-input proof.

The actual Musashi bus test now checks no-transfer behavior for byte/word/long
CPU DMA stores and both directions. Shared RAM, sample-mask, MIDI IRQ, original/
MAME DSP, cold archive and fault handling checks continue to pass.

Core SHA-256: `d565b0aa04e70674cf9c82a754fe339ae7e1a69e1596411efe37e6aaeeef7d39`.
VF2/original-DSP and Sega Rally/MAME-DSP 900-frame GL/ABI checks pass four
same-process replays, context recreation, malformed-state rejection and exact
fresh-process state/PCM/image continuation. VF2 additionally qualifies current
NVRAM authority; this run did not perform the Sega Rally NVRAM-authority check,
which is not claimed. Per-run results/logs are retained in
`states-dma-elsemi-vf2-gl` and `states-dma-elsemi-srallyc-mame-gl` under the
same evidence root. No actual RetroArch UI, listening or gameplay claim.

Reusable tools, original-code receipts and build/integration logs are retained.
No installed-core change, ROM copy, dependency installation, commit or push.
Remaining: slot/DSP/output-MIDI write reconstruction, raw object aliases, full
A68K scheduler/lifecycle and frontend integration. Astra High remains appropriate.

This increment removed 44 task-owned capture/harness files (117,895,823 bytes).
The six per-run JSON/log files remain; `dma-elsemi-cleanup.json` records removed
hashes. No user files or earlier research outputs were removed.

### A68K And Musashi DSP Ring Control — 2026-11-12

The ElSemi CPU update at 004af06d takes base bits 0–6 and length bits 7–8
from the stored register word. A68K receives the length selector in EAX.
The zero selector returns after AND, while selectors 1–3 return after an
equal CMP. Both paths leave ZF and PF set. The CPU callback now supplies all
seven base bits to the DSP. The inherited chip-internal writer retains its
six-bit decode. The MAME DSP still masks its shared RAM addresses to 0x7ffff.

`tools/scsp_write_scratch_compare.py` with `--bound` compares the compiled C
page binding to the original x86 WRITE wrappers executing under Unicorn.
The comparison includes the stored register, the DSP's base and length, EAX,
and EFLAGS. It exercises byte writes with nonzero data in the other lane,
aligned word writes for all 128 bases and four lengths, and long writes with
the ring control in either half. O0, O2 and O2 with UBSan all passed 1,760
writes and 576 acknowledgements against the original, plus 1,056 unsupported
write cases checked for rejection before mutation. Each configuration produced
digest `60fd0281656bd51425c8881ee95043761afe0d8c58dcb9f383130af37d033653`.
Receipts are in `port/build-a68k-board/scsp-write-ring-{O0,O2,ubsan}.json`.

Through the active Musashi bus, `scripts/check-dsp-integration.c` programs a
table read at MADRS 0xffff. A long write selects base 0x3f and the DSP runs.
A byte write changes the base to 0x7f and the original DSP reports exactly
0x11dffe, exercising the approved private-RAM bound. The synthetic macOS
sound integration suite passed and the research core built. This group's
runtime evidence covers the synthetic board. Game execution with A68K still
depends on the remaining sound-board callbacks and scheduler hookup.

### SCSP Voice Register Stores And Key-On Sample Addresses — 2026-11-12

The A68K WRITE callback now implements the eleven store-only words in each
slot, covering byte offsets 2–7, 12–15 and 20–31. ElSemi routine 004af810
returns sparse-table index 4 below offset 20 and the register offset above
that boundary. The final CMP supplies the flags. Long stores put both words
in the slot before the second update determines the returned EAX and flags.

`tools/scsp_slot_write_compare.py` compares the actual A68K page binding
with the original x86 wrappers. At O0, O2 and O2 with UBSan, 164 writes
matched the original, and 220 unsupported accesses preserved all 32 register
banks and the caller's return state. Fixtures cover every byte offset and
width on slots 0, 1, 15 and 31. The store digest is
`62cb124e0b4ccdca1a7c329e110407c5ae71f7c775dea7fb3ce4a427dd9a44b9`.
The existing 3,392-case global control regression reproduced its O2 digest.
The macOS core and synthetic sound integration suite passed.

The same probe runs a native key-on through the CPU WRITE wrapper, edits
the base register, then executes the native sample-address and load
instructions. The portable side programs the CPU-facing slot registers and
reads an integral-position sample through the current voice engine.
Six synthetic cases cover both sample widths. At key-on, 004af710 retains
20 base bits for 8-bit PCM and applies 0x7fffe for 16-bit PCM. The tested
readers add the cursor to the latched base. At base 0x84000 an 8-bit voice
read 0x44 from the upper half while the port read 0x11 from the lower half.
Editing the low address word after key-on changed the port's sample only.
With a 16-bit base of 0x7fffe the second word was fetched at 0x80000.
With an 8-bit base of 0xfffff and cursor 1 the native byte-lane adjustment
read offset 0x100001. The witness used a distinct Unicorn guard page beyond
the synthetic allocation. Its contents have no defined Windows equivalent.
Occurrence in games is unknown. Receipts are in
`port/build-a68k-board/slot-store-keyon-{O0,O2,ubsan}.json`.

### Voice Key-On, Fault Delivery And Cold Continuation — 2026-11-12

Both CPU paths capture the sample base on a successful key-on. 8-bit PCM
keeps all 20 bits and selects the original byte lane. 16-bit PCM aligns
and masks the starting base to 0x7fffe. Subsequent reads use the allocated
1 MiB. The first escaped read freezes sound execution, reports the byte
address, and stops content. The SDL, headless and Libretro paths identify
voice faults separately from original DSP faults.

The original WRITE wrappers and the actual A68K page binding agreed on 180
slot writes at O0, O2 and O2/UBSan. Another 204 accesses returned before
mutation. The mixed-envelope fixture compares register banks, EAX, EFLAGS,
active flags, envelope states and latched sample bases across all 32 slots.
It does not qualify the full pitch, LFO or envelope algorithms. The 5 valid
integral-position reads matched, including an edited address after key-on
and a word crossing into upper RAM. At 0x100001 the C path reported the same
address that the x86 probe read in a synthetic guard page. Receipts under
`port/build-a68k-board/slot-keyon-mixed-{O0,O2,ubsan}.json`.

Through Musashi the sound integration suite exercised the actual frontend
stop notification once, reset recovery, and exact cold PCM after changing
the live start register with both DSP backends. The MAME DSP regression
matched its 64 historical fixtures. VF2/original DSP passed 900 frames in
the GL/Libretro ABI runner with repeated and fresh-process state/PCM/image
continuation. The local receipt is `voice-keyon-vf2-gl/result.json` in the
same evidence directory. macOS Libretro, SDL and headless targets built.

**Fractional PCM decision.** A separate x86 witness executes 004aceed through
004acf39 for the first half-step of an 8-bit voice. With previous sample
zero and current byte 0x44, ElSemi produces 8704. At base 0x4000 the port
produces 10880 using the current byte and next byte 0x11. At base 0xfffff
ElSemi still produces 8704, while the port's second read escapes to 0x100001.
This synthetic difference affects the shared voice interpolator before the
selected DSP. Frequency in games and audible impact remain open.

### Shared PCM Interpolation And Loop Boundary — 2026-11-12

ElSemi 1.1a computes signed PCM from the previous sample and the current
RAM fetch using 12 fractional bits. The 8-bit routines refresh history when
the sample index changes. The 16-bit routines include cursor bit 11 in the
comparison. At key-on with sample byte 0x44 and fraction 0x800, both original
and reconstruction produce 8704, including at the final valid logical byte.

`tools/scsp_slot_write_compare.py` executes the actual x86 interpolation and
history branches (004aceed / 004acfb1 and 004ae6ed / 004ae7b2). The compiled
slot paths match all 24 signed PCM/history cases at O2 and O2 with UBSan.
Six address cases, 180 slot writes and 204 guarded writes also pass.
`scripts/check-dsp-integration.c` verifies cold PCM continuation on both
DSPs after a live sample-base edit, rejection of the SCP3 marker in otherwise
valid board snapshots, and the frontend error on a real escape. Both standalone
macOS targets and the Libretro core built successfully.

The MAME DSP and pinned baseline have the same PCM/RAM/DSP fingerprint
`a082a15f0f9c5a25` for 64 fixtures supplied with identical mixer input.
With active voices, the full-path fingerprints differ as expected after the
shared interpolator change. Sega Rally passed the macOS Libretro GL harness
with the original DSP after 900 frames, four replays and exact 12-frame
fresh-process continuation. The joint listening check remains in ROADMAP.md.

Under `port/build-a68k-board/`, see `slot-interp-{O2,ubsan}.json`,
`interpolator-mame-regression.json` and `voice-interpolation-srallyc-gl/result.json`.

**Separate forward-loop witness.** Dispatch entry 17 (004acd90) processes
an 8-bit voice at base 0xfffff with loop start 0, end 1 and step 4096.
It resets the cursor to 4096 after the first sample. The second fetch in
Unicorn reads offset 0x100001 in a synthetic guard page. The inherited
portable loop resets the cursor to 0. This witness does not establish that
a game programs this loop or that the original Windows process crashes.

### ElSemi PCM Loop Modes — 2026-11-12

The original voice dispatch at 004aaa19 selects 32 handlers by loop mode,
sample width and LFO configuration. The comparison executes each complete
handler in Unicorn with synthetic samples and unity LFO gains. It compares
the pre-envelope PCM, cursor, direction, active and key bits, and previous
raw sample at every step. All 288 sequences (2,080 steps) match at O2 and
O2/UBSan. Receipts and the pinned executable hash are in
`port/build-a68k-board/pcm-loops-{O2,ubsan}.json`.

| Mode | Recovered Boundary Behavior |
| --- | --- |
| One-shot | Stop and clear key-on when the advanced integer cursor reaches the end. |
| Forward | Restart at (loop start + 1) with zero fractional phase. |
| Reverse | At the end, clamp to the end and enter reverse. Below the start, jump back to the end. |
| Ping-pong | At the end, clamp to the end and enter reverse. At or below the start, clamp to the start and resume forward. |

Both comparisons in the bidirectional handlers use the integer position
computed before the first clamp. A backward underflow is zero-filled by
the x86 shift. The suite includes underflow, equal and inverted endpoints,
fractional overshoot, mode changes with the reverse flag already set and
32-bit pitch-modulation multiplication. The forward boundary witness at
base 0xfffff now matches the native first cursor, then stops on 0x100001.
The sound integration suite confirms a single frontend notification and
exact cold PCM in all four modes on both DSPs. The existing SCP4 payload
contains the cursor, direction and interpolation history.

Sega Rally passed the 900-frame GL/ABI Save State check with original DSP
and exact fresh-process continuation. The compact receipt is
`port/build-a68k-board/pcm-loops-srallyc-gl/result.json`.
The 64 matched-input MAME DSP fixtures retain fingerprint a082a15f0f9c5a25.
These comparisons cover synthetic modulation gain and bounded attract
execution. Joint listening in RetroArch remains scheduled.

### Sound CPU Pitch Register Survey — 2026-11-12

The optional `--pitch-survey` in `tools/scsp_slot_write_compare.py` executes
the native x87 initializer at 004af337 and pitch routine at 004ab340.
It compares all 16,384 octave/fine pairs with the port's compiled Step
function at each precision. With 53- or 64-bit x87 precision, 3,598 pairs
differ from the port (526 at octave +4 and all 3,072 at +5 through +7).
At 24-bit precision 4,384 differ. At octave +4 and fine 498 the x86 shift
wraps in all three cases, yielding a step of 16 against 97,408 in the port.
Key-on at 004af73b inlines the same calculation as a pitch-register update.
SM2 uses the same pitch formula as the inherited port in Scsp::Step.
The original process control word at table initialization and use of the
affected pitches during gameplay have not been established. See
`port/build-a68k-board/pcm-loops-O2.json` for per-octave results.

### Windows SCSP Pitch Acquisition And Shared Voice Pitch — 2026-11-12

Windows 11 ARM build 26200 in VMware Fusion ran the pinned ElSemi 1.1a
executable with Fighting Vipers from the existing share. The diagnostic
copy adds an app-local XAudio2 manifest. Eight bytes at 004af3c4, after
the last frequency was stored, record the restored x87 control word and
park the process for ReadProcessMemory. The initializer and its callers
retain their original instructions. The process returned CW 0x007f
(24-bit significand, nearest-even). All 1,024 little-endian uint32 entries
hash to `0f6bc7835cdda22c5203af777e3bf9e078a325a0a516ecd35ef896575ab07492`.
263 differ from the exact integer frequencies. This measurement concerns
sound initialization in the sampled Windows startup path.

The C engine reproduces that rounding with integer arithmetic, then shifts
in 32 bits and uses the native unsigned high product. The pinned x86 in
Unicorn reproduces the Windows table byte for byte. At O2 and O2/UBSan
all 16,384 octave/fine pairs agree for key-on, live Musashi-facing writes
and A68K page callback EAX/flags. The slot bus suite compares 196 writes
and 188 correctly rejected accesses. The octave +4/fine 498 step is 16.
Receipts are `pitch-{windows,O2,ubsan,mame}.json` under
`port/build-a68k-board/`. The Windows probe is reproducible with
`tools/prepare_scsp_pitch_probe.py` and `port/snd/test/windows_scsp_pitch.ps1`.
The latter takes the reference DirectX dependencies and a runner-provided
content path. The payload needs the distribution's scripts and base INI.
Pass the collected JSON as `--windows-pitch` to `tools/scsp_slot_write_compare.py`.

The integration suite passed same/fresh board PCM continuation with a live
high-octave update across both DSPs and all loop modes. The 64 matched-input
MAME DSP fixtures retain a082a15f0f9c5a25. The macOS GL/ABI core passed
900 Sega Rally frames, four replays and exact 12-frame fresh-process
continuation. See `port/build-a68k-board/pitch-srallyc-gl/result.json`.
The standalone build also passed. Full A68K scheduling and the joint listening
check are still open.

The next independent witness executes the original envelope updater at
004ab390. With zero Decay 2 rate, levels 0, 1 and 31 clear active and
key-on in the original. The inherited core keeps both set. Levels 32
and 33 keep both set in both engines. The original computes envelope level
with 8 fractional bits, the port with 16. At 004ae940 the original rate
index base is twice the sum of octave and key scaling, plus the high fine
bit when scaling is enabled. The port doubles only the key scaling term.
Gameplay reachability of the quiet-tail witness has not been established.

### Shared ElSemi SCSP Envelope — 2026-11-12

The original table initializer at 004af5aa, executed with the measured
0x007f x87 control word, matches all 64 attack and 64 decay rates.
The rate calculator at 004ae940 and phase updater at 004ab390 match 4,096
register and level combinations at O2 and O2/UBSan across the four phases.
The comparison includes fractional positions at the level-32 cutoff,
saturation, key scaling, hold and release. The bus comparison covers 232
supported slot writes and 152 guarded accesses. It checks all voices'
volume, rates, phase, key and hold data plus the x86 completion flags.
Live envelope writes recalculate active slots without restarting attack.

Cold PCM continuation passed on both DSPs with a live attack-rate change
and across all four loop modes. The 64 matched-input MAME DSP fixtures
retain a082a15f0f9c5a25. The macOS GL/ABI run completed 900 Sega Rally
frames, four replays and exact 12-frame fresh-process continuation.
Standalone also built. Receipts are in `port/build-a68k-board/` under
`envelope-{O2,ubsan,mame}.json` and `envelope-srallyc-gl/result.json`.

A separate 8-bit PCM voice trace compares SDIR off/on at level 31 with
zero Decay 2 rate. Handler 004acec0 silences both. The port's inherited
direct route skips the envelope when SDIR is on. The user approved the
native PCM routing follow-up, including separate DSP-send verification.

### PCM Direct Mode And Mixer Boundaries — 2026-11-12

The first PCM change applies ALFO and envelope processing with SDIR on.
The pre-envelope interpolation and loop fixtures still compare the raw
sample at the original boundary. The direct-mode cutoff witness now clears
active in both engines with SDIR off and on. This change passed O2/UBSan
and a separate 900-frame Sega Rally GL/ABI run with exact cold continuation.

The subsequent mixer change applies native TL, separately rounded direct
pan/send gains and the native DSP send for PCM sources. The MAME DSP stores
the contribution divided by 16 to account for its input shift. The
comparison initializes the original gain tables with CW 0x007f and executes
004aeb2d through 004aebbb. Left, right and signed DSP input match in 4,096
synthetic cases before the master output stage. The final core builds and
passes the board integration suite. The GL run above predates this last
gain change. Receipts: `port/build-a68k-board/pcm-direct-envelope.json`,
`pcm-direct-srallyc-gl/result.json` and `pcm-mix-O2.json`.

### Native Mixer Dispatch And First-Sample Routing — 2026-11-12

`tools/scsp_mixer_block_compare.py` executes both branches of 004af7f0 in
the pinned ElSemi binary and records ring writes, DSP input and stereo output.
The DSP is stopped so each new MIXS contribution can be measured at entry.
Four three-sample inputs exercise a gain change, ring inhibition, one-shot
completion and different previous/adjacent samples. The portable comparison
calls the production renderer one frame at a time on each DSP backend,
normalizing MAME's DSP input to the original units.

With the old gain at unity and TL changed to 8, the ordinary mixer (004aa950)
writes 8192 to ring index 0 three times. The interleaved mixer (004aead0)
writes 4092, 2896 and 2896 to indices 0, 32 and 0. Both send 1482752 to the
DSP on the first sample. Both portable DSP backends receive this same value,
while the port writes 16368 to the ring. STWINH suppresses native ring writes
only on the interleaved route in this fixture. When the one-shot voice ends
on sample two, the ordinary three-sample block sends zero for all three.
The interleaved route and the current port send 1482752 twice, then zero.

The ordinary route uses saved sample history. The interleaved route reads
adjacent sample data. The game hook at 004c6710 selects the interleaved
route for the recovered game record mapped to `hotdo`. Both native mixers
reach the DSP. Synthetic traces establish these differences independently
of host audio playback. Receipt: `port/build-a68k-board/mixer-native-block.json`.

The final gain build passed the Sega Rally GL/ABI check with the original DSP
after 900 frames, four same-process replays, context recreation and exact
12-frame fresh-process continuation. Receipt:
`port/build-a68k-board/pcm-mix-srallyc-gl/result.json`. Listening and full
A68K execution remain open.

### Native SCSP Board Exchanges — 2026-11-12

The mixer probe also runs a two-instruction DSP program emitted by ElSemi's
original x86 generator. It routes a PCM send through a half-gain coefficient
into an effect return with the direct stereo path muted. All 24 cases passed
across both mixers, four partitions of three samples and three routings.
Input buses 0 and 15 and returns 0 and 13 were exercised. Monitoring return
12 while writing return 13 produces silence. The original clears the effect
registers before each generated call and the 16 mix inputs after it.

For a one-shot ending on sample two, the ordinary mixer sends the first sample
only when the first block has length one. It tests voice activity after the
block's voice pass and before transferring its saved samples to MIXS. The
interleaved mixer sends both samples in every partition. A nonzero input of
1482752 yields effect 2896 and stereo 11584 on each channel in this fixture.
These are original program values before Windows playback.

`tools/scsp_board_exchange_probe.py` exercises the original board call at
004cc710. The machine frame at 004cc7a0 has 210 slices with sound enabled.
In the SCSP path 004aefb0 adds trunc(11289600 / (fps × 210)) to a persistent
accumulator and consumes 256 units per tick. Each tick runs A68K, updates
timers and then recomputes IRQ. The first CPU budget in each slice is 272.
Within a slice the next budget subtracts the signed remainder of the previous
run. With CPU execution inhibited, timers and IRQ still advance. Timer A in
the fixture raises a masked level three on tick two, visible at CPU entry
on tick three. All four scheduler fixtures passed at 58 and 60 Hz.

The native frontend calls the machine frame through board vtable +4. Its
separate audio callback at +0x28 (004cc4a0) selects the mixer for SCSP
boards. 004eecf0 computes the host channel count from twice the sample
rate and the audio device's frame rate. Board setup at 004cd392 halves the
truncated count. With 44100 Hz and synthetic device rates of 58 and 60 Hz
this produced 760 and 735 samples per block respectively.

The original SCSP board setup copies the 128-byte A68K context at 004cd30b,
then assigns 004aeac0 to the template at 004cd377. The live acknowledge
pointer retains 004b3090 (autovector). Using the existing 40-command guest
IRQ program from `scripts/check-dsp-integration.c`, the original scheduler
produces 40 acknowledges and 40 MIDI reads, and A0 finishes at 0x2050.
Forcing only the live pointer to 004aeac0 produces 41 acknowledges and 41
reads, with A0 at 0x2052. Both runs deliver commands 1 through 40 in order.
The extra empty read in the earlier Musashi fixture measures that second
binding. The 999 earlier isolated control comparisons remain valid.
This synthetic board test skips the Windows notification after enqueue.
Receipt: `port/build-a68k-board/scsp-board-exchange.json`.

On Windows 11 ARM the original Fighting Vipers process was sampled on 16
advancing frames (5 through 58, multiple A68K program counters). Every sample
had live 004b3090, configured 004aeac0, 760 frames per block and ordinary
mixer mode. `tools/prepare_scsp_pitch_probe.py --manifest-only` retains the
original executable instructions while binding the local XAudio2 runtime.
`port/snd/test/windows_scsp_pitch.ps1 -ObserveBoard` reads the pointers and
frame counter from that isolated process. Receipt:
`port/build-a68k-board/scsp-exchange-windows-fvipers.json`.

Sega Rally and The House of the Dead each yielded a further 16 advancing
Windows frame samples. All had the same live/configured acknowledge pair
and 760 samples per block. Sega Rally selected mode 0 and House selected
mode 1. The unmodified hotd archive key initially timed out with the MAME
parent revision. The VM user could not create a symbolic link to the matching
revision. For the successful run, `--manifest-only --hotdo` changes one padding
byte in the read-only game key so the diagnostic opens the existing
`hotdo.zip`. All original executable sections match byte for byte.
Receipts: `scsp-exchange-windows-{srallyc,hotdo}.json` in the same directory.

The ring-to-voice comparison sets the read indices to 63 and 0, at modulation
depth 15. Twelve original traces cover both mixers, 8/16-bit samples and
signed ring values −8, 0 and +8. The ordinary one-shot handlers read just
the original PCM address. The interleaved routine reads both ring words
and displaces the two PCM fetches by −4, 0 or +4 bytes. In a separate
two-voice fixture the first voice writes 0xc08f to cell 62. The next voice
reads that same cell twice at depth 7, fetching at bytes 225 and 224
instead of 257 and 256. This establishes same-sample data flow between
voices for that route.

The original CPU MIDI output producer was also traced through the page
wrappers. Across 260 alternating word and high/low byte stores, each update
enqueues the register's low byte. The write cursor wraps at 128 and the
separate byte count at 256. After 260 stores both read 4 and the ring
contains the last 128 queued bytes. A receiving cabinet, wire timing and
the approved Manx TT extension are outside this producer measurement.

**Live IRQ binding and i960 return path.** The SCSP board clears the
accepted IRQ at CPU entry and uses the original live autovector (004b3090).
Pending sources are checked again on normal board events. On Musashi the
40-command guest now performs exactly 40 ordered MIDI reads and finishes
with A0 = 0x2050. The earlier 41st read belongs to the forced template
callback experiment. The integration test also restores an outstanding IRQ
in a fresh sound board. The A68K research bus passed 576 acknowledge cases
against the live callback, alongside 1,760 writes and 1,056 rejection checks
at O2 with UBSan. Musashi is the production CPU for this test.

`tools/scsp_board_exchange_probe.py` checked both native i960 sound-port
bases (0x009c0000 and 0x01c80000). After enqueuing MIDI output, 48 byte,
word and longword reads through 004c7650/004c7620/004c75f0 returned 7 at
low-byte offsets 2 and 4, and 0xff elsewhere in the sample. The latter
reads decremented the host command count at 005aa74c down to zero. The
separate IRQ10 count was unchanged. Watchpoints recorded zero accesses to
the output ring, cursor or count during those host transactions. A scan of
all file-backed PE sections identified two absolute references to the ring
base, both writes. The apparent reference to ring+124 at 004af513 indexes
the following table. A watchpoint run of its initialization loop confirmed
that it never touches the ring. This qualifies the original i960 handlers;
the separate Manx TT serial return path is documented in MANX_TT_CABINET_AUDIO.md.

Sega Rally passed the isolated macOS GL/Libretro ABI run on the autovector
build after 900 frames, with four same-process replays, graphics-context
recreation, invalid-state rejection and 12 exact fresh-process continuation
frames. Compact local receipts in `port/build-a68k-board/`:
`autovector-bound-ubsan.json`, `scsp-board-exchange.json`,
`autovector-integration.log` and `autovector-srallyc-gl.json`.

### Native MIDI And DSP Write Returns

`tools/scsp_write_exchange_probe.py` executes the original 1.1a A68K
page wrappers and SCSP callbacks under Unicorn. It checks 70 MIDI writes,
80 DSP writes (including six DSP starts) and ten two-instruction guest
streams. The compact receipt is `port/build-a68k-board/scsp-write-exchange.json`.

- **MIDI.** At 004af0c9, EAX returns the updated seven-bit cursor. The
  INC of the separate byte count supplies the arithmetic flags, with CF
  cleared by the preceding AND. Tests cross both rollovers and the signed
  overflow at 127. A longword at 0x404 ends in the MIDI update. At 0x406
  it enqueues the byte and then returns EAX = 8 and flags from the update
  for 0x408.
- **DSP.** Ordinary writes in the sampled DSP banks return the original
  chip address 0109aae8 in EAX. The final CMP tests 0xbfe for byte/word
  writes and 0xbfc for longwords. A matching address enters the original
  recompiler. An empty program returns the allocator result in EAX, while
  a program using its last instruction returns 128. The test substitutes
  a mapped allocation for the Windows API. The address in its receipt is
  specific to that fixture.
- **Storage.** At 0x7c0–0x7ff ElSemi ignores byte stores. Word and longword
  stores starting there reach the beginning of MPRO, as the native address
  calculation continues past the 32 MADRS words. For example, a longword
  at 0x7c0 sets MPRO[0] and MPRO[1]. The portable CPU write path currently
  mirrors MADRS in this window. A native longword at 0xbfe also reaches the
  first word of TEMP and does not start the DSP. The probe checks the
  adjacent storage within the original object. Game use is unmeasured.
- **Next opcode.** A guest MOVE to each selected port runs directly into
  ST (A1). ST keeps bits 31–8 of returned EAX in its write callback argument
  and replaces the low byte with 0xff. For a normal DSP write the argument
  is 0109aaff. Both incoming DF settings survive to ST. The arithmetic
  flags returned by the writer are distinct from guest MOVE condition codes.
  The final observing callback sees the full argument, while the emulated
  byte store uses its low eight bits. This exercise qualifies native
  data flow only. It does not establish an audible difference or a
  portable allocation-address policy.

### SCSP Timer Service Across A68K Interrupt Returns

`tools/scsp_board_exchange_probe.py` runs a synthetic 68000 program through
the original board scheduler at 004cc710. The guest sets the timer to 0xfe,
selects and enables level three, and unmasks the CPU. Its autovector handler
reads SCIPD into sound RAM before, between and after two word writes. One
write reloads the timer with zero, the other clears its pending bit via SCIRE.
The probe observes the live acknowledge callback (004b3090) and the RTE
handler from the original dispatch table. The timer expires after the second
CPU run. The first acknowledge occurs on tick three.

| Guest write order | Guest-visible timer bit at the three reads | Interrupt acknowledgements | Pending level at entry to RTE |
| --- | --- | --- | --- |
| Reload, then clear | 1, 1, 0 | Once, on tick 3 | 0 on tick 3 |
| Clear, then reload | 1, 1, 1 on the first visit, then 1, 0, 0 on the second | Twice, both on tick 3 | 3 on tick 3, then 0 on tick 4 |

SCIRE at 004af1d1 reasserts the pending bit if the timer is still marked
expired. Reloading clears the expiry latch but leaves the already pending
bit set. The first RTE therefore exposes level three again when it restores
the guest's interrupt mask. The second acknowledge precedes the next timer
update, even though the second handler finishes in the following CPU run.
All 12 combinations passed (timers A/B/C, both orders, 58/60 Hz), with
14 CPU entries observed per case. The guest reads back the expected raw
SCIPD masks 0x40, 0x80 and 0x100 respectively. The receipt is the
`timer_service` section of `port/build-a68k-board/scsp-board-exchange.json`.
These timings describe this guest program in the original executable.

### MIDI To Timer Handoff And Guest STOP

Eight original-board guest programs (two FIFO lengths, two IRQ level
assignments and two handler variants) expire timer A while commands are
queued. Without a SCIRE write, the 68000 accepts one MIDI interrupt per
tick from tick 2 and accepts the timer on the next tick after the last
byte. With a zero SCIRE write after each dequeue, pending sources are
rechecked before RTE. For one byte the timer is accepted on tick 2. For
three bytes all three MIDI accepts occur on tick 2 and the timer on tick
3 in this program. Swapping levels 2 and 5 preserves source order. The
guest records every byte in sequence and then the timer bit (0x40).

In four further fixtures a privileged STOP exits its first CPU run at PC
0x104 with the live IRQ field at 0x80. The scheduler tests the *template*
field at 010482a4, which stays zero. The next CPU run executes the guest
marker even with no enabled interrupt. With timer A enabled, level 3 is
accepted on tick 3 only if the installed SR mask permits it. This qualifies
the board behavior left open by the single-instruction STOP tests. The
separate forced-template-inhibit fixture still suppresses CPU execution.
Receipts: `source_handoff` and `guest_stop` in the board exchange JSON.

### Board Reset And Original State Load With Pending Sound

The original reset at board vtable +0x14 (004cad60) ran from entry to
return with synthetic i960, work and sound memories. It cleared both
work buffers (1 MiB and 256 KiB) and copied exactly eight reset-vector
bytes into the 1 MiB sound RAM. The new A7, PC and SR high byte matched
the reset vectors and 0x27. A dirty D0, the live IRQ, FIFO contents and
indices, timer counters and latches, SCIPD/SCIEB and scheduler phase
survived. The new guest boot code unmasked interrupts and consumed the
pre-reset command 0x59. Receipt: `board_reset` in the board exchange JSON.
The current port uses `m2snd_reset` on both creation and machine reset.
Its SCSP reset clears queues, RAM and timing state. This RE exercise
does not change that policy.

The original raw archive traversal restored a small guest program in the
first 64 KiB of sound RAM while preserving the seeded live CPU context,
timer state, MIDI ring and scheduler phase. Board vtable +0x30 (004caf00)
ran to completion with empty renderer resource lists. The live sound state
also survived this hook. Resuming A68K at the pre-load PC, the restored
instructions read the live command 0x59 and pending timer mask 0x40. The
archive I/O was simulated, and the other CPU callbacks were inventoried
separately. Receipt: `port/build-scsp-dsp/original-state-audit.json`.
The port's complete cold-load contract remains as agreed.

### SCSP LFO Control And Pitch Saw

The original LFO initializer and register writer cover 512 word writes over
all 32 rates and four waveforms. The probe checks phase retention, native
table pointers, EAX and arithmetic flags. With amplitude modulation enabled
the final flags come from the x86 caller-stack adjustment. This qualifies
the original writer. The A68K research bus still binds 15 of 16 slot words.

The shared PCM engine uses the approved native pitch saw on both CPU paths.
At base step 4096 and maximum depth all 256 phase steps agree with the
original voice. Phase 128 gives 5424 (previously 3072). The square, triangle
and amplitude saw tables already matched. The native noise comparison used
a synthetic CRT thread with seed 1. The full sound check passed after sizing
its test-only state buffer for the current board payload.

Tool: `tools/scsp_slot_write_compare.py --lfo-only`.
Local receipts: `port/build-a68k-board/scsp-lfo-exchange.json` and
`port/build-a68k-board/pcm-saw-build-check.log`.

The initialized 1,024-byte amplitude noise table from two independent Windows
launches (Fighting Vipers and Sega Rally, 16 advancing frame observations
each) has SHA-256
`5d8c4698e3bd28c688e03478cc3424f31805ea0436e47b96f197f8d354711667`.
This matches the native initializer with CRT seed 1 in the oracle. Phase 211
gives signed pitch +128. On that phase the original voice reads the next
depth's first scale word, or the first amplitude-triangle word at depth 7.
The seven observed steps at base 4096 were 4064, 4032, 3952, 3824, 3584,
3072 and 4080. No captured gameplay voice was claimed to use this phase.
Receipts: `port/build-a68k-board/scsp-lfo-windows-{fvipers,srallyc}.json`.

Eight additional paired guest MOVE/ST streams cover disabled, pitch-only,
amplitude-only and combined LFOs, each with x86 DF clear and set. At rate
31 the next handler receives EAX 3 when both depths are zero, or 256 with
modulation enabled. ST forwards 0xff or 0x1ff respectively. This observes
a real consumer of callback scratch; it does not provide the original stack
address for every caller. See `tools/scsp_write_exchange_probe.py`.

### Sound CPU Exchange Qualification

- The A68K research WRITE binding matches the original global callbacks on
  1,858 writes and 576 acknowledges, with 976 nonmutating guards (O2/UBSan).
  The comparison includes the entire CPU MIDI output ring, cursor and count.
  The normal Musashi path also writes the ring through the shared CPU-side
  handler. Both DSPs pass a cold sound-board state load with pending output.
- At 0x7c0–0x7ff the CPU writes into MPRO on word/long stores and drops
  byte writes. The long store decodes its starting address once. At 0xbfe,
  its low half reaches TEMP[0] without starting the original DSP. The
  ordinary DSP write binding matches the original on 180 cases across
  two DSP choices, including register effects, EAX and flags. Twelve
  original Start cases are guarded in the A68K research binding. The
  existing MAME BF0 and original BFE start policies remain backend-specific.
  The full Musashi sound test programs a real effect through the alias and
  checks it stays silent across the BFE long store until an actual Start.
- The shared LFO noise tables match the original at all 256 positions.
  3,584 pitch/amplitude gain checks cover every position at all seven
  active depths. The extra pitch-scale element explicitly represents the
  next native word; at depth 7 it is the amplitude triangle's first value.
  The separate PCM noise-source generator retains its prior sequence.
- The isolated Sega Rally macOS GL/ABI run at 60 Hz with Musashi and the
  original DSP passed 900 frames, four continuation replays, GL context
  recreation and 12 byte-exact fresh-process state continuation frames.
- The original CPU ring window passed 72 width/flag cases. A byte store
  writes its zero-extended value as a full word on either lane. A long
  store leaves the native storage unchanged. Word/byte stores after cell
  63 continue through the native chip object. Writing 0x7000 at 0x684
  changed the synthetic sample base from 0x72006000 to 0x72007000. The
  original voice fragment at 004ab901 then fetched 0x34 instead of 0x12
  at identical coordinates. This establishes the producer and consumer;
  title use of the pointer alias has not been measured.

Local receipts in `port/build-a68k-board/`: `midi-output-bound.json`,
`dsp-register-binding.json`, `lfo-noise-bound.json`,
`cpu-dsp-map-lfo-sound.log`, `midi-dsp-lfo-srallyc-gl.json` and
`scsp-write-exchange.json`.

The research A68K bus also accepts ignored CPU writes in 0x430–0x5ff and
0xc00–0xffff. Across 72 byte/word/long cases the returned EAX and flags
match the native callbacks, with no native stores to the observed chip
object and no change to the complete portable chip. The lower hole
returns the original width-specific callback address; the upper hole
returns the chip address. Register windows are decoded by the starting
address even for an access ending outside the hole. The final native
core build and sound suite pass (`idle-window-sound.log`).

### A68K Board Startup And Scheduling

`tools/scsp_a68k_board_compare.py` executes the original Windows x86 board
callback under Unicorn and the native C research board compiled with Clang.
The portable CPU builds its dispatch table, all 256 exception costs and cold
context locally. The test compares the 33 context words after reset. The
numeric RAM and ROM bases are matched synthetic addresses on both sides.

Fourteen guest configurations at 58/60 Hz cover MIDI (including 40
queued commands), timer A, clear-before-reload, guest STOP and board CPU
inhibit, guest RESET and a masked timer after STOP. Across 252 scanlines the published CPU context, final cycle budget,
clock remainder and first 36 KiB of RAM agree after each line. The observed
RAM includes the exception stack and the guest interrupt handlers' output.

Two more cases issue a warm board reset with MIDI level 6 pending and a
nonzero clock remainder. The guest reads 0xcafe from sample ROM, attempts to
overwrite a protected program word, jumps across program ROM pages, executes
from sample ROM, consumes the original queued byte (0x59) and returns from the
interrupt. The first four subsequent scanlines at each rate match the x86
context, clock and RAM. Both ROM buffers remain byte-exact. Local receipt:
`port/build-a68k-board/cpu-clock-board.json`. The normal core build and
`check-sound` pass (`a68k-clock-sound.log`). This research board is separate
from the installed core and the production Musashi scheduler.

The guest RESET instruction (4e70) calls the first entry at 00572ab8, which
points to 004b3080 (XOR EAX,EAX; RET). The CPU preserves its prefetched
successor and continues to service queued interrupts. A separate regression
reaches STOP with a masked timer. The first scanline initially differed only
in context word 21 (portable 0x80, original zero). The SCSP now writes the
whole A68K IRQ/STOP word whenever the original selects a source or takes its
zero-level store at 004aeab0, even when the line level did not change.
An empty MIDI queue with zero pending bits returns without a store.

#### First DSP Start In Two Game Sound Programs

`--archive` reads the existing ZIP in memory. At 60 Hz the research board
executes the original sound ROMs with matching synthetic allocation bases.
Bank-control writes at 0x400000–0x400fff use the three distinct bare-RET
callbacks installed at 004cd272. The portable and x86 CPU contexts and clock
agree for 3,283 completed scanlines on Virtua Fighter 2 and 3,278 on Sega
Rally. Full 1 MiB RAM comparisons are performed at 210-line intervals.
Both programs then write a byte to 0x100bfe and reach the research DSP-start
guard. This is sound CPU boot evidence with controlled SCSP initial state.

At that boundary `--expect-dsp-start` observes the original Windows callback
and the following guest instruction with two different virtual allocations:

| Game | Original DSP steps | Return in EAX | Following guest PC |
| --- | ---: | --- | --- |
| Virtua Fighter 2 | 82 | 0x52 in both runs | 0x6002a8 |
| Sega Rally | 0 | 0x77000000 or 0x79000000 | 0x60023a |

Both following instructions are taken DBF. The native handler at 00473c74
loads the counter into AX and subsequently replaces all of EAX with the
signed branch displacement (−4). Across the two allocations the full
published CPU context and 1 MiB of sound RAM agree at the end of that
scanline for each title. The research executor still guards this callback.
Receipts: `vf2-boot-extended.json` and `srallyc-boot-extended.json`.

The unmodified x86 instructions were also observed in two isolated launches
of Sega Rally on Windows 11 ARM (VMware Fusion). Each yielded 16 distinct
frame samples. The sound RAM fetch base equaled the voice RAM pointer in
every sample. The allocation was 0x14ab7020 in one process and 0x14c16020
in the other. The initially null DSP code pointer became 0x1a7c0000 and
0x1a920000 respectively. Program/sample map bases and private DSP RAM also
changed between launches. The content stayed on the original shared volume.
Receipt: `srallyc-windows-addresses.json`.

#### Pitch-Only LFO Writes And Longword Updates

The research CPU binding now applies LFO control writes when amplitude depth
is zero. It returns the computed pitch phase step (or 3 if both depths are
zero) and the flags of the native zero-depth test. A longword at slot offset
0x10 updates pitch before LFO. At 0x12 it updates LFO before the second,
inert register, whose completion replaces the LFO scratch even when amplitude
modulation is active. A final amplitude-enabled LFO update still requires the
flags of the original caller's stack adjustment and is guarded before mutation.

The O2/UBSan comparison covers 640 targeted stores across 32 rates and five
width/address combinations: 384 qualified completions and 256 nonmutating
guards. It compares actual register storage, both phase steps, returned EAX
and flags. The general slot matrix also passes 236 writes and 148 guards.
Local receipt: `port/build-a68k-board/slot-lfo-writes.json`.

#### DSP Start And Virtual Write Frames

The research board fixes the original 32-bit address values independently of
host pointers. Sound RAM, program ROM and sample ROM start at 0x73000000,
0x74000000 and 0x75000000 respectively. The DSP code token is 0x77000000.
With scanline entry ESP at 0x71008000, the native scheduler and dispatcher
reserve 52 bytes. A MOVE write consumes eight more for PUSHFD and CALL.
The three native SCSP wrappers tail-jump to DSP Start. Its compiler returns
the flags of ADD ESP,0xd0 at wrapper ESP minus eight. The empty-program EAX
is the code token. Otherwise EAX is the last occupied DSP instruction plus
one (one-based length). The selected DSP backend retains its own start event.
An observed write without the required frame is rejected before mutation.

- With each of two code tokens (0x77000000 and 0x79000000), the first 4,200
  sound scanlines match in Sega Rally and Virtua Fighter 2. At scanline
  3,279 Sega Rally returns the selected code token for its empty program.
  At 3,284 Virtua Fighter 2 returns 82. EFLAGS is 0x202 in both games.
  A separate run with the standard layout matched 12,600 scanlines per game.
  The harness compares the native CPU context, residual budget and clock
  phase after every scanline and all 1 MiB of sound RAM every 210 scanlines
  and at the end. These runs execute the two actual sound programs under
  the board scheduler; they do not capture frontend PCM or gameplay.
- The register comparison covers 72 bound DSP starts across both backends,
  three access widths, three virtual stacks and empty, nonempty and truncated
  programs. It checks the original register bytes, EAX and EFLAGS as well
  as each selected backend's start state. The 12 unbound guards also pass.
- The amplitude-LFO epilogue returns the flags of ADD ESP,12. Its result is
  the wrapper ESP minus 40, 36 or 44 bytes for byte, word or long writes.
  The O2/UBSan comparison covers 640 bound and 640 unbound LFO writes,
  including longword updates spanning two registers. The bound cases rotate
  the virtual stack and all four waveforms, and compare both phase steps,
  register storage, EAX and flags.
- In the native ring window the 64 mixer cells accept zero-extended bytes
  on either lane and full words. Long writes return without storing
  throughout 0x600–0x6ff. The final oracle matches 500 supported width/address
  cases, including the DSP pointer and coefficients described below. The
  other 12 byte/word stores reject before mutation in the research binding. The Musashi bus regression
  checks both byte lanes and an ignored long spanning two populated cells.

Local receipts in `port/build-a68k-board/` include
`{srallyc,vf2}-start-bound.json`, `{srallyc,vf2}-board-12600.json`,
`bound-dsp-writes.json`, `bound-lfo-writes.json` and `board-frame-sound.log`.

#### Command Delivery In Two Sound Programs

One synthetic i960-side MIDI byte (0x59) is enqueued at sound scanline 12,601.
At 60 Hz Sega Rally consumes it in that scanline. Virtua Fighter 2 consumes
it at scanline 39,388. The dual-address runs match the original through 14,700
and 63,000 scanlines respectively. The oracle compares both FIFO cursors and
the wrapping count on every scanline. At each video frame and at the end it
also compares all sound RAM, 32 voice register banks, globals, the 64 mixer
cells, DSP COEF/MADRS/MPRO and the contents of both MIDI queues. Audio output
and whole-game input are outside this sound-board harness.
Receipts: `{srallyc,vf2}-board-command.json` in `port/build-a68k-board/`.

#### Sound RAM Address Captured At DSP Start

An original-code test places two **synthetic marker words** into separately
mapped buffers. A memory-read hook records the actual address touched by
the DSP code emitted by ElSemi. The 68000 word write changes the high half of
the DSP RAM address through the ring window at 0x68e.

| Event | CPU-visible pointer | Observed 16-bit read | MEMS[7], first run | MEMS[7], markers swapped |
| --- | --- | --- | --- | --- |
| Start with private RAM | 0x78000000 | 0x78000000 | 0x123400 | 0x567800 |
| CPU redirects the pointer | 0x73000000 | 0x78000000 | 0x123400 | 0x567800 |
| Issue Start again | 0x73000000 | 0x73000000 | 0x567800 | 0x123400 |

The register values and two allocations here are controlled test inputs. The
effective read address and the DSP result are observations from the pinned x86
binary in Unicorn. This demonstrates when a redirect takes effect. Use by
either commercial game has not been established. Hooks counted zero CPU writes
to either RAM pointer in both commercial program intervals reported above. Receipt: `ring-dsp-redirect.json`.

The recovered backend now latches the virtual address on compile and resolves it
to the approved bounded buffer. The full Musashi bus test changes both pointer
halves, preserves a pending redirect across a cold board restore, and observes
the DSP write into sound CPU RAM only after the next Start. It also exercises
an unmapped address at Start, a word crossing the final valid byte, and the
independent MAME address path. The GL/ABI Sega Rally run with the ElSemi DSP
passed 900 frames before save, four same-process replays and twelve byte-exact
continuation frames in a fresh process. Receipt: `dsp-redirect-srallyc-gl.json`.

In the upper ring window, 0x698–0x6ff maps onto the first 52 DSP coefficients.
CPU byte and word writes reach the same backing as the ordinary coefficient
window. In the global read window, the six-bit update selector is independent
of the eight-bit chip-object offset. A read can return a voice register or
latched sample offset while also consuming a MIDI byte. O2/UBSan comparisons
cover the first two voice register banks, active/direction flags, latched RAM
offset, cursor and step. The result is 2,608 matched reads and 1,920 guarded
cases across the complete test matrix. Receipt: `voice-object-reads.json`.

#### Live PCM Voice RAM Selection

A separate original-code experiment changes the high half of the voice RAM
pointer at 0x686 between two samples of an already active voice. The x86
memory-read hooks identify the allocation used on each fetch. In both the
ordinary and interleaved mixers the first sample reads the synthetic sound
RAM at 0x74000000 and the next sample reads private DSP RAM at 0x78000000.
This holds for both 8-bit and 16-bit PCM. The ordinary route performs one
sample fetch per output sample; the interleaved route performs two in these
fixtures. The DSP is stopped and there is no new key-on or DSP Start.
Receipt: `mixer-voice-redirect.json`.

The shared portable voice engine changes only the allocation used for a
fetch. It retains the key-on offset, byte-lane adjustment, interpolation
history and checked byte/word span. Out-of-range reads stop the content;
a partially written pointer is observable until a fetch needs it. The full
sound-board test switches a looping voice between RAMs while active, saves
between the switch and the next fetch, and checks the restored PCM and
a subsequent switch back on both DSP backends. The final GL/ABI tests run
900 frames of Sega Rally on each DSP, recreate the GL context and compare
12 frames of continuation in a fresh process. The production CPU in these
two GL checks is Musashi.
Receipts: `voice-redirect-{original,mame}-srallyc-gl.json` and
`board-frame-sound.log`.

#### Ring Address Registers And Out-Of-Range Cursors

With a compiled DSP program running, the original memory-read hook recorded
byte offsets 2, 6, 8198 and 8196 as the CPU successively changed RBL, RBP and
MADRS. After a new Start the offset remained 8196. The ring-window addresses
0x690–0x697 now access the live 32-bit base page and length through either
sound CPU. Receipt: `ring-dsp-redirect.json`.

A synthetic CPU write at 0x680 can set a cursor beyond 63. At indices 66, 70,
76 and 255, both original mixers wrote a word at twice the index, measured
from the ring base, before the cursor wrapped. This can change the low half
of either RAM pointer, a coefficient or another DSP field. For example, at
index 66 the ordinary mixer wrote 8192 and the interleaved mixer wrote 4092
into the low half of the voice RAM address in this fixture. The research
binding still guards this CPU register. Implementing the indirect stores
and preserving an outstanding cursor in a snapshot remain open.
Receipt: `mixer-voice-redirect.json`.

### Sega Rally Live A68K And PCM

The opt-in `A68K=1` core runs the SCSP CPU from the machine's 210 slice
callbacks. The scanline dispatcher owns timer ticks. The mixer consumes the
resulting chip state before the next machine frame. Its clocked entry point
suppresses a second timer tick. Model 1 sound uses its existing scheduler.

The isolated macOS GL/Libretro run of `srallyc` produced nonzero stereo
PCM and rendered 900 frames at the default 60 Hz presentation. The first
nonzero frame in the 44.1 kHz output was 246,961 (zero-based). A 12 MiB
snapshot reproduced four successive 12-frame continuations from the same
checkpoint, then reproduced the expected machine state in a fresh process.
At native timing a separate 420-frame run passed with each CPU selector.
Changing the option and resetting preserved the selected CPU. Closing and
reloading applied the selection. A real opposite-CPU snapshot was rejected
without mutation in both directions (header feature `0x00080000`).
Real RetroArch on macOS loaded A68K by default, rendered 420 frames and
exited successfully. The subsequent race listening result is recorded below.

For a pre-device comparison, enable `MODEL2EMUEX_SOUND_TRACE=1` with
`scripts/check-savestates-macos.py --timing native --sound-cpu original`.
Pass the pinned executable, parent ROM archive, first-process log and
`core.pcm` to `tools/scsp_game_audio_compare.py --frames 420`.
The probe replays the recorded i960 commands into the unchanged Windows
board, CPU and mixer routines in Unicorn, at identical scanlines. It runs
the original chip initializer and uses the same 760/761-sample block sizes
requested by the port to isolate mixer arithmetic from host pacing.
This comparison begins at cold boot and includes the start of attract audio.

| Measurement | Result |
| --- | --- |
| Original scheduler with 25 commands from the core | All 5,908 interrupt acknowledgements match in level, order and scanline |
| First active ordinary-mixer stereo frame | At index 255,476 ElSemi returns (−6, −9), the inherited final attenuation returns (−2, −3) |
| Decay/release amplitude table at 004af640 | All 1,024 entries match the recovered calculation on macOS, including the highest entry of 4,052 |
| Diagnostic build with original envelope table and no inherited final attenuation | All 319,344 stereo frames match the ordinary ElSemi mixer before device output, SHA-256 `11c6304f41e18b42e59cab93e090720d852a603517252e911380383a24cfb4af` |

The standard comparison uses ElSemi's ordinary mixer. `--interleaved`
selects the alternate routine for separate investigation. The trace replays
commands from the port's i960. This test does not establish independently
identical i960 command generation or whole-game audio equivalence.

### Integrated SCSP Output And Sega Rally Race Restore

Both sound CPUs and both DSP choices share the stereo output stage. It
clamps each mix sum to signed 16-bit PCM before the frontend gain, matching
004ab03c and 004aef48. The integrated macOS build matched the ordinary
ElSemi mixer at all 319,344 stereo frames and all 5,908 interrupt
acknowledgements in the 420-frame replay above. The complete
`make A68K=1 check-sound` suite passed, including live gain, mute and resume.
Two simultaneous loud voices saturated both channels at both signed limits.
At 50% gain, each sample equalled half the saturated output, rounded toward zero.

The `--rally-drive` recipe in `scripts/check-savestates-macos.py` applies two
coins, Start and analog accelerator pressure from cold boot. Both CPUs
reached frame 2650 with the same image (lap 0′14″35, 15th place, third gear,
128 km/h). Each 12 MiB checkpoint passed same-process and fresh-process
continuation. RetroArch 1.22.2 (fce35fc7) independently loaded each matching
checkpoint with `scripts/test-retroarch-savestate.py --initial-state …
--sound-cpu …`, created slot 0 and advanced through a changing race scene.
After a reload, the frame-2653 game region was identical for each backend;
both sessions resumed and exited normally. This pause/frame-step test
qualifies graphical recovery. Its CoreAudio underrun counters include the
intentional pauses and cannot qualify continuous device playback.

The local evidence directory `port/build-a68k-board/live-srallyc/` includes
the comparison receipts, frontend screenshots and two 44.1 kHz stereo WAV
files. Each WAV joins the final three seconds before the checkpoint to the
first 684,311 stereo frames after restoring it with the same input schedule.
The restore boundary is at 3.000 seconds in each file. The user listened
to both recordings and reported that both sounded OK. This qualifies the
agreed listening comparison for this scene. No separate observation about
a specific co-driver call was recorded.

Repeating the ordinary ElSemi mixer comparison over 3,550 machine frames
with the same two-coin input included attract mode, race start and gameplay.
Replaying 5,167 commands yielded the same 63,230 interrupts at the same
levels and scanlines. All 2,699,224 stereo frames matched before device
output (SHA-256 `0cc00b7a1f0dbaa7ffa366559d4ea5e981b3cdfcca9782db793fc4b2841ace45`).
The entire A68K WAV, including its 132,300-frame lead-in and the 684,311
frames after restore, matched the tail of the uninterrupted run byte for byte.
The original-binary replay
covers the A68K recording. The Musashi recording is a frontend alternative
for the listening comparison.

### Standard Libretro Build And Ski Super G Audio

On macOS arm64 the ordinary build and the combined SHARC/TGPx4 release build
passed the Libretro ABI check with both sound CPUs registered and ElSemi first.
An explicit A68K=0 build passed the Musashi-only ABI check. The default build
also passed the sound suite and the isolated Manx TT cabinet-audio fixture.

Ski Super G exposed two missing A68K-to-SCSP connections. At sound program
PC 0x6021c4, CLR.L (A3)+ writes zero to 0x100bfc and starts the DSP. All 23
native CLR memory handlers have a balanced stack before the write CALL, so
the callback sees the dispatch stack minus the four-byte return address.
At PC 0x600256, MOVE.W (A1)+,(A0)+ reaches global register 0x10042a.
ElSemi stores the value and its update routine at 0x4af050 returns directly
for register offsets 0x2a through 0x2f. CPU writes use these semantics on
both CPU backends. The guard on long writes crossing into slot 0 remains.

The global-register oracle passed 3,410 cases at O2 with UBSan. A separate
16,000-scanline boot comparison matched original CPU context, chip checkpoints,
RAM and both DSP Starts (scanlines 3,344 and 3,633) with two virtual DSP
code addresses. The 900-frame native-rate replay of 741 live sound commands
matched all 15,456 interrupts and all 684,310 stereo frames before device
output. The first nonzero stereo frame was 132,604. PCM SHA-256 was
`011623241273b0530b15d1331f9545c7a936ea2b976501970f17a03b41b8722e`.

The final combined binary passed 900-frame GL save/load and fresh-process
continuation on Fighting Vipers with default A68K, Ski Super G with default
A68K and selectable Musashi, and Daytona USA with its MultiPCM/FM sound
board. All captures contained nonzero audio. The 420-frame Sega Rally
regression reproduced the previously qualified ElSemi PCM hash. Compact
results are in `port/build-a68k-board/standard-build/`. The five-platform
workflow checks the ABI of each release binary when it runs.

### Multi-Game SCSP Comparison

The combined macOS arm64 core ran seven additional sets at native 58 Hz with
the default A68K CPU and the ElSemi DSP. Each produced nonzero stereo PCM.
All seven passed four same-process 12-frame continuations (RAM, devices,
audio checksum and image), context recreation and byte-identical serialized
continuation in a fresh process. Manx TT selected the Deluxe cabinet and
reported its additional sound board connected.

For the single-SCSP tests, the reference executes the original 1.1a x86
sound CPU, board and mixer routines in Unicorn, replaying the i960 commands
captured from the core on the same scanlines. The comparison is at 44.1 kHz
before host playback. It measures sound-board output given those commands.
It does not independently validate their generation by the original i960
or qualify auxiliary boards. The House of the Dead uses the interleaved
mixer previously observed on Windows. The other five use the ordinary
mixer. The combined Deluxe output needs a separate reference.

The oracle now takes audio region sizes and chip placement from the native
descriptors and verifies the chip identities against the pinned MAME catalog.
In Rail Chase 2 the second sample chip starts at 0x200000 in ElSemi's 8 MiB
region. Using the MAME offset of 0x400000 in the reference had introduced an
additional discrepancy. The production loader already used the native layout.

| Set | Frames To State | Frames Replayed In x86 | Different / Compared Stereo Frames | First Differing Machine Frame |
| --- | ---: | ---: | ---: | ---: |
| Virtua Fighter 2 (`vf2`) | 2,100 | 2,100 | 528,473 / 1,596,724 | 197 |
| Manx TT (`manxttc`, Deluxe) | 1,200 | — | Combined two-board output only | — |
| Rail Chase 2 (`rchase2`) | 1,200 | 1,200 | 1,246 / 912,413 | 1,089 |
| Last Bronx (`lastbrnx`) | 2,600 | 1,400 | 17,663 / 1,064,482 | 1,120 |
| Wave Runner (`waverunr`) | 2,600 | 1,400 | 0 / 1,064,482 | — |
| Sega Touring Car Championship (`stcc`) | 2,600 | 1,400 | 0 / 1,064,482 | — |
| The House of the Dead (`hotdo`) | 2,000 | 2,000 | 1,113,190 / 1,520,689 | 380 |

All six x86 replays matched the interrupt level and scanline sequences.
For Last Bronx, Wave Runner and Touring Car, the initial 1,200-frame runs
without input produced silence. The table reports separate runs with the
credit/start script and active audio. Virtua Fighter 2 and The House of the
Dead also used scripted input. No listening assessment was made here.

A controlled replay changed only the original mixer's call size on the first
differing machine frame. It split that frame into single-sample calls as in
the port, preserving the incoming chip state and CPU schedule. The 269
different stereo frames in Rail Chase 2 frame 1,089 and the 73 in Last Bronx
frame 1,120 both dropped to zero. In Virtua Fighter 2 frame 197 the same 211
differences remained, with identical reference PCM under both call sizes.
These results localize the first discrepancy in two titles. They do not
account for subsequent frames or explain the Virtua Fighter 2 discrepancy.

The House of the Dead provided a separate control. Its interleaved mixer
produced (229, 229) at stereo frame 288,170 while the core was still silent.
Forcing the ordinary original mixer on the same trace matched the core for
all 292,732 stereo frames through machine frame 385, including sound onset.
The route choice explains this first divergence.

To reproduce, run `scripts/check-savestates-macos.py` with the combined core,
`MODEL2EMUEX_SOUND_TRACE=1`, `--timing native`, the board flag and the input
listed above. Pass the original executable, same archive, `same-process/run.log`
and `same-process/core.pcm` to `tools/scsp_game_audio_compare.py`, using the
x86 frame count in the table and `--interleaved` for `hotdo`. To isolate the
first differing ordinary-mixer frame, end both replays on that frame and
add `--split-mixer-frame N` to the second one. Hashes, IRQ counts, state
receipts and first sample values are retained locally in
`port/build-a68k-board/standard-build/multi-game-scsp.json`.

These captures are integration regressions for the voice and mixer routines
in the [M30 reconstruction scope](ROADMAP.md#scsp-sound-board-reconstruction).
They preserve the first witness for each discrepancy.

### Original Mixer Dispatch Inventory

The four instructions at `004af7f0` select `004aa950` (ordinary) or
`004aead0` (interleaved). Both ordinary-chip loops call the table at
`00572980`, at `004aaa31` and `004aab34`. Loop mode supplies the two
low index bits, amplitude and pitch LFO enable supply bits 2 and 3, and
8-bit PCM supplies bit 4. The interleaved loops call `004548c0` directly
at `004aeb21` and `004aebfd`. Each mixer calls the DSP through `004a9fa0`.

The ROM-free `check_voice_dispatch` fixture in `tools/scsp_mixer_block_compare.py`
executed the index calculation for all 32 selectors on each chip. At both
call sites, the computed index and target matched the pinned table, which
has 32 distinct executable entries. This qualifies dispatch only. Handler
bodies, ring behavior and the interleaved voice path have separate closure
criteria in M30.

## Audio Subsystem Selection

The macOS distribution configuration with SHARC, TGPx4 and A68K registered one Audio Subsystem option with the exact labels **Model2Emu (ElSemi)** (default) and **Model2EmuEx**. The previous CPU and DSP options are absent. The explicit A68K=0 build passed its separate upstream-only ABI check. ROM-free sound checks and the Manx TT fixture passed.

The isolated OpenGL Libretro harness ran Sega Rally at 58 Hz for 420 frames under each profile. Both passed four exact 12-frame continuations, graphics-context recreation, cold restore in a new process, reset retaining the current board and content reload switching profiles. A cross-profile state was rejected before mutation in each direction. This run used the harness, without changing the installed RetroArch core.

| Profile | Stereo Frames | SHA-256 Of Raw PCM |
| --- | ---: | --- |
| Model2Emu (ElSemi) | 319,344 | `11c6304f41e18b42e59cab93e090720d852a603517252e911380383a24cfb4af` |
| Model2EmuEx | 319,344 | `06eb4c78fe1eb17941a8ac4073ae30a38e9b6e4cca7fb6bc70daedebe858a28e` |

A full-machine standalone run received only one sound command in this interval and stayed silent. For the board comparison, `tools/scsp_upstream_board_compare.py` rebuilt the pinned standalone sound objects in a temporary directory and replayed the core's 25 i960 commands at the same frame boundaries. The standalone board and the Model2EmuEx core delivered identical nonzero PCM for the entire capture. The board comparison controls for the difference in machine-level command delivery. The ROM regions were read from the archive into memory.

To reproduce, run `scripts/check-savestates-macos.py` with the same core, Sega Rally archive, `--frames 420 --timing native` and a fresh output directory for each profile. Set `MODEL2EMUEX_SOUND_TRACE=1` for the ElSemi run. Pass the pristine checkout, ROM archive, ElSemi run's `same-process/run.log` and Model2EmuEx run's `same-process/core.pcm` to the board comparator using the existing Unicorn Python environment. The inventory, original reset and archive probes are indexed in [the RE inventory](RE_INVENTORY.md#scsp-chip-and-bus-call-inventory).


### PCM Interpolation And Voice Cursor

The pinned x86 comparison in `tools/scsp_mixer_block_compare.py` covers the stage before amplitude LFO, envelope attenuation and output gain. It watches the actual memory reads and compares the sample, cursor, direction, active bit, key-on, history and envelope state. Of 448 vectors, 416 matched in bounds. The other 32 reproduced the approved stop at the first escaped address. Both widths, all four sign and loop controls, displaced ring taps and both mixer routes were exercised. The 32 ordinary handlers also passed the existing 288 sequences (2,080 voice frames) in `tools/scsp_slot_write_compare.py`.

With `hotdo` and the reconstructed audio subsystem, the 420-frame run matched the native sound-board replay at every stereo frame, including audio onset at index 288,170. The scripted 2,000-frame GL/ABI run passed four same-process continuations and a fresh-process restore. The SHA-256 of its first 1,520,689 stereo frames was `b6438a8b6fcebc5a040af02b910fc77a1aba8a84318993a80d00e66971be77c7`, matching the original board reference from the earlier six-game comparison. That reference used the sound commands from the port. The other five games were not rerun in this block. Separate ring writes, gain caching and mixer scheduling retain their own qualification items.

The macOS SHARC/TGPx4/A68K build passed `check-sound` and the Libretro ABI test. The installed core matched the tested build byte for byte. Compact voice and frontend results are in `port/build-a68k-board/standard-build/scsp-pcm-fetch.json`, `scsp-pcm-slot-regression.json` and `hotdo-pcm-fetch-states.json`.

Direct x86 replays of both 2,000-frame captures (attract and scripted) also matched all 1,520,689 stereo frames in each capture. The corresponding interrupt sequences matched at 33,210 and 33,173 entries. Results are retained in `hotdo-pcm-fetch-2000.json` and `hotdo-pcm-fetch-2000-scripted.json`. Temporary PCM, RAM and state captures were removed after comparison.

### ElSemi Ring Registers, Mixer Blocks And Cold Voices — 2026-11-14

The reconstructed A68K board passes each machine frame to the original-size
mixer block. The ordinary route finishes each active voice before running
the effects DSP. A one-shot can still contribute to direct output in its last
block while disappearing from that entire block's DSP input. The interleaved
route advances the ring for every slot and retains the previous TL for the
first ring write. The CPU can set any first destination from 0 to 255.
Following the native object offsets also accounts for writes into the cursor,
control fields, DSP coefficients, addresses and program words.

The pinned x86 callbacks and the compiled portable board agree on 4,528 reads,
4,370 global write and IRQ completion cases, and 768 bound ring stores.
The mixer harness checks both routes across 120 block/cursor cases, 256
dispatch/source combinations and 24 active DSP sends/returns. The power-on
probe compares 5,120 gain-table entries and checks all 32 voices through
four initialization/key-scan observations. The first key scan at power-on
can leave a keyed slot inactive until a preceding key-off scan sets RELEASE.

The macOS Libretro harness captured PCM before frontend resampling. The
first 2,100 frames of Virtua Fighter 2, 1,200 of Rail Chase 2, 1,400 each of
Last Bronx, Sega Touring Car and Wave Runner, and 2,000 of House of the Dead
match their archived ElSemi PCM digests. The six intervals contain 7,223,272
stereo frames in total. All six sets and Manx TT Deluxe also passed fresh-process
state continuation. The Manx TT test measures state continuation only.

The runnable probes are in `tools/scsp_mixer_block_compare.py`,
`tools/scsp_slot_write_compare.py`, `tools/scsp_callback_provenance.py` and
`tools/scsp_write_scratch_compare.py`. The local digest and state receipt is
`port/build-a68k-board/standard-build/ring-mixer-qualification.json`.

### SCSP Command Ports, Coupled Voices And Host Delivery

The i960 writes to the two SCSP command aliases were compared with the pinned executable across 72 combinations. A long store with a zero low address byte updates the board latch. Command delivery to the SCSP FIFO is immediate. The optional digital-board type comes from descriptor option 1. The machine test enters through the i960 bus. House of the Dead passed a fresh-process 550 + 12 frame restore on the resulting macOS build.

Both original mixer routes and the portable mixer agree on 134 two-active-voice cases across all 16 modulation depths and 64 ring indices. Checks include stereo, DSP inputs, ring contents and cursor. Eight native host-queue fixtures exercise 735- and 760-sample stereo deliveries through the original copy routine with the OS device boundary substituted. See `tools/scsp_mixer_block_compare.py` and `tools/scsp_board_exchange_probe.py`.

The additional Manx TT Deluxe primary SCSP replay matches 1,368,620 stereo frames and 51,521 IRQ entries at the same block cadence. This brings the primary-board total to 8,591,892 stereo frames. Both Manx TT cabinet fixtures pass fresh-session continuation. These figures exclude the auxiliary board from the primary PCM comparison.

The 58 Hz original schedules 760 samples per machine frame. Over 550 House of the Dead frames the 760/761 adapter differs on 117,049 of 418,000 common stereo samples. Both have 8,792 identical IRQ entries. With the chip fixed at 760, all 418,000 samples match. A diagnostic post-chip rate conversion passes 2,000-frame same- and fresh-process checks at both frontend timings. Cabinet mixing and the production clock policy still require a decision.

Each SCSP board now binds its own render routine at setup. The rebuilt ElSemi and Model2EmuEx profiles passed the House of the Dead 550 + 12 frame same- and fresh-process GL checks. The ElSemi PCM capture and continued state were byte-identical to the pre-refactor build. The subsequent digital board qualification below exercises these modules through the live i960 and PCM callbacks.

## Primary Model 1 Audio Board

The default audio subsystem selects the reconstructed primary 68000, bus, FM synthesizer and both MultiPCM chips together. The standalone subsystem retains the inherited board. `tools/model1_bus_compare.py` checked 360 read observations, 24 generic writes, 1,728 MultiPCM writes and 6,304 FM writes. These include the original A68K callback return registers and flags. `tools/model1_cpu_compare.py` also compared all 33 sound CPU context words after every scanline and 64 KiB of RAM after every machine frame, independently of the chip-write replay.

The Libretro GL harness captured the native-timing PCM for the first machine frames listed below. The pinned original executed the same sound program, the same i960 commands on the same scanlines and the same 760/761 block sizes. `tools/model1_game_audio_compare.py` compared every output sample and accepted interrupt. The Windows host normally uses fixed blocks of 760.

| Set | Machine Frames | Stereo Frames | Nonzero Stereo Frames | Commands / IRQs | PCM SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| Daytona USA | 1,250 | 950,431 | 848,534 | 48 / 48 | `66a1ab60f13ff3da841e45d2c804d9074c60859e5cc77de2b67576c86a3589ab` |
| Virtua Cop | 900 | 684,310 | 618,919 | 96 / 96 | `047057506bbb9eaf703d449e8204b943b190003f63d68bc2fd1f0b6023b58f1f` |
| Desert Tank | 850 | 646,293 | 218,389 | 96 / 32 | `921bd095e19c64e7a4d62e28700b1b10b60d7472817cb02d23d778219ad6d081` |

All three cases passed same-process and fresh-process Save State continuation, including rejection of the other board's state without mutation. Daytona also passed with the standalone audio subsystem. A separate 180-frame board test applied warm reset during a held note at frame 101. All 37,800 context comparisons and 136,800 stereo frames matched the original.

## Native Audio Block And Frontend Clock

At 58 Hz, ElSemi requests 760 stereo frames per machine frame. The production Libretro adapter alternates 760 and 761 to deliver 44,100 per second. Changing a chip call by one sample advances its internal state. The comparisons below exercise fixed 760-frame diagnostic builds before frontend rate conversion. The original emulator executes the machine mix callback at `004cc4a0`. The two DSB comparisons also execute the optional-board installer and the complete command callback at `004c8660` in the same x86 process image as the SCSP.

| Board / Game | Machine Frames | Exact Stereo Frames | Accepted IRQs | Original PCM SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Model 1 / Daytona USA | 1,250 | 950,000 | 48 | `7cb9e2dc0c1b72c2ce631a718b2bb6d4c9b3e4ae0542996922df1ef6c7d1bf06` |
| SCSP + DSB1 / Sega Touring Car | 1,010 | 767,600 | 16,395 | `92e2fb005d44500019ff175c06b643840dd1fe5054be25dc0159d963133ab524` |
| SCSP + DSB2 / Top Skater | 1,010 | 767,600 | 16,489 | `7d6ab4b6709a918ac95ddb2dd11236a0fc3d656a6a83753098e1881263c2514a` |

The digital board was active for 16 blocks in Sega Touring Car and 624 in Top Skater. In the Daytona comparison against production cadence, 842,755 of 950,000 corresponding stereo frames differ. The first difference is sample zero of machine frame 138. The original produces `(-195, 1938)` and the core `(3489, 3694)`. Commands and interrupts still agree. At matching production cadence all 950,431 samples agree. These two controls isolate clocking from synthesis.

The initial clock experiment used two isolated diagnostic adapters built from production objects. The raw variant exposes the native primary board block and optional DSB mix. The transport variant uses endpoint interpolation after the chip. For Manx TT it brings the primary output to the cabinet clock before adding the auxiliary samples. The usual 60 Hz conversion follows the mix. The fixture's source/timing choice is local to its output directory. `tools/model1_game_audio_compare.py` and `tools/scsp_game_audio_compare.py` consume the capture and i960 trace. For a raw capture use `--windows-block --capture-fixed`; digital boards also take `--include-dsb`. In the GL harness use `--raw-elsemi-block --timing native` with the raw diagnostic. At this diagnostic checkpoint production still used the fractional adapter cadence. See [Production ElSemi Audio Clock](#production-elsemi-audio-clock) for the installed result.

For Daytona, independently converting the 950,000 original-cadence stereo frames gives exactly the adapter's 950,431 frames at 58 Hz (SHA-256 `e219e53c3a5d5b38972da535dd4780362229cd8f1ffe026a972f9b7d9dba88d0`) and 918,750 at 60 Hz (`8750d2b966db9468ba38fb96be39e0df4f60b55e6f2e605c82710d82c36e7556`). Both transport runs passed cold save, four exact continuations and fresh-process restore. The Manx TT Deluxe cabinet transport also passed the same continuation checks.

The `compare` command of `tools/probe_audio_cadence.py` reproduces both transport digests directly from raw interleaved 16-bit PCM. In Manx TT Deluxe the entire 74,073-byte cabinet archive, including UART, auxiliary CPU, chips, PCM queue and fractional clocks, was identical in production and transport captures at machine frames 1,250 and 1,262. The comparison spans the cabinet payload after the frontend timing fields through the header’s used length.

The **Model2EmuEx** alternate profile reproduced the pristine standalone Model 1-style board in Daytona USA at native timing. Replaying 48 i960 command bytes into the standalone board gave 950,431 byte-identical stereo frames (SHA-256 `216bad6ac9795bf35c2f3ad84e325853741a7eb1541c854094d03e45af5e7505`). Use `tools/scsp_upstream_board_compare.py --model1` with the matching archive, trace and alternate-profile PCM. The same runtime build passed same-process and fresh-process continuation. The separate Musashi-only build passed its ABI contract on the test host. A fresh build of the full x86-64 macOS core with SHARC, TGPx4 and A68K passed its Libretro ABI test under Rosetta, including default option registration, rejected content and cleanup. The DSB PCM comparison below exercises x86-64 audio separately.

The installed arm64 macOS core (SHA-256 `adc0cef496873ea3043f12cf96d48fea510524837915efe2f898d388ebf7d645`) passed an isolated Daytona Save State test inside RetroArch. The saved and restored game-region images had the same digest, and the advanced frame differed. This checks the frontend restore independently of the PCM comparisons.

### A68K Store Callers And The DSP

`tools/a68k_write_frame_compare.py` executes one representative per direct-store dispatch target and observes the original stack at the actual byte, word or long bus callback. All 976 direct-store targets plus guest exception and IRQ entry agree with the portable CPU on all 986 stores. The observed depths are 4, 8, 12, 16 and 20 bytes. `tools/scsp_a68k_board_compare.py` additionally runs MOVE.W, CLR.W, ANDI.W, MOVEM.W and LSL.W to the real DSP Start register. Each returns the same EAX and EFLAGS as the original, with identical scanline CPU context, guest RAM and clock. The returned parity flag differs between instruction families. This fixture is ROM-free.

Manx TT Twin, with its auxiliary board inactive, sends the primary block directly to the frontend converter. Its 918,750 output frames at 60 Hz match a single conversion of the 950,000 raw board frames (SHA-256 `25b01dc9488ff4c18966247391fbbf465f4e7030bbc46e2e72bf831ea7d2ba64`). With the Deluxe auxiliary board active, its cabinet archive still matches the production core at both checkpoints. Both cabin variants passed fresh-process continuation.

The primary Model 1 fixture now executes the integer block-length calculation and the stores for both output streams inside original routine `004eecf0`. At 44.1 kHz the two lengths are 1,520 bytes per channel at 58 Hz (760 stereo frames), or 1,470 bytes at a 60 Hz input (735 stereo frames). Only the OS device setup is skipped. The original board initialization, command FIFO, timer schedule and MultiPCM regression report is identical to the earlier fixture. The Daytona warm reset at frame 101 also retained its recorded digest and all 37,800 scanline CPU comparisons with this initialization.

The paired Daytona listening excerpts cover seconds 2 through 8 of the same cold run at native frontend timing, stereo 44.1 kHz, with no normalization. The installed and fixed-cadence full captures reproduced their recorded PCM digests before trimming. The local files and receipt are in the ignored `port/build-a68k-board/standard-build` evidence directory.

### Digital Music Track Boundaries

`tools/dsb_board_compare.py` follows each distinct segment and lets the original MPEG header parser determine the frame size. The sweep covers 14,136 valid positions in Sega Touring Car and 26,612 in Top Skater. All are Layer II, 32 kHz, stereo mode 0. The native grouped joint-stereo stall was observed on a synthetic vector. In Sega Touring Car the sweep over representable command bytes also reached three invalid headers and three transitions to addresses outside the music region. These are command-parser cases; the machine replay did not trigger them. The candidate core stops the content explicitly on the unbound/out-of-range cases or native decoder stall.

In Top Skater, muting the four primary gains left only the DSB signal. With the same i960 commands the original digital board mixed over silence matched all 767,948 stereo frames from the installed-build ABI harness. Of these, 473,224 were nonzero. Fresh-process restore passed while the primary gains were muted. The paired fixtures use `--mute-primary` for the core and `--primary-muted` for the comparator.

The native machine reset at `004cad60` preserves playback on both DSB variants and preserves two bytes of a pending stop command. After 16 blocks playing track 1, the next eight blocks matched the uninterrupted control. Completing the packet then stopped playback. The test calls the original sound reset and stubs only the unrelated i960 CPU reset. The portable board also restored the same partial packet into a fresh instance. A macOS arm64 build and a macOS x86-64 build running under Rosetta matched the original 12,160 cold stereo frames and the subsequent 6,080 frames for each board. Reproduce with `tools/dsb_board_compare.py --machine-reset --portable-arch arm64 --portable-arch x86_64`. The recovered catalogue's nonzero DSB option appears in the three Sega Touring Car descriptors (type 1) and the three Top Skater descriptors (type 2).

### Production ElSemi Audio Clock

The installed arm64 core has SHA-256 `81d9273f3d9b3ce71a06457dff01660e4f6490166bc5fcb8169e4a814a31c0f6`. The raw diagnostic in `tools/probe_audio_cadence.py` bypasses frontend transport while retaining the production board clock. Its board PCM matches the recorded native Windows routine outputs for Daytona USA (950,000 stereo frames), Sega Touring Car (767,600), Top Skater (767,600) and The House of the Dead (418,000). The two digital-board captures replay the same scripted inputs as the reference. Independent conversion of the raw blocks matches every production output frame at the tested timings, including both 58 Hz and 60 Hz for Daytona.

The alternate Model2EmuEx Daytona profile reproduces its previous standalone-reference digest. Manx TT Twin reproduces its direct-conversion digest, and the Deluxe cabinet archives match at machine frames 1,250 and 1,262. Eight production configurations passed four same-process continuations and exact fresh-process restore. The installed core also passed an isolated RetroArch Daytona save/load: the game image advanced, returned exactly to the reference at machine frame 2,280, then resumed. The full and Musashi-only builds passed their ABI checks.

The grouped joint-stereo vector repeats native index 1. The portable digital board reports the stall at compressed offset 4,387 and leaves the input mix intact. The adapter routes this error to the content-stop handler. This vector is synthetic. The retained six-second Daytona listening excerpt matches the installed build's PCM over seconds 2–8, with no normalization. The user listened to this excerpt and reported that the audio sounded regular. This completes the final listening check for the ElSemi audio adoption scope. Compact test receipts are in the ignored local evidence file `port/build-a68k-board/standard-build/accepted-audio-clock.json`.

### Original Renderer Options — Tile Filtering And FSAA

The default-off tile filter preserves the existing nearest path. The enabled shader decodes the palette before bilinear sampling and applies native A4 priority-alpha values 0/7/15 with LESSEQUAL thresholds 0x90 and 0x20. Original references are the layer producer at 00451e90 and draw state at 004ed6f0. Synthetic red/blue palette boundaries, transparent-priority cutoff, live on/off and two GL context lifetimes pass. This qualifies the decoded filtering policy; a D3D/OpenGL pixel identity claim is outside this result.

FSAA follows the original initializer's two-sample request. Optional GL functions do not alter minimum-context loading. The renderer checks both framebuffer completeness and the actual sample count, resolves before final presentation, and handles resize and context destruction. Missing optional entry points leave ordinary rendering usable. The selected Enabled value is retained with one diagnostic per unavailable context/request, following the user's decision. Both tested desktop contexts returned exactly two samples.

The intermediate tile-filter build matched the previous installed VF2 image, RAM and PCM at the default-off setting after 900 machine frames. An initial environment-only attempt to enable filtering was discarded because the Save State runner clears external CHECK_* variables. Explicit --tilemap-filter and --fsaa arguments were added to the existing runners. The explicit enabled run passed four same-process continuations and exact fresh-process continuation.

The final installed build passed an actual RetroArch VF2 Save State test with both filtering and FSAA explicitly enabled. The game advanced, restored the reference game region exactly and resumed; exit was clean. ABI registration checks pass for both the V2 snapshot and legacy defaults. Standalone/headless builds also pass. The delivered arm64 core has SHA-256 `7160117a0d9ba28d7c599181968f24e4f7177e976b55c7db871b7902cf2b9c99`. Compact retained results are port/build-original-options/video-options-results.json. The subsequent M31/M32 qualification is recorded below.

### Original Renderer And Lua Integration — 2026-11-14

- Windows 11 in Fusion, VMware SVGA 3D driver 9.17.8.9. The ROM-free D3D9 probe used explicit levels and an autogen 64×64 checker. Fractional LOD yielded RGB 81 with ElSemi's MIPFILTER=3 and with LINEAR=2, versus 96 with POINT=1. Both point and linear in-level filters gave these results. The generated checker yielded 120. This is a measurement on the tested driver. The probe is in scripts/check-d3d9-mip.
- The ROM-free GL test in scripts/check-texture-materials.cpp checks linked vertices, a culled face and a link-zero restart. It also exercises duplicate manifest tags, CRC match and mismatch after a RAM write, both converted shader outputs (RGB 203/102/50 and 102/51/25), and a generated 1×1 mip (120/120/120). Fake Gouraud and Automatic Mipmaps passed four 12-frame VF2 continuations after 900 frames and exact fresh-process machine continuation.
- The original Daytona script declared Infinite Time. The option-on ABI test read 3,200 at the timer word (0x5010D0). The independent Lua fixture in scripts/check-lua-overlay.py verified Frame/PostDraw ordering, module-cache retention across reload, Lua progression across four machine restores, a drawn PNG, a supplied bold TTF and visible built-in glyphs with the missing-font notification.
- Installed macOS arm64 core, RetroArch 1.22.2 (fce35fc7), Daytona, Lua Script Auto, Pipeline Enabled. The run registered the original script option. Slot 0 restored the same screenshot at machine frame 2,287, the scene advanced before and after restore, and RetroArch exited normally. No original texture pack with active mappings was available. Windows measurement covers D3D9 sampling. End-to-end Lua and GL qualification here covers macOS.
- The standard core and both converted shaders were hash-verified in the user's installation. Installed core SHA-256 is `bc3306b837f9dcf7ef278b03ead8a50126d0fd1882607c7b1929fdfd0e5e29e4`.


## Universal macOS Build And Extended Input Checks — 2026-11-14

`make universal SHARC=1 TGPX4=1 -j4` builds isolated arm64 and x86_64 slices and joins them with lipo. Both include A68K, SHARC and TGPX4. The resulting core SHA-256 is `e923a41ad455e9bb1b1303f0e77301d7e22306acac5b809d9954f7c9b756cae6`. Both slices export only Libretro entry points and depend on system libraries. The existing ABI suite loads each slice of the universal file, checks options and rejected content, and exits cleanly.

The existing SM2 reference input suite and destination adapter suite pass on both architectures. Extended checks now change Normal/Test-Service for every one of the 70 catalogue entries, verify reduced descriptors, require controller republication after a change, and verify an unchanged refresh is a no-op. Test-Service polling resumes after restoration. Power Sled can legitimately poll L3/R3 for gameplay in Normal mode, so absence of all such polling is checked specifically for VF2 rather than imposed on every profile. All VF2 revisions retain the six independently checked action mappings.

RetroArch 1.22.2 loads the same universal file in native arm64 and x86_64 under Rosetta 2. Both isolated runs reach rendered VF2 attract at frame 1800 and exit 0 without timeout. The architecture-specific NEON/SSE feature logs establish the executed frontend architecture. This qualifies Intel execution under translation on the Apple M4. Native Intel hardware and physical controllers retain their own qualification requirements.

M08 remains Partial because native action correspondence in Fighting Vipers and Last Bronx still needs verification; their legacy destination rotation was preserved. Existing per-game gameplay/device limits also remain. M16's local universal build group is complete.

Compact receipts, suite logs and frontend screenshots/configuration are under ignored `port/build-universal-macos/`. No release package or publication was performed.

## M08 Fighting Family Wiring Closure — 2026-11-14

The same destination rotation found in VF2 was also incorrect in Fighting Vipers and Last Bronx. Their native Input Tests show the following paired results at frontend frame 2050, after the buttons have been held since frame 1560.

| RetroPad P1 / P2 | Before, Both Games | Corrected, Both Games |
| --- | --- | --- |
| A / B | Kick / Guard | Punch / Kick |
| Y / A | Punch / Kick | Guard / Punch |
| B / Y | Guard / Punch | Kick / Guard |

All other gameplay contacts remain OFF in these captures. The destination rotation has been removed completely. SM2's unchanged Fighting profile now reaches the native player ports directly. Adapter regressions check all three actions on both ports for VF2's four sets, Fighting Vipers' three sets and Last Bronx's three sets. The extended adapter and original reference suites pass on arm64 and x86_64 under Rosetta after this change.

The reusable replay fixture now supports Fighting Vipers and Last Bronx and their extra TGP menu entry. Before/after PNGs and run receipts are retained under ignored `port/build-libretro-macos/audit/m08-fighting-20261114/`. Each of the twelve accepted frontend runs exits 0 without timeout. ROMs were read from the existing external archive.

M08 closes its implementation and targeted native-wiring qualification. Sustained gameplay, other per-title runtime checks and physical controllers remain explicitly tracked in M14.

The corrected universal core was installed in the configured local RetroArch core directory and verified byte-for-byte. SHA-256: eb7b4fa65d8e4d5bac1da5bcc5c641e9ffd13ee9289b09131a47492a6e8fd418. Only the twelve reviewed PNGs, receipts and acquisition recipe remain from this group; isolated replay/configuration/save directories were removed.


## M30 Reconciliation And M14 Runtime Follow-Up — 2026-11-14

M30's eight audio adoption groups remain closed. Its remaining concrete questions are now listed in ROADMAP.md: original memory ownership and guest reachability beyond Dynamite Cop's recovered protection table, the Ski Super G shared-memory allocation escapes, and second-SCSP activation. The first two preserve the approved explicit failure behavior; both mixer branches already have synthetic coverage. No additional original-code execution or recovery was performed in this reconciliation. Geometry and rasterization retain the inventory's stated limits.

The current universal core, SHA-256 `eb7b4fa65d8e4d5bac1da5bcc5c641e9ffd13ee9289b09131a47492a6e8fd418`, passed these bounded macOS arm64 checks.

| Test | Evidence And Result |
| --- | --- |
| VF2 scripted play, 7,200 frames | The GL harness renders round 2 with Akira and Sarah. Four same-process state continuations and a fresh-process continuation match exactly. Rejected-state handling, NVRAM authority, cold restore and renderer-resource recreation also pass. This is about two minutes of emulated time. |
| Fighting Vipers in RetroArch 1.22.2 | The native frontend saves a state, advances visibly, restores exactly at machine frame 2281 after three matched steps, and advances again. The OSD-free region hashes match. Exit 0, no forced termination. This check uses attract mode. |

Results are under ignored `port/build-universal-macos/m14-vf2-play/` and `m14-fvipers-state/`. The existing project runners were reused, with ROMs read from their archive. These checks qualify scripted software lifecycle and bounded runtime. Physical inputs and true GPU context loss remain open.

### Model 2C Guest Memory Reachability — 2026-11-14

Four headless runs covered 28,800 frames across Dynamite Cop and Ski Super G,
with and without scripted input. LLVM branch counters distinguish fixed
protection responses, selector-dependent copies, shared memory and external
ROM. Two additional Dynamite Cop runs recorded the values written to the
selector. ROMs were read directly from their archive. The per-run counts,
input schedule and reproduction instructions are in
[RE_INVENTORY.md](RE_INVENTORY.md#guest-reachability-in-the-reconstructed-model-2c-machine).
These observations apply to the reconstructed machine. Original Windows
allocation ownership and later game sequences remain unverified.

The subsequent direct-call audit of the USA Dynamite Cop i960 program found
two callers. Both pass selector zero and length 20. Their nine response reads
per command account for each machine trace. The Ski Super G decoded-record
observer attributed all external ROM reads in both scenarios to the same
36 program indices, with zero shared-window operations. See the adjacent
[Ski Super G read-site](RE_INVENTORY.md#ski-super-g-external-read-sites)
and [Dynamite Cop caller](RE_INVENTORY.md#dynamite-cop-usa-command-callers)
results for their scope and reproduction tools.

### Original Second SCSP Activation — 2026-11-14

The original registration table contains 67 records. All 55 SCSP records
map to five distinct combinations of machine type and optional digital board.
The full x86 board installer returned in all ten ROM-free Unicorn cases
(five combinations, two initial flag values). Each case wrote the primary
voice pointer once, touched the primary DSP pointer twice, and never wrote
the chip-count flag or either corresponding secondary pointer. Both secondary
pointers remained zero. All ten cleared the separately observed mixer-mode
byte. Each DSB case selected its expected digital board. The scope is
catalog configuration and board setup. Windows audio APIs and live gameplay
were outside this probe.

```sh
port/build-sharc/venv/bin/python tools/scsp_board_activation_probe.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc-machine/model2b-catalog/original \
  --output port/build-re-inventory/scsp-activation.json
```

The JSON records the executable and catalog hashes, board settings, game
names and watch counts. The catalog prefix refers to the existing `.mem`
and `.heap` outputs from `tools/dump_games.py`.

## M14 Fighting Vipers Operator Setting Persistence — 2026-11-14

RetroArch 1.22.2 (`fce35fc7`, macOS arm64) loaded the universal core
`eb7b4fa65d8e4d5bac1da5bcc5c641e9ffd13ee9289b09131a47492a6e8fd418`
in three separate processes. Each used an isolated directory, Test/Service
controls, Automatic Initial NVRAM Setup enabled and NVRAM Settings disabled.
The baseline started with an empty save directory. Each subsequent launch
received only the raw Save RAM produced by the preceding process. Input
replays contained controls only. All three processes exited normally.

| Session | Frames | Result | Operator CRC |
| --- | ---: | --- | --- |
| Baseline | 2,100 | Game Assignment displayed Advertise Sound ON. | `2585` |
| Native edit | 2,900 | Changed Advertise Sound to OFF with Service/Test and exited Game Assignment. The game saved OFF (bit 0 set). | `26f0` |
| Fresh launch | 2,100 | Re-entered Game Assignment without editing. The screen displayed OFF. All 65,664 Save RAM bytes matched the edit session. | `26f0` |

The only changed bytes between baseline and edit were the option at
`0x3351` and its checksum at `0x3302–0x3303`. CRC-16/CCITT with an initial
value of zero over the 29 bytes at `0x3340` matched the stored little-endian
checksum in all three saves.

To repeat with `scripts/run-retroarch-macos.py`, use the SM2 replay-v1 layout
from `scripts/check-retroarch-inputs.py`. For the baseline and fresh launch,
press Test at frame 900, Service seven times at frames 1350 through 1620
(45-frame intervals), then Test at 1725. For the edit, follow the same
navigation, press Service four times starting at 1880 (45-frame intervals),
Test at 2080, Service seven times starting at 2190 (45-frame intervals), and
Test at 2520. The edit and fresh-launch inputs use 12-frame presses. Compact
evidence in `port/build-universal-macos/m14-fvipers-service/` consists of
the before/after menu captures and a JSON receipt with process, replay,
checksum and Save RAM identities.

## M14 Dead or Alive Operator Setting Persistence — 2026-11-14

Three isolated RetroArch 1.22.2 (`fce35fc7`, macOS arm64) processes ran
the parent set `doa` with the same universal core as the Fighting Vipers
test. Automatic Initial NVRAM Setup was enabled and NVRAM Settings was
disabled in all three effective configurations. The first process used an
empty save directory. The next two imported only the preceding raw Save RAM.

| Session | Frontend Frame Limit | Native Menu and Save RAM |
| --- | ---: | --- |
| Baseline | 2,100 | Game Mode Settings displayed DEMO SOUND ON. EEPROM bit 0 was set at both `0x1c` and `0x40`. |
| Native edit | 2,950 | Service/Test changed DEMO SOUND to OFF and exited the submenu. Both EEPROM bits cleared. |
| Fresh launch | 2,100 | Re-entering Game Mode Settings displayed OFF. All 128 EEPROM bytes matched the edit session. |

Both 36-byte operator banks at EEPROM offsets `0x08` and `0x2c` matched in
each save. Each bank's leading byte matched the sum of its remaining 35 bytes
modulo 256 (`0x0f` in all sessions). During the edit, EEPROM bytes `0x0c`
and `0x30` also increased from 2 to 3. The only raw Save RAM difference
between the edit and fresh launch was backup RAM byte zero (`0x16` to `0x21`).

To repeat with the macOS runner and replay layout used above, hold each
switch for 12 frames. For baseline and fresh launch, press Test at 900,
Service six times at 45-frame intervals starting at 1350, then Test at 1680.
For the edit, continue with six Service presses starting at 1890, Test at
2200, six Service presses starting at 2320, and Test at 2650. The compact
local evidence in `port/build-universal-macos/m14-doa-service/` contains
the two Game Mode Settings captures and the process, replay and Save RAM
hashes in `result.json`.

## M14 Sonic Championship Warm Restart — 2026-11-14

RetroArch 1.22.2 (`fce35fc7`, macOS arm64) loaded the universal core
`eb7b4fa65d8e4d5bac1da5bcc5c641e9ffd13ee9289b09131a47492a6e8fd418`
and `schamp` once. NVRAM Settings stayed enabled with Hard/Normal selected.
The same process (PID 23699) performed the native edit, the confirmed Quick
Menu soft reset and the final menu inspection, then exited normally.

| Observation | ENERGY(1P) / ENERGY(VS) | Raw Selectors | Shared Word | Operator CRC |
| --- | --- | --- | ---: | --- |
| Game Assignments after native edit, before reset | Hardest / Hard | 3 / 2 | 180 | `7580` |
| Game Assignments after confirmed soft reset | Hard / Normal | 2 / 1 | 200 | `7a16` |

Both autosaved checksums matched CRC-16/CCITT over the 32 bytes at
`0x3340`. The final 65,664-byte save matched the M29 fresh-process control
byte for byte. Two preliminary remote RESET attempts did not establish a
completed reset. In the accepted run the Quick Menu requested confirmation,
then the log recorded both `[Core] Riavviato.` and
`[Model2EmuEx] NVRAM Settings Applied; Game Reset`.

To repeat, use the isolated macOS runner with `autosave_interval=1`,
the M29 Hard/Normal seed and `sonic-service-edit.replay`. After the replay
ends, verify the edited save, confirm Quick Menu > Reset, resume if paused
and re-enter Game Assignments via Test/Service. The local receipt and the
two menu captures are in `port/build-universal-macos/m14-schamp-restart/`.

## M14 Control Routes Against SM2 — 2026-11-15

The comparison follows each frontend action to the byte the i960 can read.
All offsets below are hexadecimal, relative to guest address `0x01c00000`.
SM2 reference revision `6b282b94e781e20b2b6d522d0dcef5974b7a5d84` matches
the imported `input.cpp`, `input.h` and the game XML byte for byte, including
the XML actually compiled into Model2EmuEx. The arm64 reference and adapter
input suites both passed. The catalog bound 11 Model 2, 11 Model 2A, 35
Model 2B and 13 Model 2C sets, using 22 distinct profile labels.

| Control Path | Guest-Side Result |
| --- | --- |
| 2A/B/C digital panels | In input mode, B at `+02` carries IN0, C at `+04` carries IN1 and D at `+06` normally carries IN2. This covers the ordinary action, fighting, soccer, shooter, twin-stick and baseball digital controls. The two Sonic and two Dead or Alive revisions retain their own button assignments. Power Sled also exposes IN3 on E at `+08` for all three programs. The ten standard fighting revisions have separate adapter action checks and their three parents have native Input Test evidence. |
| Driving and analog controls | On 2A/B/C, select the channel at `+1E` and read the same address. The bridge supplies the shared profile's channel byte for driving, Sky Target, baseball, analog gun controls, skiing, skating and sled controls. The sweep compared each bound channel individually. A sequential read past channel seven differs: SM2 wraps to zero, whereas the destination increments its byte index beyond seven. SM2 also distinguishes configured output latches and combines adjacent registers on a 32-bit read. The destination uses its native wide-read convention. |
| Daytona USA family and Desert Tank | The SM2 board runs Z80 firmware against 2 KiB of dual-port RAM. On both parents, changing channels 0/1/2 changed bytes at `+00/+02/+04`. Toggling IN0 bit 4 and IN1 bit 0 changed `+10/+12` respectively. Model2EmuEx supplies the same addresses through its direct board reader. Both implementations encode Daytona neutral/1/2/3/4 as `00/20/10/60/50` in the shift field. The eight Daytona sets share the route; only the parent was run for the firmware measurement. |
| Sega Rally, Manx TT and Motor Raid | The Sega Rally adapter deliberately passes the handbrake through D. On Deluxe Manx TT, D can return an AMS reply. The common descriptor publishes P2 Start / VR on Manx TT, Manx TT Twin and Motor Raid. Pressing it changes SM2 IN0 bit `20`; the destination masks the transition. This concerns the P2 panel input in a one-rider profile. |
| Sega Water Ski | Pitch Left (Y or L) and Pitch Right (A or R) produced SM2 port C bytes `FF → FB` and `FF → F7`. Model2EmuEx produced `F3` at rest and `F3` on either press. Its native idle mask has both bits clear and its standalone catalog marks those controls as hotkeys. The loss is observable at the CPU byte read. |
| Super GT 24h | Both boards select the accelerator and brake at channels 1 and 2. Given raw `20`, the SM2 bus returned `20` for I/O Type C and `DF` for A/B. The Model2EmuEx reader returns the raw byte independently of I/O Type. The channels agree, while pedal polarity depends on the selected cabinet in SM2. |
| Drive and motion responses | In seven Indy-protocol sets (Indy 500, Over Rev and their revisions, plus Super GT 24h), SM2 can return the steering byte on D after E commands `80/83`. Super GT 24h returned the supplied wheel byte `A7` for both commands. The Libretro input path supplies D from the native board latch. Rail Chase 2 has a dedicated motion acknowledgement on D in both implementations. Ski Super G uses different motion command handling, and the recovered destination motion routine also runs for Water Ski. A digital latch comparison does not establish the motion response. |
| Serial guns on 2A/C | Virtua Cop 2 and The House of the Dead use the same selector/data addresses, `+14/+18`, and counter order (P1 Y/X, P2 Y/X). SM2 selects their eight bytes with 0–7; Model2EmuEx selects them with 1–8 and advances on an 8-bit `87` write to `+12`. At P1 Y = `09A`, selector zero returned `9A` in SM2 and `FF` in Model2EmuEx. These results establish a protocol difference. The ADC gun games (Gunblade NY, Rail Chase 2 and Behind Enemy Lines) follow the channel path instead. Expanded-view aim also needs separate treatment: SM2 supplies its horizontal expansion to the input calculation and the destination bridge leaves it at its default. |
| Virtua Cop on original Model 2 | The SM2 advanced I/O board delivered P1 Y/X at `+100/+102` and `+104/+106`, P2 Y/X at `+108/+10A` and `+10C/+10E`, and offscreen flags at `+110`. IN1 reached `+12`. In Model2EmuEx, P1 aim changed from `17C,0E6` to `1EF,09A`. The serial reader changed, but the four P1 bytes at `+100..+106` remained `80`, and a P1 trigger press changed `+04` while `+12` remained `00`. A 900-frame destination machine trace confirmed that the game actually read every even address from `+100` through `+110`, including 100 reads of each during the 100-frame changed-input interval. Both catalog revisions share this destination mapping. The guest trace used `vcop`. Crosshair movement alone would miss this discrepancy. |

**Test method.** The ROM-free digital sweep applied each of the 16 RetroPad
buttons independently on P1 and P2 after neutral initialization for every
set (2,240 cases). It compared the four shared digital panel bytes' changed
bits with the mapped destination latches. Seven cases suppressed a changed
bit: the four Water Ski bindings and the three motorcycle P2 Start bindings.
That count excludes protocol differences downstream of the latches. For the
analog sweep the probe varied six control axes on each port over three
values, explicitly selected each bound channel, and called the production
board reader. All 4,284 reads matched the shared profile's raw channel
byte. Super GT's subsequent SM2 board transformation was measured separately.

For Daytona, Desert Tank and Virtua Cop, a fresh headless build of the SM2
reference ran the complete machine and I/O firmware. After 450 frames the
probe changed one input at a time, held it for eight frames, restored it and
checked which i960-visible bytes reverted. An initial firmware-only attempt
produced no dual-port writes without the main CPU and was discarded. The
targeted 2A/B/C comparisons used the reference machine's real bus callbacks.
All game archives were read in place. The compact local measurements and
probe sources are in `port/build-universal-macos/m14-input-routes/`. The
measurements apply to the specified controls, modes and access sequences.

## M14 Sega Rally Live Cabinet Count — 2026-11-15

Two local RetroArch processes loaded `srallyc` with the universal core
`eb7b4fa65d8e4d5bac1da5bcc5c641e9ffd13ee9289b09131a47492a6e8fd418`.
On the host, Quick Menu > Core Options > System > Linked Cabinets changed
from **2 Cabinets** to **3 Cabinets** and back to **2 Cabinets** while the
original client remained connected with its count set to two.

| Phase | Host | Client |
| --- | --- | --- |
| Initial connection | Native state 3, ID 1, count 2 | Native state 3, ID 2, count 2 |
| Host selects three | Settings-applied reset, native state 0 | Native state 0 |
| Host restores two | Second settings-applied reset, new roster, state 3, ID 1, count 2 | New roster, state 3, ID 2, count 2 |
| Independent three-process run | State 3, ID 1, count 3 | Both state 3, IDs 3 and 2, each count 3 |

The two original process IDs remained the same throughout the edit. All
five processes in the two accepted runs exited with status zero. The
three-process case exercised native ring initialization; no race was
required or measured. The local receipt retains the ordered native events
and core hash. In a preliminary two-process run RetroArch wrote the
normal `srallyc.lrtl` playtime entry. The accepted runs disabled runtime
logging, and the network runner now isolates it with the other test files.


## M14 Virtua Cop Original Input Publication — 2026-11-15

The original ElSemi 1.1a hook at `004cb9b0` explains the discrepancy
reported above. After the host-device poll at `004caa80`, it converts X
with +0x83 and Y with +0x24, then publishes P1 Y/X and P2 Y/X as eight
little-endian counter bytes at `005aa70c..005aa713`. It writes the two
offscreen bits at `005aa714` and copies the trigger panel from
`005aa875` to `005aa87a`. The native reader at `004c88a0` exposes
these through guest offsets `+100..+110` and `+12`.

The Libretro bridge already had calibrated guest counters from the unchanged
SM2 profile, but omitted that final publication. It now fills the nine
analog bytes and the trigger port for original Model 2 lightgun bindings.
The native board reader handles these addresses. The fix follows the original
hook and is shared by `vcop` and `vcopa`.

| Check | Result |
| --- | --- |
| Original binary oracle | 288 cases, 2,880 byte comparisons and 288 release checks pass. Covers both revision bindings, three positions per axis, all P1/P2 trigger combinations and all offscreen combinations. The host-device poll alone is bypassed, supplying calibrated raw values at its output boundary. The original publication hook and reader execute under Unicorn. |
| Actual guest execution | Both revisions run 900 frames. Every observed read of the nine counter/flag addresses and trigger port matches the current profile value. Each address is exercised in neutral, P1 action, P2 action and P2 offscreen phases. 9,551 reads per revision, 19,102 total, all pass. |
| Architecture regressions | The complete 70-set adapter suite, with new P1/P2 Virtua Cop endpoint, trigger, offscreen and release assertions, passes on arm64 and x86_64 under Rosetta. Existing native EEPROM/Manx TT I/O regressions pass. |
| Real RetroArch | The universal core runs Virtua Cop for 900 frames in isolated macOS arm64 RetroArch, renders 3D attract and exits zero in 20.67 seconds. The screenshot is retained. This run supplies rendering/lifecycle evidence. Input delivery is measured by the two checks above. |
| Local installation | The tested universal core and matching info file are installed in the configured local RetroArch directories. Source and destination SHA-256 match. Core hash `f6b5fa7ebc6801e4fa3b52e7cdac5d43e736e32e8fb0351e62baf5dbe95f8401`. |

The repeatable original comparison is `tools/vcop_input_compare.py`.
Probe sources, original results, actual-guest read counts, architecture logs,
frontend screenshot/result and the installation receipt are retained locally
in `port/build-universal-macos/m14-vcop/`. The same directory retains the
build commands in `reproduce.sh`. Run the oracle with the existing
`port/build-sharc/venv/bin/python` and the pinned original executable.
The oracle requires executable-memory permission for Unicorn.

M14's Virtua Cop control-route block is complete. Physical gun/controller
qualification retains its own scope.


## M14 Sega Water Ski Pitch Inputs — 2026-11-15

The original binding decoder clarifies the polarity. ElSemi's input record
uses kind 0 for Pitch Left/Right on port 1, masks 0x04/0x08. In the
original decoder at 004f2480, a kind-0 pressed binding sets the bit.
Each poll starts from the configured idle byte, 0xf3, so release clears it.
The original keyboard predicate at 004f0c20 tests the held key state.
These are momentary active-high controls. The inherited name
M2_IN_HOTKEY and standalone mapper's skip gave the wrong interpretation
for these bindings. The per-game analog/motion routine at 004c9dc0 leaves
port 1 intact.

The unchanged SM2 profile expresses these switches active-low. The Libretro
bridge now converts masks 0x04/0x08 to the native polarity after applying
the native idle mask. Frontend labels and aliases remain those of SM2,
Pitch Left on Y/L and Pitch Right on A/R.

| Input | Native Byte At Guest 0x01c00004 |
| --- | --- |
| Released | F3 |
| Left | F7 |
| Right | FB |
| Both | FF |
| Released Again | F3 |

The original executable oracle passes **128 cases / 384 byte comparisons**.
It varies all combinations of the four Pitch aliases plus Select Up and
Set, including P2 isolation. Each case checks initial pressure, another
held poll and release. The oracle executes the original binding decoder,
keyboard predicate and I/O reader. It supplies a synthetic native binding
list with the recovered record values and keyboard-state bytes, bypasses
the OS device poll, and stops before application hotkeys. This measures
the recovered binding semantics independently of the portable conversion.

A 1,050-frame actual-machine trace observed **750 reads** of the input
register. All matched the expected values across neutral, Left, Right,
Both and release phases (157/150/150/150/143 reads). The game archive was
read from its existing archive location. The full 70-set adapter suite
passes on arm64 and x86_64 under Rosetta, including new Pitch combination,
hold and release regressions.

The universal core also completed an isolated 900-frame Sega Water Ski
RetroArch run in 20.39 seconds with exit code zero. The retained screenshot
shows the Blue Sea course introduction. This checks frontend loading,
presentation and normal exit. The CoreAudio log recorded underruns during
this run, so it supplies no listening qualification.

The tested universal core and matching info file are installed locally.
Core SHA-256 is
`6a1981e0f464de44071024eb2295d1ad89e015e304e601bc5de9fe9984733d37`.
Repeatable original comparison code is in `tools/waterski_input_compare.py`.
Local probe sources, build commands, decoder receipt, actual guest counts,
architecture logs, frontend image/result and installation receipt are in
`port/build-universal-macos/m14-waterski/`. M14's Water Ski Pitch block
is complete. Super GT 24h is the next listed block.


## M14 Super GT 24h Pedal Polarity — 2026-11-15

The destination bridge now follows SM2's `Model2B::analog_value` for
Super GT 24h. The shared profile emits reversed pedal channels. A valid
operator RAM signature `85 AD` and I/O Type word zero at offset `0x0A`
select Type C and pass those values through. A/B and uninitialized operator
RAM use `max(255 - raw, 1)`. Both bytes of the Type word are checked.
This conversion applies to accelerator and brake channels 1/2 and is
recomputed at each input poll from the current operator RAM.

| Pedal Position | Type A (1) | Type B (3) | Type C (0) |
| --- | ---: | ---: | ---: |
| Released | 1 | 1 | 255 |
| Fully Pressed | 255 | 255 | 0 |

This is the existing SM2 frontend range and cabinet policy. The ElSemi
host-device routine at `004ca450` independently clamps its supplied pedal
values to **1–254**, and the native ADC reader at `004c88a0` returns those
prepared bytes. Seventy-five original-executable cases confirm that range
and its independence from I/O Type. The portable native reader continues
to return the values supplied by the controller adapter. The chosen
RetroPad conversion uses the established SM2 endpoint convention, including
255 on full pressure for A/B. This group qualifies pedal polarity.

The primary comparison used a fresh headless build of SM2 revision
`6b282b94e781e20b2b6d522d0dcef5974b7a5d84`. The reference machine loaded the
existing Super GT archive in place. Destination profile outputs were fed
to its real I/O bus callbacks and compared with destination byte reads:

- **3,696 cases / 11,088 channel comparisons** pass. Each pedal covers all
  256 byte positions independently, with simultaneous-pressure cases.
  The sequence exercises A/B/C/A, invalid signature, absent destination
  backup pointer and a nonzero Type high byte. Channel 0 steering matches.
- An actual destination-machine run executes **1,500 frames** and records
  **4,286 matching guest ADC reads**, across controlled live operator-RAM
  updates A/B/C/A in the same process. The updates are injected before
  input polling. This measures immediate input-path handover.
- The complete 70-set adapter suite passes on arm64 and x86_64 under
  Rosetta, with new Super GT endpoint and live Type-transition assertions.
- An isolated **900-frame RetroArch run** renders 3D attract, exits zero
  in 18.97 seconds and retains its final screenshot. Physical pedal and
  Service Menu interaction qualification retain their own scope.

The tested universal core and matching info file are installed locally.
Core SHA-256 is
`df39212201423515cb7125f235d0fba1b57afe5bb83a7583c6fd3bb56ca065bf`.
The reusable comparison is `tools/sgt24h_input_compare.py`. Local sources,
build commands, reference/original receipts, guest read counts, architecture
logs and the frontend/installation evidence are retained in
`port/build-universal-macos/m14-sgt24h/`. M14's Super GT pedal-polarity
block is complete. Drive-board replies remain in the recorded protocol
review block.


## M14 Remaining Input Protocol Classification — 2026-11-15

The remaining source findings have the following dispositions.

| Protocol | Native Finding And Disposition |
| --- | --- |
| Serial Guns, Virtua Cop 2 / House Of The Dead | The original uses selector values 1–8 for the eight P1/P2 Y/X byte lanes and selector 9 for offscreen. Byte writes to +12 advance the mux only for value 87. Word writes to the serial selectors have no effect. The portable reader/writer matches the original. SM2's zero-based protocol is a distinct machine implementation. Retain the native protocol. |
| Wide I/O Reads | The original wrappers zero-extend byte and word reads. The long wrapper tail-calls driver slot 28, whose mov al,dl preserves its callback address in the upper bytes. Model 2/2A use callback 004c52c0, 2B uses 004c5e60, and 2C uses 004c5880. The port previously hard-coded 004c5200 for every board. It now selects the matching upper bytes by board type. |
| ADC Sequencing | A selector write masks the starting index to 0–7. Reads advance the original byte index beyond 7, rather than applying SM2's three-bit wrap. The portable counter follows that native rule. Values within all 16 portable analog slots were compared. Beyond those slots, the original exposes adjacent process globals. A controlled pointer at original 005aa71c yields bytes 00/40/00/72 at indices 16–19, while the existing portable containment yields zero. That is an explicit limit of native equivalence. No adjacent-process mapping was added. |
| Motorcycle P2 Start | Manx TT, Manx TT Twin and Motor Raid native records provide one Start on IN0 mask 40, plus separate coin inputs. Their native idle mask CF has bit 20 clear. The shared profile's published P2 Start does not correspond to a native second Start. Retain the native wiring and the common profile presentation. |
| Indy-Protocol Drive Replies | The seven Indy 500 / Over Rev / Super GT sets use original input callback 004ca450. It prepares analog values and preserves the digital response byte. Seventy-five original executions additionally verify that an injected port-D byte 57 remains 57. The SM2 IndyDriveReply command/steering/centre response is a different board solution. Retain the native path. Sega Rally's handbrake override retains its earlier approved contract. |
| Motion Responses | Rail Chase 2 retains its previously recovered four native acknowledgements and verified D/E integration. Ski Super G / Water Ski retain the recovered native state machine and the existing 7,825 original-fragment / 15,650 portable comparisons. The dated integration and frontend/state evidence remains applicable. This review introduced no motion algorithm change. |
| Expanded-View Aim | The shared input calculation accepts widescreen columns, but the destination currently leaves that parameter zero. SM2 supplies its selected expansion. Model2EmuEx additionally permits Lua to change the scene's expansion. The user selected effective-scene authority. The adapter supplies the expansion of the last successfully presented 3D image, including Lua scene overrides. First presentation derives the scene from native rules plus the current Lua flag. The implementation and checks are recorded below. |

The current ROM-free oracle executes the complete original read wrappers
004cb700/004cb720/004cb740, selects the original driver table for each of
the four board types, and executes the native byte/word selector writes
004cb5e0/004c86c0. It compares values and selector/counter state.
**16,224 reads and 6,144 writes pass**, including serial counter overflow,
invalid selectors, every selector-write byte value and widths 8/16/32.
The initial run isolated 2,688 mismatches, all from 32-bit reads on 2B/2C.
The adjacent-process observation is recorded separately from equivalence
within the portable analog window.

Both architecture native I/O suites pass with regression assertions for
the three width contracts on all four board types. The existing EEPROM,
Daytona settings and Manx TT AMS checks also pass. Two isolated 900-frame
macOS RetroArch runs exit zero. The Fighting Vipers capture shows its title
sequence and the House of the Dead capture shows 3D attract. House of the
Dead logged one CoreAudio underrun, so these runs supply presentation and
lifecycle evidence.

The original comparison tool is `tools/input_protocol_compare.py`.
Local sources, before/after receipts, drive observation, build commands,
native I/O logs and frontend/installation receipts are retained in
`port/build-universal-macos/m14-protocols/`. The tested universal core is
installed locally with SHA-256
`5fed685bbc18cde1c7cb24ce93fff0f69e1d8c761452a65147f02e0ea3fe3f7b`.
The expanded-view aim decision and its completed implementation are recorded below.


### M14 Effective-Scene Gun Aiming

The user selected effective scene expansion on November 15. The renderer
performs geometric expansion. Native per-game rules provide the widescreen
flag and an active Lua script can override it with Model2_SetWideScreen.

The shared input calculation now receives the scene's extra native-resolution
columns. The production adapter reuses the rendering width calculation:
16:9 uses 83 columns per side and 16:10 uses 50. Pixel scaling does not
multiply those native columns. With expansion disabled, the value is zero.

The adapter remembers the expansion of the last successfully presented
image. That is the image at which the player aims. Pipeline, skipped draws
and a Lua PostDraw update retain that image's mapping until another image
is submitted. A new content load derives its initial mapping from the native
scene rule and current Lua override. Reset and Load State retain the visible
image mapping until the next successful presentation. The presentation value
is frontend state and adds no Save State payload field. The existing live
Lua interpreter remains authoritative under the approved state contract.

| Check | Result |
| --- | --- |
| Production adapter, arm64 and x86_64 | P1/P2 endpoint counters, 4:3 / 16:9 / 16:10, resolution independence, Lua Frame/PostDraw changes, last-image authority and input recovery checks pass through read_input. The repeatable target is make check-input-view. |
| Shared-profile propagation | 1,944 ROM-free cases pass for all eight destination gun sets, three expansion values and every minimum/centre/maximum combination of the four P1/P2 axes. The destination profile outputs match direct shared SM2 polling with the corresponding expansion. Includes serial guns and analog gun channels. |
| Loaded core state continuation | Virtua Cop 2 with widescreen and a live Lua script changing expansion from both Frame and PostDraw passes four exact 12-frame machine/device/PCM/image continuations. The state buffer is 12 MiB and the PCM continuation CRC is d9fb6254 for 8,820 frames. Rejected-state no-mutation checks also pass. |
| Real RetroArch | The same final universal core loads Virtua Cop 2 with the isolated script, renders widescreen 3D attract, runs 900 frames and exits zero in 19.55 seconds. The screenshot and effective options are retained. |

The final universal core and matching info are installed locally. Final
SHA-256 is recorded in the local installation receipt. The earlier receipt
above identifies the intermediate wide-read correction. Tools and compact
results remain in port/build-universal-macos/m14-protocols. The bounded M14
control-route/protocol group is complete. The ADC adjacent-process limit
documented above and physical-device/gameplay qualification retain their
explicit limits.

## Version 0.4.0 Publication Preflight — 2026-11-15

The user authorized commit, push and release of the pending tree. Runtime and
Core Info versions are 0.4.0. The universal macOS build enables SHARC, TGPX4
and A68K. Arm64 and x86_64 sound, native I/O/EEPROM, effective-scene input-view
and network regression targets pass; the universal ABI/rejected-content check
passes. The registered Core Options inventory is regenerated from this build.
The release carries the completed audio, Lua, selected renderer and bounded
input-route work; existing detailed evidence above retains its measured scope.
M30 residual research is optional/deferred and controlled GL recovery is closed
by user decision. Physical devices and broader platform gameplay are not newly
qualified by this publication. Five-platform CI/package results and final
public-asset verification follow the committed-source preflight.
