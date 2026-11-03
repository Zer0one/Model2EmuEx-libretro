#include "sharc_aux.h"
bool m2_sharc_aux(uint32_t entry,uint32_t lhs,uint32_t rhs,uint32_t *status,uint32_t *result)
{
    uint32_t magnitude,bound,value;
    switch(entry) {
    /* Bitwise sign transfer: no x87 load/quieting and no ASTAT update. */
    case 0x462480:value=(lhs&0x7fffffffu)|(rhs&0x80000000u);break;
    case 0x4bc200:value=0;break; /* Literal original stub, not invented arithmetic. */
    case 0x4bc630: case 0x4bc640:value=lhs;break;
    case 0x4bc600:
        value=lhs*rhs; /* Original keeps ONLY the low 32 bits, no accumulator. */
        *status=(*status&~0x40u)|((value>>25)&0x40u);
        break;
    case 0x4bc240:
        magnitude=(lhs&0x80000000u)?0u-lhs:lhs;
        bound=(rhs&0x80000000u)?0u-rhs:rhs;
        /* Original JL is signed, including wrapping ABS(INT_MIN). Preserve
         * its non-mathematical boundary rather than using unsigned magnitudes. */
        value=(magnitude^0x80000000u)<(bound^0x80000000u)?lhs:
            ((lhs&0x80000000u)?0u-bound:bound);
        break;
    default:return false;
    }
    *result=value;
    return true;
}
uint32_t m2_sharc_add_sub(uint32_t lhs,uint32_t rhs,uint32_t *sum,uint32_t *difference,uint32_t *status)
{
    uint32_t a=lhs+rhs,b=lhs-rhs;
    *sum=a;
    *difference=b;
    *status&=~5u;
    if (a==0 || b==0) *status|=1u;
    if ((a|b)&0x80000000u) *status|=4u;
    return 0;
}
