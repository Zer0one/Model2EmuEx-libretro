#ifndef M2_A68K_MODEL1_BOARD_H
#define M2_A68K_MODEL1_BOARD_H
#include "model1_bus.h"

typedef struct a68k_m1_board a68k_m1_board;
a68k_m1_board *a68k_m1_create(uint8_t *ram,const uint8_t *program,size_t prog_size,
                              const uint8_t *samples,size_t size,int original_divs);
void a68k_m1_free(a68k_m1_board *b);
void a68k_m1_reset(a68k_m1_board *b);
void a68k_m1_command(a68k_m1_board *b,uint8_t command);
void a68k_m1_scanline(a68k_m1_board *b);
int a68k_m1_begin(a68k_m1_board *b,unsigned frames);
int a68k_m1_output_frames(a68k_m1_board *b,unsigned frames);
void a68k_m1_finish(a68k_m1_board *b,int16_t *out,const unsigned gain[4]);
int a68k_m1_error(const a68k_m1_board *b,char *text,size_t size);
void a68k_m1_archive(a68k_m1_board *b,m2_state *a);
#endif
