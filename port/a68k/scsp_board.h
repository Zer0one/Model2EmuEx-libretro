#ifndef M2_A68K_SCSP_BOARD_H
#define M2_A68K_SCSP_BOARD_H
#include "scsp_bus.h"

typedef struct a68k_scsp_board a68k_scsp_board;

a68k_scsp_board *a68k_board_create(uint8_t *ram, scsp *chip,
    const uint8_t *program, unsigned program_size, const uint8_t *samples, unsigned sample_size, int original_divs);
void a68k_board_roms(a68k_scsp_board *b, const uint8_t *program, unsigned program_size,
                     const uint8_t *samples, unsigned sample_size);
uint32_t a68k_board_pc(const a68k_scsp_board *b);
void a68k_board_trace_command(const a68k_scsp_board *b, uint8_t command);
void a68k_board_scanline(a68k_scsp_board *b, unsigned hz);
void a68k_board_irq(a68k_scsp_board *b, unsigned level, int asserted);
void a68k_board_reset(a68k_scsp_board *b);
int a68k_board_error(const a68k_scsp_board *b, char *text, size_t size);
void a68k_board_archive(a68k_scsp_board *b, m2_state *archive);
#endif
