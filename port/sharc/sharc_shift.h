#ifndef M2_SHARC_SHIFT_H
#define M2_SHARC_SHIFT_H

#include <stdbool.h>
#include <stdint.h>

enum m2_sharc_shift_op {
    M2_SHARC_LSHIFT = 0x200, M2_SHARC_ASHIFT = 0x204,
    M2_SHARC_ROTATE = 0x208,
    M2_SHARC_LSHIFT_OR = 0x220, M2_SHARC_ASHIFT_OR = 0x224,
    M2_SHARC_BIT_SET = 0x2c0, M2_SHARC_BIT_CLEAR = 0x2c4,
    M2_SHARC_BIT_TOGGLE = 0x2c8, M2_SHARC_BIT_TEST = 0x2cc
};

/* Original selector/operand semantics, not generic hardware operations.
 * Capture value/control before the call; only the two OR variants read base,
 * and they do so after updating status (base may point to status).
 * status/result must be distinct. Unsupported selectors leave them unchanged.
 */
bool m2_sharc_shift_compute(uint32_t operation, uint32_t value, uint32_t control,
                            const uint32_t *base, uint32_t *status, uint32_t *result);

#endif
