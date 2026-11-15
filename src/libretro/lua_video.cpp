#include "lua_video.h"
#include "lua_script.h"
#include "sm2_timing.h"
#include "m2/m2glapi.h"
#include "sm2/include/stb_image.h"
#include <imgui.h>
#include <algorithm>
#include <climits>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <vector>

namespace {
namespace fs=std::filesystem;
struct Font { fs::path path; float size; ImFont *font=nullptr; };
struct Surface { int width,height; std::vector<unsigned char> rgba; GLuint texture=0; };
struct Draw { int handle,x,y; ImU32 color; bool image; std::string text; };
std::map<int,Font> fonts;
std::map<int,Surface> surfaces;
std::vector<Draw> queue;
std::vector<GLuint> retired;
int next_handle;
fs::path assets;
void (*notice)(const char *);
ImGuiContext *ctx;
struct Current {
    ImGuiContext *previous=ImGui::GetCurrentContext();
    ~Current(){ImGui::SetCurrentContext(previous);}
};
void create_ui()
{
    if(ctx)return;
    ctx=ImGui::CreateContext();
    ImGui::SetCurrentContext(ctx);
    auto &io=ImGui::GetIO();io.IniFilename=io.LogFilename=nullptr;
    io.BackendFlags|=ImGuiBackendFlags_RendererHasTextures;
    io.Fonts->AddFontDefault();
}
bool asset_relative(const fs::path &p)
{
    return !p.empty()&&!p.is_absolute()&&!p.has_root_name()&&
        std::find(p.begin(),p.end(),fs::path(".."))==p.end();
}
int create_font(lua_State *L)
{
    const char *name=luaL_checkstring(L,1);
    int size=luaL_checkint(L,2);
    bool bold=luaL_checkint(L,3)!=0;
    if(size<=0)return luaL_argerror(L,2,"positive font size required");
    fs::path path=fs::u8path(std::string(name)+(bold?" Bold.ttf":".ttf"));
    if(!asset_relative(path)||!std::ifstream(assets/path).good()) {
        if(notice)notice(("Lua font unavailable; using the built-in font: "+path.string()).c_str());
        path.clear();
    } else path=assets/path;
    int id=++next_handle;
    fonts.emplace(id,Font{path,(float)size});
    lua_pushinteger(L,id);return 1;
}
int create_image(lua_State *L)
{
    const char *name=luaL_checkstring(L,1);
    std::string s=name;std::replace(s.begin(),s.end(),'\\','/');
    fs::path p=fs::u8path(s);
    if(!asset_relative(p))return luaL_argerror(L,1,"path must be inside scripts/assets");
    if(*p.begin()=="assets")p=p.lexically_relative("assets");
    std::ifstream f(assets/p,std::ios::binary);
    std::vector<unsigned char> bytes(std::istreambuf_iterator<char>(f),{});
    Surface image{};int channels;
    auto *pixels=bytes.empty() || bytes.size()>INT_MAX?nullptr:stbi_load_from_memory(bytes.data(),(int)bytes.size(),&image.width,&image.height,&channels,4);
    if(!pixels){if(notice)notice(("Unable to load Lua image: "+p.string()).c_str());lua_pushinteger(L,0);return 1;}
    image.rgba.assign(pixels,pixels+size_t(image.width)*image.height*4);stbi_image_free(pixels);
    int id=++next_handle;surfaces.emplace(id,std::move(image));lua_pushinteger(L,id);return 1;
}
int release(lua_State *L)
{
    int id=luaL_checkint(L,1);
    if(lua_toboolean(L,lua_upvalueindex(1))) {
        auto it=surfaces.find(id);
        if(it!=surfaces.end()){if(it->second.texture)retired.push_back(it->second.texture);surfaces.erase(it);}
    } else {
        auto it=fonts.find(id);
        if(it!=fonts.end()){
            if(ctx && it->second.font) {
                Current saved;ImGui::SetCurrentContext(ctx);
                ImGui::GetIO().Fonts->RemoveFont(it->second.font);
            }
            fonts.erase(it);
        }
    }
    return 0;
}
int draw_text(lua_State *L)
{
    int n=lua_toboolean(L,lua_upvalueindex(1)),id=n?luaL_checkint(L,1):0;
    if(n && !fonts.count(id))return luaL_argerror(L,1,"invalid font");
    int x=luaL_checkint(L,n+1),y=luaL_checkint(L,n+2);
    const char *text=luaL_checkstring(L,n+3);
    unsigned rgb=(unsigned)luaL_checkinteger(L,n+4);
    queue.push_back({id,x,y,IM_COL32((rgb>>16)&255,(rgb>>8)&255,rgb&255,255),false,text});return 0;
}
int draw_image(lua_State *L)
{
    int id=luaL_checkint(L,1),x=luaL_checkint(L,2),y=luaL_checkint(L,3);
    if(!surfaces.count(id))return luaL_argerror(L,1,"invalid surface");
    queue.push_back({id,x,y,0,true,{}});return 0;
}
}
void lua_video_bind(lua_State *L,const fs::path &dir,void (*msg)(const char *))
{
    assets=dir;notice=msg;next_handle=0;
    lua_register(L,"Video_CreateFont",create_font);lua_register(L,"Video_CreateSurfaceFromFile",create_image);
    lua_register(L,"Video_DrawSurface",draw_image);
    for(int i=0;i<2;++i) {
        lua_pushboolean(L,i);lua_pushcclosure(L,draw_text,1);lua_setglobal(L,i?"Video_DrawTextWithFont":"Video_DrawText");
        lua_pushboolean(L,i);lua_pushcclosure(L,release,1);lua_setglobal(L,i?"Video_ReleaseSurface":"Video_ReleaseFont");
    }
}
void m2lr_lua_context(int destroy)
{
    if(ctx) {
        Current saved;ImGui::SetCurrentContext(ctx);
        m2lr_imgui_release_atlas(ImGui::GetIO().Fonts,destroy!=0);
        ImGui::DestroyContext(ctx);ctx=nullptr;
        for(auto &it:fonts)it.second.font=nullptr;
    }
    for(auto &it:surfaces) {if(destroy && it.second.texture)glDeleteTextures(1,&it.second.texture);it.second.texture=0;}
    if(destroy && !retired.empty())glDeleteTextures((GLsizei)retired.size(),retired.data());
    retired.clear();queue.clear();
}
void lua_video_close()
{
    // Unload may run without a GL context. Retire names on the next draw or context destroy.
    if(ctx) {
        Current saved;ImGui::SetCurrentContext(ctx);
        for(auto *tex:ImGui::GetIO().Fonts->TexList)
            if(tex->GetTexID()!=ImTextureID_Invalid) retired.push_back((GLuint)tex->GetTexID());
        m2lr_imgui_release_atlas(ImGui::GetIO().Fonts,false);ImGui::DestroyContext(ctx);ctx=nullptr;
    }
    for(auto &it:surfaces)if(it.second.texture)retired.push_back(it.second.texture);
    surfaces.clear();fonts.clear();queue.clear();
}
void m2lr_lua_discard_draw(){queue.clear();}
void m2lr_lua_draw(unsigned w,unsigned h)
{
    if(!retired.empty()){glDeleteTextures((GLsizei)retired.size(),retired.data());retired.clear();}
    if(queue.empty())return;
    Current saved;create_ui();ImGui::SetCurrentContext(ctx);
    auto &io=ImGui::GetIO();io.DisplaySize=ImVec2((float)w,(float)h);io.DeltaTime=1.0f/60;
    for(auto &it:fonts) {
        auto &f=it.second;
        if(!f.font && !f.path.empty()) {
            f.font=io.Fonts->AddFontFromFileTTF(f.path.string().c_str(),f.size);
            if(!f.font){if(notice)notice("Unreadable Lua TTF; using built-in font");f.path.clear();}
        }
    }
    ImGui::NewFrame();
    auto *list=ImGui::GetBackgroundDrawList();
    for(const auto &d:queue) {
        ImVec2 pos((float)d.x,(float)d.y);
        if(!d.image) {
            auto it=fonts.find(d.handle);
            if(it==fonts.end()&&d.handle)continue;
            auto f=it==fonts.end()?nullptr:&it->second;
            list->AddText(f&&f->font?f->font:ImGui::GetFont(),f?f->size:13,pos,d.color,d.text.c_str());
        } else {
            auto it=surfaces.find(d.handle);if(it==surfaces.end())continue;
            auto &s=it->second;
            if(!s.texture) {
                glGenTextures(1,&s.texture);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,s.texture);
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
                glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
                glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,s.width,s.height,0,GL_RGBA,GL_UNSIGNED_BYTE,s.rgba.data());
            }
            list->AddImage((ImTextureID)s.texture,pos,ImVec2(pos.x+s.width,pos.y+s.height));
        }
    }
    queue.clear();ImGui::Render();m2lr_imgui_submit(ImGui::GetDrawData(),w,h);
}
