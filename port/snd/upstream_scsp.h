/* Model2EmuEx standalone SCSP, with the port archive and optional MIDI return. */
/*
 * Yamaha YMF292-F "SCSP": 32 slots of PCM/FM plus the effects DSP. C port of
 * MAME's scsp.cpp and scspdsp.cpp (BSD-3-Clause; SCSP emulation by ElSemi,
 * the Model 2 Emulator's author, with R. Belmont and kingshriek), with the
 * MAME scheduler replaced by per-sample timers and the serial MIDI port by a
 * byte FIFO. Output rate is the chip's own 44.1 kHz.
 */
#ifndef UPSTREAM_SCSP_H
#define UPSTREAM_SCSP_H

#include <stdint.h>
#include "../state.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct upstream_scsp upstream_scsp;

/* irq(user, level 1-7, asserted): interrupt lines of the sound CPU */
typedef void (*upstream_scsp_irq_fn)(void *user, int level, int asserted);

/* `ram`: sound RAM in 68000 (big-endian) byte order, `ram_mask` + 1 bytes */
upstream_scsp    *upstream_scsp_create(uint8_t *ram, uint32_t ram_mask, upstream_scsp_irq_fn irq, void *user);
void     upstream_scsp_destroy(upstream_scsp *s);
void     upstream_scsp_reset(upstream_scsp *s);
/* registers, byte offset 0x000-0xfff */
uint16_t upstream_scsp_read16(upstream_scsp *s, uint32_t offset);
void     upstream_scsp_write16(upstream_scsp *s, uint32_t offset, uint16_t data, uint16_t mask);
void     upstream_scsp_midi_in(upstream_scsp *s, uint8_t data);
/* writes `n` stereo samples (interleaved L/R, 16-bit range) */
void     upstream_scsp_render(upstream_scsp *s, int32_t *out, int n);
int      upstream_scsp_slots_active(const upstream_scsp *s, int *mvol);   /* debugging */

void upstream_scsp_state_archive(upstream_scsp *s, m2_state *a);
/* Optional serial return wire. Inert without a listener. */
void upstream_scsp_set_midi_reply(upstream_scsp *s,void (*reply)(void *,uint8_t),void *user);
void upstream_scsp_reset_midi(upstream_scsp *s);
void upstream_scsp_midi_state_archive(upstream_scsp *s,m2_state *a);

#ifdef __cplusplus
}
#endif

#endif
