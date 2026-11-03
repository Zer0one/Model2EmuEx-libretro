/* Synthetic board integration through the real i960 memory map. */
#include "../../m2/m2board.h"
#include "../../m2/m2sharc.h"
#include "../sharc_device.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *zero(size_t n){void *p=calloc(1,n);assert(p);return p;}
int main(void) {
    static const m2_game game={.name="schamp",.fps=60};
    m2_board *b=zero(sizeof *b);b->type=2;b->game=&game;
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
    b->sharc=m2sharc_create(b);assert(b->sharc);
    for(unsigned repeat=0;repeat<2;repeat++) {
        m2_reset(b);
        assert(i960_read32(b->cpu,0x980004)==1);
        i960_write32(b->cpu,0x980000,0x80000000);
        i960_write16(b->cpu,0x884000,0xabcd);
        assert(b->tgp.prog_upload_off==4);
        assert(!memcmp(b->tgp_prog,"\xcd\xab\xcd\xab",4));
        /* Reset upload control to begin again, without a completion call. */
        b->tgp.prog_upload_ctrl=0;
        i960_write32(b->cpu,0x980000,0x80000000);
        static const uint16_t words[]={
            0,0,0, 0,0,0, 0,0,0, 0,0,0,
            0,0x40,0x1000, 0,0xc0,0x1100,
            0,0x40,0x1001, 4,2,0x063c
        };
        for(unsigned i=0;i<sizeof words/sizeof words[0];i++)i960_write32(b->cpu,0x884000,words[i]);
        assert(b->tgp.prog_upload_off==sizeof words);
        i960_write32(b->cpu,0x980000,0);
        i960_write32(b->cpu,0x880000,0x12345678);
        assert(i960_read32(b->cpu,0x980004)==0);
        assert(i960_read32(b->cpu,0x884000)==0x12345678);
        assert(i960_read32(b->cpu,0x980004)==1);
        /* Native shared-memory pointer, packed command and dirty tracking. */
        memset(b->bufram_dirty,0,sizeof b->bufram_dirty);
        i960_write32(b->cpu,0x801008,0);
        i960_write32(b->cpu,0x800010,0x1234);
        assert(i960_read32(b->cpu,0x900000)==0x801234);
        assert(i960_read32(b->cpu,0x802008)==4);
        assert(b->bufram_dirty[0]);
        i960_write32(b->cpu,0x803008,0x456);
        assert(i960_read32(b->cpu,0x803008)==0x456 && b->tgp.reg_803008==0x456);
        i960_write32(b->cpu,0x980008,0x80000000);
        i960_write32(b->cpu,0x804000,0x12345678);
        assert(b->tgp.data_upload_off==2 && b->tgp_data[0]==0x78 && b->tgp_data[1]==0x56);
        i960_write32(b->cpu,0x980008,0);
        /* Writable program RAM can diverge from the warm instruction cache. */
        b->tgp_prog[24]^=0x80;
        size_t capacity=16u*1024u*1024u;
        uint8_t *saved=zero(capacity),*again=zero(capacity);
        m2_state a={saved,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&a);assert(!a.failed);
        size_t used=a.pos;
        uint64_t hash=m2sharc_hash(b->sharc);
        uint8_t device_state[4096],bad_state[4096];
        m2_state device_archive={device_state,sizeof device_state,0,M2_STATE_SAVE,0};
        m2sharc_state_archive(b->sharc,&device_archive);assert(!device_archive.failed);
        size_t device_used=device_archive.pos;
        const size_t source_offset=8*4+sizeof(m2_sharc_execution)+sizeof(m2_sharc_board_configuration)+sizeof(m2_sharc_fp_state)+8*4;
        uint32_t records;memcpy(&records,device_state+4,4);
        const size_t cache_offset=source_offset+records*6;
        const size_t corrupt_offsets[]={0,4,8,12,16,20,24,28,32+sizeof(m2_sharc_execution)-4-5*4,cache_offset+4*108,cache_offset+4*108+9*4};
        for(unsigned i=0;i<sizeof corrupt_offsets/sizeof corrupt_offsets[0];i++) {
            memcpy(bad_state,device_state,device_used);bad_state[corrupt_offsets[i]]^=0xff;
            device_archive=(m2_state){bad_state,device_used,0,M2_STATE_CHECK,0};
            m2sharc_state_archive(b->sharc,&device_archive);
            assert(device_archive.failed && m2sharc_hash(b->sharc)==hash);
        }
        for(size_t limit=0;limit<device_used;limit++) {
            device_archive=(m2_state){device_state,limit,0,M2_STATE_CHECK,0};
            m2sharc_state_archive(b->sharc,&device_archive);
            assert(device_archive.failed && m2sharc_hash(b->sharc)==hash);
        }
        a=(m2_state){saved,used,0,M2_STATE_CHECK,0};m2_state_archive(b,&a);
        assert(!a.failed && a.pos==used && m2sharc_hash(b->sharc)==hash);
        i960_write32(b->cpu,0x880000,0xaabbccdd);
        uint32_t expected_output=i960_read32(b->cpu,0x884000);
        uint64_t expected_hash=m2sharc_hash(b->sharc);
        /* Restore after replacing the decoded program, not only after RAM
         * writes. This exercises reallocation and callback/FIFO rebinding. */
        m2_reset(b);
        a=(m2_state){saved,used,0,M2_STATE_LOAD,0};m2_state_archive(b,&a);assert(!a.failed);
        assert(m2sharc_hash(b->sharc)==hash);
        a=(m2_state){again,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&a);
        assert(!a.failed && a.pos==used && !memcmp(saved,again,used));
        i960_write32(b->cpu,0x880000,0xaabbccdd);
        assert(i960_read32(b->cpu,0x884000)==expected_output);
        assert(m2sharc_hash(b->sharc)==expected_hash);
        free(saved);free(again);
    }
    /* Largest native program upload fits the fixed SHARC frontend capacity. */
    m2_reset(b);memset(b->tgp_prog,0,0x40000);
    b->tgp.prog_upload_ctrl=0x80000000;b->tgp.prog_upload_off=0x40000;
    i960_write32(b->cpu,0x980000,0);
    size_t capacity=16u*1024u*1024u;uint8_t *largest=zero(capacity);
    m2_state maximum={largest,capacity,0,M2_STATE_SAVE,0};m2_state_archive(b,&maximum);
    assert(!maximum.failed);
    printf("SHARC maximum upload: %zu machine bytes of %zu-byte frontend capacity\n",maximum.pos,capacity);
    free(largest);
    m2_destroy(b);puts("SHARC machine: upload, FIFO execution, shared memory, reset, state replacement/rebinding and teardown passed");
    return 0;
}
