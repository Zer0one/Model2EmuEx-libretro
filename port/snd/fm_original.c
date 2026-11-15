/* Model 2 Emulator 1.1a YM2612, 004b0b30..004b28df. The operator and rate
 * names follow Tatsuyuki Satoh's historical FM implementation. The tables,
 * signed phase division, rounding and register behavior follow the executable. */
#include "fm_original.h"
#include <stdlib.h>
#include <string.h>
#include "fm_original_tables.inc"

enum fm_stage { ATTACK, DECAY, SUSTAIN, RELEASE };
enum { FM_OFF=0x1fffffff, FM_DECAY_START=0x10000000 };

typedef struct {
    uint32_t phase, increment, counter, limit, speed, rates[4], sustain_level;
    uint16_t total_level, latched_level;
    uint8_t detune, multiplier, key_shift, key_scale, rate_index[4];
    uint8_t stage, amplitude_enabled, segment;
} fm_operator;

typedef struct {
    fm_operator op[4];
    uint32_t feedback[2], frequency;
    uint16_t pms, ams;
    uint8_t pan, algorithm, feedback_shift, high, key, dirty;
} fm_channel;

struct m2_original_fm {
    fm_channel channels[6];
    uint32_t special_frequency[3], lfo_phase, lfo_step, dac;
    uint8_t special_high[3], special_key[3], latch[2], dac_enabled;
    uint8_t mode, status, timer_b;
    uint16_t timer_a;
    uint32_t timer_count[2], timer_period[2];
};

static const uint8_t operator_order[4]={0,2,1,3};
static const uint8_t key_codes[16]={0,0,0,0,0,0,0,1,2,3,3,3,3,3,3,3};

static uint32_t rate_value(const fm_operator *op, unsigned stage)
{
    unsigned index=op->rate_index[stage];
    if (!index && stage!=RELEASE) return 0;
    return (stage==ATTACK ? fm_attack : fm_decay)[index+op->key_scale];
}

static void refresh(fm_operator *op, unsigned frequency, unsigned key)
{
    op->increment=(frequency+fm_detune[op->detune*32+key])*op->multiplier;
    unsigned scale=key>>op->key_shift;
    if (scale==op->key_scale) return;
    op->key_scale=scale;
    for (unsigned i=0;i<4;i++) op->rates[i]=rate_value(op,i);
    /* 004b0c80 updates the four cached rates. The active slope is latched. */
}

static void refresh_channels(m2_original_fm *f)
{
    static const unsigned special[3]={1,0,2};
    for (unsigned c=0;c<6;c++) {
        fm_channel *ch=&f->channels[c];
        if (!ch->dirty) continue;
        for (unsigned i=0;i<4;i++) {
            if (c==2 && (f->mode&0xc0) && i<3)
                refresh(&ch->op[i],f->special_frequency[special[i]],f->special_key[special[i]]);
            else refresh(&ch->op[i],ch->frequency,ch->key);
        }
        ch->dirty=0;
    }
}

static unsigned attenuation(uint32_t counter)
{
    unsigned index=counter>>16;
    return index<4096 ? fm_attack_curve[index] : index-4096;
}

static void key(fm_operator *op, unsigned on)
{
    if (on && op->stage==RELEASE) {
        op->phase=op->counter=0;
        op->stage=ATTACK;
        op->limit=FM_DECAY_START;
        op->speed=op->rates[ATTACK];
    } else if (!on && op->stage!=RELEASE) {
        if (op->counter<FM_DECAY_START) op->counter=(4096+attenuation(op->counter))<<16;
        op->stage=RELEASE;
        op->limit=FM_OFF;
        op->speed=op->rates[RELEASE];
    }
}

static void update_rate(fm_operator *op, unsigned stage, unsigned index)
{
    op->rate_index[stage]=index;
    op->rates[stage]=rate_value(op,stage);
    if (op->stage==stage) op->speed=op->rates[stage];
}

