/* Expose only the emulated caller's stack depth at each guest bus store. */
#include "../a68k.h"
#include <string.h>

typedef struct {
    a68k_cpu cpu;
    unsigned count;
    uint32_t *depths;
} fixture;

static a68k_host_state store(void *user,uint32_t address,uint32_t value,uint32_t flags)
{
    fixture *f=user;
    (void)address; (void)value;
    if (f->count < 32)
        f->depths[f->count]=f->cpu.dispatch_sp-f->cpu.write_wrapper_sp;
    ++f->count;
    return (a68k_host_state){0,flags,1};
}
static a68k_read_observation load(void *user,uint32_t address,uint32_t flags)
{
    (void)user; (void)address;
    return (a68k_read_observation){{0,0},flags,1};
}
static a68k_host_state bind(void *user,uint32_t address,uint32_t flags)
{
    (void)user; (void)address;
    return (a68k_host_state){0,flags,1};
}
static a68k_host_state ack(void *user,unsigned level,uint32_t flags)
{
    (void)user; (void)level;
    return (a68k_host_state){UINT32_MAX,flags,1};
}

int probe_write_frames(const uint16_t *code,const uint32_t *regs,uint32_t target,
                       uint32_t dispatch_sp,int enter_irq,uint32_t *depths)
{
    fixture f={0};
    f.depths=depths;
    uint8_t costs[256]={0};
    a68k_page fetch={.data=(uint8_t *)code,.size=16};
    a68k_page page={.user=&f,.write_observed={store,store,store},
                    .read_live={load,load,load}};
    static a68k_page pages[A68K_PAGE_COUNT];
    /* Every effective address resolves to the same observable device. */
    for (unsigned i=0;i<A68K_PAGE_COUNT;++i) pages[i]=page;
    memcpy(&f.cpu.r,regs,sizeof f.cpu.r);
    f.cpu.exception_cycles=costs;
    f.cpu.dispatch_sp=dispatch_sp;
    f.cpu.fetch_page=&fetch;
    f.cpu.read_pages=f.cpu.data_pages=f.cpu.write_pages=pages;
    f.cpu.address_mask=0xffffff;
    f.cpu.bind_observed=bind;
    f.cpu.ack_observed=ack;
    f.cpu.entry_eax_valid=1;
    f.cpu.pc=f.cpu.r.pc;
    f.cpu.flags=f.cpu.r.flags;
    a68k_host_state host={0,0x202,1};
    a68k_boundary status=enter_irq ? a68k_begin_observed(&f.cpu,&host)
        : a68k_step_observed(&f.cpu,target,code[0],&host);
    return status==A68K_BINDING_ERROR || f.count>32 || f.cpu.write_wrapper_sp ? -1 : (int)f.count;
}
