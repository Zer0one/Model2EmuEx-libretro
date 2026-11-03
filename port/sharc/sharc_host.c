#include "sharc_host.h"
static void store16(uint8_t *p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void store32(uint8_t *p,uint32_t v){store16(p,v);store16(p+2,v>>16);}
static void resume(m2_sharc_host *h,uint32_t clear) {
    *h->astat&=~clear;*h->selected=h->fixed;*h->stop=0;h->run(h->opaque);
}
static void push(m2_sharc_host *h,uint32_t value) {
    h->input[h->input[33]]=value;h->input[34]--;h->input[33]=(h->input[33]+1)&31;
    resume(h,0x80000u);
}
static void port_write32(m2_sharc_host *h,uint32_t address,uint32_t value) {
    if(address-0x880000u<0x4000u && !(address&15u)) {
        push(h,value|(((address>>4)&255u)<<23));return;
    }
    if(h->program_control&0x80000000u) {
        /* Despite the 32-bit host entry, upload stores DX and advances two. */
        store16(h->program+h->program_offset,value);h->program_offset+=2;return;
    }
    if(h->program_offset && address-0x884000u<0x4000u)push(h,value);
}
bool m2_sharc_host_access(uint32_t entry,m2_sharc_host *h,uint32_t address,
    uint32_t value,uint32_t *result)
{
    uint32_t index,captured,mask;
    switch(entry) {
    case 0x4c5e30:case 0x4c5e90:case 0x4c5ea0:case 0x4c5fb0:case 0x4c6010:
        return true; /* Native RET-only callbacks. */
    case 0x4c5f70:
        /* Native masks ECX to 0xfff then compares with 0x804000. The upload
         * branch is unreachable. Preserve, as for the upstream TGP driver. */
        return true;
    case 0x4c6220:port_write32(h,address,value);return true;
    case 0x4c6310:
        if(h->program_control&0x80000000u) {
            store16(h->program+h->program_offset,value);h->program_offset+=2;
        }
        /* Original falls through to the 32-bit entry, rather than returning.
         * Non-command uploads therefore store the low word TWICE. */
        port_write32(h,address,value&0xffffu);return true;
    case 0x4c6340:case 0x4c63a0:case 0x4c6400:
        mask=entry==0x4c6340?0xffffffffu:entry==0x4c63a0?0xffffu:0xffu;
        if(address-0x884000u>=0x4000u) {
            *result=entry==0x4c6340?0:mask;return true;
        }
        index=h->output[32];captured=h->output[index];
        h->output[34]++;h->output[32]=(index+1)&31;
        if(h->output[34]!=0)resume(h,0x100000u);
        *result=captured&mask;return true;
    case 0x4c5eb0:
        if(address==0x801008){h->shared_write=value;return true;}
        if(address==0x803008){h->reg_803008=value;return true;}
        if((address&0xfffff000u)==0x804000 && (h->data_control&0x80000000u)) {
            store16(h->data+h->data_offset,value);h->data_offset+=2;return true;
        }
        address&=0xffffu;
        if(address<0x3ff0u && !(address&15u)) {
            index=h->shared_write&0x7ffffu;
            store32(h->shared+index,value|((address&0x3f0u)<<19));
            h->shared_write=(index+4)&0x7ffffu;
        }
        if(address-0x4000u<0x4000u) {
            index=h->shared_write&0x7ffffu;store32(h->shared+index,value);
            h->shared_write=(index+4)&0x7ffffu;
        }
        return true;
    case 0x4c5fc0:
        *result=address==0x801008?h->reg_801008:address==0x802008?h->shared_write:
            address==0x803008?h->reg_803008:0;return true;
    case 0x4c5ff0:case 0x4c6000:*result=0;return true;
    case 0x4c6460:h->render(h->opaque);return true;
    default:return false;
    }
}
