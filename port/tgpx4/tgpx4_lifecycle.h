#ifndef M2_TGPX4_LIFECYCLE_H
#define M2_TGPX4_LIFECYCLE_H

#include <stddef.h>
#include <stdint.h>

enum {
    M2_TGPX4_STATE_BYTES = 0x140,
    M2_TGPX4_PC_OFFSET = 0x114,
    M2_TGPX4_PROGRAM_BASE_OFFSET = 0x140,
    M2_TGPX4_RECORD_OFFSET = 0x144,
    M2_TGPX4_RECORD_BYTES = 0x94,
};

/* These bindings represent original x86 addresses as 32-bit tokens. */
typedef struct {
    uint32_t input_fifo, output_fifo;
    uint32_t read_external, write_external;
} m2_tgpx4_bindings;

uint32_t m2_tgpx4_state_address(uint32_t *program, uint32_t state_address);
void m2_tgpx4_bind_fifos(m2_tgpx4_bindings *bindings, uint32_t input, uint32_t output);
void m2_tgpx4_bind_external(m2_tgpx4_bindings *bindings);
void m2_tgpx4_setup_fp(uint16_t *control);
void m2_tgpx4_reset_state(uint8_t *state);
void *m2_tgpx4_state_save(void *destination, const void *source, size_t bytes);
void *m2_tgpx4_state_restore(void *destination, const void *source, size_t bytes);

#endif
