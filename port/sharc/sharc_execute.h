#ifndef M2_SHARC_EXECUTE_H
#define M2_SHARC_EXECUTE_H
#include <stdint.h>

/* Experimental execution state, not a Save State/on-disk layout. Addresses
 * and callback bindings are original 32-bit virtual tokens, never host pointers.
 * state preserves the original 0x2a4-byte word layout. Stack indices must map to
 * valid state words after wrapping original byte-offset arithmetic.
 * fp_control records the original x87 control word; floating-point execution
 * and host fenv configuration are NOT provided by this integer scheduler.
 */
typedef struct m2_sharc_execution {
    uint32_t state[169];
    uint32_t budget, event_delay, event_count, stop, in_delay;
    uint32_t current_record, saved_record, program_base, active_base;
    uint32_t read_binding, write_binding, active_read, active_write, fp_control;
} m2_sharc_execution;

typedef void (*m2_sharc_dispatch_hook)(void *opaque, m2_sharc_execution *s,
                                      uint32_t record, uint32_t entry_eflags);
typedef void (*m2_sharc_event_hook)(void *opaque, m2_sharc_execution *s,
                                   uint32_t index, uint32_t entry_eflags);
typedef struct m2_sharc_execution_hooks {
    m2_sharc_dispatch_hook dispatch;
    m2_sharc_event_hook event;
    void *opaque;
} m2_sharc_execution_hooks;

/* Hooks resolve current virtual tokens/indexes and may mutate execution state.
 * They must honor the original handler ABI and valid stack/record invariants.
 * These routines intentionally have no added watchdog, stop-before-slot check
 * or saturating counter; callers must provide terminating work as appropriate.
 */
void m2_sharc_events(m2_sharc_execution *s, const m2_sharc_execution_hooks *h); /* 4bcf70 */
void m2_sharc_delay_slots(m2_sharc_execution *s, const m2_sharc_execution_hooks *h); /* 4bdfa0 */
void m2_sharc_run_bounded(m2_sharc_execution *s, const m2_sharc_execution_hooks *h); /* 4bd000 */
void m2_sharc_run_continuous(m2_sharc_execution *s, const m2_sharc_execution_hooks *h); /* 4be000 */
#endif
