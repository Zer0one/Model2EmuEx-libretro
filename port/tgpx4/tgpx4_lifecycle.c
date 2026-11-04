#include "tgpx4_lifecycle.h"
#include <string.h>

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

uint32_t m2_tgpx4_state_address(uint32_t *program, uint32_t state_address)
{
    /* 0x004b3470 clears the cached allocation token without freeing it. */
    *program = 0;
    return state_address;
}

void m2_tgpx4_bind_fifos(m2_tgpx4_bindings *bindings, uint32_t input, uint32_t output)
{
    /* 0x004b3480 snapshots both global FIFO pointers. */
    bindings->input_fifo = input;
    bindings->output_fifo = output;
}

void m2_tgpx4_bind_external(m2_tgpx4_bindings *bindings)
{
    /* 0x004b34a0 installs the original Model 2C board callbacks. */
    bindings->read_external = 0x004c5a90;
    bindings->write_external = 0x004c5a70;
}

void m2_tgpx4_setup_fp(uint16_t *control)
{
    /* 0x004b34c0 loads 003f. Reserved bit 6 reads back as one on x87. */
    *control = 0x007f;
}

void m2_tgpx4_reset_state(uint8_t *state)
{
    /* 0x004b3520 clears the CPU block and binds the record cursor to the
     * existing decoded program, without touching that allocation. */
    memset(state, 0, M2_TGPX4_STATE_BYTES);
    store_le32(state + M2_TGPX4_RECORD_OFFSET,
               load_le32(state + M2_TGPX4_PROGRAM_BASE_OFFSET));
}

void *m2_tgpx4_state_save(void *destination, const void *source, size_t bytes)
{
    return memcpy(destination, source, bytes); /* 0x004b34d0 */
}

void *m2_tgpx4_state_restore(void *destination, const void *source, size_t bytes)
{
    uint8_t *state = destination;
    memcpy(state, source, bytes); /* 0x004b34f0 */
    /* Native 32-bit arithmetic wraps. The registered 0x140-byte archive
     * leaves the decoded-program base in the destination's current session. */
    const uint32_t pc = load_le32(state + M2_TGPX4_PC_OFFSET);
    const uint32_t base = load_le32(state + M2_TGPX4_PROGRAM_BASE_OFFSET);
    store_le32(state + M2_TGPX4_RECORD_OFFSET, base + pc * M2_TGPX4_RECORD_BYTES);
    return destination;
}
