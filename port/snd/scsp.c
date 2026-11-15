/* SCSP synthesis follows MAME scsp.cpp (BSD-3-Clause, ElSemi, R. Belmont;
   thanks to kingshriek). The DSP uses recovered ElSemi 1.1a behavior; see
   scsp_dsp_original.c and AUDIO_RE_ANALYSIS.md. */
#include "scsp.h"
#include "scsp_dsp_original.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#define SHIFT     12
#define LFO_SHIFT 8
#define EG_SHIFT  8
#define FIX(v)    ((uint32_t)((float)(1 << SHIFT) * (v)))

enum { ATTACK, DECAY1, DECAY2, RELEASE };
enum { VOICE_RAM_FAULT = 1, PITCH_TABLE_FAULT, AMPLITUDE_TABLE_FAULT };

typedef struct {
    int volume, state, step, AR, D1R, D2R, RR, DL;
    uint8_t EGHOLD, LPLINK;
} eg_t;

typedef struct {
    uint16_t phase;
    uint32_t phase_step;
    uint8_t binding; /* Bit 5 marks a populated waveform/depth pair. */
    const int *table, *scale;
} lfo_t;

typedef struct {
    union { uint16_t data[0x10]; uint8_t datab[0x20]; } u;
    uint8_t Backwards, active;
    uint16_t active_high; /* Longword at register +0x1e also writes +0x21. */
    uint32_t cur_addr, nxt_addr, step;
    uint32_t sample_base; /* Latched by the native key-on at 004af710. */
    eg_t EG;
    lfo_t PLFO, ALFO;
    int slot;
    int16_t Prev;
    int32_t cached_left_gain, cached_right_gain;
    uint16_t cached_tl_gain; /* Native slot +0x80, read before refresh by 004548c0. */
} slot_t;

typedef scsp_dsp_context dsp_t;

struct scsp {
    uint8_t *ram;
    uint32_t ram_mask; /* Chip-internal DMA and MAME DSP window. */
    uint32_t voice_ram_size, voice_ram_address, voice_fault_address;
    uint8_t voice_fault;
    scsp_irq_fn irq;
    uint32_t *irq_register;
    void *user;
    void (*midi_reply)(void *,uint8_t);void *midi_reply_user;
    uint8_t midi_out[32],midi_out_read,midi_out_write,midi_transmit;
    unsigned midi_countdown;

    union { uint16_t data[0x30 / 2]; uint8_t datab[0x30]; } u;
    slot_t Slots[32];
    int16_t RINGBUF[128];
    uint32_t ring_cursor, master; /* Low bytes drive the mixer and global write gates. */
    uint32_t IrqTimA, IrqTimBC, IrqMidi, IrqCPU, IrqDMA;
    uint8_t latched_MSLC;
    uint16_t latched_MSLC_data;
    /* Native globals 010c35b0 / 010ed9d8..9 / 01078799. The count is an
     * independent wrapping byte, not write-read and not a fullness guard. */
    uint8_t MidiStack[128], MidiW, MidiR, MidiCount;
    /* ElSemi CPU output producer. The optional Manx TT wire has its own timing. */
    uint8_t cpu_midi_output[128], cpu_midi_cursor, cpu_midi_count;
    uint8_t cpu_irq_level;
    int32_t EG_TABLE[0x400];
    int LPANTABLE[0x10000], RPANTABLE[0x10000];
    uint32_t TimCnt[3];
    uint8_t TimExpired[3]; /* Native 010bdf40..42, separate from counters. */
    struct { uint32_t dmea; uint16_t drga, dtlg; uint8_t dgate, ddir; } dma;
    uint16_t mcieb, mcipd;
    int ARTABLE[64], DRTABLE[64];
    scsp_dsp_original DSP;
    unsigned dsp_backend;
    int interleaved_mixer; /* Machine hook 004c6710, fixed for the loaded content. */
    const uint32_t *cpu_write_sp;
    uint32_t dsp_code_address;
    int16_t voice_work[32][SCSP_MIXER_BLOCK]; /* 004aa950 uses a 0x600-byte stride. */
    int PLFO_TRI[256], PLFO_SQR[256], PLFO_SAW[256], PLFO_NOI[256];
    int ALFO_TRI[256], ALFO_SQR[256], ALFO_SAW[256], ALFO_NOI[256];
    int PSCALES[8][257], ASCALES[8][256];
    uint32_t rng;
};

/* slot parameters */
#define KEYONEX(s) ((s)->u.data[0x0] & 0x1000)
#define KEYONB(s)  ((s)->u.data[0x0] & 0x0800)
#define SBCTL(s)   (((s)->u.data[0x0] >> 0x9) & 0x0003)
#define SSCTL(s)   (((s)->u.data[0x0] >> 0x7) & 0x0003)
#define LPCTL(s)   (((s)->u.data[0x0] >> 0x5) & 0x0003)
#define PCM8B(s)   ((s)->u.data[0x0] & 0x0010)
#define SA(s)      ((((uint32_t)(s)->u.data[0x0] & 0xF) << 16) | (s)->u.data[0x1])
#define LSA(s)     ((s)->u.data[0x2])
#define LEA(s)     ((s)->u.data[0x3])
#define D2R(s)     (((s)->u.data[0x4] >> 0xB) & 0x001F)
#define D1R(s)     (((s)->u.data[0x4] >> 0x6) & 0x001F)
#define EGHOLD(s)  ((s)->u.data[0x4] & 0x0020)
#define AR(s)      ((s)->u.data[0x4] & 0x001F)
#define LPSLNK(s)  ((s)->u.data[0x5] & 0x4000)
#define KRS(s)     (((s)->u.data[0x5] >> 0xA) & 0x000F)
#define DL(s)      (((s)->u.data[0x5] >> 0x5) & 0x001F)
#define RR(s)      ((s)->u.data[0x5] & 0x001F)
#define STWINH(s)  ((s)->u.data[0x6] & 0x0200)
#define SDIR(s)    ((s)->u.data[0x6] & 0x0100)
#define TL(s)      ((s)->u.data[0x6] & 0x00FF)
#define MDL(s)     (((s)->u.data[0x7] >> 0xC) & 0x000F)
#define MDXSL(s)   (((s)->u.data[0x7] >> 0x6) & 0x003F)
#define MDYSL(s)   ((s)->u.data[0x7] & 0x003F)
#define OCT(s)     (((s)->u.data[0x8] >> 0xB) & 0x000F)
#define FNS(s)     ((s)->u.data[0x8] & 0x03FF)
#define LFORE(s)   ((s)->u.data[0x9] & 0x8000)
#define LFOF(s)    (((s)->u.data[0x9] >> 0xA) & 0x001F)
#define PLFOWS(s)  (((s)->u.data[0x9] >> 0x8) & 0x0003)
#define PLFOS(s)   (((s)->u.data[0x9] >> 0x5) & 0x0007)
#define ALFOWS(s)  (((s)->u.data[0x9] >> 0x3) & 0x0003)
#define ALFOS(s)   ((s)->u.data[0x9] & 0x0007)
#define ISEL(s)    (((s)->u.data[0xA] >> 0x3) & 0x000F)
#define IMXL(s)    ((s)->u.data[0xA] & 0x0007)
#define DISDL(s)   (((s)->u.data[0xB] >> 0xD) & 0x0007)
#define DIPAN(s)   (((s)->u.data[0xB] >> 0x8) & 0x001F)
#define EFSDL(s)   (((s)->u.data[0xB] >> 0x5) & 0x0007)
#define EFPAN(s)   ((s)->u.data[0xB] & 0x001F)

/* common registers */
#define DAC18B(c)  ((c)->u.data[0] & 0x0100)
#define MVOL(c)    ((c)->u.data[0] & 0x000F)
#define RBL(c)     (((c)->u.data[1] >> 0x7) & 0x0003)
#define SCILV0(c)  ((c)->u.data[0x24 / 2] & 0xff)
#define SCILV1(c)  ((c)->u.data[0x26 / 2] & 0xff)
#define SCILV2(c)  ((c)->u.data[0x28 / 2] & 0xff)
#define SCIMID 3
#define SCIDMA 4
#define SCIIRQ 5
#define SCITMA 6
#define SCITMB 7

static const double ARTimes[64] = { 100000, 100000, 8100.0, 6900.0, 6000.0, 4800.0, 4000.0, 3400.0, 3000.0, 2400.0, 2000.0, 1700.0, 1500.0,
    1200.0, 1000.0, 860.0, 760.0, 600.0, 500.0, 430.0, 380.0, 300.0, 250.0, 220.0, 190.0, 150.0, 130.0, 110.0, 95.0,
    76.0, 63.0, 55.0, 47.0, 38.0, 31.0, 27.0, 24.0, 19.0, 15.0, 13.0, 12.0, 9.4, 7.9, 6.8, 6.0, 4.7, 3.8, 3.4, 3.0, 2.4,
    2.0, 1.8, 1.6, 1.3, 1.1, 0.93, 0.85, 0.65, 0.53, 0.44, 0.40, 0.35, 0.0, 0.0 };
static const double DRTimes[64] = { 100000, 100000, 118200.0, 101300.0, 88600.0, 70900.0, 59100.0, 50700.0, 44300.0, 35500.0, 29600.0, 25300.0, 22200.0, 17700.0,
    14800.0, 12700.0, 11100.0, 8900.0, 7400.0, 6300.0, 5500.0, 4400.0, 3700.0, 3200.0, 2800.0, 2200.0, 1800.0, 1600.0, 1400.0, 1100.0,
    920.0, 790.0, 690.0, 550.0, 460.0, 390.0, 340.0, 270.0, 230.0, 200.0, 170.0, 140.0, 110.0, 98.0, 85.0, 68.0, 57.0, 49.0, 43.0, 34.0,
    28.0, 25.0, 22.0, 18.0, 14.0, 12.0, 11.0, 8.5, 7.1, 6.1, 5.4, 4.3, 3.6, 3.1 };
static const float SDLT[8] = { -1000000.0f, -36.0f, -30.0f, -24.0f, -18.0f, -12.0f, -6.0f, 0.0f };
static const float LFOFreq[32] = { 0.17f, 0.19f, 0.23f, 0.27f, 0.34f, 0.39f, 0.45f, 0.55f, 0.68f, 0.78f, 0.92f, 1.10f, 1.39f, 1.60f, 1.87f, 2.27f,
    2.87f, 3.31f, 3.92f, 4.79f, 6.15f, 7.18f, 8.60f, 10.8f, 14.4f, 17.2f, 21.5f, 28.7f, 43.1f, 57.4f, 86.1f, 172.3f };
static const float ASCALE[8] = { 0.0f, 0.4f, 0.8f, 1.5f, 3.0f, 6.0f, 12.0f, 24.0f };
static const float PSCALE[8] = { 0.0f, 7.0f, 13.5f, 27.0f, 55.0f, 112.0f, 230.0f, 494.0f };

static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }


/* ElSemi/A68K word-swapped backing, shared by CPU, samples, DMA and MAME DSP.
 * Chip address masking/alignment is unchanged. Reconstructed ElSemi DSP RAM
 * is a separate allocation and already has its native representation. */
static inline uint16_t read_word(scsp *s, uint32_t a)
{
    a &= s->ram_mask & ~1u;
    return (uint16_t)(s->ram[a] | s->ram[a + 1] << 8);
}
static inline void write_word(scsp *s, uint32_t a, uint16_t v)
{
    a &= s->ram_mask & ~1u;
    s->ram[a] = (uint8_t)v;
    s->ram[a + 1] = (uint8_t)(v >> 8);
}

