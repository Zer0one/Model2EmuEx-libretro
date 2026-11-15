// ROM-free GL readback for .pat identity, converted shaders and mip generation.
#include "m2/m2board.h"
#include "m2/m2gl.h"
#include "m2/m2glapi.h"
#include "../src/libretro/texture_materials.h"
#include <SDL2/SDL.h>
#include <zlib.h>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <vector>

namespace fs = std::filesystem;
static void put32(std::vector<uint8_t> &out, uint32_t value)
{
    for (int shift : {24, 16, 8, 0}) out.push_back(uint8_t(value >> shift));
}
static void png_chunk(std::vector<uint8_t> &out, const char *name, const std::vector<uint8_t> &data)
{
    put32(out, uint32_t(data.size()));
    size_t start = out.size();
    out.insert(out.end(), name, name + 4);
    out.insert(out.end(), data.begin(), data.end());
    put32(out, uint32_t(crc32(0, out.data() + start, unsigned(data.size() + 4))));
}
static void fixture_png(const fs::path &path)
{
    std::vector<uint8_t> png = {137,80,78,71,13,10,26,10};
    png_chunk(png, "IHDR", {0,0,0,1,0,0,0,1,8,2,0,0,0});
    uint8_t row[] = {0,204,102,50};
    uLong size = compressBound(sizeof row);
    std::vector<uint8_t> compressed(size);
    assert(compress(compressed.data(), &size, row, sizeof row) == Z_OK);
    compressed.resize(size);
    png_chunk(png, "IDAT", compressed);
    png_chunk(png, "IEND", {});
    std::ofstream(path, std::ios::binary).write((const char *)png.data(), png.size());
}
// Drive the geometry parser with one strip, including a culled face and a
// link-zero break. Only the two trailing vertices receive each new light.
static void check_strip(m2_board &board)
{
    std::vector<uint32_t> list(0x80000 / 4);
    board.bufram = reinterpret_cast<uint8_t *>(list.data());
    size_t at = 0;
    auto word = [&](uint32_t value){ list[at++] = value; };
    auto vertex = [&](uint32_t x){ word(x); word(0); word(0x3f800000); };
    word(2u << 23); word(0x800400); word(0x800000);
    vertex(0); vertex(0x3f800000);
    auto face = [&](unsigned link, unsigned light, bool culled) {
        word(1 | (link << 8)); word((light << 23) | (culled ? 0x80000000u : 0));
        word(0); vertex(0); vertex(0x3f800000);
    };
    face(2,10,false);
    face(2,40,true);
    face(2,60,false);
    face(0,20,false);
    face(2,30,false);
    word(0); word(15u << 23);
    auto geo = m2geo_create();
    assert(geo);
    geo->fake_gouraud = 1;
    m2geo_run(geo,&board);
    assert(geo->npolys == 3);
    for (int v=0;v<4;++v) {
        assert(geo->polys[0].shade[v][0] == 20);
        assert(geo->polys[1].shade[v][0] == (v<2 ? 80 : 120));
        assert(geo->polys[2].shade[v][0] == 60);
    }
    m2geo_destroy(geo);
    board.bufram = nullptr;
    puts("PASS: strip seeds, culled lighting, continuation and link-zero restart");
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    const auto root = fs::path(argv[1]);
    const auto dir = root / "model2emuex/textures";
    fs::create_directories(dir / "probe");
    for (const char *shader : {"mode_1.frag","mode_2.frag"})
        fs::copy_file(fs::path("src/libretro/assets/textures") / shader, dir / shader);
    fixture_png(dir / "probe/test.png");
    assert(SDL_Init(SDL_INIT_VIDEO) == 0);
    SDL_Window *window = SDL_CreateWindow("Texture Material Test",0,0,496,384,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    assert(window);
    auto context = SDL_GL_CreateContext(window);
    const char *missing = nullptr;
    assert(context && m2glapi_load(SDL_GL_GetProcAddress, &missing));
    auto renderer = m2gl_create(0);
    auto mesh = m2gl_mesh_create();
    auto board = std::make_unique<m2_board>();
    std::vector<uint8_t> tex(0x100000), lut(65536,64);
    board->tex0 = board->tex1 = tex.data();
    board->luma = board->xlat = board->pal = lut.data();
    check_strip(*board);
    auto tiles = std::make_unique<m2_tilegen>();
    m2_gpoly face{};
    face.th[0] = 0x4000;
    face.nverts = 4;
    face.smooth_shading = 2;
    face.v[0] = {0,0,1,0,0}; face.v[1] = {496,0,1,32,0};
    face.v[2] = {496,384,1,32,32}; face.v[3] = {0,384,1,0,32};
    for (auto &s : face.shade) { s[0]=254; s[2]=255; }
    uint32_t order = 0;
    m2_geo_frame frame{&face,&order,1};
    assert(renderer && mesh && m2gl_mesh_build_materials(mesh,&frame,496));
    m2_view view{};
    view.frame_w=496; view.scale=1; view.fill=1; view.saturation=1;
    view.bind_material=m2lr_material_bind;
    for (int mode : {1,2}) {
        std::ofstream manifest(dir/"probe.pat");
        manifest << "4000 ffffffff 1 probe/missing.png\n4000 efb5af2e " << mode << " probe/test.png\n";
        manifest.close();
        m2lr_material_load(root.string().c_str(),"probe",1,[](const char *msg){ puts(msg); });
        assert(m2lr_material_frame(board.get(),0,0,M2_TEX_NEAREST,1,0));
        m2gl_upload(renderer, board.get(), tiles.get(), 1);
        m2gl_draw(renderer, mesh, &view, 496, 384);
        std::array<uint8_t,4> rgba{};
        glReadPixels(248,192,1,1,GL_RGBA,GL_UNSIGNED_BYTE,rgba.data());
        const double light = (mode == 1 ? 254.0 : 128.0) / 255;
        for (unsigned c=0;c<3;c++) {
            const int rgb[]={204,102,50};
            assert(std::abs(rgba[c] - std::round(rgb[c]*light)) <= 1);
        }
        printf("Shader %d RGB %u %u %u\n",mode,rgba[0],rgba[1],rgba[2]);
        tex[0]=1; m2lr_material_dirty(0);
        assert(!m2lr_material_bind(nullptr, face.th));
        tex[0]=0; m2lr_material_dirty(0);
        assert(m2lr_material_bind(nullptr, face.th));
    }
    std::fill(tex.begin(),tex.end(),0x0f);
    m2lr_material_dirty(0);
    assert(m2lr_material_frame(board.get(),1,0,M2_TEX_NEAREST,1,0));
    assert(m2lr_material_bind(nullptr, face.th));
    auto get_image = reinterpret_cast<void (*)(GLenum,int,GLenum,GLenum,void*)>(SDL_GL_GetProcAddress("glGetTexImage"));
    auto get_parameter = reinterpret_cast<void (*)(GLenum,GLenum,GLint*)>(SDL_GL_GetProcAddress("glGetTexParameteriv"));
    GLint filter=0;
    std::array<uint8_t,4> mip{};
    assert(get_image && get_parameter);
    get_parameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, &filter);
    assert(filter == 0x2702); // GL_NEAREST_MIPMAP_LINEAR
    get_image(GL_TEXTURE_2D,5,GL_RGBA,GL_UNSIGNED_BYTE,mip.data());
    assert((mip == std::array<uint8_t,4>{120,120,120,255}));
    puts("PASS: replacement CRC selection, both shader pixels, dirty cache and generated 1x1 mip");
    m2lr_material_context(1); m2lr_material_unload();
    m2gl_mesh_destroy(mesh); m2gl_destroy(renderer);
    SDL_GL_DeleteContext(context); SDL_DestroyWindow(window); SDL_Quit();
}
