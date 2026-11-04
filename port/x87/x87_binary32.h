#ifndef M2_X87_BINARY32_H
#define M2_X87_BINARY32_H

#include <stdbool.h>
#include <stdint.h>

/* Shared reconstruction of the original x87 PC=24 arithmetic, independent
 * of guest DSP architecture. Extracted unchanged from the verified SHARC
 * implementation. Extended exponent survives until store32; this is not
 * interchangeable with host float arithmetic. Exceptions and NaN selection
 * follow the native instruction sequences, not the guest hardware manual. */
typedef struct { uint32_t sig,nan;int exponent;unsigned sign,kind; } number;
enum { FINITE,INFINITY_VALUE,NAN_VALUE };
static inline bool isnan32(uint32_t x){return (x&0x7fffffffu)>0x7f800000u;}
static inline bool issnan32(uint32_t x){return isnan32(x)&&!(x&0x400000u);}
static inline number unpack(uint32_t x) {
    number n={0,0,0,x>>31,FINITE};
    unsigned e=(x>>23)&255;
    n.sig=x&0x7fffffu;
    if(e==255){n.kind=n.sig?NAN_VALUE:INFINITY_VALUE;n.nan=x|0x400000u;return n;}
    n.exponent=e?(int)e-127:-126;
    if(e)n.sig|=0x800000u;
    if(n.sig)while(!(n.sig&0x800000u)){n.sig<<=1;n.exponent--;}
    return n;
}
static inline uint64_t jam(uint64_t x,unsigned shift) {
    if(!shift)return x;
    if(shift>=64)return x!=0;
    return (x>>shift)|((x&((UINT64_C(1)<<shift)-1))!=0);
}
static inline bool increment(unsigned mode,unsigned sign,uint64_t quotient,uint64_t residue,unsigned shift) {
    if(!residue)return false;
    if(mode==1)return sign!=0;
    if(mode==2)return sign==0;
    if(mode==3 || shift>=64)return false;
    return residue>(UINT64_C(1)<<(shift-1)) ||
        (residue==(UINT64_C(1)<<(shift-1)) && (quotient&1));
}
static inline number normalize(uint64_t sig,int exponent,unsigned sign,unsigned mode,uint16_t *sw) {
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
static inline number binary(uint32_t destination,uint32_t source,bool multiply,bool subtract,unsigned mode,uint16_t *sw) {
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
static inline uint32_t store32(number n,unsigned mode,uint16_t *sw) {
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
static inline number square_root(number n,unsigned mode,uint16_t *sw) {
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
static inline number reciprocal(number n,unsigned mode,uint16_t *sw) {
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

#endif
