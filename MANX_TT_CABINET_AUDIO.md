# Manx TT Cabinet Audio

Date: 2026-10-22. M24 integrates current SM2 cabinet audio for the destination
`manxtt` and `manxttc` sets. The pristine standalone checkout is untouched.

## Reference And Menu Contract

Audio → **Manx TT: Cabinet Audio** uses the same label, help, Enabled/Disabled
values and Enabled default as current SM2. It remains registered for every game
and is inert outside the Manx TT family. Changes apply on Resume without a main
machine reset. A changed audio bank resets its sound boards and clears stale
frontend samples, as in SM2.

| NVRAM Cabinet | Enabled | Disabled | Additional Board |
| --- | --- | --- | --- |
| Twin | Twin SCSP program/samples | Selected Set SCSP program/samples | Disconnected |
| Deluxe | Deluxe SCSP program/samples | Selected Set SCSP program/samples | Connected When Its ROMs Are Available |

Disabled retains the selected set's sound ROMs; it does not remove the hardware
required by a Deluxe cabinet. This is SM2's policy. Cabinet Type remains the
existing operator NVRAM selector, independently owned by the NVRAM engine.
Audio selection does not rewrite NVRAM, rename content, or change Save RAM paths.
The last valid cabinet is retained during unfinished Service Menu EEPROM writes.

Only the required sound regions are read. The selected archive has precedence,
then siblings `manxttc`, `manxtt`, `manxttdx`, following SM2. The destination's
existing ZIP/loose-file reader loads these regions in its native word layout;
optional donor chips always receive size, decompression and CRC validation, as
in SM2's sound-region loader. No new archive format or game entry is advertised.
Missing optional ROMs retain selected-set audio and emit the same SM2 notices;
they do not make ordinary content loading fail. The primary loader also treats only Manx TT auxiliary regions 12/13 as optional through an explicit neutral policy flag; standalone defaults and other regions remain mandatory. Allocation failure rejects
initialization. No production archive or save is modified.

## Native Hardware Integration

The original destination path had one sound board, fake host serial status,
no sound replies and no Manx TT AMS response. The port now reuses its native
Musashi, MultiPCM, YM3438 and SCSP implementations for the additional hardware.

- SM2's I8251 source is copied unchanged. A neutral C interface binds its host
  25 MHz UART and additional 10 MHz board UART at 31.25 kbaud. Host commands fan
  out to the SCSP and connected M1 board. Both boards return bytes to the host;
  host ready pins drive IRQ 10 and M1 receive-ready drives IRQ 2.
- The SCSP return wire uses SM2's 14-sample transmit interval. The additional
  M1 board uses its 10 MHz CPU, audio-before-CPU scheduling, instruction overshoot
  and fractional-cycle carry, one populated MultiPCM, 8 MHz YM3438, exact
  25 MHz / 560 sample cadence, 32-frame mixer delay and linear interpolation.
- AMS follows the same Deluxe-only `FF → CE → CD` handshake. Twin retains its
  P2 input port. Raw EEPROM Cabinet Type owns AMS fitting, as in SM2; the audio
  selector does not override it.
- Existing source gains apply to the additional board. Muting continues CPU
  and chip emulation. No new filter or balance profile is introduced.

`M2_CABINET_AUDIO` is a hardware capability build flag in the independent root
Makefile. The original `port/Makefile` does not enable it. Other games retain
their existing native sound scheduling/serial path. Both standalone targets
continue to build. Import hashes, unchanged-file checks and source/license
references are in `port/snd/sm2/IMPORT.json`; the existing SM2 LICENSE/NOTICE
copies remain under `src/libretro/sm2/`.

## Save States

The 12 MiB format remains fixed. Manx TT states add ABI feature bit `0x40000000`
and an `AUD1` header extension alongside `LNK1`. Header bytes 6/7 identify the
active SCSP bank and auxiliary-board availability; bytes 8–11 fingerprint the
selected bank and optional auxiliary ROMs; bytes 12–15 contain `AUD1`; bytes
16–19 remain zero. The original payload is followed by the host UART, AMS,
SCSP return wire, additional sound CPU/chips/UART and mixer continuation.

Preflight rejects unavailable or different required sound ROMs and invalid
queues/fractions before commit. ROM bindings are restored before loading sound
CPU state. Existing rollback and current-option authority remain in force.
Older destination states remain readable with original-bank/new-hardware reset;
the current NVRAM/audio options take effect on Resume. Older cores reject the
new feature bit. External linked sessions remain non-serializable. No SM2 file
or cross-platform state compatibility is claimed.

## Existing Extensions And Catalog Scope

All 28 pinned destination entries were reviewed by source/region metadata,
without launching the catalog. Only Manx TT needs this extra sound board.
Daytona/Desert Tank/Virtua Cop Model 1 sound regions already feed their primary
native board. No current destination set declares DSB/DSB2 MPEG or the Power
Sled auxiliary SCSP/relay extension. Their reference source routes are recorded
in `port/snd/sm2/IMPORT.json`; no ineffective MPEG/relay selectors are added.
Future Model 2B/2C execution remains separate from applicable frontend
preparation, and unrequested prototype-specific work remains excluded.

## Verification And Limits

Evidence is under ignored `port/build-libretro-macos/audit/m24-manxtt/`:

- `romfree-final.log`: synthetic CRC-correct chips; Twin/Deluxe/original selection,
  unfinished EEPROM, no NVRAM writes, missing-donor notices, extra PCM reaches
  output, gain mute, timed host-to-M1 fanout and real SCSP/M1 return registers,
  ROM identity rejection, legacy reset and sample-exact auxiliary continuation.
- `frontend-final/result.json`: actual options, live Twin/Deluxe/Disabled changes,
  old-state read, old-core rejection of new states and actual content loading without auxiliary chips; 900-frame VF2 main RAM,
  SRAM and PCM are identical to the pre-M24 core.
- `state-manxtt-1/result.json` and `state-deluxe-final/result.json`: Twin and
  Deluxe 900-frame OpenGL runs, four exact 12-frame RAM/device/PCM/image
  continuations, damaged-state rejection, context recreation and exact
  fresh-process continuation. Deluxe includes the active additional board.
- `retroarch-deluxe/result.json`: real RetroArch, 1,200 frames, exit 0, Deluxe
  board-connected notice and inspected 3D attract screenshot.
- `state-final/result.json`: the final installed binary also passes the exact
  same/fresh-process state suite after 60 Deluxe boot frames.
- `installed-final/result.json` and `final-install/deployment.json`: final
  installed/source hashes match; real RetroArch loads `manxttc` with Deluxe
  donors for 900 frames, renders the attract title and exits 0. Global/scoped
  configuration hashes are unchanged.
- `common-final.log`, `native-final.log`, `build-optional.log`, `initial-errors.log`
  and `standalone.log`: shared regression, serial/AMS I/O, network, preserved
  initial-template failure handling and native/core builds.

These establish integration, rendering and PCM/state continuity. Listening,
physical controls, extended gameplay and comparison with a physical Deluxe
cabinet remain M14 qualification. They are not inferred from compilation or
nonzero PCM. Local installation evidence is indexed in VALIDATION.md.

Reproduce with `make -j4`, `make check-sound check-eeprom check-network`,
`bash scripts/check-sm2-common.sh`, and
`python3 scripts/check-manxtt-audio.py --output <new-isolated-directory>`.
