#ifndef M2_SHARC_PROGRAM_H
#define M2_SHARC_PROGRAM_H
#include <stdint.h>
#include <stdbool.h>
typedef struct {
    uint32_t *allocation;
    uint32_t allocation_token,count,program_base,current_record;
} m2_sharc_program;
typedef struct {
    void *opaque;
    void (*release)(void *opaque,uint32_t *allocation,uint32_t token);
    uint32_t *(*allocate)(void *opaque,uint32_t bytes,uint32_t *token);
} m2_sharc_program_memory;
/* Original 4bf610, including replacement order and one-past record binding.
 * Allocator callbacks replace CRT ownership only. As in the original valid
 * path, allocation must succeed and count*108 must fit storage. Bytes beyond
 * the last complete 48-bit instruction are ignored. Unwritten record words
 * retain their allocator contents; this is deliberately not a zero-fill. */
void m2_sharc_decode_program(const uint8_t *source,uint32_t bytes,uint32_t state_base,
    uint32_t fixed_state_base,m2_sharc_program *program,const m2_sharc_program_memory *memory);
uint32_t m2_sharc_bind_condition(uint32_t code,uint32_t record[27]);
/* Validate immutable decoded fields against the original upload, not live
 * program RAM. Decoder-unwritten fields (including mutable scratch word 12)
 * retain their saved values, as they do in the original allocation. */
bool m2_sharc_program_matches(const uint8_t *source,const void *records,
    uint32_t count,uint32_t state,uint32_t fixed,uint32_t allocation_token);
#endif
