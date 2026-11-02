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
int main(void)
{
    assert(SDL_Init(SDL_INIT_VIDEO) == 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_Window *window = SDL_CreateWindow("Model2EmuEx Backdrop Check", 0, 0,
        496, 420, SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN);
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
        m2gl_destroy(renderer);
        SDL_GL_DeleteContext(gl);
    }
    free(tiles); SDL_DestroyWindow(window); SDL_Quit();
    puts("GL backdrop: PASS (pen 0, palette changes, black bars, scale/context recreation)");
    return 0;
}
