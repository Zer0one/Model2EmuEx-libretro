# NVRAM Source Review And Evidence Index

Current integration status: M29's Sonic correction is integrated and verified
on 2026-11-04; see the final section. M11's source/adapter and representative frontend
persistence checks were completed on 2026-11-02; see the follow-up below.
Historical M23 evidence remains separate from destination runtime acceptance.

Date: 2026-10-22. M23 reviews current SM2 source and destination integration.
The shared SEGA Model 2 workbook is not recreated. No new samples, game runs,
Service Menu captures or physical-device qualification are performed.

## Authority And Reproduction

Current SM2 source is primary for implemented fields, values, defaults,
templates, formatting and behavior. Photographs remain evidence of native
behavior. Historical documents and the shared workbook may lag behind code:
the older NVRAM_SETTINGS_AUDIT.md reports 311 fields; current source contains
340. The user's no-workbook/no-new-campaign instruction takes precedence over
the generic Framework F13 and campaign skill workflow.

Inspected SM2 working copy: HEAD `be696244fc425f55e3c0cab9bc43c03d44b621aa`,
with live hashes checked independently of HEAD. All 13 inspected imported files
match the live reference and their IMPORT.json hashes: NVRAM engine/data,
initial-template engine/data, Save RAM, ANRS and game database/metadata.
Extracted menu label/help functions also match current source exactly.
The older import HEAD remains historical import provenance.

```sh
make -j4
python3 scripts/audit-nvram-source.py \
  --output port/build-libretro-macos/audit/new-nvram-source-review
```

The audit reuses SM2's current `audit-nvram-core-catalog.py` parser and compiled
public routing/template APIs. It checks actual Core Options V2 registration
without content, the existing exported option inventory and existing evidence
paths read-only. Label comparisons use SM2's formatter rather than comparing
native uppercase text directly with frontend Title Case.

Current receipt: `audit/m23-source-review-20261022-complete/report.json` under
`port/build-libretro-macos/` (ignored). It records source hashes, per-set routing,
initial policy, template checks and evidence paths. No reference files or user
data were modified.

## Source And Registration Results

- All 340 operator definitions across 56 imported catalogs match source keys,
  formatted labels, ordered values, defaults and one `(Default)` label per
  selector. CORE_OPTIONS_IMPLEMENTED.json matches actual registration.
- The 28 destination sets resolve to 19 catalogs containing 117 distinct
  applicable fields. Other imported catalogs retain existing per-game
  visibility; this review adds no settings or supported games.
- Initial setup selects 22 exact templates and four explicitly compatible
  parent templates. The two Turbo entries have no approved initial template.
- For 25 non-prototype entries with a template, ROM-free decoding,
  integrity/layout checks, initial policy and preservation of the extra 48 KiB
  backup tail pass. This includes prepared Model 2B/2C data without executing
  those machines. Daytona93 retains existing metadata/template only; no new
  prototype qualification was performed.

The engine consumes the first 16 KiB of backup RAM and all 128 EEPROM bytes.
Model2EmuEx exposes 64 KiB plus EEPROM through its existing raw frontend buffer;
SM2 uses a separate header/container. Shared fields and templates do not imply
interchangeable frontend save files. First-frame import preserves frontend Save
RAM precedence. Native Daytona I/O lane synchronization is an already-integrated
destination boundary, not the excluded setup fallback.

## Destination Routing Index

Counts are source-defined operator fields, not acquired destination samples.
Exact templates and inherited option catalogs are independent decisions.

| Destination Sets | Catalog | Fields | Initial Template Source |
| --- | --- | ---: | --- |
| fvipers | fvipers | 6 | Exact |
| daytona | daytona | 8 | Exact |
| daytona93 | daytona93 | 4 | Existing exact template; metadata only in this review |
| daytonat, daytonata | daytona | 8 | None; no guessed parent seed |
| daytonase | daytona | 8 | Exact daytonase |
| daytonam | daytona | 8 | Explicitly compatible daytona parent |
| daytonas | daytonas | 9 | Exact |
| daytonagtx | daytonagtx | 8 | Exact |
| desert | desert | 4 | Exact |
| vcop | vcop | 4 | Exact |
| vcopa | vcop | 4 | Explicitly compatible vcop parent |
| skytargt | skytargt | 4 | Exact |
| vf2o | vf2o | 8 | Exact |
| vf2 | vf2 | 8 | Exact |
| vf2b | vf2 | 8 | Exact vf2b |
| vf2a | vf2a | 8 | Exact |
| srallyc | srallyc | 6 | Exact |
| srallycb | srallyc | 6 | Explicitly compatible srallyc parent |
| vcop2 | vcop2 | 4 | Exact |
| motoraid | motoraid | 8 | Exact |
| manxtt | manxtt | 8 | Exact |
| manxttc | manxtt | 8 | Exact manxttc |
| overrev | overrev | 7 | Exact |
| overrevb | overrev | 7 | Explicitly compatible overrev parent |
| skisuprg | skisuprg | 5 | Exact |
| waverunr | waverunr | 6 | Exact |
| segawski | segawski | 2 | Exact |

