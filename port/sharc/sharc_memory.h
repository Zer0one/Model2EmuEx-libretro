#ifndef M2_SHARC_MEMORY_H
#define M2_SHARC_MEMORY_H
#include <stdbool.h>
#include <stdint.h>
#include "sharc_operation.h"

/* Seventeen original integer compute + memory/branch handlers. Stable host
 * bindings replace the decoded record's 32-bit pointers. Callbacks may mutate
 * bound words (address modifiers are read AFTER callbacks), but must not
 * replace the active record/bindings. Board callbacks themselves are not
 * reconstructed here. mirror[n] binds data[n] - 0x80 bytes in the original.
 */
typedef uint32_t (*m2_sharc_read)(void *opaque, uint32_t address);
typedef void (*m2_sharc_write)(void *opaque, uint32_t address, uint32_t value);
typedef struct m2_sharc_memory_record {
    uint32_t condition, operation, immediate, flags;
    uint32_t *address[2], *step[2], *data[2], *mirror[2];
    const uint32_t *lhs, *rhs;
    uint32_t *destination;
} m2_sharc_memory_record;
typedef struct m2_sharc_memory_bus {
    m2_sharc_read read;
    m2_sharc_write write;
    void *opaque;
} m2_sharc_memory_bus;

/* handler is an original entry address listed in sharc_memory.c.
 * entry_eflags means original x86 flags, never current host compiler flags.
 * pc and record_offset capture branch effects BEFORE the outer-loop advance;
 * offset is the wrapping 32-bit byte displacement from decoded program base.
 * No out-of-range C pointer is formed for target zero or wrapping targets.
 * Unsupported handler/op/condition fails atomically. Valid bindings/callbacks
 * for the executed path are required. No floating-point dispatch is implied.
 */
bool m2_sharc_dispatch_memory(uint32_t handler,
    const m2_sharc_memory_record *r, const m2_sharc_memory_bus *bus,
    uint32_t entry_eflags, uint32_t loop_count, uint32_t *status,
    uint32_t *stop, uint32_t *pc, uint32_t *record_offset);
/* Same wrapper semantics with an explicit complete compute backend. NULL
 * operation selects the established integer-only API. Bindings remain stable. */
bool m2_sharc_dispatch_memory_ex(uint32_t handler,
    const m2_sharc_memory_record *r,const m2_sharc_memory_bus *bus,
    uint32_t entry_eflags,uint32_t loop_count,uint32_t *status,
    uint32_t *stop,uint32_t *pc,uint32_t *record_offset,
    const m2_sharc_operation_hooks *operation);
#endif
