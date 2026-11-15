/* Recovered behavior of ElSemi 1.1a generator 004aa040 and wrapper 004a9fa0.
 * Source: original emitted x86, checked against src/all_functions.c.
 * Preserve native quirks; do not fold original-code corrections into recovery.
 * Private DSP RAM follows the original allocation, not MAME's shared bus.
 */
#include "scsp_dsp_original.h"
#include "scsp.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "Recovered DSP context currently requires a little-endian target"
#endif
_Static_assert(sizeof(scsp_dsp_context)==SCSP_DSP_CONTEXT_SIZE,"DSP native context size");
_Static_assert(offsetof(scsp_dsp_context,MPRO)==0xcc,"DSP program offset");
_Static_assert(offsetof(scsp_dsp_context,TEMP)==0x4cc,"DSP TEMP offset");
_Static_assert(offsetof(scsp_dsp_context,ACC)==0x7bc,"DSP scratch offset");
_Static_assert(offsetof(scsp_dsp_context,ADRS_REG)==0x7e4,"DSP address offset");

static uint32_t rd(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static uint32_t rw(const uint8_t *p) { return p[0]|(uint32_t)p[1]<<8; }
static void wd(uint8_t *p,uint32_t v) {
    for (unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8));
}
static void ww(uint8_t *p,uint32_t v) { p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8); }
static int32_t sx(uint32_t v,unsigned bits) {
    uint32_t sign=1u<<(bits-1);return (int32_t)((v&((sign<<1)-1))^sign)-(int32_t)sign;
}
static int64_t signed32(uint32_t v) { return v<=0x7fffffff ? v : (int64_t)v-0x100000000LL; }
static uint32_t sar(uint32_t v,unsigned n) {
    return (v>>n)|((v&0x80000000u) ? (~0u<<(32-n)) : 0);
}

static scsp_dsp_op decode(const uint8_t *p) {
    unsigned a=rw(p),b=rw(p+2),c=rw(p+4),d=rw(p+6);
    scsp_dsp_op o={(a>>8)&127,(a>>7)&1,a&127,b>>15,(b>>13)&3,(b>>6)&63,(b>>5)&1,b&31,
        c>>15,(c>>14)&1,(c>>13)&1,(c>>12)&1,(c>>8)&15,(c>>7)&1,(c>>6)&1,
        (c>>4)&3,(c>>3)&1,(c>>2)&1,(c>>1)&1,c&1,d>>15,(d>>9)&63,(d>>2)&31,(d>>1)&1,d&1};
    return o;
}

static void rebuild(scsp_dsp_original *d) {
    memset(d->decoded,0,sizeof d->decoded);
    for (unsigned i=0;i<=d->compiled_steps;i++)d->decoded[i]=decode(d->compiled+i*8);
}
void scsp_dsp_original_init(scsp_dsp_original *d) {
    memset(d,0,sizeof *d);d->context.RBL=0x8000;d->context.Stopped=1;
    d->context.ram_address=SCSP_DSP_RAM_ADDRESS;
    d->compiled_ram_address=SCSP_DSP_RAM_ADDRESS;
}
void scsp_dsp_original_compile(scsp_dsp_original *d) {
    if (d->context.LastStep<0 || d->context.LastStep>128) { d->fault=1;return; }
    d->compiled_steps=(uint32_t)d->context.LastStep;
    d->compiled_ram_address=d->context.ram_address;
    memset(d->compiled,0,sizeof d->compiled);
    memcpy(d->compiled,(const uint8_t *)&d->context+0xcc,(d->compiled_steps+1)*8);
    rebuild(d);
}
unsigned scsp_dsp_program_length(const scsp_dsp_context *context)
{
    for (unsigned step = 128; step > 0; --step) {
        const uint16_t *words = &context->MPRO[(step - 1) * 4];
        if (words[0] || words[1] || words[2] || words[3]) return step;
    }
    return 0;
}
static int mapped_ram_address(uint32_t address)
{
    return address - SCSP_DSP_RAM_ADDRESS < SCSP_DSP_RAM_SIZE ||
           address - SCSP_SOUND_RAM_ADDRESS < SCSP_DSP_RAM_SIZE;
}

