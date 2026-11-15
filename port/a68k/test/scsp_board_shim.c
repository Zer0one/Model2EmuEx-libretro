/* A fresh synthetic SCSP board for each comparison with the Windows code. */
#include "../scsp_bus.h"
/* Inspect the running chip without issuing a side-effecting CPU read. */
#include "../../snd/scsp.c"
#include <stdlib.h>
#include <string.h>

typedef struct {
    a68k_cpu cpu;
    scsp *chip;
    uint8_t costs[256];
    uint32_t rejected_address, start_count, voice_pointer_writes, dsp_pointer_writes;
    a68k_host_state last_start;
    a68k_page chip_writes;
    a68k_page fetch[A68K_PAGE_COUNT], data[A68K_PAGE_COUNT], writes[A68K_PAGE_COUNT];
    uint32_t dispatch[A68K_OPCODE_COUNT], phase;
} fixture;

static void irq(void *user, int level, int asserted)
{
    fixture *f = user;
    if (asserted) f->cpu.r.irq = (unsigned)level;
    else if ((f->cpu.r.irq & 7) == (unsigned)level) f->cpu.r.irq = 0;
}

static a68k_host_state acknowledge(void *user, unsigned level, uint32_t flags)
{
    fixture *f = user;
    return a68k_scsp_ack(f->chip, level, flags);
}

static a68k_host_state bind_pc(void *user, uint32_t pc, uint32_t flags)
{
    fixture *f = user;
    return a68k_bind_pc_observed(&f->cpu, pc, flags);
}

static a68k_host_state trace_write(fixture *f, unsigned index, uint32_t address,
                                   uint32_t value, uint32_t flags)
{
    a68k_host_state result = f->chip_writes.write_observed[index](f->chip, address, value, flags);
    if (index < 2 && result.valid) {
        if ((address & ~3u) == 0x100684) ++f->voice_pointer_writes;
        if ((address & ~3u) == 0x10068c) ++f->dsp_pointer_writes;
    }
    if (!result.valid) f->rejected_address = address;
    else if (address == (index == 2 ? 0x100bfc : 0x100bfe)) {
        f->last_start = result;
        ++f->start_count;
    }
    return result;
}
static a68k_host_state trace_byte(void *user, uint32_t address, uint32_t value, uint32_t flags)
{
    return trace_write(user, 0, address, value, flags);
}
static a68k_host_state trace_word(void *user, uint32_t address, uint32_t value, uint32_t flags)
{
    return trace_write(user, 1, address, value, flags);
}
static a68k_host_state trace_long(void *user, uint32_t address, uint32_t value, uint32_t flags)
{
    return trace_write(user, 2, address, value, flags);
}

fixture *scsp_board_test_create(uint8_t *ram, uint32_t native_ram)
{
    fixture *f = calloc(1, sizeof *f);
    if (!f) return NULL;
    f->chip = scsp_create(ram, 0x100000, 0x7ffff, irq, f);
    if (!f->chip || !a68k_init_dispatch(f->dispatch, A68K_OPCODE_COUNT) ||
        !a68k_scsp_bind_ram(f->fetch, f->data, f->writes, ram, 0x100000) ||
        !a68k_scsp_bind_pages(f->data, f->writes, f->chip)) goto failed;
    /* Legacy synthetic fixtures share the oracle's smaller RAM mapping. */
    if (native_ram != SCSP_SOUND_RAM_ADDRESS)
        for (unsigned i = 0; i < 0x100; ++i)
            f->fetch[i].native_base = f->data[i].native_base = f->writes[i].native_base = native_ram;
    f->chip_writes = f->writes[0x100];
    f->writes[0x100].user = f;
    f->writes[0x100].write_observed[1] = trace_word;
    f->writes[0x100].write_observed[2] = trace_long;
    f->writes[0x100].write_observed[0] = trace_byte;
    f->cpu.read_pages = f->fetch;
    f->cpu.data_pages = f->data;
    f->cpu.write_pages = f->writes;
    a68k_init_exception_cycles(f->costs);
    f->cpu.exception_cycles = f->costs;
    f->cpu.address_mask = 0xffffff;
    f->cpu.user = f;
    f->cpu.bind_observed = bind_pc;
    f->cpu.ack_observed = acknowledge;
    return f;
failed:
    scsp_destroy(f->chip);
    free(f);
    return NULL;
}

