/* Adapter for the original Model 2 Emulator script API (model2lua.txt). */
#include "lua_script.h"
#include "m2/m2board.h"
#include "lua_video.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
namespace fs=std::filesystem;
lua_State *L;
m2_board *board;
fs::path scripts;
std::string game_name;
void (*notice)(const char *);
std::set<std::string> errors;
bool active, initialized;
unsigned width=496,height=384;
int wide=-1, stretch_bits,stretch_mask;
std::array<std::array<bool,256>,2> joystick{};
struct Option {
    std::string id,key,name;
    std::vector<std::string> labels,numbers;
    int value=0;
};
std::map<std::string,Option> options;
std::vector<retro_core_option_v2_definition> definitions;
void report(const std::string &s)
{
    if (notice && errors.insert(s).second) notice(s.c_str());
}
void error_message(const char *where)
{
    const char *msg=lua_tostring(L,-1);
    report(std::string("Lua ")+where+": "+(msg?msg:"unknown error"));
    lua_pop(L,1);
}
uint32_t u32(lua_State *s,int arg)
{
    double n=luaL_checknumber(s,arg);
    if (!std::isfinite(n)) luaL_argerror(s,arg,"finite integer required");
    n=std::fmod(std::trunc(n),4294967296.0);
    return (uint32_t)(n<0?n+4294967296.0:n);
}
int operation(lua_State *s) {return (int)lua_tointeger(s,lua_upvalueindex(1));}
int bits(lua_State *s)
{
    int op=operation(s);
    uint32_t a=u32(s,1),b=op==3?0:u32(s,2);
    switch(op) {
    case 0:a&=b;break; case 1:a|=b;break; case 2:a^=b;break;
    case 3:a=~a;break; case 4:a<<=(b&31);break; case 5:a>>=(b&31);break;
    }
    lua_pushnumber(s,a);
    return 1;
}
int rom(lua_State *s)
{
    int op=operation(s), count=1<<(op%3);
    unsigned region=u32(s,1), at=u32(s,2);
    if(region>=M2_REGIONS || !board->rom.ptr[region] ||
       (uint64_t)at+count>board->rom.size[region])
        return luaL_error(s,"ROM area or offset outside loaded region");
    uint8_t *p=board->rom.ptr[region]+at;
    uint32_t value=0;
    if(op>=3) {
        value=u32(s,3);
        for(int i=0;i<count;++i)p[i]=(uint8_t)(value>>(8*i));
        if(region==0)i960_invalidate_code(board->cpu,0);
        return 0;
    }
    for(int i=0;i<count;++i)value|=(uint32_t)p[i]<<(8*i);
    lua_pushnumber(s,value);
    return 1;
}
int memory(lua_State *s)
{
    int op=operation(s);
    uint32_t addr=u32(s,1);
    auto cpu=board->cpu;
    if(op>=3 && op<=5) {
        uint32_t data=u32(s,2);
        if(op==3)i960_write8(cpu,addr,(uint8_t)data);
        if(op==4)i960_write16(cpu,addr,(uint16_t)data);
        if(op==5)i960_write32(cpu,addr,data);
        return 0;
    }
    if(op==6) {
        auto page=cpu->rpage[addr>>16].host;
        lua_pushnumber(s,page?(lua_Number)(uintptr_t)(page+(addr&65535)):0);
    } else {
        uint32_t value=op==0?i960_read8(cpu,addr):op==1?i960_read16(cpu,addr):i960_read32(cpu,addr);
        lua_pushnumber(s,value);
    }
    return 1;
}
int aspect(lua_State *s)
{
    int bit=operation(s);
    bool enabled=u32(s,1)!=0;
    if(!bit)wide=enabled;
    else {
        stretch_mask|=bit;
        if(enabled)stretch_bits|=bit; else stretch_bits&=~bit;
    }
    return 0;
}
int key(lua_State *s)
{
    uint32_t code=u32(s,1),device=code>>8;
    lua_pushinteger(s,device>=1 && device<=joystick.size() && joystick[device-1][code&255]);
    return 1;
}
int screen(lua_State *s) {lua_pushinteger(s,width);lua_pushinteger(s,height);return 2;}
void bind(const char *name,lua_CFunction fn,int op)
{
    lua_pushinteger(L,op);lua_pushcclosure(L,fn,1);lua_setglobal(L,name);
}
void install()
{
    const char *b[]={"AND","OR","XOR","NOT","SHL","SHR"};
    for(int i=0;i<6;++i)bind(b[i],bits,i);
    const char *r[]={"ReadByte","ReadWord","ReadDWord","PatchByte","PatchWord","PatchDWord"};
    const char *m[]={"ReadByte","ReadWord","ReadDWord","WriteByte","WriteWord","WriteDWord","GetRamPtr"};
    for(int i=0;i<6;++i)bind((std::string("Romset_")+r[i]).c_str(),rom,i);
    for(int i=0;i<7;++i)bind((std::string("I960_")+m[i]).c_str(),memory,i);
    bind("Model2_SetWideScreen",aspect,0);
    bind("Model2_SetStretchALow",aspect,M2_STRETCH_A_LOW);
    bind("Model2_SetStretchBLow",aspect,M2_STRETCH_B_LOW);
    bind("Model2_SetStretchAHigh",aspect,M2_STRETCH_A_HIGH);
    bind("Model2_SetStretchBHigh",aspect,M2_STRETCH_B_HIGH);
    bind("Input_IsKeyPressed",key,0);
    bind("Video_GetScreenSize",screen,0);
    lua_video_bind(L,scripts/"assets",notice);
}

