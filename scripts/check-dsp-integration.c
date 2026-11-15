/* Synthetic sound program through the real 68000 bus, mixer, archive and
 * Libretro fault path. No diagnostic exports or game/ROM data. */
#include "../src/libretro/libretro.c"
#include <assert.h>
#include "../port/m68k/m68k.h"

extern void m68k_write_memory_8(unsigned, unsigned);
extern void m68k_write_memory_16(unsigned, unsigned);
extern void m68k_write_memory_32(unsigned, unsigned);
extern unsigned m68k_read_memory_8(unsigned);
extern unsigned m68k_read_memory_16(unsigned);
extern unsigned m68k_read_memory_32(unsigned);
static uint8_t program[0x200];
static const m2_game game={.name="dsp-fixture",.title="DSP Fixture",
    .board="Model 2A",.fps=58};
static unsigned shutdowns, delivered;
static char notice[256];
static bool environment(unsigned command,void *data) {
    if(command==RETRO_ENVIRONMENT_SHUTDOWN) {shutdowns++;return true;}
    if(command==RETRO_ENVIRONMENT_SET_MESSAGE_EXT) {
        snprintf(notice,sizeof notice,"%s",((struct retro_message_ext *)data)->msg);return true;
    }
    if(command==RETRO_ENVIRONMENT_SET_MESSAGE) {
        snprintf(notice,sizeof notice,"%s",((struct retro_message *)data)->msg);return true;
    }
    return false;
}
static size_t batch(const int16_t *pcm,size_t n) {(void)pcm;delivered+=(unsigned)n;return n;}
static void word(unsigned at,uint16_t v) {program[at]=(uint8_t)v;program[at+1]=(uint8_t)(v>>8);}
static void reg(unsigned at,uint16_t v) {m68k_write_memory_16(0x100000+at,v);}
static void create(void) {
    board=calloc(1,sizeof *board);assert(board);
    board->type=1;board->game=&game;
    word(0,7);word(2,0xff00);word(4,0x60);word(6,0x100);word(0x100,0x60fe);
    board->rom.ptr[5]=program;board->rom.size[5]=sizeof program;
    sound=m2snd_create(board);assert(sound);
    int16_t ignored[2];m2snd_render(sound,ignored,0); /* Bind the native bus. */
}
static void destroy(void) {m2snd_destroy(sound);sound=NULL;free(board);board=NULL;}
static size_t archive(uint8_t *data) {
    m2_state a={data,4u<<20,0,M2_STATE_SAVE,0};m2snd_state_archive(sound,&a);
    assert(!a.failed);return a.pos;
}
static void effect_tone(uint16_t value) {
    /* The forward loop cycles through samples 1 and 2 after its first pass. */
    for (unsigned i=0; i<3; ++i) m68k_write_memory_16(0x4000+2*i,value);
    reg(0x400,15);reg(2,0x4000);reg(6,3);reg(8,0x1f);
    reg(0x14,7);reg(0x16,0xe0); /* DSP input/output only; direct output disabled. */
    reg(0,0x1820);reg(0x700,0x4000);
    reg(0x802,0xa800);reg(0x804,2); /* ACC = MIXS[0] * 0.5. */
    reg(0x80c,0x1000);             /* EFREG[0] = previous ACC >> 8. */
}
static void linear_ram(void) {
    for(unsigned width=1;width<=4;width*=2) {
        unsigned lo=0x12000+width*8,hi=lo+0x80000;
        if(width==1) {
            m68k_write_memory_8(lo,0x12);m68k_write_memory_8(hi,0x34);
            assert(m68k_read_memory_8(lo)==0x12&&m68k_read_memory_8(hi)==0x34);
        } else if(width==2) {
            m68k_write_memory_16(lo,0x1122);m68k_write_memory_16(hi,0x3344);
            assert(m68k_read_memory_16(lo)==0x1122&&m68k_read_memory_16(hi)==0x3344);
        } else {
            m68k_write_memory_32(lo,0x11223344);m68k_write_memory_32(hi,0x55667788);
            assert(m68k_read_memory_32(lo)==0x11223344&&m68k_read_memory_32(hi)==0x55667788);
        }
    }
    m68k_write_memory_32(0xfffffc,0x12345678); /* Unmapped bus, not CPU RAM. */
    m68k_write_memory_32(0xffffc,0x89abcdef);
    assert(m68k_read_memory_32(0xffffc)==0x89abcdef);
    /* Raw archive begins with shared RAM: verify native backing, rather than
     * only checking a mutually consistent reader/writer pair. */
    m68k_write_memory_16(0x14000,0x1122);
    m68k_write_memory_16(0x14003,0x3344); /* Keep Musashi's odd guest access. */
    assert(m68k_read_memory_16(0x14003)==0x3344);
    uint8_t *raw=malloc(4u<<20);assert(raw);archive(raw);
    assert(raw[0]==7 && raw[1]==0 && raw[2]==0 && raw[3]==0xff);
    assert(raw[0x14000]==0x22 && raw[0x14001]==0x11);
    assert(raw[0x14002]==0x33 && raw[0x14005]==0x44);
    assert(raw[0xffffc]==0xab && raw[0xffffd]==0x89 && raw[0xffffe]==0xef && raw[0xfffff]==0xcd);
    free(raw);
    /* Original CPU writes retain DMA registers without executing a transfer. */
    m68k_write_memory_16(0x3000,0x1357);
    m68k_write_memory_16(0x3002,0x5678);m68k_write_memory_16(0x3004,0x9abc);
    reg(0x412,0x3000);reg(0x414,0x700);reg(0x416,0x1002);
    assert(m68k_read_memory_16(0x100416)==0x1002);
    assert(m68k_read_memory_16(0x100700)==0); /* Native CPU read is write-only. */
    reg(0x412,0x3002);reg(0x414,0x700);reg(0x416,0x3002);
    assert(m68k_read_memory_16(0x3002)==0x5678);
    reg(0x700,0x2468);reg(0x412,0x3004);reg(0x414,0x700);reg(0x416,0x3002);
    assert(m68k_read_memory_16(0x3004)==0x9abc);
    m68k_write_memory_8(0x100416,0x10);m68k_write_memory_8(0x100417,2);
    assert(m68k_read_memory_16(0x100416)==0x1002);
    m68k_write_memory_32(0x100414,0x07003002);
    assert(m68k_read_memory_16(0x100414)==0x700 && m68k_read_memory_16(0x100416)==0x3002);
    assert(m68k_read_memory_16(0x3004)==0x9abc);
    uint8_t *old=calloc(1,STATE_CAPACITY);assert(old);
    state_header *h=(state_header *)old;
    h->abi=STATE_ABI|STATE_DSP_BACKEND_SCHEMA|STATE_ORIGINAL_DSP_ABI;
    notice[0]=0;
    assert(!retro_unserialize(old,STATE_CAPACITY)); /* Missing linear-RAM bit. */
    assert(strstr(notice,"incompatible sound CPU RAM map"));
    assert(m68k_read_memory_32(0xffffc)==0x89abcdef);
    free(old);
}
static void midi_output_continuation(unsigned backend) {
    uint8_t expected[130] = {0};
    uint8_t *saved = malloc(4u << 20);
    uint8_t *after = malloc(4u << 20);
    assert(saved && after);
    create();
    m2snd_set_dsp_backend(sound, backend);
    for (unsigned i = 0; i < 259; ++i) {
        uint8_t byte = (uint8_t)(i * 73 + 19);
        reg(0x406, byte);
        expected[i & 127] = byte;
    }
    expected[128] = expected[129] = 3; /* cursor and count both wrapped */
    size_t used = archive(saved);
    size_t at = 0;
    while (at + sizeof expected <= used && memcmp(saved + at, expected, sizeof expected)) ++at;
    assert(at + sizeof expected <= used);
    destroy();
    create();
    m2snd_set_dsp_backend(sound, backend);
    saved[at + 128] = 128;
    m2_state check = {saved, used, 0, M2_STATE_CHECK, 0};
    m2snd_state_archive(sound, &check);
    assert(check.failed);
    saved[at + 128] = 3;
    m2_state load = {saved, used, 0, M2_STATE_LOAD, 0};
    m2snd_state_archive(sound, &load);
    assert(!load.failed && load.pos == used);
    m68k_write_memory_8(0x100406, 0xab); /* High lane enqueues the retained low byte. */
    expected[3] = expected[2];
    expected[128] = expected[129] = 4;
    assert(archive(after) == used && !memcmp(after + at, expected, sizeof expected));
    free(after);
    free(saved);
    destroy();
}

