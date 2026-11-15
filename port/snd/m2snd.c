/* Model 2 sound boards; see m2snd.h and QUIRKS.md ("Sound"). */
#include "m2snd.h"
#ifdef M2_ENABLE_A68K
#include "../a68k/scsp_board.h"
#include "../a68k/model1_board.h"
#include "dsb_board.h"
#include <stdio.h>
#endif
#include "multipcm.h"
#include "scsp.h"
#include "upstream_scsp.h"
#include "ym3438.h"
#include "../m2/m2board.h"
#include "../m68k/m68k.h"
#ifdef M2_CABINET_AUDIO
#include "m2uart.h"
#endif

#include <stdatomic.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define M1_RAM_SIZE  0x10000    /* Model 1 board: 0xf00000-0xf0ffff */
/* ElSemi 004cdaff allocates 1 MiB; 004cd136 maps it linearly for the CPU.
 * User-approved shared board map, independent of the chosen 68000 backend.
 * SCSP sample wrapping is a separate contract: do not enlarge it implicitly. */
#define M2A_RAM_SIZE 0x100000
#define M2A_SAMPLE_MASK 0x7ffff
#define SLICE 16
#define QSIZE 256              /* command queue, a power of two */

static void render_model1(m2_snd *, int16_t *, int);
static void render_upstream_scsp(m2_snd *, int16_t *, int);
static void render_musashi_scsp(m2_snd *, int16_t *, int);
#ifdef M2_ENABLE_A68K
static void render_elsemi_scsp(m2_snd *, int16_t *, int);
static void render_elsemi_model1(m2_snd *, int16_t *, int);
#endif

struct m2_snd {
    void (*render)(m2_snd *, int16_t *, int);
    int type;
    unsigned gain[4];            /* SCSP, MultiPCM 1/2, YM3438; relative percent */
    const uint8_t *prog; uint32_t prog_size;     /* region 5, A68K word-swapped */
    const uint8_t *samples; uint32_t samples_size;   /* region 6 */
    uint8_t *ram; uint32_t ram_size; /* Standalone boards store big-endian bytes. Reconstructed SCSP swaps each word. */
    double cycles_per_sample, cycle_debt;
    unsigned irq_lines;                          /* asserted 68000 levels (bit n = level n) */

    /* Model 1 board */
    uint8_t fifo[32];
    unsigned fifo_rd, fifo_wr;
    multipcm *pcm[2];
    uint32_t pcm_bank[2];
    ym3438 *ym;

    /* Model 2A */
    scsp *scsp;
    upstream_scsp *upstream;
#ifdef M2_ENABLE_A68K
    a68k_scsp_board *a68k;
    a68k_m1_board *m1;
    int m1_block_error;
    m2_dsb_board *dsb;
#endif

    void *ctx;                                   /* this board's Musashi context */
    int32_t mix[SCSP_MIXER_BLOCK * 2];
    unsigned long chip_writes, commands, cmd_reads;

    /* i960 -> sound board: single producer (m2snd_command), single consumer
       (m2snd_render), so the board can run on the audio thread */
    uint8_t q[QSIZE];
    _Atomic unsigned qw, qr;
#ifdef M2_CABINET_AUDIO
    m2_uart *uart;
    unsigned aux_sample_debt,aux_cpu_debt,aux_overshoot;
    void (*reply)(void *,uint8_t);void *reply_user;
#endif
};

static m2_snd *cur;   /* Musashi's callbacks are global */

/* makes s the board Musashi runs (saving the other's context) */
static void enter(m2_snd *s)
{
    if (cur == s)
        return;
    if (cur)
        m68k_get_context(cur->ctx);
    m68k_set_context(s->ctx);
    cur = s;
}

/* ------------------------------------------------------------ helpers */

static void update_irq(m2_snd *s)
{
    int level = 0;
    for (int l = 7; l > 0; l--)
        if (s->irq_lines & (1u << l)) { level = l; break; }
    m68k_set_irq((unsigned)level);
}

static void scsp_irq(void *user, int level, int asserted)
{
    m2_snd *s = user;
#ifdef M2_ENABLE_A68K
    if (s->a68k) {
        a68k_board_irq(s->a68k, level, asserted);
        return;
    }
#endif
    if (asserted) s->irq_lines |= 1u << level;
    else s->irq_lines &= ~(1u << level);
    update_irq(s);
}

/* ROM regions are stored like the original's 68000 core wants them: each
   16-bit word little-endian */
static inline uint8_t rom8(const uint8_t *r, uint32_t size, uint32_t a)
{
    a ^= 1;
    return a < size ? r[a] : 0xff;
}

static uint8_t pcm_read(void *user, uint32_t addr)   /* MultiPCM sample space */
{
    m2_snd *s = cur;
    int chip = user != NULL;   /* chip 0: NULL, chip 1: (void *)1 */
    uint32_t base = chip * 0x400000u, off;
    if (addr < 0x100000)
        off = addr;
    else if (addr < 0x200000)
        off = s->pcm_bank[chip] * 0x100000 + (addr - 0x100000);
    else
        return 0;
    off += base;
    return off < s->samples_size ? s->samples[off] : 0;
}

