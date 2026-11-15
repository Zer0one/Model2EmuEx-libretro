/* Recovered SCSP page callbacks and board scheduler. */
#ifndef M2_A68K_SCSP_BUS_H
#define M2_A68K_SCSP_BUS_H
#include "a68k.h"
#include "../snd/scsp.h"

/* Repeatable numeric counterparts of allocations in the x86 process.
 * Backing data stays in separate, bounded host allocations. */
enum {
    A68K_SCSP_STACK_TOP = 0x71008000,
    A68K_SCSP_PROGRAM_BASE = 0x74000000,
    A68K_SCSP_SAMPLES_BASE = 0x75000000,
    A68K_SCSP_DSP_CODE = 0x77000000
};

int a68k_scsp_bind_ram(a68k_page *fetch, a68k_page *data, a68k_page *writes,
                       uint8_t *ram, size_t size);
/* DATA/WRITE tables are caller-owned A68K_PAGE_COUNT arrays. Only the native
 * 0x100000..0x10ffff SCSP window is changed. The chip must outlive the binding.
 * Unsupported observer ranges return a binding failure before chip mutation;
 * there is no value-only fallback or portable host-register inference. */
int a68k_scsp_bind_pages(a68k_page *data,a68k_page *writes,scsp *chip);
/* Pass the SCSP chip as user. The CPU dispatcher owns clearing the accepted
 * request before the live autovector at 004b3090. Keep the SCSP line in sync. */
a68k_host_state a68k_scsp_ack(void *user,unsigned level,uint32_t flags);
/* Research board clock. A non-RETURN result ends content execution; the
 * caller must not retry a partially executed board event. */
a68k_boundary a68k_scsp_scanline(a68k_cpu *cpu, scsp *chip, const uint32_t *dispatch,
                                 unsigned hz, uint32_t template_irq, uint32_t *phase);
/* Install in a fresh board map. Each backing starts at byte zero of the
 * original region. The board supplies its stable virtual allocation bases. Missing sample ROMs have no fetch/data mapping. */
int a68k_scsp_bind_rom(a68k_page *fetch, a68k_page *data, a68k_page *writes,
                       const a68k_page *program, const a68k_page *samples);
/* Fresh, bound CPU with reset vectors already installed in RAM. */
a68k_boundary a68k_scsp_cold_cpu(a68k_cpu *cpu, scsp *chip);
a68k_boundary a68k_scsp_reset_vectors(a68k_cpu *cpu);
#endif