/* ------------------------------------------------------------ DSP (scspdsp.cpp) */

/* Recovered original DSP lives in scsp_dsp_original.c. */
#include "scsp_dsp_mame.inc"
static void dsp_step(scsp *s) {
    if(s->dsp_backend==SCSP_DSP_MAME)dsp_mame_step(s);
    else (void)scsp_dsp_original_step_board(&s->DSP,s->ram);
}
static void dsp_mame_start(scsp *s) {
    dsp_t *d=&s->DSP.context;d->Stopped=0;
    d->LastStep=scsp_dsp_program_length(d);
}

/* ------------------------------------------------------------ interrupts */

static void irq_line(scsp *s, uint32_t level, int asserted)
{
    if (level)   /* MAME: line 0 does not exist, clearing it does nothing */
        s->irq(s->user, (int)level, asserted);
}

static uint8_t DecodeSCI(scsp *s, uint8_t irq)
{
    uint8_t SCI = 0;
    SCI |= (SCILV0(s) & (1 << irq)) ? 1 : 0;
    SCI |= ((SCILV1(s) & (1 << irq)) ? 1 : 0) << 1;
    SCI |= ((SCILV2(s) & (1 << irq)) ? 1 : 0) << 2;
    return SCI;
}

static void CheckPendingIRQ(scsp *s)
{
    uint32_t pend = s->u.data[0x20 / 2], en = s->u.data[0x1e / 2];
    /* 004aea40: MIDI is first and does not depend on SCIEB/SCIPD. With an
     * empty FIFO and zero pending bits, the original leaves IRQ untouched.
     * Otherwise only timer A, B, C participate, in that order. */
    unsigned level;
    if(s->MidiW!=s->MidiR)level=s->IrqMidi;
    else if(!pend)return;
    else if(pend&en&0x40)level=s->IrqTimA;
    else if(pend&en&0x180)level=s->IrqTimBC;
    else level=0;
    /* 004aea61..004aeab0 stores the whole IRQ word even when the low
     * level is unchanged. A masked timer therefore clears a guest STOP.
     * The no-pending-source return above deliberately preserves the word. */
    if (s->irq_register) *s->irq_register = level;
    if(level!=s->cpu_irq_level) {
        irq_line(s,s->cpu_irq_level,0);
        s->cpu_irq_level=(uint8_t)level;
        irq_line(s,level,1);
    }
}

static void ResetInterrupts(scsp *s)
{
    /* 004af1d1: re-latch fired timers BEFORE recomputing the pending IRQ. */
    if (s->TimExpired[0]) s->u.data[0x20 / 2] |= 0x40;
    if (s->TimExpired[1]) s->u.data[0x20 / 2] |= 0x80;
    if (s->TimExpired[2]) s->u.data[0x20 / 2] |= 0x100;
    CheckPendingIRQ(s);
}

/* Timers counted in output samples (ElSemi's original SCSP timer code) */
void scsp_clock_tick(scsp *s)
{
    static const int reg[3] = { 0x18 / 2, 0x1a / 2, 0x1c / 2 }, bit[3] = { 0x40, 0x80, 0x100 };
    for (int t = 0; t < 3; t++) {
        if (!s->TimExpired[t]) {
            s->TimCnt[t] += 1u << (8 - ((s->u.data[reg[t]] >> 8) & 7));
            uint32_t value=s->TimCnt[t]>>8;
            /* 004ab0e0 tests equality with 0x100, not >=0xff. Keep the
             * counter and fractional byte when the separate latch fires. */
            if (value == 0x100) {
                s->TimExpired[t]=1;
                s->u.data[0x20 / 2] |= bit[t];
                s->u.data[reg[t]] |= 0xff;
            } else s->u.data[reg[t]] = (uint16_t)((s->u.data[reg[t]] & 0xff00) | value);
        }
    }
    /* 004af02d checks after each sound CPU/timer slice, even without a newly
     * fired timer. Enqueue/dequeue themselves do not recompute the native IRQ. */
    CheckPendingIRQ(s);
}

/* ------------------------------------------------------------ envelope, LFO */

static int Get_AR(scsp *s, int base, int R) { return s->ARTABLE[clampi(base + (R << 1), 0, 63)]; }
static int Get_DR(scsp *s, int base, int R) { return s->DRTABLE[clampi(base + (R << 1), 0, 63)]; }

static void Compute_EG(scsp *s, slot_t *slot)
{
    int octave = (OCT(slot) ^ 8) - 8;
    int rate = KRS(slot) != 0xf ? 2 * (octave + KRS(slot)) + ((FNS(slot) >> 9) & 1) : 0;
    slot->EG.AR = Get_AR(s, rate, AR(slot));
    slot->EG.D1R = Get_DR(s, rate, D1R(slot));
    slot->EG.D2R = Get_DR(s, rate, D2R(slot));
    slot->EG.RR = Get_DR(s, rate, RR(slot));
    slot->EG.DL = 0x1f - DL(slot);
    slot->EG.EGHOLD = (uint8_t)EGHOLD(slot);
}

static void StopSlot(slot_t *slot, int keyoff)
{
    if (keyoff)
        slot->EG.state = RELEASE;
    else
        slot->active = 0;
    slot->u.data[0] &= ~0x800;
}

static int EG_Update(slot_t *slot)
{
    switch (slot->EG.state) {
    case ATTACK:
        slot->EG.volume += slot->EG.AR;
        if (slot->EG.volume >= (0x3ff << EG_SHIFT)) {
            if (!LPSLNK(slot)) {
                slot->EG.state = DECAY1;
                if (slot->EG.D1R >= (1024 << EG_SHIFT))
                    slot->EG.state = DECAY2;
            }
            slot->EG.volume = 0x3ff << EG_SHIFT;
        }
        if (slot->EG.EGHOLD)
            return 0x3ff << (SHIFT - 10);
        break;
    case DECAY1:
        slot->EG.volume -= slot->EG.D1R;
        if (slot->EG.volume <= 0)
            slot->EG.volume = 0;
        if (slot->EG.volume >> (EG_SHIFT + 5) <= slot->EG.DL)
            slot->EG.state = DECAY2;
        break;
    case DECAY2:
        /* 004ab419 tests the current level before applying a decay step.
         * Even zero-rate voices are stopped below level 32. */
        if (slot->EG.volume < (32 << EG_SHIFT)) {
            slot->EG.volume = 0;
            StopSlot(slot, 0);
        } else if (D2R(slot)) {
            slot->EG.volume -= slot->EG.D2R;
        }
        break;
    case RELEASE:
        slot->EG.volume -= slot->EG.RR;
        if (slot->EG.volume <= 0) {
            slot->EG.volume = 0;
            StopSlot(slot, 0);
        }
        break;
    default:
        return 1 << SHIFT;
    }
    /* 004ab408 clips the returned level independently of the stored volume. */
    return (clampi(slot->EG.volume, 0, 0x3ff << EG_SHIFT) >> EG_SHIFT) << (SHIFT - 10);
}

/* 004ab340 and the inline key-on at 004af73b shift a frequency-table
 * entry in 32 bits before the unsigned multiply. The wrap at high octaves
 * is intentional. The high product also owns the live A68K callback flags. */
static uint32_t pitch_product_high(const slot_t *slot)
{
    uint32_t frequency = (1024u + FNS(slot)) * (44100u * 4);
    /* Observed ElSemi startup uses x87 CW=0x007f (24-bit, nearest-even).
     * Every entry below 2^28 is already exact. Above it, the spacing is 32. */
    if (frequency >= (1u << 28))
        frequency = (frequency + 15u + ((frequency >> 5) & 1u)) & ~31u;
    unsigned octave = OCT(slot);
    uint32_t shifted = octave < 8 ? frequency << octave : frequency >> (16 - octave);
    return (uint32_t)(((uint64_t)shifted * 0xbe37c63bu) >> 32);
}

static uint32_t Step(const slot_t *slot)
{
    return pitch_product_high(slot) >> 15;
}

static void LFO_ComputeStep(scsp *s, lfo_t *LFO, uint32_t LFOF, uint32_t LFOWS, uint32_t LFOS, int ALFO)
{
    float step = LFOFreq[LFOF] * 256.0f / 44100.0f;
    LFO->phase_step = (uint32_t)((float)(1 << LFO_SHIFT) * step);
    LFO->binding = (uint8_t)(32 | (LFOWS << 3) | LFOS);
    if (ALFO) {
        const int *t[4] = { s->ALFO_SAW, s->ALFO_SQR, s->ALFO_TRI, s->ALFO_NOI };
        LFO->table = t[LFOWS & 3];
        LFO->scale = s->ASCALES[LFOS];
    } else {
        const int *t[4] = { s->PLFO_SAW, s->PLFO_SQR, s->PLFO_TRI, s->PLFO_NOI };
        LFO->table = t[LFOWS & 3];
        LFO->scale = s->PSCALES[LFOS];
    }
}

static void Compute_LFO(scsp *s, slot_t *slot)
{
    if (PLFOS(slot))
        LFO_ComputeStep(s, &slot->PLFO, LFOF(slot), PLFOWS(slot), PLFOS(slot), 0);
    if (ALFOS(slot))
        LFO_ComputeStep(s, &slot->ALFO, LFOF(slot), ALFOWS(slot), ALFOS(slot), 1);
}

static int32_t PLFO_Step(lfo_t *LFO)
{
    LFO->phase = (uint16_t)(LFO->phase + LFO->phase_step);
    int p = LFO->table[LFO->phase >> LFO_SHIFT];
    p = LFO->scale[p + 128];
    return p << (SHIFT - LFO_SHIFT);
}

static int32_t ALFO_Step(lfo_t *LFO)
{
    LFO->phase = (uint16_t)(LFO->phase + LFO->phase_step);
    int p = LFO->table[LFO->phase >> LFO_SHIFT];
    p = LFO->scale[p];
    return p << (SHIFT - LFO_SHIFT);
}

static void StartSlot(scsp *s, slot_t *slot)
{
    slot->sample_base = SA(slot) & (PCM8B(slot) ? 0xfffffu : 0x7fffeu);
    slot->active = 1;
    slot->cur_addr = 0;
    slot->nxt_addr = 1 << SHIFT;
    slot->step = Step(slot);
    Compute_EG(s, slot);
    slot->EG.state = ATTACK;
    slot->EG.volume = 0x17F << EG_SHIFT;
    slot->Prev = 0;
    slot->Backwards = 0;
    Compute_LFO(s, slot);
}

/* ------------------------------------------------------------ registers */

static void exec_dma(scsp *s);

static void UpdateSlotReg(scsp *s, int sn, int r)
{
    slot_t *slot = s->Slots + sn;
    switch (r & 0x3f) {
    case 0: case 1:
        if (KEYONEX(slot)) {
            for (int sl = 0; sl < 32; ++sl) {
                slot_t *s2 = s->Slots + sl;
                if (KEYONB(s2) && s2->EG.state == RELEASE)
                    StartSlot(s, s2);
                if (!KEYONB(s2))
                    StopSlot(s2, 1);
            }
            slot->u.data[0] &= ~0x1000;
        }
        break;
    case 0x10: case 0x11:
        slot->step = Step(slot);
        break;
    case 8: case 9: case 0xa: case 0xb:
        if (slot->active) Compute_EG(s, slot);
        break;
    case 0x12: case 0x13:
        Compute_LFO(s, slot);
        break;
    }
}

