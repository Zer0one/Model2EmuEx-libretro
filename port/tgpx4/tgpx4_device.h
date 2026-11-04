#ifndef M2_TGPX4_DEVICE_H
#define M2_TGPX4_DEVICE_H

#include "tgpx4_loader.h"
#include "tgpx4_driver.h"

/* Frontend-neutral composition, following the SHARC device boundary. The
 * machine owns token mappings, FIFO/board buffers, allocation and diagnostics.
 * Its bus.call resolves external board/geometry callbacks or fails explicitly.
 * No fallback mapping, host-pointer conversion or guest RAM expansion occurs. */
typedef struct {
    m2_tgpx4_program program;
    m2_tgpx4_execution_registers registers;
    m2_tgpx4_execution_bus machine, bus;
    m2_tgpx4_program_memory memory;
    const m2_tgpx4_registration *registration;
} m2_tgpx4_device;

/* Populate machine/memory first; zero-initialize the device on creation. */
void m2_tgpx4_device_bind(m2_tgpx4_device *device);
void m2_tgpx4_device_load(m2_tgpx4_device *device, const uint8_t *source, uint32_t bytes);
void m2_tgpx4_device_initialize(m2_tgpx4_device *device, const char *native_game);
/* entry_stack is the original 32-bit ESP token at the selected scheduler's
 * entry, not a host stack address. Single-batch uses native 004b4660 semantics. */
void m2_tgpx4_device_run(m2_tgpx4_device *device, uint32_t entry_stack, bool single_batch);

#endif
