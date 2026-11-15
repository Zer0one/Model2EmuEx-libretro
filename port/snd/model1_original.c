/* Primary Model 1-style board in Model 2 Emulator 1.1a. The extra Manx TT
 * cabinet board has a different serial link and clock. */
#include "model1_original.h"
#include "fm_original.h"
#include "multipcm_original.h"
#include <stdlib.h>
#include <string.h>

enum { MAX_BLOCK=1024 };
struct m2_original_m1 {
    m2_original_fm *fm;
    m2_original_mpcm *pcm[2];
    uint8_t fifo[32], rd, wr;
    unsigned frames, cursor;
    int16_t stereo[2*MAX_BLOCK];
};

void m2_original_m1_free(m2_original_m1 *b)
{
    if (!b) return;
    m2_original_fm_free(b->fm);
    free(b->pcm[0]); free(b->pcm[1]);
    free(b);
}

m2_original_m1 *m2_original_m1_create(const uint8_t *samples,size_t size)
{
    m2_original_m1 *b=calloc(1,sizeof *b);
    if (!b) return NULL;
    b->fm=m2_original_fm_create();
    for (unsigned i=0;i<2;i++) b->pcm[i]=m2_original_mpcm_create(i,samples,size);
    if (!b->fm || !b->pcm[0] || !b->pcm[1]) {
        m2_original_m1_free(b);
        return NULL;
    }
    return b;
}

int m2_original_m1_begin(m2_original_m1 *b,unsigned frames)
{
    if (!frames || frames>MAX_BLOCK || b->cursor || b->frames) return 0;
    b->frames=frames;
    return 1;
}

void m2_original_m1_command(m2_original_m1 *b,uint8_t value)
{
    b->fifo[b->wr]=value;
    b->wr=(b->wr+1)&31;
}

void m2_original_m1_cursors(const m2_original_m1 *b,uint8_t cursors[2])
{
    cursors[0]=b->rd; cursors[1]=b->wr;
}

int m2_original_m1_irq_pending(const m2_original_m1 *b) { return b->rd!=b->wr; }

static void flush(void *user)
{
    m2_original_m1 *b=user;
    if (b->frames-b->cursor<10) return;
    m2_original_fm_render(b->fm,b->stereo+2*b->cursor,10);
    b->cursor+=10;
}

uint32_t m2_original_m1_tick(m2_original_m1 *b) { return m2_original_fm_tick(b->fm,flush,b); }

uint32_t m2_original_m1_read(m2_original_m1 *b,uint32_t address,unsigned width,uint32_t *irq)
{
    unsigned page=address>>16;
    uint32_t value=0;
    for (unsigned i=0;i<width;i++) {
        unsigned at=address+i;
        unsigned byte=0xff;
        if (page==0xc2) {
            byte=0;
            if ((at&65535)==1) {
                if (b->rd!=b->wr) {
                    byte=b->fifo[b->rd];
                    b->rd=(b->rd+1)&31;
                }
                if (b->rd==b->wr) *irq=0;
            }
        } else if (page>=0xc4 && page<=0xc7) byte=0;
        else if (page==0xd0) byte=at==0xd00001 ? m2_original_fm_status(b->fm) : 0;
        value=(value<<8)|byte;
    }
    return value;
}

m2_m1_completion m2_original_m1_pcm_store(m2_original_m1 *b,unsigned chip,uint32_t a,
                     unsigned width,uint32_t value,uint32_t sp,uint32_t flags)
{
    static const uint32_t entries[2][3]={{0x4cbab0,0x4cc5a0,0x4cc650},
                                         {0x4cba80,0x4cc530,0x4cc630}};
    uint32_t base=0xc40000+chip*0x20000;
    m2_m1_completion out={entries[chip][width==4 ? 2 : width-1],flags};
    for (unsigned i=0;i<width;i++) {
        unsigned at=a+i;
        uint8_t byte=value>>(8*(width-i-1));
        if (at==base+0x10001) {
            m2_original_mpcm_bank(b->pcm[chip],byte);
            if (width==1) out.eax=byte&7;
            out.flags=m1_logic_flags(out.flags,byte&7,32);
        } else if (at-base<=15) {
            uint32_t entry_sp=sp;
            /* A long calls its first word helper and tail-calls its second.
             * The word helper calls for the high byte, tail-calls for low. */
            if (width==4 && i<2) entry_sp-=12;
            if (width!=1 && !(i&1)) entry_sp-=12;
            out=m2_original_mpcm_write_observed(b->pcm[chip],(at>>1)&15,byte,
                                                entry_sp,out.flags);
        } else out.flags=m1_sub_flags(out.flags,at,base+15,32);
    }
    return out;
}

