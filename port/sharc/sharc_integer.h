#ifndef M2_SHARC_INTEGER_H
#define M2_SHARC_INTEGER_H

#include <stdbool.h>
#include <stdint.h>

/* Recovered integer compute selectors from original 0x004be800.
 * This is not the full instruction decoder. Supported selectors are listed
 * below; unsupported selectors return false without changing either output.
 * status and result must point to distinct writable words.
 *
 * entry_eflags is the original x86 helper-entry flag snapshot, NOT guest ASTAT
 * or the host compiler's flags. INC/DEC consume CF (bit 0); NOT consumes ZF/SF
 * (bits 6/7). Each dispatcher must reconstruct the original call path:
 * - 0x4bcb10/0x4bcb50: TEST of a true condition clears CF/ZF/SF/OF.
 * - 0x4bd810/0x4bd890/0x4bd910/0x4bd990: compute is on the false
 *   branch; TEST sets ZF/PF and clears CF/SF/OF.
 * - 0x4bddb0/0x4bde20/0x4bdea0/0x4bdf20: loads and pushes preserve
 *   handler-entry flags. sharc_flow.c recovers their outer-loop producers.
 * The first pair is in sharc_condition.c; the other eight integer wrappers
 * are in sharc_memory.c; sharc_execute.c supplies the execution scheduler.
 * Decoder/board integration and floating-point execution remain separate.
 * Supplying a fixed value across all paths is not an integrated solution.
 *
 * Preservation policy: these dependencies are intentional reconstructions of
 * ElSemi, not claims about physical SHARC behavior. Keep them even if computing
 * fresh flags looks more natural. See SHARC_RECONSTRUCTION.md for addresses,
 * differential witnesses and the boundary for any future accuracy review.
 * For example, with lhs=0 and ASTAT=0, original INC returns 1 with ASTAT=0
 * for entry EFLAGS=0x02, but ASTAT=8 for EFLAGS=0x03. NOT returns 0xffffffff
 * with ASTAT=0/1/4 for entry EFLAGS=0x02/0x42/0x82 respectively. Do not replace
 * these inputs with ASTAT carry or with flags recomputed from the C result.
 */
enum m2_sharc_integer_op {
    M2_SHARC_ADD = 0x01, M2_SHARC_SUB = 0x02,
    M2_SHARC_ADDC = 0x05, M2_SHARC_SUBC = 0x06,
    M2_SHARC_HALF_SUM = 0x09, M2_SHARC_COMPARE = 0x0a,
    M2_SHARC_PASS = 0x21, M2_SHARC_NEGATE = 0x22,
    M2_SHARC_INCREMENT_C = 0x25, M2_SHARC_DECREMENT_C = 0x26,
    M2_SHARC_INCREMENT = 0x29, M2_SHARC_DECREMENT = 0x2a,
    M2_SHARC_ABS = 0x30,
    M2_SHARC_AND = 0x40, M2_SHARC_OR = 0x41,
    M2_SHARC_XOR = 0x42, M2_SHARC_NOT = 0x43,
    M2_SHARC_MIN = 0x61, M2_SHARC_MAX = 0x62
};

bool m2_sharc_integer_supported(uint32_t operation);

bool m2_sharc_integer_compute(uint32_t operation, uint32_t lhs, uint32_t rhs,
                              uint32_t entry_eflags, uint32_t *status,
                              uint32_t *result);

#endif