static void set_dsp_ring(scsp *s, unsigned base_mask)
{
    s->DSP.context.RBP = s->u.data[1] & base_mask;
    s->DSP.context.RBL = 8192u << RBL(s);
}

static void UpdateReg(scsp *s, int reg)
{
    switch (reg & 0x3f) {
    case 0x2: case 0x3:
        set_dsp_ring(s, 0x3f);
        break;
    case 0x6: case 0x7:
        if(s->midi_reply) {
            uint8_t value=(uint8_t)s->u.data[0x6/2];
            if(s->midi_out_read==s->midi_out_write) { s->midi_transmit=value;s->midi_countdown=14; }
            s->midi_out[s->midi_out_write++]=value;s->midi_out_write&=31;
        }
        break;
    case 0x8: case 0x9:
        s->latched_MSLC = (uint8_t)((s->u.data[0x8 / 2] & 0xf800) >> 11);
        break;
    case 0x12: case 0x13:
        s->dma.dmea = (s->u.data[0x12 / 2] & 0xfffe) | (s->dma.dmea & 0xf0000);
        break;
    case 0x14: case 0x15:
        s->dma.dmea = ((uint32_t)(s->u.data[0x14 / 2] & 0xf000) << 4) | (s->dma.dmea & 0xfffe);
        s->dma.drga = s->u.data[0x14 / 2] & 0x0ffe;
        break;
    case 0x16: case 0x17:
        s->dma.dtlg = s->u.data[0x16 / 2] & 0x0ffe;
        s->dma.ddir = (uint8_t)((s->u.data[0x16 / 2] & 0x2000) >> 13);
        s->dma.dgate = (uint8_t)((s->u.data[0x16 / 2] & 0x4000) >> 14);
        if (s->u.data[0x16 / 2] & 0x1000)
            exec_dma(s);
        break;
    case 0x18: case 0x19:
    case 0x1a: case 0x1b:
    case 0x1c: case 0x1d: {
        unsigned t=(unsigned)(reg-0x18)/2;
        s->TimCnt[t]=((s->u.data[(0x18+2*t)/2]&0xffu)<<8)|(s->TimCnt[t]&255u);
        s->TimExpired[t]=0;break;
    }
    case 0x1e: case 0x1f: case 0x20: case 0x21:
        break; /* Native register update waits for the next IRQ check. */
    case 0x22: case 0x23:   /* SCIRE */
        s->u.data[0x20 / 2] &= ~s->u.data[0x22 / 2];
        ResetInterrupts(s);
        break;
    case 0x24: case 0x25: case 0x26: case 0x27: case 0x28: case 0x29:
        s->IrqTimA = DecodeSCI(s, SCITMA);
        s->IrqTimBC = DecodeSCI(s, SCITMB);
        s->IrqMidi = DecodeSCI(s, SCIMID);
        s->IrqCPU = DecodeSCI(s, SCIIRQ);
        s->IrqDMA = DecodeSCI(s, SCIDMA);
        break;
    case 0x2a: case 0x2b:
        s->mcieb = s->u.data[0x2a / 2];
        break;
    case 0x2c: case 0x2d:
        if (s->u.data[0x2c / 2] & 0x20)
            s->mcipd |= 0x20;
        break;
    case 0x2e: case 0x2f:
        s->mcipd &= ~s->u.data[0x2e / 2];
        break;
    }
}

static void UpdateRegR(scsp *s, int reg)
{
    switch (reg & 0x3f) {
    case 4: case 5: {   /* MIDI in */
        uint16_t v = (uint16_t)((s->u.data[0x4 / 2] & 0xff00) | s->MidiStack[s->MidiR]);
        if (s->MidiR != s->MidiW)
            s->MidiR = (s->MidiR + 1) & 127;
        if (s->MidiR == s->MidiW) {
            irq_line(s, s->IrqMidi, 0);
            s->u.data[0x20 / 2] &= ~8;
        }
        s->u.data[0x4 / 2] = v;
        break;
    }
    case 8: case 9:
        s->u.data[0x8 / 2] = s->latched_MSLC_data;
        break;
    case 0x2a: case 0x2b:
        s->u.data[0x2a / 2] = s->mcieb;
        break;
    case 0x2c: case 0x2d:
        s->u.data[0x2c / 2] = s->mcipd;
        break;
    }
}

static void w16(scsp *s, uint32_t addr, uint16_t val)
{
    addr &= 0xffff;
    if (addr < 0x400) {
        int slot = (int)(addr / 0x20);
        addr &= 0x1f;
        s->Slots[slot].u.data[addr / 2] = val;
        UpdateSlotReg(s, slot, (int)(addr & 0x1f));
    } else if (addr < 0x600) {
        if (addr < 0x430) {
            if (addr == 0x420 || addr == 0x42e)   /* SCIPD, MCIPD: only bit 5 writable */
                s->u.data[(addr & 0x3f) / 2] |= val & 0x20;
            else
                s->u.data[(addr & 0x3f) / 2] = val;
            UpdateReg(s, (int)(addr & 0x3f));
        }
    } else if (addr < 0x700) {
        s->RINGBUF[(addr - 0x600) / 2] = (int16_t)val;
    } else if (addr < 0x780) {
        s->DSP.context.COEF[(addr - 0x700) / 2] = (int16_t)val;
    } else if (addr < 0x7c0) {
        s->DSP.context.MADRS[(addr - 0x780) / 2] = val;
    } else if (addr < 0x800) {
        s->DSP.context.MADRS[(addr - 0x7c0) / 2] = val;
    } else if (addr < 0xC00) {
        s->DSP.context.MPRO[(addr - 0x800) / 2] = val;
        if(s->dsp_backend==SCSP_DSP_MAME && addr==0xbf0)dsp_mame_start(s);
    }
}

static uint16_t r16(scsp *s, uint32_t addr)
{
    uint16_t v = 0;
    addr &= 0xffff;
    if (addr < 0x400) {
        v = s->Slots[addr / 0x20].u.data[(addr & 0x1f) / 2];
    } else if (addr < 0x600) {
        if (addr < 0x430) {
            UpdateRegR(s, (int)(addr & 0x3f));
            v = s->u.data[(addr & 0x3f) / 2];
        }
    } else if (addr < 0x700) {
        v = (uint16_t)s->RINGBUF[(addr - 0x600) / 2];
    } else if (addr < 0x780) {
        v = (uint16_t)s->DSP.context.COEF[(addr - 0x700) / 2];
    } else if (addr < 0x7c0) {
        v = s->DSP.context.MADRS[(addr - 0x780) / 2];
    } else if (addr < 0x800) {
        v = s->DSP.context.MADRS[(addr - 0x7c0) / 2];
    } else if (addr < 0xC00) {
        v = s->DSP.context.MPRO[(addr - 0x800) / 2];
    } else if (addr < 0xE00) {
        int32_t t = s->DSP.context.TEMP[(addr >> 2) & 0x7f];
        v = (uint16_t)((addr & 2) ? t & 0xffff : (uint32_t)t >> 16);
    } else if (addr < 0xE80) {
        int32_t t = s->DSP.context.MEMS[(addr >> 2) & 0x1f];
        v = (uint16_t)((addr & 2) ? t & 0xffff : (uint32_t)t >> 16);
    } else if (addr < 0xEC0) {
        int32_t t = s->DSP.context.MIXS[(addr >> 2) & 0xf];
        v = (uint16_t)((addr & 2) ? t & 0xffff : (uint32_t)t >> 16);
    } else if (addr < 0xEE0) {
        v = (uint16_t)s->DSP.context.EFREG[(addr - 0xec0) / 2];
    } else if (addr < 0xEE4) {
        v = (uint16_t)s->DSP.context.EXTS[(addr - 0xee0) / 2];
    }
    return v;
}

static void exec_dma(scsp *s)
{
    uint16_t tmp_dma[3];
    int i;
    if (!s->dma.ddir)
        for (i = 0; i < 3; i++)
            tmp_dma[i] = s->u.data[(0x12 + i * 2) / 2];
    if (s->dma.ddir) {
        for (i = 0; i < s->dma.dtlg; i += 2) {
            write_word(s, s->dma.dmea, s->dma.dgate ? 0 : r16(s, s->dma.drga));
            s->dma.dmea += 2;
            if (!s->dma.dgate)
                s->dma.drga += 2;
        }
    } else {
        for (i = 0; i < s->dma.dtlg; i += 2) {
            w16(s, s->dma.drga, s->dma.dgate ? 0 : read_word(s, s->dma.dmea));
            if(s->dsp_backend==SCSP_DSP_ORIGINAL && (s->dma.drga&0xffff)==0xbfe)scsp_dsp_original_start(&s->DSP);
            if (!s->dma.dgate)
                s->dma.dmea += 2;
            s->dma.drga += 2;
        }
        for (i = 0; i < 3; i++)
            s->u.data[(0x12 + i * 2) / 2] = tmp_dma[i];
    }
    s->u.data[0x16 / 2] &= ~0x1000;
    if (s->u.data[0x1e / 2] & 0x10) {   /* DMA end irq (MAME: HOLD_LINE) */
        irq_line(s, s->IrqDMA, 1);
    }
}

/* ------------------------------------------------------------ voices */

/* 004ab901 and 004ad068 apply the byte lane or word load after
 * adding the cursor to the key-on base. Preserve x86 address arithmetic,
 * then bound the entire load before indexing the sound RAM allocation. */
static int voice_sample(scsp *s, const slot_t *slot, uint32_t offset, int32_t *sample)
{
    unsigned width = PCM8B(slot) ? 1 : 2;
    uint32_t address = slot->sample_base + offset;
    if (width == 1) address ^= 1u;
    /* The slot's relative offset is latched at key-on. Both mixers add
     * the current chip RAM pointer after the byte lane adjustment. */
    const uint8_t *ram = s->ram;
    uint32_t bias = s->voice_ram_address - SCSP_SOUND_RAM_ADDRESS;
    uint32_t size = s->voice_ram_size;
    if (bias >= size) {
        ram = s->DSP.ram;
        bias = s->voice_ram_address - SCSP_DSP_RAM_ADDRESS;
        size = sizeof s->DSP.ram;
    }
    if (bias >= size) {
        s->voice_fault_address = s->voice_ram_address + address;
        s->voice_fault = VOICE_RAM_FAULT;
        return 0;
    }
    address += bias;
    if (address >= size || width > size - address) {
        s->voice_fault_address = address;
        s->voice_fault = VOICE_RAM_FAULT;
        return 0;
    }
    const uint8_t *p = ram + address;
    *sample = width == 1 ? (int8_t)p[0] * 256 : (int16_t)(p[0] | p[1] << 8);
    return 1;
}

/* The native handlers compare the integer part of the advanced cursor
 * before clamping. SHR zero-fills on x86, including on backward underflow.
 * Only ordinary ping-pong handlers include equality at the lower limit. */
static void update_pcm_loop(slot_t *slot, unsigned mode, uint32_t position, int interleaved)
{
    uint32_t start = LSA(slot), end = LEA(slot);
    switch (mode) {
    case 0: /* 004acf39 */
        if (position >= end) StopSlot(slot, 0);
        break;
    case 1: /* 004ace09 */
        if (position >= end) slot->cur_addr = (start + 1) << SHIFT;
        break;
    case 2: /* 004accbc */
    case 3: /* 004acb5c */
        if (position >= end) {
            slot->cur_addr = end << SHIFT;
            slot->Backwards = 1;
        }
        if (slot->Backwards && (position < start || (mode == 3 && !interleaved && position == start))) {
            if (mode == 2)
                slot->cur_addr = end << SHIFT;
            else {
                slot->cur_addr = start << SHIFT;
                slot->Backwards = 0;
            }
        }
        break;
    }
}

