#include "tgpx4_decode.h"
#include <stdbool.h>

void m2_tgpx4_decode_instruction(uint32_t low, uint32_t high, uint32_t *record,
    uint32_t *previous, m2_tgpx4_decode_registers *registers,
    m2_tgpx4_subdecode subdecode, void *opaque)
{
    static const uint32_t wrapper[] = {
        0x4b36e0, 0x4b3690, 0x4b3630, 0, 0x4b35e0, 0x4b35a0, 0x4b3560, 0x4b3550
    };
    static const uint32_t operation[] = {
        0x4b7440, 0x4b7100, 0x4b6730, 0, 0x4b6ef0, 0x4b6b90, 0x4b6730, 0x4b6ac0
    };
    const uint32_t instruction_class = high >> 29;
    const uint32_t saved_esi = registers->esi;
    registers->esi = low;
    registers->eax = instruction_class;
    record[0x90 / 4] = 0;
    /* Class 3 bypasses decode and keeps the allocator-provided wrapper. */
    if (instruction_class != 3) {
        record[0x80 / 4] = wrapper[instruction_class];
        if (instruction_class < 3) {
            registers->ecx = high;
            subdecode(opaque, 0x4b75d0, registers, record);
        } else if (instruction_class < 7) {
            registers->eax = high;
            subdecode(opaque, 0x4b76b0, registers, record);
            if (instruction_class < 6)
                registers->edx = high;
        } else {
            registers->ecx = high;
        }
        registers->eax = low;
        subdecode(opaque, operation[instruction_class], registers, record);
    }

    record[0x84 / 4] = record[0x00 / 4] == 0x4b5ef0u || record[0x04 / 4] == 0x4b5ef0u
        || record[0x14 / 4] == 0x4b5ef0u || record[0x18 / 4] == 0x4b5ef0u
        || record[0x28 / 4] == 0x4b5ef0u || record[0x44 / 4] == 0x4b5ef0u;
    record[0x88 / 4] = record[0x08 / 4] == 0x4b5df0u || record[0x1c / 4] == 0x4b5df0u
        || record[0x2c / 4] == 0x4b5df0u || record[0x48 / 4] == 0x4b5df0u;
    if (previous && previous[0x90 / 4]) {
        if (record[0x84 / 4])
            previous[0x84 / 4] = 1;
        if (record[0x88 / 4])
            previous[0x88 / 4] = 1;
    }
    registers->eax = 0x4b5df0u;
    registers->ecx = 1;
    registers->esi = saved_esi;
}

static void decode_alu(uint32_t high, uint32_t *record,
                       const uint32_t *operands, uint32_t operation)
{
    const unsigned selector = (high >> 24) & 31u;
    record[0] = operands[(high >> 20) & 15u];
    record[1] = operands[(selector < 16 ? 32 : 0) + ((high >> 15) & 31u)];
    record[2] = operands[128 + ((high >> 10) & 31u)];
    record[3] = operation;
    record[4] = high;
    if (operation == 0x4b5630u || operation == 0x4b65c0u
        || operation == 0x4b51e0u || operation == 0x4b38e0u)
        record[2] = 0x4b3b80u;
}

void m2_tgpx4_decode_operands(uint32_t entry, uint32_t record_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands, const uint32_t *alu)
{
    if (entry == 0x4b75d0u) {
        const uint32_t high = registers->ecx;
        const uint32_t low = registers->esi;
        const unsigned alternate = (high >> 9) & 1u;
        decode_alu(high, record, operands, alu[(high >> 24) & 31u]);
        record[5] = operands[64 + ((high >> 5) & 15u)];
        record[6] = operands[(alternate ? 96 : 64) + (high & 31u)];
        record[7] = operands[128 + (low >> 27)];
        record[8] = alternate ? 0x4b4e60u : 0x4b4df0u;
        record[9] = low;
        registers->eax = record_token;
        registers->ecx = record[7];
        registers->edx = alternate;
    } else if (entry == 0x4b76b0u) {
        const uint32_t high = registers->eax;
        registers->ecx = record_token;
        if (high & 0x200u) {
            const uint32_t operation = alu[(high >> 24) & 31u];
            decode_alu(high, record, operands, operation);
            registers->eax = operation;
            registers->edx = operation;
        } else {
            const unsigned selector = (high >> 24) & 31u;
            record[5] = operands[64 + ((high >> 20) & 15u)];
            record[6] = operands[(selector ? 96 : 64) + ((high >> 15) & 31u)];
            record[2] = operands[128 + ((high >> 10) & 31u)];
            record[3] = selector ? 0x4b4e60u : 0x4b4df0u;
            record[4] = high;
            registers->edx = selector;
        }
    }
}

