#ifndef M2_SHARC_DECODE_H
#define M2_SHARC_DECODE_H
#include <stdint.h>
/* Original 0x4be800. Record words contain virtual address/handler tokens, NOT
 * cast native pointers. Caller supplies non-overlapping original logical state
 * and record bases; the later runtime binding layer resolves these tokens.
 * Unsupported opcodes retain the original diagnostic-handler selection. */
void m2_sharc_decode_compute(uint32_t instruction,uint32_t extension,
    uint32_t state_base,uint32_t record_base,uint32_t record[27]);
#endif
