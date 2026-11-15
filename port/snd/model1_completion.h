/* Native x86 arithmetic retained at the Model 1 board callback boundary. */
#ifndef M2_MODEL1_COMPLETION_H
#define M2_MODEL1_COMPLETION_H
#include <stdint.h>
typedef struct { uint32_t eax, flags; } m2_m1_completion;
static inline uint32_t m1_logic_flags(uint32_t flags,uint32_t value,unsigned bits)
{
    uint32_t mask=bits==32 ? UINT32_MAX : (1u<<bits)-1;
    value&=mask;
    unsigned nibble=(value^(value>>4))&15;
    return (flags&~0x8d5u) | (((0x9669u>>nibble)&1u)<<2) |
           (value==0 ? 0x40 : 0) | ((value>>(bits-1))<<7);
}

static inline uint32_t m1_sub_flags(uint32_t flags,uint32_t a,uint32_t b,unsigned bits)
{
    uint32_t mask=bits==32 ? UINT32_MAX : (1u<<bits)-1;
    a&=mask; b&=mask;
    uint32_t v=(a-b)&mask;
    return m1_logic_flags(flags,v,bits) | (a<b) | ((a^b^v)&16) |
           ((((a^b)&(a^v))>>(bits-1))<<11);
}

static inline uint32_t m1_stack_flags(uint32_t flags,uint32_t result,unsigned added)
{
    uint32_t before=result-added;
    return m1_logic_flags(flags,result,32) | (result<before) |
           ((before^added^result)&16) | ((~(before^added)&(before^result))>>31)<<11;
}
#endif
