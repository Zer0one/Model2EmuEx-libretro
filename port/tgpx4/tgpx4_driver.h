#ifndef M2_TGPX4_DRIVER_H
#define M2_TGPX4_DRIVER_H

#include "tgpx4_execute.h"

typedef void (*m2_tgpx4_bootstrap)(void *opaque, uint32_t registration_list, uint32_t bytes);

/* 004c5c80: native Model 2C driver setup. The callback invokes the recovered
 * program builder; EDX/EAX forwards the native serializer-list token.
 * The program source itself is the global pointer at 005aa87c.
 * Geometry and FIFO addresses are native tokens on the execution bus. */
void m2_tgpx4_driver_initialize(const m2_tgpx4_execution_bus *bus,
    void *opaque, m2_tgpx4_bootstrap prepare, const char *game, uint32_t registration_list);

/* Includes the native geometry handoff; 004baa60 remains the existing shared
 * renderer, not a new geometry implementation. */
bool m2_tgpx4_driver_primitive(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

#endif