static void voice_sample_continuation(unsigned backend, unsigned loop_mode) {
    create();
    m2snd_set_dsp_backend(sound,backend);
    for(unsigned i=0;i<=8;i++)m68k_write_memory_8(0x84000+i,0x11+i);
    reg(0x400,15);reg(2,0x4000);reg(6,8);reg(0xc,0x200);reg(0x16,0xe000);
    reg(0,0x1818 | (loop_mode << 5)); /* Key-on at 0x84000, 8-bit PCM. */
    reg(2,0x5000); /* A distinct, silent address for the next key-on. */
    int16_t expected[64],actual[64];
    m2snd_render(sound,actual,1);
    assert(!actual[0] && !actual[1]); /* Key-on clears the interpolation history. */
    if (loop_mode >= 2) m2snd_render(sound,actual,8); /* Save while travelling backward. */
    reg(8, 0x15); /* Recompute active attack without resetting the current volume. */
    reg(0x10,(4u << 11) | 498); /* Live update: the native high-octave step wraps to 16. */
    uint8_t *saved=malloc(4u<<20);assert(saved);
    size_t used=archive(saved);
    /* A snapshot with the previous SCSP marker must fail preflight
     * before loading any board state. This fixture contains one SCSP. */
    size_t marker = 0;
    while (marker + 4 <= used && memcmp(saved + marker, "SCP9", 4)) ++marker;
    assert(marker + 4 <= used);
    saved[marker + 3] = '8';
    m2_state old = {saved, used, 0, M2_STATE_CHECK, 0};
    m2snd_state_archive(sound, &old);
    assert(old.failed);
    saved[marker + 3] = '9';
    m2snd_render(sound,expected,32);
    assert(!m2snd_fault(sound,NULL) && memcmp(expected,(int16_t[64]){0},sizeof expected));
    destroy();create();m2snd_set_dsp_backend(sound,backend);
    m2_state a={saved,used,0,M2_STATE_LOAD,0};m2snd_state_archive(sound,&a);
    assert(!a.failed && a.pos==used);
    m2snd_render(sound,actual,32);
    assert(!m2snd_fault(sound,NULL) && !memcmp(expected,actual,sizeof actual));
    free(saved);destroy();
}
/* Save after the CPU writes the cursor and before the mixer follows it.
 * A cell above 63 aliases DSP coefficients, then wraps on increment. */
