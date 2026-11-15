/* Headless single-machine test observer. Link this object with tgpx4_execute.c
 * compiled with -Dm2_tgpx4_execute_board_memory=m2_tgpx4_unobserved_memory.
 * Leave all callers unchanged. No ROM bytes or machine memory are exported. */
#include "../tgpx4_execute.h"
#include "../tgpx4_lifecycle.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

bool m2_tgpx4_unobserved_memory(uint32_t entry, const m2_tgpx4_execution_bus *bus,
                                m2_tgpx4_execution_registers *regs);

struct read_site {
    uint64_t count;
    uint32_t lowest, highest;
};

static struct read_site sites[0x40000 / 8]; /* Maximum Model 2C upload in 64-bit words. */
static uint64_t shared_reads, shared_writes;
static bool registered;

static void report(void)
{
    for (unsigned i = 0; i < sizeof sites / sizeof sites[0]; ++i) {
        if (sites[i].count)
            fprintf(stderr, "ROM site %04x reads %" PRIu64 " first_word %x last_word %x\n",
                    i, sites[i].count, sites[i].lowest, sites[i].highest);
    }
    fprintf(stderr, "Shared window reads %" PRIu64 " writes %" PRIu64 "\n",
            shared_reads, shared_writes);
}

bool m2_tgpx4_execute_board_memory(uint32_t entry, const m2_tgpx4_execution_bus *bus,
                                   m2_tgpx4_execution_registers *regs)
{
    const uint32_t address = regs->ecx;
    if (!registered) {
        if (atexit(report) != 0)
            abort();
        registered = true;
    }
    if (entry == 0x4c5a90 && address >= 0x800000) {
        const uint32_t base = bus->read(bus->opaque, 0x10481f0, 32);
        const uint32_t record = bus->read(bus->opaque, 0x104824c, 32);
        const uint32_t delta = record - base;
        const uint32_t index = delta / M2_TGPX4_RECORD_BYTES;
        if (record < base || delta % M2_TGPX4_RECORD_BYTES || index >= sizeof sites / sizeof sites[0])
            abort();
        struct read_site *site = &sites[index];
        const uint32_t word = address - 0x800000;
        if (!site->count || word < site->lowest)
            site->lowest = word;
        if (!site->count || word > site->highest)
            site->highest = word;
        ++site->count;
    } else if (address >= 0x400000 && address < 0x800000) {
        if (entry == 0x4c5a90)
            ++shared_reads;
        else if (entry == 0x4c5a70)
            ++shared_writes;
    }
    return m2_tgpx4_unobserved_memory(entry, bus, regs);
}
