#include "sharc_board_init.h"
static unsigned fold(unsigned x) {return x>='A' && x<='Z'?x+32:x;}
static bool match(const char *a,const char *b,unsigned limit) {
    while(limit--) {
        unsigned x=(unsigned char)*a++,y=(unsigned char)*b++;
        if(fold(x)!=fold(y))return false;
        if(!x)return true;
    }
    return true;
}
void m2_sharc_board_initialize(m2_sharc_board_configuration *c,const char *game,
    uint32_t fixed_state,m2_sharc_fp_state *fp,m2_sharc_board_reset_hook reset,void *opaque)
{
    reset(opaque,0x100);
    c->offset_bits=0;c->scale_bits=0;
    c->astat=(c->astat&~0x100000u)|0x80000u;
    c->selected_state=fixed_state;c->stop=1;
    c->read_binding=0x4c6100;c->write_binding=0x4c6020;c->mode=0;
    if(match(game,"schamp",7)||match(game,"sfight",7)||match(game,"gunblade",9)||
       match(game,"fvip",4)||match(game,"von",3)) {
        c->scale_bits=0x41000000;c->offset_bits=0xc2180000;
    }
    if(match(game,"lastb",5)) {
        c->renderer_a8=0x4b9480;c->renderer_b0=0x4b9470;
        c->renderer_150=0x4b93d0;c->renderer_158=0x4b93d0;
    }
    /* Original compares "zerogun" but ignores the return value: always 1.
     * Preserve this assignment rather than inventing a title-specific flag. */
    c->enabled=1;
    if(match(game,"von",3)||match(game,"dyn",3)||match(game,"sgt",3))c->mode=1;
    c->variant=2;
    if(match(game,"indy",4))c->mode=3;
    /* FLDZ/FSTS/FSTPS and exact constant loads clear C1, retaining other SW. */
    fp->status&=(uint16_t)~0x200u;
}
