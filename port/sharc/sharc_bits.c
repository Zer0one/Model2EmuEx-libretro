#include "sharc_bits.h"

uint32_t m2_sharc_extend_immediate(uint32_t value, uint8_t encoded_width)
{
    uint32_t width = encoded_width;
    uint32_t sign = UINT32_C(1) << ((width - UINT32_C(1)) & 31u);
    uint32_t mask = (UINT32_C(1) << (width & 31u)) - UINT32_C(1);

    return (value & sign) ? (value | ~mask) : (value & mask);
}

static uint32_t field_mask(uint32_t control)
{
    return (UINT32_C(1) << ((control >> 6) & 31u)) - UINT32_C(1);
}

static void set_field_zero(uint32_t field, uint32_t *status)
{
    *status = (*status & ~UINT32_C(0x1000)) |
              (field == 0 ? UINT32_C(0x1000) : UINT32_C(0));
}

/* 0x004bc420, 0x004bc510 and 0x004bc5b0. */
uint32_t m2_sharc_field_deposit(uint32_t value, uint32_t control, uint32_t *status)
{
    uint32_t field = value & field_mask(control);
    set_field_zero(field, status);
    return field << (control & 31u);
}

/* 0x004bc470 returns EAX despite the raw decompile's void signature. */
uint32_t m2_sharc_field_extract(uint32_t value, uint32_t control, uint32_t *status)
{
    uint32_t field = (value >> (control & 31u)) & field_mask(control);
    set_field_zero(field, status);
    return field;
}

uint32_t m2_sharc_field_merge(uint32_t value, const uint32_t *base,
                             uint32_t control, uint32_t *status)
{
    uint32_t field = m2_sharc_field_deposit(value, control, status);
    return field | *base;
}