void m2_tgpx4_decode_immediate(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands)
{
    const uint32_t low = registers->eax;
    const unsigned operation = (low >> 19) & 127u;
    record[0x60 / 4] = (registers->ecx << 5) | (low >> 27);
    registers->ecx = record_token;
    registers->edx = operation;
    if (operation < 0x40) {
        registers->eax = operands[352 + operation];
        record[0x2c / 4] = registers->eax;
    } else if (operation <= 0x67) {
        const bool alternate = operation > 0x47;
        const unsigned offset = alternate ? 0x4c / 4 : 0x30 / 4;
        record[0x2c / 4] = alternate ? 0x4b5dc0u : 0x4b66d0u;
        record[offset] = operands[(alternate ? 464 : 448) + (low & 15u)];
        record[offset + 1] = state_token + 0x80u + 4u * (operation & 7u);
        registers->edx = state_token + 0x80u + 4u * ((low >> 4) & 7u);
        registers->eax = (low >> 7) & 0xfffu;
        record[offset + 3] = registers->edx;
        record[offset + 4] = registers->eax;
    }
}

void m2_tgpx4_decode_transfers(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands)
{
    const uint32_t low = registers->eax;
    const uint32_t high = registers->edx;
    const unsigned first = (high >> 6) & 3u;
    const unsigned second = (low >> 18) & 3u;
    const uint32_t state_registers = state_token + 0x80u;
    registers->ecx = record_token;
    if (first == 0) {
        record[0x28 / 4] = operands[160 + ((high >> 1) & 31u)];
        record[0x2c / 4] = operands[288 + ((high & 1u) << 4) + (low >> 28)];
        registers->edx = record[0x2c / 4];
    } else if (first < 3) {
        const uint32_t operand = (high >> 1) & 31u;
        record[0x28 / 4] = first == 1 ? operands[160 + operand] : 0x4b6700u;
        record[0x2c / 4] = first == 1 ? 0x4b66d0u : operands[288 + operand];
        record[0x30 / 4] = operands[416 + ((low >> 20) & 15u)];
        record[0x34 / 4] = state_registers + 4u * (((high & 1u) << 2) | (low >> 30));
        record[0x3c / 4] = state_registers + 4u * ((low >> 27) & 7u);
        registers->edx = record[0x40 / 4] = (low >> 24) & 7u;
    }

    const uint32_t operand = (low >> 13) & 31u;
    if (second == 0) {
        registers->edx = record[0x44 / 4] = operands[192 + operand];
        registers->eax = record[0x48 / 4] = operands[320 + ((low >> 8) & 15u)];
    } else if (second < 3) {
        record[0x44 / 4] = second == 1 ? operands[192 + operand] : 0x4b5eb0u;
        record[0x48 / 4] = second == 1 ? 0x4b5dc0u : operands[320 + operand];
        record[0x4c / 4] = operands[432 + (low & 15u)];
        record[0x50 / 4] = state_registers + 4u * ((low >> 10) & 7u);
        registers->edx = record[0x58 / 4] = state_registers + 4u * ((low >> 7) & 7u);
        registers->eax = record[0x5c / 4] = (low >> 4) & 7u;
    }
}