void scsp_dsp_original_start(scsp_dsp_original *d) {
    if (!mapped_ram_address(d->context.ram_address)) {
        d->fault = 1;
        d->fault_address = d->context.ram_address;
        return;
    }
    d->context.Stopped=0;
    d->context.LastStep=scsp_dsp_program_length(&d->context);
    scsp_dsp_original_compile(d);
}
static int step_ram(scsp_dsp_original *d,uint8_t *ram,uint32_t ram_size,uint32_t base_offset) {
    if(d->fault)return 0;
    if(d->context.Stopped)return 1;
    if(!ram || d->compiled_steps>128) {d->fault=1;return 0;}
    uint8_t *s=(uint8_t *)&d->context;
    unsigned steps=d->compiled_steps;
        memset(s+0x794,0,32);
        for (unsigned step=0;step<steps;step++) {
            scsp_dsp_op o=d->decoded[step],next=d->decoded[step+1];
            uint32_t dec=rd(s+0x74c);
            /* 004aa0e0..004aa149: load INPUTS only when used. EXTS uses a
             * DWORD load at a WORD stride, including the adjacent halfword.
             * Keep this original behavior for review, not a guessed fix. */
            if (o.xsel||o.yrl||o.adrl) {
                uint32_t v=o.ira<32 ? rd(s+0x6cc+4*o.ira) :
                    o.ira<48 ? rd(s+0x750+4*(o.ira-32)) :
                    o.ira<50 ? rd(s+0x790+2*(o.ira-48)) : 0;
                wd(s+0x7d0,(uint32_t)sx(v,24));
            }
            if (o.iwt) {
                wd(s+0x6cc+o.iwa*4,rd(s+0x7d4));
                if (o.ira==o.iwa) wd(s+0x7d0,rd(s+0x7d4));
            }
            /* ACC is generated only when the following instruction consumes
             * it. Skipped stores leave native scratch alive across samples. */
            int calc=next.twt||next.frcl||next.mwt||next.adrl||next.ewt||next.bsel;
            uint32_t b=0,x=0;
            if (calc) {
                if (!o.zero) {
                    b=o.bsel?rd(s+0x7bc):(uint32_t)sx(rd(s+0x4cc+4*((o.tra+dec)&127)),24);
                    if (o.negb)b=0u-b;
                }
                x=o.xsel?rd(s+0x7d0):(uint32_t)sx(rd(s+0x4cc+4*((o.tra+dec)&127)),24);
            }
            if (o.twt||o.frcl||o.mwt||o.adrl||o.ewt) {
                uint32_t v=rd(s+0x7bc);
                if (o.shift==1||o.shift==2)v<<=1;
                if (o.shift<2) {
                    int64_t signed_v=signed32(v);
                    v=signed_v>8388607 ? 8388607 : signed_v< -8388608 ? 0xff800000u : v;
                } else v=(uint32_t)sx(v,24);
                wd(s+0x7c0,v);
            }
            if (calc) {
                uint32_t y=o.ysel==0?rd(s+0x7d8):o.ysel==1?(rw(s+0xc+2*o.coef)>>3):
                    o.ysel==2?((rd(s+0x7dc)>>11)&8191):((rd(s+0x7dc)>>4)&4095);
                int64_t product=signed32(x)*sx(y,13);
                int64_t shifted=product/4096-(product<0 && product%4096!=0);
                wd(s+0x7bc,(uint32_t)shifted+b);
            }
            if (o.yrl)wd(s+0x7dc,rd(s+0x7d0));
            uint32_t shifted=rd(s+0x7c0);
            if (o.twt)wd(s+0x4cc+4*((o.twa+dec)&127),shifted);
            if (o.frcl)wd(s+0x7d8,o.shift==3?(shifted&4095):((shifted>>11)&8191));
            if (o.mrd||o.mwt) {
                uint32_t addr=rw(s+0x8c+2*o.masa);
                if (!o.table)addr+=dec;
                if (o.adreb)addr+=rd(s+0x7e4)&4095;
                addr+=o.nxadr;
                addr&=o.table?65535:rd(s+8)-1;
                addr+=rd(s+4)<<12;
                if (o.mwt && (step&1)) {
                    addr<<=1;
                    uint32_t at = base_offset + addr;
                    if (ram_size<2 || at>=ram_size-1) { d->fault=1;d->fault_address=at;return 0; }
                    ww(ram+at,shifted>>8);
                    /* Native emitted code leaves EAX holding SHIFTED>>8,
                     * so a simultaneous MRD derives its address from that. */
                    addr=shifted>>8;
                }
                if (o.mrd && (step&1)) {
                    addr<<=1;
                    uint32_t at = base_offset + addr;
                    if (ram_size<2 || at>=ram_size-1) { d->fault=1;d->fault_address=at;return 0; }
                    uint32_t value=rw(ram+at);
                    /* NOFL=1 emits a load/shift but no store to MEMVAL.
                     * NOFL=0 sign-extends a linear word, with no UNPACK. */
                    if (!o.nofl)wd(s+0x7d4,(uint32_t)(sx(value,16)*256));
                }
            }
            if (o.adrl)wd(s+0x7e4,o.shift==3?((shifted>>12)&4095):sar(rd(s+0x7d0),16));
            if (o.ewt)ww(s+0x794+2*o.ewa,rw(s+0x794+2*o.ewa)+sar(shifted,8));
        }
        wd(s+0x74c,rd(s+0x74c)-1);
        memset(s+0x750,0,64);
    return 1;
}
int scsp_dsp_original_step_memory(scsp_dsp_original *d,uint8_t *ram,uint32_t ram_size) {
    return step_ram(d, ram, ram_size, 0);
}

