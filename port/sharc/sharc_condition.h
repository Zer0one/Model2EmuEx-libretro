#ifndef M2_SHARC_CONDITION_H
#define M2_SHARC_CONDITION_H
#include <stdbool.h>
#include <stdint.h>

/* Original tables 0x00573490 (instruction) and 0x00573510 (loop).
 * Preserve raw return masks, not just truth values, and sticky stop side effects.
 * Invalid table/index returns false with outputs unchanged. Pointers distinct.
 */
bool m2_sharc_condition(unsigned table, unsigned code, uint32_t status,
                        uint32_t loop_count, uint32_t *stop, uint32_t *result);

typedef struct m2_sharc_integer_record {
    unsigned condition, operation;
    const uint32_t *lhs, *rhs;
    uint32_t *destination;
    const uint32_t *move_source;
    uint32_t *move_destination;
} m2_sharc_integer_record;

/* Original 0x004bcb50 (compute) / 0x004bcb10 (compute plus register move).
 * Partial dispatcher for recovered integer helpers, not memory/branch handlers.
 * Snapshot move source and both operands before compute; write compute result
 * first, then the move. Operand/destination/status aliasing is intentional.
 * Invalid condition/op is rejected before side effects. Record pointers are
 * stable host bindings, not the original serialized 32-bit pointer layout.
 */
bool m2_sharc_dispatch_integer(const m2_sharc_integer_record *record, bool move,
                               uint32_t loop_count, uint32_t *status, uint32_t *stop);
#endif
