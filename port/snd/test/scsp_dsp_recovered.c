/* The oracle now tests the reusable recovered implementation directly. */
#include "../scsp_dsp_original.h"
#include <stdlib.h>
#include <string.h>
int scsp_dsp_recovered_probe(const uint8_t *input,uint8_t *output,uint8_t *ram,
                             uint32_t ram_size,unsigned samples) {
    scsp_dsp_original *d=malloc(sizeof *d);
    if(!d)return 0;
    scsp_dsp_original_init(d);memcpy(&d->context,input,0x800);
    scsp_dsp_original_compile(d);
    int ok=!d->fault;
    for(unsigned i=0;i<samples && ok;i++)ok=scsp_dsp_original_step_memory(d,ram,ram_size);
    memcpy(output,&d->context,0x800);free(d);return ok;
}
