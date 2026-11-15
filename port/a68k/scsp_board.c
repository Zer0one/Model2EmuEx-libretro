#include "scsp_board.h"
#include "divs_error_policy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct a68k_scsp_board {
    a68k_cpu cpu;
    scsp *chip;
    a68k_page fetch[A68K_PAGE_COUNT], data[A68K_PAGE_COUNT], writes[A68K_PAGE_COUNT];
    uint32_t dispatch[A68K_OPCODE_COUNT];
    uint8_t costs[256];
    uint32_t phase;
    a68k_boundary status;
    a68k_divs_error_policy divs_policy;
    unsigned trace_line;
    int trace;
};

static a68k_host_state bind_pc(void *user, uint32_t pc, uint32_t flags)
{
    a68k_scsp_board *b = user;
    return a68k_bind_pc_observed(&b->cpu, pc, flags);
}

static a68k_host_state acknowledge(void *user, unsigned level, uint32_t flags)
{
    a68k_scsp_board *b = user;
    if (b->trace) fprintf(stderr,"A68K_IRQ %u %u\n",b->trace_line,level);
    return a68k_scsp_ack(b->chip, level, flags);
}

void a68k_board_roms(a68k_scsp_board *b, const uint8_t *program, unsigned program_size,
                     const uint8_t *samples, unsigned sample_size)
{
    /* Direct ROM descriptors are used only by FETCH and DATA. Writes have
     * separate handlers. Remove pages left by a larger previous sample bank. */
    memset(b->fetch + 0x800, 0, sizeof b->fetch[0] * 0x800);
    memset(b->data + 0x800, 0, sizeof b->data[0] * 0x800);
    a68k_page p = {.data=(uint8_t *)program, .size=program_size};
    a68k_page s = {.data=(uint8_t *)samples, .size=sample_size};
    if (!a68k_scsp_bind_rom(b->fetch, b->data, b->writes, &p, sample_size ? &s : NULL))
        b->status = A68K_BINDING_ERROR;
}

a68k_scsp_board *a68k_board_create(uint8_t *ram, scsp *chip,
    const uint8_t *program, unsigned program_size, const uint8_t *samples, unsigned sample_size, int original_divs)
{
    a68k_scsp_board *b = calloc(1, sizeof *b);
    if (!b) return NULL;
    if (!a68k_init_dispatch(b->dispatch, A68K_OPCODE_COUNT) ||
        !a68k_scsp_bind_ram(b->fetch,b->data,b->writes,ram,0x100000) ||
        !a68k_scsp_bind_pages(b->data,b->writes,chip)) goto failed;
    a68k_board_roms(b, program, program_size, samples, sample_size);
    if (b->status) goto failed;
    b->chip = chip;
    b->trace = getenv("MODEL2EMUEX_SOUND_TRACE") != NULL;
    b->divs_policy = original_divs ? A68K_DIVS_ORIGINAL : A68K_DIVS_STOP_CONTENT;
    b->cpu.read_pages = b->fetch;
    b->cpu.data_pages = b->data;
    b->cpu.write_pages = b->writes;
    b->cpu.address_mask = 0xffffff;
    b->cpu.exception_cycles = b->costs;
    a68k_init_exception_cycles(b->costs);
    b->cpu.user = b;
    b->cpu.bind_observed = bind_pc;
    b->cpu.ack_observed = acknowledge;
    memcpy(ram, program, 8);
    if (a68k_scsp_cold_cpu(&b->cpu, chip) == A68K_RETURN) return b;
    scsp_bind_irq_register(chip, NULL);
    scsp_bind_cpu_write_frame(chip, NULL, 0);
failed:
    free(b);
    return NULL;
}

void a68k_board_reset(a68k_scsp_board *b)
{
    if (!b->status) b->status = a68k_scsp_reset_vectors(&b->cpu);
}

void a68k_board_irq(a68k_scsp_board *b, unsigned level, int asserted)
{
    if (asserted) b->cpu.r.irq = level;
    else if ((b->cpu.r.irq & 7) == level) b->cpu.r.irq = 0;
}

void a68k_board_scanline(a68k_scsp_board *b, unsigned hz)
{
    if (b->trace) ++b->trace_line;
    if (!b->status)
        b->status = a68k_scsp_scanline(&b->cpu,b->chip,b->dispatch,hz,0,&b->phase);
}

int a68k_board_error(const a68k_scsp_board *b, char *text, size_t size)
{
    if (!b->status) return 0;
    if (b->status == A68K_DIVS_HOST_OVERFLOW) {
        a68k_apply_divs_error_policy(&b->cpu, b->divs_policy);
        snprintf(text,size,"A68K DIVS host overflow at PC %08x; content stopped",b->cpu.fault.exception_pc);
        return 1;
    }
    const char *cause = a68k_fault_message(&b->cpu);
    if (cause) {
        snprintf(text,size,"%s PC %08x",cause,b->cpu.fault.exception_pc);
        return 1;
    }
    snprintf(text,size,"A68K stopped at PC %08x (boundary %u)",b->cpu.pc,(unsigned)b->status);
    return 1;
}

void a68k_board_archive(a68k_scsp_board *b, m2_state *a)
{
    /* The scanline entry reloads PC/flags and starts a fresh dispatcher.
     * Keep the live values too. No native pointer or caller stack is archived. */
    a68k_cpu c = b->cpu;
    uint32_t page = (uint32_t)(c.fetch_page - b->fetch), phase = b->phase;
    m2_state_value(a,&c.r,sizeof c.r);
#define VALUE(field) m2_state_value(a,&c.field,sizeof c.field)
    VALUE(pc); VALUE(flags); VALUE(cycles); VALUE(illegal_opcode); VALUE(illegal_pc);
    VALUE(prefetched_opcode); VALUE(prefetched_valid); VALUE(entry_eax); VALUE(entry_eax_valid);
#undef VALUE
    m2_state_value(a,&page,sizeof page);
    m2_state_value(a,&phase,sizeof phase);
    if (b->status || page >= A68K_PAGE_COUNT || phase >= 256 || c.prefetched_valid > 1 ||
        c.entry_eax_valid > 1 || c.prefetched_opcode > 0xffff || (c.r.irq & ~0x87u))
        a->failed = 1;
    if (!a->failed && a->mode == M2_STATE_LOAD) {
        c.fetch_page = &b->fetch[page];
        b->cpu = c;
        b->phase = phase;
    }
}

uint32_t a68k_board_pc(const a68k_scsp_board *b) { return b->cpu.r.pc; }

void a68k_board_trace_command(const a68k_scsp_board *b, uint8_t command)
{
    if (b->trace) fprintf(stderr,"A68K_COMMAND %u %u\n",b->trace_line + 1,command);
}
