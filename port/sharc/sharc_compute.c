#include "sharc_compute.h"
#include "sharc_integer.h"
#include "sharc_shift.h"
#include "sharc_bits.h"
#include "sharc_aux.h"
#include "sharc_fp_arithmetic.h"
#include "sharc_fp_scale.h"
#include "sharc_condition.h"
#include "sharc_program.h"
#define WORD(token) c->word(c->opaque,(token))
#define READ(token) (*WORD(token))
#define INDIRECT(token) WORD(READ(token))
bool m2_sharc_compute(m2_sharc_compute_context *c,uint32_t entry,uint32_t lhs,
    uint32_t rhs,uint32_t flags,uint32_t *result)
{
    static const struct {uint32_t entry,op;} integer[]={
        {0x460f40,1},{0x460fc0,2},{0x461040,5},{0x4610c0,6},{0x461140,9},{0x4611a0,0xa},
        {0x4614e0,0x21},{0x4613e0,0x22},{0x4611e0,0x25},{0x461260,0x26},{0x4612e0,0x29},
        {0x461360,0x2a},{0x461460,0x30},{0x461520,0x40},{0x461560,0x41},{0x4615a0,0x42},
        {0x4615e0,0x43},{0x461620,0x61},{0x461660,0x62}};
    static const struct {uint32_t entry,op;} shift[]={
        {0x4627a0,0x200},{0x462900,0x204},{0x462960,0x208},{0x462800,0x220},{0x462880,0x224},
        {0x462a20,0x2c0},{0x4629c0,0x2c4},{0x462a60,0x2c8},{0x4bc3f0,0x2cc}};
    unsigned i;
    for(i=0;i<sizeof(integer)/sizeof(integer[0]);i++)if(entry==integer[i].entry)
        return m2_sharc_integer_compute(integer[i].op,lhs,rhs,flags,c->astat,result);
    for(i=0;i<sizeof(shift)/sizeof(shift[0]);i++)if(entry==shift[i].entry) {
        const uint32_t *base=0;
        if(shift[i].op==0x220 || shift[i].op==0x224) {
            uint32_t descriptor=lhs;
            rhs=*INDIRECT(descriptor+4);lhs=*INDIRECT(descriptor+12);
            base=INDIRECT(descriptor+8);
        }
        return m2_sharc_shift_compute(shift[i].op,lhs,rhs,base,c->astat,result);
    }
    switch(entry) {
    case 0x4bc420:case 0x4bc510:case 0x4bc5b0:
        *result=m2_sharc_field_deposit(lhs,rhs,c->astat);return true;
    case 0x4bc470:*result=m2_sharc_field_extract(lhs,rhs,c->astat);return true;
    case 0x4bc4c0:case 0x4bc560: {
        uint32_t value=entry==0x4bc4c0?READ(lhs+12):*INDIRECT(lhs+12);
        uint32_t *base=entry==0x4bc4c0?WORD(lhs+8):INDIRECT(lhs+8);
        *result=m2_sharc_field_merge(value,base,rhs,c->astat);return true;
    }
    case 0x4bc3a0:case 0x4bc310: {
        uint32_t a=*INDIRECT(lhs),b=*INDIRECT(lhs+8);
        uint32_t *sum=INDIRECT(lhs+16),*diff=INDIRECT(lhs+20);
        if(entry==0x4bc3a0){*result=m2_sharc_add_sub(a,b,sum,diff,c->astat);return true;}
        if(!m2_sharc_fp_compound(entry,a,b,0,0,sum,diff,c->astat,c->fp))return false;
        *result=0;return true;
    }
    case 0x4bc270:case 0x4bd1a0:case 0x4bd220:case 0x4bd2a0:case 0x4bd320:
    case 0x4bd3b0:case 0x4bd440:case 0x4bd4b0:case 0x4be220: {
        uint32_t a=*INDIRECT(lhs+4),b=*INDIRECT(lhs+12),x=*INDIRECT(lhs+28),y=*INDIRECT(lhs+32);
        uint32_t *product=INDIRECT(lhs+24),*other=INDIRECT(lhs+16);
        bool ok=entry==0x4bc270?m2_sharc_fp_triple(a,b,x,y,product,other,INDIRECT(lhs+20),c->astat,c->fp):
            m2_sharc_fp_compound(entry,a,b,x,y,product,other,c->astat,c->fp);
        if(!ok)return false;
        *result=0;return true;
    }
    case 0x4bd520:*result=m2_sharc_bad_compute(lhs,*c->pc,c->diagnostic,c->opaque);return true;
    default:break;
    }
    if(m2_sharc_aux(entry,lhs,rhs,c->astat,result))return true;
    if(m2_sharc_fp_simple(entry,lhs,rhs,c->astat,c->fp,result))return true;
    if(m2_sharc_fp_arithmetic(entry,lhs,rhs,c->astat,c->fp,result))return true;
    return m2_sharc_fp_scale(entry,lhs,rhs,c->astat,c->fp,result);
}
bool m2_sharc_dispatch_compute(m2_sharc_compute_context *c,bool move) {
    uint32_t record=*c->current_record,condition=READ(record+8),code,tmp[27],truth;
    uint32_t lhs,rhs,saved=0,result,flags,parity;
    for(code=0;code<32;code++)if(m2_sharc_bind_condition(code,tmp)==condition)break;
    if(code==32 || !m2_sharc_condition(0,code,*c->astat,*c->loop_count,c->stop,&truth))return false;
    if(!truth)return true;
    record=*c->current_record;
    if(move)saved=*INDIRECT(record+40);
    rhs=*INDIRECT(record+56);lhs=*INDIRECT(record+52);
    /* Native TEST EAX,EAX after condition: both wrappers preserve these flags
     * through loads/calls into every helper. Never use ambient host flags. */
    parity=truth&255;parity^=parity>>4;parity^=parity>>2;parity^=parity>>1;
    flags=2u|((parity&1)?0:4u)|((truth>>24)&0x80u);
    if(!m2_sharc_compute(c,READ(record+4),lhs,rhs,flags,&result))return false;
    record=*c->current_record; /* Native reload AFTER helper/diagnostic. */
    *INDIRECT(record+60)=result;
    if(move)*INDIRECT(record+36)=saved;
    return true;
}
#undef WORD
#undef READ
#undef INDIRECT