void m2_tgpx4_decode_parallel(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands)
{
    const uint32_t low = registers->eax;
    const unsigned mode = (low >> 24) & 3u;
    if (mode == 3) {
        registers->ecx = 1;
        return;
    }

    registers->ecx = record_token;
    const unsigned source = (low >> 20) & 31u;
    const unsigned transfer = (low >> 10) & (mode ? 15u : 31u);
    record[0x28 / 4] = mode == 2 ? 0x4b6700u : operands[160 + source];
    record[0x44 / 4] = mode == 2 ? 0x4b5eb0u : operands[192 + transfer];
    if (!mode) {
        record[0x2c / 4] = operands[288 + ((low >> 15) & 31u)];
        registers->edx = record[0x44 / 4];
        registers->eax = record[0x48 / 4] = operands[320 + ((low >> 5) & 31u)];
        return;
    }

    const uint32_t state_registers = state_token + 0x80u;
    record[0x2c / 4] = mode == 2 ? operands[288 + source] : 0x4b66d0u;
    record[0x30 / 4] = operands[416 + (low & 15u)];
    record[0x34 / 4] = state_registers + 4u * ((low >> 17) & 7u);
    record[0x3c / 4] = state_registers + 4u * ((low >> 14) & 7u);
    record[0x48 / 4] = mode == 2 ? operands[320 + transfer] : 0x4b5dc0u;
    record[0x4c / 4] = operands[432 + (low & 15u)];
    registers->edx = record[0x50 / 4] = state_registers + 4u * ((low >> 7) & 7u);
    registers->eax = record[0x58 / 4] = state_registers + 4u * ((low >> 4) & 7u);
}

static uint32_t move_source(uint32_t low, unsigned selector, uint32_t base,
    uint32_t *record, const uint32_t *operands, uint32_t increment_mask,
    uint32_t immediate_mask, uint32_t memory_reader)
{
    const uint32_t index = base + 4u * (selector & 7u);
    const uint32_t modifier = base + 4u * ((low >> 4) & 7u);
    const uint32_t increment = (low >> 7) & increment_mask;
    if (selector < 0x40)
        return record[0x28 / 4] = operands[224 + selector];
    if (selector < 0x48) {
        record[0x28 / 4] = memory_reader;
        record[0x30 / 4] = operands[448 + (low & 15u)];
        record[0x34 / 4] = index;
        record[0x3c / 4] = modifier;
        return record[0x40 / 4] = increment;
    }
    if (selector == 0x58) {
        record[0x28 / 4] = 0x4b3fa0u;
        return record[0x60 / 4] = low & immediate_mask;
    }
    if (selector < 0x68) {
        record[0x28 / 4] = 0x4b5eb0u;
        record[0x4c / 4] = operands[464 + (low & 15u)];
        record[0x50 / 4] = index;
        record[0x58 / 4] = modifier;
        return record[0x5c / 4] = increment;
    }
    return selector;
}

static void move_destination(uint32_t low, unsigned selector, uint32_t base,
    uint32_t *record, m2_tgpx4_decode_registers *registers, const uint32_t *operands,
    bool port, uint32_t increment_mask)
{
    const uint32_t index = base + 4u * (selector & 7u);
    const uint32_t modifier = base + 4u * ((low >> 4) & 7u);
    const uint32_t increment = (low >> 7) & increment_mask;
    if (selector < 0x40) {
        registers->eax = record[0x2c / 4] = operands[352 + selector];
    } else if (selector < 0x48) {
        record[0x2c / 4] = port ? 0x4b5d90u : 0x4b66a0u;
        record[0x30 / 4] = operands[448 + (low & 15u)];
        record[0x38 / 4] = index;
        registers->edx = record[0x3c / 4] = modifier;
        registers->eax = record[0x40 / 4] = increment;
    } else if (selector != 0x58 && selector < 0x68) {
        record[0x2c / 4] = 0x4b5d60u;
        record[0x4c / 4] = operands[464 + (low & 15u)];
        record[0x54 / 4] = index;
        registers->edx = record[0x58 / 4] = modifier;
        registers->eax = record[0x5c / 4] = increment;
    }
}

