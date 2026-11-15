/* Original per-texture path. Independent of the upstream index-atlas renderer. */
#include "texture_materials.h"
#include "m2/m2board.h"
#include "m2/m2gl.h"
#include "m2/m2glapi.h"
#include "sm2/include/stb_image.h"
#include <zlib.h>
#include <algorithm>
#include <cstdint>
#include <climits>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <set>
#include <sstream>
#include <vector>

namespace {
namespace fs = std::filesystem;
struct Replacement { unsigned crc, mode; fs::path file; };
struct Material {
    GLuint texture = 0;
    unsigned mode = 0;
    uint64_t generation = 0, last_frame = 0;
    bool mip = false;
};
struct Program {
    GLuint name = 0;
    GLint mesh = -1, scale = -1;
    bool tried = false;
};
std::map<unsigned, std::vector<Replacement>> patches;
std::map<unsigned, Material> cache;
Program programs[16];
fs::path directory;
void (*notice)(const char *);
std::set<std::string> reported;
const m2_board *source;
uint64_t frame, generation[2] = {1,1};
int filter, resolution, mesh_blend;
bool mipmaps, gouraud_materials, new_content;

void report(const std::string &message)
{
    if (notice && reported.insert(message).second) notice(message.c_str());
}

std::string read_file(const fs::path &p)
{
    std::ifstream f(p,std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(f), {});
}

const char *vertex =
    "#version 120\nattribute vec4 pos, rect, light, base; attribute vec2 uv;\n"
    "varying vec4 LightMap, BaseColor; varying vec2 TexCoord0;\n"
    "void main(){ gl_Position=pos; LightMap=light; BaseColor=base;\n"
    "vec2 origin=mod(rect.xy,32768.0); TexCoord0=(uv*2048.0-origin)/rect.zw; }\n";
const char *interface =
    "#version 120\nuniform sampler2D Texture,Luma,Xlat; uniform float mesh; uniform vec2 scale;\n"
    "varying vec4 LightMap,BaseColor; varying vec2 TexCoord0;\n";
const char *native_fragment =
    "void main(){ vec4 c=texture2D(Texture,TexCoord0); if(c.a<=0.5)discard;\n"
    "float l=LightMap.b==0.0?c.r:texture2D(Luma,vec2(c.r,LightMap.g)).r; l*=LightMap.r;\n"
    "vec3 rgb=vec3(texture2D(Xlat,vec2(l,BaseColor.r)).r,texture2D(Xlat,vec2(l,BaseColor.g)).g,"
    "texture2D(Xlat,vec2(l,BaseColor.b)).b);\n"
    "if(mesh==1.0 && mod(dot(floor(gl_FragCoord.xy/scale),vec2(1.0)),2.0)>0.5) discard;\n"
    "gl_FragColor=vec4(rgb,mesh==2.0 && c.a==1.0?0.5:c.a); }\n";

GLuint shader(GLenum type, const char *head, const char *body)
{
    GLuint s=glCreateShader(type);
    const char *parts[]={head,body};
    glShaderSource(s,2,parts,nullptr);
    glCompileShader(s);
    GLint ok;
    glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if (!ok) {
        char log[1024]={};
        glGetShaderInfoLog(s,sizeof log,nullptr,log);
        report(std::string("Texture shader compilation failed: ")+log);
        m2_glDeleteShader(s);
        return 0;
    }
    return s;
}

GLuint program(unsigned mode)
{
    Program &p=programs[mode];
    if (p.tried) return p.name;
    p.tried=true;
    std::string fragment=native_fragment;
    if (mode) {
        auto path=directory/("mode_"+std::to_string(mode)+".frag");
        fragment=read_file(path);
        if (fragment.empty()) {
            report("Missing GLSL texture shader: "+path.string()+" (convert the original .ps file)");
            return 0;
        }
    }
    if (mode) {
        // D3DRS_ALPHATESTENABLE, GREATER and ALPHAREF=0x30 in the original device setup.
        // D3D applies this after any user pixel shader.
        fragment = "#define main replacement_main\n" + fragment +
            "\n#undef main\nvoid main(){replacement_main(); if(gl_FragColor.a <= 48.0/255.0) discard;}\n";
    }
    GLuint vs=shader(GL_VERTEX_SHADER,"",vertex), fsname=shader(GL_FRAGMENT_SHADER,interface,fragment.c_str());
    if (vs && fsname) {
        p.name=glCreateProgram();
        glAttachShader(p.name,vs); glAttachShader(p.name,fsname);
        const char *attrs[]={"pos","uv","par","rect","light","base"};
        for (unsigned i=0;i<6;++i) glBindAttribLocation(p.name,i,attrs[i]);
        glLinkProgram(p.name);
        GLint ok;
        glGetProgramiv(p.name,GL_LINK_STATUS,&ok);
        if (!ok) {
            char log[1024]={};
            glGetProgramInfoLog(p.name,sizeof log,nullptr,log);
            report(std::string("Texture shader link failed: ")+log);
            glDeleteProgram(p.name); p.name=0;
        } else {
            glUseProgram(p.name);
            glUniform1i(glGetUniformLocation(p.name,"Texture"),0);
            glUniform1i(glGetUniformLocation(p.name,"Luma"),1);
            glUniform1i(glGetUniformLocation(p.name,"Xlat"),3);
            p.mesh=glGetUniformLocation(p.name,"mesh");
            p.scale=glGetUniformLocation(p.name,"scale");
        }
    }
    if (vs) m2_glDeleteShader(vs);
    if (fsname) m2_glDeleteShader(fsname);
    return p.name;
}

/* 004531e0 and 004b7b70 checksum the stored bytes, including the second
   width of bytes after each packed row. Texture decoding uses a separate
   right-half address mapping. Do not checksum a decoded PNG. */
const Replacement *lookup(unsigned tag,const uint8_t *ram,unsigned offset,unsigned w,unsigned h)
{
    auto it=patches.find(tag);
    if (it==patches.end()) return nullptr;
    if (offset+(h/2-1)*1024+2*w>0x100000) return nullptr;
    uLong crc=0;
    for (unsigned y=0;y<h/2;++y) crc=crc32(crc,ram+offset+1024*y,2*w);
    for (const auto &p : it->second) if (p.crc==crc) return &p;
    return nullptr;
}

void build(Material &m,unsigned tag,const uint16_t th[4],int bank)
{
    unsigned w=32u<<(th[0]&7), h=32u<<((th[0]>>3)&7);
    unsigned x0=(th[2]&63)*32u, y0=((th[2]>>6)&31)*32u;
    const uint8_t *ram=bank?source->tex1:source->tex0;
    const unsigned offset=(y0/2+(x0/1024)*512)*1024+(x0%1024);
    auto patch=lookup(tag,ram,offset,w,h);
    std::vector<uint8_t> pixels;
    m.mode=0;
    if (patch && program(patch->mode)) {
        auto data=read_file(patch->file);
        int width,height,channels;
        auto raw= data.empty() || data.size()>INT_MAX ? nullptr : stbi_load_from_memory(
            reinterpret_cast<const stbi_uc*>(data.data()),(int)data.size(),&width,&height,&channels,4);
        if (raw) {
            w=(unsigned)width; h=(unsigned)height;
            pixels.assign(raw,raw+size_t(w)*h*4);
            stbi_image_free(raw);
            m.mode=patch->mode;
        } else report("Unable to load replacement PNG: "+patch->file.string());
    }
    if (pixels.empty()) {
        if ((!mipmaps && !gouraud_materials) || w>1024 || h>1024 || y0+h>1024 || x0+w>2048) return;
        pixels.resize(size_t(w)*h*4);
        for (unsigned y=0;y<h;++y) for(unsigned x=0;x<w;++x) {
            unsigned sx=x0+x, sy=y0+y;
            auto at=((sy/2)+(sx/1024)*512)*1024+((sx%1024) & ~1u);
            uint16_t word;
            memcpy(&word,ram+at,2);
            unsigned pen=word>>((1-(sy&1))*8+(1-(sx&1))*4)&15;
            auto *p=&pixels[4*(w*y+x)];
            p[0]=p[1]=p[2]=(uint8_t)(pen<<4);
            p[3]=(th[0]&0x2000) && pen==15 ? 0 : 255;
        }
        /* 00453210 fills transparent RGB from the nearest opaque texel
           horizontally, preferring the left at equal distance. */
        if (th[0]&0x2000) for (unsigned y=0;y<h;++y) {
            uint8_t *row=pixels.data()+size_t(y)*w*4;
            unsigned next=0;
            int left=-1;
            for (unsigned x=0;x<w;++x) {
                if (row[4*x+3]) { left=(int)x; continue; }
                if (next<=x) {
                    next=x+1;
                    while (next<w && !row[4*next+3]) ++next;
                }
                int near=left;
                if (next<w && (left<0 || next-x < x-(unsigned)left)) near=(int)next;
                if (near>=0) memcpy(row+4*x,row+4*near,3);
            }
        }
    }
    glGenTextures(1,&m.texture);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D,m.texture);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,w,h,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    if (mipmaps) m2_glGenerateMipmap(GL_TEXTURE_2D);
}