## Existing Evidence And Limits

The receipt indexes current `data/diagnostic-menus/<set>.yaml`,
`scripts/libretro_nvram_samples.<set>.toml` and existing campaign outputs.
GAME_SETTINGS_CATALOG.md and CLONE_NVRAM.md retain native observations and
accepted clone evidence. Exact-set recipes, catalog references and compatible
template parents remain distinct; parent documentation alone is not a clone
observation or template approval. Relative recipe paths follow SM2's runner.

The VF2 summary retains old temporary artifact paths. All 120 referenced files
are present under the permanent campaign's saves/screenshots directories; the
index records that relocation without rewriting the source summary. Some
historical clone recipes have no summary at their current configured path.
This is an evidence-location limit, not grounds to discard accepted embedded
templates or repeat acquisition. SM2 clone acceptance remains traceable through
CLONE_NVRAM.md and source data.

| Destination Evidence | Established Boundary |
| --- | --- |
| `scripts/check-sm2-bridge.cpp`, via `bash scripts/check-sm2-common.sh` | Existing labels/defaults, visibility/gate, VF2 all-value application, checksums/tail preservation, invalid/disabled selections and template routing. ROM-free adapter evidence. |
| `audit/sm2-applicability/{vf2,srallyc}.json` | Existing source/template application probes, not target Service Menu acceptance. |
| NVRAM_SAVESTATE_DIAGNOSTIC.md and `audit/srallyc-nvram-report-20261021/` | Existing destination Country Export/USA visual checks and EEPROM framing correction; not every Rally field. |
| `audit/m13-catalog-loopback/conventions/results.json` | Existing APIs 2/1/0 and four-family ANRS authority, handover, reset and frontend Save RAM reload. ABI evidence, not complete operator-menu coverage. |
| `audit/m13-catalog-loopback/state-vf2/result.json` | Existing current-option/NVRAM authority during state restore and exact continuation. |
| `audit/m13-catalog-loopback/retroarch-state-vf2/result.json` | Existing real RetroArch Save/Load and exact image restoration, not a sample campaign. |

## Finding And Follow-Up

**Initial-template error reporting differs from SM2.** SM2 core.cpp rejects an
invalid embedded template or an unsupported post-seed layout. Here,
`sm2lr_initial_nvram` returns false on failed seed and discards the subsequent
`nvram::apply` result. It can therefore continue without initialization or report
success after failed policy application. All currently checked applicable
templates passed; no active production-template failure was reproduced during
the review. The omission was corrected immediately in the follow-up below,
rather than left as a deferred M25 task.

No field/value/default or approved-template routing mismatch was found.
Turbo templates remain deliberately unavailable; no parent permission is
inferred. M11's wider destination persistence/Service Menu qualification remains
separate from completed source reconciliation. No calibration, acquisition,
exhaustive game launch, commit or push was performed.

The original M23 audit examined core
`7d113892c9f24bc7b3fa1eb11e904b3e4e2a703fdfb36d808ccddb17dec4c684`.
That source-review receipt predates the correction below.

### Immediate Error-Handling Correction — 2026-10-22

The destination bridge now distinguishes ordinary Unchanged (disabled or no
template), Loaded, Invalid Template and Invalid Layout. It checks the same
seed/apply results as current SM2, including skipping policy application when
there is no operator catalog. Invalid results reach the C adapter explicitly;
it logs/notifies with SM2's messages, unloads partial content and returns a
failed load. Negative results can no longer be mistaken for successful seeding.
No new template, fallback, option, storage format or standalone behavior was added.

`scripts/check-initial-nvram-errors.py` builds isolated test dylibs: one with a
corrupt VF2 template CRC, one with a valid decode but invalid native layout.
Both enabled cases reject content, emit the expected message and release
Save RAM. With automatic setup disabled both still load; the production core's
normal enabled case also loads. No native frames are executed in these tests.
Production imports/templates remain unchanged. Existing common checks pass,
including disabled/no-template handling, approved parent routing and tail
preservation. Evidence: `audit/nvram-initial-errors-20261022/`.

