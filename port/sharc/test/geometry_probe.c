/* Diagnostic only: compile the portable geometry helpers, an independent x87
 * oracle, or the Model 2B path for the observed 53-bit mode.
 * Records are 17 little-endian uint32 words: point flag, CW, matrix[12], xyz[3].
 * The original 4b9cb0/4b9df0 multiply y then x, add them, then add z (and
 * translation for points). Finite inputs only; this is not a full renderer.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#ifdef GEOMETRY_BINARY64_CANDIDATE
#define M2_ENABLE_SHARC
#ifndef GEOMETRY_BOARD_TYPE
#define GEOMETRY_BOARD_TYPE 2
#endif
#endif
#ifndef GEOMETRY_X87_ORACLE
#include "../../m2/m2geo.c"
#endif

int main(void)
{
    uint32_t words[17];
    while (fread(words, sizeof(words), 1, stdin) == 1) {
        float m[12], p[3], out[3];
        memcpy(m, words + 2, sizeof(m));
        memcpy(p, words + 14, sizeof(p));
#ifdef GEOMETRY_X87_ORACLE
        uint16_t cw = (uint16_t)words[1];
        __asm__ volatile("fninit; fldcw %0" :: "m"(cw) : "memory");
        for (int i = 0; i < 3; ++i) {
            __asm__ volatile(
                "flds %0; fmuls %1; flds %2; fmuls %3; faddp; "
                "flds %4; fmuls %5; faddp"
                :: "m"(p[1]), "m"(m[i+3]), "m"(p[0]), "m"(m[i]),
                   "m"(p[2]), "m"(m[i+6]) : "st", "memory");
            if (words[0])
                __asm__ volatile("fadds %0" :: "m"(m[i+9]) : "st", "memory");
            __asm__ volatile("fstps %0" : "=m"(out[i]) :: "st", "memory");
        }
#else
        static m2_geo geo;
#ifdef GEOMETRY_BINARY64_CANDIDATE
        static const m2_board test_board = {.type = GEOMETRY_BOARD_TYPE};
        const m2_board *board = &test_board;
#else
        const m2_board *board = NULL;
#endif
        memcpy(geo.matrix, m, sizeof(m));
        if (words[0]) {
            pvert v = {p[0], p[1], p[2], 0, 0};
            xform_point(&geo, board, &v);
            out[0] = v.x; out[1] = v.y; out[2] = v.z;
        } else {
            m2_vec3 v = {p[0], p[1], p[2]};
            v = xform_vec(&geo, board, v);
            out[0] = v.x; out[1] = v.y; out[2] = v.z;
        }
#endif
        if (fwrite(out, sizeof(out), 1, stdout) != 1) return 2;
    }
    return ferror(stdin) ? 1 : 0;
}
