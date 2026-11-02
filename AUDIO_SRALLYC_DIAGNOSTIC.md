# Sega Rally Audio — Quick Diagnostic

Date: 2026-10-21. Status: premature SCSP stream termination reproduced and corrected locally. User listening confirmation remains pending.

## Initial Offline Baseline

Captured 3,600 `srallyc` machine frames with no input (warning screen followed by attract mode). The Libretro core ran headlessly with native audio callbacks, at both Native and 60 Hz timing. Same-revision pristine standalone `m2run` used the exact initial NVRAM exported by the core. These runs bypass actual frontend/device playback and do not constitute listening tests.

| Path | Delivered Stereo Frames | Duration | PCM SHA-256 |
| --- | --- | --- | --- |
| Core Native | 2,737,241 | 62.068957 s | `9611c8f99116b6aad95ebf5722de0284f6b0d180fb11b5fdd63828ae4610b942` |
| Pristine Standalone Native | 2,737,241 | 62.068957 s | `9611c8f99116b6aad95ebf5722de0284f6b0d180fb11b5fdd63828ae4610b942` |
| Core 60 Hz | 2,646,000 | 60 s | `6bd11dc6f7356549a947d31ba45a88fae5f0d99fd10ee874b562c00cc595ae41` |

The Native streams are byte-identical; generated/delivered sample counts match the selected cadence. No integer full-scale clipping occurs (absolute peaks 1,246 Native and 1,237 at 60 Hz). This rules out missing samples in this bounded offline adapter path and confirms parity with standalone synthesis. It does not distinguish native note/envelope truncation from a real playback underrun reported by the user.

## Source Comparison And Isolated Probe

Model2EmuEx runs the 68000 before SCSP output in 16-sample blocks. Current SM2 `src/hw/model2_sound.cpp` instead tracks sample phase against 256 sound-CPU cycles, carries instruction overshoot, advances the chip sample-by-sample, and charges sound-RAM/SCSP bus waits. Its reference evidence is `Docs/UPSTREAM_SOUND_TIMING_PACKAGE_2026-10-08.md`. These are concrete timing differences worth investigating, not a demonstrated cause of this report.

An isolated build replaced only `SLICE 16` with `SLICE 1` in an audit copy of `m2snd.c`, linked against the existing core objects. It was not installed and source/build/installed production artifacts were not replaced. At 60 Hz it still delivers 2,646,000 samples and no full-scale clipping. The waveform changes, but this alone is not a quality improvement: exact-zero 10 ms blocks after 20 s increase from 49 to 113, and RMS changes from 112.12 to 142.34. Natural source silence cannot be classified as an underrun from these counts. A one-line slice reduction is not an accepted correction and does not implement SM2's full scheduler.

## Evidence And Next Boundary

Ignored evidence: `port/build-libretro-macos/audit/srallyc-audio-quick-20261021/`, including full WAVs, capture/probe code, logs and `analysis.json`.

The initial core and installed hash was `742192cec335c3e02026280378f4313066dca26eb8775bcdef39b893a8cfd848`. Pristine reference HEAD remains `25d82be56f339c754cc566f771ca9ffb90b69289`.

## Reproduction And Cause

A second 6,000-frame probe includes scripted credit/Start input. Paid gameplay was not visually qualified; these results cover the initial attract sequence and a recognized credit sound. The trace records MIDI delivery, slot starts, stop causes, loop ends and playback cursors. All 43 command bytes are consumed without FIFO overflow. A separate probe replays those exact bytes at the same sound-sample timestamps into the current SM2-Emu sound board, with output filtering and balance disabled. Its source is compiled against the current reference headers/libraries; an audit copy of SCSP adds traces without modifying SM2's checkout.