static void pending_ring_continuation(void)
{
    create();
    effect_tone(0x1b4d);
    int16_t warmup[8], expected[8], actual[8];
    m2snd_render(sound, warmup, 4);
    reg(0x680, 76); reg(0x682, 0x705a);
    reg(0x688, 0x100); reg(0x68a, 0x39de);
    reg(0x12, 0x7fe4); /* Bind both LFOs, then disable them before saving. */
    reg(0x12, 0);
    uint32_t pitch_table = m68k_read_memory_16(0x100490);
    uint32_t amplitude_table = m68k_read_memory_16(0x1004a0);
    assert(pitch_table && amplitude_table);
    uint8_t *saved = malloc(4u << 20);
    assert(saved);
    size_t used = archive(saved);
    m2snd_render(sound, expected, 4);
    unsigned coeff = m68k_read_memory_16(0x100698);
    assert(coeff == 0x1b4d);
    destroy();
    create();
    m2_state a = {saved, used, 0, M2_STATE_LOAD, 0};
    m2snd_state_archive(sound, &a);
    assert(!a.failed && a.pos == used);
    assert(m68k_read_memory_16(0x100680) == 76 && m68k_read_memory_16(0x100682) == 0x705a);
    assert(m68k_read_memory_16(0x100688) == 0x100 && m68k_read_memory_16(0x10068a) == 0x39de);
    assert(m68k_read_memory_16(0x100490) == pitch_table && m68k_read_memory_16(0x1004a0) == amplitude_table);
    m2snd_render(sound, actual, 4);
    assert(!memcmp(expected, actual, sizeof actual));
    assert(m68k_read_memory_16(0x100698) == coeff && m68k_read_memory_16(0x100680) == 16);
    free(saved);
    destroy();
}

