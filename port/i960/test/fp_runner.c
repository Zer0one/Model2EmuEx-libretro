/* Native portable-core counterpart to linux_original_fp -DI960_FP_ORACLE.
 * Same synthetic input/result records; no original EXE or ROM is needed. */
#include <stdint.h>
#include <stdio.h>
extern int t_fp(uint32_t, uint32_t, const uint32_t *, const uint32_t *, uint32_t *);
int main(void)
{
    static const uint32_t map[][2]={
        {0x4c3d80,0x688},{0x4c3d40,0x698},{0x4c2d30,0x78b},{0x4c2dc0,0x78c},
        {0x4c2e50,0x78d},{0x4c2ee0,0x78f},{0x4c2cf0,0x79b},{0x4c2d80,0x79c},
        {0x4c2e10,0x79d},{0x4c2ea0,0x79f}};
    uint32_t input[7];
    size_t n;
    while ((n=fread(input,1,sizeof input,stdin))) {
        if (n!=sizeof input || input[6]!=0x27f || (input[1]&~0x3800u)) return 2;
        uint32_t output[4]={0};
        unsigned i;
        for (i=0; i<sizeof map/sizeof map[0]; ++i) if (input[0]==map[i][0]) break;
        if (i==sizeof map/sizeof map[0] || !t_fp(map[i][1],input[1],input+2,input+4,output)) return 3;
        if (fwrite(output,1,sizeof output,stdout)!=sizeof output) return 4;
    }
    return ferror(stdin) || fflush(stdout) ? 5 : 0;
}
