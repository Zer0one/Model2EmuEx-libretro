/* Model 2 Emulator 1.1a MultiPCM. See 004b01b0 (setup), 004b0700
 * (slot registers), 004afed0 (envelope) and 004affb0 (mix). */
#include "multipcm_original.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include "multipcm_original_tables.inc"

typedef struct {
    uint32_t start, loop, end;
    uint8_t attack, decay1, decay2, level, release, key_scale, pitch_lfo, amp_lfo;
} sample_descriptor;

typedef struct {
    uint16_t phase, reserved;
    uint32_t step, wave, scale;
} native_lfo;

typedef struct {
    uint8_t index, regs[8], active, pad[2];
    uint32_t descriptor, start, offset, step, pan, total, target, ramp;
    int32_t previous, volume;
    uint32_t envelope, reserved, attack, decay1, decay2, release, level;
    native_lfo pitch, amplitude;
} native_slot;

typedef struct {
    sample_descriptor samples[512];
    native_slot slots[28];
    int32_t selected;
    uint32_t reg, bank, rom_address;
} chip_image;

_Static_assert(sizeof(sample_descriptor)==20 && sizeof(native_slot)==0x70, "MultiPCM layout");
_Static_assert(offsetof(chip_image,slots)==0x2800 && sizeof(chip_image)==0x3450, "MultiPCM layout");

struct m2_original_mpcm {
    chip_image image;
    uint32_t address;
    const uint8_t *rom;
    size_t rom_size;
    unsigned chip;
    const char *error;
};

static uint32_t be16(const uint8_t *p) { return ((uint32_t)p[0]<<8) | p[1]; }

m2_original_mpcm *m2_original_mpcm_create(unsigned chip, const uint8_t *rom, size_t size)
{
    size_t base = (size_t)chip * 0x400000;
    if (chip > 1 || !rom || size < base+512*12) return NULL;
    m2_original_mpcm *m = calloc(1,sizeof *m);
    if (!m) return NULL;
    m->address = 0x1087020 + chip*0x3450;
    m->rom = rom;
    m->rom_size = size;
    m->chip = chip;
    m->image.rom_address = 0x76000000 + (uint32_t)base;
    for (unsigned i=0; i<512; i++) {
        const uint8_t *p = rom+base+12*i;
        m->image.samples[i] = (sample_descriptor){
            ((uint32_t)p[0]<<16) | be16(p+1), be16(p+3), 65535-be16(p+5),
            p[8]>>4,p[8]&15,p[9]&15,p[9]>>4,p[10]&15,p[10]>>4,p[7],p[11]
        };
    }
    for (unsigned i=0; i<28; i++) m->image.slots[i].index = i;
    return m;
}

static const sample_descriptor *descriptor(m2_original_mpcm *m, uint32_t address)
{
    uint32_t at = address-m->address;
    if (at >= sizeof m->image.samples || at%sizeof(sample_descriptor)) {
        m->error = "MultiPCM descriptor outside sample table";
        return NULL;
    }
    return &m->image.samples[at/sizeof(sample_descriptor)];
}

static uint32_t rate(const int32_t *table, unsigned value, int key)
{
    int n = value ? (value == 15 ? 63 : 4*(int)value+key) : 0;
    return (uint32_t)table[12+(n>63 ? 63 : n)];
}

static void key_on(m2_original_mpcm *m, native_slot *s)
{
    uint8_t id = s->regs[1];
    const sample_descriptor *d = &m->image.samples[id];
    s->descriptor = m->address + (uint32_t)id*sizeof *d;
    s->active = 1;
    s->start = d->start;
    if (s->start >= 0x100000) s->start = (m->image.bank<<20) | (s->start & 0xfffff);
    s->offset = 0;
    s->previous = 0;
    s->total = s->target<<12;
    int octave = ((s->regs[3]>>4)-1)&15;
    if (octave&8) octave -= 16;
    int key = d->key_scale == 15 ? 0 : 2*(octave+d->key_scale)+((s->regs[3]>>3)&1);
    if (d->attack>15 || d->decay1>15 || d->decay2>15 || d->release>15 ||
        d->key_scale>15 || d->level>15) {
        m->error = "MultiPCM modified descriptor outside rate tables";
        return;
    }
    s->attack = rate(attack_rate,d->attack,key);
    s->decay1 = rate(decay_rate,d->decay1,key);
    s->decay2 = rate(decay_rate,d->decay2,key);
    s->release = rate(decay_rate,d->release,key);
    s->level = 15-d->level;
    s->envelope = s->volume = 0;
}

