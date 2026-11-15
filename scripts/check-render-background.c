/* ROM-free GL regression: palette pen zero is the backdrop, bars stay black. */
#include "m2/m2gl.h"
#include "m2/m2glapi.h"
#include <SDL2/SDL.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static void pixel(int x, int y, uint32_t colour)
{
    uint8_t rgba[4];
    glReadPixels(x, y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
    for (unsigned channel = 0; channel < 3; ++channel) {
        int expected = (int)((colour >> (channel * 8)) & 255);
        assert(abs((int)rgba[channel] - expected) <= 1);
    }
}
static void draw(m2_gl *renderer, m2_tilegen *tiles, int scale)
{
    m2_view view = {.frame_w=496, .scale=scale, .fill=0, .saturation=1};
    /* No ROMs or machine table data: only the synthetic transparent layers. */
    m2gl_upload(renderer, NULL, tiles, 0);
    m2gl_draw(renderer, NULL, &view, 496, 420);
    pixel(248, 210, tiles->pal[0]);
    pixel(248, 4, 0); /* outside the 4:3 image */
    pixel(248, 415, 0);
}
/* Exercise decoded-colour filtering and the original priority alpha test.
 * Adjacent palette indices 1/2 must blend red and blue, never palette 1.25. */
static void filtering(m2_gl *renderer, m2_tilegen *tiles)
{
    m2_view view = {.frame_w=496, .scale=2, .fill=1, .saturation=1};
    tiles->pal[0] = 0xff00ff00;
    tiles->pal[1] = 0xff0000ff;
    tiles->pal[2] = 0xffff0000;
    for (int y = 0; y < M2_SCREEN_H; ++y) {
        for (int x = 0; x < M2_SCREEN_W; ++x) {
            tiles->layer[0][y*M2_SCREEN_W+x] = 0;
            tiles->layer[1][y*M2_SCREEN_W+x] = x < 248 ? 1 : 2;
        }
    }
    ++tiles->pal_version;
    ++tiles->layer_version;
    m2gl_invalidate(renderer);
    m2gl_upload(renderer, NULL, tiles, 0);
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, 0x000000ff);
    view.tile_filter = 1;
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, 0x004000bf);
    pixel(496, 300, 0x00bf0040);
    /* Transparent green carries alpha 255. At a low-priority boundary,
     * 25% transparency raises 119 to 153, beyond native threshold 144. */
    for (int y = 0; y < M2_SCREEN_H; ++y)
        for (int x = 248; x < M2_SCREEN_W; ++x)
            tiles->layer[1][y*M2_SCREEN_W+x] = 0;
    ++tiles->layer_version;
    m2gl_invalidate(renderer);
    m2gl_upload(renderer, NULL, tiles, 0);
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, 0x0000ff00);
    view.tile_filter = 0;
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, 0x000000ff);
    for (int layer = 0; layer < 2; ++layer)
        for (int i = 0; i < M2_SCREEN_W*M2_SCREEN_H; ++i)
            tiles->layer[layer][i] = 0;
    ++tiles->layer_version;
}
static void multisampling(m2_gl *renderer, m2_tilegen *tiles)
{
    /* The target desktop context must support the requested original 2x mode. */
    int available = m2gl_set_fsaa(renderer, 1, 496, 384);
    printf("Exact 2x FSAA on this context: %s\n", available ? "available" : "unavailable");
    m2_view view = {.frame_w=496, .scale=1, .fill=1, .saturation=1};
    m2gl_upload(renderer, NULL, tiles, 0);
    m2gl_draw(renderer, NULL, &view, 496, 384);
    pixel(248, 190, tiles->pal[0]);
    assert(m2gl_set_fsaa(renderer, 1, 992, 768) == available);
    view.scale = 2;
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, tiles->pal[0]);
    assert(m2gl_set_fsaa(renderer, 0, 992, 768));
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, tiles->pal[0]);
    /* Missing optional symbols leave the base renderer functional. */
    void (M2GL_APIENTRY *saved)(GLenum, GLsizei, GLenum, GLsizei, GLsizei) =
        m2_glRenderbufferStorageMultisample;
    m2_glRenderbufferStorageMultisample = NULL;
    assert(!m2gl_set_fsaa(renderer, 1, 992, 768));
    m2gl_draw(renderer, NULL, &view, 992, 768);
    pixel(495, 300, tiles->pal[0]);
    m2_glRenderbufferStorageMultisample = saved;
    assert(m2gl_set_fsaa(renderer, 1, 496, 384) == available);
    assert(m2gl_set_fsaa(renderer, 0, 496, 384));
}
int main(void)
{
    assert(SDL_Init(SDL_INIT_VIDEO) == 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_Window *window = SDL_CreateWindow("Model2EmuEx Backdrop Check", 0, 0,
        992, 768, SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN);
    assert(window);
    m2_tilegen *tiles = calloc(1, sizeof *tiles); assert(tiles);
    for (unsigned context = 0; context < 2; ++context) {
        SDL_GLContext gl = SDL_GL_CreateContext(window); assert(gl);
        const char *missing = NULL;
        assert(m2glapi_load(SDL_GL_GetProcAddress, &missing));
        m2_gl *renderer = m2gl_create(0); assert(renderer);
        tiles->pal[0] = 0xffc65a31; ++tiles->pal_version;
        draw(renderer, tiles, 1);
        tiles->pal[0] = 0xff1234a6; ++tiles->pal_version;
        draw(renderer, tiles, 1);
        m2gl_invalidate(renderer);
        draw(renderer, tiles, 2);
        filtering(renderer, tiles);
        multisampling(renderer, tiles);
        m2gl_destroy(renderer);
        SDL_GL_DeleteContext(gl);
    }
    free(tiles); SDL_DestroyWindow(window); SDL_Quit();
    puts("GL tiles: PASS (backdrop, decoded bilinear colour, native alpha cutoff, live toggle, context recreation)");
    return 0;
}
