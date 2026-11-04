#include "tgpx4_program.h"
#include <stdlib.h>

static uint32_t load_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8
        | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void store_le32(uint8_t *p, uint32_t value)
{
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(value >> (8 * byte));
}

void m2_tgpx4_prepare_program(m2_tgpx4_program *program, const uint8_t *source,
    uint32_t bytes, uint32_t state_token, const m2_tgpx4_program_hooks *hooks,
    const m2_tgpx4_registration *registration)
{
    program->active_base = load_le32(program->state + M2_TGPX4_PROGRAM_BASE_OFFSET);
    if (registration && registration->list) {
        const m2_tgpx4_registration *r = registration;
        const m2_tgpx4_state_descriptor descriptor = {
            1, state_token, M2_TGPX4_STATE_BYTES, 0x004b34f0, 0x004b34d0, "TGPX4"
        };
        const uint32_t head = r->read(r->opaque, r->list);
        const uint32_t next = r->read(r->opaque, head + 4);
        const uint32_t node = r->create(r->opaque, head, next, &descriptor);
        const uint32_t count = r->read(r->opaque, r->list + 4);
        if (count == 0x0aaaaaa9u) {
            r->fatal(r->opaque, "list<T> too long");
            abort();
        }
        r->write(r->opaque, r->list + 4, count + 1);
        r->write(r->opaque, head + 4, node);
        r->write(r->opaque, r->read(r->opaque, node + 4), node);
    }

    if (program->active_base)
        hooks->release(hooks->opaque, program->active_base);
    const uint32_t count = bytes / 8u;
    program->active_state = state_token;
    uint32_t token;
    uint32_t *record = hooks->allocate(hooks->opaque, count * M2_TGPX4_RECORD_BYTES, &token);
    program->active_base = token;
    program->active_record = token;
    store_le32(program->state + M2_TGPX4_PROGRAM_BASE_OFFSET, token);
    for (uint32_t i = 0; i < count; ++i) {
        record[0x8c / 4] = i;
        hooks->decode(hooks->opaque, load_le32(source), load_le32(source + 4), record);
        if (record[0x0c / 4] == 0x004b38e0u && record[0x68 / 4] == 0x004b3820u
            && record[-0x2c / 4] == 0x004b37e0u)
            record[-0x2c / 4] = 0x004b3820u;
        record += M2_TGPX4_RECORD_BYTES / 4;
        source += 8;
        program->active_record += M2_TGPX4_RECORD_BYTES;
    }
    store_le32(program->state + M2_TGPX4_PROGRAM_BASE_OFFSET, program->active_base);
    m2_tgpx4_reset_state(program->state);
}
