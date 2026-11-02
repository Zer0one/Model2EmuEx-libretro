/* ROM-free fixtures through the actual adapter option readers/native mixer.
 * Including the adapter avoids exporting a diagnostic core ABI. */
#include "../src/libretro/libretro.c"
#include <assert.h>
#include <math.h>

extern void m68k_write_memory_8(unsigned, unsigned);
extern void m68k_write_memory_16(unsigned, unsigned);
#define GAIN_FRAMES 4096
#define GAIN_STATE_BYTES (2u * 1024u * 1024u)
static uint8_t tone_program[0x200];
static uint8_t *tone_samples;
static bool tone_auxiliary;
static const char *selected_gain[4];
static const char *gain_keys[] = {"model2emuex_scsp_gain", "model2emuex_multipcm1_gain",
    "model2emuex_multipcm2_gain", "model2emuex_ym3438_gain"};
static bool gain_environment(unsigned command, void *data)
{
    if (command != RETRO_ENVIRONMENT_GET_VARIABLE) return false;
    struct retro_variable *v = data;
    for (unsigned i=0;i<4;i++) if (!strcmp(v->key,gain_keys[i])) {
        v->value=selected_gain[i];return v->value!=NULL;
    }
    return false;
}
static void tone_word(unsigned offset,uint16_t value)
{
    tone_program[offset]=(uint8_t)value;tone_program[offset+1]=(uint8_t)(value>>8);
}
static void pcm_register(unsigned chip,unsigned reg,unsigned value)
{
    unsigned base=chip?0xc60000:0xc40000;
    m68k_write_memory_8(base+3,0);
    m68k_write_memory_8(base+5,reg);m68k_write_memory_8(base+1,value);
}
static void fm_register(unsigned reg,unsigned value)
{
    m68k_write_memory_8(0xd00001,reg);m68k_write_memory_8(0xd00003,value);
}
static void start_tones(unsigned sources)
{
    int16_t scratch[2];m2snd_render(sound,scratch,0);
    if(sources&1) {
        for(unsigned i=0;i<256;i++)m68k_write_memory_16(0x4000+i*2,(uint16_t)(int16_t)(((int)(i&63)-32)*64));
        m68k_write_memory_16(0x100400,0xf);
        m68k_write_memory_16(0x100002,0x4000);m68k_write_memory_16(0x100006,256);
        m68k_write_memory_16(0x100008,0x1f);m68k_write_memory_16(0x100016,0xe000);
        m68k_write_memory_16(0x100000,0x1820);
    }
    for(unsigned chip=0;chip<2;chip++)if(sources&(2u<<chip)) {
        pcm_register(chip,0,chip?0x90:0x70); // Distinct left/right sources.
        pcm_register(chip,1,0);pcm_register(chip,2,0);pcm_register(chip,3,0x10);
        pcm_register(chip,5,1);pcm_register(chip,4,0x80);
    }
    if(sources&8) {
        // Channel 0: four carriers, low output level, stereo, stable envelope.
        for(unsigned slot=0;slot<4;slot++) {
            unsigned offset=slot*4;
            fm_register(0x30+offset,1);fm_register(0x40+offset,0x30);
            fm_register(0x50+offset,0x1f);fm_register(0x60+offset,0);
            fm_register(0x70+offset,0);fm_register(0x80+offset,0xf);
        }
        fm_register(0xb0,7);fm_register(0xb4,0xc0);
        fm_register(0xa4,0x22);fm_register(0xa0,0x69);fm_register(0x28,0xf0);
    }
}
static void create_tones(unsigned sources)
{
    assert(!sound);
    memset(tone_program,0,sizeof tone_program);
    tone_word(0,sources&1?7:0xf0);tone_word(2,0xff00);
    tone_word(4,sources&1?0x60:0);tone_word(6,0x100);tone_word(0x100,0x60fe);
    m2_board *b=calloc(1,sizeof *b);assert(b);
    b->type=sources&1?1:0;
    b->rom.ptr[5]=tone_program;b->rom.size[5]=sizeof tone_program;
    b->rom.ptr[6]=tone_samples;b->rom.size[6]=0x400000+0x1000;
    sound=tone_auxiliary?m2snd_create_aux(tone_program,sizeof tone_program,tone_samples,0x400000+0x1000):m2snd_create(b);
    free(b);assert(sound);
    start_tones(sources);
}
static void destroy_tones(void) { m2snd_destroy(sound);sound=NULL; }
static void render_tones(int16_t *pcm,unsigned frames)
{
    if(tone_auxiliary) {
        for(unsigned i=0;i<frames;i++)assert(m2snd_run_aux(sound,560,pcm+i*2)==1);
    } else m2snd_render(sound,pcm,(int)frames);
}
static size_t native_state(uint8_t *bytes)
{
    m2_state a={bytes,GAIN_STATE_BYTES,0,M2_STATE_SAVE,0};
    if(tone_auxiliary)m2snd_aux_state_archive(sound,&a);else m2snd_state_archive(sound,&a);
    assert(!a.failed);return a.pos;
}
static void restore_native_state(uint8_t *bytes,size_t used)
{
    m2_state a={bytes,used,0,M2_STATE_LOAD,0};
    if(tone_auxiliary)m2snd_aux_state_archive(sound,&a);else m2snd_state_archive(sound,&a);
    assert(!a.failed && a.pos==used);
}
static void capture(unsigned sources,int16_t *pcm,uint8_t *state,size_t *used)
{
    create_tones(sources);read_options();render_tones(pcm,GAIN_FRAMES);
    if(state)*used=native_state(state);
    destroy_tones();
}
static bool nonzero(const int16_t *pcm)
{
    for(unsigned i=0;i<GAIN_FRAMES*2;i++)if(pcm[i])return true;
    return false;
}
int main(void)
{
    int16_t native[GAIN_FRAMES*2],actual[GAIN_FRAMES*2];
    uint8_t *baseline_state=malloc(GAIN_STATE_BYTES),*actual_state=malloc(GAIN_STATE_BYTES);
    uint8_t *initial_state=malloc(GAIN_STATE_BYTES);
    tone_samples=calloc(1,0x400000+0x1000);assert(baseline_state && actual_state && initial_state && tone_samples);
    for(unsigned chip=0;chip<2;chip++) {
        uint8_t *rom=tone_samples+chip*0x400000;
        rom[1]=1;rom[5]=0xff;rom[8]=0xf0;
        for(unsigned i=0;i<256;i++)rom[0x100+i]=(uint8_t)((int)(i&(chip?31:63))-(chip?16:32));
    }
    env=gain_environment;
    const char *choices[]={NULL,"auto","0","10","20","30","40","50","60","70","80","90","100","invalid"};
    for(unsigned path=0;path<2;path++) {
        tone_auxiliary=path!=0;
        for(unsigned source=tone_auxiliary?1:0;source<4;source++) {
            memset(selected_gain,0,sizeof selected_gain);
            create_tones(1u<<source);
            // Native constructor defaults, before any adapter option reader.
            size_t initial_size=native_state(initial_state);
            render_tones(native,GAIN_FRAMES);
            size_t baseline_size=native_state(baseline_state);assert(nonzero(native));
            for(unsigned c=0;c<sizeof choices/sizeof choices[0];c++) {
                selected_gain[source]=choices[c];
                restore_native_state(initial_state,initial_size);read_options();
                render_tones(actual,GAIN_FRAMES);
                size_t size=native_state(actual_state);
                if(size!=baseline_size || memcmp(actual_state,baseline_state,size)) {
                    for(size_t i=0;i<size && i<baseline_size;i++)if(actual_state[i]!=baseline_state[i]) {
                        fprintf(stderr,"State mismatch source=%u value=%s size=%zu offset=%zu expected=%u actual=%u\n",source,choices[c]?choices[c]:"<missing>",size,i,baseline_state[i],actual_state[i]);break;
                    }
                }
                assert(size==baseline_size && !memcmp(actual_state,baseline_state,size));
                unsigned gain=(!choices[c] || !strcmp(choices[c],"auto") || !strcmp(choices[c],"invalid"))?100:(unsigned)atoi(choices[c]);
                for(unsigned i=0;i<GAIN_FRAMES*2;i++) {
                    assert(abs(native[i])<30000); // Scaling assertions must not hide clipping.
                    assert(abs((int)actual[i]-(int)native[i]*(int)gain/100)<=1);
                }
                if(gain==100)assert(!memcmp(actual,native,sizeof native));
                if(!gain)assert(!nonzero(actual));
            }
            selected_gain[source]="auto";
            for(unsigned other=0;other<4;other++)if(other!=source) {
                selected_gain[other]="0";
                restore_native_state(initial_state,initial_size);read_options();
                render_tones(actual,GAIN_FRAMES);
                size_t size=native_state(actual_state);
                assert(!memcmp(actual,native,sizeof native));
                assert(size==baseline_size && !memcmp(actual_state,baseline_state,size));
                selected_gain[other]=NULL;
            }
            selected_gain[source]="0";restore_native_state(initial_state,initial_size);read_options();
            render_tones(actual,1024);
            for(unsigned i=0;i<2048;i++)assert(!actual[i]);
            selected_gain[source]="auto";read_options();
            render_tones(actual+2048,GAIN_FRAMES-1024);
            assert(!memcmp(actual+2048,native+2048,sizeof native-2048*sizeof *actual));
            size_t size=native_state(actual_state);
            assert(size==baseline_size && !memcmp(actual_state,baseline_state,size));
            selected_gain[source]="50";read_options();m2snd_reset(sound);start_tones(1u<<source);
            render_tones(actual,GAIN_FRAMES);
            for(unsigned i=0;i<GAIN_FRAMES*2;i++)assert(abs((int)actual[i]-(int)native[i]/2)<=1);
            destroy_tones();
            printf("PASS: %s %s Auto/100 exact; 0..100 levels; other-source no-op; unchanged synthesis state; mute/resume; reset retains gain\n",tone_auxiliary?"auxiliary":"main",gain_keys[source]);
        }
        // All three original-board sources active together: muting one must only
        // remove that source. Integer native mix rounding permits one sample unit.
        int16_t mixed[GAIN_FRAMES*2],isolated[GAIN_FRAMES*2];
        memset(selected_gain,0,sizeof selected_gain);
        create_tones(14);render_tones(mixed,GAIN_FRAMES);destroy_tones();
        for(unsigned source=1;source<4;source++) {
            memset(selected_gain,0,sizeof selected_gain);selected_gain[source]="0";
            capture(14,actual,NULL,NULL);
            memset(selected_gain,0,sizeof selected_gain);
            capture(1u<<source,isolated,NULL,NULL);
            assert(nonzero(isolated));
            for(unsigned i=0;i<GAIN_FRAMES*2;i++)assert(abs((int)mixed[i]-actual[i]-isolated[i])<=1);
        }
    }
    free(tone_samples);free(baseline_state);free(actual_state);free(initial_state);
    puts("PASS: independent native mixed-source contributions; no ROMs, games or audio devices used");
    return 0;
}