static void frequency(uint8_t high,uint8_t low,uint32_t *result,uint8_t *key_code)
{
    unsigned n=(high&7)*256+low, octave=high>>3;
    *result=(uint32_t)fm_frequency[n]>>(7-octave);
    *key_code=4*octave+key_codes[n>>7];
}

static void channel_write(m2_original_fm *f, unsigned bank, unsigned reg, uint8_t v)
{
    unsigned id=reg&3;
    if (id==3) return;
    unsigned group=(reg>>2)&3;
    fm_channel *ch=&f->channels[id+3*bank];
    fm_operator *op=&ch->op[group];
    switch (reg>>4) {
    case 3:
        op->detune=(v>>4)&7;
        op->multiplier=(v&15) ? 2*(v&15) : 1;
        ch->dirty=1;
        break;
    case 4:
        op->total_level=((v&127)*129)>>2;
        if (id+3*bank!=2 || !(f->mode&128)) op->latched_level=op->total_level;
        break;
    case 5:
        op->key_shift=3-(v>>6);
        update_rate(op,ATTACK,2*(v&31));
        ch->dirty=1;
        break;
    case 6:
        update_rate(op,DECAY,2*(v&31));
        op->amplitude_enabled=v>>7;
        break;
    case 7: update_rate(op,SUSTAIN,2*(v&31)); break;
    case 8:
        op->sustain_level=fm_sustain_levels[v>>4];
        update_rate(op,RELEASE,4*(v&15)+2);
        break;
    case 9: op->segment=v&15; break;
    case 10:
        switch (group) {
        case 0: frequency(ch->high,v,&ch->frequency,&ch->key); ch->dirty=1; break;
        case 1: ch->high=v&63; break;
        case 2:
            if (!bank) {
                frequency(f->special_high[id],v,&f->special_frequency[id],&f->special_key[id]);
                f->channels[2].dirty=1;
            }
            break;
        case 3: if (!bank) f->special_high[id]=v&63; break;
        }
        break;
    case 11:
        if (!group) {
            ch->algorithm=v&7;
            unsigned fb=(v>>3)&7;
            ch->feedback_shift=fb ? 9-fb : 0;
        } else if (group==1) {
            ch->pan=v>>6;
            ch->ams=fm_ams[(v>>4)&3];
            ch->pms=fm_pms[v&7];
        }
        break;
    }
}

static uint32_t period(const m2_original_fm *f,unsigned timer)
{
    return 144u*(timer ? 16u*(256u-f->timer_b) : 1024u-f->timer_a);
}

static void mode_write(m2_original_fm *f,uint8_t v)
{
    f->mode=v;
    f->status&=~((v>>4)&3);
    for (unsigned i=0;i<2;i++) {
        if (!(v&(1u<<i))) f->timer_period[i]=0;
        else if (!f->timer_period[i]) f->timer_period[i]=period(f,i);
    }
}

void m2_original_fm_write(m2_original_fm *f, unsigned port, uint8_t v)
{
    unsigned bank=(port>>1)&1;
    if (!(port&1)) { f->latch[bank]=v; return; }
    unsigned reg=f->latch[bank];
    if (bank || (reg>>4)!=2) { channel_write(f,bank,reg,v); return; }
    switch (reg) {
    case 0x22: f->lfo_step=(v&8) ? fm_lfo_steps[v&7] : 0; break;
    case 0x24: f->timer_a=(f->timer_a&3)|(v<<2); break;
    case 0x25: f->timer_a=(f->timer_a&1020)|(v&3); break;
    case 0x26: f->timer_b=v; break;
    case 0x27: mode_write(f,v); break;
    case 0x28:
        if ((v&3)!=3) {
            fm_channel *ch=&f->channels[(v&3)+((v&4)?3:0)];
            for (unsigned i=0;i<4;i++) key(&ch->op[operator_order[i]],v&(16u<<i));
        }
        break;
    case 0x2a: f->dac=(uint32_t)((int)v-128)*0x80000u; break;
    case 0x2b: f->dac_enabled=(v>>7); break;
    }
}