/* The native chip places the control words and DSP registers immediately after
 * the 64 ring cells. A CPU-supplied cursor is an unsigned byte; the first
 * mixer write can reach MPRO, before the normal six-bit increment. */
static uint32_t *ring_control_word(scsp *s, unsigned index)
{
    switch (index & ~1u) {
    case 64: return &s->ring_cursor;
    case 66: return &s->voice_ram_address;
    case 68: return &s->master;
    case 70: return &s->DSP.context.ram_address;
    case 72: return &s->DSP.context.RBP;
    case 74: return &s->DSP.context.RBL;
    default: return NULL;
    }
}

static void write_ring_word(scsp *s, unsigned index, uint16_t word)
{
    if (index < 64) s->RINGBUF[index] = (int16_t)word;
    else if (index < 76) {
        uint32_t *field = ring_control_word(s, index);
        unsigned shift = (index & 1) * 16;
        *field = (*field & ~(0xffffu << shift)) | ((uint32_t)word << shift);
    } else if (index < 140) s->DSP.context.COEF[index-76] = (int16_t)word;
    else if (index < 172) s->DSP.context.MADRS[index-140] = word;
    else s->DSP.context.MPRO[index-172] = word;
}

static void advance_ring(scsp *s)
{
    s->ring_cursor = (s->ring_cursor & ~255u) | ((s->ring_cursor + 1) & 63);
}

/* An odd register store can enable modulation without running the native
 * table-selection callback. Check at the first actual fetch: an inactive
 * slot can keep that register value indefinitely, including across a state. */
static int lfo_ready(scsp *s, lfo_t *lfo, uint8_t fault)
{
    if (lfo->table) return 1;
    lfo->phase = (uint16_t)(lfo->phase + lfo->phase_step);
    s->voice_fault_address = (lfo->phase >> LFO_SHIFT) * 4u;
    s->voice_fault = fault;
    return 0;
}

static int32_t advance_voice_sample(scsp *s, slot_t *slot)
{
    int32_t sample = 0;
    const uint32_t old_cursor = slot->cur_addr;
    int32_t current_pcm = 0;
    uint32_t step = slot->step;
    uint32_t addr1;

    if (PLFOS(slot)) {
        /* x86 IMUL keeps the low 32 bits of the product before SAR. */
        if (!lfo_ready(s, &slot->PLFO, PITCH_TABLE_FAULT)) return 0;
        uint32_t product = step * (uint32_t)PLFO_Step(&slot->PLFO);
        step = (uint32_t)((int32_t)product >> SHIFT);
    }
    unsigned width = PCM8B(slot) ? 1 : 2;
    addr1 = (old_cursor >> SHIFT) * width;
    if (s->interleaved_mixer) {
        /* 004548c0 modulates the byte offset, then aligns word fetches.
         * The interpolation weight comes from that offset, even at step zero. */
        if (MDL(slot) || MDXSL(slot) || MDYSL(slot)) {
            int first = s->RINGBUF[(s->ring_cursor + MDXSL(slot)) & 63];
            int second = s->RINGBUF[(s->ring_cursor + MDYSL(slot)) & 63];
            int displacement = ((first + second) / 2 * 1024) >> (26 - MDL(slot));
            addr1 += (uint32_t)displacement;
            if (width == 2) addr1 &= ~1u;
        }
        /* Native byte reads are current then next. Word reads are next then
         * current, with the larger weight on the next word at offset zero. */
        uint32_t first_offset = width == 1 ? addr1 : addr1 + 2;
        uint32_t second_offset = width == 1 ? addr1 + 1 : addr1;
        int32_t first_sample, second_sample;
        if (!voice_sample(s, slot, first_offset, &first_sample) ||
            !voice_sample(s, slot, second_offset, &second_sample)) return 0;
        int weight = addr1 & (width == 1 ? 0xfff : 0x7ff);
        sample = (first_sample * (4096 - weight) + second_sample * weight) >> SHIFT;
        /* Both XORs operate on EDI, including its upper 16 bits. */
        if (SBCTL(slot) & 1) sample ^= 0x7fff;
        if (SBCTL(slot) & 2) sample ^= 0x8000;
        if ((old_cursor >> SHIFT) >= LSA(slot) && !slot->Backwards &&
            LPSLNK(slot) && slot->EG.state == ATTACK)
            slot->EG.state = DECAY1;
    } else {
        int weight = old_cursor & 0xfff;
        if (!voice_sample(s, slot, addr1, &current_pcm)) return 0;
        sample = (slot->Prev * (4096 - weight) + current_pcm * weight) >> SHIFT;
    }

    unsigned mode = LPCTL(slot);
    /* Forward and one-shot PCM handlers always add the step, even when
     * software changes mode while a reverse voice is running. */
    if (slot->Backwards && mode >= 2)
        slot->cur_addr -= step;
    else
        slot->cur_addr += step;
    uint32_t position = slot->cur_addr >> SHIFT;
    update_pcm_loop(slot, mode, position, s->interleaved_mixer);
    if (!s->interleaved_mixer) {
        uint32_t history_mask = width == 1 ? 0xfffff000u : 0xfffff800u;
        if ((old_cursor ^ slot->cur_addr) & history_mask)
            slot->Prev = (int16_t)current_pcm;
    }

    return sample;
}

static int32_t UpdateSlot(scsp *source, scsp *s, slot_t *slot, unsigned ring_dest)
{
    /* 004548ce returns before touching the voice or ring. The 32 ordinary
     * handlers selected at 00572980 read PCM regardless of these two bits. */
    if (s->interleaved_mixer && SSCTL(slot)) return 0;
    int32_t sample = advance_voice_sample(source, slot);
    if (source->voice_fault) return 0;
    /* Both the block handler and DSP-enabled 00454b40 apply ALFO and
     * envelope to PCM when the direct bit is set. */
    if (ALFOS(slot)) {
        if (!lfo_ready(source, &slot->ALFO, AMPLITUDE_TABLE_FAULT)) return 0;
        sample = sample * ALFO_Step(&slot->ALFO);
        sample >>= SHIFT;
    }
    if (!s->interleaved_mixer)
        write_ring_word(s, ring_dest, (uint16_t)sample);
    if (slot->EG.state == ATTACK)
        sample = (sample * EG_Update(slot)) >> SHIFT;
    else
        sample = (sample * s->EG_TABLE[EG_Update(slot) >> (SHIFT - 10)]) >> SHIFT;
    if (s->interleaved_mixer && !STWINH(slot))
        write_ring_word(s, ring_dest, (uint16_t)((int32_t)((uint32_t)sample * slot->cached_tl_gain) >> 13));
    return sample;
}

static void add_dsp_send(scsp *s, unsigned input, uint32_t contribution)
{
    if (s->dsp_backend == SCSP_DSP_MAME)
        contribution = (uint32_t)((int32_t)contribution / 16);
    s->DSP.context.MIXS[input] = (int32_t)((uint32_t)s->DSP.context.MIXS[input] + contribution);
}

static void cache_voice_gains(slot_t *slot)
{
    slot->cached_tl_gain = scsp_pcm_level(4096, TL(slot));
    scsp_pcm_pan_gains(DIPAN(slot), DISDL(slot), &slot->cached_left_gain, &slot->cached_right_gain);
}

static int32_t voice_gain(int32_t sample, int32_t gain)
{
    return (int32_t)((uint32_t)sample * (uint32_t)gain) >> 12;
}

/* 004aa950 finishes each voice's entire block before the first DSP step.
 * A voice that stops during that pass still contributes to the direct output,
 * but its scratch samples are skipped in every DSP frame of that block. */
static void render_ordinary_voices(scsp *source, scsp *s, int32_t *out, int n)
{
    for (int sl = 0; sl < 32; ++sl) {
        slot_t *slot = &s->Slots[sl];
        if (!slot->active) continue;
        unsigned ring_dest = (uint8_t)s->ring_cursor;
        cache_voice_gains(slot);
        for (int i = 0; i < n && slot->active; ++i) {
            int32_t sample = UpdateSlot(source, s, slot, ring_dest);
            if (source->voice_fault) return;
            int32_t leveled = voice_gain(sample, slot->cached_tl_gain);
            s->voice_work[sl][i] = (int16_t)leveled;
            out[2*i] += voice_gain(leveled, slot->cached_left_gain);
            out[2*i+1] += voice_gain(leveled, slot->cached_right_gain);
        }
        advance_ring(s);
    }
}

static void render_interleaved_slot(scsp *source, scsp *chip, int sl, int frame, int32_t *stereo)
{
    slot_t *slot = &chip->Slots[sl];
    if (!slot->active) return;
    /* Both slots fetch through the primary chip binding at 005728bc.
     * The outer routine supplies a separate ring destination for each chip. */
    int32_t sample = UpdateSlot(source, chip, slot, (uint8_t)chip->ring_cursor);
    if (source->voice_fault) return;
    if (!frame) cache_voice_gains(slot);
    int32_t leveled = voice_gain(sample, slot->cached_tl_gain);
    add_dsp_send(chip, ISEL(slot), scsp_pcm_send(leveled, IMXL(slot)));
    stereo[0] += voice_gain(leveled, slot->cached_left_gain);
    stereo[1] += voice_gain(leveled, slot->cached_right_gain);
}

static void mix_effects(scsp *s, int32_t *stereo)
{
    for (int e = 0; e < 16; ++e) {
        slot_t *slot = s->Slots + e;
        if (EFSDL(slot)) {
            int32_t left,right;
            if(s->dsp_backend==SCSP_DSP_MAME) {
                uint16_t gain=(uint16_t)((EFPAN(slot)<<8)|(EFSDL(slot)<<13));
                left=(s->DSP.context.EFREG[e]*s->LPANTABLE[gain])>>SHIFT;
                right=(s->DSP.context.EFREG[e]*s->RPANTABLE[gain])>>SHIFT;
            } else scsp_dsp_original_output(s->DSP.context.EFREG[e],EFPAN(slot),EFSDL(slot),&left,&right);
            stereo[0]+=left;stereo[1]+=right;
        }
    }
}

static void run_block_dsp(scsp *s, int frame)
{
    if (!s->interleaved_mixer) {
        for (int sl = 0; sl < 32; ++sl) {
            slot_t *slot = &s->Slots[sl];
            if (slot->active)
                add_dsp_send(s, ISEL(slot), scsp_pcm_send(s->voice_work[sl][frame], IMXL(slot)));
        }
    }
    dsp_step(s);
}

