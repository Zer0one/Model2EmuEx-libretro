#ifndef M2_TGPX4_FP_H
#define M2_TGPX4_FP_H
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint16_t control, status;
    /* Native MSVC CRT flag at 010f1fec, selected at process startup. Both
     * paths are retained: SSE2 converts to int32, legacy returns int64 low. */
    uint32_t crt_sse2;
} m2_tgpx4_fp_state;

/* Scalar numerical bodies. first/second retain native operand-reader order,
 * including second-minus-first. Status is the guest status word at +0x110.
 * This does not yet dispatch the instruction's indirect operand callbacks.
 * Masked x87 exceptions and an initially empty x87 stack are required, as in
 * the native execution loop. Arithmetic requires its PC=24 setting. */
bool m2_tgpx4_fp_operation(uint32_t entry, uint32_t first, uint32_t second,
    uint32_t *status, m2_tgpx4_fp_state *fp, uint32_t *result);

/* Same numerical body with the pre-clamp integer needed to reproduce native
 * EDX on return from 004b53b0. Other operations leave scratch unchanged. */
bool m2_tgpx4_fp_operation_details(uint32_t entry, uint32_t first, uint32_t second,
    uint32_t *status, m2_tgpx4_fp_state *fp, uint32_t *result, uint32_t *scratch);
#endif
