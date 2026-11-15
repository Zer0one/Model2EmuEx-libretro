# Sound boards: what the port does, and how it differs from the original

Source: Sega Model 2 Emulator 1.1a, `EMULATOR.EXE`:
- sound CPU memory maps at 0x4ccbe0 (both boards)
- UART at 0x4c6a40/0x4c82d0
- MultiPCM at 0x4b01b0–0x4b0cd0, YM2612/3438 at 0x4b0b30–0x4b2580
- SCSP at 0x4ab000–0x4b0000, with its DSP recompiler at 0x4aa040

The original's 68000 core is A68K, x86 assembly (its init at 0x462ae0
unpacks a compressed opcode table). The upstream portable implementation chose
**Musashi** (MIT) instead of reconstructing that assembly and its native ABI.
This is an implementation choice, not proof that A68K cannot be recovered for
ARM. The current dispatch/SCSP recovery boundaries and qualification limits are
recorded in [Original Audio Reconstruction Boundaries](../../AUDIO_RE_ANALYSIS.md).
The table below describes the inherited board. Its wiring was informed by
the original. The FIFO, bank and timing rows identify observable differences.
For the ElSemi subsystem, each retained upstream path requires original-code
evidence. The current qualification and remaining work are in
[the audio roadmap](../../ROADMAP.md#scsp-sound-board-reconstruction).

| Part | Port | Notes |
|------|------|-------|
| 68000 | Musashi 4.60, `m68kconf.h` with `M68K_EMULATE_INT_ACK` on | Interrupt lines are levels, held until the device drops them. Musashi's default clears the level when an interrupt is taken, which starves the UART: Daytona's driver reads one byte per IRQ 2. |
| MultiPCM | `multipcm.c`, from MAME gew.cpp + multipcm.cpp | Runs at 44.1 kHz, not the chip's 44.64 kHz: the envelope tables already assume 44.1 kHz, and pitch uses the output rate. Writes to the unused slot numbers (7, 15, 23, 31) are dropped; MAME would index slot −1. |
| YM3438 | `ym3438.cpp` via ymfm (BSD-3) | The original has its own YM2612 core. Daytona's driver takes its music tempo from the timer overflow flags, so without the timers it never keys a note on. Rendered at 55.5 kHz and resampled to 44.1 kHz; mixed at MAME's 0.30. |
| SCSP + DSP | `scsp.c`, from MAME scsp.cpp/scspdsp.cpp | Timers count in output samples (ElSemi's earlier SCSP timer code) instead of MAME's scheduler. MIDI in is a byte FIFO; MIDI out is dropped (the i960 never reads it, as in the original). EXTS inputs are silent. Ordinary CPU global-register writes store directly as in ElSemi; writing MIDI-in does not pop a byte. Chip-internal DMA register access is separate. |

## Board wiring

| # | Where | Original | Port |
|---|-------|----------|------|
| 1 | Model 2 UART 0xc20001 | Pops the i960's command FIFO; clears the 68000's pending interrupt when the FIFO empties. Status reads (0xc20003) return 0. | Same, with IRQ 2 asserted while the FIFO holds data. The driver's handler treats a 0xff byte as "reset": it reloads its stack and restarts at 0x300. |
| 2 | Model 2 MultiPCM banks 0xc50001/0xc70001 | `value & 7` | `value & 3`, as MAME; bank n maps sample ROM n MB to chip addresses 0x100000–0x1fffff. Each chip sees its own 4 MB of region 6. |
| 3 | command FIFO full | The i960 write handler overwrites unread entries. | A full FIFO drops the new byte. |
| 4 | Model 2A 0x400000 (sample banks) | Ignored. | Ignored: the samples are mapped linearly at 0x800000, which equals MAME's default banks. |
| 5 | ROM byte order | Regions 5 and 6 are stored as A68K wants them, each 16-bit word little-endian (checked: Daytona's vectors only make sense that way). | The 68000 reads ROM through that swap. SCSP-board RAM now also uses original word-swapped storage by explicit user decision; Musashi and SCSP accessors preserve their guest-visible byte order. Model 1 RAM retains its inherited big-endian representation. MultiPCM reads region 6 byte for byte. |
| 6 | timing | Sound runs in its own thread, synced to the frame. | This independent port uses one-sample slices for SCSP, correcting Sega Rally streaming truncation caused by stale sample-address reads; see ../../AUDIO_SRALLYC_DIAGNOSTIC.md. The Model 1 board retains 16-sample slices. In each slice the 68000 runs its share of cycles, then the chips render. The i960's command bytes go through a lock-free queue and reach the sound CPU at the start of the next slice. `m2emu` renders from SDL's audio callback, so the sound board runs on its own core at the audio device's pace, not synced to frames: when the emulation runs slow, music and effects keep their tempo, and commands arrive up to one audio buffer (1024 samples, 23 ms) late. On fast forward the sound stays at normal speed; if the queue (256 bytes) fills, new commands are dropped. `m2run` renders after each frame, on one thread. The sound board never answers the i960 (the board fakes the status reads), so the i960 can't tell the difference. |

Sega Rally's long warning screen is not caused by sound: it lasts just as long with the sound board running.


## Optional Manx TT Hardware In The Independent Core

The table above describes the original standalone wiring. With the root
Makefile's `M2_CABINET_AUDIO`, Manx TT uses the unchanged SM2 I8251 for real
host/auxiliary UARTs, returns SCSP/M1 serial bytes and connects the additional
Model 1 board for Deluxe. Its clocks, mixer and AMS handshake follow SM2.
The copied I8251 retains its GPL-3.0-or-later header and existing SM2
LICENSE/NOTICE copies; adapted mixer/policy provenance is recorded separately.
Other sets and the original `port/Makefile` retain their prior sound path.
See ../../MANX_TT_CABINET_AUDIO.md for source, lifecycle, state and evidence.

## DSP Reconstruction Policy — 2026-11-04

The recovered `scsp_dsp_original.c` now supplies the default SCSP DSP path.
It matches 1,439 original-code cases at O0/O2/UBSan; representative macOS
full-core state/PCM/frontend qualification now passes
(VF2, Indy 500, Top Skater; real RetroArch VF2). Preserve native
quirks, including memory conversion/stores, scratch persistence and compiler
lookahead. Differences from the MAME-derived path are not automatically errors
in ElSemi. Original-code corrections require separate evidence and discussion.
See [Original Audio Reconstruction Boundaries](../../AUDIO_RE_ANALYSIS.md).

The module owns the native private 1 MiB DSP RAM, preserves cached programs and
uses native mixer boundaries and the BFE start event. For escaped RAM accesses,
the user approved an explicit address diagnostic and content stop. Game
reachability is unknown. No memory wrapping, invented value or MAME fallback.

The Audio Subsystem option selects the primary sound board at content load. Model2EmuEx uses the standalone Musashi board, with its own SCSP or Model 1 FM and MultiPCM path. Model2Emu (ElSemi) uses A68K with the reconstructed SCSP and DSP or the reconstructed primary Model 1 board. With the digital board fitted, the i960 command goes to both SCSP and DSB, and DSB mixes after SCSP. A warm machine reset preserves the active digital track and any partial command. The Manx TT auxiliary cabinet has a separate clock. See [Audio Subsystem Selection](../../ROADMAP.md#audio-subsystem-selection).

Original Save State disassembly distinguishes the 64 KiB `M2SCSP` archive entry
from the 1 MiB sound RAM allocation and the separate private DSP allocation.
The traced native archive does not save the DSP context/private RAM/generated
program. The port retains its complete-snapshot contract; reproducing this
native persistence omission is not part of preserving DSP execution behavior.


## Original SCSP-Board RAM Layout — 2026-11-04

Native allocation 004cdaff and DATA-map installer 004cd136 establish a linear
1 MiB CPU window. The inherited 512 KiB mirror was replaced by explicit user
decision. The user then selected original word-swapped storage, avoiding a
storage conversion in the reconstructed A68K path. Musashi byte/word/long
accessors, reset vectors and SCSP sample/DMA helpers are adapted; MAME DSP
accesses already use those SCSP helpers. The independent 0x7ffff chip sample
mask, original DSP private RAM and Model 1 board RAM remain unchanged.
Save States retain the entire allocation and reject old map/storage identities.
See VALIDATION.md for bus/DMA, baseline PCM and complete-core state evidence.


## CPU Read Callback Recovery — First Group

By user decision, both 68000 backends use recovered ElSemi SCSP CPU reads.
Byte reads from ring/DSP return zero, DSP word reads return zero, and long
reads return all ones without two word-read side effects. Odd slot words use
native byte positions, including the trailing active byte. Internal DMA/DSP
readback remains independent. The ordinary global CPU range and MIDI/timer/IRQ control paths are recovered
as described below. Raw global-object aliases and remaining write/DMA semantics
remain explicitly tracked in AUDIO_RE_ANALYSIS.md.


## Native MIDI, Timer And IRQ Control — 2026-11-04

The native MIDI queue holds 128 bytes, with independent wrapping occupancy
bookkeeping. Reads from an empty queue still return the stale indexed byte and
decrement that byte counter. Neither enqueue nor CPU dequeue changes IRQ
immediately. MIDI takes priority independently of SCIEB; zero pending bits
with an empty queue retain the previous request. CPU acknowledgement clears
the accepted request and recomputes before the handler consumes MIDI.

Timer register writes preserve the fractional counter byte and clear the
expired flag. Expiration is the native exact counter test, not saturation;
SCIRE re-latches expired timers before checking IRQ. The slot monitor reads
the live cursor's top byte, without the inherited envelope/status synthesis.
CPU global writes do not read/pop MIDI first and preserve raw SCIPD stores.
Original addresses and 999-case comparisons are recorded in VALIDATION.md.
This does not qualify warm-reset retention, all aliases, DMA IRQ or full
A68K scheduling. No native quirk is presented as a hardware-correctness fix.


## Original CPU DMA Register Stores — 2026-11-04

By explicit user decision, both CPU backends retain ElSemi's writes to global
0x12–0x17 without performing a DMA transfer. `UpdateCpuReg` skips those update
handlers after storing their values; the start bit remains set and no DMA IRQ
is generated. This follows sparse-table entry 2 -> RET at 004af26c.
The chip-internal `w16`/`UpdateReg` path is independent and unchanged. This
choice is shared by original/MAME DSP backends and introduces no selector.
The research A68K observer also preserves the native EAX selector and flags.
