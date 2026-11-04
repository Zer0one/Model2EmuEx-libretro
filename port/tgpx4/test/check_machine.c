/* Synthetic board integration through the real i960 memory map. */
#include "../../m2/m2board.h"
#include "../../m2/m2tgpx4.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *zero(size_t n){void *p=calloc(1,n);assert(p);return p;}
int main(void) {
    static const m2_game game={.name="skisuprg",.fps=60,.input_fn=0x4c9dc0};
    m2_board *b=zero(sizeof *b);b->type=3;b->game=&game;
    b->cpu=zero(sizeof *b->cpu);
#define MEM(name,bytes) b->name=zero(bytes)
    MEM(ram,0x100000);MEM(fb,0x80000);MEM(ram2,0x40000);MEM(pal,0x10000);
    MEM(cg,0x100000);MEM(tile,0x10000);MEM(back,0x18000);MEM(xlat,0x10004);
    MEM(luma,0x20004);MEM(bufram,0x80004);MEM(tgp_prog,0x40000);MEM(tgp_data,0x40000);
    MEM(coproram,0x40000);MEM(tex0,0x100004);MEM(tex1,0x100004);MEM(zshared,0x18000);MEM(scsp,0x10000);
#undef MEM
    b->rom.ptr[0]=zero(0x40000);b->rom.size[0]=0x40000;
    b->rom.ptr[1]=zero(0x10000);b->rom.size[1]=0x10000;
    b->rom.ptr[2]=zero(0x2000000);b->rom.size[2]=0x2000000;
    b->tgpx4=m2tgpx4_create(b);assert(b->tgpx4);
    for(unsigned repeat=0;repeat<3;repeat++) {
        m2_reset(b);
        /* Native per-frame acknowledgement, selected by the original input
         * routine. A missing command must not advance the countdown. */
        i960_write8(b->cpu,0x1c0000a,0xff);m2tgpx4_input_step(b);
        i960_write8(b->cpu,0x1c0000a,0);m2tgpx4_input_step(b);
        assert(i960_read8(b->cpu,0x1c00006)==0xce && b->reg_574cf0==UINT32_MAX);
        for(unsigned n=0;n<12;n++)m2tgpx4_input_step(b);
        assert(i960_read32(b->cpu,0x980004)==1);
        i960_write32(b->cpu,0x980000,0x80000000);
        i960_write16(b->cpu,0x884000,0xabcd);
        assert(b->tgp.prog_upload_off==2);
        assert(!memcmp(b->tgp_prog,"\xcd\xab",2));
        b->tgp.prog_upload_ctrl=0;
        i960_write32(b->cpu,0x980000,0x80000000);
        /* Native wide move FIFO->r0, r0->FIFO, then the next input gate. */
        static const uint32_t words[]={0x80000000,0xa7000218,
            0x32000000,0xa7000200,0x80000000,0xa7000218};
        for(unsigned i=0;i<sizeof words/sizeof words[0];i++)i960_write32(b->cpu,0x884000,words[i]);
        assert(b->tgp.prog_upload_off==sizeof words);
        i960_write32(b->cpu,0x980000,0);
        b->tgp_prog[0]^=0x80; /* Backing RAM diverges from the decoded cache. */
        size_t capacity=16u*1024u*1024u;
        uint8_t *saved=zero(capacity),*again=zero(capacity);
        m2_state archive={saved,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&archive);
        assert(!archive.failed);size_t used=archive.pos;
        archive=(m2_state){saved,used,0,M2_STATE_CHECK,0};m2_state_archive(b,&archive);
        assert(!archive.failed && archive.pos==used);
        i960_write32(b->cpu,0x880000,0x12345678);
        assert(i960_read32(b->cpu,0x980004)==0);
        assert(i960_read32(b->cpu,0x884000)==0x12345678);
        assert(i960_read32(b->cpu,0x980004)==1);
        memset(b->bufram_dirty,0,sizeof b->bufram_dirty);
        i960_write32(b->cpu,0x801008,0);
        i960_write32(b->cpu,0x800010,0x1234);
        assert(i960_read32(b->cpu,0x900000)==0x801234);
        assert(i960_read32(b->cpu,0x802008)==4 && b->bufram_dirty[0]);
        i960_write32(b->cpu,0x803008,0x456);
        assert(i960_read32(b->cpu,0x803008)==0x456);
        i960_write32(b->cpu,0x980008,0x80000000);
        i960_write32(b->cpu,0x804000,0x12345678);
        assert(b->tgp.data_upload_off==4 && !memcmp(b->tgp_data,"\x78\x56\x34\x12",4));
        i960_write32(b->cpu,0x980008,0);
        /* Replace the device allocation/session before loading, as M2A/M2B do. */
        m2tgpx4_destroy(b->tgpx4);b->tgpx4=m2tgpx4_create(b);assert(b->tgpx4);
        m2_reset(b);
        archive=(m2_state){saved,used,0,M2_STATE_LOAD,0};m2_state_archive(b,&archive);
        assert(!archive.failed);
        archive=(m2_state){again,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&archive);
        assert(!archive.failed && archive.pos==used && !memcmp(saved,again,used));
        for(unsigned n=0;n<9;n++) {
            i960_write8(b->cpu,0x1c0000a,0x80);m2tgpx4_input_step(b);
            assert(i960_read8(b->cpu,0x1c00006)==0xce);
        }
        i960_write8(b->cpu,0x1c0000a,0x80);m2tgpx4_input_step(b);
        assert(i960_read8(b->cpu,0x1c00006)==0xff);
        for(unsigned n=0;n<10;n++) {
            i960_write8(b->cpu,0x1c0000a,0x80);m2tgpx4_input_step(b);
        }
        assert(i960_read8(b->cpu,0x1c00006)==0x80);
        i960_write32(b->cpu,0x880000,0x12345678);
        assert(i960_read32(b->cpu,0x884000)==0x12345678);
        uint8_t device[16384],bad[16384];
        archive=(m2_state){device,sizeof device,0,M2_STATE_SAVE,0};
        m2tgpx4_state_archive(b->tgpx4,&archive);assert(!archive.failed);
        size_t device_used=archive.pos;
        const size_t corrupt[]={0,4,8+0x114,8+0x140,8+0x148,8+0x2154,8+0xa0,
            8+0x2164+0x148,8+0x2164+0xf4,device_used-3*0x94+0x80};
        for(unsigned i=0;i<sizeof corrupt/sizeof corrupt[0];i++) {
            memcpy(bad,device,device_used);bad[corrupt[i]]^=0xff;
            archive=(m2_state){bad,device_used,0,M2_STATE_CHECK,0};
            m2tgpx4_state_archive(b->tgpx4,&archive);assert(archive.failed);
        }
        for(size_t limit=0;limit<device_used;limit++) {
            archive=(m2_state){device,limit,0,M2_STATE_CHECK,0};
            m2tgpx4_state_archive(b->tgpx4,&archive);assert(archive.failed);
        }
        archive=(m2_state){bad,sizeof bad,0,M2_STATE_SAVE,0};
        m2tgpx4_state_archive(b->tgpx4,&archive);
        assert(!archive.failed && archive.pos==device_used && !memcmp(device,bad,device_used));
        free(saved);free(again);
    }
    /* Original Dynamite Cop page hook: preserve width-specific responses,
     * aliases, pending index/toggle and native reset persistence. */
    static const m2_game dynamcop={.name="dynamcopc",.fps=60,
        .hook=M2_HOOK_UNKNOWN,.hook_addr=0x4c7fa0};
    b->game=&dynamcop;m2_reset(b);
    for(uint32_t page=0x1d8;page<0x1e0;page++) {
        assert(i960_read8(b->cpu,page<<16)==0xff);
        assert(i960_read32(b->cpu,page<<16)==0xffff);
    }
    assert(i960_read16(b->cpu,0x1d90000)==0);
    assert(i960_read16(b->cpu,0x1d8400c)==0xffff);
    i960_write16(b->cpu,0x1d9000c,0x7700);
    assert(i960_read16(b->cpu,0x1d9000e)==0); /* First word is retained. */
    assert(i960_read16(b->cpu,0x1d87ff8)==0x5543);
    uint8_t protected_state[16384];
    m2_state protection={protected_state,sizeof protected_state,0,M2_STATE_SAVE,0};
    m2tgpx4_state_archive(b->tgpx4,&protection);assert(!protection.failed);
    const size_t protected_size=protection.pos;
    i960_write16(b->cpu,0x1d9000c,0x7140);
    assert(i960_read16(b->cpu,0x1d8400c)==0xfff0);
    m2tgpx4_destroy(b->tgpx4);b->tgpx4=m2tgpx4_create(b);assert(b->tgpx4);m2_reset(b);
    protection=(m2_state){protected_state,protected_size,0,M2_STATE_LOAD,0};
    m2tgpx4_state_archive(b->tgpx4,&protection);assert(!protection.failed);
    assert(i960_read16(b->cpu,0x1d8400c)==0xfff0);
    i960_write8(b->cpu,0x1d9000c,0);i960_write32(b->cpu,0x1d9000c,0);
    assert(i960_read16(b->cpu,0x1d9000e)==0x4849); /* Byte/dword writes do nothing. */
    m2_reset(b); /* Native hook only installs the map; does not clear globals. */
    assert(i960_read16(b->cpu,0x1d87ff8)==0x4441);
    i960_write16(b->cpu,0x1d9000c,0xffff); /* Unknown command resets only cursor. */
    assert(i960_read16(b->cpu,0x1d9000e)==0);
    assert(i960_read16(b->cpu,0x1d9000e)==0x5543);
    i960_write16(b->cpu,0x1d87ff2,0);
    assert(i960_read16(b->cpu,0x1d87ff8)==0x2020);
    puts("Dynamite Cop native protection widths/pages/aliases/reset and fresh-device continuation passed");
    m2_reset(b);memset(b->tgp_prog,0,0x40000);
    b->tgp.prog_upload_ctrl=0x80000000;b->tgp.prog_upload_off=0x40000;
    i960_write32(b->cpu,0x980000,0);
    size_t capacity=16u*1024u*1024u;uint8_t *largest=zero(capacity);
    m2_state maximum={largest,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&maximum);
    assert(!maximum.failed);
    printf("TGPX4 maximum upload: %zu machine bytes of %zu-byte frontend capacity\n",maximum.pos,capacity);
    free(largest);
    m2_destroy(b);
    puts("Model 2C i960 mapping/upload/FIFO/shared-memory synthetic integration and complete-state replacement/validation passed (3 resets)");
    return 0;
}
