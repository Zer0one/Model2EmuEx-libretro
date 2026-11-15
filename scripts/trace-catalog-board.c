/* Isolated board/serial-I/O diagnostic through the actual Libretro adapter.
 * No GL context is created; this is machine execution, not rendered evidence. */
#include "../src/libretro/libretro.c"
#include <assert.h>
static const struct retro_core_option_v2_definition *diagnostic_definitions;
static i960_write_page original_io_write;
static unsigned commands,reads[16],io_writes;
static bool diagnostic_environment(unsigned command,void *data) {
    if(command==RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION) {*(unsigned *)data=2;return true;}
    if(command==RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2) {diagnostic_definitions=((struct retro_core_options_v2 *)data)->definitions;return true;}
    if(command==RETRO_ENVIRONMENT_GET_VARIABLE) {
        struct retro_variable *v=data;
        if(!strcmp(v->key,"model2emuex_pipeline")) {v->value="disabled";return true;}
        for(const struct retro_core_option_v2_definition *d=diagnostic_definitions;d && d->key;d++)
            if(!strcmp(v->key,d->key)) {v->value=d->default_value;return true;}
        return false;
    }
    if(command==RETRO_ENVIRONMENT_SET_HW_RENDER || command==RETRO_ENVIRONMENT_SET_PIXEL_FORMAT
        || command==RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS || command==RETRO_ENVIRONMENT_SET_CONTROLLER_INFO
        || command==RETRO_ENVIRONMENT_SET_CORE_OPTIONS_DISPLAY || command==RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME)return true;
    return false;
}
static size_t diagnostic_audio(const int16_t *p,size_t n) {(void)p;return n;}
static void poll_empty(void) {}
static int16_t input_empty(unsigned p,unsigned d,unsigned i,unsigned k) {(void)p;(void)d;(void)i;(void)k;return 0;}
static void trace_read(void *u,uint32_t a,uint32_t v) {(void)u;(void)v;if((a&0xffff)<32)reads[(a&31)/2]++;}
static void write_value(void *u,uint32_t a,uint32_t v,unsigned width) {
    m2_board *b=u;int before=b->eeprom.serial_count,sending=b->eeprom.sending;
    if(width==1)original_io_write.w8(u,a,v);
    if(width==2)original_io_write.w16(u,a,v);
    if(width==4)original_io_write.w32(u,a,v);
    io_writes++;
    if(commands<160 && ((!sending && b->eeprom.sending) ||
       (before<25 && b->eeprom.serial_count==25) ||
       (before>=4 && !b->eeprom.serial_count && !b->eeprom.sending))) {
        printf("EEPROM PC=%08x serial=%s count=%d sending=%d addr=%u value=%04x locked=%d\n",
            b->cpu->prev_ip,b->eeprom.serial_buffer,b->eeprom.serial_count,b->eeprom.sending,
            b->eeprom.read_address,b->eeprom.data_bits,b->eeprom.locked);commands++;
    }
}
static void write8(void *u,uint32_t a,uint8_t v) {write_value(u,a,v,1);}
static void write16(void *u,uint32_t a,uint16_t v) {write_value(u,a,v,2);}
static void write32(void *u,uint32_t a,uint32_t v) {write_value(u,a,v,4);}
static void invalid(void *u,uint32_t a,uint32_t v) {(void)u;printf("INVALID PC=%08x raw=%08x\n",a,v);}
int main(int argc,char **argv) {
    assert(argc==3);retro_set_environment(diagnostic_environment);retro_init();
    retro_set_audio_sample_batch(diagnostic_audio);retro_set_input_poll(poll_empty);retro_set_input_state(input_empty);
    struct retro_game_info content={.path=argv[1]};assert(retro_load_game(&content));
    original_io_write=board->cpu->wpage[0x1c0];
    board->cpu->wpage[0x1c0]=(i960_write_page){NULL,write8,write16,write32};
    board->cpu->invalid_opcode=invalid;board->hooks.io_read=trace_read;
    for(unsigned f=0;f<(unsigned)atoi(argv[2]);f++) {
        retro_run();
        if(f%60==0 || content_failed) {
            uint16_t pc;memcpy(&pc,board->tgp.blk+TGP_O_PC,2);
            printf("FRAME %u PC=%08x last=%08x op=%s stop=%u TGP=%04x upload=%u input_free=%d output_free=%d IOdir=%02x writes=%u\n",
                f,board->cpu->ip,board->cpu->prev_ip,board->cpu->cur && board->cpu->cur->op?board->cpu->cur->op->name:"-",
                board->cpu->stop,pc,board->tgp.prog_upload_off,board->tgp.in.free,board->tgp.out.free,board->io_direction,io_writes);
        }
        if(content_failed)break;
    }
    printf("I/O reads:");for(unsigned i=0;i<16;i++)printf(" %02x=%u",i*2,reads[i]);puts("");
    for(unsigned i=0;i<128;i+=16) {printf("EEP %02x:",i);for(unsigned j=0;j<16;j++)printf(" %02x",board->eeprom.data[i+j]);puts("");}
    bool failed=content_failed;retro_unload_game();retro_deinit();return failed?1:0;
}