/* ------------------------------------------------------------ Model 1 board (type 0) */

static uint8_t m1_read8(m2_snd *s, uint32_t a)
{
#ifdef M2_CABINET_AUDIO
    if(s->uart && a>=0x40000 && a<0x80000)return 0xff; /* SM2 auxiliary M1 ROM window. */
    if(s->uart && a>=0xc20000 && a<0xc20004)
        return a&1?m2uart_read(s->uart,(a-0xc20000)>>1):0;
#endif
    if (a < 0x80000)
        return rom8(s->prog, s->prog_size, a);
    if (a >= 0x80000 && a < 0xa0000)
        return rom8(s->prog, s->prog_size, a - 0x60000);
    if (a >= 0xf00000 && a < 0xf10000)
        return s->ram[a - 0xf00000];
    if (a == 0xc20001) {   /* UART data (orig 0x4c6a40): pops the FIFO, IRQ off when empty */
        uint8_t v = 0;
        s->cmd_reads++;
        if (s->fifo_rd != s->fifo_wr) {
            v = s->fifo[s->fifo_rd];
            s->fifo_rd = (s->fifo_rd + 1) & 31;
        }
        if (s->fifo_rd == s->fifo_wr) {
            s->irq_lines &= ~(1u << 2);
            update_irq(s);
        }
        return v;
    }
    if (a >= 0xd00000 && a <= 0xd00007 && (a & 1))
        return ym3438_read(s->ym, (int)((a >> 1) & 3));
    return 0;   /* UART status and MultiPCM status read 0 (as the original) */
}

static void m1_write8(m2_snd *s, uint32_t a, uint8_t v)
{
#ifdef M2_CABINET_AUDIO
    if(s->uart && a>=0xc20000 && a<0xc20004) {
        if(a&1)m2uart_write(s->uart,(a-0xc20000)>>1,v);
        return;
    }
#endif
    if (a >= 0xf00000 && a < 0xf10000) {
        s->ram[a - 0xf00000] = v;
        return;
    }
    if (a >= 0xc40000 && a <= 0xc4000f) {
        if (a & 1)
            multipcm_write(s->pcm[0], (int)((a >> 1) & 3), v), s->chip_writes++;
        return;
    }
    if (a >= 0xc60000 && a <= 0xc6000f) {
        if (a & 1)
            multipcm_write(s->pcm[1], (int)((a >> 1) & 3), v), s->chip_writes++;
        return;
    }
    if (a == 0xc50001) { s->pcm_bank[0] = v & 3; return; }   /* orig: & 7 */
    if (a == 0xc70001) { s->pcm_bank[1] = v & 3; return; }
    if (a >= 0xd00000 && a <= 0xd00007 && (a & 1)) {
        ym3438_write(s->ym, (int)((a >> 1) & 3), v);
        s->chip_writes++;
    }
}

/* ------------------------------------------------------------ Model 2A board (type 1) */

static uint8_t m2a_read8(m2_snd *s, uint32_t a)
{
    if (a < 0x100000)
        return s->ram[(s->upstream ? a : (a ^ 1u)) & (s->ram_size - 1)];
    if (s->upstream && a >= 0x100000 && a < 0x101000) {
        uint16_t word = upstream_scsp_read16(s->upstream, a & 0xffe);
        return (uint8_t)(a & 1 ? word : word >> 8);
    }
    if (!s->upstream && a < 0x110000)
        return scsp_cpu_read8(s->scsp,a);
    if (a >= 0x600000 && a < 0x680000)
        return rom8(s->prog, s->prog_size, a - 0x600000);
    if (a >= 0x800000)
        return rom8(s->samples, s->samples_size, a - 0x800000);
    return 0;
}

static uint16_t m2a_read16(m2_snd *s, uint32_t a)
{
    if (s->upstream && a >= 0x100000 && a < 0x101000)
        return upstream_scsp_read16(s->upstream, a & 0xffe);
    if (!s->upstream && a >= 0x100000 && a < 0x110000)
        return scsp_cpu_read16(s->scsp,a);
    return (uint16_t)(m2a_read8(s, a) << 8 | m2a_read8(s, a + 1));
}

static void m2a_write8(m2_snd *s, uint32_t a, uint8_t v)
{
    if (a < 0x100000)
        s->ram[(s->upstream ? a : (a ^ 1u)) & (s->ram_size - 1)] = v;
    else if (s->upstream && a < 0x101000)
        upstream_scsp_write16(s->upstream, a & 0xffe, a & 1 ? v : (uint16_t)(v << 8), a & 1 ? 0xff : 0xff00);
    else if (s->scsp && a < 0x110000)
        scsp_cpu_store(s->scsp, a, 1, v);
    /* 0x400000: sample bank control, ignored by the original too */
}

