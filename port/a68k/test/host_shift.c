/* Instruction-only x86-64/Rosetta cross-check, not the original 32-bit CPU.
 * Preserve partial-register writes and capture flags before any C arithmetic. */
#include <stdint.h>
#include <stdio.h>

#define PROBE(instruction) __asm__ volatile( \
    "pushq $0x202\n\tpopfq\n\t" instruction "\n\tpushfq\n\tpopq %1" \
    : "+a"(value), "=r"(flags) : "c"(count) : "cc")

static void probe(unsigned operation,unsigned bits,unsigned count,uint32_t input) {
    uint32_t value=input;uint64_t flags=0;
    if(operation==0) {
        if(bits==8){PROBE("shrb %%cl, %%al");}
        else if(bits==16){PROBE("shrw %%cl, %%ax");}
        else {PROBE("shrl %%cl, %%eax");}
    } else if(operation==1) {
        if(bits==8){PROBE("shlb %%cl, %%al");}
        else if(bits==16){PROBE("shlw %%cl, %%ax");}
        else {PROBE("shll %%cl, %%eax");}
    } else {
        if(bits==8){PROBE("sarb %%cl, %%al");}
        else if(bits==16){PROBE("sarw %%cl, %%ax");}
        else {PROBE("sarl %%cl, %%eax");}
    }
    uint32_t row[]={operation,bits,count,input,value,(uint32_t)flags};
    if(fwrite(row,sizeof(row),1,stdout)!=1)return;
}

int main(void) {
    static const uint32_t values[]={0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,
                                    0x7fffffff,0x80000000,0xffffffff,0xa5c3e791};
    for(unsigned operation=0;operation<3;operation++)
        for(unsigned bits=8;bits<=32;bits*=2)
            for(unsigned count=0;count<64;count++)
                for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++)
                    probe(operation,bits,count,values[i]);
    return ferror(stdout)?1:0;
}
