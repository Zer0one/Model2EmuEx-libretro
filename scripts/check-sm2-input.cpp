#include "sm2_input_bridge.h"
#include "m2/m2board.h"
#include <array>
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <map>
#include <string>
#include <vector>
static std::map<std::string,std::string> options;
static std::array<std::array<int16_t,16>,4> buttons{};
static std::array<std::array<int16_t,6>,4> axes{};
static std::array<std::array<int16_t,20>,4> guns{};
static std::vector<std::string> descriptions;
static unsigned service_reads,republished;
static std::array<uint16_t,2> motors{};
static bool set_motor(unsigned port,enum retro_rumble_effect effect,uint16_t level) {
    assert(port==0);motors[static_cast<unsigned>(effect)]=level;return true;
}
static bool environment(unsigned cmd,void *data) {
    if(cmd==RETRO_ENVIRONMENT_GET_RUMBLE_INTERFACE) {static_cast<retro_rumble_interface*>(data)->set_rumble_state=set_motor;return true;}
    if(cmd==RETRO_ENVIRONMENT_GET_VARIABLE) {
        auto *v=static_cast<retro_variable*>(data);auto found=options.find(v->key);
        v->value=found==options.end()?nullptr:found->second.c_str();return v->value;
    }
    if(cmd==RETRO_ENVIRONMENT_SET_CONTROLLER_INFO) { ++republished;return true; }
    if(cmd==RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS) {
        descriptions.clear();
        for(auto d=static_cast<retro_input_descriptor*>(data);d->description;++d)
            descriptions.emplace_back(d->description);
        return true;
    }
    return false;
}
static int16_t input(unsigned port,unsigned device,unsigned index,unsigned id) {
    assert(device!=RETRO_DEVICE_KEYBOARD);
    if(port>=4)return 0;
    if(device==RETRO_DEVICE_JOYPAD) {
        if(id==RETRO_DEVICE_ID_JOYPAD_L3 || id==RETRO_DEVICE_ID_JOYPAD_R3)++service_reads;
        return id<16?buttons[port][id]:0;
    }
    if(device==RETRO_DEVICE_ANALOG) {
        if(index==RETRO_DEVICE_INDEX_ANALOG_BUTTON) {
            if(id==RETRO_DEVICE_ID_JOYPAD_L2)return axes[port][4];
            if(id==RETRO_DEVICE_ID_JOYPAD_R2)return axes[port][5];
            return 0;
        }
        return index<2 && id<2?axes[port][index*2+id]:0;
    }
    if(device==RETRO_DEVICE_LIGHTGUN)return id<20?guns[port][id]:0;
    return 0;
}
static m2_board board;
static void bind(const char *name) {
    buttons={};axes={};guns={};board={};board.game=m2_find_game(name);assert(board.game);
    board.type=!std::strcmp(board.game->board,"Model 2")?0:!std::strcmp(board.game->board,"Model 2A")?1:2;
    assert(sm2lr_input_bind(&board));
    sm2lr_input_poll(&board,input);
}
int main() {
    sm2lr_input_environment(environment);
    int count=0;const auto *games=m2_game_list(&count);assert(count==28);
    for(int i=0;i<count;++i) {bind(games[i].name);std::cout<<games[i].name<<": "<<sm2lr_input_profile()<<'\n';}
    bind("vf2");
    buttons[0][RETRO_DEVICE_ID_JOYPAD_A]=1;sm2lr_input_poll(&board,input);
    assert(!(board.port[1]&2) && (board.port[1]&5)==5);
    buttons={};buttons[1][RETRO_DEVICE_ID_JOYPAD_B]=1;sm2lr_input_poll(&board,input);
    assert(!(board.port[2]&4) && (board.port[2]&3)==3);
    buttons={};buttons[0][RETRO_DEVICE_ID_JOYPAD_Y]=1;sm2lr_input_poll(&board,input);
    assert(!(board.port[1]&1) && (board.port[1]&6)==6);
    buttons={};buttons[0][RETRO_DEVICE_ID_JOYPAD_L3]=1;buttons[0][RETRO_DEVICE_ID_JOYPAD_R3]=1;
    sm2lr_input_poll(&board,input);assert(!(board.port[0]&0x0c));
    options["model2emuex_controller_profile_type"]="normal";
    const auto published=republished;assert(sm2lr_input_refresh() && republished==published+1);
    for(const auto &d:descriptions)assert(d!="Service" && d!="Test");
    service_reads=0;sm2lr_input_poll(&board,input);assert(service_reads==0 && (board.port[0]&0x0c)==0x0c);
    assert(!sm2lr_input_refresh());
    options["model2emuex_controller_profile_type"]="invalid";sm2lr_input_refresh();
    service_reads=0;sm2lr_input_poll(&board,input);assert(service_reads && !(board.port[0]&0x0c));
    sm2lr_input_device(0,RETRO_DEVICE_NONE);sm2lr_input_poll(&board,input);assert((board.port[0]&0x0c)==0x0c);
    sm2lr_input_device(0,RETRO_DEVICE_JOYPAD);
    bind("daytona");assert((board.port[6]&0x70)==0x50); // SM2 rolling start: gear 4.
    axes[0][2]=-32768;axes[0][3]=-32768;sm2lr_input_poll(&board,input);assert((board.port[6]&0x70)==0x20);
    axes={};sm2lr_input_poll(&board,input);
    buttons[0][RETRO_DEVICE_ID_JOYPAD_R]=1;
    for(unsigned f=0;f<6;++f) {sm2lr_input_poll(&board,input);assert((board.port[6]&0x70)==0);}
    sm2lr_input_poll(&board,input);assert((board.port[6]&0x70)==0x10);
    buttons={};buttons[0][RETRO_DEVICE_ID_JOYPAD_DOWN]=1;sm2lr_input_poll(&board,input);assert(!(board.port[5]&0x20));
    for(const char *name:{"skytargt","waverunr","motoraid","manxtt","manxttc","srallyc","srallycb"}) {
        bind(name);buttons[0][RETRO_DEVICE_ID_JOYPAD_UP]=1;sm2lr_input_poll(&board,input);
        std::array<uint8_t,8> up;std::copy_n(board.port,8,up.begin());
        buttons={};buttons[0][RETRO_DEVICE_ID_JOYPAD_DOWN]=1;sm2lr_input_poll(&board,input);
        assert(std::equal(up.begin(),up.end(),board.port));
    }
    bind("srallyc");assert(board.port[2]==0);
    buttons[0][RETRO_DEVICE_ID_JOYPAD_B]=1;sm2lr_input_poll(&board,input);assert(board.port[2]==0xff);
    buttons={};sm2lr_input_poll(&board,input);assert(board.port[2]==0);
    bind("desert");assert(board.port[6]&1);
    buttons[0][RETRO_DEVICE_ID_JOYPAD_Y]=1;sm2lr_input_poll(&board,input);assert(!(board.port[6]&1));
    bind("skytargt");buttons[0][RETRO_DEVICE_ID_JOYPAD_DOWN]=1;
    sm2lr_input_poll(&board,input);assert(!(board.port[0]&0x20));
    bind("vcop2");
    buttons[1][RETRO_DEVICE_ID_JOYPAD_B]=1;sm2lr_input_poll(&board,input);assert(!(board.port[2]&1));
    const uint32_t x=board.gun_xy[0];
    const uint32_t counter=((x-0x53)&255)|(((x+0xad)>>8)<<8);
    assert(counter>=0x89 && counter<=0x276);
    options["model2emuex_gun_input"]="lightgun";bind("vcop");
    guns[0][RETRO_DEVICE_ID_LIGHTGUN_SCREEN_X]=-32768;
    guns[0][RETRO_DEVICE_ID_LIGHTGUN_SCREEN_Y]=-32768;
    guns[0][RETRO_DEVICE_ID_LIGHTGUN_TRIGGER]=1;
    sm2lr_input_poll(&board,input);assert(!(board.port[1]&1));
    const uint32_t gx=board.gun_xy[0],gy=board.gun_xy[1];
    assert((((gx-0x53)&255)|(((gx+0xad)>>8)<<8))==0x84);
    assert(gy+0x56==0x25);
    assert((static_cast<uint8_t>(~board.gun_word)&3)==0);
    options["model2emuex_gamepad_rumble"]="disabled";bind("daytona");
    sm2lr_input_drive_write(0x57);sm2lr_input_feedback(input);assert(motors[0]==0 && motors[1]==0);
    options["model2emuex_gamepad_rumble"]="enabled";sm2lr_input_feedback(input);assert(motors[0]>0 && motors[1]>0);
    options["model2emuex_gamepad_rumble"]="disabled";sm2lr_input_feedback(input);assert(motors[0]==0 && motors[1]==0);
    sm2lr_input_drive_write(0x10);
    for(unsigned i=0;i<13;++i)sm2lr_input_feedback(input);
    options["model2emuex_gamepad_rumble"]="enabled";sm2lr_input_feedback(input);assert(motors[0]==0 && motors[1]==0);
    sm2lr_input_drive_write(0x67);sm2lr_input_feedback(input);assert(motors[0]>0);
    sm2lr_input_reset();assert(motors[0]==0 && motors[1]==0);
    sm2lr_input_clear();assert(motors[0]==0 && motors[1]==0);
    std::cout<<"PASS: all 28 profiles, native VF2 action wiring, paused profile refresh, Service/Test gate, None, H-gate/sequential delay, rolling start, VR1 Down alias, Desert shift, Rally handbrake, gun counters/P2 trigger, rumble startup-muted/mute-unmute/release/reset/unload\n";
}
