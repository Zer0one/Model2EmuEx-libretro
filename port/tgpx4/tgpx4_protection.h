#ifndef M2_TGPX4_PROTECTION_H
#define M2_TGPX4_PROTECTION_H
#include "tgpx4_execute.h"

/* Original 004c7330..004c75e0 protection handlers, normalized to physical
 * i960 access widths. Native scratch x86 registers/flags are not exported.
 * The bus supplies the original constant tables and mutable response globals;
 * this preserves ElSemi's responses, not a replacement hardware decryptor. */
uint32_t m2_tgpx4_protection_read(const m2_tgpx4_execution_bus *bus,
    uint32_t address, unsigned bits);
void m2_tgpx4_protection_write(const m2_tgpx4_execution_bus *bus,
    uint32_t address, uint32_t value, unsigned bits);
bool m2_tgpx4_protection_constant(uint32_t address, unsigned bits, uint32_t *value);
#endif