static void m2a_write16(m2_snd *s, uint32_t a, uint16_t v)
{
    if (a >= 0x100000 && a < 0x101000) {
        if (s->upstream) upstream_scsp_write16(s->upstream, a & 0xffe, v, 0xffff);
        else scsp_cpu_store(s->scsp, a, 2, v);
        s->chip_writes++;
        return;
    }
    m2a_write8(s, a, (uint8_t)(v >> 8));
    m2a_write8(s, a + 1, (uint8_t)v);
}

/* ------------------------------------------------------------ Musashi callbacks */

unsigned int m68k_read_memory_8(unsigned int a)
{
    a &= 0xffffff;
    return cur->type == 0 ? m1_read8(cur, a) : m2a_read8(cur, a);
}

unsigned int m68k_read_memory_16(unsigned int a)
{
    a &= 0xffffff;
    if (cur->type == 0) {
#ifdef M2_CABINET_AUDIO
        if(cur->uart && a>=0x40000 && a<0x80000)return 0xffff;
#endif
        if (a < 0x80000 || (a >= 0x80000 && a < 0xa0000)) {   /* fast path: ROM */
            uint32_t o = a < 0x80000 ? a : a - 0x60000;
            if (o + 1 < cur->prog_size)
                return (unsigned)(cur->prog[o] | cur->prog[o + 1] << 8);
        }
        if (a >= 0xf00000 && a < 0xf10000)
            return (unsigned)(cur->ram[a - 0xf00000] << 8 | cur->ram[a - 0xf00000 + 1]);
        return (unsigned)(m1_read8(cur, a) << 8 | m1_read8(cur, a + 1));
    }
    if (a < 0x100000) {
        /* Preserve Musashi byte reads, including odd addresses, over the
         * original ElSemi/A68K word-swapped backing allocation. */
        uint32_t o = a & (cur->ram_size - 1);
        if (cur->upstream) return (unsigned)(cur->ram[o] << 8 | cur->ram[o+1]);
        return (unsigned)(cur->ram[o ^ 1u] << 8 | cur->ram[(o+1) ^ 1u]);
    }
    if (a >= 0x600000 && a < 0x680000 && a - 0x600000 + 1 < cur->prog_size)
        return (unsigned)(cur->prog[a - 0x600000] | cur->prog[a - 0x600000 + 1] << 8);
    return m2a_read16(cur, a);
}

unsigned int m68k_read_memory_32(unsigned int a)
{
    a &= 0xffffff;
    /* Native SCSP long callback 004ab220 is OR EAX,-1 / RET. It does not
     * perform two word reads or their MIDI/global-register side effects. */
    if(cur->scsp && a>=0x100000 && a<0x110000)return 0xffffffffu;
    return m68k_read_memory_16(a) << 16 | m68k_read_memory_16(a + 2);
}

void m68k_write_memory_8(unsigned int a, unsigned int v)
{
    a &= 0xffffff;
    if (cur->type == 0) m1_write8(cur, a, (uint8_t)v);
    else m2a_write8(cur, a, (uint8_t)v);
}

void m68k_write_memory_16(unsigned int a, unsigned int v)
{
    a &= 0xffffff;
    if (cur->type == 0) {
        m1_write8(cur, a, (uint8_t)(v >> 8));
        m1_write8(cur, a + 1, (uint8_t)v);
    } else {
        m2a_write16(cur, a, (uint16_t)v);
    }
}

void m68k_write_memory_32(unsigned int a, unsigned int v)
{
    a &= 0xffffff;
    if (cur->scsp && a >= 0x100000 && a < 0x110000) {
        scsp_cpu_store(cur->scsp, a, 4, v);
        if (a < 0x100600 || (a >= 0x100700 && a < 0x101000)) cur->chip_writes += 2;
        return;
    }
    m68k_write_memory_16(a, v >> 16);
    m68k_write_memory_16(a + 2, v & 0xffff);
}

/* ElSemi clears the accepted SCSP request before its live autovector callback. */
static int int_ack(int level) {
    (void)level;
    if(cur && cur->scsp) {
        scsp_cpu_ack_irq(cur->scsp);
    }
    return M68K_INT_ACK_AUTOVECTOR;
}

unsigned int m68k_read_disassembler_16(unsigned int a) { return m68k_read_memory_16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a) { return m68k_read_memory_32(a); }

/* ------------------------------------------------------------ interface */

static scsp *create_scsp(m2_snd *s, const m2_board *b)
{
    scsp *chip = scsp_create(s->ram, M2A_RAM_SIZE, M2A_SAMPLE_MASK, scsp_irq, s);
    if (chip && b->game)
        scsp_set_interleaved_mixer(chip, b->game->hook == M2_HOOK_UNKNOWN &&
                                         b->game->hook_addr == 0x4c6710);
    return chip;
}

