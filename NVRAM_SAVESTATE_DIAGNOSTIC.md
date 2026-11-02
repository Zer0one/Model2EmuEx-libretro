# Sega Rally NVRAM And Save State Report

Date: 2026-10-21.

## Save State Availability In RetroArch

The reported OSD was “Core does not support save states.” The installed library exposed a fixed 12 MiB serializer and passed a fresh RetroArch 1.22.2 save/load test. Inspection of the global RZIP Core Info cache found the original Model2EmuEx entry: Development display name, description saying Save States unavailable, and `savestate_support_level: 0`. The installed `.info` already described the implemented capability, so the catalogue was stale. No older active user process remained available to inspect; an old mapped library was considered but was not established as the cause.

The `.info` now declares `savestate_features = "serialized"`, matching SM2. Only the Model2EmuEx cache entry was refreshed from a freshly parsed entry and the serialized feature level; all other cached entries were preserved. The installed library, `.info` and cache were backed up before atomic replacement. Reload RetroArch to discard any in-memory catalogue from the old session.

## Automatic Initial NVRAM Country

The user's existing 65,664-byte `srallyc.srm` already contained country value 2 (Export), exactly as the approved automatic-initial policy and NVRAM Settings default require. The patch/checksum engine and template were therefore not changed. A read-only copy nevertheless produced JPN in the native Game Assignments menu.

Native `ee_init` zeroed `wait_start`, making the 93C46 command parser treat leading idle zeroes as opcode bits. Sega Rally emits such zeroes. The original trace decoded no EEPROM transactions, so the game used native defaults despite a valid image. Setting `wait_start = 1` makes the parser wait for the start bit, matching `src/hw/eeprom_93c46.cpp` in the current SM2 reference. The same copied image then decoded 54 EEPROM transactions in the bounded probe and showed Export in Game Assignments.

This is a frontend-neutral machine correction in `port/m2/m2board.c`, also used by this repository's standalone/headless builds. The pristine sibling remains unchanged. No frontend remapping, new setting, template reacquisition, ROM change or user-save migration is required.

## Verification

- `make check-eeprom`: ROM-free native I/O-pin regression for 0–7 leading zeroes, reads, unlocked writes and interrupted commands. The previous framing fails; corrected framing passes.
- `make check-sound`: existing SCSP callback-size regression passes.
- Core, standalone and headless builds pass.
- An isolated core/GL Service Menu run without an existing save shows Export from Automatic Initial NVRAM Setup.
- A second isolated core/GL Service Menu run with NVRAM Settings enabled and Country USA shows USA, with byte 9 equal to 1.
- The user's save copied into the isolated native runner shows Export after correction. The production `.srm` is untouched.
- The corrected core passes four exact same-process 12-frame state continuations, cold save/load, invalid-state rejection, context recreation and exact fresh-process continuation for Sega Rally at Native timing.
- Before the EEPROM correction, the installed-core real RetroArch test had already saved/loaded a 12,582,936-byte frontend container, matched restored pixels after three controlled machine frames, resumed and exited cleanly. This separates the working serializer from the stale catalogue.

The corrected installed core SHA-256 is `29b2fd66531019d0241579998e7bd574b8edf54e3adca22ef09d312f01115518`. The installation receipt verifies unchanged user-save SHA-256 `60215556a9bf10f274525329f08f2dbdcc26d62ffc97411fa510b84bb5c0d074` and unchanged global configuration SHA-256 `3f6734f47d8d6eeb9e94472906a1c7464e1b6356c8ae70f375a90c119d788f3b`.

The final installed build was also tested in RetroArch with a copy of the refreshed global cache: support level 2, correct rolling display name, successful state creation/load, exact restored image after three controlled machine frames, resumed advancement and clean exit. Evidence: `port/build-libretro-macos/audit/srallyc-eeprom-cached-retroarch-20261021/result.json`.

## Evidence And Limits

Ignored evidence:

- `port/build-libretro-macos/audit/srallyc-nvram-report-20261021/`: before/after native menu captures, EEPROM traces, regression probes, `fresh-export/menu.png`, `override-usa/menu.png`, installation backups and `deployment.json`.
- `port/build-libretro-macos/audit/srallyc-eeprom-state-20261021/`: final ABI/GL and fresh-process continuation results.
- `port/build-libretro-macos/audit/srallyc-savestate-report-20261021/`: initial real frontend save/load result.

Only Country is visually qualified in this incident; other operator values, all games and physical devices are not qualified by these tests. The user's later listening confirmation reports the navigator voice is now correct after the separate SCSP scheduling correction. The black upper-sky report, subsequently resolved in SKY_SRALLYC_DIAGNOSTIC.md, was reported as follows: the user states it occurs during normal gameplay, without any prior Save State load, and is absent in the first section. A clean attract-mode screenshot sweep does not reproduce that exact paid-gameplay camera/position. The later supplied state reproduces that region; the renderer now uses the hardware backdrop pen. No commit or push.
