#include "sharc_fp_scale.h"

typedef struct { uint64_t mag;int64_t power;unsigned sign,kind;uint32_t nan; } scaled;
enum { FINITE,INF,NAN_VALUE };
static unsigned top_bit(uint64_t x){unsigned n=0;while(x>>1){x>>=1;n++;}return n;}
static uint64_t round_shift(uint64_t x,int64_t shift,unsigned mode,unsigned sign,bool *inexact,bool *up) {
    uint64_t quotient,residue;
    *inexact=*up=false;
    if(shift<=0)return x<<(unsigned)-shift; /* Caller bounds left shifts. */
    quotient=shift>=64?0:x>>(unsigned)shift;
    residue=shift>=64?x:x&((UINT64_C(1)<<(unsigned)shift)-1);
    *inexact=residue!=0;
    if(residue) {
        if(mode==1)*up=sign!=0;
        else if(mode==2)*up=sign==0;
        else if(mode==0 && shift<64) {
            uint64_t half=UINT64_C(1)<<((unsigned)shift-1);
            *up=residue>half || (residue==half && (quotient&1));
        }
    }
    return quotient+*up;
}
static uint32_t float_store(scaled n,unsigned mode,uint16_t *sw) {
    uint32_t sign=n.sign<<31;
    int64_t exponent,shift;
    uint64_t sig;
    bool inexact,up;
    if(n.kind==NAN_VALUE)return n.nan;
    if(n.kind==INF)return sign|0x7f800000u;
    if(!n.mag)return sign;
    exponent=n.power+top_bit(n.mag);
    if(exponent<-126) {
        sig=round_shift(n.mag,-149-n.power,mode,n.sign,&inexact,&up);
        if(inexact)*sw|=0x30;
        if(up)*sw|=0x200;
        return sign|(uint32_t)sig;
    }
    shift=(int64_t)top_bit(n.mag)-23;
    sig=round_shift(n.mag,shift,mode,n.sign,&inexact,&up);
    if(sig==0x1000000){sig>>=1;exponent++;}
    if(exponent>127) {
        bool infinity=mode==0 || (mode==1 && n.sign) || (mode==2 && !n.sign);
        *sw|=0x28;
        if(infinity)*sw|=0x200;
        return sign|(infinity?0x7f800000u:0x7f7fffffu);
    }
    if(inexact)*sw|=0x20;
    if(up)*sw|=0x200;
    return sign|((uint32_t)(exponent+127)<<23)|((uint32_t)sig&0x7fffff);
}
static uint32_t integer_store(scaled n,unsigned mode,uint16_t *sw) {
    uint64_t magnitude;
    bool inexact,up;
    if(n.kind!=FINITE || (n.mag && n.power+top_bit(n.mag)>31)){*sw|=1;return 0x80000000;}
    if(!n.mag)return 0;
    magnitude=round_shift(n.mag,-n.power,mode,n.sign,&inexact,&up);
    if(magnitude>(n.sign?UINT64_C(0x80000000):UINT64_C(0x7fffffff))){*sw|=1;return 0x80000000;}
    if(inexact)*sw|=0x20;
    if(up)*sw|=0x200;
    return n.sign?0u-(uint32_t)magnitude:(uint32_t)magnitude;
}
bool m2_sharc_fp_scale(uint32_t entry,uint32_t lhs,uint32_t rhs,
    uint32_t *astat,m2_sharc_fp_state *fp,uint32_t *result)
{
    scaled n={0,0,lhs>>31,FINITE,0};
    uint16_t sw=fp->status,cc;
    unsigned mode=(fp->control>>10)&3;
    bool integer_input=entry==0x4622a0,inexact,up;
    int64_t exponent;
    if((fp->control&0x33f)!=0x3f || (entry!=0x461d60 && entry!=0x462000 && entry!=0x462140 && !integer_input))return false;
    if(integer_input)n.mag=n.sign?0u-lhs:lhs;
    else {
        unsigned e=(lhs>>23)&255;
        n.mag=lhs&0x7fffff;
        if(e==255) {
            n.kind=n.mag?NAN_VALUE:INF;n.nan=lhs|0x400000;
            if(n.mag && !(lhs&0x400000))sw|=1;
        } else {
            if(e)n.mag|=0x800000;
            n.power=e?(int)e-150:-149;
        }
    }
    if(n.kind==FINITE && n.mag) {
        /* FILD RHS is signed INT32, not an exponent byte or host shift count. */
        n.power+=(rhs&0x80000000u)?-(int64_t)(0u-rhs):(int64_t)rhs;
        exponent=n.power+top_bit(n.mag);
        if(exponent>16383) {
            bool infinity=mode==0 || (mode==1 && n.sign) || (mode==2 && !n.sign);
            sw|=0x28;
            if(infinity)n.kind=INF;
            else {n.mag=UINT64_MAX;n.power=16383-63;}
        } else if(n.power<-16445) {
            /* FSCALE retains the x87 exponent domain. Only lost bits at its
             * extended subnormal boundary can turn the intermediate to zero. */
            n.mag=round_shift(n.mag,-16445-n.power,mode,n.sign,&inexact,&up);
            n.power=-16445;
            if(inexact)sw|=0x30;
        }
        if(entry==0x462140 && n.kind==FINITE && n.mag && n.power<0) {
            n.mag=round_shift(n.mag,-n.power,mode,n.sign,&inexact,&up);n.power=0;
            if(inexact)sw|=0x20;
        }
    }
    cc=n.kind==NAN_VALUE?0x4500:n.kind==FINITE&&!n.mag?0x4000:n.sign?0x100:0;
    *astat=(*astat&~0x3fu)|0x400u|((sw&1)?0x20u:0)|((sw&8)?2u:0)|((cc&0x100)?4u:0)|((cc&0x4000)?1u:0);
    sw=(uint16_t)((sw&~0xc7ffu)|cc);
    *result=(entry==0x462000 || entry==0x462140)?integer_store(n,mode,&sw):float_store(n,mode,&sw);
    /* Discarding the exponent operand with FSTP ST(0) clears C1 AFTER the
     * result store. The other conversion helpers do not have this last pop. */
    fp->status=(uint16_t)(sw&~0x200u);return true;
}
