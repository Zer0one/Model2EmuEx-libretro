#ifndef M2_SHARC_COMPUTE_H
#define M2_SHARC_COMPUTE_H
#include "sharc_fp.h"
#include "sharc_lifecycle.h"
#include "sharc_operation.h"
typedef uint32_t *(*m2_sharc_word_resolver)(void *opaque,uint32_t token);
typedef struct {
    void *opaque;
    m2_sharc_word_resolver word;
    m2_sharc_diagnostic_hook diagnostic;
    uint32_t *astat,*pc,*loop_count,*stop,*current_record;
    m2_sharc_fp_state *fp;
} m2_sharc_compute_context;
/* Bind recovered helpers to original 32-bit decoded-record tokens. Resolver
 * provides valid, stable word storage and may alias guest state/record words.
 * Original x86 entry flags are explicit. No invented fallback on unknown code. */
bool m2_sharc_compute(m2_sharc_compute_context *c,uint32_t entry,uint32_t lhs,
    uint32_t rhs,uint32_t entry_eflags,uint32_t *result);
/* Full 4bcb50 / 4bcb10 compute(+move) paths, including diagnostic callbacks
 * changing the current record. Other memory/control wrappers remain separate. */
bool m2_sharc_dispatch_compute(m2_sharc_compute_context *c,bool move);
/* Adapter for memory/control wrappers. Uses the native PC=24/masked FP
 * contract; computation updates the exact supplied ASTAT binding. */
m2_sharc_operation_hooks m2_sharc_compute_hooks(m2_sharc_compute_context *context);
#endif
