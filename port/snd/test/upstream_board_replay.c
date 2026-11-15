/* Build against pristine Model2EmuEx. stdin carries two little-endian sized
 * ROM regions followed by per-frame command counts/bytes. stdout is raw PCM. */
#include "m2/m2board.h"
#include "snd/m2snd.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    static m2_board board;
    if (argc != 2 || (argv[1][0] != '0' && argv[1][0] != '1') || argv[1][1]) return 1;
    board.type = argv[1][0] - '0';
    for (unsigned region = 5; region <= 6; ++region) {
        uint8_t bytes[4];
        if (fread(bytes, 1, 4, stdin) != 4) return 1;
        uint32_t size = bytes[0] | bytes[1] << 8 | bytes[2] << 16 | (uint32_t)bytes[3] << 24;
        board.rom.ptr[region] = malloc(size);
        board.rom.size[region] = size;
        if (!board.rom.ptr[region] || fread(board.rom.ptr[region], 1, size, stdin) != size) return 1;
    }
    m2_snd *sound = m2snd_create(&board);
    if (!sound) return 1;
    double debt = 0;
    int count;
    while ((count = getchar()) != EOF) {
        int16_t pcm[2 * 761];
        debt += M2SND_RATE / 58.0;
        int frames = (int)debt;
        debt -= frames;
        m2snd_render(sound, pcm, frames);
        if (fwrite(pcm, sizeof(*pcm) * 2, frames, stdout) != (size_t)frames) return 1;
        while (count--) {
            int command = getchar();
            if (command == EOF) return 1;
            m2snd_command(sound, (uint8_t)command);
        }
    }
    m2snd_destroy(sound);
    free(board.rom.ptr[5]);
    free(board.rom.ptr[6]);
    return ferror(stdin) || fflush(stdout) != 0;
}