m2_m1_completion m2_original_m1_fm_store(m2_original_m1 *b,uint32_t a,unsigned width,
                                          uint32_t value,uint32_t flags)
{
    m2_m1_completion out={0,flags};
    for (unsigned i=0;i<width;i++) {
        unsigned port=((a+i)>>1)&3;
        uint8_t byte=value>>(8*(width-i-1));
        if (m2_original_fm_write_flush(b->fm,port)) flush(b);
        out=m2_original_fm_store(b->fm,port,byte,out.flags);
    }
    return out;
}

void m2_original_m1_write(m2_original_m1 *b,uint32_t address,unsigned width,uint32_t value)
{
    unsigned page=address>>16;
    if (page>=0xc4 && page<=0xc7)
        (void)m2_original_m1_pcm_store(b,(page-0xc4)>>1,address,width,value,0,0);
    else if (page==0xd0) (void)m2_original_m1_fm_store(b,address,width,value,0);
}

/* RetroArch can clear fractional sample debt on reset. A partly rendered
 * block can still finish at the new length if all committed samples fit. */
int m2_original_m1_output_frames(m2_original_m1 *b,unsigned frames)
{
    if (!frames || frames>MAX_BLOCK || b->cursor>frames) return 0;
    b->frames=frames;
    return 1;
}

void m2_original_m1_finish(m2_original_m1 *b,int16_t *out,unsigned pcm1,
                           unsigned pcm2,unsigned fm)
{
    m2_original_fm_render(b->fm,b->stereo+2*b->cursor,b->frames-b->cursor);
    if (fm==100) memcpy(out,b->stereo,2*b->frames*sizeof *out);
    else for (unsigned i=0;i<2*b->frames;i++) out[i]=(int)b->stereo[i]*(int)fm/100;
    m2_original_mpcm_mix(b->pcm[0],out,b->frames,pcm1);
    m2_original_mpcm_mix(b->pcm[1],out,b->frames,pcm2);
    b->cursor=b->frames=0;
}

const char *m2_original_m1_error(const m2_original_m1 *b)
{
    const char *error=m2_original_mpcm_error(b->pcm[0]);
    return error ? error : m2_original_mpcm_error(b->pcm[1]);
}

void m2_original_m1_archive(m2_original_m1 *b,m2_state *a)
{
    uint32_t tag=0x3141314d; /* M1A1 */
    uint32_t frames=b->frames, cursor=b->cursor;
    uint8_t rd=b->rd,wr=b->wr;
    m2_state_value(a,&tag,sizeof tag);
    if (tag!=0x3141314d) a->failed=1;
    m2_state_value(a,&frames,sizeof frames);
    m2_state_value(a,&cursor,sizeof cursor);
    m2_state_value(a,&rd,sizeof rd);
    m2_state_value(a,&wr,sizeof wr);
    if (frames>MAX_BLOCK || cursor>frames || cursor%10 || rd>31 || wr>31) a->failed=1;
    m2_state_bytes(a,b->fifo,sizeof b->fifo);
    m2_state_bytes(a,b->stereo,sizeof b->stereo);
    m2_original_fm_archive(b->fm,a);
    for (unsigned i=0;i<2;i++) m2_original_mpcm_archive(b->pcm[i],a);
    if (!a->failed && a->mode==M2_STATE_LOAD) {
        b->rd=rd; b->wr=wr; b->frames=frames; b->cursor=cursor;
    }
}