The corrected core and matching info were copied atomically to the authorized
local RetroArch directories, with backups and an unchanged global-config hash.
Build/installed core SHA256:
`80670ced8e9fba92e8f459d6961cc053086d1a95b2e83b84127a9da3fda51091`.
The bounded installed-core frontend check is recorded in
`retroarch-vf2-final/result.json` under the correction evidence root. No commit or push.

## M11 — Adapter Coverage And Raw Persistence (2026-11-02)

The current SM2 implementation remains the authority for fields, values,
checksums and approved templates. The existing `scripts/audit-nvram-source.py`
confirms all 340 fields/56 catalogs and actual registered labels/values/defaults
still match that source. No workbook or new acquisition was involved.

The existing `scripts/check-sm2-bridge.cpp` now enumerates the actual destination
catalogue. Explicit selections through the unchanged SM2 engine form the
expected image; the destination receives those choices through frontend keys
and its own bridge. All 526 value cases across 25 sets/18 catalogs match,
including checksums/layout, disabled/no-op behavior and preservation of the
extra 48 KiB backup tail. This checks adapter/key/memory boundaries rather than
revalidating SM2's native field mappings. Prepared Model 2B/2C data is exercised
without executing those machines. Both Turbo sets retain their approved
no-template/no-mutation result; Daytona93 stays metadata-only.

`scripts/check-frontend-contracts.py` additionally creates an isolated native
raw VF2 image using the actual core's existing Hard override. Fresh core loads
with automatic setup enabled and disabled preserve that entire saved image
byte-for-byte when overrides are off. Enabled Normal overrides retain authority
while preserving the extra backup tail and EEPROM; a later Hard selection causes
one live reset. The raw buffer remains 65,664 bytes with no new header or import.

The existing RetroArch runner accepts that isolated fixture via `--save-ram`.
Two separate 900-frame frontend processes, both with automatic setup enabled
and overrides disabled, preserve Hard, the native raw size and an extra-RAM
marker. The second loads the first process's saved file; both exit normally.
ROMs are read directly from the archive; production saves remain untouched.

Evidence: `audit/m11-persistence-20261102/result.json`, `common.log`,
`source/report.json`, `abi/result.json`, `frontend-persistence.json` and the two
RetroArch receipts. Core SHA256 remains
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.
No core fix was needed. M11's integration/adapter/persistence contract is
complete; per-title native Service Menu acceptance and gameplay remain explicit
M14 qualification, rather than being inferred from these checks. No replacement
acquisition campaign, prototype execution, commit or push.

## M29 — Sonic Shared Derived Energy Word (2026-11-04)

The current SM2 catalog has two independent selectors, ENERGY(1P) at backup
`0x3343` and ENERGY(VS) at `0x3344`. Its separately acquired sample deltas also
patch overlapping bits at `0x3354` (masks `0x30` / `0x7c`). Applying both patches
unconditionally causes repeated Changed results and can overwrite the derived
value even when the corresponding selector did not change. This was exposed
by the destination all-catalog idempotence check; it is shared catalog behavior,
not a missing standalone Model2EmuEx feature.

### Existing Evidence And Native Cause

The existing SM2 campaign was reused read-only:
`~/Documents/RetroArch/sm2-nvram-analysis/schamp/generated`, including all eight
energy samples and the Service Menu screenshots. Recipes and menu metadata are
`../sm2-emu-libretro/scripts/libretro_nvram_samples.schamp.toml` and
`../sm2-emu-libretro/data/diagnostic-menus/schamp.yaml`. No new workbook or bulk
acquisition campaign was created. The Hard/Normal and Normal/Hard screenshots
confirm that these are separate operator settings.

The original game routines explain the shared word. Sonic Championship's
callbacks at `0005dfe4` / `0005e014` and Sonic The Fighters' callbacks at
`0005df58` / `0005df88` both write a 16-bit value at backup `0x3354`, and the
corresponding RAM mirror. Their menu handlers call them on selector changes.
**Both write `0x3354`; neither redirects the VS result to `0x3356`.**

| Selector | Easy (0) | Normal (1) | Hard (2) | Hardest (3) |
|---|---:|---:|---:|---:|
| ENERGY(1P) Derived Word | 176 | 160 | 144 | 128 |
| ENERGY(VS) Derived Word | 220 | 200 | 180 | 160 |

