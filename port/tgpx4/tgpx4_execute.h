#ifndef M2_TGPX4_EXECUTE_H
#define M2_TGPX4_EXECUTE_H

#include <stdint.h>
#include <stdbool.h>

/* Native x86 tokens remain explicit across machine integration. The bus maps
 * state, decoded records, FIFO counters and deferred queues; it never treats
 * a 32-bit token as a host pointer. Callbacks preserve the native nonvolatile
 * registers and may change the bus and all scratch registers below. */
typedef struct {
    uint32_t eax, ecx, edx, flags;
    uint32_t ebx, ebp, esi, edi;
    uint16_t fp_control, fp_status;
    /* Original entry ESP token. Independent of the host C stack. */
    uint32_t esp;
} m2_tgpx4_execution_registers;

typedef struct {
    void *opaque;
    uint32_t (*read)(void *opaque, uint32_t address, unsigned bits);
    void (*write)(void *opaque, uint32_t address, uint32_t value, unsigned bits);
    void (*call)(void *opaque, uint32_t entry, m2_tgpx4_execution_registers *registers);
} m2_tgpx4_execution_bus;

/* 004b6010: run until the original stop/FIFO condition. There is no added cycle
 * budget. This sets the emulated x87 control token, not the host FP environment.
 * Arithmetic handlers implement its precision/rounding semantics explicitly.
 * Scratch exit FLAGS are unspecified (the original stack epilogue changes
 * them); callback-entry arithmetic flags are preserved explicitly. */
void m2_tgpx4_execute(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* 004b4660: one native batch, with unconditional binding and ECX count output. */
void m2_tgpx4_execute_batch(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* Seven execution wrappers, 004b3550..004b36e0. Indirect arithmetic/transfer
 * callbacks remain separate; the wrappers preserve original call ordering. */
void m2_tgpx4_execute_wrapper(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* Recovered register/immediate/control primitives; false means unimplemented,
 * never an implicit no-op. Floating-point primitives are not included here. */
bool m2_tgpx4_execute_register(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

bool m2_tgpx4_execute_control(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* 004b44d0 takes two stack arguments; the operation token arrives in EDX. */
void m2_tgpx4_enqueue_write(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers, uint32_t address, uint32_t value);

bool m2_tgpx4_execute_integer(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

bool m2_tgpx4_execute_address(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

bool m2_tgpx4_execute_transfer(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* Native FP callback ABI, including stack-derived entry/exit FLAGS. The stack
 * argument is the original x86 entry ESP token, never a host pointer. No host
 * stack memory is accessed. Numerical kernels are qualified separately. */
bool m2_tgpx4_execute_fp(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers, uint32_t stack);

/* Resolve a recovered CPU callback, including wrappers and FP. Board callbacks
 * remain the caller's responsibility; false is never an implicit no-op. */
bool m2_tgpx4_dispatch(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

/* 004c5a70/004c5a90 CPU-facing external-memory ABI, including scratch FLAGS
 * and the native pointer tokens returned in EAX/EDX. */
bool m2_tgpx4_execute_board_memory(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *registers);

#endif
