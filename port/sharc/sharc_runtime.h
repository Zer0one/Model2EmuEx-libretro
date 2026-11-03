#ifndef M2_SHARC_RUNTIME_H
#define M2_SHARC_RUNTIME_H
#include "sharc_bind.h"
/* Composition of the recovered instruction handlers and scheduler. This does
 * not allocate a machine or replace native board/address-space bindings.
 * The resolver and bus obey the binding contracts in sharc_bind.h/memory.h.
 * execution represents the fixed board state; event_queue has native capacity.
 * Each current decoded record consists of 27 valid word tokens. Guest operands
 * and stack indices retain the original valid-storage preconditions.
 */
typedef struct {
    m2_sharc_execution *execution;
    m2_sharc_fp_state *fp;
    m2_sharc_word_resolver word;
    void *opaque;
    m2_sharc_diagnostic_hook diagnostic;
    const m2_sharc_memory_bus *bus;
    uint32_t *event_queue;
    /* Unsupported code is an explicit integration failure, never a NOP.
     * Called by scheduler callbacks only; MUST NOT return. Direct dispatch
     * and event calls instead return false to their caller. */
    void (*failure)(void *opaque,uint32_t entry,uint32_t record);
} m2_sharc_runtime;
bool m2_sharc_runtime_dispatch(m2_sharc_runtime *runtime,uint32_t entry_eflags);
bool m2_sharc_runtime_event(m2_sharc_runtime *runtime,uint32_t index);
void m2_sharc_runtime_run_bounded(m2_sharc_runtime *runtime);
void m2_sharc_runtime_run_continuous(m2_sharc_runtime *runtime);
#endif