void m2_tgpx4_decode_move(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands)
{
    const uint32_t low = registers->eax;
    const unsigned source = (low >> 19) & 127u;
    const unsigned destination = (low >> 12) & 127u;
    const uint32_t base = state_token + 0x80u;
    registers->ecx = record_token;
    if (!(low & 0x04000000u)) {
        registers->edx = move_source(low, source, base, record, operands, 31, 0xfff, 0x4b6700);
        move_destination(low, destination, base, record, registers, operands, false, 31);
    } else if (!(low & 0x02000000u)) {
        registers->edx = move_source(low, destination, base, record, operands, 31, 0xfff, 0x4b6700);
        record[0x2c / 4] = 0x4b5d00u;
        registers->eax = record[0x64 / 4] = source & 63u;
    } else {
        record[0x28 / 4] = 0x4b5e50u;
        record[0x64 / 4] = source & 63u;
        registers->edx = destination;
        move_destination(low, destination, base, record, registers, operands, true, 31);
    }
}

void m2_tgpx4_decode_wide_move(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands)
{
    const uint32_t low = registers->eax, high = registers->edx;
    const unsigned destination = (low >> 24) & 127u;
    const uint32_t base = state_token + 0x80u;
    registers->ecx = record_token;
    /* Unlike 004b7100, this class takes the source/port selector from EDX and
     * the sign bit of EAX. Its offsets are 14 bits and immediates 24 bits.
     * The memory-to-port path deliberately binds 004b5ed0, not 004b6700. */
    if (!(high & 0x40u)) {
        const unsigned source = ((high & 63u) << 1) | (low >> 31);
        registers->edx = move_source(low, source, base, record, operands,
                                     0x3fff, 0xffffff, 0x4b6700);
        move_destination(low, destination, base, record, registers, operands, false, 0x3fff);
    } else {
        const unsigned port = ((high & 31u) << 1) | (low >> 31);
        if (!(high & 0x20u)) {
            move_source(low, destination, base, record, operands,
                        0x3fff, 0xffffff, 0x4b5ed0);
            record[0x2c / 4] = 0x4b5d00u;
            registers->edx = record[0x64 / 4] = port;
        } else {
            record[0x28 / 4] = 0x4b5e50u;
            registers->edx = record[0x64 / 4] = port;
            move_destination(low, destination, base, record, registers, operands, true, 0x3fff);
        }
    }
}

void m2_tgpx4_decode_register_address(uint32_t entry, uint32_t state_token,
    m2_tgpx4_decode_registers *registers)
{
    const uint32_t selector = registers->eax;
    if (selector < 8)
        registers->ecx = state_token;
    else
        registers->edx = state_token;
    registers->eax = state_token + (entry == 0x4b3b20u ? 0x40u : 0)
        + (selector < 8 ? 0 : 0x20u) + (selector & 7u) * 4u;
}

void m2_tgpx4_decode_target(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers)
{
    static const uint32_t target[] = {
        0x4b3880, 0x4b3860, 0x4b3850, 0x4b3830,
        0x4b3850, 0x4b3830, 0x4b3850, 0x4b3830,
        0x4b4dd0, 0x4b4da0, 0x4b4d80, 0x4b4d50,
        0x4b4d30, 0x4b4d00, 0x4b4ce0, 0x4b4cb0
    };
    const uint32_t low = registers->eax;
    const unsigned mode = (low >> 12) & 15u;
    record[0x7c / 4] = target[mode];
    registers->ecx = record_token;
    if (mode < 2 || (mode >= 8 && mode < 12)) {
        registers->eax = record[0x70 / 4] = low & (mode < 2 ? 0xfffu : 0x3ffu);
    } else if (mode >= 4 && mode < 8) {
        /* 004b6280 leaves ECX as the mode before the address-helper call.
         * Only one of ECX/EDX is overwritten by that helper. */
        registers->ecx = mode;
        registers->eax = ((low >> 6) & 7u) + ((low & 0x800u) ? 8u : 0);
        m2_tgpx4_decode_register_address(mode < 6 ? 0x4b3b50u : 0x4b3b20u,
                                         state_token, registers);
        record[0x74 / 4] = registers->eax;
    } else {
        registers->edx = state_token;
        registers->eax = record[0x74 / 4] = state_token + 0x80u + ((low >> 6) & 7u) * 4u;
    }
}

