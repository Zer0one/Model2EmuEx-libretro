# NVRAM Source Review And Evidence Index

Current integration status: M11's source/adapter and representative frontend
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
