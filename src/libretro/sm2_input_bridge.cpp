// Destination wiring for the unchanged SM2 input profiles and metadata.
#include "sm2_input_bridge.h"
#include "sm2/input.h"
#include "sm2/rumble.h"
#include "sm2_overlay.h"
#include "sm2/include/rom/game_db.h"
#include "sm2/data/games_xml.inc"
#include "m2/m2board.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <unistd.h>
#include <cstring>
#include <deque>
#include <optional>
#include <string>
#include <vector>

namespace {
using namespace sm2;
using namespace sm2::libretro;
retro_environment_t env;
rom::GameDatabase database;
std::optional<rom::GameSpec> game;
InputRuntime runtime;
CrosshairPresentation crosshairs;
CrosshairState crosshair_current,crosshair_previous;
bool artwork_directory, artwork_directory_notice;
hw::Inputs inputs;
InputDevices devices{RETRO_DEVICE_JOYPAD,RETRO_DEVICE_JOYPAD,RETRO_DEVICE_JOYPAD,RETRO_DEVICE_JOYPAD};
ControllerConfiguration controllers;
std::vector<retro_input_descriptor> bindings;
std::deque<std::string> option_value_label_storage;
std::string presentation;
bool automatic_start=true;
retro_input_state_t state;
GamepadRumble rumble;
retro_set_rumble_state_t frontend_rumble;
bool rumble_enabled=true;
std::array<uint16_t,2> motor_levels{};
std::vector<uint8_t> drive_writes;
bool output_rumble(unsigned port,enum retro_rumble_effect motor,uint16_t level) {
    if(port || motor>RETRO_RUMBLE_WEAK)return false;
    motor_levels[static_cast<unsigned>(motor)]=level;
    return frontend_rumble && frontend_rumble(port,motor,rumble_enabled?level:0);
}
bool rumble_environment(unsigned cmd,void *data) {
    if(cmd==RETRO_ENVIRONMENT_GET_RUMBLE_INTERFACE) {
        retro_rumble_interface actual{};
        frontend_rumble=env && env(cmd,&actual)?actual.set_rumble_state:nullptr;
        static_cast<retro_rumble_interface*>(data)->set_rumble_state=output_rumble;
        return true;
    }
    return env && env(cmd,data);
}
const char *variable(const char *key) {
    retro_variable v{key,nullptr};
    return env && env(RETRO_ENVIRONMENT_GET_VARIABLE,&v)?v.value:nullptr;
}
bool is(const char *key,const char *value) {
    const char *v=variable(key);return v && std::strcmp(v,value)==0;
}
unsigned number(const char *key,unsigned fallback,unsigned lo,unsigned hi,unsigned step=1) {
    const char *v=variable(key);if(!v || !*v)return fallback;
    char *end=nullptr;const auto n=std::strtoul(v,&end,10);
    return end && !*end && n>=lo && n<=hi && (n-lo)%step==0 ? static_cast<unsigned>(n):fallback;
}
GunInputMode gun_mode() {
    if(is("model2emuex_gun_input","lightgun"))return GunInputMode::Lightgun;
    if(is("model2emuex_gun_input","mouse_analog"))return GunInputMode::MouseAnalog;
    if(is("model2emuex_gun_input","mouse"))return GunInputMode::Mouse;
    if(is("model2emuex_gun_input","analog"))return GunInputMode::AnalogSticks;
    return GunInputMode::Hybrid;
}
bool load_database() {
    // The reference's load_from_string helper is test-only and uses a shared
    // temporary filename. Use an exclusively owned file with the unchanged parser.
    std::string pattern=(std::filesystem::temp_directory_path()/"model2emuex-metadata-XXXXXX").string();
    std::vector<char> path(pattern.begin(),pattern.end());path.push_back(0);
    const int descriptor=mkstemp(path.data());if(descriptor<0)return false;
    std::FILE *file=fdopen(descriptor,"wb");
    if(!file) {close(descriptor);unlink(path.data());return false;}
    const bool wrote=std::fwrite(sm2_games_xml,1,sizeof(sm2_games_xml)-1,file)==sizeof(sm2_games_xml)-1;
    const bool closed=std::fclose(file)==0;
    bool loaded=false;
    try { if(wrote && closed)loaded=database.load(path.data()); }
    catch(...) { unlink(path.data());throw; }
    unlink(path.data());return loaded;
}
std::vector<uint32_t> program(const m2_game *g) {
    std::vector<uint32_t> crcs;unsigned region=~0u;
    for(auto e=g->roms;e->type>=0;++e) {
        if(e->type==0)region=e->arg&255;
        if(e->type==1 && region==0)crcs.push_back(e->crc);
    }
    std::sort(crcs.begin(),crcs.end());return crcs;
}
std::vector<uint32_t> program(const rom::GameSpec &g) {
    std::vector<uint32_t> crcs;
    for(const auto &r:g.regions)if(r.name=="maincpu")
        for(const auto &f:r.files)crcs.push_back(f.has_crc?f.crc32:0);
    std::sort(crcs.begin(),crcs.end());return crcs;
}
bool same_wiring(const m2_game *a,const m2_game *b) {
    if(!b || a->input_fn!=b->input_fn || std::strcmp(a->board,b->board))return false;
    const auto *x=a->inputs,*y=b->inputs;
    for(;x->kind>=0 && y->kind>=0;++x,++y)
        if(x->kind!=y->kind || x->port!=y->port || x->mask!=y->mask || std::strcmp(x->name,y->name))return false;
    return x->kind==y->kind;
}
void initialize() {
    runtime={};inputs={};crosshairs.reset_activity();crosshair_current={};crosshair_previous={};
    if(!game)return;
    for(unsigned i=0;i<inputs.analog.size();++i)inputs.analog[i]=game->analog[i].rest;
    inputs.gun_p1x=game->lightgun.p1x.rest;inputs.gun_p1y=game->lightgun.p1y.rest;
    inputs.gun_p2x=game->lightgun.p2x.rest;inputs.gun_p2y=game->lightgun.p2y.rest;
}
// Framework F09: these single-view profiles have no independent D-Pad Down
// action. Preserve Up/Start aliases and provide the same native action on Down.
bool down_is_view() {
    if(!game)return false;
    const auto profile=recognize_profile(*game);
    return profile==InputProfile::JoystickAnalogSkyTarget
        || profile==InputProfile::SpecialWaveRunner
        || profile==InputProfile::DrivingSequentialMotorRaid;
}
int16_t frontend_input(unsigned port,unsigned device,unsigned index,unsigned id) {
    if(!state)return 0;
    auto value=state(port,device,index,id);
    if(down_is_view() && port==0
       && device==RETRO_DEVICE_JOYPAD && id==RETRO_DEVICE_ID_JOYPAD_UP)
        value=static_cast<int16_t>(value || state(port,device,index,RETRO_DEVICE_ID_JOYPAD_DOWN));
    return value;
}
uint8_t fighting_port(uint8_t value) {
    // SM2 Punch/Kick/Guard bits 0/1/2 -> native Guard/Punch/Kick bits 0/1/2.
    return static_cast<uint8_t>((value&0xf8)|((value&4)>>2)|((value&3)<<1));
}
unsigned range(const char *key) {
    const unsigned n=number(key,100,50,150);
    return n==50 || n==60 || n==63 || (n>=70 && n%10==0)?n:100;
}
unsigned pedal_range(const char *key) {
    if(is(key,"75.3"))return 753;
    const unsigned n=number(key,100,50,150,10);return n*10;
}
}