/* Last native flag-setting instruction before each write returns to A68K.
 * The older FM source describes the chip state but does not expose these
 * incidental caller-visible x86 results. */
static uint32_t store_flags(m2_original_fm *f,unsigned port,uint8_t v,uint32_t flags)
{
    static const uint32_t stages[4]={0x4b1e60,0x4b1ae0,0x4b11e0,0x4b1200};
    port&=3;
    if (!(port&1)) return m1_sub_flags(flags,port,3,32);
    unsigned bank=port>>1, reg=f->latch[bank], id=reg&3, group=(reg>>2)&3;
    if (!bank && reg>>4==2) {
        switch (reg) {
        case 0x22: return m1_logic_flags(flags,(v&8) ? v&7 : 0,32);
        case 0x24: return m1_logic_flags(flags,(f->timer_a&3)|(v<<2),32);
        case 0x25: return m1_logic_flags(flags,(f->timer_a&1020)|(v&3),32);
        case 0x26: case 0x23: return m1_sub_flags(flags,reg-0x22,6,32);
        case 0x27: {
            if (!(v&1) || f->timer_period[0])
                return m1_logic_flags(flags,(v&1) ? f->timer_period[0]/144 : 0,32);
            return m1_logic_flags(flags,0xc7f,32);
        }
        case 0x28: {
            if ((v&3)==3) return m1_sub_flags(flags,3,3,8);
            fm_operator *op=&f->channels[(v&3)+((v&4)?3:0)].op[3];
            uint32_t cmp=m1_sub_flags(flags,stages[op->stage],stages[RELEASE],32);
            if ((v&128) || op->stage==RELEASE) return cmp;
            if (op->counter>=FM_DECAY_START)
                return m1_sub_flags(flags,op->counter,FM_DECAY_START,32);
            return m1_logic_flags(flags,(4096+attenuation(op->counter))<<16,32);
        }
        case 0x2a: return m1_logic_flags(flags,(uint32_t)((int)v-128)<<19,32) |
                           (v<128 ? 1u : 0u);
        case 0x2b: return m1_logic_flags(flags,v&128,32);
        default: return m1_sub_flags(flags,reg-0x22,6,32);
        }
    }
    if (id==3) return m1_logic_flags(flags,0,8);
    fm_channel *ch=&f->channels[id+bank*3];
    fm_operator *op=&ch->op[group];
    switch (reg>>4) {
    case 3: return m1_logic_flags(flags,(v&0x70)<<3,32);
    case 4: return m1_sub_flags(flags,(!bank && id==2 && (f->mode&128)) ? 1 : 0,0,32);
    case 5: return m1_sub_flags(flags,stages[op->stage],stages[ATTACK],32);
    case 6: return m1_logic_flags(flags,(v>>7)*ch->ams,32);
    case 7: return m1_sub_flags(flags,stages[op->stage],stages[SUSTAIN],32);
    case 8: return m1_sub_flags(flags,stages[op->stage],stages[RELEASE],32);
    case 9: return m1_logic_flags(flags,v&15,8);
    case 10: {
        if (group>=2 && bank) return m1_sub_flags(flags,256+reg,256,32);
        if (group&1) return m1_logic_flags(flags,v&63,8);
        unsigned high=group==0 ? ch->high : f->special_high[id];
        unsigned shift=7-(high>>3);
        if (!shift) return m1_logic_flags(flags,0,32);
        uint32_t freq=fm_frequency[(high&7)*256+v];
        return m1_logic_flags(flags,freq>>shift,32)|((freq>>(shift-1))&1)|
               ((freq>>31)<<11);
    }
    case 11:
        if (group<=1) return m1_sub_flags(flags,group ? ch->algorithm : v&7,7,32);
        return m1_sub_flags(flags,group,1,32);
    default: return m1_sub_flags(flags,(reg&0xf0)-0x30u,0x80,32);
    }
}

