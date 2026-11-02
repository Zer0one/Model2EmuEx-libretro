// SM2 timing aggregation and ImGui panel, submitted through frontend GL pointers.
#include "sm2_timing.h"
#include "m2/m2glapi.h"
#include <imgui.h>
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <unordered_set>
#include <vector>
namespace {
using sm2::libretro::TimingOverlayData;
TimingOverlayData display;
unsigned font,callbacks,intervals;
bool native,ui_ready,gl_failed;
double fps=60,machine_total,video_total,audio_total,run_total,worst,previous_start,interval_total;
retro_log_printf_t logger;
GLuint program,buffer;
unsigned layout_width,layout_height,layout_font;
std::unordered_set<GLuint> textures;
std::vector<ImDrawVert> vertices;
using DeleteShader=void (M2GL_APIENTRY *)(GLuint);
DeleteShader delete_shader;
void reset_window() {
    callbacks=intervals=0;machine_total=video_total=audio_total=run_total=worst=interval_total=0;
}
GLuint compile(GLenum type,const char *source) {
    const auto shader=glCreateShader(type);GLint ok=0;
    glShaderSource(shader,1,&source,nullptr);glCompileShader(shader);glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok) {delete_shader(shader);return 0;}return shader;
}
bool initialize_gl() {
    const auto vs=compile(GL_VERTEX_SHADER,"#version 120\nattribute vec2 position;attribute vec2 uv;attribute vec4 colour;"
        "uniform vec2 scale;varying vec2 t;varying vec4 c;void main(){gl_Position=vec4(position*scale+vec2(-1,1),0,1);t=uv;c=colour;}");
    const auto fs=compile(GL_FRAGMENT_SHADER,"#version 120\nuniform sampler2D image;varying vec2 t;varying vec4 c;void main(){gl_FragColor=c*texture2D(image,t);}");
    if(!vs || !fs) {if(vs)delete_shader(vs);if(fs)delete_shader(fs);return false;}
    program=glCreateProgram();glAttachShader(program,vs);glAttachShader(program,fs);
    glBindAttribLocation(program,0,"position");glBindAttribLocation(program,1,"uv");glBindAttribLocation(program,2,"colour");
    glLinkProgram(program);delete_shader(vs);delete_shader(fs);
    GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);if(!ok)return false;
    glGenBuffers(1,&buffer);return buffer!=0;
}
void update_textures(ImDrawData *draw) {
    if(!draw->Textures)return;
    for(auto *texture:*draw->Textures) {
        if(texture->Status==ImTextureStatus_WantCreate || texture->Status==ImTextureStatus_WantUpdates) {
            if(texture->Format!=ImTextureFormat_RGBA32)continue;
            GLuint id=static_cast<GLuint>(texture->GetTexID());
            if(!id) {glGenTextures(1,&id);textures.insert(id);texture->SetTexID(static_cast<ImTextureID>(id));}
            glBindTexture(GL_TEXTURE_2D,id);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
            glPixelStorei(GL_UNPACK_ALIGNMENT,1);
            // Full atlas upload avoids driver-specific unpack-row state; only on atlas changes.
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,texture->Width,texture->Height,0,GL_RGBA,GL_UNSIGNED_BYTE,texture->GetPixels());
            texture->SetStatus(ImTextureStatus_OK);
        } else if(texture->Status==ImTextureStatus_WantDestroy && texture->UnusedFrames>0) {
            const auto id=static_cast<GLuint>(texture->GetTexID());
            if(textures.erase(id))glDeleteTextures(1,&id);
            texture->SetTexID(ImTextureID_Invalid);texture->SetStatus(ImTextureStatus_Destroyed);
        }
    }
}
}
const TimingOverlayData& sm2lr_timing_data() {return display;}
extern "C" void sm2lr_timing_logger(retro_log_printf_t cb) {logger=cb;}
extern "C" double sm2lr_timing_clock() {
    return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
extern "C" void sm2lr_timing_clear() {
    reset_window();previous_start=0;display={};display.enabled=font!=0;display.font_pixels=font;display.native_timing=native;
}
extern "C" void sm2lr_timing_config(unsigned pixels,bool is_native,double cadence) {
    const unsigned next=pixels>=11 && pixels<=14?pixels:0;
    const bool reset=(next!=0)!=(font!=0) || is_native!=native || cadence!=fps;
    font=next;native=is_native;fps=cadence;
    if(reset)sm2lr_timing_clear();
    display.enabled=font!=0;display.font_pixels=font;display.native_timing=native;
}
extern "C" void sm2lr_timing_sample(double machine_ms,double video_ms,double audio_ms,double run_ms,double start) {
    if(!font)return;
    if(previous_start>0 && start>previous_start) {++intervals;interval_total+=start-previous_start;}
    previous_start=start;
    machine_total+=machine_ms;video_total+=video_ms;audio_total+=audio_ms;run_total+=run_ms;worst=std::max(worst,run_ms);
    if(++callbacks<61)return;
    const auto machine=machine_total/callbacks,video=video_total/callbacks,audio=audio_total/callbacks,run=run_total/callbacks;
    display={true,true,native,font,static_cast<float>(machine),static_cast<float>(video),static_cast<float>(audio),
        static_cast<float>(run),static_cast<float>(worst),static_cast<float>(interval_total>0?1000.0*intervals/interval_total:0),
        static_cast<float>(machine+video>0?1000.0/(machine+video):0),static_cast<float>(run>0?1000.0/run:0)};
    if(logger)logger(RETRO_LOG_INFO,"[Model2EmuEx Timing] 61 callbacks/machine frames | machine %.3f ms, video %.3f ms, audio/pacing %.3f ms, retro_run %.3f ms, worst %.3f ms, actual %.2f FPS, engine-cap %.2f FPS, callback-cap %.2f FPS\n",
        machine,video,audio,run,worst,display.actual_fps,display.engine_cap_fps,display.callback_cap_fps);
    reset_window();
}
extern "C" void sm2lr_timing_shutdown() {
    if(ui_ready)sm2::libretro::timing_overlay_shutdown();ui_ready=false;
    sm2lr_timing_clear();
}
extern "C" void sm2lr_timing_gl_destroy() {
    sm2lr_timing_shutdown();
    for(auto id:textures)glDeleteTextures(1,&id);textures.clear();
    if(buffer)glDeleteBuffers(1,&buffer);if(program)glDeleteProgram(program);
    sm2lr_timing_gl_abandon();
}
extern "C" void sm2lr_timing_gl_abandon() {
    sm2lr_timing_shutdown();textures.clear();
    buffer=program=0;delete_shader=nullptr;gl_failed=false;vertices.clear();
    layout_width=layout_height=layout_font=0;
}
// The caller resolves the one shader-lifetime entry absent from the native table.
extern "C" void sm2lr_timing_gl_proc(retro_hw_get_proc_address_t getproc) {
    delete_shader=reinterpret_cast<DeleteShader>(getproc("glDeleteShader"));
}
extern "C" void sm2lr_timing_draw(unsigned width,unsigned height) {
    if(!display.enabled || !display.valid || !width || !height || gl_failed)return;
    if(!program) {
        if(!delete_shader || !initialize_gl()) {gl_failed=true;if(logger)logger(RETRO_LOG_WARN,"[Model2EmuEx] Timing overlay GL initialization failed\n");return;}
    }
    if(!ui_ready) {
        sm2::libretro::timing_overlay_initialize();ui_ready=true;
        auto &io=ImGui::GetIO();io.BackendFlags|=ImGuiBackendFlags_RendererHasTextures;
        io.BackendRendererName="Model2EmuEx Libretro Overlay";io.LogFilename=nullptr;
    }
    auto *draw=sm2::libretro::build_timing_overlay(display,width,height,fps);
    if(!draw)return;
    glBindFramebuffer(GL_FRAMEBUFFER,0);glViewport(0,0,width,height);glActiveTexture(GL_TEXTURE0);
    update_textures(draw);
    if(layout_width!=width || layout_height!=height || layout_font!=font) {
        // ImGui auto-fit consumes the previous layout. Settle a new size before
        // submission so the first visible frame does not clip enlarged text.
        draw=sm2::libretro::build_timing_overlay(display,width,height,fps);
        if(!draw)return;
        update_textures(draw);layout_width=width;layout_height=height;layout_font=font;
    }
    const auto setup=[&] {
        glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glEnable(GL_BLEND);glEnable(GL_SCISSOR_TEST);
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);glUseProgram(program);
        glUniform2f(glGetUniformLocation(program,"scale"),2.0f/width,-2.0f/height);
        glUniform1i(glGetUniformLocation(program,"image"),0);glBindBuffer(GL_ARRAY_BUFFER,buffer);
        for(unsigned a=0;a<3;++a)glEnableVertexAttribArray(a);
        glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,sizeof(ImDrawVert),reinterpret_cast<void*>(offsetof(ImDrawVert,pos)));
        glVertexAttribPointer(1,2,GL_FLOAT,GL_FALSE,sizeof(ImDrawVert),reinterpret_cast<void*>(offsetof(ImDrawVert,uv)));
        glVertexAttribPointer(2,4,GL_UNSIGNED_BYTE,GL_TRUE,sizeof(ImDrawVert),reinterpret_cast<void*>(offsetof(ImDrawVert,col)));
    };setup();
    for(const auto *list:draw->CmdLists)for(const auto &command:list->CmdBuffer) {
        if(command.UserCallback) {
            if(command.UserCallback==ImDrawCallback_ResetRenderState)setup();else command.UserCallback(list,&command);
            continue;
        }
        const int x0=std::clamp(static_cast<int>(command.ClipRect.x),0,static_cast<int>(width));
        const int y0=std::clamp(static_cast<int>(command.ClipRect.y),0,static_cast<int>(height));
        const int x1=std::clamp(static_cast<int>(command.ClipRect.z),0,static_cast<int>(width));
        const int y1=std::clamp(static_cast<int>(command.ClipRect.w),0,static_cast<int>(height));
        if(x1<=x0 || y1<=y0)continue;
        glScissor(x0,height-y1,x1-x0,y1-y0);glBindTexture(GL_TEXTURE_2D,static_cast<GLuint>(command.GetTexID()));
        for(unsigned offset=0;offset<command.ElemCount;) {
            const unsigned count=std::min(65535u,command.ElemCount-offset);vertices.resize(count);
            for(unsigned i=0;i<count;++i)vertices[i]=list->VtxBuffer[command.VtxOffset+list->IdxBuffer[command.IdxOffset+offset+i]];
            glBufferData(GL_ARRAY_BUFFER,vertices.size()*sizeof(ImDrawVert),vertices.data(),GL_STREAM_DRAW);glDrawArrays(GL_TRIANGLES,0,count);offset+=count;
        }
    }
    for(unsigned a=0;a<3;++a)glDisableVertexAttribArray(a);
    glBindBuffer(GL_ARRAY_BUFFER,0);glBindTexture(GL_TEXTURE_2D,0);glUseProgram(0);glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);
}
