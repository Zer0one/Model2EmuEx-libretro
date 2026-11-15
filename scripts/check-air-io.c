/* Air Walkers' added physical I/O wiring through the native i960 bus. */
#include "m2/m2board.h"
#include "state.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const m2_rom_entry roms[]={
 {0,NULL,0,0x40000,0,0,0},{0,NULL,1,0x10000,0,0,0},
 {0,NULL,2,0x10000,0,0,0},{4,NULL,0,1,0,0,0},{-1,NULL,0,0,0,0,0}};
int main(void) {
 const char *dirs[]={NULL};m2_game game={.name="airwlkrs",.fps=60,.roms=roms};
 m2_board *b=m2_create(&game,dirs,NULL);assert(b && b->io_extension);
 assert(i960_read8(b->cpu,0x1c00000)==0);
 i960_write8(b->cpu,0x1c00000,0x40);assert(i960_read8(b->cpu,0x1c00000)==0x40);
 i960_write16(b->cpu,0x1c00000,0);i960_write16(b->cpu,0x1c00010,0x7e);
 assert(b->io_direction==0x7e && !b->eeprom_select);
 b->port[0]=0xff;b->port[1]=0x57;b->port[2]=0xab;b->port[3]=0x39;b->port[4]=0xce;
 b->io_starts=9;b->io_dips=0xa5;
 assert(i960_read8(b->cpu,0x1c00002)==0xdf);
 assert(i960_read8(b->cpu,0x1c00004)==0x57 && i960_read8(b->cpu,0x1c00006)==0xab);
 i960_write8(b->cpu,0x1c0000a,0x80);
 assert(i960_read8(b->cpu,0x1c00002)==0xef);
 assert(i960_read8(b->cpu,0x1c00004)==0x39 && i960_read8(b->cpu,0x1c00006)==0xce);
 assert(i960_read8(b->cpu,0x1c0000c)==0xa5);
 assert(i960_read8(b->cpu,0x1c0001a)==0x0c && i960_read8(b->cpu,0x1c00016)==0);
 i960_write8(b->cpu,0x1c0001c,3);assert(b->io_mode==3);
 uint8_t *bytes=calloc(1,12u<<20);assert(bytes);
 m2_state save={bytes,12u<<20,0,M2_STATE_SAVE,0};m2_state_archive(b,&save);assert(!save.failed);
 m2_reset(b);assert(!b->io_direction && !b->io_latch[5]);
 m2_state load={bytes,save.pos,0,M2_STATE_LOAD,0};m2_state_archive(b,&load);assert(!load.failed);
 assert(b->io_direction==0x7e && b->io_latch[5]==0x80 && b->io_mode==3);
 assert(i960_read8(b->cpu,0x1c00004)==0x39 && i960_read8(b->cpu,0x1c00006)==0xce);
 i960_write8(b->cpu,0x1c00010,0);i960_write8(b->cpu,0x1c00004,0x1b);
 assert(i960_read8(b->cpu,0x1c00004)==0x1b);
 i960_write32(b->cpu,0x1c00004,0x002d003c);
 assert(i960_read32(b->cpu,0x1c00004)==0x002d003c);
 i960_write16(b->cpu,0x1c00000,1);assert(b->eeprom_select && b->io_latch[0]==1);
 free(bytes);m2_destroy(b);
 puts("PASS: Air Walkers output readback/directions, four-player port-F matrix, independent Starts/DIPs, serial status, reset and exact matrix state restoration");
 return 0;
}
