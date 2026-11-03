#ifndef M2_SHARC_FP_H
#define M2_SHARC_FP_H
#include <stdbool.h>
#include <stdint.h>
typedef struct { uint16_t control, status; } m2_sharc_fp_state;
/* Balanced x87 helpers with masked exceptions and a valid empty x87 stack.
 * control is architectural FNSTCW state (reserved bit 6 set), not the raw
 * scheduler memory constant 0x003f. Model host x87 flags separately from ASTAT. No host
 * float casts/fenv are used, so the caller's rounding/NaN mode cannot leak in.
 * Unsupported entries/unmasked controls return false without mutation. */
bool m2_sharc_fp_simple(uint32_t entry, uint32_t lhs, uint32_t rhs,
    uint32_t *astat, m2_sharc_fp_state *fp, uint32_t *result);
#endif
