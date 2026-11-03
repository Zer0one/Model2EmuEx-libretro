#include "sharc_integer.h"

#define SIGN UINT32_C(0x80000000)

bool m2_sharc_integer_supported(uint32_t operation)
{
    switch (operation) {
    case M2_SHARC_ADD: case M2_SHARC_SUB: case M2_SHARC_ADDC: case M2_SHARC_SUBC:
    case M2_SHARC_HALF_SUM: case M2_SHARC_COMPARE: case M2_SHARC_PASS:
    case M2_SHARC_NEGATE: case M2_SHARC_INCREMENT_C: case M2_SHARC_DECREMENT_C:
    case M2_SHARC_INCREMENT: case M2_SHARC_DECREMENT: case M2_SHARC_ABS:
    case M2_SHARC_AND: case M2_SHARC_OR: case M2_SHARC_XOR: case M2_SHARC_NOT:
    case M2_SHARC_MIN: case M2_SHARC_MAX:
        return true;
    default:
        return false;
    }
}

bool m2_sharc_integer_compute(uint32_t operation, uint32_t lhs, uint32_t rhs,
                              uint32_t entry_eflags, uint32_t *status,
                              uint32_t *result)
{
    uint32_t old = *status;
    uint32_t value, flags_value;
    uint32_t clear = UINT32_C(0x43f);
    uint32_t carry = 0, overflow = 0, extra = 0;
    bool inherited_zs = false;

    switch (operation) {
    case M2_SHARC_ADDC: /* 0x00461040: wrap rhs BEFORE the final ADD. */
        rhs += (old >> 3) & 1u;
        /* fall through */
    case M2_SHARC_ADD: /* 0x00460f40 */
        value = lhs + rhs;
        carry = value < lhs;
        overflow = ((~(lhs ^ rhs) & (lhs ^ value)) >> 31) & 1u;
        break;
    case M2_SHARC_SUBC: /* 0x004610c0: DEC/INC rhs, then ordinary SUB. */
        rhs += ((old & 8u) == 0);
        /* fall through */
    case M2_SHARC_SUB: /* 0x00460fc0: AC stores x86 borrow, not its inverse. */
        value = lhs - rhs;
        carry = lhs < rhs;
        overflow = (((lhs ^ rhs) & (lhs ^ value)) >> 31) & 1u;
        break;
    case M2_SHARC_HALF_SUM: /* 0x00461140: two LOGICAL shifts, then ADD. */
        lhs >>= 1;
        rhs >>= 1;
        value = lhs + rhs;
        carry = value < lhs;
        break;
    case M2_SHARC_COMPARE: /* 0x004611a0: return lhs; flags from wrapped SUB. */
        flags_value = lhs - rhs;
        value = lhs;
        goto finish;
    case M2_SHARC_INCREMENT_C: /* 0x004611e0: TEST clears CF; two INCs. */
        lhs += (old >> 3) & 1u;
        value = lhs + 1u;
        overflow = lhs == UINT32_C(0x7fffffff);
        break;
    case M2_SHARC_DECREMENT_C: /* 0x00461260: TEST, optional INC, DEC. */
        lhs += (old >> 3) & 1u;
        value = lhs - 1u;
        overflow = lhs == SIGN;
        break;
    case M2_SHARC_INCREMENT: /* 0x004612e0: x86 INC preserves entry CF. */
        value = lhs + 1u;
        overflow = lhs == UINT32_C(0x7fffffff);
        carry = entry_eflags & 1u;
        break;
    case M2_SHARC_DECREMENT: /* 0x00461360 */
        value = lhs - 1u;
        overflow = lhs == SIGN;
        carry = entry_eflags & 1u;
        break;
    case M2_SHARC_NEGATE: /* 0x004613e0 */
        value = 0u - lhs;
        carry = lhs != 0;
        overflow = lhs == SIGN;
        break;
    case M2_SHARC_ABS: /* 0x00461460: AS is sticky for nonnegative inputs. */
        value = lhs;
        clear = UINT32_C(0x42f);
        if (lhs & SIGN) {
            value = 0u - lhs;
            carry = 1;
            overflow = lhs == SIGN;
            extra = 0x10;
        }
        break;
    case M2_SHARC_PASS: /* 0x004614e0 */
        value = lhs;
        break;
    case M2_SHARC_AND: /* 0x00461520 */
        value = lhs & rhs;
        break;
    case M2_SHARC_OR: /* 0x00461560 */
        value = lhs | rhs;
        break;
    case M2_SHARC_XOR: /* 0x004615a0 */
        value = lhs ^ rhs;
        break;
    case M2_SHARC_NOT: /* 0x004615e0: NOT leaves host flags untouched. */
        value = ~lhs;
        inherited_zs = true;
        break;
    case M2_SHARC_MIN: /* 0x00461620: signed ordering without signed overflow. */
        value = (lhs ^ SIGN) <= (rhs ^ SIGN) ? lhs : rhs;
        break;
    case M2_SHARC_MAX: /* 0x00461660 */
        value = (lhs ^ SIGN) >= (rhs ^ SIGN) ? lhs : rhs;
        break;
    default:
        return false;
    }
    flags_value = value;
finish:
    *status = (old & ~clear) | extra | (carry << 3) | (overflow << 1);
    if (inherited_zs) {
        *status |= ((entry_eflags >> 6) & 1u) | ((entry_eflags >> 5) & 4u);
    } else {
        *status |= (flags_value == 0 ? 1u : 0u) | ((flags_value >> 29) & 4u);
    }
    *result = value;
    return true;
}
