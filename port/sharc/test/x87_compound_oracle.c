/* Independent transcription of the original compound x87 sequences, run as
 * x86_64 under Rosetta. This is not physical-x86 qualification. */
#include <stdint.h>
#include <stdio.h>
int main(void) {
    uint32_t in[9],out[5];
    while(fread(in,sizeof(in),1,stdin)==1) {
        uint32_t env[7]={in[6],in[7],0xffff,0,0,0,0},a=in[1],b=in[2],x=in[3],y=in[4];
        uint32_t first,second,status=in[5],half=0x3f000000;
        uint16_t cc,sw,cw;
        int pair=in[0]==0x4bc310,scale=in[0]==0x4bd320 || in[0]==0x4bd3b0;
        __asm__ volatile("fninit; fldenv %0"::"m"(env):"st","memory");
        if(pair)__asm__ volatile("flds %0; fadds %1; flds %1; fsubs %0"::"m"(b),"m"(a):"st","memory");
        else {
            __asm__ volatile("flds %0; fmuls %1"::"m"(y),"m"(x):"st","memory");
            if(scale) {
                uint32_t two32=0x4f800000;uint16_t captured;
                __asm__ volatile("fstps %0; fildl %1":"=m"(first):"m"(b):"st","memory");
                if(in[0]==0x4bd320)__asm__ volatile("flds %0; fscale; frndint"::"m"(a):"st","memory");
                else __asm__ volatile("fildl %0; fscale"::"m"(a):"st","memory");
                __asm__ volatile("fnstsw %0; fnclex; ftst; fnstsw %1; fnclex":"=m"(captured),"=m"(cc)::"st","memory");
                if(in[0]==0x4bd320)__asm__ volatile("fistpl %0":"=m"(second)::"st","memory");
                else __asm__ volatile("fstps %0":"=m"(second)::"st","memory");
                __asm__ volatile("fstp %%st(0); flds %0; fsts %0; fildl %1":"+m"(first):"m"(second):"st","memory");
                if(second&0x80000000u)__asm__ volatile("fadds %0"::"m"(two32):"st","memory");
                status=(status&~0x3fu)|0x400u|((captured&1)?0x20u:0)|((captured&8)?2u:0)|((cc&0x100)?4u:0)|((cc&0x4000)?1u:0);
            } else if(in[0]==0x4bd440)__asm__ volatile("flds %0; fsubs %1"::"m"(a),"m"(b):"st","memory");
            else if(in[0]==0x4bd2a0) __asm__ volatile("flds %0; fadds %1; fmuls %2"::"m"(b),"m"(a),"m"(half):"st","memory");
            else if(in[0]==0x4bd4b0)__asm__ volatile("flds %0; fadds %1"::"m"(b),"m"(a):"st","memory");
            else if(in[0]==0x4be220)__asm__ volatile("flds %0; fabs"::"m"(a):"st","memory");
            else if(in[0]==0x4bd1a0 || in[0]==0x4bd220) {
                __asm__ volatile("flds %1; fcomps %2; fnstsw %0":"=m"(cc):"m"(b),"m"(a):"st","memory");
                if(in[0]==0x4bd1a0?!(cc&0x4100):(cc&0x4500)==0x100)
                    __asm__ volatile("flds %0"::"m"(a):"st","memory");
                else __asm__ volatile("flds %0"::"m"(b):"st","memory");
            } else return 2;
        }
        if(!scale)__asm__ volatile("fxch %%st(1); fsts %0; fxch %%st(1); fsts %1":"=m"(first),"=m"(second)::"st","memory");
        if(in[8]&1)status=first;
        if(in[8]&2)status=second;
        status&=pair?~5u:~0x45u;
        if(pair) {
            __asm__ volatile("fld %%st(1); fldz; fld %%st(0); fucomp %%st(2); fnstsw %0; fstp %%st(1)":"=m"(cc)::"st","memory");
            if((cc&0x4500)!=0x4000) {
                __asm__ volatile("fld %%st(1); fld %%st(1); fucompp; fnstsw %0":"=m"(cc)::"st","memory");
            }
            if((cc&0x4500)==0x4000)status|=1;
            __asm__ volatile("fcom %%st(2); fnstsw %0; fstp %%st(2)":"=m"(cc)::"st","memory");
            if(!(cc&0x4100)) {
                status|=4;__asm__ volatile("fstp %%st(0); fstp %%st(0)":::"st");
            } else {
                __asm__ volatile("fcompp; fnstsw %0":"=m"(cc)::"st","memory");
                if((cc&0x500)==0x100)status|=4;
            }
        } else {
            __asm__ volatile("fldz; fcom %%st(2); fnstsw %0; fstp %%st(2)":"=m"(cc)::"st","memory");
            if(!(cc&0x4100))status|=0x40;
            __asm__ volatile("fcom %%st(1); fnstsw %0":"=m"(cc)::"st","memory");
            if((cc&0x500)==0x100)status|=4;
            __asm__ volatile("fucompp; fnstsw %0":"=m"(cc)::"st","memory");
            if((cc&0x4400)==0x4000)status|=1;
        }
        __asm__ volatile("fnstsw %0; fnstcw %1":"=m"(sw),"=m"(cw)::"memory");
        out[0]=first;out[1]=second;out[2]=status;out[3]=cw;out[4]=sw;
        if(fwrite(out,sizeof(out),1,stdout)!=1)return 3;
    }
    return ferror(stdin)?1:0;
}
