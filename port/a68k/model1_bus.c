/* Model 1 A68K board map installed by 004ccbe0. CPU observations include the
 * x86 scratch state which survives the width-specific wrapper. */
#include "model1_bus.h"

#include "../snd/model1_completion.h"

static a68k_read_observation read_bus(void *user,uint32_t a,uint32_t flags,unsigned width)
{
    a68k_m1_bus *bus=user;
    unsigned page=a>>16;
    uint8_t cursors[2]={0};
    if (page==0xc2 && width==1)
        m2_original_m1_cursors(bus->sound,cursors);
    uint32_t value=m2_original_m1_read(bus->sound,a,width,&bus->cpu->r.irq);
    uint32_t eax=value,edx=0;
    flags=m1_logic_flags(flags,value,32);
    if (page==0xc2) {
        if (width==1) {
            if ((a&65535)==1) {
                edx=cursors[1];
                m2_original_m1_cursors(bus->sound,cursors);
                flags=m1_sub_flags(flags,cursors[0],edx,8);
            } else eax=(a&0xff00);
        } else edx=width==2 ? value&255 : (value>>16)&255;
    } else if (page==0xd0) {
        if (width==1) {
            eax=a==0xd00001 ? A68K_M1_FM|value : 0x4c6900;
            flags=m1_logic_flags(flags,0,8);
        } else edx=width==2 ? A68K_M1_FM : value&65535;
    } else if (page>=0xc4 && page<=0xc7) {
        if (width==1) eax=0x4c6a00;
        if (width==4) edx=page>=0xc6 ? 0x4cb190 : 0x4cb1a0;
    } else {
        if (width==1) eax=0x4c7dff;
        if (width==4) edx=0x4c7d20;
        flags=width==2 ? m1_logic_flags(flags,0,32) : m1_logic_flags(flags,UINT32_MAX,8);
    }
    return (a68k_read_observation){{eax,edx},flags,1};
}

static a68k_host_state write_bus(void *user,uint32_t a,uint32_t value,uint32_t flags,unsigned width)
{
    a68k_m1_bus *bus=user;
    unsigned page=a>>16;
    if (page>=0xc4 && page<=0xc7) {
        m2_m1_completion r=m2_original_m1_pcm_store(bus->sound,(page-0xc4)>>1,
                            a,width,value,bus->cpu->write_wrapper_sp,flags);
        return (a68k_host_state){r.eax,r.flags,1};
    }
    if (page==0xd0) {
        m2_m1_completion r=m2_original_m1_fm_store(bus->sound,a,width,value,flags);
        /* 004ccbdb discards the 12-byte local frame with ADD ESP,12
         * after the fourth FM byte. Its flags reach the next A68K handler. */
        if (width==4) r.flags=m1_stack_flags(r.flags,bus->cpu->write_wrapper_sp,12);
        return (a68k_host_state){r.eax,r.flags,1};
    }
    uint32_t token=width==1 ? 0x4c7d10 : width==2 ? 0x4c7d00 : 0x4c7cf0;
    if (page==0xc1) token=width==1 ? 0x4c6a30 : width==2 ? 0x4c82c0 : 0x4cb1b0;
    return (a68k_host_state){token,m1_logic_flags(flags,0,32),1};
}

#define WIDTH(W) \
static a68k_read_observation read##W(void *u,uint32_t a,uint32_t f) \
{ return read_bus(u,a,f,W); } \
static a68k_host_state write##W(void *u,uint32_t a,uint32_t v,uint32_t f) \
{ return write_bus(u,a,v,f,W); }
WIDTH(1)
WIDTH(2)
WIDTH(4)
#undef WIDTH

int a68k_m1_bind_pages(a68k_m1_bus *bus,a68k_page *fetch,a68k_page *data,
                        a68k_page *writes,uint8_t *program,size_t size,
                        uint8_t *ram,size_t ram_size)
{
    if (!bus || !bus->cpu || !bus->sound || !fetch || !data || !writes ||
        !program || size<0x40000 || !ram || ram_size!=65536) return 0;
    a68k_page io={.user=bus,.read_live={read1,read2,read4},.write_observed={write1,write2,write4}};
    if (!a68k_map_pages(data,A68K_MAP_DATA,0,0xffffff,&io) ||
        !a68k_map_pages(writes,A68K_MAP_WRITE,0,0xffffff,&io)) return 0;
    a68k_page low={.data=program,.size=size,.native_base_valid=1,.native_base=A68K_M1_PROGRAM};
    a68k_page high={.data=program+0x20000,.guest_base=0x80000,.size=size-0x20000,
                    .native_base_valid=1,.native_base=A68K_M1_PROGRAM-0x60000};
    a68k_page work={.data=ram,.guest_base=0xf00000,.size=ram_size,
                    .native_base_valid=1,.native_base=A68K_M1_RAM-0xf00000};
    return a68k_map_pages(fetch,A68K_MAP_FETCH,0,0x1ffff,&low) &&
           a68k_map_pages(fetch,A68K_MAP_FETCH,0x80000,0x9ffff,&high) &&
           a68k_map_pages(data,A68K_MAP_DATA,0,0x1ffff,&low) &&
           a68k_map_pages(data,A68K_MAP_DATA,0x80000,0x9ffff,&high) &&
           a68k_map_pages(data,A68K_MAP_DATA,0xf00000,0xf0ffff,&work) &&
           a68k_map_pages(writes,A68K_MAP_WRITE,0xf00000,0xf0ffff,&work);
}