static void render_block(scsp *s, scsp *second, int32_t *out, int n, int clock_timers)
{
    memset(out, 0, (size_t)n * 2 * sizeof *out);
    if (!s->interleaved_mixer && !s->voice_fault) {
        render_ordinary_voices(s, s, out, n);
        if (second && !s->voice_fault) render_ordinary_voices(s, second, out, n);
    }
    for (int i = 0; i < n; ++i) {
        if (s->voice_fault) {
            memset(out+i*2,0,(size_t)(n-i)*2*sizeof *out);
            return;
        }
        if(s->midi_countdown && !--s->midi_countdown) {
            if(s->midi_reply)s->midi_reply(s->midi_reply_user,s->midi_transmit);
            s->midi_out_read=(s->midi_out_read+1)&31;
            if(s->midi_out_read!=s->midi_out_write) {
                s->midi_transmit=s->midi_out[s->midi_out_read];s->midi_countdown=14;
            }
        }
        int32_t *stereo = out + 2*i;
        if (s->interleaved_mixer) {
            for (int sl = 0; sl < 32; ++sl) {
                render_interleaved_slot(s, s, sl, i, stereo);
                if (s->voice_fault) break;
                advance_ring(s);
                /* 004aecb3 advances the slot pointer only. The secondary
                 * cursor, also used by its next slot, is left untouched. */
                if (second) render_interleaved_slot(s, second, sl, i, stereo);
                if (s->voice_fault) break;
            }
        }
        if (!s->voice_fault) {
            run_block_dsp(s, i);
            if (second && !s->DSP.fault) run_block_dsp(second, i);
        }
        if (s->voice_fault || s->DSP.fault || (second && second->DSP.fault)) {
            memset(stereo,0,(size_t)(n-i)*2*sizeof *out);return;
        }
        mix_effects(s, stereo);
        if (second) mix_effects(second, stereo);
        stereo[0] = clampi(stereo[0], -32768, 32767);
        stereo[1] = clampi(stereo[1], -32768, 32767);

        /* MSLC monitor, latched every sample */
        slot_t *m = s->Slots + s->latched_MSLC;
        uint32_t SGC = (uint32_t)m->EG.state & 3, CA = (m->cur_addr >> (SHIFT + 12)) & 0xf;
        uint32_t EG = (0x1f - (m->EG.volume >> (EG_SHIFT + 5))) & 0x1f;
        s->latched_MSLC_data = (uint16_t)((CA << 7) | (SGC << 5) | EG);
        if (clock_timers) scsp_clock_tick(s);
    }
}

static void render(scsp *s, scsp *second, int32_t *out, int n, int clock_timers)
{
    while (n > 0) {
        int block = n < SCSP_MIXER_BLOCK ? n : SCSP_MIXER_BLOCK;
        render_block(s, second, out, block, clock_timers);
        n -= block;
        out += 2 * block;
    }
}

void scsp_render(scsp *s, int32_t *out, int n) { render(s, NULL, out, n, 1); }

/* The A68K scanline clock has already advanced the chip timers. */
void scsp_render_clocked(scsp *s, int32_t *out, int n) { render(s, NULL, out, n, 0); }

/* Native two-chip mixer entry. The shipped board descriptions select one
 * chip. A second initialized chip uses the same mixer mode for this call. */
void scsp_render_pair_clocked(scsp *primary, scsp *second, int32_t *out, int n)
{
    second->interleaved_mixer = primary->interleaved_mixer;
    render(primary, second, out, n, 0);
}

/* ------------------------------------------------------------ interface */

static void init_tables(scsp *s)
{
    for (int i = 0; i < 0x400; ++i) {
        /* ElSemi 004af640 starts 96 dB below unity and takes 1024 steps.
         * Entry 1023 is 4052; reaching full attack uses the separate linear path. */
        float envDB = (float)(3 * (i - 1024)) / 32.0f;
        s->EG_TABLE[i] = (int32_t)(powf(10.0f, envDB * 0.05f) * (float)(1 << SHIFT));
    }
    for (int i = 0; i < 0x10000; ++i) {
        int iTL = i & 0xff, iPAN = (i >> 8) & 0x1f, iSDL = (i >> 0xD) & 7;
        float SegaDB = 0, TLv, PAN, LPAN, RPAN, fSDL;
        if (iTL & 0x01) SegaDB -= 0.4f;
        if (iTL & 0x02) SegaDB -= 0.8f;
        if (iTL & 0x04) SegaDB -= 1.5f;
        if (iTL & 0x08) SegaDB -= 3.0f;
        if (iTL & 0x10) SegaDB -= 6.0f;
        if (iTL & 0x20) SegaDB -= 12.0f;
        if (iTL & 0x40) SegaDB -= 24.0f;
        if (iTL & 0x80) SegaDB -= 48.0f;
        TLv = powf(10.0f, SegaDB / 20.0f);
        SegaDB = 0;
        if (iPAN & 0x1) SegaDB -= 3.0f;
        if (iPAN & 0x2) SegaDB -= 6.0f;
        if (iPAN & 0x4) SegaDB -= 12.0f;
        if (iPAN & 0x8) SegaDB -= 24.0f;
        PAN = (iPAN & 0xf) == 0xf ? 0.0f : powf(10.0f, SegaDB / 20.0f);
        if (iPAN < 0x10) { LPAN = PAN; RPAN = 1.0f; }
        else { RPAN = PAN; LPAN = 1.0f; }
        fSDL = iSDL ? powf(10.0f, SDLT[iSDL] / 20.0f) : 0.0f;
        s->LPANTABLE[i] = (int)FIX(4.0f * LPAN * TLv * fSDL);
        s->RPANTABLE[i] = (int)FIX(4.0f * RPAN * TLv * fSDL);
    }
    s->ARTABLE[0] = s->DRTABLE[0] = 0;
    s->ARTABLE[1] = s->DRTABLE[1] = 0;
    for (int i = 2; i < 64; ++i) {
        double t = ARTimes[i], scale = (double)(1 << EG_SHIFT);
        s->ARTABLE[i] = t != 0.0 ? (int)((1023 * 1000.0) / (44100.0 * t) * scale) : 1024 << EG_SHIFT;
        t = DRTimes[i];
        s->DRTABLE[i] = (int)((1023 * 1000.0) / (44100.0 * t) * scale);
    }
    /* 004ab6a0 draws 256 values from the MS CRT. Both Windows startup
     * acquisitions match this initial seed. This generator belongs to LFO. */
    uint32_t noise_seed = 1;
    for (int i = 0; i < 256; ++i) {
        int a, p;
        a = 255 - i;
        /* 004ab6c4..004ab6d7 uses the descending amplitude value on the
         * second half of the pitch saw as well (0..127, 127..0). */
        p = i < 128 ? i : a;
        s->ALFO_SAW[i] = a; s->PLFO_SAW[i] = p;
        if (i < 128) { a = 255; p = 127; } else { a = 0; p = -128; }
        s->ALFO_SQR[i] = a; s->PLFO_SQR[i] = p;
        a = i < 128 ? 255 - i * 2 : i * 2 - 256;
        if (i < 64) p = i * 2;
        else if (i < 128) p = 255 - i * 2;
        else if (i < 192) p = 256 - i * 2;
        else p = i * 2 - 511;
        s->ALFO_TRI[i] = a; s->PLFO_TRI[i] = p;
        noise_seed = noise_seed * 214013u + 2531011u;
        a = (noise_seed >> 16) & 255;
        p = 128 - a;
        s->ALFO_NOI[i] = a; s->PLFO_NOI[i] = p;
    }
    for (int sc = 0; sc < 8; ++sc) {
        float limit = PSCALE[sc];
        for (int i = -128; i < 128; ++i)
            s->PSCALES[sc][i + 128] = (int)(uint32_t)((float)(1 << LFO_SHIFT) * powf(2.0f, (limit * (float)i / 128.0f) / 1200.0f));
        limit = -ASCALE[sc];
        for (int i = 0; i < 256; ++i)
            s->ASCALES[sc][i] = (int)(uint32_t)((float)(1 << LFO_SHIFT) * powf(10.0f, (limit * (float)i / 256.0f) / 20.0f));
    }
    /* Noise +128 reads one past the original 256-word row. Model the
     * adjacent word explicitly, including the triangle after the last row. */
    for (int sc = 0; sc < 7; ++sc) s->PSCALES[sc][256] = s->PSCALES[sc + 1][0];
    s->PSCALES[7][256] = s->ALFO_TRI[0];
}

scsp *scsp_create(uint8_t *ram, uint32_t ram_size, uint32_t ram_mask, scsp_irq_fn irq, void *user)
{
    if (!ram || ram_size != 0x100000 || ram_mask >= ram_size) return NULL;
    scsp *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    s->ram = ram;
    s->ram_mask = ram_mask;
    s->voice_ram_size = ram_size;
    s->irq = irq;
    s->user = user;
    /* Retain the reserved RNG field in the state archive. */
    s->rng = 0x92d86978;
    init_tables(s);
    scsp_reset(s);
    return s;
}

void scsp_set_interleaved_mixer(scsp *s, int enabled) { s->interleaved_mixer = enabled; }

void scsp_destroy(scsp *s) { free(s); }

void scsp_bind_cpu_write_frame(scsp *s, const uint32_t *wrapper_sp, uint32_t code_address)
{
    s->cpu_write_sp = wrapper_sp;
    s->dsp_code_address = code_address;
}

void scsp_bind_irq_register(scsp *s, uint32_t *irq_register)
{
    s->irq_register = irq_register;
}

void scsp_set_dsp_backend(scsp *s,unsigned backend) {
    if(s && backend<=SCSP_DSP_MAME && s->dsp_backend!=backend) {
        s->dsp_backend=backend;scsp_reset(s);
    }
}
unsigned scsp_get_dsp_backend(const scsp *s) {return s?s->dsp_backend:SCSP_DSP_ORIGINAL;}

void scsp_reset(scsp *s)
{
    s->voice_fault = 0;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_fault_address = 0;
    memset(&s->u, 0, sizeof s->u);
    memset(s->Slots, 0, sizeof s->Slots);
    memset(s->RINGBUF, 0, sizeof s->RINGBUF);
    s->ring_cursor = 0;
    s->master = 1;
    scsp_dsp_original_init(&s->DSP);
    if(s->dsp_backend==SCSP_DSP_MAME)s->DSP.context.RBL=8192;
    s->IrqTimA = s->IrqTimBC = s->IrqMidi = s->IrqCPU = s->IrqDMA = 0;
    s->MidiR = s->MidiW = s->MidiCount = s->cpu_irq_level = 0;
    memset(s->cpu_midi_output, 0, sizeof s->cpu_midi_output);
    s->cpu_midi_cursor = s->cpu_midi_count = 0;
    s->midi_out_read=s->midi_out_write=s->midi_transmit=0;s->midi_countdown=0;
    s->mcieb = s->mcipd = 0;
    s->latched_MSLC = 0;
    for (int i = 0; i < 32; ++i) {
        s->Slots[i].slot = i;
        s->Slots[i].active = 0;
        s->Slots[i].EG.state = RELEASE;
    }
    memset(s->TimCnt,0,sizeof s->TimCnt);memset(s->TimExpired,0,sizeof s->TimExpired);
}

/* The original process starts with zero-filled slot records. 004af690
 * sets the slot indices. A subsequent key-off scan puts each unkeyed slot
 * in RELEASE. A warm A68K reset only resets the CPU. */
void scsp_original_power_on(scsp *s)
{
    scsp_reset(s);
    for (unsigned i = 0; i < 32; ++i) s->Slots[i].EG.state = ATTACK;
}

uint16_t scsp_read16(scsp *s, uint32_t offset) { return r16(s, offset & 0xffe); }
static void UpdateCpuRegR(scsp *s,unsigned reg)
{
    /* Native 004ab230; notably no IRQ clear and no synthesized MIDI flags. */
    switch(reg&0x3f) {
    case 4: case 5:
        s->u.data[2]=(uint16_t)((s->u.data[2]&0xff00)|s->MidiStack[s->MidiR]);
        if(s->MidiR!=s->MidiW)s->MidiR=(s->MidiR+1)&127;
        s->MidiCount--; /* Includes empty reads, wrapping exactly like DEC byte. */
        break;
    case 8: case 9: {
        uint16_t old=s->u.data[4];unsigned slot=old>>11;
        s->u.data[4]=(uint16_t)((old&0xf87f)|((s->Slots[slot].cur_addr>>24)<<7));
        break;
    }
    }
}
/* CPU reads at 0x400..0x5ff first decode a six-bit update selector,
 * then load bytes at the eight-bit offset inside the original chip object.
 * The slot records have an x86 stride independent of sizeof(slot_t). */
