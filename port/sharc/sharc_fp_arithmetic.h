#ifndef M2_SHARC_FP_ARITHMETIC_H
#define M2_SHARC_FP_ARITHMETIC_H
#include "sharc_fp.h"
/* Native scheduler PC=24-bit significand, with x87's extended exponent range.
 * Supports all RC modes. Other PC settings are outside this recovered caller
 * contract and return false without mutation; no host-float fallback exists. */
bool m2_sharc_fp_arithmetic(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t *astat,m2_sharc_fp_state *fp,uint32_t *result);
/* First output is sum for 4bc310, otherwise product; second is the companion
 * result. Inputs are snapshots. Writes precede ASTAT updates, preserving aliases. */
bool m2_sharc_fp_compound(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t mul_lhs,uint32_t mul_rhs,uint32_t *first,uint32_t *second,
    uint32_t *astat,m2_sharc_fp_state *fp);
/* 4bc270 snapshots all inputs, then writes product, sum, difference, ASTAT. */
bool m2_sharc_fp_triple(uint32_t lhs,uint32_t rhs,uint32_t mul_lhs,uint32_t mul_rhs,
    uint32_t *product,uint32_t *sum,uint32_t *difference,uint32_t *astat,m2_sharc_fp_state *fp);
#endif
