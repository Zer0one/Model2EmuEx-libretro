/* ROM-free Model 2/2A integration through the production i960 memory map.
 * Fixture convention matches SHARC/TGPx4 check_machine.c; the uploaded FIFO
 * program is the one already compared with ElSemi in boardtest.py. */
#include "../../m2/m2board.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *zero(size_t n) { void *p=calloc(1,n); assert(p); return p; }
static m2_board *board(unsigned type)
{
    static const m2_game game={.name="synthetic",.fps=60};
    m2_board *b=zero(sizeof *b); b->type=type; b->game=&game;
    b->cpu=zero(sizeof *b->cpu);
#define MEM(name,bytes) b->name=zero(bytes)
    MEM(ram,0x100000); MEM(fb,0x80000); MEM(ram2,0x40000); MEM(pal,0x10000);
    MEM(cg,0x100000); MEM(tile,0x10000); MEM(back,0x18000); MEM(xlat,0x10004);
    MEM(luma,0x20004); MEM(bufram,0x80004); MEM(tgp_prog,0x40000); MEM(tgp_data,0x40000);
    MEM(coproram,0x40000); MEM(tex0,0x100004); MEM(tex1,0x100004); MEM(zshared,0x18000); MEM(scsp,0x10000);
#undef MEM
    b->rom.ptr[0]=zero(0x40000); b->rom.size[0]=0x40000;
    b->rom.ptr[1]=zero(0x10000); b->rom.size[1]=0x10000;
    b->rom.ptr[2]=zero(0x10000); b->rom.size[2]=0x10000;
    m2_reset(b); return b;
}
static void command_received(void *user, uint8_t command)
{
    uint8_t *received = user;
    *received = command;
}

static void check_sound_ports(m2_board *b)
{
    uint8_t delivered = 0;
    b->hooks.user = &delivered;
    b->hooks.sound_command = command_received;
    const uint32_t bases[] = {0x9c0000, 0x1c80000};
    const unsigned offsets[] = {0, 2, 4, 0x100, 0x102, 0xff};
    for (unsigned i = 0; i < 2; i++) {
        for (unsigned width = 1; width <= 4; width *= 2) {
            for (unsigned j = 0; j < sizeof offsets / sizeof offsets[0]; j++) {
                uint32_t addr = bases[i] + offsets[j];
                uint32_t data = 0xa9724d16u + width * 31 + j;
                int accepted = (addr & 255) == 0;
                b->sound_irqs = b->sound_count = UINT32_MAX;
                b->sound_word = 0x98b74d21;
                uint8_t next = b->sound_wr;
                delivered = 0;
                if (width == 1) i960_write8(b->cpu, addr, data);
                if (width == 2) i960_write16(b->cpu, addr, data);
                if (width == 4) i960_write32(b->cpu, addr, data);
                assert(delivered == (accepted ? (uint8_t)data : 0));
                assert(b->sound_irqs == (accepted ? 0 : UINT32_MAX));
                assert(b->sound_count == b->sound_irqs);
                assert(b->sound_word == (accepted && width == 4 ? data : 0x98b74d21));
                if (accepted && !b->type) assert(b->sound_fifo[next] == (uint8_t)data);
                assert(b->sound_wr == ((next + (accepted && !b->type)) & 31));
                b->sound_count = 1;
                unsigned status = (addr & 255) == 2 || (addr & 255) == 4;
                uint32_t value;
                if (width == 1) value = i960_read8(b->cpu, addr);
                else if (width == 2) value = i960_read16(b->cpu, addr);
                else value = i960_read32(b->cpu, addr);
                assert(value == (status ? 7 : 255));
                assert(b->sound_count == status);
            }
        }
    }
    b->hooks.user = NULL;
    b->hooks.sound_command = NULL;
}

int main(void)
{
    for (unsigned type=0; type<2; ++type) {
        m2_board *b=board(type);
        check_sound_ports(b);
        /* No direct FIFO injection: upload and execute through board ports. */
        static const uint32_t copy[]={
            0x1c000000 | (0x13 << 21) | (0x1f << 16) | (0x22 << 9) | 0x21,
            (0x2fu << 26) | (0x16 << 20)};
        i960_write32(b->cpu,0x980000,0x80000000);
        for (unsigned i=0; i<2; ++i) i960_write32(b->cpu,0x884000,copy[i]);
        i960_write32(b->cpu,0x980000,0);
        for (unsigned i=0; i<40; ++i) {
            uint32_t v=0x12345678u+i*0x1020304u;
            i960_write32(b->cpu,0x884000,v);
            assert(i960_read32(b->cpu,0x884000)==v);
        }
        /* Native Model 2/2A command port encodes the address, not write data. */
        i960_write32(b->cpu,0x880120,0xdeadbeef);
        assert(i960_read32(b->cpu,0x884000)==((0x12u<<23)|(0x12u<<8)|0x12u));
        memset(b->bufram_dirty,0,sizeof b->bufram_dirty);
        i960_write32(b->cpu,0x801008,0);
        i960_write32(b->cpu,0x800010,0x1234);
        assert(i960_read32(b->cpu,0x900000)==0x801234 && b->bufram_dirty[0]);
        assert(i960_read32(b->cpu,0x802008)==4);
        i960_write32(b->cpu,0x980008,0x80000000);
        i960_write32(b->cpu,0x804000,0x12345678);
        i960_write32(b->cpu,0x980008,0);
        assert(!memcmp(b->tgp_data,"\x78\x56\x34\x12",4));
        /* Pending output must survive replacement of the complete machine,
         * including program, FIFO indices and host-memory pointer rebinding. */
        i960_write32(b->cpu,0x884000,0xaabbccdd);
        size_t cap=12u*1024u*1024u;
        uint8_t *saved=zero(cap), *again=zero(cap);
        m2_state a={saved,cap,0,M2_STATE_SAVE,0}; m2_state_archive(b,&a);
        assert(!a.failed); size_t used=a.pos;
        a=(m2_state){saved,used,0,M2_STATE_CHECK,0}; m2_state_archive(b,&a);
        assert(!a.failed && a.pos==used);
        m2_destroy(b); b=board(type);
        a=(m2_state){saved,used,0,M2_STATE_LOAD,0}; m2_state_archive(b,&a); assert(!a.failed);
        a=(m2_state){again,cap,0,M2_STATE_SAVE,0}; m2_state_archive(b,&a);
        assert(!a.failed && a.pos==used && !memcmp(saved,again,used));
        assert(i960_read32(b->cpu,0x884000)==0xaabbccdd);
        i960_write32(b->cpu,0x884000,0x11223344);
        assert(i960_read32(b->cpu,0x884000)==0x11223344);
        assert(i960_read32(b->cpu,0x900000)==0x801234);
        free(saved); free(again); m2_destroy(b);
        printf("Model 2%s: upload, 43 FIFO transfers, shared/data RAM, fresh-machine state passed\n",type?"A":"");
    }
    return 0;
}
