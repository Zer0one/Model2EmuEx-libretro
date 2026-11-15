/* Test-only access to the preserved prior MAME DSP comparator. The fixture maps
 * recovered original context offsets; RAM byte order and input scaling are
 * explicit responsibilities of the caller, not hidden equivalence fixes. */
#include "../scsp.c"

static int probe(const uint8_t *input, uint8_t *output, uint8_t *ram,
                 uint32_t ram_size, unsigned samples, int arithmetic_only)
{
    scsp *s=calloc(1,sizeof *s);
    if (!s) return 0;
    dsp_t *d=&s->DSP.context;
#define LOAD(field, offset) memcpy(&d->field,input+(offset),sizeof d->field)
    LOAD(RBP,4); LOAD(RBL,8); LOAD(COEF,0xc); LOAD(MADRS,0x8c);
    LOAD(MPRO,0xcc); LOAD(TEMP,0x4cc); LOAD(MEMS,0x6cc); LOAD(DEC,0x74c);
    LOAD(MIXS,0x750); LOAD(EXTS,0x790); LOAD(EFREG,0x794);
    LOAD(Stopped,0x7b4); LOAD(LastStep,0x7b8);
#undef LOAD
    if (d->LastStep<0 || d->LastStep>128) { free(s); return 0; }
    if (arithmetic_only) {
        for (int i=0;i<16;i++) if (d->MIXS[i]) { free(s); return 0; }
        for (int i=0;i<2;i++) if (d->EXTS[i]) { free(s); return 0; }
    }
    for (int i=0;i<d->LastStep;i++) {
        const uint16_t *p=d->MPRO+i*4;
        if (((p[1]>>6)&63)>49 ||
            (arithmetic_only && ((p[2]&0x6000) || ((p[1]>>6)&63)>31))) {
            free(s); return 0;
        }
    }
    if (ram) {
        if (!ram_size || (ram_size&(ram_size-1))) { free(s); return 0; }
        s->ram=ram; s->ram_mask=ram_size-1;
    } else if (!arithmetic_only) { free(s); return 0; }
    for (unsigned i=0;i<samples;i++) dsp_mame_step(s);
    /* The interpreter resets its local scratch each sample; do not invent
     * a serialized counterpart for it in this comparison fixture. */
    memcpy(output,input,0x800);
#define SAVE(field, offset) memcpy(output+(offset),&d->field,sizeof d->field)
    SAVE(TEMP,0x4cc); SAVE(MEMS,0x6cc); SAVE(DEC,0x74c);
    SAVE(MIXS,0x750); SAVE(EFREG,0x794);
#undef SAVE
    free(s); return 1;
}

int scsp_dsp_probe(const uint8_t *input, uint8_t *output)
{
    return probe(input,output,NULL,0,1,1);
}

int scsp_dsp_sequence_probe(const uint8_t *input, uint8_t *output,
                            uint8_t *ram, uint32_t ram_size, unsigned samples)
{
    return probe(input,output,ram,ram_size,samples,0);
}
