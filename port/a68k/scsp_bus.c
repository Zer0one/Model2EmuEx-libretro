#include "scsp_bus.h"
#include <string.h>

static a68k_read_observation read_width(void *user,uint32_t address,uint32_t flags,unsigned width)
{
    scsp_cpu_observation out;
    if(!scsp_cpu_read_observed(user,address,width,flags,&out))return (a68k_read_observation){0};
    return (a68k_read_observation){{out.eax,out.edx},out.flags,1};
}
static a68k_host_state write_width(void *user,uint32_t address,uint32_t value,uint32_t flags,unsigned width)
{
    scsp_cpu_completion out;
    if(!scsp_cpu_write_observed(user,address,width,value,flags,&out))return (a68k_host_state){0};
    return (a68k_host_state){out.eax,out.flags,1};
}
#define CALLBACKS(W) \
static a68k_read_observation read##W(void *u,uint32_t a,uint32_t f){return read_width(u,a,f,W);} \
static a68k_host_state write##W(void *u,uint32_t a,uint32_t v,uint32_t f){return write_width(u,a,v,f,W);}
CALLBACKS(1)
CALLBACKS(2)
CALLBACKS(4)
#undef CALLBACKS

int a68k_scsp_bind_ram(a68k_page *fetch, a68k_page *data, a68k_page *writes,
                       uint8_t *ram, size_t size)
{
    if (!ram || size != 0x100000 || !fetch || !data || !writes ||
        fetch == data || fetch == writes || data == writes) return 0;
    a68k_page page = {.data=ram, .size=size, .native_base=SCSP_SOUND_RAM_ADDRESS, .native_base_valid=1};
    return a68k_map_pages(fetch, A68K_MAP_FETCH, 0, 0xfffff, &page) &&
           a68k_map_pages(data, A68K_MAP_DATA, 0, 0xfffff, &page) &&
           a68k_map_pages(writes, A68K_MAP_WRITE, 0, 0xfffff, &page);
}

int a68k_scsp_bind_pages(a68k_page *data,a68k_page *writes,scsp *chip)
{
    if(!data || !writes || data==writes || !chip)return 0;
    a68k_page binding={0};binding.user=chip;
    binding.read_live[0]=read1;binding.read_live[1]=read2;binding.read_live[2]=read4;
    binding.write_observed[0]=write1;binding.write_observed[1]=write2;binding.write_observed[2]=write4;
    return a68k_map_pages(data,A68K_MAP_DATA,0x100000,0x10ffff,&binding) &&
           a68k_map_pages(writes,A68K_MAP_WRITE,0x100000,0x10ffff,&binding);
}
a68k_host_state a68k_scsp_ack(void *user,unsigned level,uint32_t flags)
{
    (void)level;scsp_cpu_completion out;
    if(!scsp_cpu_ack_observed(user,flags,&out))return (a68k_host_state){0};
    return (a68k_host_state){out.eax,out.flags,1};
}

/* ElSemi 004aefb0, called 210 times per emulated video frame. Each call
 * starts with ESI zero. Only the sub-256 clock remainder crosses scanlines.
 * 010482a4 is the board's template IRQ field, distinct from live CPU STOP. */
a68k_boundary a68k_scsp_scanline(a68k_cpu *cpu, scsp *chip, const uint32_t *dispatch,
                                 unsigned hz, uint32_t template_irq, uint32_t *phase)
{
    if (!cpu || !chip || !dispatch || !phase || *phase >= 256 || (hz != 58 && hz != 60))
        return A68K_BINDING_ERROR;
    if (cpu->fault.boundary) return cpu->fault.boundary;

    uint32_t clocks = *phase + 11289600u / (hz * 210u);
    uint32_t residue = 0;
    while (clocks >= 256) {
        cpu->cycles = 272 - residue;
        if (template_irq != 0x80) {
            /* EAX is the current clock accumulator at CALL 004af01d.
             * The dispatcher tests the budget before the first fetch. */
            a68k_host_state host = {clocks, 0x202, 1};
            /* 004aefb0 reserves 12, saves ESI and calls the PUSHAD dispatcher. */
            cpu->dispatch_sp = A68K_SCSP_STACK_TOP - 52;
            a68k_boundary status = a68k_begin_observed(cpu, &host);
            while (status == A68K_FETCH) {
                unsigned steps;
                status = a68k_run_live(cpu, dispatch, &host, 256, &steps);
            }
            cpu->dispatch_sp = 0;
            if (status != A68K_EXIT) return status;
            residue = cpu->cycles;
        }
        scsp_clock_tick(chip);
        clocks -= 256;
    }
    *phase = clocks;
    return A68K_RETURN;
}

/* Program ROM writes return through a bare RET (004c69c0/d0/e0).
 * The wrapper's last TEST of the zero direct base sets ZF and PF. */
