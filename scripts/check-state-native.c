/* Regression: writable guest code can differ from the warm predecode cache. */
#include "i960/i960.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void put(uint8_t *p,uint32_t v) {memcpy(p,&v,4);}
int main(void) {
    uint8_t *rom=calloc(1,0x10000),*code=calloc(1,0x10000),*bytes=malloc(0x100000);
    i960_state *s=malloc(sizeof *s);assert(rom && code && bytes && s);
    put(rom+4,0x800);put(rom+12,0x200000);put(rom+0x818,0x4000);
    put(code,0x90203000);put(code+4,0x200100); /* ld absolute,r4 */
    put(code+0x100,5);put(code+0x104,9);
    i960_init(s,NULL);i960_map_read(s,0,0xffff,rom,NULL,NULL,NULL);
    i960_map_read(s,0x200000,0x20ffff,code,NULL,NULL,NULL);
    assert(!i960_set_code_region(s,0,0,0x10000));
    assert(!i960_set_code_region(s,1,0x200000,0x10000));
    assert(!i960_set_code_region(s,2,0x500000,0));
    i960_reset(s);assert(s->region[1].valid);
    put(code+4,0x200104); /* Same opcode; displacement RAM changed after predecode. */
    m2_state state={bytes,0x100000,0,M2_STATE_SAVE,0};i960_state_archive(s,&state);assert(!state.failed);
    size_t size=state.pos;int first_cycles=i960_step(s);assert(s->r[4]==5);
    state=(m2_state){bytes,size,0,M2_STATE_CHECK,0};i960_state_archive(s,&state);assert(!state.failed && state.pos==size);
    state=(m2_state){bytes,size,0,M2_STATE_LOAD,0};i960_state_archive(s,&state);assert(!state.failed);
    assert(i960_step(s)==first_cycles && s->r[4]==5);
    uint32_t raw;memcpy(&raw,code+4,4);assert(raw==0x200104);
    i960_free(s);free(s);free(bytes);free(code);free(rom);
    puts("PASS: warm writable i960 cache survives changed backing RAM with rebound operands and identical cycle charge");
}
