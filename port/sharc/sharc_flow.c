#include "sharc_flow.h"

static uint32_t logical_flags(uint32_t value)
{
    uint32_t parity = value & 255u;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    return 2u | ((parity & 1u) ? 0u : 4u) |
           (value == 0 ? 0x40u : 0u) | ((value >> 24) & 0x80u);
}

bool m2_sharc_flow_flags(unsigned origin, uint32_t value, uint32_t *flags)
{
    uint32_t result, extra = 0;
    switch (origin) {
    case M2_SHARC_FLOW_BOUNDED_FIRST:
        /* OR EDI,-1, AFTER the entry budget check, survives until CALL.
         * Therefore an unconditional NOT sees SF=1 on this first dispatch. */
        result = 0xffffffffu;
        break;
    case M2_SHARC_FLOW_CONTINUOUS_FIRST:
        result = value; /* CMP budget,0 */
        break;
    case M2_SHARC_FLOW_NEXT:
        result = value - 1u;
        extra = (value == 0 ? 1u : 0u) | (value == 0x80000000u ? 0x800u : 0u);
        break;
    case M2_SHARC_FLOW_DELAY:
        result = value + 0x6cu;
        extra = (result < value ? 1u : 0u) |
                ((~(value ^ 0x6cu) & (value ^ result) & 0x80000000u) ? 0x800u : 0u);
        break;
    default:
        return false;
    }
    *flags = logical_flags(result) | extra;
    return true;
}
