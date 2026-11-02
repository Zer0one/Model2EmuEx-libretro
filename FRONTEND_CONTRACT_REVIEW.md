# Frontend Error Handling, Recovery And Save Import Review

Analysis: 2026-10-22. Implementation: 2026-11-02. The analysis below describes
the pre-fix adapter; the implementation and verification are recorded at the
end. ROADMAP.md remains the sole implementation roadmap.

## Scope And Authority

Compare current SM2 source with the destination in four areas: frontend
notifications/error propagation, save import, resource recovery and option
corrections. Framework 0.1.42 F01/F03/F12/F14/F17, its notification policy, and current
REFERENCE_SOURCES.md were inspected, together with SM2's porting manifesto,
design and relevant implementation. Existing approved exclusions remain in
force. No workbook or new acquisition campaign is part of this review.

Reference SM2 HEAD: `be696244fc425f55e3c0cab9bc43c03d44b621aa`; live file hashes,
not HEAD alone, identify the inspected working copy. Evidence and source hashes:
`port/build-libretro-macos/audit/m25-analysis/{result.json,sources.json}`.
The native target remains the existing upstream baseline plus the local port.

## Confirmed Adapter Omissions — Analysis Baseline

| Finding | SM2 Behavior | Destination Behavior | Consequence And Required Alignment |
| --- | --- | --- | --- |
| A1 — Pending NVRAM Overrides | Retain a pending request when LayoutNotReady is returned. Retry before/after frames, coalesce changes and reset once after a real persisted change. Warn and clear after 600 unsuccessful frames. | Attempt only on first frame, an option change or state-option refresh. LayoutNotReady is logged; the request is not retained. | A valid later layout can retain native values despite enabled overrides. Transfer the existing SM2 pending/retry/timeout lifecycle, including ANRS-managed fields. |
| A2 — Error Notifications And Fatal Recovery | A common message helper preserves severity, negotiates extended OSD messages with legacy fallback, and uses priority 2 for errors. Fatal runtime/GPU errors stop rumble, mark content failed and request frontend shutdown. Loading failures report their reason and reject content. | Many load/GPU/audio/state paths use an INFO-only log helper. Network/template paths already use the extended message helper, but errors there still have priority 1. GPU initialization errors return without declaring failure; audio faults request shutdown without the common immediate failure cleanup or detailed OSD notification. | Unify equivalent failure paths with SM2 severity, notification and cleanup behavior. Preserve recoverable errors as recoverable; do not turn every rejected state or optional resource into a fatal error. |
| A3 — Unannounced OpenGL Context Loss | context_reset abandons old render-pass handles before destruction, avoiding GL deletion against a replacement context. Normal context_destroy releases live resources. | context_reset calls context_destroy first, which deletes renderer, timing-overlay and crosshair handles. There is no abandon path for a lost context. | Add the corresponding destination-neutral abandonment path for all owned GL resources. Retain ordinary destruction when the frontend announces it. Existing texture/cache reconstruction remains separate and already has announced-recreation evidence. |
| A4 — Invalid Network Option Correction | Invalid Linked Cabinets/ANRS values use the applicable fallback and enqueue a warning plus SET_VARIABLE correction. Publish after leaving option readers, allowing frontend callbacks to re-enter safely. | Safe fallback and duplicate-warning suppression exist, but the invalid frontend value remains stored. The warning is sent directly from the reader/display path and omits the option key. | Transfer the existing correction/warning queue and publication lifecycle. Preserve parser-only aliases and canonical visible values; add no selector choices. |

These are missing adapter behaviors, not native standalone capabilities that
require a different policy. No new product decision is needed to restore these
clear SM2 equivalents. They are adapter defects, not a requirement to make
Model2EmuEx's emulation behave like SM2. See the implementation below.

### A1 Reproduction

Use the real destination core with VF2, Automatic Initial NVRAM Setup Disabled,
NVRAM Settings Enabled and Difficulty Hard. Advance 600 frames in an isolated
headless ABI frontend, without changing options:

- The stored difficulty remains Normal (`1`).
- The unchanged reference engine recognizes the resulting layout as valid.
- Applying Hard to a copy returns Changed (`3`), proving that the desired value
  differs and that layout readiness no longer blocks application.
