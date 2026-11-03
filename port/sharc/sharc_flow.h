#ifndef M2_SHARC_FLOW_H
#define M2_SHARC_FLOW_H
#include <stdbool.h>
#include <stdint.h>

/* Original execution-loop flag producers, not a complete execution loop.
 * Return the defined CF/PF/ZF/SF/OF bits plus x86's fixed bit 1; AF is omitted.
 * value is the original 32-bit budget/address BEFORE the indicated operation.
 * Delay-slot addresses are original virtual record addresses, never truncated
 * host pointers. Their mapping must be settled when the program store is ported.
 */
enum m2_sharc_flow_origin {
    M2_SHARC_FLOW_BOUNDED_FIRST, /* 0x4bd058: OR EDI,-1 */
    M2_SHARC_FLOW_CONTINUOUS_FIRST, /* 0x4be076: CMP budget,0 */
    M2_SHARC_FLOW_NEXT, /* 0x4bd13a / 0x4be165: SUB budget,1 */
    M2_SHARC_FLOW_DELAY /* 0x4bdfa5 / 0x4bdfce: ADD record,0x6c */
};
bool m2_sharc_flow_flags(unsigned origin, uint32_t value, uint32_t *flags);
#endif
