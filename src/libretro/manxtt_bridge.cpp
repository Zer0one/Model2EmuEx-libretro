//  ____  __  __  ____         _____ __  __ _   _
// / ___||  \/  ||___ \       | ____|  \/  | | | |
// \___ \| |\/| |  __) |_____ |  _| | |\/| | | | |
//  ___) | |  | | / __/|_____|| |___| |  | | |_| |
// |____/|_|  |_||_____|      |_____|_|  |_|\___/
//
// A Sega Model 2 arcade emulator.
// Copyright (c) 2025+ Daniel Martin (dmanlfc)
// SPDX-License-Identifier: GPL-3.0-or-later AND BSD-3-Clause
//
// This header must not be removed. sm2-emu is licensed under the GNU General
// Public License, version 3 or later, with additional terms under section 7 of
// that licence. See LICENSE and NOTICE.
//
//
// See model2_sound.h.

// Policy and mixer adapted from SM2 src/libretro/manxtt_audio.cpp and
// src/hw/model2_sound.cpp. Machine execution remains in port/snd.
#include "manxtt_bridge.h"
#include "sm2/nvram_settings.h"
#include "snd/m2uart.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <deque>
#include <string>
#include <zlib.h>

namespace {
#include "data/manxtt_sound.inc"
struct CabinetAudio {
    m2_board *board=nullptr;
    m2_snd *main=nullptr,*aux=nullptr;
    m2_regions banks[3]{},extra{};
    bool available[3]{true,false,false},enabled=false,aux_notice=false;
    unsigned bank=0,host_phase=0;
    uint64_t phase=0;
    int last_cabinet=-1,last_request=-1,missing_notice=-1;
    std::deque<uint32_t> samples;
    std::string notice;
} cabinet;
void reset_mix() {
    cabinet.samples.assign(32,0);cabinet.phase=0;cabinet.host_phase=0;
}
uint32_t identity(unsigned bank) {
    uint32_t crc=0;
    for(const auto *regions:{&cabinet.banks[bank],&cabinet.extra})
        for(unsigned i:{5u,6u})if(regions->ptr[i])
            crc=(uint32_t)crc32(crc,regions->ptr[i],regions->size[i]);
    return crc;
}
bool load(const m2_rom_entry *roms,const char *const *dirs,m2_regions *out) {
    // Selected archive first, then SM2's manxttc/manxtt/manxttdx sibling order.
    const char *sets[3]={cabinet.board->game->name,nullptr,nullptr};unsigned n=1;
    for(const char *s:{"manxttc","manxtt","manxttdx"})
        if(std::strcmp(s,sets[0]))sets[n++]=s;
    m2_game view{};view.name=sets[0];view.parent=sets[1];view.shared=sets[2];view.roms=roms;
    if(m2_load_roms_with_policy(&view,dirs,out,nullptr,M2_ROM_CRC_METADATA|M2_ROM_CRC_CONTENTS)) {
        m2_free_roms(out);return false;
    }
    return true;
}
void bind(unsigned bank) {
    const auto &rom=cabinet.banks[bank];
    m2snd_bind_roms(cabinet.main,rom.ptr[5],rom.size[5],rom.ptr[6],rom.size[6]);
    cabinet.bank=bank;
}
}
extern "C" bool m2lr_manxtt_prepare(m2_board *b,m2_snd *main,const char *const *dirs) {
    m2lr_manxtt_destroy();
    if(!b->manxtt_audio)return true;
    cabinet.board=b;cabinet.main=main;
    cabinet.banks[0].ptr[5]=b->rom.ptr[5];cabinet.banks[0].size[5]=b->rom.size[5];
    cabinet.banks[0].ptr[6]=b->rom.ptr[6];cabinet.banks[0].size[6]=b->rom.size[6];
    cabinet.available[1]=load(twin_roms,dirs,&cabinet.banks[1]);
    cabinet.available[2]=load(deluxe_roms,dirs,&cabinet.banks[2]);
    if(load(auxiliary_roms,dirs,&cabinet.extra)) {
        cabinet.aux=m2snd_create_aux(cabinet.extra.ptr[5],cabinet.extra.size[5],cabinet.extra.ptr[6],cabinet.extra.size[6]);
        if(!cabinet.aux)return false;
        m2snd_set_reply(cabinet.aux,m2_sound_reply,b);
    }
    m2snd_set_reply(main,m2_sound_reply,b);
    cabinet.enabled=cabinet.aux && std::strcmp(b->game->name,"manxttc");
    reset_mix();return true;
}
extern "C" void m2lr_manxtt_destroy() {
    if(cabinet.aux)m2snd_destroy(cabinet.aux);
    for(unsigned i=1;i<=2;i++)m2_free_roms(&cabinet.banks[i]);
    m2_free_roms(&cabinet.extra);cabinet=CabinetAudio{};
}
extern "C" bool m2lr_manxtt_present() { return cabinet.board!=nullptr; }
extern "C" void m2lr_manxtt_command(uint8_t cmd) {
    if(cabinet.enabled)m2snd_command(cabinet.aux,cmd);
}
extern "C" const char *m2lr_manxtt_update(bool enabled,bool *changed) {
    *changed=false;if(!cabinet.board)return nullptr;
    auto *b=cabinet.board;
    if(sm2::libretro::nvram::valid_layout("manxtt",{b->back,0x4000},{b->eeprom.data,128})) {
        uint8_t value=b->eeprom.data[0x0a];if(value<=1)cabinet.last_cabinet=value;
    }
    if(cabinet.last_cabinet<0)return nullptr;
    unsigned requested=!enabled?0:cabinet.last_cabinet==1?1:2;
    unsigned selected=cabinet.available[requested]?requested:0;
    bool extra=cabinet.last_cabinet==0 && cabinet.aux;
    if(selected!=cabinet.bank) {
        bind(selected);m2snd_reset(cabinet.main);
        if(cabinet.aux)m2snd_reset(cabinet.aux);
        reset_mix();*changed=true;
    }
    if(extra!=cabinet.enabled) {
        cabinet.enabled=extra;if(cabinet.aux)m2snd_reset(cabinet.aux);
        reset_mix();*changed=true;
    }
    cabinet.notice.clear();
    if(!cabinet.available[requested] && cabinet.missing_notice!=(int)requested) {
        cabinet.missing_notice=(int)requested;
        cabinet.notice="Manx TT: matching cabinet audio ROMs unavailable; using selected set audio";
    } else if(cabinet.last_cabinet==0 && !cabinet.aux && !cabinet.aux_notice) {
        cabinet.aux_notice=true;cabinet.notice="Manx TT: Deluxe additional sound ROMs unavailable";
    } else if(cabinet.last_request!=(int)requested || *changed) {
        cabinet.notice=std::string("Manx TT audio: ")+(selected==1?"Twin":selected==2?"Deluxe":"Selected Set")
            +(cabinet.enabled?"; additional Deluxe board connected":"");
    }
    cabinet.last_request=(int)requested;
    return cabinet.notice.empty()?nullptr:cabinet.notice.c_str();
}
extern "C" void m2lr_manxtt_reset() {
    if(cabinet.aux)m2snd_reset(cabinet.aux);reset_mix();
}
extern "C" void m2lr_manxtt_gains(unsigned pcm1,unsigned pcm2,unsigned fm) {
    if(cabinet.aux)m2snd_set_gains(cabinet.aux,100,pcm1,pcm2,fm);
}
extern "C" void m2lr_manxtt_mix(int16_t *out,unsigned frames) {
    if(!cabinet.enabled)return;
    constexpr uint64_t denominator=560ull*44100;
    for(unsigned i=0;i<frames;i++) {
        cabinet.host_phase+=25000000;
        unsigned cycles=cabinet.host_phase/44100;cabinet.host_phase%=44100;
        int16_t input[16];unsigned count=m2snd_run_aux(cabinet.aux,cycles,input);
        for(unsigned k=0;k<count;k++)cabinet.samples.push_back((uint16_t)input[k*2]|((uint32_t)(uint16_t)input[k*2+1]<<16));
        if(cabinet.samples.size()<2)continue;
        for(unsigned ch=0;ch<2;ch++) {
            int64_t first=(int16_t)(cabinet.samples[0]>>(ch*16));
            int64_t second=(int16_t)(cabinet.samples[1]>>(ch*16));
            int64_t value=first+(second-first)*(int64_t)cabinet.phase/(int64_t)denominator;
            out[i*2+ch]=(int16_t)std::clamp<int64_t>(out[i*2+ch]+value,-32768,32767);
        }
        cabinet.phase+=25000000;
        while(cabinet.phase>=denominator) { cabinet.phase-=denominator;if(!cabinet.samples.empty())cabinet.samples.pop_front(); }
    }
}
extern "C" void m2lr_manxtt_state_header(uint8_t reserved[20]) {
    reserved[6]=(uint8_t)cabinet.bank;reserved[7]=cabinet.aux?1:0;
    uint32_t crc=identity(cabinet.bank);memcpy(reserved+8,&crc,4);memcpy(reserved+12,"AUD1",4);
}
extern "C" bool m2lr_manxtt_state_compatible(const uint8_t reserved[20]) {
    uint32_t crc;memcpy(&crc,reserved+8,4);const uint8_t zero[4]{};
    return cabinet.board && reserved[6]<=2 && cabinet.available[reserved[6]]
        && reserved[7]==(cabinet.aux?1:0) && !memcmp(reserved+12,"AUD1",4)
        && !memcmp(reserved+16,zero,4) && crc==identity(reserved[6]);
}
extern "C" void m2lr_manxtt_state_bind(const uint8_t *reserved) {
    if(!cabinet.board)return;
    bind(reserved?reserved[6]:0);
    if(!reserved) { cabinet.enabled=false;m2uart_reset(cabinet.board->sound_uart);cabinet.board->ams_enabled=0;cabinet.board->ams_response=0xff;
        m2snd_reset_midi(cabinet.main);m2lr_manxtt_reset(); }
}
extern "C" void m2lr_manxtt_state_archive(m2_state *a) {
    m2_cabinet_state_archive(cabinet.board,a);m2snd_midi_state_archive(cabinet.main,a);
    uint8_t enabled=cabinet.enabled?1:0;unsigned host=cabinet.host_phase;
    uint64_t phase=cabinet.phase;uint32_t count=(uint32_t)cabinet.samples.size();
    m2_state_value(a,&enabled,1);m2_state_value(a,&host,sizeof host);m2_state_value(a,&phase,sizeof phase);
    m2_state_value(a,&count,sizeof count);
    if(enabled>1 || (enabled && !cabinet.aux) || host>=44100 || phase>=560ull*44100 || count>128)a->failed=1;
    std::array<uint32_t,128> values{};
    if(a->mode==M2_STATE_SAVE)std::copy(cabinet.samples.begin(),cabinet.samples.end(),values.begin());
    if(!a->failed)m2_state_value(a,values.data(),count*sizeof(uint32_t));
    if(cabinet.aux)m2snd_aux_state_archive(cabinet.aux,a);
    if(a->mode==M2_STATE_LOAD && !a->failed) {
        cabinet.enabled=enabled;cabinet.host_phase=host;cabinet.phase=phase;
        cabinet.samples.assign(values.begin(),values.begin()+count);
    }
}