m2_m1_completion m2_original_fm_store(m2_original_fm *f,unsigned port,uint8_t v,uint32_t flags)
{
    flags=store_flags(f,port,v,flags);
    m2_original_fm_write(f,port,v);
    return (m2_m1_completion){f->status!=0,flags};
}

int m2_original_fm_write_flush(const m2_original_fm *f,unsigned port)
{
    return (port&1) && ((port&2) || f->latch[0]!=0x2b);
}

uint32_t m2_original_fm_tick(m2_original_fm *f, void (*flush)(void *), void *user)
{
    uint32_t eax=f->timer_period[1];
    for (unsigned timer=0;timer<2;timer++) {
        f->timer_count[timer]+=67;
        if (!f->timer_period[timer] || f->timer_count[timer]<f->timer_period[timer])
            continue;
        if (!timer && flush) flush(user);
        if (f->mode&(4u<<timer)) f->status|=1u<<timer;
        uint32_t next=period(f,timer);
        if (timer) {
            /* 004a9c98 compares the old integer period with the intermediate
             * BEFORE truncation. At TB=250 both integer periods are 13824,
             * but the new x87 value is 13824.0009765625, so EAX is 13824.
             * At equality FNSTSW replaces AX in the 8 MHz clock value.
             * Its low exception bits are unobservable on this board: the
             * only A68K consumer (Scc memory) overwrites AL before the bus. */
            float ticks=(float)(16u*(256u-f->timer_b))*(float)(144.0/8000000.0);
            float clocks=ticks*8000000.0f;
            eax=clocks==(float)f->timer_period[timer] ? 0x007a7804u : next;
        }
        f->timer_period[timer]=next;
        if (!timer && (f->mode&128)) {
            for (unsigned j=0;j<4;j++) {
                fm_operator *op=&f->channels[2].op[j];
                op->latched_level=op->total_level;
                key(op,1);
            }
        }
        f->timer_count[timer]=0;
    }
    return eax;
}

unsigned m2_original_fm_status(const m2_original_fm *f) { return f->status; }

static unsigned envelope(fm_operator *op)
{
    op->counter+=op->speed;
    if ((int32_t)op->counter>=(int32_t)op->limit) {
        switch (op->stage) {
        case ATTACK:
            op->stage=DECAY;
            op->counter=FM_DECAY_START;
            op->limit=op->sustain_level;
            op->speed=op->rates[DECAY];
            break;
        case DECAY:
            op->stage=SUSTAIN;
            op->counter=op->sustain_level;
            op->limit=FM_OFF;
            op->speed=op->rates[SUSTAIN];
            break;
        default: op->counter=FM_OFF; op->limit=FM_OFF+1; op->speed=0; break;
        }
    }
    return op->latched_level+attenuation(op->counter);
}

static int32_t wave(uint32_t phase,unsigned envelope_level)
{
    unsigned p=((int32_t)phase/8192)&2047;
    unsigned quadrant=p&1023;
    if (quadrant>512) quadrant=1024-quadrant;
    unsigned index=fm_sine_offsets[quadrant]+envelope_level;
    if (index>=0xd00) return 0;
    return (p&1024) ? -fm_levels[index] : fm_levels[index];
}

