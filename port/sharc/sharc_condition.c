#include "sharc_condition.h"
#include "sharc_integer.h"

bool m2_sharc_condition(unsigned table, unsigned code, uint32_t status,
                        uint32_t loop_count, uint32_t *stop, uint32_t *result)
{
    static const uint32_t masks[11] = {
        8, 2, 0x80, 0x40, 0x800, 0x1000,
        0x80000, 0x100000, 0x200000, 0x400000, 0x40000
    };
    uint32_t value;
    unsigned slot;
    if (table > 1 || code > 31)
        return false;
    if (code == 15) {
        *result = table ? loop_count == 1 : loop_count != 1;
        return true;
    }
    if (code >= 30) {
        *result = (code == 30 || table == 0) ? 1u : 0u;
        return true;
    }
    slot = code & 15u;
    if (slot == 0)
        value = status & 1u;
    else if (slot == 1)
        value = (status & 4u) != 0 && (status & 1u) == 0;
    else if (slot == 2)
        value = (status & 5u) != 0;
    else if (slot == 14)
        value = 0;
    else {
        value = status & masks[slot - 3];
        /* Both positive and negative flag conditions stop on a SET flag. */
        if ((slot == 9 || slot == 10) && value != 0)
            *stop = 1;
    }
    *result = code >= 16 ? value == 0 : value;
    return true;
}

bool m2_sharc_dispatch_integer(const m2_sharc_integer_record *record, bool move,
                               uint32_t loop_count, uint32_t *status, uint32_t *stop)
{
    uint32_t condition, lhs, rhs, saved_move = 0, value;
    uint32_t flags, byte, parity;
    if (record->condition > 31 || !m2_sharc_integer_supported(record->operation))
        return false;
    if (!m2_sharc_condition(0, record->condition, *status, loop_count, stop, &condition))
        return false;
    if (condition == 0)
        return true;
    if (move)
        saved_move = *record->move_source;
    rhs = *record->rhs;
    lhs = *record->lhs;
    /* 0x4bcb1a / 0x4bcb5a: TEST EAX,EAX establishes helper-entry flags.
     * Loads/PUSH/CALL preserve them. All current true conditions are positive:
     * CF=ZF=SF=OF=0, PF reflects the low-byte parity. This is a derived caller
     * contract for these TWO paths, not a global substitute for entry EFLAGS.
     * Preserve ElSemi's resulting INC/DEC carry and NOT flag behavior.
     */
    byte = condition & 255u;
    parity = byte ^ (byte >> 4);
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    flags = 2u | ((parity & 1u) == 0 ? 4u : 0u) |
            ((condition >> 24) & 0x80u);
    if (!m2_sharc_integer_compute(record->operation, lhs, rhs, flags, status, &value))
        return false;
    *record->destination = value;
    if (move)
        *record->move_destination = saved_move;
    return true;
}
