#ifndef M2_FM_ORIGINAL_H
#define M2_FM_ORIGINAL_H
#include "../state.h"
#include "model1_completion.h"

typedef struct m2_original_fm m2_original_fm;

m2_original_fm *m2_original_fm_create(void);
void m2_original_fm_reset(m2_original_fm *chip);
void m2_original_fm_free(m2_original_fm *chip);
void m2_original_fm_write(m2_original_fm *chip, unsigned port, uint8_t value);
/* The board may advance ten frames before a register write or timer A overflow.
 * The caller owns the block and its cursor; timer B never renders ahead. */
m2_m1_completion m2_original_fm_store(m2_original_fm *chip,unsigned port,uint8_t value,uint32_t flags);
int m2_original_fm_write_flush(const m2_original_fm *chip, unsigned port);
uint32_t m2_original_fm_tick(m2_original_fm *chip, void (*flush)(void *), void *user);
unsigned m2_original_fm_status(const m2_original_fm *chip);
void m2_original_fm_render(m2_original_fm *chip, int16_t *stereo, size_t frames);
void m2_original_fm_archive(m2_original_fm *chip, m2_state *archive);
#endif