/* Native 32-bit data addresses are observable over the CPU bus. Disabled
 * LFOs retain their last binding. A never-configured LFO has null pointers. */
static uint32_t lfo_object_word(const lfo_t *lfo, unsigned offset, unsigned amplitude)
{
    static const uint32_t wave[2][4] = {
        {0x010bf560, 0x010bf960, 0x010c31b0, 0x010982e8},
        {0x010bfd68, 0x010c3630, 0x0109a6e8, 0x010bdf50}
    };
    if (offset == 0) return lfo->phase;
    if (offset == 4) return lfo->phase_step;
    if (!lfo->binding) return 0;
    if (offset == 8) return wave[amplitude][(lfo->binding >> 3) & 3];
    return (amplitude ? 0x010c11b0u : 0x010986e8u) + (lfo->binding & 7) * 0x400;
}

static uint8_t cpu_object_byte(const scsp *s, unsigned at)
{
    if (at < 0x30) return (uint8_t)(s->u.data[at / 2] >> ((at & 1) * 8));
    const slot_t *slot = &s->Slots[(at - 0x30) / 0x8c];
    unsigned field = (at - 0x30) % 0x8c;
    if (field < 0x20) return (uint8_t)(slot->u.data[field / 2] >> ((field & 1) * 8));
    uint32_t word;
    switch (field & ~3u) {
    case 0x20: word = slot->active | ((uint32_t)slot->active_high << 8); break;
    case 0x24: word = slot->sample_base; break;
    case 0x28: word = slot->cur_addr; break;
    case 0x2c: word = slot->step; break;
    case 0x30: word = slot->Backwards; break;
    case 0x34: word = (uint32_t)slot->EG.volume; break;
    case 0x38: word = (uint32_t)slot->EG.state; break;
    case 0x40: word = (uint32_t)slot->EG.AR; break;
    case 0x44: word = (uint32_t)slot->EG.D1R; break;
    case 0x48: word = (uint32_t)slot->EG.D2R; break;
    case 0x4c: word = (uint32_t)slot->EG.RR; break;
    case 0x50: word = (uint32_t)slot->EG.DL; break;
    case 0x54: word = slot->EG.EGHOLD; break;
    case 0x78: word = (uint32_t)slot->slot; break;
    case 0x7c: word = (uint16_t)slot->Prev; break;
    case 0x80: word = slot->cached_tl_gain; break;
    case 0x84: word = (uint32_t)slot->cached_left_gain; break;
    case 0x88: word = (uint32_t)slot->cached_right_gain; break;
    default:
        word = field >= 0x58 && field < 0x78
             ? lfo_object_word(field < 0x68 ? &slot->PLFO : &slot->ALFO,
                               (field - 0x58) & 12, field >= 0x68)
             : 0; /* The unused +0x3c word retains its loader zero. */
        break;
    }
    return (uint8_t)(word >> ((field & 3) * 8));
}
uint8_t scsp_cpu_read8(scsp *s,uint32_t offset)
{
    offset&=0xffff;
    /* 004ae870: byte reads of ring/DSP space return zero, unlike r16(). */
    if(offset>=0x600)return 0;
    if(offset>=0x400) {
        UpdateCpuRegR(s,offset);return cpu_object_byte(s,(offset&0xff)^1);
    }
    uint16_t v=scsp_read16(s,offset);
    return (uint8_t)(offset&1?v:v>>8);
}
/* The native ring window continues into these 32-bit chip fields.
 * A CPU word (even on the upper guest lane) accesses one native half. */
uint16_t scsp_cpu_read16(scsp *s,uint32_t offset)
{
    offset&=0xffff;
    /* 004ae800: DSP space is write-only to a CPU word read. DMA retains r16. */
    if(offset>=0x700)return 0;
    /* The native ring index runs into the first 52 DSP coefficients. */
    if (offset >= 0x680 && offset < 0x698) {
        uint32_t *field = ring_control_word(s, (offset-0x600)/2);
        if (field) return (uint16_t)(*field >> ((offset & 2) * 8));
    }
    if(offset>=0x698)return (uint16_t)s->DSP.context.COEF[(offset-0x698)/2];
    if(offset>=0x400 && offset<0x600) {
        UpdateCpuRegR(s,offset);unsigned at=offset&0xff;
        return (uint16_t)(cpu_object_byte(s,at)|(cpu_object_byte(s,at+1)<<8));
    }
    if(offset<0x400 && (offset&1)) {
        const slot_t *slot=&s->Slots[offset>>5];unsigned at=offset&31;
        /* Native MOVZX reads at the exact odd byte in word-swapped storage.
         * The final register byte is followed by native slot.active (+0x20),
         * cleared by StopSlot 004ab331. Do not read the portable struct layout. */
        unsigned next=at==31?slot->active:slot->u.data[(at+1)/2]&255u;
        return (uint16_t)((slot->u.data[at/2]>>8)|(next<<8));
    }
    return scsp_read16(s,offset);
}

/* Original x86 arithmetic flags are data consumed by recovered A68K handlers.
 * These helpers model the observed ordinary flag domain, not the host ABI.
 * Logical/shift AF follows the pinned x86 oracle; it is undefined by x86 ISA. */
static uint32_t cpu_logic_flags(uint32_t flags,uint32_t value,unsigned bits)
{
    uint32_t mask=bits==8?255u:0xffffffffu;value&=mask;
    unsigned parity=(unsigned)__builtin_parity(value&255u);
    return (flags&~0x8d5u)|(!parity?4u:0u)|(!value?0x40u:0u)|
        (value&(1u<<(bits-1))?0x80u:0u);
}
static uint32_t cpu_sub_flags(uint32_t flags,uint32_t a,uint32_t b,unsigned bits)
{
    uint32_t mask=bits==8?255u:0xffffffffu,sign=1u<<(bits-1);
    a&=mask;b&=mask;uint32_t result=(a-b)&mask;
    return cpu_logic_flags(flags,result,bits)|(a<b?1u:0u)|((a^b^result)&16u)|
        (((a^b)&(a^result)&sign)?0x800u:0u);
}
/* Flags left by the compiler epilogue's ADD ESP,imm32. */
static uint32_t cpu_stack_add_flags(uint32_t flags, uint32_t result, uint32_t amount)
{
    uint32_t before = result - amount;
    return cpu_logic_flags(flags, result, 32) | (result < before ? 1u : 0u) |
           ((before ^ amount ^ result) & 16u) |
           ((~(before ^ amount) & (before ^ result)) >> 31 << 11);
}
int scsp_cpu_read_observed(scsp *s,uint32_t address,unsigned width,
                          uint32_t input_flags,scsp_cpu_observation *out)
{
    if(!s || !out || address<0x100000 || address>=0x110000 ||
       (width!=1 && width!=2 && width!=4))return 0;
    unsigned offset=address&0xffff;uint32_t eax=0,edx=0,flags=input_flags;
    /* DATA long wrapper jumps through EDX; byte/word jump through EAX.
     * These are original PE tokens, never executable portable addresses. */
    if(width==4) {
        *out=(scsp_cpu_observation){0xffffffffu,0x004ab220u,
            cpu_logic_flags(flags,0xffffffffu,32)};return 1;
    }
    if(offset<0x400) {
        uint32_t slot=(offset>>5)*0x8c,base=0x0109aae8u,result=slot+base;
        flags=cpu_logic_flags(flags,result,32)|((slot^base^result)&16u);
        /* This bounded positive addition cannot carry or overflow. */
        eax=width==1?(result&0xffffff00u)|scsp_cpu_read8(s,offset):scsp_cpu_read16(s,offset);
    } else if(offset<0x600) {
        unsigned at=offset&255u,reg=offset&63u;
        eax=reg-4u;flags=cpu_sub_flags(flags,eax,5,32);
        if(reg==4 || reg==5) {
            eax=s->MidiR;
            if(s->MidiR!=s->MidiW)eax=(eax+1)&127u;
            edx=(s->u.data[2]&0xff00u)|s->MidiStack[s->MidiR];
            /* CMP(equal) or AND 127 leaves CF zero before DEC count. */
            flags=cpu_sub_flags(flags,s->MidiCount,1,8)&~1u;
        } else if(reg==8 || reg==9) {
            uint32_t old=s->u.data[4];eax=(s->Slots[old>>11].cur_addr>>24)<<7;
            edx=(old&0xf87fu)|eax;flags=cpu_logic_flags(flags,edx,32);
        }
        if(width==1) {
            flags=cpu_logic_flags(flags,at^1u,32);
            eax=(eax&0xffffff00u)|scsp_cpu_read8(s,offset);
        } else eax=scsp_cpu_read16(s,offset);
    } else if(width==1) {
        eax=0x004ae800u; /* XOR AL,AL leaves the callback token's high bytes. */
        flags=offset<0x700?cpu_logic_flags(flags,0,8):cpu_sub_flags(flags,offset,0x700,32);
    } else if(offset<0x700) {
        unsigned index=offset-0x600;edx=0x0109aae8u;
        flags=cpu_logic_flags(flags,index>>1,32)|(index&1u);
        eax=scsp_cpu_read16(s,offset);
    } else flags=cpu_sub_flags(flags,offset,0x700,32);
    *out=(scsp_cpu_observation){eax,edx,flags};return 1;
}

static scsp_cpu_completion cpu_irq_completion(const scsp *s,uint32_t flags)
{
    uint32_t pend=s->u.data[0x20/2],en=s->u.data[0x1e/2];
    if(s->MidiW!=s->MidiR)return (scsp_cpu_completion){s->IrqMidi,
        cpu_sub_flags(flags,s->MidiW,s->MidiR,8)};
    if(!pend)return (scsp_cpu_completion){0,cpu_logic_flags(flags,0,32)};
    if(pend&en&0x40)return (scsp_cpu_completion){pend,cpu_logic_flags(flags,en&0x40,8)};
    if(pend&en&0x80)return (scsp_cpu_completion){pend,cpu_logic_flags(flags,en,8)};
    if(pend&en&0x100)return (scsp_cpu_completion){s->IrqTimBC,cpu_logic_flags(flags,en&0x100,32)};
    return (scsp_cpu_completion){pend,cpu_logic_flags(flags,0,32)};
}
/* The timer and interrupt updates test the low master byte after storing. */
static int master_gated(unsigned word)
{
    return (word >= 0x18 && word <= 0x1c) || (word >= 0x22 && word <= 0x28);
}

