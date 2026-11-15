#include "m2protection.h"
#include "m2board.h"
#include "../tgpx4/tgpx4_protection.h"

int m2_protection_present(const m2_board *b) {
    if(b->type!=1 && b->type!=2)return 0;
    if(b->game->hook!=M2_HOOK_UNKNOWN)return 0;
    switch(b->game->hook_addr) {
    case 0x4c7e90: case 0x4c7f30: case 0x4c7fa0: case 0x4c8000:return 1;
    default:return 0;
    }
}
static uint8_t *mutable(m2_board *b,uint32_t address,unsigned bytes) {
    if(address>=0x5aa770 && (uint64_t)address+bytes<=0x5aa870)
        return b->protection_response+(address-0x5aa770);
    switch(address) {
    case 0x10ed908:return bytes==4?(uint8_t *)&b->protection_index:0;
    case 0x10ed90c:return bytes==4?(uint8_t *)&b->protection_selector:0;
    case 0x10f01b0:return bytes==4?(uint8_t *)&b->protection_toggle:0;
    default:return 0;
    }
}
static void escaped(m2_board *b,uint32_t address) {
    if(!b->protection_fault)b->protection_fault_address=address;
    b->protection_fault=1;
    if(b->cpu)b->cpu->stop=1;
}
static uint32_t read(void *opaque,uint32_t address,unsigned bits) {
    m2_board *b=opaque;unsigned bytes=bits/8;uint32_t value=0;
    uint8_t *p=mutable(b,address,bytes);
    if(p) {for(unsigned i=0;i<bytes;i++)value|=(uint32_t)p[i]<<(8*i);return value;}
    /* Original unbounded response copies can observe adjacent process
       objects. Supply their native values, not a host address or a frozen
       capture. These protected native games have no optional DSB; consequently
       its two synthesis cursors retain the original initialization value 64.
       External-link transport variables are not qualified here. */
    if(address>=0x574da8 && (uint64_t)address+bytes<=0x574de8) {
        uint32_t field=address&~3u;unsigned shift=(address&3u)*8;
        int known=1;
        switch(field) {
        case 0x574da8:
            /* 004c8440/4c84a0/4c8500 are Model 2 ROM-bank callbacks.
               They are not mapped by these 2A/2B installers. */
            value=0xc00000;break;
        case 0x574dcc: {
            float fps=(float)b->prev_fps;uint8_t *p=(uint8_t *)&fps;
            value=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
            break;
        }
        case 0x574dd0:case 0x574dd4:
            value=0xff;known=b->net_enabled!=M2_NET_EXTERNAL;break;
        case 0x574dd8:value=0x1c0;known=b->net_enabled!=M2_NET_EXTERNAL;break;
        case 0x574ddc:value=1;known=b->net_enabled!=M2_NET_EXTERNAL;break;
        case 0x574de0:case 0x574de4:
            value=64;known=b->rom.option[1]==0;break;
        default:known=0;break;
        }
        if(known && (address&3u)+bytes<=4)
            return (value>>shift)&(bits==32?0xffffffffu:(1u<<bits)-1u);
    }
    if(m2_tgpx4_protection_constant(address,bits,&value))return value;
    /* Keep the existing explicit boundary: adjacent native process objects
       are not an invented extension of the recovered response tables. */
    escaped(b,address);return 0;
}
static void write(void *opaque,uint32_t address,uint32_t value,unsigned bits) {
    m2_board *b=opaque;unsigned bytes=bits/8;uint8_t *p=mutable(b,address,bytes);
    if(!p) {escaped(b,address);return;}
    for(unsigned i=0;i<bytes;i++)p[i]=(uint8_t)(value>>(8*i));
}
uint32_t m2_protection_access(m2_board *b,uint32_t address,uint32_t value,unsigned bits,int writing) {
    m2_tgpx4_execution_bus bus={b,read,write,0};
    if(b->protection_fault)return 0;
    if(writing) {m2_tgpx4_protection_write(&bus,address,value,bits);return 0;}
    return m2_tgpx4_protection_read(&bus,address,bits);
}
void m2_protection_install(m2_board *b) {
    if(!m2_protection_present(b))return;
    /* Original installers patch predecoded entries, not ROM bytes. A native
       entry is 0x30 bytes with its op pointer at +0x18. Preserve the exact
       instruction positions and reinstall after cache restoration. */
    switch(b->game->hook_addr) {
    case 0x4c7e90:
        i960_nop_insn(b->cpu,0x630); /* original cache +4a58 */
        i960_nop_insn(b->cpu,0x808); /* original cache +6078 */
        i960_stop_after_insn(b->cpu,0x27e0);break;
    case 0x4c7f30:i960_nop_insn(b->cpu,0x730);break; /* +5658 */
    case 0x4c8000:i960_nop_insn(b->cpu,0x700);break; /* +5418 */
    default:break; /* 004c7fa0 installs only the memory handlers. */
    }
}