/* The generated x86 body embeds the allocation address at Start. Reading
 * the live CPU register here would redirect an already compiled program. */
int scsp_dsp_original_step_board(scsp_dsp_original *d, uint8_t *sound_ram)
{
    if (d->fault) return 0;
    if (d->context.Stopped) return 1;
    uint32_t offset = d->compiled_ram_address - SCSP_DSP_RAM_ADDRESS;
    uint8_t *ram = d->ram;
    if (offset >= SCSP_DSP_RAM_SIZE) {
        offset = d->compiled_ram_address - SCSP_SOUND_RAM_ADDRESS;
        ram = sound_ram;
    }
    if (!ram || offset >= SCSP_DSP_RAM_SIZE) {
        d->fault = 1;
        d->fault_address = d->compiled_ram_address;
        return 0;
    }
    return step_ram(d, ram, SCSP_DSP_RAM_SIZE, offset);
}

int scsp_dsp_original_step(scsp_dsp_original *d) {
    return scsp_dsp_original_step_board(d, NULL);
}
/* This is the port's complete-snapshot contract, not ElSemi .sta compatibility.
 * Native 004f7540/004f7400 only traverse registered blocks. M2SCSP registers
 * 64 KiB of sound RAM; it is not this DSP context or the private 1 MiB RAM.
 * Neither those DSP buffers nor generated code are restored by that path.
 * See AUDIO_RE_ANALYSIS.md, Original Save State Audit. Preserve execution
 * quirks without inheriting the original session-dependent persistence gap. */
void scsp_dsp_original_archive(scsp_dsp_original *d,m2_state *a) {
    if(a->mode==M2_STATE_CHECK) {
        scsp_dsp_original *copy=malloc(sizeof *copy);
        if(!copy) {a->failed=1;return;}
        *copy=*d;m2_state probe=*a;probe.mode=M2_STATE_LOAD;
        scsp_dsp_original_archive(copy,&probe);free(copy);
        a->pos=probe.pos;a->failed=probe.failed;return;
    }
    M2_FIELD(a,d,context);M2_FIELD(a,d,compiled);M2_FIELD(a,d,compiled_steps);
    M2_FIELD(a,d,compiled_ram_address);
    M2_FIELD(a,d,ram);M2_FIELD(a,d,fault);M2_FIELD(a,d,fault_address);
    if(d->compiled_steps>128 || d->context.LastStep<0 || d->context.LastStep>128 ||
       !mapped_ram_address(d->compiled_ram_address) || d->context.Stopped>1 || d->fault>1 || d->compiled_steps!=(uint32_t)d->context.LastStep)
        a->failed=1;
    if(a->mode==M2_STATE_LOAD && !a->failed)rebuild(d);
}

#include "scsp_dsp_gains.inc"
/* 004aeb76..004aeba5: two separate truncations, then signed-24 input units.
 * Keep x86 low-32-bit IMUL and SAR semantics, including overflow behavior. */
int32_t scsp_pcm_level(int32_t sample, unsigned tl) {
    return (int32_t)signed32(sar((uint32_t)sample*(uint32_t)original_tl[tl&255],12));
}
void scsp_pcm_pan_gains(unsigned pan, unsigned level, int32_t *left, int32_t *right)
{
    int gain = original_sdl[level & 7];
    *left = (original_lpan[pan & 31] * gain) >> 12;
    *right = (original_rpan[pan & 31] * gain) >> 12;
}

uint32_t scsp_pcm_send(int32_t leveled, unsigned send)
{
    return sar((uint32_t)leveled * original_sdl[send & 7], 12) << 8;
}

uint32_t scsp_pcm_mix(int32_t leveled, unsigned pan, unsigned level, unsigned send,
                      int32_t *left, int32_t *right) {
    scsp_pcm_pan_gains(pan, level, left, right);
    *left = (int32_t)signed32(sar((uint32_t)leveled * *left, 12));
    *right = (int32_t)signed32(sar((uint32_t)leveled * *right, 12));
    return scsp_pcm_send(leveled, send);
}
uint32_t scsp_dsp_original_input(int32_t sample,unsigned tl,unsigned level) {
    return scsp_pcm_send(scsp_pcm_level(sample, tl), level);
}
/* 004aecf0..004aed36: effect gain is applied before the two pan gains.
 * PAN=31 is deliberately not treated as PAN=15: the native tables differ. */
void scsp_dsp_original_output(int16_t effect,unsigned pan,unsigned level,
                              int32_t *left,int32_t *right) {
    uint32_t v=sar((uint32_t)(int32_t)effect*(uint32_t)original_sdl[level&7],12);
    *left=(int32_t)signed32(sar(v*(uint32_t)original_lpan[pan&31],12));
    *right=(int32_t)signed32(sar(v*(uint32_t)original_rpan[pan&31],12));
}