static m2_snd *create_board(const m2_board *b, int upstream, int original_board, int original_divs)
{
    m2_snd *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    for (unsigned i = 0; i < 4; i++) s->gain[i] = 100;
    s->type = b->type == 0 ? 0 : 1;
    s->prog = b->rom.ptr[5];
    s->prog_size = b->rom.size[5];
    s->samples = b->rom.ptr[6];
    s->samples_size = b->rom.size[6];
    s->ram_size = s->type == 0 ? M1_RAM_SIZE : (upstream ? 0x80000 : M2A_RAM_SIZE);
    s->ram = calloc(1, s->ram_size + 2);
#ifdef M2_ENABLE_A68K
    if (original_board) {
        if (!s->ram || !s->prog) goto failed;
        if (s->type == 0) {
            s->m1 = a68k_m1_create(s->ram, s->prog, s->prog_size, s->samples,
                                   s->samples_size, original_divs);
            if (!s->m1) goto failed;
            s->render = render_elsemi_model1;
            a68k_m1_reset(s->m1);
        } else {
            s->scsp = create_scsp(s, b);
            if (!s->scsp || !m2snd_enable_a68k(s, original_divs)) goto failed;
            if (b->rom.option[1]) {
                s->dsb = m2_dsb_board_create(b->rom.option[1], b->rom.ptr[7], b->rom.size[7],
                                             b->rom.ptr[8], b->rom.size[8]);
                if (!s->dsb) goto failed;
            }
        }
        return s;
    }
#else
    (void)original_board; (void)original_divs;
#endif
    s->ctx = calloc(1, m68k_context_size());
    if (!s->ram || !s->prog || !s->ctx) goto failed;
    if (cur)   /* keep the running board's CPU */
        m68k_get_context(cur->ctx);
    cur = s;
    if (s->type == 0) {
        s->render = render_model1;
        s->cycles_per_sample = 10000000.0 / M2SND_RATE;
        s->pcm[0] = multipcm_create(M2SND_RATE, pcm_read, NULL);
        s->pcm[1] = multipcm_create(M2SND_RATE, pcm_read, (void *)1);
        s->ym = ym3438_create(8000000, M2SND_RATE);
        if (!s->pcm[0] || !s->pcm[1] || !s->ym) goto failed;
    } else {
        s->render = upstream ? render_upstream_scsp : render_musashi_scsp;
        s->cycles_per_sample = 11289600.0 / M2SND_RATE;
        if (upstream)
            s->upstream = upstream_scsp_create(s->ram, s->ram_size - 1, scsp_irq, s);
        else
            s->scsp = create_scsp(s, b);
        if (!s->scsp && !s->upstream) goto failed;
    }
    m68k_init();
    m68k_set_cpu_type(M68K_CPU_TYPE_68000);
    m68k_set_int_ack_callback(int_ack);
    m2snd_reset(s);
    m68k_get_context(s->ctx);
    return s;
failed:
    m2snd_destroy(s);
    return NULL;
}

m2_snd *m2snd_create(const m2_board *b)
{
    return create_board(b,0,0,0);
}

m2_snd *m2snd_create_subsystem(const m2_board *b,int upstream,int original_divs)
{
    return create_board(b, upstream, !upstream, original_divs);
}

void m2snd_destroy(m2_snd *s)
{
    if (!s)
        return;
    if (s->pcm[0]) multipcm_destroy(s->pcm[0]);
    if (s->pcm[1]) multipcm_destroy(s->pcm[1]);
    if (s->ym) ym3438_destroy(s->ym);
#ifdef M2_ENABLE_A68K
    a68k_m1_free(s->m1);
    free(s->dsb);
    free(s->a68k);
#endif
    if (s->upstream) upstream_scsp_destroy(s->upstream);
    if (s->scsp) scsp_destroy(s->scsp);
#ifdef M2_CABINET_AUDIO
    if(s->uart)m2uart_destroy(s->uart);
#endif
    free(s->ram);
    free(s->ctx);
    if (cur == s)
        cur = NULL;
    free(s);
}

void m2snd_reset(m2_snd *s)
{
#ifdef M2_ENABLE_A68K
    if (s->m1) { a68k_m1_reset(s->m1); return; }
    if (s->a68k) {
        a68k_board_reset(s->a68k);
        return;
    }
#endif
    enter(s);
    memset(s->ram, 0, s->ram_size);
    s->fifo_rd = s->fifo_wr = 0;
    atomic_store(&s->qr, atomic_load(&s->qw));   /* drop pending commands */
    s->irq_lines = 0;
    s->pcm_bank[0] = s->pcm_bank[1] = 0;
    s->cycle_debt = 0;
#ifdef M2_CABINET_AUDIO
    s->aux_sample_debt=s->aux_cpu_debt=s->aux_overshoot=0;
    if(s->uart)m2uart_reset(s->uart);
#endif
    if (s->type == 0) {
        multipcm_reset(s->pcm[0]);
        multipcm_reset(s->pcm[1]);
        ym3438_reset(s->ym);
    } else {
        if (s->upstream) upstream_scsp_reset(s->upstream);
        else scsp_reset(s->scsp);
        /* the vector table is copied from the program ROM into RAM */
        for (uint32_t i = 0; i < 16; i++)
            s->ram[s->upstream ? i : (i ^ 1u)] = rom8(s->prog, s->prog_size, i);
    }
    m68k_pulse_reset();
    m68k_set_irq(0);
}

