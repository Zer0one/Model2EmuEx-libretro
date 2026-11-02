// Destination GL submission for the unchanged SM2 crosshair geometry.
#include "sm2_overlay.h"
#include "m2/m2glapi.h"
#include <array>
#include <cstdint>
#include <cstdio>
#include <vector>
namespace {
GLuint program,buffer;
using DeleteShader=void (M2GL_APIENTRY *)(GLuint);
DeleteShader delete_shader;
struct Vertex {float x,y,r,g,b,a;};
std::vector<Vertex> vertices;
GLuint compile(GLenum type,const char *source) {
    const auto shader=glCreateShader(type);
    glShaderSource(shader,1,&source,nullptr);glCompileShader(shader);
    GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok) {delete_shader(shader);return 0;}
    return shader;
}
}
extern "C" void sm2lr_overlay_destroy() {
    if(buffer)glDeleteBuffers(1,&buffer);
    if(program)glDeleteProgram(program);
    sm2lr_overlay_abandon();
}
extern "C" void sm2lr_overlay_abandon() { program=buffer=0;delete_shader=nullptr;vertices.clear(); }
extern "C" bool sm2lr_overlay_reset(retro_hw_get_proc_address_t getproc) {
    sm2lr_overlay_destroy();
    delete_shader=reinterpret_cast<DeleteShader>(getproc("glDeleteShader"));
    if(!delete_shader)return false;
    const auto vs=compile(GL_VERTEX_SHADER,
        "#version 120\nattribute vec2 position;attribute vec4 colour;varying vec4 c;"
        "void main(){gl_Position=vec4(position,0.0,1.0);c=colour;}");
    const auto fs=compile(GL_FRAGMENT_SHADER,
        "#version 120\nvarying vec4 c;void main(){gl_FragColor=c;}");
    if(!vs || !fs) {if(vs)delete_shader(vs);if(fs)delete_shader(fs);return false;}
    program=glCreateProgram();glAttachShader(program,vs);glAttachShader(program,fs);
    glBindAttribLocation(program,0,"position");glBindAttribLocation(program,1,"colour");
    glLinkProgram(program);delete_shader(vs);delete_shader(fs);
    GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok) {sm2lr_overlay_destroy();return false;}
    glGenBuffers(1,&buffer);return buffer!=0;
}
void sm2lr_overlay_draw(const sm2::libretro::CrosshairGeometry& geometry,unsigned width,unsigned height) {
    if(!program || !buffer || geometry.rectangles.empty() || !width || !height)return;
    // Bound temporary GPU batches even for maximum-size user PNGs.
    constexpr size_t batch_rectangles=4096;
    vertices.clear();vertices.reserve(batch_rectangles*6);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glViewport(0,0,static_cast<GLsizei>(width),static_cast<GLsizei>(height));
    glDisable(GL_SCISSOR_TEST);glDisable(GL_CULL_FACE);glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    glUseProgram(program);glBindBuffer(GL_ARRAY_BUFFER,buffer);
    glEnableVertexAttribArray(0);glEnableVertexAttribArray(1);
    glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,sizeof(Vertex),nullptr);
    glVertexAttribPointer(1,4,GL_FLOAT,GL_FALSE,sizeof(Vertex),reinterpret_cast<const void*>(2*sizeof(float)));
    const auto flush=[] {
        glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(vertices.size()*sizeof(Vertex)),vertices.data(),GL_STREAM_DRAW);
        glDrawArrays(GL_TRIANGLES,0,static_cast<GLsizei>(vertices.size()));vertices.clear();
    };
    for(const auto &rect:geometry.rectangles) {
        const float x0=2.0f*rect.x/width-1.0f,x1=2.0f*(rect.x+rect.width)/width-1.0f;
        const float y0=1.0f-2.0f*rect.y/height,y1=1.0f-2.0f*(rect.y+rect.height)/height;
        const float r=((rect.colour>>16)&255)/255.0f,g=((rect.colour>>8)&255)/255.0f;
        const float b=(rect.colour&255)/255.0f,a=(rect.colour>>24)/255.0f;
        for(const auto &xy:std::array<std::array<float,2>,6>{{{x0,y0},{x0,y1},{x1,y0},{x1,y0},{x0,y1},{x1,y1}}})
            vertices.push_back({xy[0],xy[1],r,g,b,a});
        if(vertices.size()==batch_rectangles*6)flush();
    }
    if(!vertices.empty())flush();
    glDisableVertexAttribArray(0);glDisableVertexAttribArray(1);glBindBuffer(GL_ARRAY_BUFFER,0);
    glUseProgram(0);glDisable(GL_BLEND);
}
