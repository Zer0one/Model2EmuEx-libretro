#include "tgpx4_loader.h"
#include <stdlib.h>
#include <string.h>

#include "tgpx4_tables.inc"

typedef struct {
    uint32_t record, state;
} decode_context;

static void subdecode(void *opaque, uint32_t entry,
    m2_tgpx4_decode_registers *r, uint32_t *record)
{
    const decode_context *c = opaque;
    switch (entry) {
    case 0x4b75d0: case 0x4b76b0:
        m2_tgpx4_decode_operands(entry, c->record, record, r, native_operands, native_alu);
        break;
    case 0x4b6730:
        m2_tgpx4_decode_control(c->record, c->state, record, r, native_operands, native_conditions);
        break;
    case 0x4b6ac0:
        m2_tgpx4_decode_immediate(c->record, c->state, record, r, native_operands);
        break;
    case 0x4b6b90:
        m2_tgpx4_decode_wide_move(c->record, c->state, record, r, native_operands);
        break;
    case 0x4b6ef0:
        m2_tgpx4_decode_transfers(c->record, c->state, record, r, native_operands);
        break;
    case 0x4b7100:
        m2_tgpx4_decode_move(c->record, c->state, record, r, native_operands);
        break;
    case 0x4b7440:
        m2_tgpx4_decode_parallel(c->record, c->state, record, r, native_operands);
        break;
    default:
        abort(); /* Internal dispatch invariant; never substitute a no-op. */
    }
}

void m2_tgpx4_decode_native(uint32_t low, uint32_t high, uint32_t record_token,
    uint32_t state_token, uint32_t *record, uint32_t *previous,
    m2_tgpx4_decode_registers *registers)
{
    decode_context context = { record_token, state_token };
    m2_tgpx4_decode_instruction(low, high, record, previous, registers,
                              subdecode, &context);
}

typedef struct {
    m2_tgpx4_program *program;
    const m2_tgpx4_program_memory *memory;
    m2_tgpx4_decode_registers registers;
    uint32_t state;
} load_context;

static void release(void *opaque, uint32_t token)
{
    load_context *c = opaque;
    c->memory->release(c->memory->opaque, token);
}

static uint32_t *allocate(void *opaque, uint32_t bytes, uint32_t *token)
{
    load_context *c = opaque;
    return c->memory->allocate(c->memory->opaque, bytes, token);
}

static void decode(void *opaque, uint32_t low, uint32_t high, uint32_t *record)
{
    load_context *c = opaque;
    const m2_tgpx4_program *p = c->program;
    uint32_t *previous = p->active_record == p->active_base ? NULL
        : record - M2_TGPX4_RECORD_BYTES / sizeof(*record);
    m2_tgpx4_decode_native(low, high, p->active_record, c->state,
                          record, previous, &c->registers);
}

void m2_tgpx4_load_program(m2_tgpx4_program *program, const uint8_t *source,
    uint32_t bytes, uint32_t state_token, const m2_tgpx4_program_memory *memory,
    const m2_tgpx4_registration *registration)
{
    load_context context = { program, memory, { 0 }, state_token };
    const m2_tgpx4_program_hooks hooks = { &context, release, allocate, decode };
    m2_tgpx4_prepare_program(program, source, bytes, state_token, &hooks, registration);
}

typedef struct { uint32_t *words, token; } validation_memory;
static uint32_t *validation_allocate(void *opaque, uint32_t bytes, uint32_t *token)
{
    validation_memory *m = opaque;
    (void)bytes; *token = m->token; return m->words + 0x2c / 4;
}

bool m2_tgpx4_program_matches(const uint8_t *source, const void *records,
    uint32_t count, uint32_t state_token, uint32_t program_token)
{
    if (count > 0x40000u / 8u) return false;
    const size_t bytes = (size_t)count * M2_TGPX4_RECORD_BYTES;
    uint32_t *copy = malloc(bytes + 0x2c);
    if (!copy) return false;
    memset(copy, 0, 0x2c);
    memcpy(copy + 0x2c / 4, records, bytes);
    validation_memory context = { copy, program_token };
    const m2_tgpx4_program_memory memory = { &context, NULL, validation_allocate };
    m2_tgpx4_program program = { { 0 }, 0, 0, 0 };
    m2_tgpx4_load_program(&program, source, count * 8u, state_token, &memory, NULL);
    const bool matches = !memcmp(copy + 0x2c / 4, records, bytes);
    free(copy);
    return matches;
}
