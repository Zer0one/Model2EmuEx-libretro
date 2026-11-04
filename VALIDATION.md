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

The exploratory Sega Rally session reached its 900-second bound and exited 0 after the watchdog QUIT; its timeout remains recorded. A separate VF2 profile session entered the native Input Test and opened the frontend menu, but UI access lost its window before the Normal selector was changed. It was closed normally (exit 0, no timeout). That live change and paused-menu metadata refresh remain uncompleted in the frontend, despite passing adapter tests. No retry or broader campaign followed. No core implementation change was justified; only reusable test tooling and documentation changed.

### Post-Test Artifact Retention

At the user's request, cleanup covered only this M08 audit and the preceding M18 audit plus explicitly named task-owned temporary files. It removed 1,004 files and 496,291,840 allocated bytes (approximately 473 MiB). `m08-inputs-20261102/cleanup.json` records every removal and 154 retained-file hashes, verified after cleanup. All 197 protected source/core/configuration hashes and the pristine sibling checkout remained unchanged.

Retained evidence includes the accepted M08 screenshots, recipes, native-value receipts and logs; M18 visibility/style keyframes, timeout pairs (22/24), restored-aim frame 25, custom artwork/restart and Auto fallback images; and one useful `vcop.state`. Redundant raw screenshot sequences, duplicate/failed state probes, regenerable replay files and temporary OCR/compiler outputs were removed. Earlier capture counts describe acquisition, not retained file counts. No ROM, user save, unrelated process, core binary or global frontend setting was removed or changed. No commit or push was made.


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
