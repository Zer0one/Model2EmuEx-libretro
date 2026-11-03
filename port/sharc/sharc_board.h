#ifndef M2_SHARC_BOARD_H
#define M2_SHARC_BOARD_H
#include <stdbool.h>
#include <stdint.h>
/* Original word-addressed bus. Memory buffers use explicit little endian;
 * FIFO words retain data[32], read index, write index, free count. Indices must
 * be in 0..31 on entry; counters wrap exactly as the native implementation.
 * All buffers/tokens are bound by the caller, not allocated by this layer. */
typedef struct {
    uint8_t *ram0,*ram1,*shared;
    const uint8_t *rom;
    uint32_t *input_fifo,*output_fifo,*astat;
    uint32_t active_state,fixed_state,stop;
} m2_sharc_board_bus;
uint32_t m2_sharc_board_read(m2_sharc_board_bus *bus,uint32_t address);
void m2_sharc_board_write(m2_sharc_board_bus *bus,uint32_t address,uint32_t value);
/* Three game-selected renderer skip callbacks: only advance the stream token. */
bool m2_sharc_renderer_skip(uint32_t entry,uint32_t *cursor);
#endif