- Change the unrelated Pipeline option: Hard (`2`) is then applied and exactly
  one NVRAM Settings reset notification is sent.

This isolates the missing retry lifecycle from the NVRAM engine, field encoding
and initialization-template logic. The earlier M23 template-error correction
remains delivered; it did not cover this separate late-layout path.

Source: destination `src/libretro/libretro.c:694` and
`src/libretro/sm2_bridge.cpp:186`; SM2 `src/libretro/core.cpp:544`, `:574`,
`:1222` and `:1279`.

### A2 And A4 ABI Evidence

The current core was exercised with consuming option reads and isolated buffers:

| Probe | Observed Result |
| --- | --- |
| Unknown content name | Rejected; no core OSD detail. RetroArch may independently display a generic load-failure message. |
| Missing GL entry points | No OSD detail or shutdown; another callback still produces 735 audio frames. The test injects missing procedures, not physical GPU loss. |
| Audio callback accepts more frames than offered | Shutdown requested; no core OSD detail. Immediate rumble cleanup is absent from that source path; motor behavior was not tested. |
| Invalid Manx TT Linked Cabinets and ANRS values | Two deduplicated warnings; zero correction writes. Both frontend values remain `invalid`. |
| Same invalid values through current SM2 option readers | Safe one-cabinet/Disabled results plus two queued corrections and two warnings. |

Source: destination `src/libretro/libretro.c:172`, `:197`, `:265`, `:569`,
`src/libretro/net_bridge.cpp:18` and `src/libretro/sm2_bridge.cpp:44`;
SM2 `src/libretro/core.cpp:532`, `:607`, `:625`, `:670`, `:1148`,
and `src/libretro/core_options.h:48`, `:1243`.

### A3 Evidence Limit

The source call chain is conclusive: destination reset invokes GL deletion;
SM2 reset explicitly abandons the old handles first. Actual unannounced device
loss has not been reproduced in this analysis. The earlier M12/M24 tests call
context_destroy before context_reset; they demonstrate announced recreation
and do not qualify this different path. Do not invalidate those earlier tests
or claim physical device-loss coverage from them.

Source: destination `src/libretro/libretro.c:190`,
`port/m2/m2gl.c:386`, `src/libretro/sm2_overlay.cpp:22`,
`src/libretro/sm2_timing.cpp:97`; SM2 `src/libretro/core.cpp:670` and
`src/libretro/opengl_renderer.cpp:132`.

## Save RAM: Selected Native Standalone-Compatible Format

This is distinct from Save States, whose identity, full-buffer checksum,
preflight, rollback and current-option authority are already implemented.

| Property | SM2 | Destination |
| --- | --- | --- |
| Frontend Save RAM | 64-byte header + 16 KiB backup + 128-byte EEPROM = 16,576 bytes | Raw 64 KiB backup + 128-byte EEPROM = 65,664 bytes |
| Frontend validation | Magic, version, sizes, exact game identity and payload CRC16; Empty/Loaded/Invalid results | Direct memcpy; no file-container identity/version/checksum or import result |
| Native files | Reads game.nv and game.eeprom from the frontend save directory before initialization; valid frontend Save RAM takes precedence | Adapter does not import a separate native file. Standalone helper uses one combined backup/EEPROM file. |
| Initial templates | Valid frontend data, then available native data, then exact/explicit-compatible template policy | Template export during load, replaced by frontend raw SRAM before first emulated frame |

A probe replaced the exposed destination buffer with 65,664 bytes of `A5`.
After one callback every byte remained and no invalid-save warning was sent.
The current SM2 import routine accepts its own valid test container, rejects a
different game identity and rejects a payload checksum change. Its implementation
is already imported unchanged, but the destination wrapper does not use its
container import/export contract.

User decision — 2026-10-22: preserve the native standalone-compatible raw
format if it is an established solution in other Libretro cores. Primary-source
inspection confirms that condition:

