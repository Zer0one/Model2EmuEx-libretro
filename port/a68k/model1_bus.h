#ifndef M2_A68K_MODEL1_BUS_H
#define M2_A68K_MODEL1_BUS_H
#include "a68k.h"
#include "../snd/model1_original.h"

/* Repeatable addresses for the allocation values exposed by the original
 * x86 callbacks. They never refer to host process addresses. */
enum {
    A68K_M1_PROGRAM=0x75000000, A68K_M1_RAM=0x77000000,
    A68K_M1_FM=0x78000000, A68K_M1_MACHINE=0x74000000
};
typedef struct {
    m2_original_m1 *sound;
    a68k_cpu *cpu;
} a68k_m1_bus;

int a68k_m1_bind_pages(a68k_m1_bus *bus, a68k_page *fetch, a68k_page *data,
                        a68k_page *writes, uint8_t *program,size_t program_size,
                        uint8_t *ram,size_t ram_size);
#endif