static a68k_host_state rom_write_result(uint32_t flags, uint32_t callback)
{
    return (a68k_host_state){callback, (flags & ~0x8d5u) | 0x44u, 1};
}

#define EMPTY_WRITE(NAME, TOKEN) \
static a68k_host_state NAME(void *user, uint32_t address, uint32_t value, uint32_t flags) { \
    (void)user; (void)address; (void)value; return rom_write_result(flags, TOKEN); \
}
EMPTY_WRITE(rom_write8, 0x004c69e0)
EMPTY_WRITE(rom_write16, 0x004c69d0)
EMPTY_WRITE(rom_write32, 0x004c69c0)
EMPTY_WRITE(bank_write8, 0x004c6a90)
EMPTY_WRITE(bank_write16, 0x004c8380)
EMPTY_WRITE(bank_write32, 0x004cb1f0)
#undef EMPTY_WRITE

int a68k_scsp_bind_rom(a68k_page *fetch, a68k_page *data, a68k_page *writes,
                       const a68k_page *program, const a68k_page *samples)
{
    if (!fetch || !data || !writes || fetch == data || fetch == writes || data == writes ||
        !program || !program->data || program->size < 8 ||
        (samples && (!samples->data || samples->size == 0 || samples->size > 0x800000))) return 0;
    /* 004cd272 installs separate bare RET callbacks on the bank-control page. */
    a68k_page bank = {.write_observed={bank_write8, bank_write16, bank_write32}};
    a68k_map_pages(writes, A68K_MAP_WRITE, 0x400000, 0x400fff, &bank);
    a68k_page ignored = {0};
    ignored.write_observed[0] = rom_write8;
    ignored.write_observed[1] = rom_write16;
    ignored.write_observed[2] = rom_write32;
    a68k_page prog = *program;
    if (!prog.native_base_valid) prog.native_base = A68K_SCSP_PROGRAM_BASE - 0x600000;
    prog.native_base_valid = 1;
    a68k_map_pages(fetch, A68K_MAP_FETCH, 0x600000, 0x67ffff, &prog);
    a68k_map_pages(data, A68K_MAP_DATA, 0x600000, 0x67ffff, &prog);
    a68k_map_pages(writes, A68K_MAP_WRITE, 0x600000, 0x67ffff, &ignored);
    if (samples) {
        uint32_t end = 0x7fffff + (uint32_t)samples->size;
        a68k_page bank_rom = *samples;
        if (!bank_rom.native_base_valid) bank_rom.native_base = A68K_SCSP_SAMPLES_BASE - 0x800000;
        bank_rom.native_base_valid = 1;
        a68k_map_pages(fetch, A68K_MAP_FETCH, 0x800000, end, &bank_rom);
        a68k_map_pages(data, A68K_MAP_DATA, 0x800000, end, &bank_rom);
    }
    return 1;
}

a68k_boundary a68k_scsp_reset_vectors(a68k_cpu *cpu)
{
    if (!cpu || !cpu->read_pages) return A68K_BINDING_ERROR;
    if (cpu->fault.boundary) return cpu->fault.boundary;
    const a68k_page *ram = &cpu->read_pages[0], *program = &cpu->read_pages[0x600];
    if (!ram->data || ram->guest_base != 0 || ram->size < 8 ||
        !program->data || program->guest_base != 0x600000 || program->size < 8)
        return A68K_BINDING_ERROR;
    /* Board reset 004cad8c..004cad98 only copies the reset vectors to the
     * live sound RAM. The SCSP, clock phase and pending commands survive. */
    memmove(ram->data, program->data, 8);
    return a68k_reset(cpu);
}

/* Guest RESET calls the first entry of 00572ab8, not the board's warm
 * reset routine. The installed function 004b3080 is XOR EAX,EAX; RET. */
static a68k_host_state scsp_guest_reset(void *user, uint32_t flags)
{
    (void)user;
    return (a68k_host_state){0, (flags & ~0x8d5u) | 0x44u, 1};
}

a68k_boundary a68k_scsp_cold_cpu(a68k_cpu *cpu, scsp *chip)
{
    /* Fresh process only. At 004cd2e8 the zero-initialized template
     * receives two opaque x86 tokens before the first 128 bytes are copied.
     * The trailing raw_pc is initially zero in the executable image. */
    if (!cpu || !chip || !cpu->read_pages) return A68K_BINDING_ERROR;
    if (cpu->fault.boundary) return cpu->fault.boundary;
    scsp_bind_irq_register(chip, &cpu->r.irq);
    scsp_bind_cpu_write_frame(chip, &cpu->write_wrapper_sp, A68K_SCSP_DSP_CODE);
    cpu->reset_observed = scsp_guest_reset;
    cpu->r = (a68k_registers){.ack_token = 0x004b3090, .opaque24 = {[1] = 0x00572ab8}};
    return a68k_reset(cpu);
}
