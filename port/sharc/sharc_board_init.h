#ifndef M2_SHARC_BOARD_INIT_H
#define M2_SHARC_BOARD_INIT_H
#include "sharc_fp.h"
typedef struct {
    uint32_t astat,selected_state,stop,read_binding,write_binding;
    uint32_t offset_bits,scale_bits,mode,enabled,variant;
    uint32_t renderer_a8,renderer_b0,renderer_150,renderer_158;
} m2_sharc_board_configuration;
typedef void (*m2_sharc_board_reset_hook)(void *opaque,uint32_t bytes);
/* 004c6510 body. Reset hook is the native 004c0230 boundary and must complete
 * its machine/serializer work first (or propagate its non-returning failure).
 * Game identifiers are native ASCII names; comparisons use the CRT C-locale
 * case folding, not frontend/MAME aliases. Renderer defaults belong to caller. */
void m2_sharc_board_initialize(m2_sharc_board_configuration *config,const char *game,
    uint32_t fixed_state,m2_sharc_fp_state *fp,m2_sharc_board_reset_hook reset,void *opaque);
#endif