Model2EmuEx lets the sound CPU run 16 samples before advancing SCSP. Sega Rally streams/decompresses data into sound RAM and polls SCSP's current-address monitor before changing loop/end registers. With the coarse schedule, the CPU can disable looping and reduce the end address while the stale playback cursor is already beyond the new end. The next SCSP update stops immediately, losing the remaining buffered tail. For example, slot 0 stops at cursor 4,746 with a final end of 1,410; the reference and corrected path wrap and finish at 1,409.

| Stream Event | Previous Duration | Corrected Duration | SM2 Reference Duration |
| --- | --- | --- | --- |
| Slot 0, RAM `0x10000`, first start | 215.26 ms | 435.37 ms | 435.37 ms |
| Slot 2, RAM `0x14000`, first start | 674.26 ms | 2,742.77 ms | 2,742.77 ms |
| Slot 8, RAM `0x20000`, first start | 885.40 ms | 2,742.77 ms | 2,742.77 ms |
| Credit-associated stream, RAM `0x32000` | 86.85 ms | 458.32 ms | 458.32 ms |

Durations are measured from actual slot start to inactive, not inferred from total WAV length. The credit event follows host command `ae 21 21`. This demonstrates real premature termination independently of audio-device playback. The first three streams have not been assigned subjective voice/effect labels.

## Correction And Regression Checks

`port/snd/m2snd.c` now advances SCSP in one-sample slices. The Model 1 MultiPCM/YM3438 board retains its native 16-sample slices. Clocks, gain and filtering are unchanged. This targeted correction also applies to the standalone built in this independent repository; the pristine sibling remains untouched. No new Core Option is needed for the scheduling defect.

`make check-sound` runs a ROM-free synthetic 68000/SCSP program which keys a tone after a sample boundary. Its PCM must be invariant across callback sizes 1, 7, 16, 256, 735, 761 and 2,048. The previous scheduler fails at size 7; the corrected scheduler passes all sizes. This tests an externally meaningful scheduling property rather than the chosen slice constant.

- Native macOS core and adapted standalone/headless builds pass.
- Corrected 3,600-frame, no-input Native core and adapted standalone deliver identical PCM: 2,737,241 stereo frames, SHA-256 `e76f3bed3a23ca4a8fefdfa7956227867ef4cc587d81a966d087417d71b46511`.
- Public Libretro Save State restore while SCSP is active reproduces the next 12 frames' PCM exactly.
- The trace of the corrected production code restores all four durations above to the SM2 reference durations.
- Installed RetroArch test core was replaced atomically after backing up the previous binary. Source/installed SHA-256: `ed28974be3fc383e2b3784fd201ae6ad838e7b8adf8df76a049f31f2d091d943`. Receipt: `deployment.json`; backup: `installed-before-scsp-fix.dylib`, in the ignored evidence directory.

## Limits And Follow-Up

This is a bounded stream-termination correction, not wholesale adoption of SM2's sound scheduler. Sound-RAM/SCSP bus waits and other native chip differences remain. Sequencer timing still differs: one repeated sample is spaced approximately 1.24 s before correction, 0.96 s after, and 0.99 s in SM2. One-sample scheduling fixes the reproduced stream ends but does not establish complete musical or all-game accuracy.

Historical pristine PCM parity describes the pre-fix baseline. Active SCSP PCM is now intentionally different; the strict pristine comparison script may therefore flag PCM differences. It must not be treated as an expected all-green acceptance test for this correction. The adapted standalone remains the paired frontend-neutral PCM reference, and the pristine source/old artifact retain the before baseline.

These checks are offline synthesis/delivery tests. No current real-frontend playback, subjective listening, navigator callout, engine/tire or physical-device qualification is claimed. User listening confirmation of the reported symptom remains pending. No commit or push.

## User Listening Follow-Up

On 2026-10-21 the user confirms “Voce navigatore ok” with the installed SCSP correction. This adds subjective confirmation for the reported navigator voice; it does not qualify every sound source or complete musical timing. The subsequent EEPROM correction produces a newer core artifact recorded in NVRAM_SAVESTATE_DIAGNOSTIC.md.
