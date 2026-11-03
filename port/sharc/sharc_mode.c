#include "sharc_mode.h"
#define W(s,o) ((s)->state[(uint32_t)(o)/4u])
static void enqueue(m2_sharc_execution *s,uint32_t *queue,uint32_t entry)
{
    queue[s->event_count]=entry;
    ++s->event_count;
    s->event_delay=1;
}
bool m2_sharc_state_helper(uint32_t entry,m2_sharc_execution *s,uint32_t *target,
    uint32_t arg0,uint32_t arg1,uint32_t *queue,const m2_sharc_memory_bus *bus,uint32_t *result)
{
    uint32_t old,changed,index,value,first,second,i;
    switch(entry) {
    case 0x4bd550: case 0x4bd5d0:
        old=*target;
        *target=entry==0x4bd550 ? old&~arg0 : old|arg0;
        if (target==&W(s,0x238)) {
            changed=old^*target;
            /* Original order is high bank (bit 7), then low bank (bit 10).
             * Repeating an unchanged bit does not enqueue another swap. */
            if (changed&0x80u) enqueue(s,queue,entry==0x4bd550?0x4bce60:0x4bcf00);
            if (changed&0x400u) enqueue(s,queue,entry==0x4bd550?0x4bce10:0x4bceb0);
        }
        break;
    case 0x4bce10: case 0x4bce60: case 0x4bceb0: case 0x4bcf00:
        first=(entry==0x4bce10||entry==0x4bceb0)?0xd8u:0xf8u;
        second=first==0xd8u?0x264u:0x284u;
        for(i=0;i<8;i++) {
            value=W(s,first+4*i);
            W(s,first+4*i)=W(s,second+4*i);
            W(s,second+4*i)=value;
        }
        break;
    case 0x4bcd50:*result=bus->read(bus->opaque,arg0);break;
    case 0x4bcd60:
        --W(s,0xd4);index=W(s,0xd4);
        W(s,0x18)=W(s,0x9cu+index*4u);
        W(s,0x14)=W(s,0xb8u+index*4u);
        break;
    case 0x4bcd90:
        ++W(s,0xd4);index=W(s,0xd4);
        W(s,0x18)=arg0;W(s,0x14)=arg1;
        W(s,0x9cu+index*4u)=arg0;
        W(s,0xb8u+W(s,0xd4)*4u)=arg1;
        break;
    case 0x4bcdc0:*result=W(s,0x20u+W(s,0x10)*4u);break;
    case 0x4bcdd0:
        index=W(s,0x10);value=W(s,0x20u+index*4u);
        W(s,0xc)=value;W(s,0x10)=index-1u;*result=value;
        break;
    case 0x4bcdf0:
        ++W(s,0x10);index=W(s,0x10);
        W(s,0xc)=arg0;W(s,0x20u+index*4u)=arg0;
        break;
    case 0x4bcf50:enqueue(s,queue,arg0);break;
    case 0x4bcfc0:W(s,0x240)&=~arg0;break;
    case 0x4bcfe0:W(s,0x240)|=arg0;break;
    default:return false;
    }
    return true;
}
