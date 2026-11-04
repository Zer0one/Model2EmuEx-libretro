#ifndef M2_TGPX4_GEOMETRY_H
#define M2_TGPX4_GEOMETRY_H
#include <stdbool.h>
#include <stdint.h>

/* Native geometry-control globals, separate from the CPU register file.
 * Matrix words are copied bit-for-bit, including NaNs and signed zero.
 * list_position is the native byte pointer, not a word index. */
typedef struct {
    uint32_t primary[16];       /* 010f00a8 */
    uint32_t alternate[16];     /* 010f0068 */
    uint32_t list_position;     /* 01003018 */
    uint32_t special_object;    /* 00dcec08 */
} m2_tgpx4_geometry_control;

/* Recovered Top Skater overrides only. 004bc040 stops at its tail transfer
 * to common object handler 004bb280; this does not emulate that handler.
 * The caller supplies twelve words for 004ba010; other entries ignore input.
 * Native transient x86 registers/flags are not part of this normalized API.
 * The shared renderer uses these matrix operations with the separately
 * recovered special polygon grammar; no common object-handler claim here. */
bool m2_tgpx4_geometry_command(m2_tgpx4_geometry_control *state,
    uint32_t entry, const uint32_t *input);
uint32_t m2_tgpx4_geometry_center(uint32_t command, uint32_t native_mode);
#endif
