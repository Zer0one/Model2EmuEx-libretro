#ifndef M2_SHARC_CONTROL_H
#define M2_SHARC_CONTROL_H
#include <stdbool.h>
#include "sharc_execute.h"
#include "sharc_operation.h"

typedef struct m2_sharc_control_record {
    uint32_t condition, operation, immediate, count, flags;
    const uint32_t *value, *address, *step, *lhs, *rhs;
    uint32_t *destination;
} m2_sharc_control_record;
/* Resolve the current virtual record again after delay-slot callbacks, as the
 * original reloads the global record pointer. Bindings/metadata are stable
 * between callbacks; operands may alias the execution state. */
typedef const m2_sharc_control_record *(*m2_sharc_control_resolver)(void *, uint32_t);
bool m2_sharc_dispatch_control(uint32_t handler, m2_sharc_execution *s,
    const m2_sharc_execution_hooks *h, m2_sharc_control_resolver resolve, void *opaque);
bool m2_sharc_dispatch_control_ex(uint32_t handler,m2_sharc_execution *s,
    const m2_sharc_execution_hooks *h,m2_sharc_control_resolver resolve,void *opaque,
    const m2_sharc_operation_hooks *operation);
#endif
