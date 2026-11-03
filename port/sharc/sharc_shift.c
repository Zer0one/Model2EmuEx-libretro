#include "sharc_shift.h"

bool m2_sharc_shift_compute(uint32_t operation, uint32_t value, uint32_t control,
                            const uint32_t *base, uint32_t *status, uint32_t *result)
{
    uint32_t output, test_value;
    uint32_t encoded, count;
    bool negative, rotate, merge, arithmetic, zero;

    switch (operation) {
    case M2_SHARC_BIT_TEST: /* 0x004bc3f0: unlike the other bit ops, no range check. */
        test_value = value & (UINT32_C(1) << (control & 31u));
        *status = (*status & ~UINT32_C(0x1000)) | (test_value == 0 ? 0x1000u : 0u);
        *result = value;
        return true;
    case M2_SHARC_BIT_SET:   /* 0x00462a20 */
    case M2_SHARC_BIT_CLEAR: /* 0x004629c0 */
    case M2_SHARC_BIT_TOGGLE:/* 0x00462a60 */
        *status |= UINT32_C(0x1800);
        /* The original uses signed JG: negative indices reach the masked shift.
         * Positive indices >31 return the INDEX, preserving this early-exit
         * quirk rather than silently returning the input value.
         */
        if (control > 31u && !(control & UINT32_C(0x80000000))) {
            *result = control;
            return true;
        }
        test_value = UINT32_C(1) << (control & 31u);
        if (operation == M2_SHARC_BIT_SET)
            output = value | test_value;
        else if (operation == M2_SHARC_BIT_CLEAR)
            output = value & ~test_value;
        else
            output = value ^ test_value;
        *status = (*status & ~UINT32_C(0x3800)) | (output == 0 ? 0x1000u : 0u);
        *result = output;
        return true;
    case M2_SHARC_LSHIFT:    /* 0x004627a0 */
    case M2_SHARC_ASHIFT:    /* 0x00462900 */
    case M2_SHARC_ROTATE:    /* 0x00462960 */
    case M2_SHARC_LSHIFT_OR: /* 0x00462800 */
    case M2_SHARC_ASHIFT_OR: /* 0x00462880 */
        break;
    default:
        return false;
    }

    encoded = control & 255u;
    negative = (encoded & 128u) != 0;
    count = (negative ? 0u - encoded : encoded) & 31u;
    rotate = operation == M2_SHARC_ROTATE;
    merge = operation == M2_SHARC_LSHIFT_OR || operation == M2_SHARC_ASHIFT_OR;
    arithmetic = operation == M2_SHARC_ASHIFT || operation == M2_SHARC_ASHIFT_OR;
    output = value;
    if (count != 0) {
        if (negative) {
            output = value >> count;
            if (rotate)
                output |= value << (32u - count);
            else if (arithmetic && (value & UINT32_C(0x80000000)))
                output |= ~(UINT32_MAX >> count);
        } else {
            output = value << count;
            if (rotate)
                output |= value >> (32u - count);
        }
    }
    /* Preservation quirk: zero-count x86 shifts leave ZF from TEST/NEG CL;
     * rotates leave ZF unchanged for EVERY count. Thus flag 0x80 need not
     * describe output==0. No dependency on the current host CPU flags exists.
     */
    zero = (rotate || count == 0) ? encoded == 0 : output == 0;
    *status = (*status & ~UINT32_C(0x2880)) | (zero ? 0x80u : 0u) |
              (negative ? 0u : 0x800u);
    if (merge)
        output |= *base;
    *result = output;
    return true;
}
