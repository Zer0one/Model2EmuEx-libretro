/* Independent transcription of 004bc270's three-result x87 sequence. */
#include <stdint.h>
#include <stdio.h>
int main(void) {
    uint32_t in[8],out[6];
    while(fread(in,sizeof(in),1,stdin)==1) {
        uint32_t env[7]={in[5],in[6],0xffff,0,0,0,0},a=in[0],b=in[1],x=in[2],y=in[3],status=in[4];
        uint32_t product,sum,difference;uint16_t cc,sw,cw;
        __asm__ volatile("fninit; fldenv %0"::"m"(env):"st","memory");
        __asm__ volatile("flds %3; fmuls %2; flds %0; fadds %1; flds %0; fsubs %1"::"m"(a),"m"(b),"m"(x),"m"(y):"st","memory");
        __asm__ volatile("fxch %%st(2); fsts %0; fxch %%st(1); fsts %1; fxch %%st(2); fsts %2":"=m"(product),"=m"(sum),"=m"(difference)::"st","memory");
        if(in[7]&1)status=product;
        if(in[7]&2)status=sum;
        if(in[7]&4)status=difference;
        status&=~0x45u;
        __asm__ volatile("fld %%st(0); fldz; fld %%st(0); fucomp %%st(2); fnstsw %0; fstp %%st(1)":"=m"(cc)::"st","memory");
        if((cc&0x4400)!=0x4000)__asm__ volatile("fld %%st(3); fld %%st(1); fucompp; fnstsw %0":"=m"(cc)::"st","memory");
        if((cc&0x4400)==0x4000)status|=1;
        __asm__ volatile("fcom %%st(1); fnstsw %0; fstp %%st(1)":"=m"(cc)::"st","memory");
        if(!(cc&0x4100)) {
            status|=4;__asm__ volatile("fstp %%st(2)":::"st");
        } else {
            __asm__ volatile("fcom %%st(2); fnstsw %0; fstp %%st(2)":"=m"(cc)::"st","memory");
            if(!(cc&0x4100))status|=4;
        }
        __asm__ volatile("fcompp; fnstsw %0":"=m"(cc)::"st","memory");
        if((cc&0x500)==0x100)status|=0x40;
        __asm__ volatile("fnstsw %0; fnstcw %1":"=m"(sw),"=m"(cw)::"memory");
        out[0]=product;out[1]=sum;out[2]=difference;out[3]=status;out[4]=cw;out[5]=sw;
        if(fwrite(out,sizeof(out),1,stdout)!=1)return 3;
    }
    return ferror(stdin)?1:0;
}
