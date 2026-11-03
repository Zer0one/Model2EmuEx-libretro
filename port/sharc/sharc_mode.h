#ifndef M2_SHARC_MODE_H
#define M2_SHARC_MODE_H
#include "sharc_execute.h"
#include "sharc_memory.h"
/* Fifteen native mode/bank/stack primitives. queue holds original 32-bit event
 * tokens and must have room at the current event_count (two for mode writes).
 * As in the original, valid stack indices and queue storage are caller-owned.
 * result is written only by read forwarding, PC peek and PC pop. State represents
 * the original fixed SHARC instance, including ASTAT selection by 4bcfc0/4bcfe0.
 * Original x86 ABI requires DF clear for the four bank-copy callbacks.
 */
bool m2_sharc_state_helper(uint32_t entry,m2_sharc_execution *s,uint32_t *target,
    uint32_t arg0,uint32_t arg1,uint32_t *queue,const m2_sharc_memory_bus *bus,uint32_t *result);
#endif