static void set_lfo(native_slot *s)
{
    static const unsigned steps[8] = {0,3,4,6,7,8,9,10}; /* 004afc50, 44100 Hz */
    s->pitch.step = s->amplitude.step = steps[(s->regs[6]>>3)&7];
    s->pitch.wave = 0x1095dd8;
    s->pitch.scale = 0x108d8c0+((s->regs[6]&7)<<10);
    s->amplitude.wave = 0x108f8c0;
    s->amplitude.scale = 0x1093dd8+((s->regs[7]&7)<<10);
}

static void write_reg(m2_original_mpcm *m, native_slot *s, unsigned reg, uint8_t value)
{
    s->regs[reg] = value;
    switch (reg) {
    case 0: s->pan = value>>4; break;
    case 1: {
        const sample_descriptor *d = &m->image.samples[value];
        s->regs[6] = d->pitch_lfo;
        if (s->regs[6]) set_lfo(s);
        s->regs[7] = d->amp_lfo;
        if (s->regs[7]) set_lfo(s);
        break;
    }
    case 2: case 3: {
        unsigned oct = ((s->regs[3]>>4)-1)&15;
        uint32_t f = (uint32_t)frequency[((s->regs[3]&15)<<6) | (s->regs[2]>>2)];
        s->step = (oct&8 ? f>>(16-oct) : f<<oct) / 44100;
        break;
    }
    case 4:
        if (value&128) key_on(m,s);
        else if (s->active) {
            const sample_descriptor *d = descriptor(m,s->descriptor);
            if (!d) break;
            if (d->release==15) s->active = 0;
            else s->envelope = 3;
        }
        break;
    case 5:
        s->target = value>>1;
        if (value&1) s->total = s->target<<12;
        else s->ramp = (s->total>>12)>s->target ? (uint32_t)-150 : 75;
        break;
    case 6: case 7: if (value) set_lfo(s); break;
    }
}

void m2_original_mpcm_bank(m2_original_mpcm *m, unsigned value) { m->image.bank = value&7; }

static m2_m1_completion slot_write(m2_original_mpcm *m,native_slot *s,unsigned reg,
                                   uint8_t v,uint32_t sp,uint32_t flags)
{
    /* 004b0700 loads AL, retaining the chip pointer's upper three bytes. */
    uint32_t eax=(m->address&~255u)|v;
    uint32_t old_total=s->total;
    int active=s->active;
    write_reg(m,s,reg,v);
    switch (reg) {
    case 0: flags=m1_logic_flags(flags,v>>4,32)|((v>>3)&1); break;
    case 1: {
        const sample_descriptor *d=&m->image.samples[v];
        uint32_t intermediate=d->pitch_lfo ? s->pitch.step : (v*5u&~255u);
        eax=(intermediate&~255u)|d->amp_lfo;
        if (!d->amp_lfo) { flags=m1_logic_flags(flags,0,8); break; }
        eax=s->amplitude.step;
        flags=m1_stack_flags(flags,sp-36,12);
        break;
    }
    case 2: case 3: eax=s->step; flags=m1_logic_flags(flags,0,32); break;
    case 4:
        if (v&128) {
            uint32_t start=m->image.samples[s->regs[1]].start;
            eax=start;
            if (start<0x100000) flags=m1_sub_flags(flags,start,0x100000,32);
            else { eax=start&0xfffff; flags=m1_logic_flags(flags,s->start,32); }
        } else if (active) {
            eax=s->descriptor;
            const sample_descriptor *d=descriptor(m,eax);
            flags=m1_sub_flags(flags,d ? d->release : 0,15,8);
        } else flags=m1_logic_flags(flags,0,8);
        break;
    case 5:
        if (v&1) flags=m1_logic_flags(flags,s->total,32);
        else {
            flags=m1_sub_flags(flags,old_total>>12,s->target,32);
            if ((old_total>>12)>s->target) eax=(uint32_t)-150;
        }
        break;
    case 6: case 7:
        if (v) { eax=s->amplitude.step; flags=m1_stack_flags(flags,sp-36,12); }
        else flags=m1_logic_flags(flags,0,8);
        break;
    }
    return (m2_m1_completion){eax,flags};
}

