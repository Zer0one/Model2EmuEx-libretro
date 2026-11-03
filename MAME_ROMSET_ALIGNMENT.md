# MAME ROM Set Alignment

Date: 2026-10-20. Scope: Libretro Content Metadata Only. No Commit Or Push.

Reference: [Official MAME Model 2 Driver](https://github.com/mamedev/mame/blob/b106b9345dc32ab3c99514d6caeeabe0d0a78830/src/mame/sega/model2.cpp), revision `b106b9345dc32ab3c99514d6caeeabe0d0a78830`. Source SHA-256: `31fc8da039a0d13b5e83c43b8c0cf5fd5e112f672b3920200736c7be0077e562`.

## Policy And Boundary

- MAME set names, parent relationships, titles and required file identities take precedence over the historical emulator metadata.
- The Libretro build selects a generated overlay with `M2_ROMSET_MAME`; standalone/headless builds keep the original `port/m2/gamedb.inc`. The pristine sibling checkout is untouched.
- The existing 29-entry upstream catalogue becomes 28 Libretro entries: `dayton93` becomes `daytona93`, and `srallyp` is excluded by explicit user decision because no matching MAME main-program identity was found. No new MAME games or board backends are added.
- No ROM archives, production saves or installed cores were changed. Existing archives with the old `dayton93` stem must be supplied under the canonical MAME set name; no automatic save-file migration is performed.
- The legacy shared `model2.zip` search remains an additional compatibility location; it is not presented as a MAME BIOS requirement. Canonical content and MAME parent archives are searched first.

## Model 2B Expansion — 2026-11-03

The current Libretro catalogue has **61 sets**, including **35 Model 2B**.
The 28-set baseline described below remains the historical starting point.
The standalone database still contains 29 entries.

The original 1.1a PE initializers complete with no errors under the existing
`tools/dump_games.py`. The list at `0x010ed5e0` has 29 entries, but 22 additional
Model 2B records are initialized outside that list. Their main-program size/CRC
signatures each match one Model 2B set in pinned MAME. The recovered input
tables, hook identities, native ROM operations and original record addresses
are in `src/libretro/data/gamedb_model2b_recovered.inc`.

Added: `doab`, `dynamcopb`, `dynabb97`, `dyndeka2b`, `gunblade`, `indy500`,
`indy500d`, `indy500to`, `lastbrnx`, `lastbrnxj`, `lastbrnxu`, `pltkids`,
`rchase2`, `schamp`, `sfight`, `sgt24h`, `vonu`, `vonj`, `vstriker`,
`vstrikero`, `zerogun`, and `zerogunj`. MAME parent names are retained even
including the parent of `vonu` and `vonj`.

Dead or Alive Revision B has one explicit MAME polygon identity correction:
`mpr-19324.19` at offset `0x1000000`, size `0x400000`, uses CRC `0d6bf454`
in MAME and `d972201f` in the original record. The generator checks region,
filename, offset, size and old CRC before replacing it.

Four additional MAME revisions use explicitly checked donors: `overrevba`
from `overrevb`, `rchase2a` from `rchase2`, `doa` from `doab`, and `von`
from `vonu`. Dead or Alive and Virtual-On retain the donor input wiring.
The port did not execute the unidentified donor i960 hooks, and the new
revisions carry no borrowed hook address. The generator requires identical
non-program file identities and placement, and identical program slot layout; it substitutes each program
by exact offset, size and donor CRC. The donor remains recorded in the manifest.

The final seven MAME entries use the pinned MAME slot maps. `vonr` uses the
verified Japanese layout, `fvipersa` and `fvipersb` use their own program and
data EPRs without borrowing the Revision D wait-loop address, and `dynabb`
uses the earlier cabinet's ROM population. The three Power Sled definitions
use pinned MAME ROM identities and the guarded SM2 program patches. The
reconstructed Main is based on Relay; its original Main ROM was not dumped.

The 61-set compiled metadata and ROM-free archive tests pass. Distribution
builds enable Model 2B with `SHARC=1`. Preserved hook/input routine identities
do not mean every original routine is implemented. Indy 500 reaches rendered 3D
attract in isolated macOS RetroArch (1,800 frames, normal exit). Dead or Alive
Revision C and Virtual-On Twin Export also reach rendered 3D attract in
isolated macOS RetroArch runs with the default CRC policy.
No ROM archive was modified or copied.

## Applied Differences

- 125 filename corrections across set definitions, preserving payload size and CRC. These are occurrences across sets, not 125 distinct files.
- Four wildcard CRCs pinned to MAME for Daytona GTX: `gtx.12`, `gtx.13`, `bank0.bin` and `bank1.bin`. This tightens content identity; it does not implement the missing GTX protection hook.
- Daytona 1993 sound program corrected from the later `epr-16720.7` / `epr-16721.8` pair to MAME `epr-16489.7` / `epr-16490.8`. This is an intentional payload revision change.
- Three Model 2A video-table files removed from each of eleven original Model 2 set requirements. MAME does not associate those tables with original Model 2. Native TGP table functions read the lower table range, below the removed tail at 0x0c0000; allocation and existing table placement are preserved.
- MAME parent identities and titles replace historical descriptions, including `manxttc` inheriting from `manxtt`. Root sets now have no parent; the archive-search deduplication handles that NULL parent safely before continuing to the optional shared archive.
- Main-program size/CRC signatures match MAME for every included set. GTX previously used wildcard CRCs; the same named files now have explicit MAME CRCs.

## Included Sets

| Historical Name | Canonical MAME Name | MAME Parent | Board | File Renames | Other Changes |
| --- | --- | --- | --- | --- | --- |
| fvipers | fvipers | None | Model 2B | 0 | None |
| daytona | daytona | None | Model 2 | 10 | 3 unused video-table requirements removed |
| dayton93 | daytona93 | daytona | Model 2 | 15 | 3 unused video-table requirements removed; 2 sound-program revisions corrected |
| daytonat | daytonat | daytona | Model 2 | 10 | 3 unused video-table requirements removed |
| daytonata | daytonata | daytona | Model 2 | 10 | 3 unused video-table requirements removed |
| daytonase | daytonase | daytona | Model 2 | 12 | 3 unused video-table requirements removed |
| daytonam | daytonam | daytona | Model 2 | 10 | 3 unused video-table requirements removed |
| daytonas | daytonas | daytona | Model 2 | 14 | 3 unused video-table requirements removed |
| daytonagtx | daytonagtx | daytona | Model 2 | 24 | 3 unused video-table requirements removed; 4 wildcard CRCs pinned |
| desert | desert | None | Model 2 | 2 | 3 unused video-table requirements removed |
| vcop | vcop | None | Model 2 | 0 | 3 unused video-table requirements removed |
| vcopa | vcopa | vcop | Model 2 | 0 | 3 unused video-table requirements removed |
| skytargt | skytargt | None | Model 2A | 0 | None |
| vf2o | vf2o | vf2 | Model 2A | 0 | None |
| vf2 | vf2 | None | Model 2A | 0 | None |
| vf2b | vf2b | vf2 | Model 2A | 0 | None |
| vf2a | vf2a | vf2 | Model 2A | 4 | None |
| srallyc | srallyc | None | Model 2A | 3 | None |
| srallycb | srallycb | srallyc | Model 2A | 3 | None |
| vcop2 | vcop2 | None | Model 2A | 2 | None |
| motoraid | motoraid | None | Model 2A | 0 | None |
| manxtt | manxtt | None | Model 2A | 4 | None |
| manxttc | manxttc | manxtt | Model 2A | 2 | None |
| overrev | overrev | None | Model 2C | 0 | None |
| overrevb | overrevb | overrev | Model 2B | 0 | None |
| skisuprg | skisuprg | None | Model 2C | 0 | None |
| waverunr | waverunr | None | Model 2C | 0 | None |
| segawski | segawski | None | Model 2C | 0 | None |

## Additional MAME Regions

The manifest retains metadata for additional ROMs that this backend does not consume: drive-board and communication CPU images, plus the cabinet EEPROM images for Manx TT. Their absence from the required-file list does not imply those devices are emulated. Existing native region layout, input wiring, hooks, cycle timing and sound mixer are preserved. Future device integration must use the same pinned metadata or a reviewed update.

## NVRAM Identity

The canonical `daytona93` name now selects the existing exact SM2 NVRAM catalogue/template path. Other matching set names remain unchanged. The removed `srallyp` can no longer inherit an assumed Sega Rally operator catalogue through a non-MAME content name. The complete imported NVRAM catalogue remains available as preparation; unsupported board execution and unimplemented aliases in the broader SM2 metadata are not silently promoted to runtime support.

## Verification

- `python3 scripts/check-mame-romsets.py --source /path/to/model2.cpp`: passes all 28 compiled names/titles/parents, every consumed filename/size/CRC tuple, main-program identities, unchanged native input/hook wiring, 29-entry standalone isolation, exclusion/rename policy and ROM-free stored/deflated split-parent/merged-path archive lookup, including missing root archives with NULL parents.
- `make -j4` and `make standalone -j4`: pass. No dependencies installed.
- `audit/mame-aligned-daytona`: 900 frames, exact RAM/PCM match to pristine same-revision upstream with identical initial NVRAM. OpenGL lifecycle/options harness passes. An isolated support ZIP supplies the pristine runner with the three historical video files; the Libretro catalogue does not require them. Source ROM archives remain untouched.
- `audit/mame-aligned-vf2`: 900 frames, exact RAM/PCM match to pristine same-revision upstream; OpenGL harness passes.
- `audit/mame-aligned-daytona93`: canonical MAME archive loads, 900-frame 3D attract scene inspected, 926 total rendering callbacks including lifecycle checks. The sound-program revision intentionally differs from historical upstream; no old-audio equivalence is claimed.
- No physical input, audible sound or complete gameplay claim follows from these tests. Model 2B/2C and unknown protection hooks retain their previous runtime limitations.

## Reproduction And Provenance

The generator requires the pinned official source SHA-256 and rejects a different driver until explicitly reviewed. Generated files are checked in as plain ROM metadata, without ROM bytes or ROM-derived executable game code.

```sh
curl -L https://raw.githubusercontent.com/mamedev/mame/b106b9345dc32ab3c99514d6caeeabe0d0a78830/src/mame/sega/model2.cpp -o /tmp/model2.cpp
python3 scripts/align-mame-romsets.py --source /tmp/model2.cpp --check
python3 scripts/check-mame-romsets.py --source /tmp/model2.cpp
```

Source artefacts: `src/libretro/data/gamedb_mame.inc` (runtime overlay) and `src/libretro/data/mame_model2_catalog.json` (source identities and complete per-file change manifest).
