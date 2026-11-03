#ifndef M2_SHARC_AUX_H
#define M2_SHARC_AUX_H
#include <stdbool.h>
#include <stdint.h>
bool m2_sharc_aux(uint32_t entry,uint32_t lhs,uint32_t rhs,uint32_t *status,uint32_t *result);
/* Original 4bc3a0 snapshots operands, stores sum THEN difference, then updates
 * ASTAT from both computed values. Output/status aliases preserve that order. */
uint32_t m2_sharc_add_sub(uint32_t lhs,uint32_t rhs,uint32_t *sum,uint32_t *difference,uint32_t *status);
#endif