All 16 cases (eight per set) were checked by executing the unchanged five-
instruction lookup/store fragment in the port's i960 interpreter, stopping
before the checksum call. The archived ROMs were read directly. The receipts
are `port/build-m29-nvram/native-energy.log` and the two native-reference logs;
these are ignored audit outputs, not generated game code to distribute.

The VS Normal campaign sample retains 160 because that recipe does not change
the already-Normal selector. It therefore does not demonstrate a VS Normal
callback result of 160; the native table gives 200. A combined frontend option
would still need to choose callback ordering and would diverge from the native
menu/SM2 interface. The two exposed options remain unchanged.

### Approved Correction And Verification

User decision, 2026-11-04: preserve the native quirk. Change the selectors through
the existing masks, and derive the shared word only when that selector changes.
When both change, apply callbacks in menu order: 1P followed by VS. Reapplying
unchanged selections preserves the prior word and reports Unchanged. Keep the
native checksum and unrelated memory intact; do not add a persistence container,
fix the game's shared destination, or replace emulator behavior with SM2 HLE.

`nvram_settings_data.inc` now describes only the two selectors; the engine
implements their native conditional side effect. The two local adaptations are
recorded in `IMPORT.json`, with both donor and destination hashes. The source
review still rejects unrecorded destination changes or reference drift and still
requires identical frontend option names, values, defaults and visibility.
The sibling SM2 repository is untouched; this correction is applicable there
but has not been applied or sent to its chat by this task.

- `scripts/check-sm2-sonic.cpp`: 1,536 transitions across both games, all old/new
  selector pairs, independent/both overrides, shared-word ordering, complete-word
  writes, unchanged-word preservation, native checksum and repeat idempotence.
- `scripts/check-sm2-common.sh`: complete suite passes, including 67 destination
  NVRAM routes / 3,035 value cases, 70 input bindings, timing and native state/ABI
  regressions. The earlier failing assertion remains active.
- `scripts/audit-nvram-source.py`: 340 operator fields / 56 catalogs, no
  registration or snapshot errors, documented adaptations and all pins checked.
- Actual RetroArch: 2,100 frames each for initial Hard/Normal application and
  fresh reload with NVRAM overrides disabled. Both Service Menu captures show
  Hard/Normal; both 65,664-byte raw saves retain selectors 2/1 and derived word
  144. Both runs exit normally. This verifies a representative frontend path,
  not all 16 combinations in the Service Menu.

Reproduction logs, source review, replay recipe and frontend receipt are under
`port/build-m29-nvram/`. No ROM, user save, existing campaign artifact, installed
core, sibling reference or pristine standalone file was modified.

### Manual And Gameplay Consumer Follow-Up (2026-11-04)

M29 was reopened after the user identified a missing acceptance case: overrides
must be reapplied at least on the next content load after the user commits
changes through the native Service Menu. The earlier disabled-override reload
only proves persistence and does not prove this authority contract.

The SEGA *Sonic The Fighters Service Manual*, 420-6218, printed page 8
(PDF page 10), Game Assignments (E)/(F), describes ENERGY(1P) as character
vitality in single-player play and ENERGY(VS) as character vitality in versus
play. Both have Easy/Normal/Hard/Hardest values, with greater vitality at Easy
and less at Hardest; both default to Normal. Pages 8-9 do not describe another
operator selector choosing between these two settings. DAMAGE is separately
described as damage compensation, not the 1P/VS energy selector.
Source: https://arcade.segakore.fr/file.php?id=5 (original SEGA manual scan,
visually inspected). This establishes intended semantics, not memory layout.

Additional Sonic Championship code inspection distinguishes menu side effects
from gameplay consumers. The fragment at `0x11bac` reads selectors `0x3344`
and `0x3343` independently, uses tables at `0x11c40` and `0x11c48`, and stores
two RAM values at `0x50a708` / `0x50a70a`. Both tables contain
160/140/130/120 for Easy/Normal/Hard/Hardest, unlike the Service Menu callback
tables above. The fragment at `0xc3d8` selects one of those values for
`0x5000a0` according to the byte at `0x50004c` (0/1 selects the 1P value;
2 selects VS in the tested cases). Neither fragment reads backup `0x3354`.

The unchanged native fragments were executed through the existing i960
interpreter for all 16 selector pairs and three mode-byte values (48 cases),
with the shared word deliberately set to an unrelated value. All results
matched the independent table lookups and selection. This is native-code
fragment evidence for `schamp`, not a complete gameplay proof or a claim that
no other code ever reads the shared word. Reproduction source/log:
`port/build-m29-nvram/native-energy-consumers.c` / `.log` (ignored).

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