#ifdef M2_ENABLE_A68K
static void immediate_a68k_commands(void)
{
    create();
    assert(m2snd_enable_a68k(sound, 0));
    for (unsigned i = 0; i < 259; ++i) m2snd_command(sound, (uint8_t)(i * 53 + (i >> 7)));
    /* The i960 port has returned but the sound CPU has not had a timeslice.
     * The 128-byte hardware FIFO has overwritten its oldest cells twice. */
    uint8_t *saved = malloc(4u << 20);
    assert(saved);
    size_t used = archive(saved);
    for (unsigned run = 0; run < 2; ++run) {
        if (run) {
            destroy(); create();
            assert(m2snd_enable_a68k(sound, 0));
            m2_state load = {saved, used, 0, M2_STATE_LOAD, 0};
            m2snd_state_archive(sound, &load);
            assert(!load.failed && load.pos == used);
        }
        m2snd_reset(sound);
        for (unsigned i = 256; i < 259; ++i)
            assert((m68k_read_memory_16(0x100404) & 255) == (uint8_t)(i * 53 + (i >> 7)));
    }
    free(saved); destroy();
}
#endif

static void unbound_lfo_continuation(void)
{
    for (unsigned depth = 1; depth <= 0x20; depth *= 0x20) {
        create();
        reg(2,0x4000); reg(6,16); reg(0,0x1820);
        /* The odd word straddles the pitch/LFO registers. Its update
         * selects pitch only, leaving both LFO table pointers at zero. */
        m68k_write_memory_16(0x100011, depth << 8);
        assert(m68k_read_memory_16(0x100012) == depth);
        uint8_t *saved = malloc(4u << 20);
        assert(saved); size_t used = archive(saved);
        destroy(); create();
        m2_state state = {saved, used, 0, M2_STATE_CHECK, 0};
        m2snd_state_archive(sound, &state);
        assert(!state.failed && state.pos == used);
        state.mode=M2_STATE_LOAD; state.pos=0;
        m2snd_state_archive(sound, &state);
        assert(!state.failed && !m2snd_fault(sound,NULL));
        int16_t pcm[2]; uint32_t address;
        m2snd_render(sound,pcm,1);
        const char *fault = m2snd_fault(sound,&address);
        assert(fault && !strcmp(fault, depth == 1 ? "SCSP amplitude LFO" : "SCSP pitch LFO"));
        assert(address == 0 && !pcm[0] && !pcm[1]);
        free(saved); destroy();
    }
}