m2_m1_completion m2_original_mpcm_write_observed(m2_original_mpcm *m,unsigned port,
                                                  uint8_t v,uint32_t sp,uint32_t flags)
{
    m2_m1_completion out={m->address,flags};
    if (m->error) return out;
    if (port==1) {
        unsigned i=v&31;
        m->image.selected=(i&7)==7 ? -1 : (int)(i-i/8);
        out.flags=m1_logic_flags(flags,i,32);
    } else if (port==2) {
        m->image.reg=v<8 ? v : 7;
        out.flags=m1_sub_flags(flags,v,7,8);
    } else if (port==0 && m->image.selected>=0) {
        out=slot_write(m,&m->image.slots[m->image.selected],m->image.reg,v,sp,flags);
    } else if (port==0) {
        native_slot alias;
        unsigned char *at=(unsigned char *)&m->image+offsetof(chip_image,slots)-sizeof alias;
        memcpy(&alias,at,sizeof alias);
        out=slot_write(m,&alias,m->image.reg,v,sp,flags);
        memcpy(at,&alias,sizeof alias);
    } else out.flags=m1_sub_flags(flags,port-1,1,32)&~1u;
    return out;
}

void m2_original_mpcm_write(m2_original_mpcm *m,unsigned port,uint8_t value)
{
    (void)m2_original_mpcm_write_observed(m,port,value,0,0);
}

/* 004afed0 sign-extends the upper word before indexing the envelope curve.
 * Negative rates from key scaling can carry the lookup into adjacent data. */
static int32_t envelope_lookup(m2_original_mpcm *m, int index, size_t frames)
{
    if ((unsigned)index < 1024) return envelope_gain[index];
    if (index == -1) return 75;
    if (index == -2) return -150;
    /* Original left and right output addresses in the repeatable board map. */
    if (index == 1024) return 0x74205068;
    if (index == 1025) return 0x74230178;
    if (index == 1026) return (int32_t)frames;
    if (index == 1027) return 44100;
    static const struct {
        uint32_t address;
        const int32_t *words;
        size_t count;
    } tables[] = {
        {0x108d8c0, pitch_gain, 2048}, {0x108f8c0, amp_wave, 256},
        {0x108fcc0, attack_rate+12, 64}, {0x108fdc0, left_pan, 2048},
        {0x1092dd8, frequency, 1024}, {0x1093dd8, amp_gain, 2048},
        {0x1095dd8, pitch_wave, 256}, {0x10961d8, decay_rate+12, 64},
        {0x10962d8, right_pan, 2048}
    };
    uint32_t address = 0x1091dc8 + (uint32_t)index*4;
    for (unsigned i=0; i<sizeof tables/sizeof tables[0]; ++i) {
        uint32_t word = (address-tables[i].address)/4;
        if (word < tables[i].count) return tables[i].words[word];
    }
    m->error = "MultiPCM envelope outside mapped synthesis tables";
    return 0;
}

static int32_t envelope(m2_original_mpcm *m, native_slot *s, size_t frames)
{
    switch (s->envelope) {
    case 0:
        s->volume = (int32_t)((uint32_t)s->volume+s->attack);
        if (s->volume >= 0x3ff0000) {
            s->volume = 0x3ff0000;
            s->envelope = (int32_t)s->decay1 >= 0x4000000 ? 2 : 1;
        }
        break;
    case 1: case 2: case 3: {
        uint32_t decay = s->envelope==1 ? s->decay1 : s->envelope==2 ? s->decay2 : s->release;
        s->volume = (int32_t)((uint32_t)s->volume-decay);
        if (s->volume<=0) {
            s->volume = 0;
            if (s->envelope==3) s->active = 0;
        }
        if (s->envelope==1 && (uint32_t)(s->volume>>16)<=s->level*64) s->envelope=2;
        break;
    }
    default: return 4096;
    }
    return envelope_lookup(m,s->volume>>16,frames);
}