static uint32_t channel_sample(fm_channel *ch,int32_t pitch,unsigned amp)
{
    /* Route each operator result to the next phase or the channel output
     * in the original 004b1090 order. Value 5 fans out to operators 2–4. */
    static const uint8_t route[8][3] = {
        {1,2,3},{2,2,3},{3,2,3},{1,3,3},
        {1,4,3},{5,4,4},{1,4,4},{4,4,4}
    };
    uint32_t signals[5]={0};
    unsigned levels[4];
    int pms=(int32_t)((uint32_t)pitch*ch->pms)/65536;
    for (unsigned i=0;i<4;i++) {
        fm_operator *op=&ch->op[operator_order[i]];
        int extra=(int32_t)(op->increment*(uint32_t)pms)/1024;
        op->phase+=op->increment+(uint32_t)extra;
        signals[i]=op->phase;
        levels[i]=envelope(op);
        if (op->amplitude_enabled) levels[i]+=(ch->ams*amp)>>16;
    }
    for (unsigned i=0;i<4;i++) {
        if (levels[i]>=0xb55) continue;
        if (!i && ch->feedback_shift) {
            signals[0]+=(int32_t)(ch->feedback[0]+ch->feedback[1])>>ch->feedback_shift;
            ch->feedback[1]=ch->feedback[0];
        }
        uint32_t result=(uint32_t)wave(signals[i],levels[i]);
        if (!i) ch->feedback[0]=result;
        unsigned dest=i==3 ? 4 : route[ch->algorithm][i];
        if (dest==5) {
            signals[1]+=result; signals[2]+=result; signals[3]+=result;
        } else signals[dest]+=result;
    }
    return signals[4];
}

static int16_t output(uint32_t value)
{
    int32_t v=(int32_t)value;
    if (v>0xfffffff) v=0xfffffff;
    if (v< -0x10000000) v= -0x10000000;
    return (int16_t)(v>>13);
}

void m2_original_fm_render(m2_original_fm *f,int16_t *stereo,size_t frames)
{
    refresh_channels(f);
    for (size_t n=0;n<frames;n++) {
        unsigned amp=0;
        int pitch=0;
        if (f->lfo_step) {
            f->lfo_phase+=f->lfo_step;
            unsigned p=f->lfo_phase>>23;
            amp=(p<=255 ? p : 512-p)*256;
            pitch=(int)amp-32768;
        }
        uint32_t bus[4]={0};
        for (unsigned c=0;c<6;c++) {
            fm_channel *ch=&f->channels[c];
            bus[ch->pan]+=c==5 && f->dac_enabled ? f->dac : channel_sample(ch,pitch,amp);
        }
        stereo[2*n]=output(bus[2]+bus[3]);
        stereo[2*n+1]=output(bus[1]+bus[3]);
    }
}

void m2_original_fm_reset(m2_original_fm *f)
{
    memset(f,0,sizeof *f);
    for (unsigned c=0;c<6;c++) {
        fm_channel *ch=&f->channels[c];
        ch->pan=3;
        for (unsigned i=0;i<4;i++) {
            fm_operator *op=&ch->op[i];
            op->stage=RELEASE;
            op->counter=FM_OFF;
            op->limit=FM_OFF+1;
        }
    }
    for (int reg=0xb2;reg>=0x30;--reg)
        for (unsigned bank=0;bank<2;bank++) channel_write(f,bank,reg,0);
}

m2_original_fm *m2_original_fm_create(void)
{
    m2_original_fm *f=malloc(sizeof *f);
    if (f) m2_original_fm_reset(f);
    return f;
}

void m2_original_fm_free(m2_original_fm *f) { free(f); }

void m2_original_fm_archive(m2_original_fm *f,m2_state *a)
{
    m2_original_fm saved=*f;
    m2_state_value(a,&saved,sizeof saved);
    if (saved.timer_a>1023) a->failed=1;
    for (unsigned i=0;i<3;i++)
        if (saved.special_high[i]>63 || saved.special_key[i]>31) a->failed=1;
    for (unsigned c=0;c<6;c++) {
        const fm_channel *ch=&saved.channels[c];
        if (ch->algorithm>7 || ch->pan>3 || ch->high>63 || ch->key>31 ||
            ch->feedback_shift>8) a->failed=1;
        for (unsigned i=0;i<4;i++) {
            const fm_operator *op=&ch->op[i];
            if (op->detune>7 || op->stage>RELEASE || op->key_shift>3 || op->key_scale>31 ||
                op->rate_index[ATTACK]>62 || op->rate_index[DECAY]>62 ||
                op->rate_index[SUSTAIN]>62 || op->rate_index[RELEASE]>62) a->failed=1;
        }
    }
    if (!a->failed && a->mode==M2_STATE_LOAD) *f=saved;
}
