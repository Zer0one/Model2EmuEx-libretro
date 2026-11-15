#ifndef M2_MODEL1_ORIGINAL_H
#define M2_MODEL1_ORIGINAL_H
#include "../state.h"
#include "model1_completion.h"

/* Model 1-style primary audio board. The guest CPU owns scanline execution;
 * the board owns each partially generated FM block until the frame service. */
typedef struct m2_original_m1 m2_original_m1;
m2_original_m1 *m2_original_m1_create(const uint8_t *samples, size_t size);
void m2_original_m1_free(m2_original_m1 *b);
int m2_original_m1_begin(m2_original_m1 *b, unsigned frames);
void m2_original_m1_command(m2_original_m1 *b, uint8_t value);
void m2_original_m1_cursors(const m2_original_m1 *b,uint8_t cursors[2]);
int m2_original_m1_irq_pending(const m2_original_m1 *b);
uint32_t m2_original_m1_tick(m2_original_m1 *b);
uint32_t m2_original_m1_read(m2_original_m1 *b, uint32_t address, unsigned width,
                             uint32_t *irq);
void m2_original_m1_write(m2_original_m1 *b, uint32_t address, unsigned width,
                          uint32_t value);
m2_m1_completion m2_original_m1_fm_store(m2_original_m1 *b,uint32_t a,unsigned width,
                                         uint32_t value,uint32_t flags);
m2_m1_completion m2_original_m1_pcm_store(m2_original_m1 *b,unsigned chip,uint32_t a,
                     unsigned width,uint32_t value,uint32_t sp,uint32_t flags);
int m2_original_m1_output_frames(m2_original_m1 *b,unsigned frames);
void m2_original_m1_finish(m2_original_m1 *b, int16_t *output, unsigned pcm1,
                           unsigned pcm2, unsigned fm);
const char *m2_original_m1_error(const m2_original_m1 *b);
void m2_original_m1_archive(m2_original_m1 *b,m2_state *a);
#endif
