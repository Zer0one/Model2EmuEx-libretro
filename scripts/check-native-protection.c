/* ROM-free native installer/map/state integration, not a decryptor test. */
#include "m2/m2board.h"
#include "m2/m2protection.h"
#include "state.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const m2_rom_entry roms[]={
    {0,NULL,0,0x40000,0,0,0},{0,NULL,1,0x10000,0,0,0},
    {0,NULL,2,0x10000,0,0,0},{4,NULL,0,1,0,0,0},{-1,NULL,0,0,0,0,0}};
static void installed(const m2_board *b) {
    const i960_insn *p=b->cpu->region[0].cache;
    switch(b->game->hook_addr) {
    case 0x4c7e90:
        assert(!strcmp(p[0x630/4].op->name,"(nop)"));
        assert(!strcmp(p[0x808/4].op->name,"(nop)"));
        assert(!strcmp(p[0x27e0/4].op->name,"(stop)"));break;
    case 0x4c7f30:assert(!strcmp(p[0x730/4].op->name,"(nop)"));break;
    case 0x4c8000:assert(!strcmp(p[0x700/4].op->name,"(nop)"));break;
    }
}
static unsigned slices;
static void check_slice(void *ctx) { m2_board *b=ctx;assert(b->cpu->stop==(b->game->hook_addr!=0x4c7e90));slices++; }
static int stop_slice(void *ctx,int cycles) { (void)cycles;((m2_board *)ctx)->cpu->stop=1;return 0; }
int main(void) {
    const char *dirs[]={NULL};
    for(unsigned k=0;k<4;k++) {
        const uint32_t hooks[]={0x4c7e90,0x4c7f30,0x4c7fa0,0x4c8000};
        m2_game game={.name="native_protection_fixture",.fps=60,.roms=roms,
            .hook=M2_HOOK_UNKNOWN,.hook_addr=hooks[k]};
        m2_board *b=m2_create(&game,dirs,NULL);assert(b && m2_protection_present(b));installed(b);
        b->cpu_execute=stop_slice;b->cpu_ctx=b;
        b->hooks.user=b;b->hooks.slice_done=check_slice;slices=0;m2_run_frame(b);
        assert(slices==210);b->cpu_execute=NULL;b->cpu_ctx=NULL;b->hooks=(m2_hooks){0};
        for(uint32_t page=0x1d8;page<0x1e0;page++) {
            assert(i960_read8(b->cpu,page<<16)==0xff);
            assert(i960_read32(b->cpu,page<<16)==0xffff);
        }
        assert(i960_read16(b->cpu,0x1d90000)==0);
        assert(i960_read16(b->cpu,0x1d8400c)==0xffff);
        assert(i960_read16(b->cpu,0x1d8400c)==0xfff0);
        i960_write8(b->cpu,0x1d90008,5);assert(!b->protection_selector);
        i960_write32(b->cpu,0x1d90008,5);assert(!b->protection_selector);
        i960_write16(b->cpu,0x1d90008,3);assert(b->protection_selector==3);
        i960_write16(b->cpu,0x1d9000c,0x1326);
        assert(i960_read16(b->cpu,0x1d9000e)==0); /* native word zero is retained */
        assert(i960_read16(b->cpu,0x1d9000e)==0x4366);
        i960_write16(b->cpu,0x1d9000c,0x7140);
        assert(i960_read16(b->cpu,0x1d87ff8)==0);
        assert(i960_read16(b->cpu,0x1d87ff8)==0x3938);
        i960_write16(b->cpu,0x1d87ff2,0);
        assert(i960_read16(b->cpu,0x1d9000e)==0x2020);
        i960_write16(b->cpu,0x1d9000c,0x10);
        assert(!b->protection_fault);
        uint8_t *state=calloc(1,12u<<20);assert(state);
        m2_state save={state,12u<<20,0,M2_STATE_SAVE,0};m2_state_archive(b,&save);assert(!save.failed);
        const unsigned cursor=b->protection_index;
        m2_state check={state,save.pos,0,M2_STATE_CHECK,0};m2_state_archive(b,&check);
        assert(!check.failed && b->protection_index==cursor);
        uint32_t expected[12];for(unsigned i=0;i<12;i++)expected[i]=i960_read16(b->cpu,0x1d9000e);
        m2_state load={state,save.pos,0,M2_STATE_LOAD,0};m2_state_archive(b,&load);assert(!load.failed);installed(b);
        for(unsigned i=0;i<12;i++)assert(i960_read16(b->cpu,0x1d9000e)==expected[i]);
        /* A read beyond the recovered response allocation stops explicitly. */
        b->protection_index=128;i960_read16(b->cpu,0x1d9000e);
        assert(b->protection_fault && b->protection_fault_address==0x5aa870);
        const unsigned selector=b->protection_selector;
        m2_reset(b);assert(!b->protection_fault && b->protection_selector==selector);installed(b);
        /* Native table selector beyond the recovered source is not clamped. */
        i960_write16(b->cpu,0x1d90008,366);i960_write16(b->cpu,0x1d9000c,0x10);
        assert(b->protection_fault && b->protection_fault_address==0x574f88);
        free(state);m2_destroy(b);
    }
    puts("PASS: four native installers, mapped byte/word/long exchanges, exact cache patches, pending protection state/preflight/continuation, warm reset and explicit memory bounds");
    return 0;
}