void clear_gpu(bool destroy)
{
    if (destroy) for (auto &it : cache)
        if (it.second.texture) glDeleteTextures(1,&it.second.texture);
    cache.clear();
    for (auto &p:programs) {
        if (destroy && p.name) glDeleteProgram(p.name);
        p={};
    }
}
}

void m2lr_material_load(const char *system,const char *game,int replacements,void (*message)(const char *))
{
    patches.clear(); reported.clear(); notice=message; new_content=true;
    if (!replacements || !system) return;
    directory=fs::u8path(system)/"model2emuex"/"textures";
    std::ifstream manifest(directory/(std::string(game)+".pat"));
    std::string line;
    while (std::getline(manifest,line)) {
        if (line.empty() || line[0]=='/') continue;
        std::istringstream row(line);
        unsigned tag,crc,mode;
        std::string name;
        if (!(row>>std::hex>>tag>>crc>>mode>>name)) continue;
        if (mode>15) { report("Invalid replacement shader mode: "+name); continue; }
        std::replace(name.begin(),name.end(),'\\','/');
        fs::path rel=fs::u8path(name);
        if (rel.is_absolute() || rel.has_root_name() ||
            std::find(rel.begin(),rel.end(),fs::path(".."))!=rel.end()) {
            report("Replacement image must be inside textures/: "+name); continue;
        }
        patches[tag].push_back({crc,mode,directory/rel});
    }
}