static int32_t voice(m2_original_mpcm *m, native_slot *s, size_t frames)
{
    const sample_descriptor *d = descriptor(m,s->descriptor);
    uint32_t index=s->offset>>12, weight=s->offset&4095;
    size_t at=(size_t)m->chip*0x400000+s->start+index;
    if (!d || at>=m->rom_size) {
        if (d) m->error = "MultiPCM sample outside shared ROM";
        return 0;
    }
    int current = (int8_t)m->rom[at]*256;
    int sample = ((4096-(int)weight)*s->previous+(int)weight*current)>>12;
    uint32_t step=s->step;
    if (s->regs[6]&7) {
        s->pitch.phase += (uint16_t)s->pitch.step;
        int wave=pitch_wave[s->pitch.phase>>8];
        step = (step*(uint32_t)(pitch_gain[(s->regs[6]&7)*256+128+wave]*16))>>12;
    }
    s->offset += step;
    if (s->offset >= (d->end<<12)) s->offset=d->loop<<12;
    if ((s->offset>>12)!=index) s->previous=current;
    if ((s->total>>12)!=s->target) s->total += s->ramp;
    if (s->regs[7]&7) {
        s->amplitude.phase += (uint16_t)s->amplitude.step;
        int wave=amp_wave[s->amplitude.phase>>8];
        sample = (sample*(amp_gain[(s->regs[7]&7)*256+wave]*16))>>12;
    }
    return (int32_t)((uint32_t)envelope(m,s,frames)*(uint32_t)sample)>>12;
}

static int16_t clip(int64_t v) { return v>32767 ? 32767 : v<-32768 ? -32768 : (int16_t)v; }

void m2_original_mpcm_mix(m2_original_mpcm *m, int16_t *stereo, size_t frames, unsigned gain)
{
    for (size_t i=0; i<frames && !m->error; ++i) {
        int32_t left=0,right=0;
        for (unsigned j=0; j<28; ++j) {
            native_slot *s=&m->image.slots[j];
            if (!s->active) continue;
            unsigned pan=(s->pan<<7)|(s->total>>12);
            if (pan>=2048) { m->error="MultiPCM level outside pan table"; return; }
            int value=voice(m,s,frames);
            if (m->error) return;
            left += (int32_t)((uint32_t)left_pan[pan]*(uint32_t)value)>>12;
            right += (int32_t)((uint32_t)right_pan[pan]*(uint32_t)value)>>12;
        }
        stereo[2*i]=clip(stereo[2*i]+(int64_t)left*gain/100);
        stereo[2*i+1]=clip(stereo[2*i+1]+(int64_t)right*gain/100);
    }
}

const char *m2_original_mpcm_error(const m2_original_mpcm *m) { return m->error; }

void m2_original_mpcm_archive(m2_original_mpcm *m, m2_state *a)
{
    /* The selector value -1 aliases one slot immediately before slots[0].
     * All earlier decoded descriptors are immutable and rebuilt from the ROM. */
    const size_t mutable_offset = offsetof(chip_image, slots) - sizeof(native_slot);
    chip_image image=m->image;
    m2_state_value(a,(unsigned char *)&image+mutable_offset,sizeof image-mutable_offset);
    if (m->error || image.selected < -1 || image.selected>=28 || image.reg>7 || image.bank>7 ||
        image.rom_address != m->image.rom_address) a->failed=1;
    for (unsigned i=0; i<28; i++) {
        const native_slot *s=&image.slots[i];
        if (s->active>1 || s->pan>15 || s->target>127 || s->total>>12>127 ||
            s->previous < -32768 || s->previous > 32767 ||
            s->envelope>3 || s->level>15 ||
            (s->active && (s->descriptor<m->address || s->descriptor-m->address>=512*20 ||
                           (s->descriptor-m->address)%20))) a->failed=1;
    }
    if (!a->failed && a->mode==M2_STATE_LOAD) m->image=image;
}
