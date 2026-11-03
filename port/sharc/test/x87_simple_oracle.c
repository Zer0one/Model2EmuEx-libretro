/* Independent x87 instruction-sequence oracle, NOT original executable
 * execution. Build x86_64 and run under Rosetta on Apple Silicon. This catches
 * Unicorn's missing exception flags/SNaN quieting. Physical x86 remains a
 * separate qualification. Inputs/outputs use host little-endian uint32 words.
 */
#include <stdint.h>
#include <stdio.h>
int main(void) {
    uint32_t in[6],out[4];
    while(fread(in,sizeof(in),1,stdin)==1) {
        uint32_t env[7]={in[4]&0xffffu,in[5]&0xffffu,0xffff,0,0,0,0};
        uint32_t lhs=in[1],rhs=in[2],a=0,b=0;
        uint16_t sw=0,cw=0,cmp=0;
        __asm__ volatile("fninit; fldenv %0"::"m"(env):"st","memory");
        if(in[0]==0x461700 || in[0]==0x4617a0 || in[0]==0x461840 || in[0]==0x4618e0 || in[0]==0x461980 || in[0]==0x462700 || in[0]==0x462340 || in[0]==0x4623e0) {
            uint16_t captured;
            uint32_t half=0x3f000000;
            if(in[0]==0x462340)__asm__ volatile("fld1; fdivs %0"::"m"(lhs):"st","memory");
            else if(in[0]==0x4623e0)__asm__ volatile("fld1; flds %0; fsqrt; .byte 0xde,0xf9"::"m"(lhs):"st","memory");
            else if(in[0]==0x462700)__asm__ volatile("flds %0; fmuls %1"::"m"(rhs),"m"(lhs):"st","memory");
            else if(in[0]==0x4617a0 || in[0]==0x4618e0)__asm__ volatile("flds %0; fsubs %1"::"m"(lhs),"m"(rhs):"st","memory");
            else __asm__ volatile("flds %0; fadds %1"::"m"(lhs),"m"(rhs):"st","memory");
            if(in[0]==0x461840 || in[0]==0x4618e0)__asm__ volatile("fabs":::"st");
            if(in[0]==0x461980)__asm__ volatile("fmuls %0"::"m"(half):"st","memory");
            __asm__ volatile("fnstsw %0; fnclex; ftst; fnstsw %1; fnclex; fstps %2"
                :"=m"(captured),"=m"(cmp),"=m"(a)::"st","memory");
            if(in[0]==0x462700)in[3]=(in[3]&~0x2c0u)|((captured&1)?0x200u:0)|((captured&8)?0x80u:0)|((cmp&0x100)?0x40u:0);
            else in[3]=(in[3]&~0x3fu)|0x400u|((captured&1)?0x20u:0)|((captured&8)?2u:0)|((cmp&0x100)?4u:0)|((cmp&0x4000)?1u:0);
            out[0]=a;
        } else if(in[0]==0x461d60 || in[0]==0x462000 || in[0]==0x462140 || in[0]==0x4622a0) {
            uint16_t captured;
            __asm__ volatile("fildl %0"::"m"(rhs):"st","memory");
            if(in[0]==0x4622a0)__asm__ volatile("fildl %0"::"m"(lhs):"st","memory");
            else __asm__ volatile("flds %0"::"m"(lhs):"st","memory");
            __asm__ volatile("fscale":::"st");
            if(in[0]==0x462140)__asm__ volatile("frndint":::"st");
            __asm__ volatile("fnstsw %0; fnclex; ftst; fnstsw %1; fnclex"
                :"=m"(captured),"=m"(cmp)::"st","memory");
            if(in[0]==0x462000 || in[0]==0x462140)__asm__ volatile("fistpl %0":"=m"(a)::"st","memory");
            else __asm__ volatile("fstps %0":"=m"(a)::"st","memory");
            __asm__ volatile("fstp %%st(0)":::"st");
            in[3]=(in[3]&~0x3fu)|0x400u|((captured&1)?0x20u:0)|((captured&8)?2u:0)|
                ((cmp&0x100)?4u:0)|((cmp&0x4000)?1u:0);out[0]=a;
        } else if(in[0]==0x461a40) {
            __asm__ volatile("flds %2; fcoms %3; fnstsw %0; fnclex; fstps %1"
                :"=m"(cmp),"=m"(a):"m"(lhs),"m"(rhs):"st","memory");
            in[3]=(in[3]&~0x3fu)|0x400u|((cmp&1)?0x20u:0)|((cmp&8)?2u:0)|
                ((cmp&0x100)?4u:0)|((cmp&0x4000)?1u:0);out[0]=a;
        } else if(in[0]==0x461ae0 || in[0]==0x461b80 || in[0]==0x461c20 || in[0]==0x461cc0 || in[0]==0x461f60 || in[0]==0x462200) {
            uint16_t captured;
            if(in[0]==0x462200)__asm__ volatile("fildl %0"::"m"(lhs):"st","memory");
            else __asm__ volatile("flds %0"::"m"(lhs):"st","memory");
            if(in[0]==0x461ae0)__asm__ volatile("fchs":::"st");
            if(in[0]==0x461b80)__asm__ volatile("fabs":::"st");
            if(in[0]==0x461cc0)__asm__ volatile("frndint":::"st");
            __asm__ volatile("fnstsw %0; fnclex; ftst; fnstsw %1; fnclex"
                :"=m"(captured),"=m"(cmp)::"st","memory");
            if(in[0]==0x461f60)__asm__ volatile("fistpl %0":"=m"(a)::"st","memory");
            else __asm__ volatile("fstps %0":"=m"(a)::"st","memory");
            in[3]=(in[3]&~0x3fu)|0x400u|((captured&1)?0x20u:0)|((captured&8)?2u:0)|
                ((cmp&0x100)?4u:0)|((cmp&0x4000)?1u:0);
            out[0]=a;
        } else if(in[0]==0x4be1d0) {
            __asm__ volatile("flds %2; fsts %0; flds %3; fabs; fld %%st(1); fabs; fcomp %%st(1); fnstsw %1"
                :"=m"(a),"=m"(cmp):"m"(lhs),"m"(rhs):"st","memory");
            if((cmp&0x4500)==0x100 || (cmp&0x4500)==0x4000) {
                __asm__ volatile("fstp %%st(0); fstp %%st(0)":::"st");out[0]=a;
            } else {
                __asm__ volatile("fldz; fcomp %%st(2); fnstsw %0; fstp %%st(1)":"=m"(cmp)::"st","memory");
                if(!(cmp&0x4100))__asm__ volatile("fchs":::"st");
                __asm__ volatile("fstps %0":"=m"(a)::"st","memory");out[0]=a;
            }
        } else if(in[0]==0x4bc130 || in[0]==0x4bc170) {
            __asm__ volatile("flds %3; fsts %0; flds %4; fcom %%st(1); fnstsw %2; fstp %%st(1); fstps %1"
                :"=m"(a),"=m"(b),"=m"(cmp):"m"(lhs),"m"(rhs):"st","memory");
            out[0]=((in[0]==0x4bc130)?(cmp&0x4500)==0x100:(cmp&0x4500)==0)?a:b;
        } else if(in[0]==0x4bc1b0) {
            __asm__ volatile("flds %1; fldz; fucompp; fnstsw %0":"=m"(cmp):"m"(lhs):"st","memory");
            in[3]&=~2u;
            if((cmp&0x4500)==0x4000){in[3]|=2;out[0]=0xff800000;}
            else out[0]=((lhs>>23)&255u)-127u;
        } else if(in[0]==0x4bc210) {
            int64_t value;
            uint16_t trunc=(uint16_t)(in[4]|0xc00);
            __asm__ volatile("flds %1; fnstcw %2; fldcw %3; fistpq %0; fldcw %2"
                :"=m"(value),"+m"(lhs),"=m"(cw):"m"(trunc):"st","memory");
            out[0]=(uint32_t)value;
        } else return 2;
        __asm__ volatile("fnstsw %0; fnstcw %1":"=m"(sw),"=m"(cw)::"memory");
        out[1]=in[3];out[2]=cw;out[3]=sw;
        if(fwrite(out,sizeof(out),1,stdout)!=1)return 3;
    }
    return ferror(stdin)?1:0;
}