static void deliver(m2_snd *s, uint8_t cmd)
{
    s->commands++;
    if (s->type == 0) {
#ifdef M2_CABINET_AUDIO
        if(s->uart) { m2uart_receive(s->uart,cmd);return; }
#endif
        unsigned next = (s->fifo_wr + 1) & 31;
        if (next != s->fifo_rd) {   /* the original overwrites; a full FIFO drops here */
            s->fifo[s->fifo_wr] = cmd;
            s->fifo_wr = next;
        }
        s->irq_lines |= 1u << 2;
        update_irq(s);
    } else {
#ifdef M2_ENABLE_A68K
        if(s->a68k) a68k_board_trace_command(s->a68k,cmd);
#endif
        if (s->upstream) upstream_scsp_midi_in(s->upstream, cmd);
        else scsp_midi_in(s->scsp, cmd);
    }
}

void m2snd_command(m2_snd *s, uint8_t cmd)
{
#ifdef M2_ENABLE_A68K
    if (s->m1) {
        s->commands++;
        a68k_m1_command(s->m1,cmd);
        return;
    }
    /* 004c868a writes the MIDI ring inside the i960 port callback. This CPU
     * and its scanline service run serially in the core. Even if more than
     * 256 bytes arrive in one slice, every write advances the native FIFO. */
    if (s->a68k) {
        deliver(s, cmd);
        if (s->dsb) m2_dsb_board_command(s->dsb, cmd);
        return;
    }
#endif
    unsigned w = atomic_load_explicit(&s->qw, memory_order_relaxed);
    if (w - atomic_load_explicit(&s->qr, memory_order_acquire) >= QSIZE)
        return;   /* the sound board is far behind: drop */
    s->q[w & (QSIZE - 1)] = cmd;
    atomic_store_explicit(&s->qw, w + 1, memory_order_release);
}

static void drain(m2_snd *s)
{
    unsigned r = atomic_load_explicit(&s->qr, memory_order_relaxed);
    unsigned w = atomic_load_explicit(&s->qw, memory_order_acquire);
    if (r == w)
        return;
    for (; r != w; r++)
        deliver(s, s->q[r & (QSIZE - 1)]);
    atomic_store_explicit(&s->qr, r, memory_order_release);
}

#ifdef M2_ENABLE_A68K
int m2snd_enable_a68k(m2_snd *s, int original_divs)
{
    if (!s->scsp || s->a68k) return 0;
    scsp_original_power_on(s->scsp);
    memset(s->ram, 0, s->ram_size);
    s->a68k = a68k_board_create(s->ram, s->scsp, s->prog, s->prog_size,
                                s->samples, s->samples_size, original_divs);
    if (s->a68k) s->render = render_elsemi_scsp;
    return s->a68k != NULL;
}

void m2snd_scanline(m2_snd *s, unsigned hz)
{
    if (s->m1) { a68k_m1_scanline(s->m1); return; }
    if (!s->a68k) return;
    drain(s);
    a68k_board_scanline(s->a68k, hz);
}

int m2snd_has_a68k(const m2_snd *s) { return s && (s->a68k || s->m1); }

void m2snd_prepare_audio_frame(m2_snd *s,unsigned frames)
{
    if (s->m1 && !a68k_m1_begin(s->m1,frames)) s->m1_block_error=1;
}

static void render_elsemi_model1(m2_snd *s,int16_t *out,int n)
{
    if (!a68k_m1_output_frames(s->m1,(unsigned)n)) {
        s->m1_block_error=1;
        memset(out,0,(size_t)n*2*sizeof *out);
        return;
    }
    a68k_m1_finish(s->m1,out,s->gain);
}

int m2snd_a68k_error(m2_snd *s, char *text, size_t size)
{
    if (s->m1_block_error) {
        snprintf(text,size,"Inconsistent Model 1 audio frame length");
        return 1;
    }
    if (s->m1) return a68k_m1_error(s->m1,text,size);
    return s->a68k && a68k_board_error(s->a68k, text, size);
}

int m2snd_dsb_error(m2_snd *s, char *text, size_t size)
{
    if (!s->a68k || !s->dsb) return 0;
    uint32_t offset;
    const char *error = m2_dsb_board_error(s->dsb,&offset);
    if (!error) return 0;
    snprintf(text,size,"DSB at compressed offset 0x%08x: %s",offset,error);
    return 1;
}
#endif

