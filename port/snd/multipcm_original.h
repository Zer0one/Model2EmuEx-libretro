#ifndef M2_MULTIPCM_ORIGINAL_H
#define M2_MULTIPCM_ORIGINAL_H
#include <stddef.h>
#include <stdint.h>
#include "../state.h"
#include "model1_completion.h"

typedef struct m2_original_mpcm m2_original_mpcm;
m2_original_mpcm *m2_original_mpcm_create(unsigned chip, const uint8_t *rom, size_t size);
m2_m1_completion m2_original_mpcm_write_observed(m2_original_mpcm *m,unsigned port, uint8_t value,
                                                  uint32_t sp,uint32_t flags);
void m2_original_mpcm_bank(m2_original_mpcm *m, unsigned value);
void m2_original_mpcm_write(m2_original_mpcm *m, unsigned port, uint8_t value);
void m2_original_mpcm_mix(m2_original_mpcm *m, int16_t *stereo, size_t frames, unsigned gain);
const char *m2_original_mpcm_error(const m2_original_mpcm *m);
void m2_original_mpcm_archive(m2_original_mpcm *m, m2_state *a);
#endif
