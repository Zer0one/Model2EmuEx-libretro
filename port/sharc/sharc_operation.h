#ifndef M2_SHARC_OPERATION_H
#define M2_SHARC_OPERATION_H
#include <stdbool.h>
#include <stdint.h>
/* Injectable computation for already-recovered wrappers. Operation can be an
 * original helper token or a caller-defined selector. Supported must validate
 * the current helper/caller contract before wrapper side effects. */
typedef struct {
    void *opaque;
    bool (*supported)(void *opaque,uint32_t operation);
    bool (*run)(void *opaque,uint32_t operation,uint32_t lhs,uint32_t rhs,
                uint32_t entry_eflags,uint32_t *status,uint32_t *result);
} m2_sharc_operation_hooks;
#endif
