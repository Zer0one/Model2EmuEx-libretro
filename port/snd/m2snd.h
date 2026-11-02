/*
 * Model 2 sound boards, driven by the i960's sound port:
 *  - Model 2 (board type 0): the Model 1 sound board, a 68000 at 10 MHz with
 *    two MultiPCMs and a YM3438; commands arrive through a UART (IRQ 2).
 *  - Model 2A (type 1): a 68000 at 11.29 MHz with an SCSP; commands arrive
 *    through the SCSP's MIDI input.
 * Memory maps as the original (0x4ccbe0), I/O details as MAME's
 * segam1audio.cpp and model2.cpp. The 68000 is Musashi (the original's
 * A68K is x86 assembly). Output: 44.1 kHz stereo.
 *
 * Several boards: Musashi is one global CPU, so each board keeps its own
 * saved context and the calls below switch to it. Calls for different
 * boards must not run at the same time (render them from one thread).
 *
 * Threads: m2snd_command may run on one thread (the emulation) while
 * m2snd_render runs on another (the audio callback); commands go through a
 * lock-free queue and reach the board at the next slice (one sample for SCSP,
 * up to 16 for the Model 1 sound board). Every
 * other call needs the render thread stopped (SDL_LockAudioDevice).
 */
#ifndef M2SND_H
#define M2SND_H

#include <stdint.h>
#include "../state.h"

#ifdef __cplusplus
extern "C" {
#endif

struct m2_board;
typedef struct m2_snd m2_snd;

#define M2SND_RATE 44100

m2_snd *m2snd_create(const struct m2_board *b);
void    m2snd_destroy(m2_snd *s);
void    m2snd_reset(m2_snd *s);
/* a byte from the i960 (board hook sound_command); never blocks */
void    m2snd_command(m2_snd *s, uint8_t cmd);
/* delivers queued commands and runs the sound board for `n` samples,
   writing interleaved stereo */
void    m2snd_render(m2_snd *s, int16_t *out, int n);
/* Relative output gains, 0..100 percent; synthesis always continues.
   Defaults are 100 and preserve the native mix; reset preserves these gains. */
void    m2snd_set_gains(m2_snd *s, unsigned scsp_gain, unsigned pcm1_gain,
                       unsigned pcm2_gain, unsigned fm_gain);
/* debugging: one-line state summary */
void    m2snd_debug(m2_snd *s, char *buf, int size);

void m2snd_state_archive(m2_snd *s, m2_state *a);
#ifdef M2_CABINET_AUDIO
/* Optional cabinet hardware. Existing standalone scheduling is unchanged. */
void m2snd_bind_roms(m2_snd *s,const uint8_t *program,uint32_t program_size,
                   const uint8_t *samples,uint32_t samples_size);
void m2snd_reset_midi(m2_snd *s);
void m2snd_set_roms(m2_snd *s,const uint8_t *program,uint32_t program_size,
                   const uint8_t *samples,uint32_t samples_size);
m2_snd *m2snd_create_aux(const uint8_t *program,uint32_t program_size,
                       const uint8_t *samples,uint32_t samples_size);
/* Advance the auxiliary M1 by 25 MHz host cycles; output has room for 8 frames.
   Caller uses bounded steps <= 4000 cycles, as the source sound scheduler. */
unsigned m2snd_run_aux(m2_snd *s,unsigned host_cycles,int16_t *output);
void m2snd_aux_state_archive(m2_snd *s,m2_state *a);
void m2snd_set_reply(m2_snd *s,void (*reply)(void *,uint8_t),void *user);
void m2snd_midi_state_archive(m2_snd *s,m2_state *a);
#endif

#ifdef __cplusplus
}
#endif

#endif
