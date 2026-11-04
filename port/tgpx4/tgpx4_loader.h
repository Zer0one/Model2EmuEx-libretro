#ifndef M2_TGPX4_LOADER_H
#define M2_TGPX4_LOADER_H

#include "tgpx4_decode.h"
#include "tgpx4_program.h"
#include <stdbool.h>

/* Frontend-neutral composition of the recovered decoders. Tokens retain the
 * original 32-bit address space; no executable or ROM is needed at runtime. */
void m2_tgpx4_decode_native(uint32_t low, uint32_t high, uint32_t record_token,
    uint32_t state_token, uint32_t *record, uint32_t *previous,
    m2_tgpx4_decode_registers *registers);

typedef struct {
    void *opaque;
    void (*release)(void *opaque, uint32_t token);
    /* Same successful-allocation/prefix contract as tgpx4_program.h. */
    uint32_t *(*allocate)(void *opaque, uint32_t bytes, uint32_t *token);
} m2_tgpx4_program_memory;

/* Upload/decode/reset with the native token tables and subdecoders. The caller
 * still owns allocation, state registration and board storage. */
void m2_tgpx4_load_program(m2_tgpx4_program *program, const uint8_t *source,
    uint32_t bytes, uint32_t state_token, const m2_tgpx4_program_memory *memory,
    const m2_tgpx4_registration *registration);

/* Same validation policy as SHARC: seed with the saved cache, re-decode and
 * compare all decoder-owned bits, retaining native unused allocator words. */
bool m2_tgpx4_program_matches(const uint8_t *source, const void *records,
    uint32_t count, uint32_t state_token, uint32_t program_token);

#endif