void m2snd_set_gains(m2_snd *s, unsigned scsp_gain, unsigned pcm1_gain,
                       unsigned pcm2_gain, unsigned fm_gain)
{
    if (!s) return;
    const unsigned values[] = {scsp_gain, pcm1_gain, pcm2_gain, fm_gain};
    for (unsigned i = 0; i < 4; i++) s->gain[i] = values[i] > 100 ? 100 : values[i];
}

static void run_musashi_audio_slice(m2_snd *s, int n)
{
    drain(s);
    s->cycle_debt += s->cycles_per_sample * n;
    int run = (int)s->cycle_debt;
    s->cycle_debt -= m68k_execute(run);
}

static void publish_pcm(const int32_t *mix, int16_t *out, int n, unsigned gain)
{
    for (int i = 0; i < 2*n; i++) {
        int32_t v = mix[i];
        if (gain != 100) v = (int32_t)((int64_t)v * gain / 100);
        out[i] = (int16_t)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
    }
}

static void render_model1(m2_snd *s, int16_t *out, int n)
{
    enter(s);
    while (n > 0) {
        int k = n < SLICE ? n : SLICE;
        run_musashi_audio_slice(s, k);
        memset(s->mix, 0, sizeof(int32_t) * (size_t)k * 2);
        if (s->gain[1] == 100 && s->gain[2] == 100) {
            multipcm_render(s->pcm[0], s->mix, k);
            multipcm_render(s->pcm[1], s->mix, k);
            for (int i = 0; i < k * 2; i++)
                s->mix[i] /= 2;   /* Native MAME mix: 0.5 per MultiPCM */
        } else {
            int32_t pcm1[SLICE * 2] = {0}, pcm2[SLICE * 2] = {0};
            multipcm_render(s->pcm[0], pcm1, k);
            multipcm_render(s->pcm[1], pcm2, k);
            for (int i = 0; i < k * 2; i++)
                s->mix[i] = (int32_t)(((int64_t)pcm1[i] * s->gain[1]
                                     + (int64_t)pcm2[i] * s->gain[2]) / 200);
        }
        ym3438_render(s->ym, s->mix, k, s->gain[3] == 100 ? 0.30f : 0.30f * (float)s->gain[3] / 100.0f);
        publish_pcm(s->mix, out, k, 100);
        out += k*2;
        n -= k;
    }
}

static void render_upstream_scsp(m2_snd *s, int16_t *out, int n)
{
    enter(s);
    while (n > 0) {
        int k = n < SLICE ? n : SLICE;
        run_musashi_audio_slice(s, k);
        upstream_scsp_render(s->upstream, s->mix, k);
        publish_pcm(s->mix, out, k, s->gain[0]);
        out += k*2;
        n -= k;
    }
}

/* Used by standalone and component probes that pair Musashi with the
 * reconstructed chip. Streamed PCM observes register writes every sample. */
static void render_musashi_scsp(m2_snd *s, int16_t *out, int n)
{
    enter(s);
    while (n > 0) {
        if (m2snd_fault(s,NULL)) { memset(out,0,(size_t)n*2*sizeof *out); return; }
        run_musashi_audio_slice(s, 1);
        scsp_render(s->scsp, s->mix, 1);
        publish_pcm(s->mix, out, 1, s->gain[0]);
        out += 2;
        n--;
    }
}

#ifdef M2_ENABLE_A68K
static void render_elsemi_scsp(m2_snd *s, int16_t *out, int n)
{
    /* The scanline service owns the CPU and timers. The mixer receives
     * the complete board block, including voices that stop within it. */
    while (n > 0) {
        if (m2snd_fault(s,NULL)) { memset(out,0,(size_t)n*2*sizeof *out); return; }
        int k = n < SCSP_MIXER_BLOCK ? n : SCSP_MIXER_BLOCK;
        scsp_render_clocked(s->scsp, s->mix, k);
        publish_pcm(s->mix, out, k, s->gain[0]);
        if (s->dsb) m2_dsb_board_mix(s->dsb, out, (size_t)k);
        out += k*2;
        n -= k;
    }
}
#endif

void m2snd_render(m2_snd *s, int16_t *out, int n)
{
    s->render(s, out, n);
}

#include <stdio.h>
void m2snd_debug(m2_snd *s, char *buf, int size)
{
#ifdef M2_ENABLE_A68K
    if (s->m1) {
        snprintf(buf,(size_t)size,"A68K Model 1 | cmds %lu",s->commands);
        return;
    }
    if (s->a68k) {
        int mvol;
        int voices = scsp_slots_active(s->scsp,&mvol);
        snprintf(buf,(size_t)size,"A68K pc %06x | cmds %lu | voices %d mvol %d",
                 a68k_board_pc(s->a68k),s->commands,voices,mvol);
        return;
    }
#endif
    enter(s);
    int a = 0, b = 0, mvol = 0;
    if (s->type == 0) {
        a = multipcm_voices_playing(s->pcm[0]);
        b = multipcm_voices_playing(s->pcm[1]);
    } else {
        a = s->upstream ? upstream_scsp_slots_active(s->upstream, &mvol) : scsp_slots_active(s->scsp, &mvol);
    }
    snprintf(buf, (size_t)size, "68k pc %06x sr %04x irq %02x | cmds %lu, cmd reads %lu, chip writes %lu | voices %d %d mvol %d",
             m68k_get_reg(NULL, M68K_REG_PC), m68k_get_reg(NULL, M68K_REG_SR), s->irq_lines,
             s->commands, s->cmd_reads, s->chip_writes, a, b, mvol);
}


