#include "sharc_fp.h"

static bool nan32(uint32_t x) { return (x&0x7fffffffu)>0x7f800000u; }
static bool snan32(uint32_t x) { return nan32(x) && !(x&0x400000u); }
static bool denormal32(uint32_t x) {
    return (x&0x7fffffffu)!=0 && (x&0x7f800000u)==0;
}
static uint32_t quiet32(uint32_t x) { return nan32(x)?x|0x400000u:x; }
static uint16_t compare32(uint32_t a,uint32_t b) {
    uint32_t ka,kb;
    if(nan32(a)||nan32(b))return 0x4500;
    if(a==b || ((a|b)&0x7fffffffu)==0)return 0x4000;
    ka=(a&0x80000000u)?~a:a^0x80000000u;
    kb=(b&0x80000000u)?~b:b^0x80000000u;
    return ka<kb?0x100:0;
}
static uint32_t round_integer32(uint32_t x,unsigned mode) {
    uint32_t sign=x&0x80000000u,mag=x&0x7fffffffu,mask,truncated,fraction,unit;
    int e=(int)(mag>>23)-127;
    bool increment;
    if(e>=23 || !mag)return x;
    if(e<0) {
        increment=mode==0?(mag>0x3f000000u):
            (mode==1?sign!=0:mode==2?sign==0:false);
        return sign|(increment?0x3f800000u:0);
    }
    unit=1u<<(unsigned)(23-e);mask=unit-1;fraction=mag&mask;
    truncated=mag&~mask;
    increment=mode==0?(fraction>unit/2 || (fraction==unit/2 && (truncated&unit))):
        (fraction!=0 && (mode==1?sign!=0:mode==2?sign==0:false));
    return sign|(truncated+(increment?unit:0));
}
bool m2_sharc_fp_simple(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t *astat,m2_sharc_fp_state *fp,uint32_t *result)
{
    uint32_t out;
    uint16_t sw=(uint16_t)(fp->status&~0x200u),cc;
    bool flag_unary=entry==0x461ae0 || entry==0x461b80 ||
        entry==0x461c20 || entry==0x461cc0 || entry==0x461f60 || entry==0x462200;
    bool unary=entry==0x4bc1b0 || entry==0x4bc210 || flag_unary;
    if((fp->control&0x3f)!=0x3f ||
       (!unary && entry!=0x4bc130 && entry!=0x4bc170 && entry!=0x4be1d0 && entry!=0x461a40))return false;
    /* FLD raises DE for binary32 denormals and quiets SNaN with IE. Unicorn
     * 2.1.4 omits these effects; do NOT preserve that oracle defect as ElSemi
     * behavior. The instruction-sequence x87 oracle checks them separately. */
    if(entry!=0x462200) {
        if(denormal32(lhs) || (!unary && denormal32(rhs)))sw|=2;
        if(snan32(lhs) || (!unary && snan32(rhs)))sw|=1;
    }
    if(entry==0x461a40) {
        cc=compare32(lhs,rhs);
        if(nan32(lhs)||nan32(rhs))sw|=1;
        *astat=(*astat&~0x3fu)|0x400u|((sw&1)?0x20u:0)|((sw&8)?2u:0)|
            ((cc&0x100)?4u:0)|((cc&0x4000)?1u:0);
        sw=(uint16_t)((sw&~0xc7ffu)|cc);out=quiet32(lhs);
    } else
    if(flag_unary) {
        out=quiet32(lhs);
        if(entry==0x461ae0)out^=0x80000000u;
        else if(entry==0x461b80)out&=0x7fffffffu;
        else if(entry==0x461cc0)out=round_integer32(out,(fp->control>>10)&3);
        /* FNSTSW is BEFORE FNCLEX: even a plain register pass can import
         * incoming sticky x87 IE/OE into AI/AV. Preserve this original coupling;
         * computing flags solely from this operation would change behavior. */
        *astat=(*astat&~0x3fu)|0x400u|((sw&1)?0x20u:0)|((sw&8)?2u:0);
        cc=entry==0x462200?(lhs==0?0x4000:(lhs&0x80000000u)?0x100:0):compare32(out,0);
        if(cc&0x100)*astat|=4;
        if(cc&0x4000)*astat|=1;
        /* Two FNCLEX instructions discard exceptions, including FTST's IE.
         * The final binary32 store is exact for these four unary operations. */
        sw=(uint16_t)((sw&~0xc7ffu)|cc);
        if(entry==0x461f60) {
            uint32_t rounded=round_integer32(out,(fp->control>>10)&3);
            uint32_t mag=rounded&0x7fffffffu,sign=rounded>>31;
            int e=(int)(mag>>23)-127;
            /* FTST/ASTAT precedes FISTP: final conversion exceptions are NOT
             * reflected in this operation's AI/AV, but survive for the next. */
            if(e>31 || (e==31 && (!sign || (mag&0x7fffffu)))) {out=0x80000000u;sw|=1;}
            else {
                uint32_t significand=(mag&0x7fffffu)|0x800000u;
                uint32_t value=e<0?0:e>=23?significand<<(unsigned)(e-23):significand>>(unsigned)(23-e);
                if(rounded!=out) {
                    sw|=0x20;
                    if(mag>(out&0x7fffffffu))sw|=0x200;
                }
                out=sign?0u-value:value;
            }
        } else if(entry==0x462200) {
            uint32_t sign=lhs&0x80000000u,mag=sign?0u-lhs:lhs;
            if(!mag)out=0;
            else {
                unsigned e=0,shift,mode=(fp->control>>10)&3;
                uint32_t n=mag,sig,fraction=0,unit=1;
                bool increment=false;
                while(n>>1){n>>=1;e++;}
                if(e<=23)sig=mag<<(23-e);
                else {
                    shift=e-23;unit=1u<<shift;fraction=mag&(unit-1);sig=mag>>shift;
                    increment=mode==0?(fraction>unit/2 || (fraction==unit/2 && (sig&1))):
                        (fraction && (mode==1?sign!=0:mode==2?sign==0:false));
                }
                if(fraction)sw|=0x20;
                if(increment){sw|=0x200;sig++;}
                out=sign+((e+127)<<23)+(sig-0x800000u);
            }
        }
    } else if(entry==0x4be1d0) {
        cc=compare32(lhs&0x7fffffffu,rhs&0x7fffffffu);
        if(nan32(lhs)||nan32(rhs))sw|=1;
        if(cc==0x100 || cc==0x4000)out=quiet32(lhs);
        else {
            cc=compare32(0,lhs);
            out=quiet32(rhs)&0x7fffffffu;
            if(cc==0)out|=0x80000000u;
        }
        sw=(uint16_t)((sw&~0x4500u)|cc);
    } else if(!unary) {
        cc=compare32(rhs,lhs); /* Original FCOM compares RHS against LHS. */
        sw=(uint16_t)((sw&~0x4500u)|cc);
        if(nan32(lhs)||nan32(rhs))sw|=1; /* FCOM, not FUCOM. */
        out=quiet32((entry==0x4bc130?cc==0x100:cc==0)?lhs:rhs);
    } else if(entry==0x4bc1b0) {
        cc=compare32(0,lhs); /* FUCOMPP: quiet NaNs do not raise IE. */
        sw=(uint16_t)((sw&~0x4500u)|cc);
        *astat&=~2u;
        if((lhs&0x7fffffffu)==0) { *astat|=2;out=0xff800000u; }
        else out=((lhs>>23)&255u)-127u;
    } else {
        uint32_t exponent=(lhs>>23)&255u,sign=lhs>>31;
        int e=(int)exponent-127;
        uint64_t magnitude=0;
        bool invalid=exponent==255 || e>63 ||
            (e==63 && (!sign || (lhs&0x7fffffu)));
        /* FISTP is to signed INT64, then only its LOW WORD is returned. A
         * binary32 outside INT32 range is not automatically invalid here. */
        if(invalid)sw|=1;
        else if(e<0) { if(lhs&0x7fffffffu)sw|=0x20; }
        else {
            uint32_t significand=(lhs&0x7fffffu)|0x800000u;
            if(e>=23)magnitude=(uint64_t)significand<<(unsigned)(e-23);
            else {
                unsigned shift=(unsigned)(23-e);
                magnitude=significand>>shift;
                if(significand&((1u<<shift)-1u))sw|=0x20;
            }
        }
        out=invalid?0:(uint32_t)(sign?0u-magnitude:magnitude);
        /* Temporary RC=truncate is restored, including caller PC/RC bits. */
    }
    fp->status=sw;
    *result=out;
    return true;
}