static bool hook_supported(void *opaque,uint32_t entry) {
    static const uint32_t entries[]={
        0x00460f40,0x00460fc0,0x00461040,0x004610c0,0x00461140,0x004611a0,0x004611e0,0x00461260,
        0x004612e0,0x00461360,0x004613e0,0x00461460,0x004614e0,0x00461520,0x00461560,0x004615a0,
        0x004615e0,0x00461620,0x00461660,0x00461700,0x004617a0,0x00461840,0x004618e0,0x00461980,
        0x00461a40,0x00461ae0,0x00461b80,0x00461c20,0x00461cc0,0x00461d60,0x00461f60,0x00462000,
        0x00462140,0x00462200,0x004622a0,0x00462340,0x004623e0,0x00462480,0x00462700,0x004627a0,
        0x00462800,0x00462880,0x00462900,0x00462960,0x004629c0,0x00462a20,0x00462a60,0x004bc130,
        0x004bc170,0x004bc1b0,0x004bc200,0x004bc210,0x004bc240,0x004bc270,0x004bc310,0x004bc3a0,
        0x004bc3f0,0x004bc420,0x004bc470,0x004bc4c0,0x004bc510,0x004bc560,0x004bc5b0,0x004bc600,
        0x004bc630,0x004bc640,0x004bd1a0,0x004bd220,0x004bd2a0,0x004bd320,0x004bd3b0,0x004bd440,
        0x004bd4b0,0x004bd520,0x004be1d0,0x004be220,
    };
    m2_sharc_compute_context *c=opaque;
    unsigned i;
    bool floating=(entry>=0x461700 && entry<=0x4623e0 && entry!=0x462480)||
        entry==0x462700 || entry==0x4bc130 || entry==0x4bc170 || entry==0x4bc1b0 ||
        entry==0x4bc210 || entry==0x4bc270 || entry==0x4bc310 || entry==0x4be1d0 ||
        (entry>=0x4bd1a0 && entry<=0x4bd4b0) || entry==0x4be220;
    if(floating && (c->fp->control&0x33f)!=0x3f)return false;
    for(i=0;i<sizeof(entries)/sizeof(entries[0]);i++)if(entry==entries[i])return true;
    return false;
}
static bool hook_run(void *opaque,uint32_t op,uint32_t lhs,uint32_t rhs,
    uint32_t flags,uint32_t *status,uint32_t *result) {
    m2_sharc_compute_context copy=*(m2_sharc_compute_context *)opaque;
    copy.astat=status;
    return m2_sharc_compute(&copy,op,lhs,rhs,flags,result);
}
m2_sharc_operation_hooks m2_sharc_compute_hooks(m2_sharc_compute_context *c) {
    m2_sharc_operation_hooks h={c,hook_supported,hook_run};return h;
}
