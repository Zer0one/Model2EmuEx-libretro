# Save States

M12 implements native machine serialization and the Libretro Save State callbacks for the currently executable Model 2/2A boards. Reference: current SM2 `src/libretro/core.cpp`, native archive/serializer design, `Docs/SAVE_STATE_COMPATIBILITY_REVIEW_2026-10-09.md`, and Framework F12. The source revision remains `25d82be56f339c754cc566f771ca9ffb90b69289` plus the documented local port changes. No reference checkout was modified.

The opt-in M27 `SHARC=1` research build adds Model 2B SHARC snapshots following
the same complete-state contract as Model 2A, by the user's latest instruction
on 2026-11-03. Fighting Vipers passes cold save/load, repeated exact
continuations and loading before the first frame in a new process. Model 2/2A
retain their existing payload and capacity; VF2's state suite also passes in
the SHARC-enabled build. Default/release builds still exclude Model 2B.

The original Windows emulator does have Save States. Its recovered SHARC save
and restore callbacks already exist in `port/sharc/sharc_lifecycle.c`; they
archive the 0x2a4-byte CPU block and rebind the PC against the session's existing
decoded program. The user chose the port's Model 2A conventions after reviewing
this distinction: the adapter supplies the additional context needed for a
self-contained snapshot without replacing the native emulation. See the
original-path review and subsequent integration in SHARC_RECONSTRUCTION.md.

## Format And Ownership

| Property | Destination Contract |
| --- | --- |
| Format | Model2EmuEx format 1; magic `M2EXSTAT` |
| Libretro Capacity | Model 2/2A: 12 MiB (12,582,912 bytes), also returned without content. Enabled Model 2B and opt-in research Model 2C: 16 MiB (16,777,216 bytes), fixed while that content is loaded |
| Header | 128 bytes: version, used length, CRC32, native ABI/architecture marker, board type, saved cadence, game, hardware, loaded-ROM fingerprint and native frame counter |
| Integrity | CRC32 covers the header and entire fixed buffer except the checksum field; unused bytes are zero |
| Identity | Exact game, hardware, board type and loaded-ROM fingerprint; unsupported version/ABI, invalid lengths and corruption are rejected |
| Compatibility | This core's format only; no SM2, historical Windows emulator or preliminary local snapshot compatibility is advertised |
| Portability | Native scalar/structure representation, guarded by version/ABI and expected payload layout. Only macOS arm64 is qualified; cross-platform portability is not promised |
| Frontend Ownership | RetroArch owns slots, filenames, compression, screenshots, rewind and run-ahead configuration; no new Core Option or direct state-file write |

The capacity differs from SM2's 9 MiB because the native memory/device layouts differ. Save RAM stays a separate, stable 65,664-byte frontend buffer. Serialization is refused without content, for a null/undersized buffer, with an external CPU replacement, or with an external native network session configured. The adapter now supports external Linked Cabinets. Following SM2, both state operations are rejected with a notification whenever more than one cabinet is configured, including while waiting for peers. No peer/session data is serialized. Replacement CPU selection remains unexposed. M13 preserves the 12 MiB size and payload layout. All-set local loopback is serializable: an LNK1 header extension and ABI feature bit guard its protocol state. Previous zero-reserved-header states remain readable; old cores reject the new feature bit. No distributed-session data is serialized; see EXTERNAL_LINKED_CABINETS.md.

## Audio Subsystem Identity

