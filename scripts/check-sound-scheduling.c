/* ROM-free sound CPU fixture: audio timing must not depend on callback size. */
#include "m2/m2board.h"
#include "snd/m2snd.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t program[0x200];
static unsigned pc;
static void word(uint16_t v)
{
    /* Program region uses the native A68K word-swapped layout. */
    program[pc++] = (uint8_t)v;
    program[pc++] = (uint8_t)(v >> 8);
}
static void write_word(uint32_t address, uint16_t value)
{
    word(0x33fc); word(value); word((uint16_t)(address >> 16)); word((uint16_t)address);
}
static void fixture(void)
{
    pc = 0;
    word(0x0007); word(0xff00); /* Initial stack. */
    word(0x0060); word(0x0100); /* Entry point. */
    pc = 0x100;
    write_word(0x004000, 0x6000); /* A nonzero PCM word in sound RAM. */
    write_word(0x100400, 0x000f); /* Master volume. */
    write_word(0x100002, 0x4000); /* Slot 0 start address. */
    write_word(0x100006, 0x0001); /* One-word forward loop. */
    write_word(0x100008, 0x001f); /* Immediate attack. */
    write_word(0x100016, 0xe000); /* Direct output, full level. */
    /* Key on after the first sample boundary, during a typical callback. */
    for (unsigned i = 0; i < 80; ++i) word(0x4e71); /* NOP, four CPU cycles. */
    write_word(0x100000, 0x1820); /* Key on and execute. */
    word(0x60fe);                /* BRA to itself. */
}
static int capture(unsigned chunk, int16_t *pcm)
{
    m2_board *board = calloc(1, sizeof *board);
    if (!board) return 0;
    board->type = 1;
    board->rom.ptr[5] = program;
    board->rom.size[5] = sizeof program;
    m2_snd *sound = m2snd_create(board);
    if (!sound) { free(board); return 0; }
    for (unsigned done = 0; done < 4096;) {
        unsigned n = chunk < 4096 - done ? chunk : 4096 - done;
        m2snd_render(sound, pcm + 2 * done, (int)n);
        done += n;
    }
    m2snd_destroy(sound);
    free(board);
    return 1;
}
int main(void)
{
    int16_t expected[4096 * 2], actual[4096 * 2];
    const unsigned chunks[] = {7, 16, 256, 735, 761, 2048};
    fixture();
    if (!capture(1, expected)) return 2;
    unsigned nonzero = 0;
    for (unsigned i = 0; i < 4096 * 2; ++i) nonzero += expected[i] != 0;
    if (!nonzero) { fprintf(stderr, "Synthetic SCSP fixture is silent\n"); return 2; }
    for (unsigned i = 0; i < sizeof chunks / sizeof chunks[0]; ++i) {
        if (!capture(chunks[i], actual)) return 2;
        if (memcmp(expected, actual, sizeof expected)) {
            fprintf(stderr, "SCSP PCM depends on callback size %u\n", chunks[i]);
            return 1;
        }
    }
    puts("SCSP callback-size invariance: PASS (1/7/16/256/735/761/2048 samples)");
    return 0;
}
