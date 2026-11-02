/* ROM-free regression through the native I/O pins, including command framing. */
#include "../port/m2/m2board.c"
#include <assert.h>

static void pins(m2_board *b, unsigned bits)
{
    io_write8(b, 0, (uint8_t)(1 | bits));
}
static void begin(m2_board *b)
{
    pins(b, 0); pins(b, 0x40);
}
static void bit(m2_board *b, unsigned value)
{
    unsigned data = 0x40 | (value ? 0x20 : 0);
    pins(b, data); pins(b, data | 0x80);
}
static void bits(m2_board *b, uint32_t value, unsigned count)
{
    while (count) bit(b, (value >> --count) & 1);
}
static uint16_t read_word(m2_board *b, unsigned address, unsigned idle)
{
    begin(b);
    bits(b, 0, idle); bits(b, 6, 3); bits(b, address, 6);
    uint16_t word = 0;
    for (unsigned i = 0; i < 16; ++i) {
        bit(b, 0);
        word = (uint16_t)((word << 1) | ((io_read(b, 2) >> 5) & 1));
    }
    pins(b, 0);
    return word;
}
int main(void)
{
    m2_board *b = calloc(1, sizeof *b); assert(b);
    ee_init(&b->eeprom);
    st16(b->eeprom.data + 8, 0x0201); /* Export + Advertise Sound On. */
    for (unsigned idle = 0; idle < 8; ++idle)
        assert(read_word(b, 4, idle) == 0x0201);
    /* Enable writes, then write and re-read a word with idle clocks. */
    begin(b); bits(b, 0, 3); bits(b, 0x13, 5); pins(b, 0);
    begin(b); bits(b, 0, 2); bits(b, 5, 3); bits(b, 5, 6);
    bits(b, 0xa65c, 16); pins(b, 0);
    assert(read_word(b, 5, 4) == 0xa65c);
    /* Chip-select reset must abandon an incomplete command. */
    begin(b); bits(b, 6, 3); bits(b, 1, 2); pins(b, 0);
    assert(read_word(b, 4, 2) == 0x0201);
    /* The original Model 2 keeps an additional low-byte-lane settings
       image behind its I/O interface. Synchronize only reviewed settings. */
    m2_game game={0};game.name="daytona";b->game=&game;b->type=0;
    b->back=malloc(0x18000);assert(b->back);memset(b->back,0xa5,0x18000);
    memcpy(b->back,"SEGA@",5);b->back[11]=2;b->back[12]=1;
    daytona_settings_crc(b->back);memcpy(b->back+128,b->back,128);
    assert(m2_nvram_sync_settings_io(b));
    for(unsigned i=0;i<128;i++) {
        assert(io_read(b,0x200+i*2)==b->back[i]);
        assert(b->back[0x8001+i*2]==0xa5);
    }
    assert(b->back[0x8100]==0xa5);
    b->back[11]^=1;assert(!m2_nvram_sync_settings_io(b));
    b->manxtt_audio=1;b->port[2]=0x5a;b->eeprom.data[10]=1;
    io_write8(b,8,0x3d);assert(io_read(b,6)==0x5a);
    b->eeprom.data[10]=0;assert(io_read(b,6)==0xff);
    io_write8(b,8,0x3d);assert(io_read(b,6)==0xce);
    io_write16(b,8,0x7f);assert(io_read(b,6)==0xcd);
    b->eeprom.data[10]=1;assert(io_read(b,6)==0x5a);
    b->eeprom.data[10]=0;assert(io_read(b,6)==0xff);
    free(b->back);
    free(b);
    puts("Native I/O: PASS (93C46 idle/read/write/interruption; validated Daytona settings lane synchronization; Manx TT AMS Twin/Deluxe handshake/reset)");
    return 0;
}
