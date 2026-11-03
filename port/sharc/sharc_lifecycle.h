#ifndef M2_SHARC_LIFECYCLE_H
#define M2_SHARC_LIFECYCLE_H
#include <stddef.h>
#include <stdint.h>
#include "sharc_fp.h"
/* Original callbacks copy caller-owned, non-overlapping buffers. Restore needs
 * at least 0x2b0 writable bytes, even when the copied payload is only 0x2a4.
 * No bounds/version/checksum layer existed in these native callbacks. They are
 * not the Libretro Save State API and do not alter its validation contracts. */
void *m2_sharc_state_save(void *destination,const void *source,size_t bytes);
void *m2_sharc_state_restore(void *destination,const void *source,size_t bytes);
uint32_t m2_sharc_state_address(uint32_t *allocation,uint32_t fixed_state);
uint32_t m2_sharc_setup(uint32_t astat_address,uint32_t incoming_eax,
    uint32_t *astat_binding,uint32_t *control_memory,m2_sharc_fp_state *fp);
void m2_sharc_nop(void);
typedef void (*m2_sharc_diagnostic_hook)(void *opaque,const char *format,uint32_t pc);
uint32_t m2_sharc_bad_compute(uint32_t lhs,uint32_t pc,
    m2_sharc_diagnostic_hook report,void *opaque);
#endif
