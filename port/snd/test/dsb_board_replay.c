/* Feed the two native ROM regions on stdin. Return track 1 interleaved PCM
 * before and after a fresh-board restore with a stop command half received. */
#include "../dsb_board.h"
#include <stdio.h>
#include <stdlib.h>

static uint8_t *read_region(size_t *size)
{
    uint32_t length;
    if (fread(&length, sizeof length, 1, stdin) != 1 || !length) return NULL;
    uint8_t *region = malloc(length);
    if (!region || fread(region, 1, length, stdin) != length) {
        free(region);
        return NULL;
    }
    *size = length;
    return region;
}

static int write_blocks(m2_dsb_board *board, unsigned blocks)
{
    while (blocks--) {
        int16_t pcm[760 * 2] = {0};
        m2_dsb_board_mix(board, pcm, 760);
        if (m2_dsb_board_error(board, NULL) ||
            fwrite(pcm, sizeof pcm, 1, stdout) != 1) return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "1") && strcmp(argv[1], "2"))) return 1;
    unsigned kind = (unsigned)(argv[1][0] - '0');
    size_t program_size = 0, music_size = 0;
    uint8_t *program = read_region(&program_size);
    uint8_t *music = read_region(&music_size);
    m2_dsb_board *board = m2_dsb_board_create(kind, program, program_size, music, music_size);
    int success = 0;
    if (!board) goto done;
    uint8_t prefix = kind == 1 ? 0xaf : 0xae;
    m2_dsb_board_command(board, prefix);
    m2_dsb_board_command(board, kind == 1 ? 0x6f : 0x10);
    m2_dsb_board_command(board, 1);
    if (!write_blocks(board, 16)) goto done;
    m2_dsb_board_command(board, prefix);
    m2_dsb_board_command(board, 3);
    uint8_t snapshot[16384];
    m2_state archive = {snapshot, sizeof snapshot, 0, M2_STATE_SAVE, 0};
    m2_dsb_board_archive(board, &archive);
    if (archive.failed) goto done;
    free(board);
    board = m2_dsb_board_create(kind, program, program_size, music, music_size);
    if (!board) goto done;
    archive.size = archive.pos;
    for (int mode = M2_STATE_CHECK; mode <= M2_STATE_LOAD; ++mode) {
        archive.mode = mode;
        archive.pos = 0;
        m2_dsb_board_archive(board, &archive);
        if (archive.failed || archive.pos != archive.size) goto done;
    }
    if (!write_blocks(board, 8)) goto done;
    m2_dsb_board_command(board, 0);
    int16_t output[760 * 2] = {0};
    m2_dsb_board_mix(board, output, 760);
    for (unsigned i = 0; i < 760 * 2; ++i)
        if (output[i]) goto done;
    success = !m2_dsb_board_error(board, NULL) && fflush(stdout) == 0;
done:
    free(board);
    free(music);
    free(program);
    return !success;
}
