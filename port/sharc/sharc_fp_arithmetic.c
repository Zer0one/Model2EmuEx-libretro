#include "sharc_fp_arithmetic.h"
#include "sharc_fp_scale.h"

typedef struct { uint32_t sig,nan;int exponent;unsigned sign,kind; } number;
enum { FINITE,INFINITY_VALUE,NAN_VALUE };
static bool isnan32(uint32_t x){return (x&0x7fffffffu)>0x7f800000u;}
static bool issnan32(uint32_t x){return isnan32(x)&&!(x&0x400000u);}
static number unpack(uint32_t x) {
    number n={0,0,0,x>>31,FINITE};
    unsigned e=(x>>23)&255;
    n.sig=x&0x7fffffu;
    if(e==255){n.kind=n.sig?NAN_VALUE:INFINITY_VALUE;n.nan=x|0x400000u;return n;}
    n.exponent=e?(int)e-127:-126;
    if(e)n.sig|=0x800000u;
    if(n.sig)while(!(n.sig&0x800000u)){n.sig<<=1;n.exponent--;}
    return n;
}
static uint64_t jam(uint64_t x,unsigned shift) {
    if(!shift)return x;
    if(shift>=64)return x!=0;
    return (x>>shift)|((x&((UINT64_C(1)<<shift)-1))!=0);
}
static bool increment(unsigned mode,unsigned sign,uint64_t quotient,uint64_t residue,unsigned shift) {
    if(!residue)return false;
    if(mode==1)return sign!=0;
    if(mode==2)return sign==0;
    if(mode==3 || shift>=64)return false;
    return residue>(UINT64_C(1)<<(shift-1)) ||
        (residue==(UINT64_C(1)<<(shift-1)) && (quotient&1));
}
static number normalize(uint64_t sig,int exponent,unsigned sign,unsigned mode,uint16_t *sw) {
    number n={0,0,exponent,sign,FINITE};
    uint64_t fraction;
    if(!sig)return n;
    if(sig&(UINT64_C(1)<<61)){sig=jam(sig,1);n.exponent++;}
    while(!(sig&(UINT64_C(1)<<60))){sig<<=1;n.exponent--;}
    n.sig=(uint32_t)(sig>>37);fraction=sig&((UINT64_C(1)<<37)-1);
    if(fraction)*sw|=0x20;
    if(increment(mode,sign,n.sig,fraction,37))n.sig++;
    if(n.sig==0x1000000u){n.sig>>=1;n.exponent++;}
    return n;
}
static number binary(uint32_t destination,uint32_t source,bool multiply,bool subtract,unsigned mode,uint16_t *sw) {
    number a=unpack(destination),b=unpack(source),n=a;
    if((destination&0x7fffffffu) && !(destination&0x7f800000u))*sw|=2;
    if(issnan32(destination)||issnan32(source))*sw|=1;
    if(a.kind==NAN_VALUE || b.kind==NAN_VALUE) {
        /* FLD has already quieted the destination before memory arithmetic.
         * A remaining source SNaN yields an existing destination QNaN. */
        if(a.kind!=NAN_VALUE)return b;
        if(b.kind!=NAN_VALUE || issnan32(source))return a;
        if((a.nan&0x7fffffffu)!=(b.nan&0x7fffffffu))
            return (a.nan&0x7fffffffu)>(b.nan&0x7fffffffu)?a:b;
        return a.sign?b:a;
    }
    if((source&0x7fffffffu) && !(source&0x7f800000u))*sw|=2;
    if(subtract)b.sign^=1;
    if(multiply) {
        n.sign=a.sign^b.sign;
        if((a.kind==INFINITY_VALUE && b.kind==FINITE && !b.sig) ||
           (b.kind==INFINITY_VALUE && a.kind==FINITE && !a.sig)) {
            n.kind=NAN_VALUE;n.nan=0xffc00000u;*sw|=1;return n;
        }
        if(a.kind==INFINITY_VALUE || b.kind==INFINITY_VALUE){n.kind=INFINITY_VALUE;return n;}
        if(!a.sig || !b.sig){n.sig=0;return n;}
        return normalize(((uint64_t)a.sig*b.sig)<<14,a.exponent+b.exponent,n.sign,mode,sw);
    }
    if(a.kind==INFINITY_VALUE || b.kind==INFINITY_VALUE) {
        if(a.kind==b.kind && a.sign!=b.sign){n.kind=NAN_VALUE;n.nan=0xffc00000u;*sw|=1;return n;}
        return a.kind==INFINITY_VALUE?a:b;
    }
    if(!a.sig && !b.sig){n.sign=a.sign==b.sign?a.sign:mode==1;return n;}
    if(!a.sig)return b;
    if(!b.sig)return a;
    if(a.exponent<b.exponent || (a.exponent==b.exponent && a.sig<b.sig)){number t=a;a=b;b=t;}
    {
        uint64_t x=(uint64_t)a.sig<<37,y=jam((uint64_t)b.sig<<37,(unsigned)(a.exponent-b.exponent));
        uint64_t value=a.sign==b.sign?x+y:x-y;
        return normalize(value,a.exponent,value?a.sign:mode==1,mode,sw);
    }
}
static uint32_t store32(number n,unsigned mode,uint16_t *sw) {
    uint32_t sign=n.sign<<31;
    if(n.kind==NAN_VALUE)return n.nan;
    if(n.kind==INFINITY_VALUE)return sign|0x7f800000u;
    if(!n.sig)return sign;
    if(n.exponent>127) {
        bool infinity=mode==0 || (mode==1 && n.sign) || (mode==2 && !n.sign);
        *sw|=0x28;
        if(infinity)*sw|=0x200;
        return sign|(infinity?0x7f800000u:0x7f7fffffu);
    }
    if(n.exponent>=-126)return sign|((uint32_t)(n.exponent+127)<<23)|(n.sig&0x7fffffu);
    {
        unsigned shift=(unsigned)(-126-n.exponent);
        uint32_t quotient=shift>=32?0:n.sig>>shift;
        uint64_t residue=shift>=32?n.sig:n.sig&((UINT64_C(1)<<shift)-1);
        bool up=increment(mode,n.sign,quotient,residue,shift);
        if(residue)*sw|=0x30;
        if(up){quotient++;*sw|=0x200;}
        return sign|quotient;
    }
}
static number square_root(number n,unsigned mode,uint16_t *sw) {
    uint64_t radicand,root=0,bit;
    unsigned odd;
    if(n.kind==NAN_VALUE || (n.kind==FINITE && !n.sig))return n;
    if(n.sign){n.kind=NAN_VALUE;n.nan=0xffc00000u;*sw|=1;return n;}
    if(n.kind==INFINITY_VALUE)return n;
    odd=n.exponent%2!=0;
    radicand=(uint64_t)n.sig<<(37+odd);
    for(bit=UINT64_C(1)<<31;bit;bit>>=1) {
        uint64_t candidate=root|bit;
        if(candidate*candidate<=radicand)root=candidate;
    }
    if(root*root!=radicand)root|=1; /* Remaining fractional bits are sticky. */
    return normalize(root<<30,(n.exponent-(int)odd)/2,0,mode,sw);
}
static number reciprocal(number n,unsigned mode,uint16_t *sw) {
    if(n.kind==NAN_VALUE)return n;
    if(n.kind==INFINITY_VALUE){n.kind=FINITE;n.sig=0;return n;}
    if(!n.sig){n.kind=INFINITY_VALUE;*sw|=4;return n;}
    {
        uint64_t numerator=UINT64_C(0x800000)<<31;
        uint64_t quotient=numerator/n.sig,remainder=numerator%n.sig;
        if(remainder)quotient|=1;
        return normalize(quotient<<29,-n.exponent,n.sign,mode,sw);
    }
}
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