void sm2lr_add_input_options(std::vector<retro_core_option_v2_definition>& registered_definitions) {
    option_value_label_storage.clear();
#include "sm2_input_options.inc"
}
extern "C" void sm2lr_input_environment(retro_environment_t cb) { env=cb; }
extern "C" bool sm2lr_input_bind(m2_board *board) {
    game.reset();presentation.clear();
    try {
        if(database.empty() && !load_database())return false;
        const auto *native=board->game;
        const auto identity=program(native);
        const rom::GameSpec *found=database.find(native->name);
        if(found && program(*found)!=identity)found=nullptr;
        if(!found)for(const auto &candidate:database.games()) {
            if(program(candidate)==identity) {
                if(found)return false; // Ambiguous signatures are not aliases.
                found=&candidate;
            }
        }
        if(!found && (!std::strcmp(native->name,"daytonat") || !std::strcmp(native->name,"daytonata"))
           && same_wiring(native,m2_find_game("daytona"))) {
            found=database.find("daytona");
            if(found) { game=*found;game->name=native->name;game->parent="daytona"; }
        } else if(found)game=*found;
        if(!game || recognize_profile(*game)==InputProfile::Unsupported) {game.reset();return false;}
        automatic_start=!is("model2emuex_automatic_start_gear","disabled");
        const char *system=nullptr;
        if(env)env(RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY,&system);
        artwork_directory=system && *system;artwork_directory_notice=false;
        crosshairs.configure(*game,artwork_directory?std::filesystem::path(system)/"model2emuex"/"crosshairs":std::filesystem::path{});
        initialize();drive_writes.clear();
        rumble_enabled=!is("model2emuex_gamepad_rumble","disabled");
        (void)rumble.init(rumble_environment);
        sm2lr_input_refresh();return true;
    } catch(...) {game.reset();return false;}
}
extern "C" void sm2lr_input_reset() { rumble.stop();drive_writes.clear();initialize(); }
extern "C" void sm2lr_input_stop_rumble() { rumble.stop();drive_writes.clear();motor_levels={}; }
extern "C" void sm2lr_input_clear() { rumble.stop();drive_writes.clear();game.reset();presentation.clear();runtime={};crosshair_current={};crosshair_previous={}; }
extern "C" void sm2lr_input_device(unsigned port,unsigned device) {
    if(port<devices.size())devices[port]=device;
    if(game)sm2lr_input_refresh();
}
extern "C" const char *sm2lr_input_profile() {
    return game?profile_name(recognize_profile(*game)):"Unsupported";
}
extern "C" bool sm2lr_input_refresh() {
    if(!game || !env)return false;
    const bool test=!is("model2emuex_controller_profile_type","normal");
    const auto mode=gun_mode();
    const bool reload=!is("model2emuex_offscreen_reload_shortcut","disabled");
    std::string next=game->name+":"+std::to_string(test)+":"+std::to_string(static_cast<int>(mode))+":"+std::to_string(reload);
    for(auto d:devices)next+=":"+std::to_string(d);
    if(next==presentation)return false;
    configure_controllers(*game,controllers,mode,test);
    bindings=descriptors(*game,profile_devices(devices,test),mode,reload);
    if(down_is_view()) {
        const auto up=std::find_if(bindings.begin(),bindings.end(),[](const auto &d){return d.description && d.port==0 && d.device==RETRO_DEVICE_JOYPAD && d.id==RETRO_DEVICE_ID_JOYPAD_UP;});
        if(up!=bindings.end()) { auto down=*up;down.id=RETRO_DEVICE_ID_JOYPAD_DOWN;bindings.insert(bindings.end()-1,down); }
    }
    env(RETRO_ENVIRONMENT_SET_CONTROLLER_INFO,controllers.ports.data());
    env(RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS,bindings.data());
    presentation=std::move(next);return true;
}
extern "C" void sm2lr_input_poll(m2_board *board,retro_input_state_t callback) {
    if(!game)return;
    sm2lr_input_refresh();state=callback;
    const bool test=!is("model2emuex_controller_profile_type","normal");
    DrivingAnalogOptions driving;
    driving.steering_response=is("model2emuex_steering_response","progressive")?SteeringResponse::Progressive:
        is("model2emuex_steering_response","fbneo")?SteeringResponse::FBNeoLogarithmic:SteeringResponse::Linear;
    driving.steering_output_range=range("model2emuex_steering_output_range");
    driving.accelerator_output_range_per_mille=pedal_range("model2emuex_accelerator_output_range");
    driving.brake_output_range_per_mille=pedal_range("model2emuex_brake_output_range");
    DesertElevationOptions desert;
    desert.control=is("model2emuex_desert_elevation_control","absolute")?DesertElevationControl::Absolute:DesertElevationControl::Relative;
    desert.speed_percent=number("model2emuex_desert_elevation_speed",100,10,200,10);
    desert.inverted=is("model2emuex_desert_elevation_axis","inverted");
    SpecialAnalogOptions special;
    special.gun_stick_control=is("model2emuex_gun_stick_control","absolute")?GunStickControl::Absolute:GunStickControl::Relative;
    const unsigned neutral=number("model2emuex_gear_shift_neutral_time",100,0,500,10);
    // Preserve SM2's algorithm but round the requested duration at this board's cadence.
    const unsigned frames=static_cast<unsigned>(std::ceil(neutral*board->game->fps/1000.0));
    const unsigned source_ms=frames?static_cast<unsigned>((frames-0.5)*1000.0/57.5245):0;
    poll_input(inputs,*game,profile_devices(devices,test),runtime,
        !is("model2emuex_four_speed_shifter","standard"),frontend_input,gun_mode(),
        !is("model2emuex_offscreen_reload_shortcut","disabled"),driving,desert,automatic_start,
        is("model2emuex_mouse_edge_offscreen_reload","enabled"),special,source_ms);
    const uint8_t ports[]={inputs.in0,inputs.in1,inputs.in2,inputs.in3,inputs.in4};
    for(unsigned p=0;p<8;++p)board->port[p]=static_cast<uint8_t>(board->game->port_defaults[p] & (p<5?ports[p]:0xff));
    std::copy(inputs.analog.begin(),inputs.analog.end(),board->analog);
    const auto profile=recognize_profile(*game);
    if(profile==InputProfile::Fighting) {
        board->port[1]=fighting_port(inputs.in1)&board->game->port_defaults[1];
        board->port[2]=fighting_port(inputs.in2)&board->game->port_defaults[2];
    }
    if(board->type==0) {
        board->port[5]=inputs.in0&board->game->port_defaults[5];
        if(!game->lightgun.present) {
            board->port[2]=inputs.analog[0];board->port[0]=inputs.analog[1];board->port[1]=inputs.analog[2];
            board->port[6]=inputs.in1&board->game->port_defaults[6];
            if(profile==InputProfile::SpecialDesertTank)
                board->port[6]=static_cast<uint8_t>((board->port[6]&~1u)|(inputs.in1&1));
        }
    }
    if(game->gearbox) {
        static constexpr uint8_t codes[]={0,0x20,0x10,0x60,0x50};
        unsigned gear=0;for(unsigned i=1;i<=4;++i)if(inputs.gears&(1u<<i))gear=i;
        const unsigned port=board->type==0?6:1;
        board->port[port]=static_cast<uint8_t>((board->port[port]&0x8f)|codes[gear]);
    }
    if(profile==InputProfile::Driving4SpeedVR1Handbrake)board->port[2]=inputs.in2;
    // The SM2/MAME IN2 lane is Sega Rally's handbrake. The standalone
    // adapter synthesizes drive readback here; this frontend supplies the real
    // native input lane instead, leaving drive command state independent.
    if(game->lightgun.present) {
        // Invert the native serial-I/O offsets so the actual counters match SM2,
        // including the native X high-byte +0x100 carry convention.
        board->gun_xy[0]=static_cast<uint32_t>(inputs.gun_p1x)-0xadu;
        board->gun_xy[1]=static_cast<uint32_t>(inputs.gun_p1y)-0x56u;
        board->gun_xy[2]=static_cast<uint32_t>(inputs.gun_p2x)-0xadu;
        board->gun_xy[3]=static_cast<uint32_t>(inputs.gun_p2y)-0x56u;
        board->gun_word=static_cast<uint32_t>(~inputs.gun_offscreen)&3u;
        const bool p2=!(game->lightgun.p2_trigger_on_in2?inputs.in2&1:inputs.in1&2);
        board->port[2]=static_cast<uint8_t>((board->port[2]|1)&~(p2?1:0));
    }
}