std::string key_suffix(const std::string &id)
{
    // Encode the escape character as well, so independent script keys cannot collide.
    static const char digits[]="0123456789abcdef";
    std::string out;
    for(unsigned char c:id) {
        if((c>='a'&&c<='z')||(c>='0'&&c<='9'))out+=char(c);
        else {out+='_';out+=digits[c>>4];out+=digits[c&15];}
    }
    return out;
}
// The host reads the declared menu and callbacks outside script execution.
// Raw lookups keep a script-defined __index/__newindex from running here.
void raw_field(int table, const char *key)
{
    lua_pushstring(L, key);
    lua_rawget(L, table < 0 && table > LUA_REGISTRYINDEX ? table - 1 : table);
}
void set_option_value(int value)
{
    lua_pushliteral(L, "value");
    lua_pushinteger(L, value);
    lua_rawset(L, -3);
}
void read_options()
{
    options.clear(); definitions.clear();
    raw_field(LUA_GLOBALSINDEX, "Options");
    if(lua_istable(L,-1)) {
        lua_pushnil(L);
        while(lua_next(L,-2)) {
            if(lua_type(L,-2)==LUA_TSTRING && lua_istable(L,-1)) {
                Option o;
                o.id=lua_tostring(L,-2);
                o.key="model2emuex_lua_"+game_name+"_"+key_suffix(o.id);
                raw_field(-1,"name");
                if(lua_isstring(L,-1)) o.name=lua_tostring(L,-1);
                lua_pop(L,1);
                raw_field(-1,"values");
                if(lua_isnil(L,-1))o.labels={"Off","On"};
                if(lua_istable(L,-1)) {
                    size_t n=lua_objlen(L,-1);
                    if(n>=RETRO_NUM_CORE_OPTION_VALUES_MAX)
                        report("Lua option exceeds the frontend value limit: "+o.id);
                    else for(size_t i=1;i<=n;++i) {
                        lua_rawgeti(L,-1,(int)i);
                        if(lua_isstring(L,-1)) o.labels.emplace_back(lua_tostring(L,-1));
                        lua_pop(L,1);
                    }
                }
                lua_pop(L,1);
                if(!o.name.empty() && !o.labels.empty()) {
                    for(size_t i=0;i<o.labels.size();++i)o.numbers.push_back(std::to_string(i));
                    set_option_value(0);
                    options.emplace(o.id,o);
                }
            }
            lua_pop(L,1);
        }
    }
    lua_pop(L,1);
    for(auto &it:options) {
        auto &o=it.second;
        retro_core_option_v2_definition d{};
        d.key=o.key.c_str(); d.desc=o.name.c_str();d.category_key="lua_options";
        d.info="Declared by the current game's Lua script. Changes apply on return to the game.";
        for(size_t i=0;i<o.labels.size();++i)d.values[i]={o.numbers[i].c_str(),o.labels[i].c_str()};
        d.default_value=d.values[0].value;definitions.push_back(d);
    }
    definitions.emplace_back();
}
void callback(Option &o,const char *fn)
{
    int top=lua_gettop(L);
    raw_field(LUA_GLOBALSINDEX, "Options");
    if(lua_istable(L,-1)) {
        raw_field(-1,o.id.c_str());
        if(lua_istable(L,-1)) {
            set_option_value(o.value);
            raw_field(-1,fn);
            if(lua_isfunction(L,-1)) {
                lua_pushinteger(L,o.value);
                if(lua_pcall(L,1,0,0))error_message(fn);
            }
        }
    }
    lua_settop(L,top);
}
}

