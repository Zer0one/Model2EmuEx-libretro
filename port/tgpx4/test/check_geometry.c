/* Synthetic mixed display list: special triangles/quads, both matrix banks,
 * argument-free restore, ordinary objects and archived continuation. No ROMs. */
#include "../../m2/m2geo.h"
#include "../../m2/m2board.h"
#include "../../m2/m2tgpx4.h"
#include "../../m2/m2pipe.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Driver binding is independently exercised by check-tgpx4-machine. */
int m2tgpx4_dual_matrix(const m2_board *board) { return board->tgpx4_geometry_dual; }
uint32_t m2tgpx4_center_mode(const m2_board *board) { return board->tgpx4_geometry_center_mode; }
static unsigned seen;
static unsigned sizes[8];
static float xs[8][4];
static void capture(void *opaque, const m2_geo *geo, const m2_gvert *v, int n,
                    const uint16_t th[4], uint8_t luma)
{
    (void)opaque; (void)geo; (void)th; (void)luma;
    assert(seen < 8);
    sizes[seen] = (unsigned)n;
    for (int i = 0; i < n; ++i) xs[seen][i] = v[i].x;
    ++seen;
}
static uint32_t bits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static void point(uint32_t **p, float x, float y, int alternate)
{
    *(*p)++ = bits(x) | (uint32_t)alternate;
    *(*p)++ = bits(y);
    *(*p)++ = bits(10);
}
static void matrix(uint32_t **p, unsigned cmd, float translation)
{
    *(*p)++ = cmd << 23;
    for (unsigned i = 0; i < 12; ++i)
        *(*p)++ = bits(i == 0 || i == 4 || i == 8 ? 1 : i == 9 ? translation : 0);
}
static void object(uint32_t **p, unsigned cmd, unsigned address)
{
    *(*p)++ = cmd << 23;
    *(*p)++ = 0x800000; *(*p)++ = 0x800000;
    *(*p)++ = address; *(*p)++ = 0;
}
int main(void)
{
    m2_board *board = calloc(1, sizeof *board);
    m2_geo *geo = m2geo_create();
    assert(board && geo);
    board->bufram = calloc(1, 0x80000);
    assert(board->bufram);
    board->type = 3;
    static const m2_game game = { .name = "topskatr" };
    board->game = &game;
    board->tgpx4_geometry_dual = 1;
    board->tgpx4_geometry_center_mode = 3;
    geo->dump = capture;
    geo->focus_x = geo->focus_y = 1;
    uint32_t *poly = geo->poly_ram[0];
    point(&poly, 2, 0, 0); point(&poly, 4, 0, 1);
    *poly++ = 0x20202; /* drawn, two-sided triangle; no normal or fourth point */
    point(&poly, 6, 1, 1);
    *poly++ = 0x20203; /* immediately following quad; would desync old parser */
    point(&poly, 8, 1, 0); point(&poly, 10, 2, 1);
    *poly++ = 0;
    /* Ordinary triangle still carries a normal and an unused fourth point. */
    poly = geo->poly_ram[0] + 64;
    point(&poly, 2, 0, 0); point(&poly, 4, 0, 0);
    *poly++ = 0x20202;
    *poly++ = 0; *poly++ = 0; *poly++ = bits(1);
    point(&poly, 6, 1, 0); point(&poly, 99, 99, 0);
    *poly++ = 0; *poly++ = 0; *poly++ = 0; *poly++ = 0;

    uint32_t *list = (uint32_t *)board->bufram;
    matrix(&list, 0x0b, 0);
    matrix(&list, 0x1b, 16);
    object(&list, 0x11, 0);
    *list++ = 0x1c << 23; /* restore: the next word is already another opcode */
    object(&list, 0x11, 0);
    object(&list, 0x01, 64);
    *list++ = 0x0f << 23;
    m2geo_run(geo, board);
    assert(seen == 5 && sizes[0] == 3 && sizes[1] == 4 && sizes[4] == 3);
    assert(xs[0][0] >= 20 && xs[0][0] < 20.001f && xs[0][1] == 2);
    assert(xs[0][2] >= 22 && xs[0][2] < 22.001f);
    assert(xs[1][2] == 8 && xs[1][3] >= 26 && xs[1][3] < 26.001f);
    assert(xs[2][0] > 4 && xs[2][0] < 4.001f && xs[2][1] == 2);
    assert(xs[4][0] == 4 && xs[4][1] == 2 && xs[4][2] == 6);

    /* Opposing low/high selectors prove that Model 2C uses bits 6..7,
     * while the other board path still uses bits 29..30. */
    for(unsigned center=0;center<4;center++) {
        list=(uint32_t *)board->bufram;
        object(&list,0x01,64);*list++=0x0f<<23;
        ((uint32_t *)board->bufram)[0] |= (center<<6) | ((3-center)<<29);
        board->type=3;seen=0;m2geo_run(geo,board);assert(geo->center_sel==(int)center);
        board->type=1;seen=0;m2geo_run(geo,board);assert(geo->center_sel==(int)(3-center));
    }
    board->type=3;
    /* Save after a matrix-only list, then use it from the next list. */
    list = (uint32_t *)board->bufram;
    matrix(&list, 0x1b, 32); *list++ = 0x0f << 23;
    m2geo_run(geo, board);
    size_t capacity = sizeof *geo;
    uint8_t *blob = malloc(capacity);
    assert(blob);
    m2_state save = {blob, capacity, 0, M2_STATE_SAVE, 0};
    m2geo_state_archive(geo, &save);
    m2geo_tgpx4_state_archive(geo, &save);
    assert(!save.failed);
    memset(geo->alternate_matrix, 0, sizeof geo->alternate_matrix);
    m2_state check = {blob, save.pos, 0, M2_STATE_CHECK, 0};
    m2geo_state_archive(geo, &check);
    m2geo_tgpx4_state_archive(geo, &check);
    assert(!check.failed && check.pos == save.pos);
    m2_state load = {blob, save.pos, 0, M2_STATE_LOAD, 0};
    m2geo_state_archive(geo, &load);
    m2geo_tgpx4_state_archive(geo, &load);
    assert(!load.failed && geo->alternate_matrix[9] == 32);
    list = (uint32_t *)board->bufram;
    object(&list, 0x11, 0); *list++ = 0x0f << 23;
    seen = 0; m2geo_run(geo, board);
    assert(seen == 2 && xs[0][0] >= 36 && xs[0][0] < 36.001f);
    /* The render-side board intentionally has no live CPU binding. */
#define VIDEO_ALLOC(field, size) board->field = calloc(1, size); assert(board->field)
    VIDEO_ALLOC(tile, 0x10000); VIDEO_ALLOC(pal, 0x4000);
    VIDEO_ALLOC(xlat, 0x10004); VIDEO_ALLOC(luma, 0x20004);
    VIDEO_ALLOC(cg, 0x80000); VIDEO_ALLOC(tex0, 0x100004); VIDEO_ALLOC(tex1, 0x100004);
#undef VIDEO_ALLOC
    m2_pipe *pipe = m2pipe_create(); assert(pipe);
    m2pipe_attach(pipe, board);
    m2pipe_capture(pipe, board);
    board->tgpx4_geometry_dual = 0; /* Next frame must not change the first. */
    board->tgpx4_geometry_center_mode = 2;
    m2pipe_capture(pipe, board);
    m2_hooks hooks = { 0 };
    const m2_board *view = m2pipe_apply(pipe, &hooks, NULL);
    assert(view->tgpx4_geometry_center_mode==3);
    assert(view->tgpx4 == NULL && view->tgpx4_geometry_dual == 1);
    seen = 0; m2geo_run(geo, view);
    assert(seen == 2 && xs[0][0] >= 36 && xs[0][0] < 36.001f);
    view = m2pipe_apply(pipe, &hooks, NULL);
    assert(view->tgpx4_geometry_dual == 0);
    m2pipe_destroy(pipe);
    /* Native special winding: negative normal dot is visible. Exercise the
     * actual culler too, since dump mode deliberately bypasses it. */
    board->tgpx4_geometry_dual = 1;
    geo->dump = NULL;
    geo->poly_ram[0][6] &= ~0x20000u; /* Single-sided. */
    list = (uint32_t *)board->bufram;
    object(&list, 0x11, 0); list[-1] = 1; *list++ = 0x0f << 23;
    m2geo_run(geo, board);
    assert(geo->npolys == 1);
    geo->poly_ram[0][8] = bits(-1); /* Reverse the triangle's winding. */
    m2geo_run(geo, board);
    assert(geo->npolys == 0);
    free(board->tile); free(board->pal); free(board->xlat); free(board->luma);
    free(board->cg); free(board->tex0); free(board->tex1);
    free(blob); free(board->bufram); free(board); m2geo_destroy(geo);
    puts("Top Skater polygon grammar, dual matrices, state continuation and pipeline snapshots passed");
    return 0;
}
