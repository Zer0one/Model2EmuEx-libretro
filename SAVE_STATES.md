# Save States

M12 implements native machine serialization and the Libretro Save State callbacks for the currently executable Model 2/2A boards. Reference: current SM2 `src/libretro/core.cpp`, native archive/serializer design, `Docs/SAVE_STATE_COMPATIBILITY_REVIEW_2026-10-09.md`, and Framework F12. The source revision remains `25d82be56f339c754cc566f771ca9ffb90b69289` plus the documented local port changes. No reference checkout was modified.

## Format And Ownership

| Property | Destination Contract |
| --- | --- |
| Format | Model2EmuEx format 1; magic `M2EXSTAT` |
| Libretro Capacity | Fixed 12 MiB (12,582,912 bytes), available before loading content |
| Header | 128 bytes: version, used length, CRC32, native ABI/architecture marker, board type, saved cadence, game, hardware, loaded-ROM fingerprint and native frame counter |
| Integrity | CRC32 covers the header and entire fixed buffer except the checksum field; unused bytes are zero |
| Identity | Exact game, hardware, board type and loaded-ROM fingerprint; unsupported version/ABI, invalid lengths and corruption are rejected |
| Compatibility | This core's format only; no SM2, historical Windows emulator or preliminary local snapshot compatibility is advertised |
| Portability | Native scalar/structure representation, guarded by version/ABI and expected payload layout. Only macOS arm64 is qualified; cross-platform portability is not promised |
| Frontend Ownership | RetroArch owns slots, filenames, compression, screenshots, rewind and run-ahead configuration; no new Core Option or direct state-file write |

The capacity differs from SM2's 9 MiB because the native memory/device layouts differ. Save RAM stays a separate, stable 65,664-byte frontend buffer. Serialization is refused without content, for a null/undersized buffer, with an external CPU replacement, or with an external native network session configured. The adapter now supports external Linked Cabinets. Following SM2, both state operations are rejected with a notification whenever more than one cabinet is configured, including while waiting for peers. No peer/session data is serialized. Replacement CPU selection remains unexposed. M13 preserves the 12 MiB size and payload layout. All-set local loopback is serializable: an LNK1 header extension and ABI feature bit guard its protocol state. Previous zero-reserved-header states remain readable; old cores reject the new feature bit. No distributed-session data is serialized; see EXTERNAL_LINKED_CABINETS.md.

## Native Machine Coverage

Frontend-neutral APIs live beside their native subsystems and use `port/state.h`; they do not depend on Libretro, SDL or a filesystem.

- All board allocations, including observable slack, backup RAM, EEPROM serial state, ports/ADCs/gun counters, IRQs/timers, sound FIFO, local network registers, frame counters and dirty masks.
- i960 register/FPU/local-frame state, literals, interrupt/cycle state, selected region and predecode validity. Warm writable-code caches preserve raw opcodes and decoded displacement words: a changed extension word can differ from the cached displacement even when the opcode still matches. Host operand/function pointers are reconstructed; ROM caches are rebuilt against the validated ROM identity. Cold regions remain cold so restoration does not introduce the native predecode cycle quirk. Native board instruction hooks are restored.
- TGP block, upload/control registers, FIFOs, program/data/shared memories. ROM/memory links remain bound to this process's board allocations.
- Sound RAM, 68000 value context, cycle debt, IRQs, native pending command queue, UART FIFO and sample banks. Musashi host timing-table/callback pointers remain those of the loading process.
- SCSP registers, slot/envelope/LFO history, DSP, ring buffer, timer/MIDI state and RNG; generated tables and callbacks remain local and LFO/ring pointers are rebound.
- Both MultiPCM chips' complete voice/envelope/LFO state, register cursor and banks; table pointers are rebound. YM3438 uses ymfm's own serializer, with host timers, resampler position and preceding samples. Archive scratch storage is retained between calls so the commit pass does not need another vector allocation.
- Persistent geometrizer RAM, matrices, coefficients, lighting and windows. Polygon output buffers, meshes, textures and GL objects are derived resources and are regenerated.

## Continuation And Restore Order

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
  --core /path/to/model2emuex_dev_libretro.dylib \
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