static void UpdateCpuReg(scsp *s,unsigned reg)
{
    /* ElSemi 004af050: 0x12..0x17 select sparse-table entry 2, a bare RET
     * at 004af26c. CPU stores remain visible, but do not update DMA internals,
     * copy memory, clear the start bit or assert DMA IRQ. User-approved
     * original behavior, shared by both CPU/DSP backend choices. The internal
     * w16/UpdateReg path remains separate; do not route it through this gate. */
    unsigned word=reg&~1u;
    if (master_gated(word) && !(uint8_t)s->master) return;
    if (word == 2) {
        /* CPU callback 004af06d decodes all seven base bits from the
         * stored word, including after a write to just one byte. */
        set_dsp_ring(s, 0x7f);
        return;
    }
    if (word == 6) {
        s->cpu_midi_output[s->cpu_midi_cursor] = (uint8_t)s->u.data[3];
        s->cpu_midi_cursor = (s->cpu_midi_cursor + 1) & 127;
        s->cpu_midi_count++;
    }
    /* 004af059 also branches directly to RET for selectors 0x2a..0x2f.
     * The CPU store remains visible without changing the internal IRQ state. */
    if((word>=0x12 && word<=0x16) || word>=0x2a)return;
    UpdateReg(s,(int)reg);
}
static scsp_cpu_completion cpu_global_write_completion(scsp *s,unsigned reg,uint32_t flags)
{
    UpdateCpuReg(s,reg);
    unsigned word=reg&~1u;
    if (word == 2) {
        /* EAX holds the length selector. Selector 0 returns after AND,
         * and selectors 1..3 after an equal CMP. Each leaves ZF/PF set. */
        return (scsp_cpu_completion){RBL(s), cpu_logic_flags(flags, 0, 32)};
    }
    if (word == 6) {
        /* Cursor AND clears CF. INC byte supplies flags from the new count. */
        uint8_t count = s->cpu_midi_count;
        uint32_t result = cpu_logic_flags(flags, count, 8);
        if (!(count & 15)) result |= 0x10;
        if (count == 0x80) result |= 0x800;
        return (scsp_cpu_completion){s->cpu_midi_cursor, result};
    }
    if (master_gated(word) && !(uint8_t)s->master) {
        /* 004af0f0..004af22e: the SCI levels use EDX for the chip
         * pointer, leaving sparse-table index 7 in EAX. */
        return (scsp_cpu_completion){word >= 0x24 ? 7u : 0x0109aae8u,
                                     cpu_sub_flags(flags, 0, 0, 8)};
    }
    if(word>=0x18 && word<=0x1c) {
        uint32_t counter=s->TimCnt[(word-0x18)/2];
        return (scsp_cpu_completion){counter,cpu_logic_flags(flags,counter,32)};
    }
    if(word==0x22)return cpu_irq_completion(s,flags);
    if(word>=0x24 && word<=0x28)return (scsp_cpu_completion){s->IrqMidi,
        cpu_logic_flags(flags,s->IrqMidi,8)};
    /* 004af050's sparse jump table has index 2 for DMA and 8 for other no-ops.
     * MOVZX of the index preserves flags from CMP (reg - 2), 0x27. */
    uint32_t selector=reg-2u;
    return (scsp_cpu_completion){selector>0x27?selector:(word>=0x12 && word<=0x16?2u:8u),
        cpu_sub_flags(flags,selector,0x27,32)};
}
/* CPU long stores put the high word at the lower 68000 address. Both words
 * reach the register array before ElSemi calls either update routine. */
/* The two register regions are laid out as little-endian words. A byte
 * store selects the opposite lane; word and long stores retain odd offsets.
 * payload is in x86 memory order after the native longword rotate. */
static uint32_t register_payload(unsigned width, uint32_t value)
{
    return width == 4 ? (value << 16) | (value >> 16) : value;
}

static void store_register_byte(uint16_t *words, unsigned at, uint8_t value)
{
    unsigned shift = (at & 1) * 8;
    words[at/2] = (uint16_t)((words[at/2] & ~(255u << shift)) | ((unsigned)value << shift));
}

static void store_slot_byte(slot_t *slot, unsigned at, uint8_t value)
{
    if (at < 32) store_register_byte(slot->u.data, at, value);
    else if (at == 32) slot->active = value;
    else store_register_byte(&slot->active_high, at-33, value);
}

/* The two byte lanes both replace an entire signed mixer word. Beyond
 * cell 63 the original aliases its chip object. Only long writes there
 * have no effect; byte/word aliases require their own field bindings. */
int scsp_cpu_write_ring(scsp *s, unsigned offset, unsigned width, uint32_t value)
{
    if (offset < 0x600 || offset >= 0x700) return 0;
    if (width == 4) return 1;
    if (width != 1 && width != 2) return 0;
    uint16_t word = (uint16_t)(width == 1 ? value & 255 : value);
    write_ring_word(s, (offset-0x600)/2, word);
    return 1;
}

static uint8_t *cpu_dsp_word(scsp *s, unsigned reg);

static int cpu_store(scsp *s,uint32_t address,unsigned width,uint32_t value,
                     uint32_t input_flags,scsp_cpu_completion *out, int observe_return)
{
    if(!s || !out || address<0x100000 || address>=0x110000 ||
       (width!=1 && width!=2 && width!=4))return 0;
    unsigned offset = address - 0x100000;
    if (offset >= 0x430 && offset < 0x600) {
        /* The native page wrapper loads the width-specific callback into
         * EAX. In this hole the callback returns before replacing it. */
        uint32_t token = width == 1 ? 0x004afb00 : width == 2 ? 0x004afa20 : 0x004af900;
        *out = (scsp_cpu_completion){token, cpu_sub_flags(input_flags, offset, 0x430, 32)};
        return 1;
    }
    if (scsp_cpu_write_ring(s, offset, width, value)) {
        if (width == 4) {
            out->eax = 0x004af900u;
            out->flags = cpu_sub_flags(input_flags, offset, 0x700, 32);
        } else {
            out->eax = 0x0109aae8u;
            out->flags = cpu_logic_flags(input_flags, (offset - 0x600) >> 1, 32) | (offset & 1u);
        }
        return 1;
    }
    if (offset >= 0x700) {
        unsigned reg = offset;
        unsigned trigger = width == 4 ? 0xbfc : 0xbfe;
        if (reg >= 0xc00) {
            *out = (scsp_cpu_completion){0x0109aae8u, cpu_sub_flags(input_flags, reg, trigger, 32)};
            return 1;
        }
        if (observe_return && reg == trigger && (!s->cpu_write_sp || !*s->cpu_write_sp || !s->dsp_code_address))
            return 0;
        if (width == 4)
            scsp_cpu_write_dsp32(s, reg, value);
        else if (width == 2 && (reg & 1) && s->dsp_backend == SCSP_DSP_ORIGINAL) {
            uint16_t word = (uint16_t)value;
            memcpy(cpu_dsp_word(s, reg & ~1u), &word, sizeof word);
        } else {
            unsigned shift = width == 1 && !(reg & 1) ? 8 : 0;
            uint16_t mask = width == 1 ? (uint16_t)(0xffu << shift) : 0xffff;
            scsp_write16(s, reg, (uint16_t)(value << shift), mask);
        }
        if (observe_return && reg == trigger) {
            /* 004aa7f0 saves EDI and calls the compiler. Its final ADD
             * ESP,0xd0 returns to that virtual frame before the two RETs. */
            unsigned steps = scsp_dsp_program_length(&s->DSP.context);
            out->eax = steps ? steps : s->dsp_code_address;
            out->flags = cpu_stack_add_flags(input_flags, *s->cpu_write_sp - 8, 0xd0);
            return 1;
        }
        /* Pinned x86 chip address returned by the CPU callback. */
        *out = (scsp_cpu_completion){0x0109aae8u, cpu_sub_flags(input_flags, reg, trigger, 32)};
        return 1;
    }
    if (address >= 0x100430) return 0;
    if (address < 0x100400) {
        unsigned reg = address & 31u;
        unsigned last_update = width == 4 ? reg + 2 : reg;
        slot_t *slot = &s->Slots[offset / 32];
        unsigned start = width == 1 ? reg ^ 1u : reg;
        uint32_t payload = register_payload(width, value);
        if (observe_return && (last_update & ~1u) == 0x12 && (!s->cpu_write_sp || !*s->cpu_write_sp)) {
            unsigned depth = ALFOS(slot);
            if (start <= 0x12 && 0x12 < start+width)
                depth = (payload >> (8*(0x12-start))) & 7;
            if (depth) return 0;
        }
        for (unsigned i = 0; i < width; ++i)
            store_slot_byte(slot, start+i, (uint8_t)(payload >> (8*i)));
        if (reg < 2) {
            /* 004af840 scans every slot. EAX holds slot 31's control word
             * before KEYONEX is cleared, even if slot 31 triggered the scan. */
            unsigned executed = KEYONEX(slot);
            uint32_t final_eax = executed ? s->Slots[31].u.data[0] : 0;
            UpdateSlotReg(s, (int)(slot - s->Slots), (int)reg);
            if (last_update < 2) {
                out->eax = final_eax;
                out->flags = cpu_logic_flags(input_flags, executed ? slot->u.data[0] : 0, 16);
                return 1;
            }
        }
        /* Long stores update both register words after both have been written.
         * With LFO first, the second update replaces its host scratch. */
        if (width == 4 && (reg & ~1u) == 0x10) slot->step = Step(slot);
        if (width == 4 && (reg & ~1u) == 0x12) Compute_LFO(s, slot);
        if ((last_update & ~1u) == 0x12) {
            Compute_LFO(s, slot);
            if (!observe_return) return 1;
            if (ALFOS(slot)) {
                /* At the four waveform returns ADD ESP,12 leaves a different
                 * frame depth for each width-specific SCSP write wrapper. */
                unsigned depth = width == 1 ? 40 : width == 2 ? 36 : 44;
                out->eax = slot->ALFO.phase_step;
                out->flags = cpu_stack_add_flags(input_flags, *s->cpu_write_sp - depth, 12);
            } else {
                out->eax = PLFOS(slot) ? slot->PLFO.phase_step : 3;
                out->flags = cpu_logic_flags(input_flags, 0, 32);
            }
            return 1;
        }
        if (width == 4 && reg >= 8 && reg < 12 && slot->active)
            Compute_EG(s, slot);
        if (last_update >= 8 && last_update < 12) {
            if (slot->active) Compute_EG(s, slot);
            /* 004aea28: AND AL,0x20 supplies EAX and arithmetic flags.
             * Inactive slots return the sparse-table index after CMP active,0. */
            out->eax = slot->active ? slot->EG.EGHOLD : 1;
            out->flags = cpu_logic_flags(input_flags, slot->active ? slot->EG.EGHOLD : 0, 8);
            return 1;
        }
        if ((last_update & ~1u) == 0x10) {
            uint32_t high = pitch_product_high(slot);
            slot->step = high >> 15;
            out->eax = slot->step;
            /* SHR EAX,15 shifts bit 14 into CF. Observed AF and OF are zero. */
            out->flags = cpu_logic_flags(input_flags, slot->step, 32) | ((high >> 14) & 1u);
            return 1;
        }
        /* 004af810: CMP leaves the flags. The sparse table yields EAX=4
         * for its inert entries. Above 0x13 the jump bypasses the table. */
        out->eax = last_update > 0x13 ? last_update : 4;
        out->flags = cpu_sub_flags(input_flags, last_update, 0x13, 32);
        return 1;
    }
    unsigned reg=address-0x100400;
    unsigned start = width == 1 ? reg ^ 1u : reg;
    uint32_t payload = register_payload(width, value);
    for (unsigned i = 0; i < width; ++i) {
        unsigned at = start+i;
        uint8_t byte = (uint8_t)(payload >> (8*i));
        if (at < 0x30) store_register_byte(s->u.data, at, byte);
        else store_register_byte(s->Slots[0].u.data, at-0x30, byte);
    }
    if(width==4) {
        (void)cpu_global_write_completion(s,reg,input_flags);
        reg+=2;
    }
    *out=cpu_global_write_completion(s,reg,input_flags);return 1;
}
int scsp_cpu_write_observed(scsp *s,uint32_t address,unsigned width,uint32_t value,
                            uint32_t input_flags,scsp_cpu_completion *out)
{
    return cpu_store(s,address,width,value,input_flags,out,1);
}