extern "C" void sm2lr_input_drive_write(uint8_t value) {
    if(game)drive_writes.push_back(value);
}
extern "C" void sm2lr_input_feedback(retro_input_state_t callback) {
    if(!game)return;
    const bool enabled=!is("model2emuex_gamepad_rumble","disabled");
    if(enabled!=rumble_enabled) {
        rumble_enabled=enabled;
        if(frontend_rumble)for(unsigned motor=0;motor<2;++motor)
            frontend_rumble(0,static_cast<retro_rumble_effect>(motor),enabled?motor_levels[motor]:0);
    }
    const auto steering=callback && devices[0]!=RETRO_DEVICE_NONE?
        callback(0,RETRO_DEVICE_ANALOG,RETRO_DEVICE_INDEX_ANALOG_LEFT,RETRO_DEVICE_ID_ANALOG_X):0;
    // Framework F11: gate output only. Native effect state must keep updating
    // while muted and must resume without another native drive command.
    rumble.update(*game,drive_writes,static_cast<int16_t>(steering),true);
    drive_writes.clear();
}

extern "C" void sm2lr_input_presentation(double seconds) {
    crosshair_previous=crosshair_current;
    if(!game) {crosshair_current={};return;}
    unsigned mask=game->lightgun.present?1:0;
    for(unsigned i=0;i<4;++i)if(is("model2emuex_crosshairs",std::to_string(i).c_str()))mask=i;
    CrosshairStyle style=CrosshairStyle::Sm2;
    if(is("model2emuex_crosshair_style","supermodel"))style=CrosshairStyle::Supermodel;
    else if(is("model2emuex_crosshair_style","auto"))style=CrosshairStyle::Auto;
    else if(is("model2emuex_crosshair_style","custom"))style=CrosshairStyle::Custom;
    unsigned timeout=0;
    for(unsigned t:{1u,2u,3u,4u,5u,6u,7u,8u,10u,15u,30u,60u})
        if(is("model2emuex_crosshair_timeout",std::to_string(t).c_str()))timeout=t;
    if(!artwork_directory && (style==CrosshairStyle::Auto || style==CrosshairStyle::Custom)) {
        if(style==CrosshairStyle::Custom) {
            mask=0;
            if(!artwork_directory_notice && env) {
                retro_message message{"Set the frontend System/BIOS directory to load custom crosshairs.",240};
                env(RETRO_ENVIRONMENT_SET_MESSAGE,&message);artwork_directory_notice=true;
            }
        }
        style=CrosshairStyle::Sm2; // Never search the process working directory.
    }
    crosshair_current=crosshairs.update(*game,runtime,mask,style,timeout,seconds);
    auto notice=crosshairs.take_notice();
    if(!notice.empty() && env) {
        const auto pos=notice.find("system/sm2-emu/");
        if(pos!=std::string::npos)notice.replace(pos,15,"system/model2emuex/");
        retro_message message{notice.c_str(),240};env(RETRO_ENVIRONMENT_SET_MESSAGE,&message);
    }
}
extern "C" void sm2lr_input_video(unsigned width,unsigned height,bool previous_frame) {
    sm2lr_overlay_draw(crosshair_geometry(previous_frame?crosshair_previous:crosshair_current,width,height),width,height);
}

