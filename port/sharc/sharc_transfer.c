#include "sharc_transfer.h"
bool m2_sharc_transfer(uint32_t handler,const m2_sharc_memory_record *r,
                       const m2_sharc_memory_bus *bus,uint32_t *status)
{
    uint32_t value,address;
    switch(handler) {
    case 0x4bca50:
        value=*r->data[0]==r->immediate;
        *status=(*status&~0x40000u)|(value?0x40000u:0u);
        break;
    case 0x4bca80:
        value=(*r->data[0]&r->immediate)==r->immediate;
        *status=(*status&~0x40000u)|(value?0x40000u:0u);
        break;
    case 0x4bcab0:*r->data[0]^=r->immediate;break;
    case 0x4bcac0:*r->data[0]=r->immediate;break;
    case 0x4bd540:*r->address[0]+=r->immediate;break;
    case 0x4bd650:
        bus->write(bus->opaque,*r->address[0],r->immediate);
        *r->address[0]+=*r->step[0];
        break;
    case 0x4bd680:
        address=*r->address[0]+r->immediate;
        value=*r->data[0];
        bus->write(bus->opaque,address,value);
        break;
    case 0x4bd6a0:
        value=bus->read(bus->opaque,*r->address[0]+r->immediate);
        *r->data[0]=value;
        break;
    case 0x4bd6c0:
        value=*r->data[0];bus->write(bus->opaque,r->immediate,value);break;
    case 0x4bd6e0:
        value=bus->read(bus->opaque,r->immediate);*r->data[0]=value;break;
    default:return false;
    }
    return true;
}
