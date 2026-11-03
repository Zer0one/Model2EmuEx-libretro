#ifndef M2_SHARC_FP_SCALE_H
#define M2_SHARC_FP_SCALE_H
#include "sharc_fp.h"
/* FSCALE paths with native PC=24, masked exceptions and all RC modes. */
bool m2_sharc_fp_scale(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t *astat,m2_sharc_fp_state *fp,uint32_t *result);
#endif