void m2lr_material_context(int destroy) { clear_gpu(destroy!=0); }
void m2lr_material_unload(void) { patches.clear(); source=nullptr; new_content=true; }
void m2lr_material_dirty(int bank) { ++generation[bank&1]; }

int m2lr_material_frame(const m2_board *board,int automip,int gouraud,int f,int scale,int blend)
{
    if (new_content) { clear_gpu(true); new_content=false; }
    if (automip && !m2_glGenerateMipmap) report("The OpenGL context cannot generate mipmaps");
    if (gouraud_materials != (gouraud != 0)) {
        m2lr_material_dirty(0); m2lr_material_dirty(1);
    }
    gouraud_materials = gouraud != 0;
    source=board; mipmaps=automip && m2_glGenerateMipmap; filter=f; resolution=scale; mesh_blend=blend;
    ++frame;
    /* ElSemi retires textures after 200 idle frames. */
    for (auto it=cache.begin();it!=cache.end();) {
        if (frame-it->second.last_frame>200) {
            if (it->second.texture) glDeleteTextures(1,&it->second.texture);
            it=cache.erase(it);
        } else ++it;
    }
    return mipmaps || gouraud_materials || !patches.empty();
}

int m2lr_material_bind(void *,const uint16_t th[4])
{
    if (!(th[0]&0x4000)) return 0;
    unsigned tag=((unsigned(th[2])<<16)|th[0])&0x1fffe03fu;
    if (!mipmaps && !gouraud_materials && patches.find(tag)==patches.end()) return 0;
    const int bank=(th[2]>>12)&1;
    auto &m=cache[tag];
    if (m.generation!=generation[bank] || m.mip!=mipmaps) {
        if (m.texture) glDeleteTextures(1,&m.texture);
        m={};
        m.generation=generation[bank]; m.mip=mipmaps;
        build(m,tag,th,bank);
    }
    m.last_frame=frame;
    if (!m.texture || !program(m.mode)) return 0;
    glUseProgram(programs[m.mode].name);
    int mesh=(th[0]&0x8000)?(mesh_blend?2:1):0;
    glUniform1f(programs[m.mode].mesh,m.mode ? (mesh!=0) : mesh);
    glUniform2f(programs[m.mode].scale,(float)resolution,(float)resolution);
    glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D,m.texture);
    bool linear=filter!=M2_TEX_NEAREST;
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,linear?GL_LINEAR:GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,mipmaps?(linear?0x2703:0x2702):(linear?GL_LINEAR:GL_NEAREST));
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,(th[0]&0x100)?0x8370:0x2901);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,(th[0]&0x200)?0x8370:0x2901);
    return 1;
}
