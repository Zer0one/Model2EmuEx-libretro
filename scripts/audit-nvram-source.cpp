// Source-level routing/template probe. Reuses the unchanged SM2 public APIs.
// No ROMs, frontend sessions, disk saves or native game execution.
#include "nvram_settings.h"
#include "initial_nvram.h"
#include "save_ram.h"
#include "menu_wording.h"
#include <algorithm>
#include <array>
#include <iostream>
#include <string>
int main(int argc,char **argv) {
    using namespace sm2::libretro;
    if(argc==2 && std::string_view(argv[1])=="--labels") {
        std::string value;
        while(std::getline(std::cin,value))std::cout<<retroarch_option_label(value)<<'\n';
        return 0;
    }
    if(argc!=4)return 2;
    const std::string game=argv[1],parent=argv[2];
    const auto catalog=nvram::catalog_for_game(game,parent);
    const auto source=initial_nvram::has_template(game)?game:
        initial_nvram::can_use_parent_template(game) && initial_nvram::has_template(parent)?parent:"";
    const auto options=nvram::options_for_game(catalog);
    const auto initial=nvram::initial_values(catalog);
    std::cout<<catalog<<'\t'<<source<<'\t'<<options.size()<<'\t';
    // Preserve existing prototype metadata; no new prototype qualification.
    if(std::string_view(argv[3])=="metadata" || source.empty()) {
        std::cout<<"not_checked\t";
    } else {
        std::array<sm2::u8,0x10000> backup;backup.fill(0xa5);
        std::array<sm2::u8,kEepromSize> eeprom{};
        auto view=std::span(backup).first(kBackupRamSize);
        if(initial_nvram::seed(source,view,eeprom)!=initial_nvram::SeedResult::Loaded)return 3;
        if(!options.empty()) {
            if(!nvram::valid_layout(catalog,view,eeprom))return 4;
            const auto result=nvram::apply(catalog,view,eeprom,initial);
            if(result!=nvram::ApplyResult::Changed && result!=nvram::ApplyResult::Unchanged)return 5;
            if(!nvram::valid_layout(catalog,view,eeprom))return 6;
        }
        if(!std::all_of(backup.begin()+kBackupRamSize,backup.end(),[](auto b){return b==0xa5;}))return 7;
        std::cout<<"valid_seed_policy_and_preserved_tail\t";
    }
    for(size_t i=0;i<initial.size();i++)
        if(!initial[i].empty())std::cout<<options[i].suffix<<'='<<initial[i]<<';';
    std::cout<<'\n';
}
