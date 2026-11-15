#ifndef M2_DSB_BOARD_H
#define M2_DSB_BOARD_H

#include "dsb_original.h"
#include "../state.h"

typedef struct m2_dsb_board m2_dsb_board;
m2_dsb_board *m2_dsb_board_create(unsigned kind, const uint8_t *program, size_t program_size,
                                  const uint8_t *music, size_t music_size);
void m2_dsb_board_command(m2_dsb_board *b, uint8_t byte);
void m2_dsb_board_mix(m2_dsb_board *b, int16_t *stereo, size_t frames);
const char *m2_dsb_board_error(const m2_dsb_board *b, uint32_t *position);
void m2_dsb_board_archive(m2_dsb_board *b, m2_state *archive);
#endif