SCSP states carry the loaded subsystem's CPU, DSP and RAM layout in the ABI header. The payload uses that board's serializer. For **Model2EmuEx** this includes the 512 KiB sound RAM and the standalone SCSP state. For **Model2Emu (ElSemi)** it includes the linear 1 MiB sound RAM, A68K, voice and DSP state. An incompatible state is rejected before mutation. See [Audio Subsystem Selection](VALIDATION.md#audio-subsystem-selection).

## Native Machine Coverage

Frontend-neutral APIs live beside their native subsystems and use `port/state.h`; they do not depend on Libretro, SDL or a filesystem.

- All board allocations, including observable slack, backup RAM, EEPROM serial state, ports/ADCs/gun counters, IRQs/timers, sound FIFO, local network registers, frame counters and dirty masks.
- i960 register/FPU/local-frame state, literals, interrupt/cycle state, selected region and predecode validity. Warm writable-code caches preserve raw opcodes and decoded displacement words: a changed extension word can differ from the cached displacement even when the opcode still matches. Host operand/function pointers are reconstructed; ROM caches are rebuilt against the validated ROM identity. Cold regions remain cold so restoration does not introduce the native predecode cycle quirk. Native board instruction hooks are restored.
- TGP block, upload/control registers, FIFOs, program/data/shared memories. ROM/memory links remain bound to this process's board allocations.
- Opt-in SHARC: original 0x2a4-byte CPU block through native save/restore callbacks, scheduler globals, pending bank events, FP control/status and board configuration; the original upload that generated the decoded cache and all 27 words per decoded record. Native decoder-unwritten bits and mutable scratch are retained. Structural decoded fields are checked by replaying the native decoder against the saved upload, not current program RAM. All addresses are virtual tokens; host callbacks and memory ownership are rebound locally. A `SHR1` subheader and ABI bit `0x20000000` distinguish this payload. Allocation happens before replacing the cache, and load never shrinks its storage, allowing rollback without another allocation.
- Sound RAM, 68000 value context, cycle debt, IRQs, native pending command queue, UART FIFO and sample banks. Musashi host timing-table/callback pointers remain those of the loading process.
- SCSP registers, slot/envelope/LFO history, DSP, ring buffer, timer/MIDI state and RNG; generated tables and callbacks remain local and LFO/ring pointers are rebound.
- Both MultiPCM chips' complete voice/envelope/LFO state, register cursor and banks; table pointers are rebound. YM3438 uses ymfm's own serializer, with host timers, resampler position and preceding samples. Archive scratch storage is retained between calls so the commit pass does not need another vector allocation.
- Persistent geometrizer RAM, matrices, coefficients, lighting and windows. Polygon output buffers, meshes, textures and GL objects are derived resources and are regenerated.

## Continuation And Restore Order

### Recovered SCSP DSP Payload — 2026-11-04

SCSP machines require backend-schema bit `0x02000000` plus exactly one backend
bit: `0x08000000` for recovered ElSemi or `0x04000000` for MAME. A backend marker
also precedes the SCSP payload. The active, content-load-latched backend is
authoritative: loading never changes it, and incompatible backend/schema bits
are rejected before mutation. Pre-selector states have no migration path.

The ElSemi sound payload contains the recovered DSP context, private 1 MiB RAM, compiled program snapshot
(including the captured successor), compiled length and fault diagnostics.
Decoded instructions are rebuilt from the saved compiled snapshot, not current
MPRO. Host executable addresses are never restored. The MAME payload retains
its live interpreter context; its DSP memory is the already-archived sound RAM.
Model 2's non-SCSP sound payload is unchanged. Capacities remain 12/16 MiB.

The native ElSemi `.sta` format omits the DSP context/private RAM, as documented
in AUDIO_RE_ANALYSIS.md. That native persistence omission does not supersede
this port's complete fresh-session snapshot contract.

Integrated macOS checks pass for VF2, Indy 500 and Top Skater: cold state,
four exact RAM/device/PCM/image continuations, context recreation, rejected
invalid states and exact fresh-process continuation. The largest of these
payloads is 9,519,948 bytes, within its 16 MiB capacity. Real RetroArch 1.22.2
also passes VF2 Save/Load, exact frame restoration, advancement and clean exit.
These are representative local checks, not whole-catalog or cross-platform
state compatibility. The selector follow-up qualifies both backend schemas on
VF2, including fresh processes, same-backend Reset, reload-only changes and
opposite-backend rejection. MAME also passes an actual RetroArch round-trip.
The added SCSP marker increases each ElSemi payload by four bytes relative to
the pre-selector measurements above. See VALIDATION.md for receipts.

### Restore Lifecycle

The adapter preserves SM2 gear/shift delay and held-input state, Desert Tank elevation, per-player gun cursor/lightgun history and source ownership. It also preserves native fallback control values, first-frame/video-readiness state and native/output sample remainders. Device assignments and Core Options remain owned by the current frontend.

1. Validate the header, full-buffer integrity and identity before changing machine state.
2. Quiesce the pipeline worker and validate the complete payload, including bounded native indices/queues and frontend values. Validation uses detached values/chip copies, not live-machine writes.
3. Take a rollback snapshot, then restore the machine, sound, geometry and frontend continuation. A failed commit restores that snapshot and returns failure.
4. Invalidate/recapture pipeline video and tile/texture/colour caches without GL calls. Native `m2gl_invalidate` also clears upload validity so equal old/new CPU version counters cannot retain stale GPU layers or palettes. Cold video startup remains cold. Clear stale frontend audio batches and timing diagnostics; preserve native scheduler fractions and native queued sound commands. Stop rumble and clear presentation activity.
5. On the next `retro_run`, refresh current presentation/audio/input options and reapply currently enabled NVRAM Settings. If they differ from the snapshot, commit them and perform one effective-change reset. Disabled preserves the restored operator choices. Automatic Initial NVRAM Setup is not rerun as a state-load replacement policy.

A state can be loaded under the other A/V Timing selection: the current session's cadence remains active; native scheduling is preserved and the presentation remainder is rebased. Serialization does not change Core Options. The normal frontend Save RAM buffer is restored with the snapshot and exported again during execution.

## Repeatable Verification

ROM-free native regression (also included in `bash scripts/check-sm2-common.sh`) verifies a warm writable i960 instruction cache whose displacement differs from backing RAM, including operand rebinding and identical cycle charge.

```sh
python3 scripts/check-savestates-macos.py \
  --rom /path/to/vf2.zip --frames 1800 --play \
  --output /path/to/new-save-state-audit
```

The GL harness checks cold save/load, four exact 12-frame continuations, native payload/PCM/image identity, reverse-order loads, context recreation, corrupt/truncated/header and well-checksummed invalid-payload rejection without mutation. VF2 also checks current NVRAM authority and one-reset behavior. A fresh harness process loads the snapshot and its 12-frame result must match the uninterrupted complete snapshot exactly. Native timing and Pipeline Disabled are selectable test parameters.

```sh
python3 scripts/test-retroarch-savestate.py \
  --retroarch /path/to/RetroArch.app/Contents/MacOS/RetroArch \
  --core /path/to/model2emuex_libretro.dylib \
  --system /path/to/test-system --rom /path/to/vf2.zip \
  --set-name vf2 --boot-wait 20 --output /path/to/new-frontend-audit
```

The real frontend runner adapts SM2's pause/slot/three-frame procedure and the `retroarch-savestate-test` skill's dynamic OSD-free crop. It uses the installed frontend's `FRAMEADVANCE` command and the optional `MODEL2EMUEX_STATE_TRACE=1` diagnostic to verify the actual machine frame on both paths, rather than assuming that simulated keys were delivered. The state header also records the native frame counter; a header/payload disagreement is rejected with rollback. Configuration, options, saves, states, info, runtime logs and playlists are isolated. It requires actual scene advancement, exact restored game-region pixels, advancement after restoration, confirmed save/load log messages and clean owned-process exit. Replay input is optional. Current receipts and artifact hashes are in VALIDATION.md.

The tests do not establish exhaustive all-game compatibility, physical controls/rumble, audible fidelity, actual GPU context loss, other OS support or synchronized external cabinets. Frontend rewind/run-ahead UI qualification is separate from the repeated ABI restore tests.


## M24 Optional Cabinet Audio Extension

Manx TT uses feature bit `0x40000000` and `AUD1` header bytes 6–15 alongside
`LNK1`; bytes 16–19 remain zero. The original payload remains at the same offset
and gains an appended hardware/mixer extension. The current sound-bank ROMs
and auxiliary-board presence/fingerprint are checked before any mutation.
Host I8251, AMS, SCSP return wire, M1 CPU/chips/UART and mixer fractions/queue
are preserved. Bank pointers are rebound before restoring CPU state, including
on rollback. Current options retain Resume authority. Legacy states reset the
new hardware and bind the original selected-set bank, then resume the current
policy. Old cores reject the new feature bit. The fixed 12 MiB capacity and
external-linked-session refusal are unchanged. See
[Manx TT Cabinet Audio](MANX_TT_CABINET_AUDIO.md) for exact header layout and
Twin/Deluxe same/fresh-process continuation evidence.

## M28 Research Model 2C Extension

The explicit `TGPX4=1` build adds a `TGX3` device archive and ABI bit
`0x10000000`. Model 2C uses the same 16 MiB capacity as SHARC; Model 2/2A stay
at 12 MiB. The recovered native 0x140-byte CPU save/restore callbacks remain in
use, with the additional CPU/driver/scheduler state, virtual x86 register and
FP context, decoded upload and complete 0x94-byte records required for loading
in a new session. All tokens are virtual, with local host memory/callbacks rebound.

Validation checks bounded PC/cursors, queues and bindings, and replays the
native decoder against the saved upload while preserving native unwritten
record bytes. Current program RAM may legitimately differ from the decoded
upload. Allocate before replacing the cache and never shrink it during load,
so rollback does not require a new allocation. The adapter retains its existing
whole-buffer integrity, preflight, rollback and current-option authority.

The ROM-free machine fixture passes exact reserialization after device
recreation, malformed/truncated rejection without mutation and the maximum
upload size. Over Rev passes the GL/ABI cold load, four exact replays, context
recreation and 12-frame exact continuation in a fresh process at frame 1,800.
No Windows state-file or cross-platform compatibility is implied. See
MODEL2C_ANALYSIS.md and VALIDATION.md for frontend evidence and remaining scope.

The TGX3 research schema includes the original Ski Super G motion-board phase
and countdown. The command latch and current response already belong to board
state. A pending command is consumed once per frame; idle frames do not consume
the countdown. TGX1 snapshots from the preceding local research build are
rejected rather than migrated; no published M2C state compatibility is implied.
Ski Super G now passes same/fresh-process GL/ABI continuation and exact real
RetroArch visual restoration, including clean exit.

M2C geometry additionally archives the twelve-word Top Skater alternate matrix
after the unchanged shared geometry prefix. It survives lists that reuse the
previous matrix and fresh-session loading. This field is present only for an
actual M2C machine, so M2/2A/2B payloads remain unchanged even in a combined
research build. The dual-matrix enable flag is restored with the native driver
configuration and copied into each renderer-pipeline frame; no mutable CPU
binding pointer is shared with the render thread.

The current private TGX3 schema also retains the native Dynamite Cop protection
response buffer, read index, selector and toggle. The original reset hook only
installs memory handlers, so machine reset does not clear these globals. The
synthetic i960 fixture checks reset persistence and continuation after device
recreation. Earlier private TGX2 research snapshots are not accepted; this does
not alter Model 2/2A/2B payloads or the raw standalone-compatible Save RAM format.


## Shared Sound RAM Layout — 2026-11-04

The approved SCSP-board CPU RAM layout is the original linear 1 MiB allocation
in ElSemi/A68K word-swapped byte order. The complete allocation is archived.
Header bits 0x00800000 and 0x00400000 identify capacity/map and byte order;
both are required for an SCSP-board state and absent for a Model 1 board.
The initial 0x7ffff voice sample window was superseded by the key-on map below. Original DSP private RAM
and raw standalone-compatible Save RAM are unaffected.

A mismatched map or byte order is rejected before payload mutation, with an
explicit frontend diagnostic. No migration or user-save rewriting is performed.
Feature bits are statically checked against the base ABI. This is an internal
port snapshot contract, not compatibility with original Windows state files.


## Native SCSP Control Snapshot — 2026-11-04

SCSP-board headers require feature bit 0x00200000. The SCP2 schema (0x32504353) introduced snapshots of the 128-byte FIFO, read/write indexes,
independent byte counter, pending IRQ level, full fractional timer counters
and expired flags. Preflight validates indexes, level and boolean flags before
mutating the live board. The previous private schema is rejected explicitly,
without migration. Model 1 states and native raw Save RAM remain unaffected.

A synthetic 68000 interrupt handler proves exact cold continuation with queued
commands and an asserted IRQ. VF2/original-DSP and Sega Rally/MAME-DSP pass
full-core same/fresh-process GL/ABI continuation and invalid-header rejection.

## Voice Key-On Snapshot — 2026-11-12

SCSP boards require header feature 0x00100000. Each slot archives its key-on sample base independently of
the writable start registers. Its signed previous PCM sample now participates
in synthesis. SCP3 snapshots cannot reconstruct this history for active voices
and fail payload preflight. The payload includes the first escaped sample
address. Cold continuation covers a voice whose program edited the start
registers after key-on on both DSP backends. Model 1 retains its own layout.

The pitch implementation introduced marker SCP5 (0x35504353). The archived step
now includes native high-octave wrap and Windows frequency-table rounding.
SCP4 stored a step computed by the previous pitch implementation and fails
preflight. Cold continuation covers a live pitch update before saving,
in all four loop modes on both DSPs.

SCP6 (0x36504353) stores envelope volume and rates with eight fractional
bits. SCP5 contains values at a different scale and fails preflight.
Fresh-process Sega Rally continuation and cold board snapshots with a
live attack-rate update passed on the current layout.

SCP7 (0x37504353) additionally saves the 128-byte ElSemi CPU MIDI output
ring, its seven-bit write cursor and separate wrapping byte count. A cursor
outside the ring or an earlier marker fails preflight. Fresh-board tests
write 259 entries, restore the ring on both DSPs and verify the next
high-lane store enqueues the retained low byte. The optional serial return
wire keeps its independent Manx TT state.

SCP8 (0x38504353) retains the live 32-bit DSP RAM address exposed to the
sound CPU. For the original DSP it also saves the independent address captured
at the last Start. The pending register can contain a partially written value.
The compiled address must belong to a mapped audio allocation. A new sound
board restores both values and the compiled program before rendering. The
MAME DSP keeps its own memory path. SCP8 also saves the live voice base,
an explicit voice-fault flag (address zero can fault), and private DSP RAM on
either backend because PCM voices can read it. SCP7 fails preflight. The frontend buffer
capacities and standalone Save RAM format are unchanged.


SCP9 (0x39504353) stores the complete CPU-writable ring cursor and master
register, cached left/right voice gains, and each LFO's last table selection.
A disabled LFO can retain its previous binding. On load the core rebinds
tables to the current process. A pending cursor outside the first 64 cells
is valid until the next mixer write. Fresh-board tests also cover the next
write into a DSP coefficient. SCP8 fails preflight for the reconstructed chip.

### Reconstructed SCSP Sound CPU

A68K-enabled builds record the selected CPU in header bit `0x00080000`.
A68K stores the native registers, dispatcher scalars, fetch-page index and
sub-scanline clock remainder. Callbacks, ROM/RAM page maps and the bound
IRQ register belong to the receiving board. The selected DSP has its own
header check. A CPU mismatch rejects the archive before machine mutation.
The 420-frame Sega Rally native-timing test restores both CPU selections in
fresh processes and rejects an actual archive from the other backend.

### Optional Digital Sound Board

The ElSemi profile saves the board type, pending command, descriptor, segment and ROM offsets, source phase and increment, interpolation history, decoded PCM, the two synthesis histories and their cursors. The archive also records whether a decoder call has bound its output buffers. Cold load binds ROMs from the loaded set and recreates the cosine table. A DSB1 block is present only on the fitted ElSemi boards. A state made before this hardware was integrated lacks the block and is rejected for these boards.

### Primary Model 1 Audio

The A68K feature bit distinguishes the reconstructed primary sound board from the standalone Musashi board. Its payload carries all 64 KiB of sound RAM, the A68K context and fetch-page binding, the command FIFO and cursors, the mutable tails of both MultiPCM chips, FM register/operator/timer state, and partially rendered FM samples with their write cursor. The M1A1 payload carries 3,264 bytes per MultiPCM chip, including the slot-selector alias into the last 112 bytes of decoded descriptors. The loaded ROM reconstructs the earlier descriptors and the sound board rebinds its host pointers. The Manx TT auxiliary board has its own cabinet payload. See [primary Model 1 validation](VALIDATION.md#primary-model-1-audio-board).

### Lua And Original Renderer Options

Load State restores the emulated machine and leaves the current Lua interpreter live. Globals, closures, loaded modules, user files and overlay handles follow that session. A new content load executes the main script in a fresh interpreter. Restore tests using scripts that modify ROM must supply the same patched program. A final optional SHD1 payload stores the last luma row and base colour used by linked-face lighting. Earlier snapshots initialize these four bytes to zero. Texture objects regenerate from the restored memory and active frontend options.

## M33 Protected Boards And Air Walkers I/O — 2026-11-15

Protected native 2A/2B boards append response bytes, cursor/selector/toggle and
fault context under ABI bit `0x00040000`. Air Walkers appends its I/O latches,
directions/mode and player-start/DIP inputs under bit `0x00010000`. These bits
are required only by their applicable boards; incompatible payloads are rejected
explicitly. Cache patches are reinstalled after native cache restoration.
No raw Save RAM format change or state migration is implied. Nine new-set
same-process continuations and four fresh-process continuations pass; see
VALIDATION.md and the compact M33 results.