extern "C" void sm2lr_input_state_archive(m2_state *archive) {
    InputRuntime restored=runtime;
    m2_state local=*archive;
    if(local.mode==M2_STATE_CHECK)local.mode=M2_STATE_LOAD;
#define F(m) M2_FIELD(&local,&restored,m)
    F(gear); F(shift_neutral_frames); F(desert_elevation);
    F(gun_cursor_x); F(gun_cursor_y); F(gun_lightgun_x); F(gun_lightgun_y);
#undef F
    auto flag=[&](bool &field) {
        uint8_t value=field?1:0; m2_state_bytes(&local,&value,sizeof value);
        if(value>1)local.failed=1;
        if(local.mode==M2_STATE_LOAD)field=value!=0;
    };
    flag(restored.gear_initialized); flag(restored.shift_up_held); flag(restored.shift_down_held);
    flag(restored.desert_shift); flag(restored.desert_shift_held);
    for(unsigned p=0;p<2;p++) {
        flag(restored.gun_lightgun_initialized[p]); flag(restored.gun_stick_owns[p]);
        flag(restored.gun_aim_active[p]); flag(restored.gun_aim_offscreen[p]);
    }
    if(restored.gear>16 || restored.shift_neutral_frames>60 || !std::isfinite(restored.desert_elevation)
        || restored.desert_elevation<0 || restored.desert_elevation>255)local.failed=1;
    if(archive->mode==M2_STATE_LOAD && !local.failed)runtime=restored;
    archive->pos=local.pos;archive->failed=local.failed;
}
extern "C" void sm2lr_input_after_state_load() {
    rumble.stop();drive_writes.clear();motor_levels={};
    crosshairs.reset_activity();crosshair_current={};crosshair_previous={};
}