void scsp_cpu_store(scsp *s,uint32_t address,unsigned width,uint32_t value)
{
    /* A value-only CPU consumes the same board side effects. It has no
     * original x86 caller frame from which to derive a host return value. */
    scsp_cpu_completion unused;
    cpu_store(s,address,width,value,0,&unused,0);
}

int scsp_cpu_ack_observed(scsp *s,uint32_t input_flags,scsp_cpu_completion *out)
{
    if(!s || !out)return 0;
    scsp_cpu_ack_irq(s);
    /* Live callback 004b3090 executes OR EAX,-1 and returns. */
    *out=(scsp_cpu_completion){0xffffffffu,cpu_logic_flags(input_flags,0xffffffffu,32)};
    return 1;
}

/* CPU callbacks 004af900/004afa20 address adjacent words in the
 * original DSP object. Index its checked byte representation so a store
 * crossing MADRS/MPRO or MPRO/TEMP never crosses a C array boundary. */
static uint8_t *cpu_dsp_word(scsp *s, unsigned reg)
{
    size_t at = reg < 0x800 ? offsetof(scsp_dsp_context, COEF) + reg - 0x700
                            : offsetof(scsp_dsp_context, MPRO) + reg - 0x800;
    return (uint8_t *)&s->DSP.context + at;
}

void scsp_cpu_write_dsp32(scsp *s, uint32_t reg, uint32_t value)
{
    if (reg < 0x700 || reg >= 0xc00) return;
    unsigned start = reg;
    reg &= ~1u;
    uint8_t *p = cpu_dsp_word(s, reg);
    uint16_t high = (uint16_t)(value >> 16), low = (uint16_t)value;
    memcpy(p, &high, sizeof high);
    if (s->dsp_backend == SCSP_DSP_MAME && reg == 0xbf0) dsp_mame_start(s);
    memcpy(p + 2, &low, sizeof low);
    if (s->dsp_backend == SCSP_DSP_MAME && reg + 2 == 0xbf0) dsp_mame_start(s);
    if (s->dsp_backend == SCSP_DSP_ORIGINAL && start == 0xbfc) scsp_dsp_original_start(&s->DSP);
}

void scsp_write16(scsp *s, uint32_t offset, uint16_t data, uint16_t mask)
{
    offset &= 0xffe;
    if(offset>=0x400 && offset<0x430) {
        /* CPU callbacks 004afa20/004afb00 store directly before UpdateReg.
         * A read/merge through r16 would dequeue MIDI or alter its IRQ.
         * SCIPD is a raw writable register here, unlike the inherited DMA
         * register interface. Keep CPU and chip-internal accesses distinct. */
        uint16_t *reg=&s->u.data[(offset-0x400)/2];
        *reg=(uint16_t)((*reg&~mask)|(data&mask));
        UpdateCpuReg(s,offset-0x400);
        return;
    }
    if (offset >= 0x700 && offset < 0xc00) {
        if (offset >= 0x7c0 && offset < 0x800 && mask != 0xffff) return;
        uint8_t *p = cpu_dsp_word(s, offset);
        uint16_t word;
        memcpy(&word, p, sizeof word);
        word = (uint16_t)((word & ~mask) | (data & mask));
        memcpy(p, &word, sizeof word);
        if (s->dsp_backend == SCSP_DSP_MAME && offset == 0xbf0) dsp_mame_start(s);
        if (s->dsp_backend == SCSP_DSP_ORIGINAL && offset == 0xbfe && (mask & 0xff00))
            scsp_dsp_original_start(&s->DSP);
        return;
    }
    uint16_t tmp = r16(s, offset);
    tmp = (uint16_t)((tmp & ~mask) | (data & mask));
    w16(s, offset, tmp);
}

void scsp_midi_in(scsp *s, uint8_t data)
{
    s->MidiStack[s->MidiW] = data;
    s->MidiW = (s->MidiW + 1) & 127;
    s->MidiCount++;
}

void scsp_cpu_ack_irq(scsp *s)
{
    /* Mirror the accepted request cleared at 00462b9c. The live callback
     * autovectors. The following timer tick performs the ordinary IRQ check. */
    irq_line(s,s->cpu_irq_level,0);s->cpu_irq_level=0;
}

int scsp_slots_active(const scsp *s, int *mvol)
{
    int n = 0;
    for (int i = 0; i < 32; i++)
        n += s->Slots[i].active != 0;
    if (mvol)
        *mvol = MVOL(s);
    return n;
}

void scsp_state_archive(scsp *s, m2_state *a)
{
    const uint32_t expected_schema = 0x39504353u; /* SCP9 includes slot gain, the writable ring cursor and master word. */
    uint32_t schema=expected_schema;
    m2_state_value(a,&schema,sizeof schema);
    if(a->failed || schema!=expected_schema) {a->failed=1;return;}
    unsigned backend=s->dsp_backend;
    m2_state_value(a,&backend,sizeof backend);
    if(a->failed || backend!=s->dsp_backend) {a->failed=1;return;}
    if(a->mode==M2_STATE_CHECK) {
        scsp *copy=malloc(sizeof *copy);
        if(!copy) { a->failed=1;return; }
        *copy=*s;m2_state probe=*a;probe.mode=M2_STATE_LOAD;
        /* The schema/backend markers were already consumed above. */
        probe.pos-=sizeof schema+sizeof backend;scsp_state_archive(copy,&probe);free(copy);
        a->pos=probe.pos;a->failed=probe.failed;return;
    }

#define F(m) M2_FIELD(a,s,m)
    F(u);
    for(int i=0;i<32;i++) {
        slot_t *v=&s->Slots[i];
        M2_FIELD(a,v,u); M2_FIELD(a,v,Backwards); M2_FIELD(a,v,active);
        M2_FIELD(a,v,cur_addr); M2_FIELD(a,v,nxt_addr); M2_FIELD(a,v,step); M2_FIELD(a,v,EG);
        M2_FIELD(a,v,PLFO.phase); M2_FIELD(a,v,PLFO.phase_step);
        M2_FIELD(a,v,ALFO.phase); M2_FIELD(a,v,ALFO.phase_step); M2_FIELD(a,v,Prev); M2_FIELD(a,v,sample_base); M2_FIELD(a,v,cached_tl_gain);
        M2_FIELD(a,v,cached_left_gain); M2_FIELD(a,v,cached_right_gain); M2_FIELD(a,v,active_high);
        M2_FIELD(a,v,PLFO.binding); M2_FIELD(a,v,ALFO.binding);
        if ((v->PLFO.binding && (v->PLFO.binding >> 5) != 1) ||
            (v->ALFO.binding && (v->ALFO.binding >> 5) != 1)) { a->failed=1; return; }
        if(a->mode==M2_STATE_LOAD && !a->failed) {
            /* Generated tables belong to this chip in the loading process. */
            uint32_t p=v->PLFO.phase_step, q=v->ALFO.phase_step;
            if (v->PLFO.binding)
                LFO_ComputeStep(s,&v->PLFO,LFOF(v),(v->PLFO.binding >> 3)&3,v->PLFO.binding&7,0);
            else v->PLFO.table = v->PLFO.scale = NULL;
            if (v->ALFO.binding)
                LFO_ComputeStep(s,&v->ALFO,LFOF(v),(v->ALFO.binding >> 3)&3,v->ALFO.binding&7,1);
            else v->ALFO.table = v->ALFO.scale = NULL;
            v->PLFO.phase_step=p;v->ALFO.phase_step=q;v->slot=i;
        }
    }
    F(RINGBUF); F(ring_cursor); F(master); F(IrqTimA); F(IrqTimBC); F(IrqMidi); F(IrqCPU); F(IrqDMA);
    F(latched_MSLC); F(latched_MSLC_data); F(MidiStack); F(MidiW); F(MidiR);F(MidiCount);F(cpu_irq_level);
    F(cpu_midi_output); F(cpu_midi_cursor); F(cpu_midi_count);
    F(TimCnt);F(TimExpired); F(dma); F(mcieb); F(mcipd);
    if(s->dsp_backend==SCSP_DSP_MAME) {
        F(DSP.context);
        F(DSP.ram); /* A PCM voice can select this allocation on either backend. */
    } else scsp_dsp_original_archive(&s->DSP,a);
    F(rng); F(voice_ram_address); F(voice_fault); F(voice_fault_address);
#undef F

    if (s->voice_fault > AMPLITUDE_TABLE_FAULT || (!s->voice_fault && s->voice_fault_address)) a->failed=1;
    if(s->cpu_midi_cursor>=128 || s->MidiR>=128 || s->MidiW>=128 || s->latched_MSLC>=32
        || s->cpu_irq_level>7 || s->TimExpired[0]>1 || s->TimExpired[1]>1 || s->TimExpired[2]>1
        || s->DSP.context.LastStep<0 || s->DSP.context.LastStep>128)a->failed=1;
    for(int i=0;i<32;i++)if((uint32_t)s->Slots[i].cached_left_gain>16384 || (uint32_t)s->Slots[i].cached_right_gain>16384 || s->Slots[i].cached_tl_gain>4096 || s->Slots[i].sample_base>0xfffff || s->Slots[i].EG.state<0 || s->Slots[i].EG.state>3
        || s->Slots[i].EG.volume<0 || s->Slots[i].EG.volume>(1023<<EG_SHIFT))a->failed=1;
}


/* Optional Manx TT serial return, matching SM2's 31.25 kbaud/14-sample wire. */
void scsp_set_midi_reply(scsp *s,void (*reply)(void *,uint8_t),void *user) {
    s->midi_reply=reply;s->midi_reply_user=user;
}
void scsp_reset_midi(scsp *s) {
    memset(s->midi_out,0,sizeof s->midi_out);
    s->midi_out_read=s->midi_out_write=s->midi_transmit=0;s->midi_countdown=0;
}
void scsp_midi_state_archive(scsp *s,m2_state *a) {
    uint8_t bytes[32],r=s->midi_out_read,w=s->midi_out_write,tx=s->midi_transmit;
    unsigned count=s->midi_countdown;memcpy(bytes,s->midi_out,sizeof bytes);
    m2_state_bytes(a,bytes,sizeof bytes);m2_state_value(a,&r,1);m2_state_value(a,&w,1);
    m2_state_value(a,&tx,1);m2_state_value(a,&count,sizeof count);
    if(r>=32 || w>=32 || count>14)a->failed=1;
    if(a->mode==M2_STATE_LOAD && !a->failed) {
        memcpy(s->midi_out,bytes,sizeof bytes);s->midi_out_read=r;s->midi_out_write=w;
        s->midi_transmit=tx;s->midi_countdown=count;
    }
}

const char *scsp_fault(const scsp *s,uint32_t *address) {
    if (!s) return NULL;
    if (s->voice_fault) {
        if (address) *address = s->voice_fault_address;
        if (s->voice_fault == PITCH_TABLE_FAULT) return "SCSP pitch LFO";
        if (s->voice_fault == AMPLITUDE_TABLE_FAULT) return "SCSP amplitude LFO";
        return "SCSP voice";
    }
    if (!s->DSP.fault) return NULL;
    if(address)*address=s->DSP.fault_address;
    return "Original SCSP DSP";
}