/* Caller must quiesce command production and rendering. Native queued commands
 * are machine state; frontend sample buffers and current gain options are not. */
void m2snd_state_archive(m2_snd *s, m2_state *a)
{
#ifdef M2_ENABLE_A68K
    if (s->m1) {
        if (s->m1_block_error) a->failed=1;
        m2_state_bytes(a,s->ram,s->ram_size);
        a68k_m1_archive(s->m1,a);
        return;
    }
    if (!s->a68k)
#endif
    {
        enter(s);
        m68k_get_context(s->ctx);
    }
#define F(m) do { m2_state_value(a,&values.m,sizeof values.m); if(a->mode==M2_STATE_LOAD && !a->failed)memcpy(&s->m,&values.m,sizeof values.m); } while(0)
    m2_snd values=*s;
    m2_state_bytes(a,s->ram,s->ram_size);
    F(cycle_debt); F(irq_lines); F(fifo); F(fifo_rd); F(fifo_wr); F(pcm_bank);
    F(chip_writes); F(commands); F(cmd_reads); F(q);
    unsigned w=atomic_load(&s->qw), r=atomic_load(&s->qr);
    m2_state_value(a,&w,sizeof w); m2_state_value(a,&r,sizeof r);
    if(w-r>QSIZE)a->failed=1;
    if(a->mode==M2_STATE_LOAD && !a->failed) { atomic_store(&s->qw,w);atomic_store(&s->qr,r); }
    if(!isfinite(values.cycle_debt) || fabs(values.cycle_debt)>1000000.0
        || values.fifo_rd>=32 || values.fifo_wr>=32 || values.pcm_bank[0]>3 || values.pcm_bank[1]>3
        || values.irq_lines>255)a->failed=1;
#ifdef M2_ENABLE_A68K
    if (s->a68k) a68k_board_archive(s->a68k, a);
    else
#endif
        m68k_state_archive(s->ctx,a);
    if(s->type==0) {
        multipcm_state_archive(s->pcm[0],a); multipcm_state_archive(s->pcm[1],a);
        ym3438_state_archive(s->ym,a);
    } else if (s->upstream) upstream_scsp_state_archive(s->upstream,a);
    else scsp_state_archive(s->scsp,a);
#ifdef M2_ENABLE_A68K
    if (s->a68k && s->dsb) m2_dsb_board_archive(s->dsb,a);
    if (!s->a68k)
#endif
        if(a->mode==M2_STATE_LOAD && !a->failed)m68k_set_context(s->ctx);
#undef F
}

#ifdef M2_CABINET_AUDIO
/* Native Model 1 chips/context are reused, with SM2's dedicated M1 clock,
 * I8251 protocol and audio-before-CPU ordering for the additional board only.
 * Adapted from SM2 hw/m1audio.cpp, Copyright (c) 2025+ Daniel Martin
 * (dmanlfc), GPL-3.0-or-later AND BSD-3-Clause with additional terms;
 * see src/libretro/sm2/LICENSE.sm2 and NOTICE.sm2. */
