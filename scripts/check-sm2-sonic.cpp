// M29 regression: the original Sonic menu has two selectors sharing one word.
// Native callback/table evidence and existing SM2 samples: NVRAM_SOURCE_REVIEW.md.
#include "sm2/nvram_settings.h"
#include "sm2/initial_nvram.h"
#include "sm2/save_ram.h"
#include <array>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

int main()
{
    using namespace sm2;
    using namespace sm2::libretro;
    constexpr const char* keys[] = {"easy", "normal", "hard", "hardest"};
    // Independently executed native callback outputs, in selector order.
    constexpr u16 native[2][4] = {{176,160,144,128}, {220,200,180,160}};
    size_t cases = 0;
    for (const char* game : {"schamp", "sfight"}) {
        std::array<u8,kBackupRamSize> backup{};
        std::array<u8,kEepromSize> eeprom{};
        assert(initial_nvram::seed(game,backup,eeprom) == initial_nvram::SeedResult::Loaded);
        const auto seed=backup;
        const auto seed_e=eeprom;
        const auto options=nvram::options_for_game(game);
        size_t fields[2]={options.size(),options.size()};
        for(size_t i=0;i<options.size();++i) {
            if(options[i].suffix==std::string_view("energy_1p"))fields[0]=i;
            if(options[i].suffix==std::string_view("energy_vs"))fields[1]=i;
        }
        assert(fields[0]<fields[1] && fields[1]<options.size());
        for(unsigned old1=0;old1<4;++old1)for(unsigned oldvs=0;oldvs<4;++oldvs)
        for(unsigned new1=0;new1<4;++new1)for(unsigned newvs=0;newvs<4;++newvs)
        for(unsigned enabled=1;enabled<=3;++enabled) {
            backup=seed;eeprom=seed_e;
            backup[0x3343]=old1;backup[0x3344]=oldvs;
            // Keep a non-table word to prove no-op selections preserve native
            // history, while a real edit writes the full word, clearing high bits.
            backup[0x3354]=0x7b;backup[0x3355]=0x12;
            const u16 crc=crc16_ccitt(std::span(backup).subspan(0x3340,32));
            backup[0x3302]=crc;backup[0x3303]=crc>>8;
            const auto before=backup;
            std::vector<std::string> selected(options.size());
            if(enabled&1)selected[fields[0]]=keys[new1];
            if(enabled&2)selected[fields[1]]=keys[newvs];
            u16 expected=0x127b;
            const bool one=(enabled&1)&&old1!=new1,vs=(enabled&2)&&oldvs!=newvs;
            if(one)expected=native[0][new1];
            if(vs)expected=native[1][newvs];
            assert(nvram::apply(game,backup,eeprom,selected)==
                (one||vs?nvram::ApplyResult::Changed:nvram::ApplyResult::Unchanged));
            assert((backup[0x3354]|(backup[0x3355]<<8))==expected);
            assert(backup[0x3343]==((enabled&1)?new1:old1));
            assert(backup[0x3344]==((enabled&2)?newvs:oldvs));
            assert(nvram::valid_layout(game,backup,eeprom));
            assert(eeprom==seed_e);
            for(size_t i=0;i<backup.size();++i)
                if(i!=0x3302&&i!=0x3303&&i!=0x3343&&i!=0x3344&&i!=0x3354&&i!=0x3355)
                    assert(backup[i]==before[i]);
            const auto applied=backup;
            assert(nvram::apply(game,backup,eeprom,selected)==nvram::ApplyResult::Unchanged);
            assert(backup==applied);
            ++cases;
        }
    }
    std::cout<<"PASS: Sonic native selector transitions, partial edits, shared-word order, integrity and idempotence: "<<cases<<" cases\n";
}
