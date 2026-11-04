#ifndef M2_TGPX4_DECODE_H
#define M2_TGPX4_DECODE_H

#include <stdint.h>

typedef struct {
    uint32_t eax, ecx, edx, esi;
} m2_tgpx4_decode_registers;

/* Internal subdecoder ABI. Some helpers use caller-saved registers left by a
 * previous helper. The class dispatcher forwards untouched inputs exactly. */
typedef void (*m2_tgpx4_subdecode)(void *opaque, uint32_t entry,
    m2_tgpx4_decode_registers *registers, uint32_t *record);

/* 004b77a0. Supply the preceding record only after the first instruction. */
void m2_tgpx4_decode_instruction(uint32_t low, uint32_t high, uint32_t *record,
    uint32_t *previous, m2_tgpx4_decode_registers *registers,
    m2_tgpx4_subdecode subdecode, void *opaque);

/* 004b75d0 and 004b76b0 share the original operand and ALU token tables.
 * The record token is the x86 address returned in a caller-saved register. */
void m2_tgpx4_decode_operands(uint32_t entry, uint32_t record_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands, const uint32_t *alu);

/* 004b6ac0: bind a control/immediate operation against the current state. */
void m2_tgpx4_decode_immediate(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands);

/* 004b6ef0: bind the two transfer lanes of class 4. */
void m2_tgpx4_decode_transfers(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands);

/* 004b7440: bind the two transfer lanes of class 0. */
void m2_tgpx4_decode_parallel(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands);

/* 004b7100: bind class 1 transfers and immediate ports. */
void m2_tgpx4_decode_move(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands);

/* 004b6b90: class 5, wide immediates and transfer offsets. */
void m2_tgpx4_decode_wide_move(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands);

/* 004b3b20/004b3b50: original state-register address selectors. */
void m2_tgpx4_decode_register_address(uint32_t entry, uint32_t state_token,
    m2_tgpx4_decode_registers *registers);

/* 004b6280: target-address subdecoder used by control operations. */
void m2_tgpx4_decode_target(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers);

/* 004b6730: classes 2/6, conditions and target-address dispatch. */
void m2_tgpx4_decode_control(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands, const uint32_t *conditions);

#endif