static void voice_sample_fault(void) {
    create();
    reg(2,0xffff);reg(6,1);reg(0,0x183f); /* Native forward loop restarts at sample 1. */
    int16_t pcm[2];uint32_t address;
    m2snd_render(sound,pcm,1);assert(!m2snd_fault(sound,NULL));
    m2snd_render(sound,pcm,1);
    const char *source=m2snd_fault(sound,&address);
    assert(source && !strcmp(source,"SCSP voice") && address==0x100001);
    first_frame=false;nvram_pending=network_reset_pending=state_options_pending=false;
    retro_run();retro_run();
    assert(content_failed && shutdowns==1 && !delivered && strstr(notice,"SCSP voice accessed 0x00100001"));
    content_failed=false;shutdowns=0;notice[0]=0;
    m2snd_reset(sound);assert(!m2snd_fault(sound,NULL));destroy();
}
static void voice_ram_redirection(unsigned backend)
{
    uint8_t *saved = malloc(4u << 20);
    int16_t pcm[32], expected[32], silence[32] = {0};
    assert(saved);
    create();
    m2snd_set_dsp_backend(sound, backend);
    /* The active voice loops over a constant, nonzero word in sound RAM.
     * The matching addresses in private DSP RAM contain reset-time zero. */
    for (unsigned at = 0x4000; at < 0x4010; at += 2)
        m68k_write_memory_16(at, 0x4567);
    reg(0x400, 15); reg(2, 0x4000); reg(6, 3); reg(8, 0x1f);
    reg(0x16, 0xe000); reg(0, 0x1820);
    m2snd_render(sound, pcm, 16);
    assert(memcmp(pcm, silence, sizeof pcm));
    reg(0x686, 0x7800);
    assert(m68k_read_memory_16(0x100686) == 0x7800);
    size_t used = archive(saved);
    m2snd_render(sound, expected, 16);
    /* Interpolation retains the previous sample at the switch. */
    assert(!memcmp(expected+2, silence, sizeof expected-2*sizeof *expected));
    destroy();
    create();
    m2snd_set_dsp_backend(sound, backend);
    m2_state load = {saved, used, 0, M2_STATE_LOAD, 0};
    m2snd_state_archive(sound, &load);
    assert(!load.failed && load.pos == used);
    m2snd_render(sound, pcm, 16);
    assert(!memcmp(pcm, expected, sizeof pcm));
    reg(0x686, 0x7300);
    m2snd_render(sound, pcm, 16);
    assert(!m2snd_fault(sound,NULL) && memcmp(pcm, silence, sizeof pcm));
    reg(0x686, 0x5500);
    assert(!m2snd_fault(sound,NULL));
    m2snd_render(sound, pcm, 1);
    uint32_t address;
    assert(m2snd_fault(sound,&address) && (address >> 16) == 0x5500);
    destroy();
    free(saved);
}

static void dsp_ram_redirection(void)
{
    uint8_t *saved = malloc(4u << 20);
    int16_t pcm[2];
    assert(saved);
    create();
    reg(0x780, 0x2000); /* Word address, byte offset 0x4000. */
    reg(0x80c, 0xc000); /* Step 1 writes zero to the selected TABLE word. */
    reg(0xbfe, 0);
    m68k_write_memory_16(0x4020, 0x5678);
    reg(0x68c, 0x20);
    reg(0x68e, 0x7300);
    assert(m68k_read_memory_16(0x10068c) == 0x20 && m68k_read_memory_16(0x10068e) == 0x7300);
    size_t used = archive(saved); /* CPU pointer changed, compiled pointer still private. */
    for (unsigned pass = 0; pass < 2; ++pass) {
        if (pass) {
            destroy();
            create();
            m2_state load = {saved, used, 0, M2_STATE_LOAD, 0};
            m2snd_state_archive(sound, &load);
            assert(!load.failed && load.pos == used);
        }
        m2snd_render(sound, pcm, 1);
        assert(!m2snd_fault(sound,NULL) && m68k_read_memory_16(0x4020) == 0x5678);
        reg(0xbfe, 0);
        m2snd_render(sound, pcm, 1);
        assert(!m2snd_fault(sound,NULL) && m68k_read_memory_16(0x4020) == 0);
    }
    /* Unknown pending values can be written in halves. Start is the boundary. */
    reg(0x68e, 0x5500);
    assert(!m2snd_fault(sound,NULL));
    reg(0xbfe, 0);
    uint32_t address = 0;
    assert(m2snd_fault(sound,&address) && address == 0x55000020);
    destroy();

    create();
    reg(0x780, 1);
    reg(0x80c, 0xa000);
    reg(0x68c, 0xfffd);
    reg(0x68e, 0x730f);
    reg(0xbfe, 0);
    m2snd_render(sound, pcm, 1); /* Word straddles the upper sound RAM boundary. */
    assert(m2snd_fault(sound,&address) && address == 0xfffff);
    destroy();

    create();
    m2snd_set_dsp_backend(sound, 1);
    reg(0x68e, 0x5500);
    reg(0xbf0, 0);
    m2snd_render(sound, pcm, 1);
    assert(!m2snd_fault(sound,NULL));
    destroy();
    free(saved);
    puts("PASS: live and compiled DSP RAM addresses, pending switch across a cold restore, bounded shared RAM and independent MAME addressing");
}

