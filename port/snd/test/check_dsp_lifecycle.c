/* ROM-free recovered DSP state/cache/private-RAM contracts. */
#include "../scsp_dsp_original.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void instruction(scsp_dsp_original *d,unsigned step,uint16_t a,uint16_t b,uint16_t c,uint16_t e) {
    uint16_t *p=d->context.MPRO+step*4;p[0]=a;p[1]=b;p[2]=c;p[3]=e;
}
static void save(scsp_dsp_original *d,uint8_t *bytes,size_t size,size_t *used) {
    m2_state a={bytes,size,0,M2_STATE_SAVE,0};scsp_dsp_original_archive(d,&a);
    assert(!a.failed);*used=a.pos;
}
int main(void) {
    scsp_dsp_original *d=malloc(sizeof *d),*cold=malloc(sizeof *cold),*before=malloc(sizeof *before);
    size_t cap=sizeof *d;uint8_t *state=malloc(cap),*expected=malloc(cap),*actual=malloc(cap);
    assert(d&&cold&&before&&state&&expected&&actual);
    scsp_dsp_original_init(d);assert(d->context.Stopped && d->context.RBL==0x8000);
    /* IWT sees the previous sample's MEMVAL; odd-step read updates it. */
    instruction(d,0,0,0x27,0,0);
    instruction(d,1,0,0,0xa000,0);
    d->ram[0]=0x34;d->ram[1]=0x12;scsp_dsp_original_start(d);
    assert(scsp_dsp_original_step(d));assert(d->context.MEMS[7]==0);
    assert(d->context.MEMVAL==0x123400);
    /* Guest program RAM changes without the native start event. The cached
     * program must survive save/load, not be rebuilt from these new words. */
    memset(d->context.MPRO,0,sizeof d->context.MPRO);
    size_t used;save(d,state,cap,&used);*before=*d;
    for(int i=0;i<4;i++)assert(scsp_dsp_original_step(d));
    assert(d->context.MEMS[7]==0x123400);
    size_t expected_size;save(d,expected,cap,&expected_size);
    scsp_dsp_original_init(cold);
    m2_state a={state,used,0,M2_STATE_CHECK,0};*before=*cold;
    scsp_dsp_original_archive(cold,&a);assert(!a.failed && a.pos==used && !memcmp(cold,before,sizeof *cold));
    a=(m2_state){state,used,0,M2_STATE_LOAD,0};scsp_dsp_original_archive(cold,&a);assert(!a.failed);
    for(int i=0;i<4;i++)assert(scsp_dsp_original_step(cold));
    size_t actual_size;save(cold,actual,cap,&actual_size);
    assert(actual_size==expected_size && !memcmp(actual,expected,actual_size));
    scsp_dsp_original_start(cold);assert(cold->compiled_steps==0 && !cold->context.Stopped);
    assert(scsp_dsp_original_step(cold));
    /* Corrupt/truncated archive preflight must reject without mutating. */
    *before=*cold;
    a=(m2_state){state,used-1,0,M2_STATE_CHECK,0};scsp_dsp_original_archive(cold,&a);
    assert(a.failed && !memcmp(cold,before,sizeof *cold));
    uint32_t invalid=129;memcpy(state+SCSP_DSP_CONTEXT_SIZE+129*8,&invalid,4);
    a=(m2_state){state,used,0,M2_STATE_CHECK,0};scsp_dsp_original_archive(cold,&a);
    assert(a.failed && !memcmp(cold,before,sizeof *cold));
    /* An out-of-buffer address is reported exactly, without wrapping it. */
    scsp_dsp_original_init(d);instruction(d,1,0,0,0xa000,0);
    d->context.RBP=127;d->context.MADRS[0]=65535;scsp_dsp_original_start(d);
    assert(!scsp_dsp_original_step(d) && d->fault_address==1171454);
    scsp_dsp_original_init(d);assert(!d->fault && !d->ram[0]);
    free(d);free(cold);free(before);free(state);free(expected);free(actual);
    puts("PASS: native defaults, scratch continuation, private RAM, cached program, cold restore, preflight rejection, boundary report and reset");
}
