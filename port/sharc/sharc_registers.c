#include "sharc_registers.h"

static unsigned location_offset(uint32_t record[27],uint8_t code,unsigned *in_record)
{
    static const unsigned base[] = {0xd8, 0x138, 0x178, 0x1f8, 0x1b8};
    static const unsigned special[] = {0, 0x23c, 0x238, 0x240, 0x24c, 0x244, 0x250};
    unsigned group = code >> 4;
    unsigned index = code & 15u;
    *in_record=0;

    if (group <= 4) {
        if (group == 4)
            record[0x2c / 4] |= UINT32_C(0x80);
        return base[group]+4*index;
    }
    if (group == 6) {
        if (index <= 1)
            return 4*index;
        if (index >= 3 && index <= 8)
            return 4*(index-1);
        /* The original group-6 jump table falls through to group 7 here. */
    }
    if ((group == 6 || group == 7) && index >= 9)
        return special[index-9];
    *in_record=1;
    return 0x30;
}
uint32_t *m2_sharc_register_location(uint32_t state[169],uint32_t record[27],uint8_t code)
{
    unsigned in_record,offset=location_offset(record,code,&in_record);
    return (in_record?record:state)+offset/4;
}
uint32_t m2_sharc_register_token(uint32_t state,uint32_t base,uint32_t record[27],uint8_t code)
{
    unsigned in_record,offset=location_offset(record,code,&in_record);
    return (in_record?base:state)+offset;
}