void scsp_board_test_code_address(fixture *f, uint32_t address)
{
    scsp_bind_cpu_write_frame(f->chip, &f->cpu.write_wrapper_sp, address);
}

int scsp_board_test_boot(fixture *f)
{
    return a68k_scsp_cold_cpu(&f->cpu, f->chip);
}

void scsp_board_test_destroy(fixture *f)
{
    scsp_destroy(f->chip);
    free(f);
}

void scsp_board_test_write(fixture *f, unsigned reg, uint16_t value)
{
    scsp_write16(f->chip, reg, value, 0xffff);
}

void scsp_board_test_command(fixture *f, uint8_t command)
{
    scsp_midi_in(f->chip, command);
}

int scsp_board_test_scanline(fixture *f, unsigned hz, unsigned gate, uint32_t *out)
{
    a68k_boundary status = a68k_scsp_scanline(&f->cpu, f->chip, f->dispatch, hz, gate, &f->phase);
    memcpy(out, &f->cpu.r, sizeof f->cpu.r);
    out[33] = f->phase;
    out[34] = f->cpu.cycles;
    out[35] = f->cpu.pc;
    out[36] = f->rejected_address;
    out[37] = f->start_count;
    out[38] = f->last_start.eax;
    out[39] = f->last_start.control_flags;
    out[40] = f->chip->MidiW | ((uint32_t)f->chip->MidiR << 8) |
              ((uint32_t)f->chip->MidiCount << 16);
    out[41] = f->voice_pointer_writes;
    out[42] = f->dsp_pointer_writes;
    return status;
}

void scsp_board_test_registers(const fixture *f, uint8_t *out)
{
    const scsp *s = f->chip;
    memcpy(out, s->u.datab, 0x30);
    out += 0x30;
    for (unsigned i = 0; i < 32; ++i, out += 32)
        memcpy(out, s->Slots[i].u.data, 32);
    memcpy(out, s->RINGBUF, 128);
    out += 128;
    memcpy(out, s->DSP.context.COEF, sizeof s->DSP.context.COEF);
    out += sizeof s->DSP.context.COEF;
    memcpy(out, s->DSP.context.MADRS, sizeof s->DSP.context.MADRS);
    out += sizeof s->DSP.context.MADRS;
    memcpy(out, s->DSP.context.MPRO, sizeof s->DSP.context.MPRO);
    out += sizeof s->DSP.context.MPRO;
    memcpy(out, s->MidiStack, 128);
    memcpy(out + 128, s->cpu_midi_output, 128);
    out[256] = s->cpu_midi_cursor;
    out[257] = s->cpu_midi_count;
    memcpy(out + 258, &s->voice_ram_address, 4);
    memcpy(out + 262, &s->DSP.context.ram_address, 4);
}

int scsp_board_test_rom(fixture *f, uint8_t *program, unsigned program_size,
                        uint8_t *samples, unsigned sample_size)
{
    a68k_page p = {.data=program, .size=program_size};
    a68k_page s = {.data=samples, .size=sample_size};
    return a68k_scsp_bind_rom(f->fetch, f->data, f->writes, &p, &s);
}

int scsp_board_test_reset(fixture *f)
{
    return a68k_scsp_reset_vectors(&f->cpu);
}

void scsp_board_test_cold_state(fixture *f, uint32_t *context, uint8_t *costs)
{
    memcpy(context, &f->cpu.r, sizeof f->cpu.r);
    memcpy(costs, f->costs, sizeof f->costs);
}