void m2_tgpx4_decode_control(uint32_t record_token, uint32_t state_token, uint32_t *record,
    m2_tgpx4_decode_registers *registers, const uint32_t *operands, const uint32_t *conditions)
{
    const uint32_t low = registers->eax;
    const unsigned operation = (low >> 22) & 31u, condition = (low >> 16) & 63u;
    /* ECX is rebuilt from EAX at 004b6732. It does not inherit the previous
     * subdecoder's value; retain the exact exit registers for future review. */
    registers->ecx = low >> 16;
    registers->edx = low & 0xffffu;
    switch (operation) {
    case 0:
        registers->eax = record_token;
        record[0x68 / 4] = 0x4b3820;
        return;
    case 1: case 2:
        registers->eax = record_token;
        registers->ecx = record_token + 0x70u;
        record[0x68 / 4] = operation == 1 ? 0x4b37e0 : 0x4b37b0;
        record[0x70 / 4] = registers->edx;
        if (condition == 63) {
            registers->ecx = state_token;
            registers->edx = state_token + 0x80u + ((low >> 13) & 7u) * 4u;
            record[0x74 / 4] = registers->edx;
        } else {
            record[0x74 / 4] = registers->ecx;
        }
        return;
    case 3:
        registers->eax = record_token;
        record[0x70 / 4] = condition;
        record[0x68 / 4] = 0x4b37a0;
        return;
    case 4: case 5:
        registers->eax = record_token;
        registers->edx = (low >> 6) & 63u;
        record[0x68 / 4] = operation == 4 ? 0x4b4c80 : 0x4b4c40;
        if (operation == 4)
            registers->ecx = record[0x6c / 4] = operands[224 + registers->edx];
        else
            registers->edx = record[0x6c / 4] = operands[352 + registers->edx];
        return;
    case 8: case 9: case 10: case 11: case 12: case 13: {
        static const uint32_t masks[] = {0xffff, 0x7000, 0xe00, 0x80, 0x10, 7};
        registers->eax = record_token;
        record[0x68 / 4] = 0x4b3770;
        record[0x70 / 4] = registers->edx;
        record[0x78 / 4] = masks[operation - 8];
        return;
    }
    case 16: case 17: case 24: case 25:
        registers->edx = record[0x6c / 4] = conditions[condition];
        record[0x68 / 4] = operation == 16 ? (condition == 63 ? 0x4b3760 : 0x4b4bf0)
            : operation == 17 ? (condition == 63 ? 0x4b3750 : 0x4b4ba0)
            : operation == 24 ? 0x4b49e0 : 0x4b4970;
        break;
    case 18: case 26:
        record[0x68 / 4] = operation == 18 ? 0x4b4b60 : 0x4b4910;
        break;
    case 19:
        registers->ecx = record_token;
        registers->eax = record[0x70 / 4] = low & 0xfffu;
        record[0x68 / 4] = 0x4b4af0;
        record[0x90 / 4] = 1;
        return;
    case 20: case 21:
        registers->edx = record_token;
        registers->ecx &= 15u;
        registers->eax = record[0x6c / 4] = 1u << registers->ecx;
        record[0x68 / 4] = operation == 20 ? 0x4b4aa0 : 0x4b4a50;
        record[0x70 / 4] = low & 0xfffu;
        record[0x74 / 4] = state_token + 0x80u + ((low >> 13) & 7u) * 4u;
        record[0x90 / 4] = 1;
        return;
    case 27:
        registers->eax = record_token;
        record[0x68 / 4] = 0x4b48c0;
        record[0x90 / 4] = 1;
        return;
    default:
        return;
    }
    record[0x90 / 4] = 1;
    m2_tgpx4_decode_target(record_token, state_token, record, registers);
}
