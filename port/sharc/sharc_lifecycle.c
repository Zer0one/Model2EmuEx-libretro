#include "sharc_lifecycle.h"
#include <string.h>
static uint32_t read_le(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void write_le(unsigned char *p,uint32_t value) {
    p[0]=(unsigned char)value;p[1]=(unsigned char)(value>>8);
    p[2]=(unsigned char)(value>>16);p[3]=(unsigned char)(value>>24);
}
void *m2_sharc_state_save(void *destination,const void *source,size_t bytes) {
    return memcpy(destination,source,bytes); /* 0x004bc0d0, native CRT boundary. */
}
void *m2_sharc_state_restore(void *destination,const void *source,size_t bytes) {
    unsigned char *p=destination;
    memcpy(destination,source,bytes); /* 0x004bc0f0 */
    /* Native 32-bit decoded-record pointer rebinding, after the whole copy.
     * PC multiplication and base addition wrap, including unusual saved PCs.
     * Retain 0x2ac from the destination when restoring the usual 0x2a4 bytes.
     * This is the original session-dependent restore: it neither archives nor
     * rebuilds the decoded program. The Windows loader's subsequent Model2
     * vtable +0x30 call (004caf00) invalidates graphics, not this cache. Any
     * self-contained frontend archive must supply that additional context
     * explicitly; do not silently substitute current program RAM here. */
    write_le(p+0x2a8,read_le(p+8)*108u+read_le(p+0x2ac));
    return destination;
}
uint32_t m2_sharc_state_address(uint32_t *allocation,uint32_t fixed_state) {
    *allocation=0;return fixed_state; /* 0x004bc120; no free in this entry. */
}
uint32_t m2_sharc_setup(uint32_t astat_address,uint32_t incoming_eax,
    uint32_t *astat_binding,uint32_t *control_memory,m2_sharc_fp_state *fp) {
    *astat_binding=astat_address;
    *control_memory=(*control_memory&0xffff0000u)|0x3fu;
    /* 0x00460f20 writes only AX and the low memory word. FLDCW/FNSTCW has
     * architectural reserved bit 6 set; memory itself stays 0x003f. */
    fp->control=0x7f;
    return (incoming_eax&0xffff0000u)|0x3fu;
}
void m2_sharc_nop(void) { /* 0x004bca40: literal RET, no guest effects. */ }
uint32_t m2_sharc_bad_compute(uint32_t lhs,uint32_t pc,
    m2_sharc_diagnostic_hook report,void *opaque) {
    /* 0x004bd520 does not stop execution or replace the destination with zero.
     * Snapshot LHS survives even if the diagnostic callback changes state. */
    report(opaque,"SHARC bad compute opcode at %X",pc);
    return lhs;
}
