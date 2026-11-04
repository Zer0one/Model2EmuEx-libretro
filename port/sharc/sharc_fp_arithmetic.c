#include "sharc_fp_arithmetic.h"
#include "sharc_fp_scale.h"

#include "../x87/x87_binary32.h"

bool m2_sharc_fp_arithmetic(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t *astat,m2_sharc_fp_state *fp,uint32_t *result)
{
    bool multiply=entry==0x462700;
    bool inverse=entry==0x462340 || entry==0x4623e0;
    bool subtract=entry==0x4617a0 || entry==0x4618e0;
    unsigned mode=(fp->control>>10)&3;
    uint16_t sw=fp->status,cc;
    number n;
    if((fp->control&0x33f)!=0x3f || (!multiply && !inverse && entry!=0x461700 &&
        entry!=0x4617a0 && entry!=0x461840 && entry!=0x4618e0 && entry!=0x461980))return false;
    if(inverse) {
        n=unpack(lhs);
        if(issnan32(lhs))sw|=1;
        if(entry==0x4623e0)n=square_root(n,mode,&sw);
        n=reciprocal(n,mode,&sw);
    } else n=binary(multiply?rhs:lhs,multiply?lhs:rhs,multiply,subtract,mode,&sw);
    if(entry==0x461840 || entry==0x4618e0){n.sign=0;n.nan&=0x7fffffffu;}
    if(entry==0x461980 && n.kind==FINITE && n.sig)n.exponent--; /* FMUL 0.5 */
    cc=n.kind==NAN_VALUE?0x4500:n.kind==FINITE&&!n.sig?0x4000:n.sign?0x100:0;
    /* Native flags observe the extended-exponent intermediate BEFORE FSTPS.
     * Binary32 overflow/underflow during that store remains x87 state for the
     * NEXT operation. It must not retroactively become this operation's AV. */
    if(multiply)*astat=(*astat&~0x2c0u)|((sw&1)?0x200u:0)|((sw&8)?0x80u:0)|((cc&0x100)?0x40u:0);
    else *astat=(*astat&~0x3fu)|0x400u|((sw&1)?0x20u:0)|((sw&8)?2u:0)|((cc&0x100)?4u:0)|((cc&0x4000)?1u:0);
    sw=(uint16_t)((sw&~0xc7ffu)|cc);
    *result=store32(n,mode,&sw);fp->status=sw;return true;
}

/* Compound routines keep extended temporaries alive across FSTS. Calling the
 * scalar helper would lose that value AND clear exceptions too early. */