- [Snes9x](https://github.com/libretro/snes9x/blob/master/libretro/libretro.cpp#L2148)
  returns `Memory.SRAM` directly for RETRO_MEMORY_SAVE_RAM, with the native SRAM
  size. It does not prepend an extra core-owned save-container header.
- [Genesis Plus GX](https://github.com/libretro/Genesis-Plus-GX/blob/master/libretro/libretro.c#L3707)
  returns `sram.sram` directly for RETRO_MEMORY_SAVE_RAM. Its raw SRAM size policy
  differs, but the relevant established practice is direct memory exposure.

The decision therefore selects the current 65,664-byte destination layout:
64 KiB backup RAM followed by 128-byte EEPROM, in the native byte order. The
standalone writes the same content to DAT files; RetroArch owns the frontend
filename/extension and locations. Frontend compression, if enabled, is a
frontend file-storage layer rather than a change to the exposed native buffer.
Do not add the SM2 header, a new container checksum, a migration path or a format
selector. No runtime change is needed to retain this existing behavior.

The SM2 standalone writes raw `.nv` and `.eeprom` files. Its `SM2SRAM` envelope
is an additional Libretro choice; TGPulse uses a similar custom envelope, while
Supermodel's current Libretro path preserves its native standalone block-file
container. These are destination-specific persistence choices rather than one
universal core format.

The all-A5 probe documents absence of an added container check; it is not a
failure of the selected raw-format contract. Game-native checksums/layout
validation and the A1 pending-override omission remain separate. The user
requires no general backward compatibility with other unpublished development
formats; standalone raw compatibility is now explicitly required. All native
memory is retained. Existing files and binaries are unchanged.

Automatic native-file fallback remains a separate feature, not implied by preserving binary compatibility: the native
formats and filenames differ from SM2's pair of files. Keep any future fallback
inside frontend-managed locations, read-only, after valid frontend Save RAM and
before templates. Never inspect or alter the pristine sibling's user data as
part of an automatic import.

Source: destination `src/libretro/libretro.c:221`, `:226`, `:621`, `:701`,
`port/m2/m2board.c:1021`; SM2 `src/libretro/save_ram.h:12`,
`src/libretro/save_ram.cpp:65`, `src/libretro/core.cpp:457`, `:1084`,
and `src/hw/model2.cpp:1706`. Framework F12 requests identity/format/integrity validation as a shared convention; the explicit user-approved raw persistence policy takes precedence over adding the SM2 container. Preserve the destination tail
and existing valid-save precedence in any eventual design.

## Already Aligned Or Previously Approved

- Extended message negotiation and legacy fallback already exist for network,
  template and Manx TT notices. A2 concerns consistent adoption/severity and
  fatal cleanup, not inventing another notification system.
- Initial-template failures already reject content and notify the frontend.
  Distinct unsupported/disabled, loaded and fatal outcomes remain intact.
- Valid ready-layout operator changes already commit and reset once; SRAM tail
  preservation and ANRS field handover remain independently tested.
- External linked states remain rejected; local LNK1/AUD1 guarded state
  recovery, GPU cache invalidation, audio clearing and current-option authority
  retain their prior evidence.
- Frontend remapping/scaling, 60 Hz timing, native selectors, native SCSP
  output, excluded Hide Shot Flash/cooperative play/keyboard controls and the
  rolling core name are unchanged.
- No absent Vulkan/software renderer or unsupported prototype feature is
  proposed as a requirement of this review.

## Reproduction And Change Boundary

The ignored audit directory contains `probe.py`, `reference-probe.cpp`,
`reference-result.jsonl`, `probe.log`, `result.json` and `sources.json`.
The reference probe includes live SM2 core_options.h and links unchanged
imported persistence/network objects, verified byte-for-byte against live SM2
sources. It does not run a separate emulator. The destination probe exercises
the existing binary without requesting an OS graphics context or opening
RetroArch. VF2's 600-frame run is the single targeted late-layout reproduction;
the remaining cases use zero or one frame. No catalog-wide launch campaign ran.

At the end of the original analysis, reviewed source/installed core SHA256 was
`234d6b9c01c88f953bcbf7f9da1a79687e8262878fdc7acacb5468c1b6452949`.
Only this review and roadmap/validation documentation were added or updated.
No implementation, installation, commit or push was performed during that analysis.

## Implementation And Verification — 2026-11-02

M25 fixes the four documented Libretro adapter defects. SM2 supplies the existing
frontend lifecycle solutions; CPU, emulated rendering, audio synthesis, ROM data,
selectors and defaults remain Model2EmuEx's approved implementation. This is not
an emulator-convergence or feature-parity activity. The pristine standalone
checkout and all ROM archives remain untouched.

- A1: retain pending overrides, retry before/after frames, cancel or refresh on
  option changes, and warn once after 600 unsuccessful frames. Effective NVRAM
  and topology changes coalesce into one reset. Explicit Restart and current
  option authority after state restoration use the same path. The existing
  native checksum/layout engine, ANRS handover and raw SRAM format are retained.
- A2: reuse the existing extended/legacy notification helper, with error priority
  2 and the original error reason. Fatal GPU/audio failures stop rumble, mark
  content failed and request shutdown; further callbacks do not advance it.
  Rejected loads and state preflight/rollback failures report errors without
  treating recoverable state rejection as fatal. Optional crosshair failure
  remains a warning.
- A3: context reset abandons obsolete renderer/overlay handles without GL calls,
  releases their CPU allocations and recreates resources. Announced destroy
  still deletes resources in the live context. The native `m2gl_abandon` helper
  changes resource ownership only, not emulated graphics or rendering algorithms.
- A4: invalid network readers queue canonical `-1` corrections and warnings
  containing the key. Publication moves the queues before frontend callbacks,
  preserving reentrancy, parser-only aliases and existing visible choices.

`scripts/check-frontend-contracts.py` reuses the existing ABI frontend and reads
ROMs from their storage directory without copying them. Its accepted receipt is
`audit/m25-contracts-accepted-20261102/result.json`: extended error severity and
legacy fallback, GPU initialization failure, invalid/stalled audio, deduplicated
reentrant network corrections, VF2 late-layout Hard application after native
initialization with exactly one reset, live Normal application, cancellation and
the unchanged 65,664-byte SRAM size all pass. The 600-frame timeout is implemented
and source-reviewed; this receipt exercises successful retry and cancellation,
not a forced permanently-unready layout.

The same fault/retry suite also passes with native Pipeline Enabled in
`audit/m25-contracts-pipeline-20261102/result.json`; the original accepted run
uses synchronous execution. No new selector is added for these checks.

`audit/m25-gl-accepted-20261102/run.log` records an actual replacement GL context
without the old destroy callback, with timing-overlay resources active. No old
texture/buffer/FBO/program deletion is issued during reset, visible pixels return,
and the existing lifecycle/SRAM/geometry checks pass. This is controlled context
replacement, not physical GPU device-loss qualification.

`audit/m25-state-vf2-20261102/result.json` retains four exact 12-frame same-process
continuations, cold/fresh-process loads, invalid-state rejection, announced
context recreation and NVRAM authority. The final binary also passes Deluxe
Manx TT's guarded audio/state continuation in
`audit/m25-state-manxtt-20261102/result.json`. Existing F05/F14 regressions for
Daytona, Sega Rally and Manx TT pass in `audit/m25-network-20261102/results.json`.
These target adapter lifecycle dependencies; they do not establish all-game
playability. Common/source/ABI, native audio scheduling, EEPROM and transport
checks pass; the original standalone target builds with the neutral helper.

Final core SHA256:
`a18df5d0773bbec0d8f7fd6033d18d6fa3eed6f8489ab2946e001cbe2276cd46`.
The existing user-authorized development installation is updated with its
previous binary retained and configuration/info hashes unchanged; receipt:
`audit/m25-local-install-20261102/deployment.json`. Physical controllers/motors,
actual device loss and wider frontend/platform qualification remain M14/M16.
No new options, Save RAM header/import path, commit or push.

`audit/m25-installed-retroarch-20261102/result.json` records the installed final
core in real RetroArch: 900 VF2 frames, clean exit, isolated configuration/saves,
and an inspected 3D attract screenshot. The existing core-specific GL override
works from a Vulkan base configuration. This is frontend rendering evidence,
not paid gameplay, audible output or physical-device qualification.
