#include "sharc_upload.h"
void m2_sharc_upload_control(m2_sharc_host *h,uint32_t *reg_98000c,
    uint32_t address,uint32_t value,void *opaque,
    void (*program_complete)(void *),void (*data_complete)(void *))
{
    /* The XOR compares the entire control word, not just bit 31. Completion
     * sees the OLD latch; the incoming word is committed after the callback,
     * even when that callback changes the latch itself. Preserve this order. */
    if(address==0x980000) {
        if((h->program_control^value)==0x80000000u) {
            if(value&0x80000000u) {
                h->program_control=value;h->program_offset=0;return;
            }
            program_complete(opaque);
        }
        h->program_control=value;
    } else if(address==0x980008) {
        if((h->data_control^value)==0x80000000u) {
            if(value&0x80000000u) {
                h->data_control=value;h->data_offset=0;return;
            }
            data_complete(opaque);
        }
        h->data_control=value;
    } else if(address==0x98000c)*reg_98000c=value;
}
