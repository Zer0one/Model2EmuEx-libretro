#ifndef M2_TGPX4_PROGRAM_H
#define M2_TGPX4_PROGRAM_H

#include "tgpx4_lifecycle.h"

typedef struct {
    uint8_t state[M2_TGPX4_RECORD_OFFSET + 4];
    uint32_t active_base, active_state, active_record;
} m2_tgpx4_program;

typedef struct {
    uint32_t flag, state, bytes, restore, save;
    const char *name;
} m2_tgpx4_state_descriptor;

typedef struct {
    void *opaque;
    uint32_t list;
    uint32_t (*read)(void *opaque, uint32_t address);
    void (*write)(void *opaque, uint32_t address, uint32_t value);
    uint32_t (*create)(void *opaque, uint32_t head, uint32_t next,
                       const m2_tgpx4_state_descriptor *descriptor);
    /* Native exception boundary. Must not return. */
    void (*fatal)(void *opaque, const char *message);
} m2_tgpx4_registration;

typedef struct {
    void *opaque;
    void (*release)(void *opaque, uint32_t token);
    /* As in the original valid path, allocation must succeed. Return word
     * storage with 0x2c bytes of accessible allocator prefix in the same array.
     * The original rewrite can inspect that prefix even at record zero. */
    uint32_t *(*allocate)(void *opaque, uint32_t bytes, uint32_t *token);
    void (*decode)(void *opaque, uint32_t low, uint32_t high, uint32_t *record);
} m2_tgpx4_program_hooks;

/* 004b7940. Uploads contain complete 8-byte instructions. The optional
 * registration precedes allocation. Allocator/decoder callbacks are seams. */
void m2_tgpx4_prepare_program(m2_tgpx4_program *program, const uint8_t *source,
    uint32_t bytes, uint32_t state_token, const m2_tgpx4_program_hooks *hooks,
    const m2_tgpx4_registration *registration);

#endif
