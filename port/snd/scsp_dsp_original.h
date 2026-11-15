/* Recovered ElSemi 1.1a DSP. Fidelity to the original is distinct from fixes
 * to original behavior; see AUDIO_RE_ANALYSIS.md. No executable host pointers. */
#ifndef M2_SCSP_DSP_ORIGINAL_H
#define M2_SCSP_DSP_ORIGINAL_H
#include <stdint.h>
#include "../state.h"
#define SCSP_DSP_RAM_SIZE 0x100000u
#define SCSP_DSP_CONTEXT_SIZE 0x800u

typedef struct {
    uint32_t ram_address; /* CPU-visible numeric pointer, sampled by the compiler. */
    uint32_t RBP,RBL;
    int16_t COEF[64];
    uint16_t MADRS[32],MPRO[512];
    int32_t TEMP[128],MEMS[32];
    uint32_t DEC;
    int32_t MIXS[16];
    int16_t EXTS[2],EFREG[16];
    uint8_t Stopped,reserved_stop[3];
    int32_t LastStep;
    uint32_t ACC,SHIFTED,reserved_x,reserved_y,reserved_input,INPUTS,MEMVAL,FRC_REG,Y_REG;
    uint32_t reserved_b,ADRS_REG,code_cookie;
    uint8_t reserved_context[20];
} scsp_dsp_context;

typedef struct {
    unsigned tra,twt,twa,xsel,ysel,ira,iwt,iwa,table,mwt,mrd,ewt,ewa;
    unsigned adrl,frcl,shift,yrl,negb,zero,bsel,nofl,coef,masa,adreb,nxadr;
} scsp_dsp_op;

typedef struct {
    scsp_dsp_context context;
    /* Snapshot of the program as compiled, including the successor inspected
     * for dead stores. At 128 steps that successor comes from TEMP[0..1]. */
    uint8_t compiled[129*8];
    uint32_t compiled_steps, compiled_ram_address;
    scsp_dsp_op decoded[129]; /* Derived from compiled, never archived. */
    uint8_t ram[SCSP_DSP_RAM_SIZE];
    uint32_t fault,fault_address;
} scsp_dsp_original;

void scsp_dsp_original_init(scsp_dsp_original *d);
void scsp_dsp_original_compile(scsp_dsp_original *d);
unsigned scsp_dsp_program_length(const scsp_dsp_context *context);
void scsp_dsp_original_start(scsp_dsp_original *d);
int scsp_dsp_original_step(scsp_dsp_original *d);
int scsp_dsp_original_step_board(scsp_dsp_original *d, uint8_t *sound_ram);
void scsp_dsp_original_archive(scsp_dsp_original *d,m2_state *a);
/* Original mixer-side integer contracts, before final chip/output scaling. */
/* PCM voice mixer at 004aeb2d, before the master output stage. */
int32_t scsp_pcm_level(int32_t sample, unsigned tl);
void scsp_pcm_pan_gains(unsigned pan, unsigned level, int32_t *left, int32_t *right);
uint32_t scsp_pcm_send(int32_t leveled, unsigned send);
uint32_t scsp_pcm_mix(int32_t leveled, unsigned pan, unsigned level, unsigned send,
                      int32_t *left, int32_t *right);
uint32_t scsp_dsp_original_input(int32_t sample,unsigned tl,unsigned level);
void scsp_dsp_original_output(int16_t effect,unsigned pan,unsigned level,
                              int32_t *left,int32_t *right);
/* Fixture boundary: bounded external RAM; no production masking policy. */
int scsp_dsp_original_step_memory(scsp_dsp_original *d,uint8_t *ram,uint32_t size);
#endif