static void dsp_ring_base(void) {
    create();
    /* The ring aliases expose the full RBP and RBL fields that the
     * ordinary global register initializes with its decoded geometry. */
    reg(0x402, 0x0081);
    assert(m68k_read_memory_16(0x100690) == 1 && m68k_read_memory_16(0x100694) == 0x4000);
    reg(0x692, 0x4321);
    reg(0x696, 0x4567);
    assert(m68k_read_memory_16(0x100692) == 0x4321 && m68k_read_memory_16(0x100696) == 0x4567);
    reg(0x780,0xffff); /* MADRS[0] selects the last word of the table. */
    reg(0x80c,0xa000); /* Step 1: TABLE and MRD. */
    m68k_write_memory_32(0x100400,0x000f003f);
    reg(0xbfe,0);
    int16_t pcm[2];
    m2snd_render(sound,pcm,1);
    assert(!m2snd_fault(sound,NULL));
    m68k_write_memory_8(0x100403,0x7f);
    m2snd_render(sound,pcm,1);
    uint32_t address=0;
    assert(m2snd_fault(sound,&address) && address==0x11dffe);
    destroy();
}
static void create_irq_fixture(void) {
    create();
    const uint16_t main_code[]={0x207c,0,0x2000,0x46fc,0x2000,0x60fe};
    const uint16_t irq_code[]={0x3039,0x0010,0x0404,0x30c0,0x4e73};
    for(unsigned i=0;i<sizeof main_code/sizeof main_code[0];i++)word(0x100+i*2,main_code[i]);
    for(unsigned i=0;i<sizeof irq_code/sizeof irq_code[0];i++)word(0x120+i*2,irq_code[i]);
    m2snd_reset(sound);
    m68k_write_memory_32(0x78,0x600120); /* Level-6 autovector. */
    reg(0x424,0);reg(0x426,8);reg(0x428,8); /* MIDI level 6, SCIEB still zero. */
}
static void midi_irq_continuation(void) {
    create_irq_fixture();
    for(unsigned i=1;i<=40;i++)m2snd_command(sound,(uint8_t)i);
    int16_t pcm[128];m2snd_render(sound,pcm,1); /* Enqueue, then native IRQ check. */
    uint8_t *saved=malloc(4u<<20),*expected=malloc(4u<<20),*actual=malloc(4u<<20);assert(saved&&expected&&actual);
    size_t used=archive(saved);m2snd_render(sound,pcm,64);size_t expected_used=archive(expected);
    for(unsigned i=0;i<40;i++)assert(m68k_read_memory_16(0x2000+i*2)==i+1);
    /* One receive per command, as measured with the original live autovector. */
    unsigned a0=m68k_get_reg(NULL,M68K_REG_A0);assert(a0==0x2050);
    destroy();create_irq_fixture();
    m2_state a={saved,used,0,M2_STATE_CHECK,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    a=(m2_state){saved,used,0,M2_STATE_LOAD,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    m2snd_render(sound,pcm,64);assert(archive(actual)==expected_used&&!memcmp(actual,expected,expected_used));
    assert(m68k_get_reg(NULL,M68K_REG_A0)==a0);
    free(saved);free(expected);free(actual);destroy();
    printf("PASS: native 128-byte MIDI FIFO, 40-command Musashi IRQ consumer with SCIEB zero, live ElSemi autovector, exact cold continuation with pending IRQ\n");
}
int main(int argc,char **argv) {
    retro_set_environment(environment);retro_set_audio_sample_batch(batch);retro_init();
    if(argc==2 && !strcmp(argv[1],"--midi-read-probe")) {
        create();for(unsigned i=1;i<=40;i++)m2snd_command(sound,(uint8_t)i);
        int16_t pcm[2];m2snd_render(sound,pcm,1);
        printf("[");for(unsigned i=0;i<40;i++)printf("%s%u",i?",":"",m68k_read_memory_16(0x100404));
        printf("]\n");destroy();return 0;
    }
    if(argc==2 && !strcmp(argv[1],"--board-read-probe")) {
        create();reg(2,0x1357);reg(0x600,0x2468);reg(0x700,0x369a);reg(0,0x1820);
        printf("[");
        const unsigned offsets[]={2,3,0x1f,0x600,0x601,0x700,0x701};
        for(unsigned i=0;i<sizeof offsets/sizeof offsets[0];i++)for(unsigned width=1;width<=4;width*=2) {
            unsigned address=0x100000+offsets[i];
            unsigned value=width==1?m68k_read_memory_8(address):width==2?m68k_read_memory_16(address):m68k_read_memory_32(address);
            printf("%s{\"address\":%u,\"width\":%u,\"value\":%u}",i||width!=1?",":"",address,width,value);
        }
        printf("]\n");destroy();return 0;
    }
    pending_ring_continuation();
    unbound_lfo_continuation();
#ifdef M2_ENABLE_A68K
    immediate_a68k_commands();
#endif
    midi_irq_continuation();
    for (unsigned backend=0;backend<2;++backend)
        for (unsigned mode=0;mode<4;++mode)
            voice_sample_continuation(backend,mode);
    voice_sample_fault();dsp_ring_base();dsp_ram_redirection();
    voice_ram_redirection(0);
    voice_ram_redirection(1);
    midi_output_continuation(0);
    midi_output_continuation(1);
    puts("PASS: native MIDI output ring wrap, invalid cursor rejection and cold continuation on both DSPs");
    create();linear_ram();
    /* These ring words alias the DSP's first and 52nd coefficient. */
    for (unsigned i=0; i<52; ++i) {
        reg(0x700+2*i, 0xae00+i);
        assert(m68k_read_memory_16(0x100698+2*i)==0xae00+i);
        m68k_write_memory_8(0x100699+2*i, i+1);
        assert(m68k_read_memory_16(0x100698+2*i)==i+1);
        reg(0x700+2*i, 0);
    }
    effect_tone(0x4000);
    reg(0x67c,0x4321); reg(0x67e,0xfedc);
    m68k_write_memory_8(0x10067e,0x91);
    assert(m68k_read_memory_16(0x10067e)==0x91);
    m68k_write_memory_8(0x10067f,0x85);
    m68k_write_memory_32(0x10067c,0x11223344);
    assert(m68k_read_memory_16(0x10067c)==0x4321 && m68k_read_memory_16(0x10067e)==0x85);
    int16_t pcm[256*2],expected[256*2];
    reg(0x802,0);reg(0x804,0);
    m68k_write_memory_32(0x1007c2,0xa8000002); /* Upper MADRS writes MPRO[1..2]. */
    m68k_write_memory_8(0x1007c2,0); /* Upper MADRS ignores byte stores. */
    reg(0xbf0,0);m68k_write_memory_8(0x100bff,0);
    m68k_write_memory_32(0x100bfe,0x00001234); /* Low word reaches TEMP without Start. */
    m2snd_render(sound,pcm,256);
    for(unsigned i=0;i<512;i++)assert(!pcm[i]); /* These writes leave the original DSP stopped. */
    reg(0xbfe,0);m2snd_render(sound,pcm,256);
    unsigned nonzero=0;for(unsigned i=0;i<512;i++)nonzero+=pcm[i]!=0;
    assert(nonzero && !m2snd_fault(sound,NULL));
    /* Writable MPRO diverges from cached code until the next Start event. */
    reg(0x802,0);reg(0x804,0);reg(0x80c,0);
    uint8_t *saved=malloc(4u<<20),*after=malloc(4u<<20),*actual=malloc(4u<<20);
    assert(saved&&after&&actual);size_t used=archive(saved);
    m2snd_render(sound,expected,256);size_t after_used=archive(after);
    assert(memcmp(expected,(int16_t[512]){0},sizeof expected));
    destroy();create();
    size_t before_used=archive(actual);
    m2_state a={saved,used,0,M2_STATE_CHECK,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    uint8_t *untouched=malloc(4u<<20);assert(untouched);
    assert(archive(untouched)==before_used&&!memcmp(untouched,actual,before_used));free(untouched);
    a=(m2_state){saved,used,0,M2_STATE_LOAD,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    assert(m68k_read_memory_32(0xffffc)==0x89abcdef);
    m2snd_render(sound,pcm,256);assert(!memcmp(pcm,expected,sizeof pcm));
    assert(archive(actual)==after_used&&!memcmp(actual,after,after_used));
    reg(0xbfe,0);m2snd_render(sound,pcm,256);
    for(unsigned i=0;i<512;i++)assert(!pcm[i]);
    /* Valid bus values exercise the original combined MWT/MRD quirk:
     * negative SHIFTED becomes an escaped unsigned read address. */
    effect_tone(0xc000);
    reg(0x80c,0xe000);reg(0xbfe,0);
    m2snd_render(sound,pcm,256);
    uint32_t address=0;assert(m2snd_fault(sound,&address));assert(address>=0x100000);
    size_t failed_used=archive(saved);
    memset(pcm,0x55,sizeof pcm);m2snd_render(sound,pcm,256);
    for(unsigned i=0;i<512;i++)assert(!pcm[i]);
    assert(archive(actual)==failed_used&&!memcmp(actual,saved,failed_used));
    /* Exercise retro_run's actual notification/shutdown branch; the fault
     * prevents board_step/rendering, so no GL/window or game CPU is needed. */
    first_frame=false;nvram_pending=network_reset_pending=state_options_pending=false;
    retro_run();assert(content_failed && shutdowns==1 && delivered==0);
    assert(strstr(notice,"Original SCSP DSP")&&strstr(notice,"content stopped"));
    char hex[16];snprintf(hex,sizeof hex,"%08x",address);assert(strstr(notice,hex));
    retro_run();assert(shutdowns==1 && delivered==0);
    m2snd_reset(sound);assert(!m2snd_fault(sound,NULL));
    printf("PASS: bus start masks, nonzero DSP-only PCM, cached program, cold sound archive (%zu bytes), nonmutating preflight, exact PCM/state continuation, escaped address 0x%08x, frozen fault, frontend message/shutdown, reset\n",used,address);
    printf("PASS: linear 1 MiB CPU byte/word/long RAM, native raw byte order/vectors, odd Musashi word, native CPU DMA register stores without transfers, upper edge, cold-state retention, old-map rejection, latched SCSP sample bases on both DSPs and bounded voice fault\n");
    assert(m2snd_get_dsp_backend(sound)==0);
    m2snd_set_dsp_backend(sound,1);assert(m2snd_get_dsp_backend(sound)==1);
    effect_tone(0x4000);reg(0xbfe,0);m2snd_render(sound,pcm,256);
    for(unsigned i=0;i<512;i++)assert(!pcm[i]); /* MAME starts at BF0. */
    reg(0xbf0,0);m2snd_render(sound,pcm,256);
    assert(memcmp(pcm,(int16_t[512]){0},sizeof pcm));
    used=archive(saved);m2snd_render(sound,expected,256);after_used=archive(after);
    destroy();create(); /* New chip has the approved original default. */
    before_used=archive(actual);
    a=(m2_state){saved,used,0,M2_STATE_CHECK,0};m2snd_state_archive(sound,&a);assert(a.failed);
    uint8_t *unchanged=malloc(4u<<20);assert(unchanged);
    assert(archive(unchanged)==before_used&&!memcmp(actual,unchanged,before_used));free(unchanged);
    m2snd_set_dsp_backend(sound,1);
    a=(m2_state){saved,used,0,M2_STATE_CHECK,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    a=(m2_state){saved,used,0,M2_STATE_LOAD,0};m2snd_state_archive(sound,&a);assert(!a.failed);
    m2snd_render(sound,pcm,256);assert(!memcmp(pcm,expected,sizeof pcm));
    assert(archive(actual)==after_used&&!memcmp(actual,after,after_used));
    reg(0x802,0);reg(0x804,0);reg(0x80c,0);m2snd_render(sound,pcm,256);
    for(unsigned i=0;i<512;i++)assert(!pcm[i]); /* Live MPRO, no Start needed. */
    m2snd_reset(sound);assert(m2snd_get_dsp_backend(sound)==1);
    printf("PASS: MAME BF0 start, live program, nonzero DSP-only PCM, cold sound archive (%zu bytes), exact PCM/state continuation, other-backend preflight rejection without mutation, reset retains backend\n",used);
    free(saved);free(after);free(actual);destroy();return 0;
}