static void aux_ready(void *user,int tx,int ready) {
    m2_snd *s=user;
    (void)tx;
    if(ready)s->irq_lines|=1u<<2;else s->irq_lines&=~(1u<<2);
    update_irq(s);
}
static void aux_reply(void *user,uint8_t value) {
    m2_snd *s=user;if(s->reply)s->reply(s->reply_user,value);
}
void m2snd_set_reply(m2_snd *s,void (*reply)(void *,uint8_t),void *user) {
    s->reply=reply;s->reply_user=user;
    if (s->upstream) upstream_scsp_set_midi_reply(s->upstream,reply,user);
    else if(s->scsp)scsp_set_midi_reply(s->scsp,reply,user);
}
void m2snd_midi_state_archive(m2_snd *s,m2_state *a) {
    if (s->upstream) upstream_scsp_midi_state_archive(s->upstream,a);
    else if(s->scsp)scsp_midi_state_archive(s->scsp,a);
}
void m2snd_reset_midi(m2_snd *s) { if (s->upstream) upstream_scsp_reset_midi(s->upstream); else if(s->scsp)scsp_reset_midi(s->scsp); }
void m2snd_bind_roms(m2_snd *s,const uint8_t *program,uint32_t program_size,
                   const uint8_t *samples,uint32_t samples_size) {
    s->prog=program;s->prog_size=program_size;s->samples=samples;s->samples_size=samples_size;
#ifdef M2_ENABLE_A68K
    if(s->a68k) a68k_board_roms(s->a68k,program,program_size,samples,samples_size);
#endif
}
void m2snd_set_roms(m2_snd *s,const uint8_t *program,uint32_t program_size,
                   const uint8_t *samples,uint32_t samples_size) {
    m2snd_bind_roms(s,program,program_size,samples,samples_size);
    m2snd_reset(s);
}
m2_snd *m2snd_create_aux(const uint8_t *program,uint32_t program_size,
                       const uint8_t *samples,uint32_t samples_size) {
    m2_board view={0};view.rom.ptr[5]=(uint8_t *)program;view.rom.size[5]=program_size;
    view.rom.ptr[6]=(uint8_t *)samples;view.rom.size[6]=samples_size;
    m2_snd *s=m2snd_create(&view);if(!s)return NULL;
    s->uart=m2uart_create(10000000,aux_ready,aux_reply,s);
    if(!s->uart) { m2snd_destroy(s);return NULL; }
    multipcm_destroy(s->pcm[0]);multipcm_destroy(s->pcm[1]);ym3438_destroy(s->ym);
    s->pcm[0]=multipcm_create(10000000.0f/224.0f,pcm_read,NULL);
    s->pcm[1]=multipcm_create(10000000.0f/224.0f,pcm_read,(void *)1);
    s->ym=ym3438_create(8000000,10000000/224);
    if(!s->pcm[0] || !s->pcm[1] || !s->ym) { m2snd_destroy(s);return NULL; }
    m2snd_reset(s);return s;
}
unsigned m2snd_run_aux(m2_snd *s,unsigned host_cycles,int16_t *out) {
    if(!s || !s->uart || host_cycles>4000)return 0;
    enter(s);drain(s);
    s->aux_sample_debt+=host_cycles;unsigned frames=s->aux_sample_debt/560;
    s->aux_sample_debt%=560;
    if(frames) {
        memset(s->mix,0,frames*2*sizeof *s->mix);
        int32_t p1[SLICE*2]={0},p2[SLICE*2]={0};
        multipcm_render(s->pcm[0],p1,(int)frames);multipcm_render(s->pcm[1],p2,(int)frames);
        for(unsigned i=0;i<frames*2;i++)s->mix[i]=(int32_t)(((int64_t)p1[i]*s->gain[1]+(int64_t)p2[i]*s->gain[2])/200);
        ym3438_render(s->ym,s->mix,(int)frames,0.30f*(float)s->gain[3]/100.0f);
        for(unsigned i=0;i<frames*2;i++)out[i]=(int16_t)(s->mix[i]>32767?32767:s->mix[i]<-32768?-32768:s->mix[i]);
    }
    /* SM2's I8251 is counted in M1 CPU cycles at 10 MHz. */
    m2uart_run(s->uart,(unsigned)((uint64_t)host_cycles*2/5));
    s->aux_cpu_debt+=host_cycles*2;unsigned owed=s->aux_cpu_debt/5;s->aux_cpu_debt%=5;
    if(owed<=s->aux_overshoot)s->aux_overshoot-=owed;
    else { owed-=s->aux_overshoot;s->aux_overshoot=0;int used=m68k_execute((int)owed);if(used>(int)owed)s->aux_overshoot=(unsigned)used-owed; }
    return frames;
}
void m2snd_aux_state_archive(m2_snd *s,m2_state *a) {
    m2snd_state_archive(s,a);m2uart_state_archive(s->uart,a);
    unsigned sample=s->aux_sample_debt,cpu=s->aux_cpu_debt,over=s->aux_overshoot;
    m2_state_value(a,&sample,sizeof sample);m2_state_value(a,&cpu,sizeof cpu);m2_state_value(a,&over,sizeof over);
    if(sample>=560 || cpu>=5 || over>1000000)a->failed=1;
    if(a->mode==M2_STATE_LOAD && !a->failed) { s->aux_sample_debt=sample;s->aux_cpu_debt=cpu;s->aux_overshoot=over; }
}
#endif

int m2snd_is_upstream(const m2_snd *s)
{
    return s && (s->type == 0 ? s->ym != NULL : s->upstream != NULL);
}

const char *m2snd_fault(const m2_snd *s,uint32_t *address) {
    return s ? scsp_fault(s->scsp,address) : NULL;
}
void m2snd_set_dsp_backend(m2_snd *s,unsigned backend) {
    if(s && s->scsp)scsp_set_dsp_backend(s->scsp,backend);
}
unsigned m2snd_get_dsp_backend(const m2_snd *s) {
    if (s && s->upstream) return SCSP_DSP_MAME;
    return s && s->scsp?scsp_get_dsp_backend(s->scsp):SCSP_DSP_ORIGINAL;
}