static number load32(uint32_t x,uint16_t *sw) {
    if(issnan32(x))*sw|=1;
    if((x&0x7fffffffu) && !(x&0x7f800000u))*sw|=2;
    return unpack(x);
}
static uint16_t compare_zero(number n,bool reverse,bool ordered,uint16_t *sw) {
    uint16_t cc;
    if(n.kind==NAN_VALUE){cc=0x4500;if(ordered)*sw|=1;}
    else if(n.kind==FINITE && !n.sig)cc=0x4000;
    else cc=(n.sign!=reverse)?0x100:0;
    *sw=(uint16_t)((*sw&~0x4700u)|cc);return cc;
}
bool m2_sharc_fp_compound(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t mul_lhs,uint32_t mul_rhs,uint32_t *first,uint32_t *second,
    uint32_t *astat,m2_sharc_fp_state *fp)
{
    number a,b;
    unsigned mode=(fp->control>>10)&3;
    uint16_t sw=fp->status,cc;
    bool pair=entry==0x4bc310;
    bool scale=entry==0x4bd320 || entry==0x4bd3b0;
    if((fp->control&0x33f)!=0x3f || (!pair && !scale && entry!=0x4bd1a0 && entry!=0x4bd220 &&
        entry!=0x4bd2a0 && entry!=0x4bd440 && entry!=0x4bd4b0 && entry!=0x4be220))return false;
    a=pair?binary(rhs,lhs,false,false,mode,&sw):binary(mul_rhs,mul_lhs,true,false,mode,&sw);
    if(scale) {
        uint32_t spill=store32(a,mode,&sw),value;
        m2_sharc_fp_state inner={fp->control,sw};
        /* These two originals spill the product BEFORE calling the conversion
         * helper. Its overflow/underflow can affect the helper's ASTAT flags. */
        (void)m2_sharc_fp_scale(entry==0x4bd320?0x462140:0x4622a0,lhs,rhs,astat,&inner,&value);
        sw=inner.status;a=load32(spill,&sw);
        *first=store32(a,mode,&sw);*second=value;
        /* Original FILD signed(result), then FADD 2^32 for bit 31, compares
         * the returned BITS as an unsigned integer. This even applies to
         * 4bd3b0's floating result. Preserve it; do not reinterpret as float.
         * Only that high-bit FADD rounds the integer to PC=24. */
        if((value&0x80000000u) && (value&255u))sw|=0x20;
        *astat&=~0x45u;
        if(!compare_zero(a,true,true,&sw))*astat|=0x40;
        if(!value)*astat|=1;
        sw=(uint16_t)((sw&~0x4700u)|(value?0:0x4000));
        fp->status=sw;return true;
    }
    if(pair || entry==0x4bd440)b=binary(lhs,rhs,false,true,mode,&sw);
    else if(entry==0x4bd4b0 || entry==0x4bd2a0){
        b=binary(rhs,lhs,false,false,mode,&sw);
        if(entry==0x4bd2a0 && b.kind==FINITE && b.sig)b.exponent--;
    }
    else if(entry==0x4be220){b=load32(lhs,&sw);b.sign=0;b.nan&=0x7fffffffu;}
    else {
        number left=unpack(lhs),right=load32(rhs,&sw);
        bool unordered=left.kind==NAN_VALUE || right.kind==NAN_VALUE;
        bool less=false,greater=false;
        if(unordered)sw|=1; /* FCOM, not FUCOM: even quiet NaNs are invalid. */
        else {
            uint32_t x=lhs&0x7fffffffu,y=rhs&0x7fffffffu;
            if(x || y) {
                less=right.sign!=left.sign?right.sign!=0:(right.sign?y>x:y<x);
                greater=right.sign!=left.sign?right.sign==0:(right.sign?y<x:y>x);
            }
            if((lhs&0x7fffffffu) && !(lhs&0x7f800000u))sw|=2;
        }
        b=load32((entry==0x4bd1a0?greater:less)?lhs:rhs,&sw);
    }
    *first=store32(a,mode,&sw);
    *second=store32(b,mode,&sw);
    /* Deliberately after BOTH writes: result pointers may alias ASTAT. */
    *astat&=pair?~5u:~0x45u;
    if(pair) {
        if((a.kind==FINITE&&!a.sig)||(b.kind==FINITE&&!b.sig))*astat|=1;
        cc=compare_zero(a,true,true,&sw);
        if(!cc)*astat|=4; /* Zero > sum, ordered. Original skips final compare. */
        else if(compare_zero(b,false,true,&sw)==0x100)*astat|=4;
    } else {
        if(!compare_zero(a,true,true,&sw))*astat|=0x40;
        if(compare_zero(b,false,true,&sw)==0x100)*astat|=4;
        if(compare_zero(b,false,false,&sw)==0x4000)*astat|=1;
    }
    fp->status=sw;return true;
}
bool m2_sharc_fp_triple(uint32_t lhs,uint32_t rhs,uint32_t mul_lhs,uint32_t mul_rhs,
    uint32_t *product,uint32_t *sum,uint32_t *difference,uint32_t *astat,m2_sharc_fp_state *fp)
{
    unsigned mode=(fp->control>>10)&3;
    uint16_t sw=fp->status,cc;
    number a,b,c;
    if((fp->control&0x33f)!=0x3f)return false;
    a=binary(mul_rhs,mul_lhs,true,false,mode,&sw);
    b=binary(lhs,rhs,false,false,mode,&sw);
    c=binary(lhs,rhs,false,true,mode,&sw);
    *product=store32(a,mode,&sw);*sum=store32(b,mode,&sw);*difference=store32(c,mode,&sw);
    *astat&=~0x45u;
    if((b.kind==FINITE&&!b.sig)||(c.kind==FINITE&&!c.sig))*astat|=1;
    cc=compare_zero(c,true,true,&sw);
    if(!cc || !compare_zero(b,true,true,&sw))*astat|=4;
    if(compare_zero(a,false,true,&sw)==0x100)*astat|=0x40;
    fp->status=sw;return true;
}
