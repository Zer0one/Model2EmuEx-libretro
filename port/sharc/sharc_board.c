#include "sharc_board.h"
static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void write16(uint8_t *p,uint32_t value) {p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);}
static void write32(uint8_t *p,uint32_t value) {write16(p,value);write16(p+2,value>>16);}
uint32_t m2_sharc_board_read(m2_sharc_board_bus *b,uint32_t address) {
    uint32_t value,index;
    const uint8_t *p;
    switch(address>>16) {
    case 2:return read32(b->ram0+4*(address&0xffffu));
    case 3:return read32(b->ram1+4*(address&0xffffu));
    case 4:case 6:
        p=((address>>16)==4?b->ram0:b->ram1)+2*(address&0x1ffffu);
        return (uint32_t)p[0]|((uint32_t)p[1]<<8);
    case 0x40:
        b->active_state=b->fixed_state;
        if(b->input_fifo[34]==32) {
            *b->astat|=0x80000u;b->stop=1;return 0;
        }
        *b->astat&=~0x80000u;
        index=b->input_fifo[32];value=b->input_fifo[index];
        b->input_fifo[34]++;b->input_fifo[32]=(index+1)&31;
        if(b->input_fifo[34]==32)*b->astat|=0x80000u;
        return value;
    case 0x140:return read32(b->shared+4*(address&0xfffffu));
    default:
        if(address-0x1c00000u<=0x7fffffu)return read32(b->rom+4*(address-0x1c00000u));
        return 0;
    }
}
void m2_sharc_board_write(m2_sharc_board_bus *b,uint32_t address,uint32_t value) {
    uint32_t index;
    switch(address>>16) {
    case 2:write32(b->ram0+4*(address&0xffffu),value);break;
    case 3:write32(b->ram1+4*(address&0xffffu),value);break;
    case 4:write16(b->ram0+2*(address&0x1ffffu),value);break;
    case 6:write16(b->ram1+2*(address&0x1ffffu),value);break;
    case 0xc0:
        index=b->output_fifo[33];b->output_fifo[index]=value;
        b->output_fifo[34]--;b->output_fifo[33]=(b->output_fifo[33]+1)&31;
        b->active_state=b->fixed_state;
        if(!b->output_fifo[34])*b->astat|=0x100000u;
        else *b->astat&=~0x100000u;
        break;
    case 0x140:write32(b->shared+4*(address&0xfffffu),value);break;
    default:break;
    }
}
bool m2_sharc_renderer_skip(uint32_t entry,uint32_t *cursor) {
    if(entry!=0x4b93d0 && entry!=0x4b9470 && entry!=0x4b9480)return false;
    *cursor+=4;return true;
}
