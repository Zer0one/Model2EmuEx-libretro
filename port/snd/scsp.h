/*
 * Yamaha YMF292-F "SCSP": 32 slots of PCM/FM plus the effects DSP. C port of
 * MAME's scsp.cpp (BSD-3-Clause; SCSP emulation by ElSemi,
 * the Model 2 Emulator's author, with R. Belmont and kingshriek), with the
 * MAME scheduler replaced by per-sample timers and the serial MIDI port by a
 * byte FIFO. The effects DSP preserves recovered ElSemi 1.1a behavior in
 * scsp_dsp_original.c by default; the upstream subsystem is implemented
 * separately in upstream_scsp.c. Output rate is the chip's own 44.1 kHz.
 */
#ifndef SCSP_H
#define SCSP_H

#include <stdint.h>
#include "../state.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct scsp scsp;
enum { SCSP_MIXER_BLOCK = 768 };
/* Stable 32-bit process addresses; actual audio buffers are separately bounded. */
enum { SCSP_SOUND_RAM_ADDRESS = 0x73000000, SCSP_DSP_RAM_ADDRESS = 0x78000000 };
enum { SCSP_DSP_ORIGINAL, SCSP_DSP_MAME };
/* Select before execution; changing backend resets the chip. */
void scsp_set_dsp_backend(scsp *s,unsigned backend);
unsigned scsp_get_dsp_backend(const scsp *s);

/* irq(user, level 1-7, asserted): interrupt lines of the sound CPU */
typedef void (*scsp_irq_fn)(void *user, int level, int asserted);

/* `ram`: sound RAM in ElSemi/A68K word-swapped byte order, 1 MiB. ram_mask applies to DMA/MAME DSP */
void scsp_set_interleaved_mixer(scsp *s, int enabled);
scsp    *scsp_create(uint8_t *ram, uint32_t ram_size, uint32_t ram_mask, scsp_irq_fn irq, void *user);
void     scsp_destroy(scsp *s);
void     scsp_reset(scsp *s);
void     scsp_original_power_on(scsp *s);
/* registers, byte offset 0x000-0xfff */
uint16_t scsp_read16(scsp *s, uint32_t offset);
/* CPU-facing reads differ from chip-internal DMA/register access in ElSemi.
 * Slot/ring/DSP widths and ordinary global/MIDI side effects are recovered.
 * Global mirrors also expose the native 32-bit slot record layout. */
uint8_t  scsp_cpu_read8(scsp *s, uint32_t offset);
uint16_t scsp_cpu_read16(scsp *s, uint32_t offset);
void     scsp_cpu_ack_irq(scsp *s);
/* Live A68K DATA wrappers return the numeric x86 scratch values consumed
 * by the reconstructed executor. The host address is never published. */
typedef struct { uint32_t eax,edx,flags; } scsp_cpu_observation;
int scsp_cpu_read_observed(scsp *s,uint32_t address,unsigned width,
                          uint32_t input_flags,scsp_cpu_observation *out);
/* WRITE callbacks/acknowledge expose the EAX/control subset consumed by the
 * recovered executor. No write-return EDX provenance is implied. */
typedef struct { uint32_t eax,flags; } scsp_cpu_completion;
int scsp_cpu_write_observed(scsp *s,uint32_t address,unsigned width,uint32_t value,
                           uint32_t input_flags,scsp_cpu_completion *out);
void scsp_cpu_store(scsp *s,uint32_t address,unsigned width,uint32_t value);
int scsp_cpu_ack_observed(scsp *s,uint32_t input_flags,scsp_cpu_completion *out);
/* Returns 1 for a handled CPU ring write, including a native ignored long. */
int scsp_cpu_write_ring(scsp *s, unsigned offset, unsigned width, uint32_t value);
/* CPU long store with one native address decode and one start decision. */
void     scsp_cpu_write_dsp32(scsp *s, uint32_t offset, uint32_t data);
void     scsp_write16(scsp *s, uint32_t offset, uint16_t data, uint16_t mask);
/* One native SCSP timer/IRQ event. scsp_render already includes this in
 * the production schedule. The original board clock drives it separately. */
void     scsp_clock_tick(scsp *s);
/* For an A68K board, keep its published IRQ/STOP word bound while the chip
 * runs. Other CPU backends continue to receive interrupt-line transitions. */
/* Numeric x86 caller frame and DSP allocation for the research bus. */
void scsp_bind_cpu_write_frame(scsp *s, const uint32_t *wrapper_sp, uint32_t code_address);
void     scsp_bind_irq_register(scsp *s, uint32_t *irq_register);
void     scsp_midi_in(scsp *s, uint8_t data);
/* writes `n` stereo samples (interleaved L/R, 16-bit range) */
void     scsp_render(scsp *s, int32_t *out, int n);
void     scsp_render_clocked(scsp *s, int32_t *out, int n);
void     scsp_render_pair_clocked(scsp *primary, scsp *second, int32_t *out, int n);
int      scsp_slots_active(const scsp *s, int *mvol);   /* debugging */

const char *scsp_fault(const scsp *s,uint32_t *address);
void scsp_state_archive(scsp *s, m2_state *a);
/* Optional serial return wire. Inert without a listener. */
void scsp_set_midi_reply(scsp *s,void (*reply)(void *,uint8_t),void *user);
void scsp_reset_midi(scsp *s);
void scsp_midi_state_archive(scsp *s,m2_state *a);

#ifdef __cplusplus
}
#endif

#endif