void m2lr_lua_reload()
{
    if(!L)return;
    options.clear();definitions.clear();active=false;errors.clear();
    auto file=scripts/(game_name+".lua");
    std::ifstream f(file,std::ios::binary);
    if(!f)return;
    std::string data(std::istreambuf_iterator<char>(f),{});
    if(luaL_loadbuffer(L,data.data(),data.size(),("@"+file.string()).c_str()) || lua_pcall(L,0,0,0)) {
        error_message("load");return;
    }
    active=true;read_options();
}
void m2lr_lua_open(m2_board *b,const char *system,const char *game,void (*message)(const char *))
{
    board=b;notice=message;game_name=game;
    wide=-1;stretch_bits=stretch_mask=0;initialized=false;width=496;height=384;
    if(!system) {report("Lua needs the RetroArch System directory");return;}
    scripts=fs::u8path(system)/"model2emuex"/"scripts";
    L=luaL_newstate();
    if(!L){report("Lua interpreter allocation failed");return;}
    luaL_openlibs(L);
    lua_getglobal(L,"package");
    std::string path=(scripts/"?.lua").string()+";"+(scripts/"?"/"init.lua").string();
    lua_pushstring(L,path.c_str());lua_setfield(L,-2,"path");
    lua_pop(L,1);install();m2lr_lua_reload();
}
void m2lr_lua_close()
{
    m2lr_lua_event("End");
    if(L)lua_close(L);
    L=nullptr;board=nullptr;active=false;initialized=false;options.clear();definitions.clear();errors.clear();
    lua_video_close();
}
const retro_core_option_v2_definition *m2lr_lua_options()
{
    return definitions.empty()?nullptr:definitions.data();
}
int m2lr_lua_active(){return active;}
void m2lr_lua_event(const char *event)
{
    if(!active)return;
    if(!strcmp(event,"Init")) {
        if(initialized)return;
        initialized=true;
    }
    if(!strcmp(event,"Reset") && !initialized)return;
    raw_field(LUA_GLOBALSINDEX, event);
    if(lua_isfunction(L,-1)) {
        if(lua_pcall(L,0,0,0))error_message(event);
    } else lua_pop(L,1);
    if(!strcmp(event,"Frame"))
        for(auto &it:options)if(it.second.value!=0)callback(it.second,"runfunc");
}
void m2lr_lua_sync(retro_environment_t env)
{
    if(!active || !env)return;
    unsigned version=0;
    env(RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION,&version);
    for(auto &it:options) {
        auto &o=it.second;
        retro_variable v{o.key.c_str(),nullptr};
        if(!env(RETRO_ENVIRONMENT_GET_VARIABLE,&v)||!v.value)continue;
        const auto &values=version>=2?o.numbers:o.labels;
        auto pos=std::find(values.begin(),values.end(),v.value);
        if(pos!=values.end() && o.value!=pos-values.begin()) {
            o.value=(int)(pos-values.begin()); callback(o,"changefunc");
        }
    }
}
void m2lr_lua_input(retro_input_state_t in)
{
    if(!active || !in)return;
    static const unsigned dpad[]={6,7,4,5};
    static const unsigned buttons[]={RETRO_DEVICE_ID_JOYPAD_B,RETRO_DEVICE_ID_JOYPAD_A,RETRO_DEVICE_ID_JOYPAD_Y,
        RETRO_DEVICE_ID_JOYPAD_X,RETRO_DEVICE_ID_JOYPAD_L,RETRO_DEVICE_ID_JOYPAD_R,RETRO_DEVICE_ID_JOYPAD_L2,RETRO_DEVICE_ID_JOYPAD_R2};
    for(unsigned p=0;p<joystick.size();++p) {
        for(unsigned i=0;i<4;++i)joystick[p][i]=in(p,RETRO_DEVICE_JOYPAD,0,dpad[i])!=0;
        for(unsigned axis=0;axis<4;++axis) {
            auto value=in(p,RETRO_DEVICE_ANALOG,axis/2,axis%2);
            joystick[p][4+axis*2]=value<-16384;joystick[p][5+axis*2]=value>16384;
        }
        for(unsigned i=0;i<8;++i)joystick[p][16*(i+1)]=in(p,RETRO_DEVICE_JOYPAD,0,buttons[i])!=0;
    }
}
void m2lr_lua_wide(m2_wide_state *state)
{
    if(!active)return;
    if(wide>=0)state->widescreen=wide;
    state->stretch=(state->stretch&~stretch_mask)|stretch_bits;
}
void m2lr_lua_size(unsigned w,unsigned h){width=w;height=h;}
