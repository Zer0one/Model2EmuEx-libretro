#include "sm2_bridge.h"
#include "sm2/nvram_settings.h"
#include "sm2/save_ram.h"
#include "sm2/automatic_network.h"
#include "m2/m2rom.h"
#include "network_options.h"
#include <array>
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstring>
#include <iostream>
#include <map>
#include <span>
#include <string>
#include <vector>
static std::map<std::string,std::string> values;
static bool changed;
static std::map<std::string,bool> visibility;
static retro_core_options_update_display_callback_t display;
static bool environment(unsigned cmd,void *data) {
    switch(cmd) {
    case RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION: *static_cast<unsigned*>(data)=2; return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE: *static_cast<bool*>(data)=changed; changed=false; return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        changed=false; // RetroArch consuming-read behavior.
        auto *v=static_cast<retro_variable*>(data); auto i=values.find(v->key);
        v->value=i==values.end()?nullptr:i->second.c_str(); return i!=values.end();
    }
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2: {
        auto *o=static_cast<retro_core_options_v2*>(data); unsigned count=0;
        unsigned operators=0;
        for (;o->definitions[count].key;count++) {
            const auto &d=o->definitions[count];
            const std::string_view key=d.key;
            if (!key.starts_with("model2emuex_nvram_") || key=="model2emuex_nvram_settings") continue;
            unsigned defaults=0;
            for (const auto &v:d.values) {
                if (!v.value) break;
                const bool selected=std::string_view(v.value)==d.default_value;
                const bool marked=std::string_view(v.label).ends_with(" (Default)");
                assert(selected==marked);
                defaults+=marked;
            }
            assert(defaults==1); ++operators;
        }
        assert(operators==340);
        assert(count>100); return true;
    }
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_UPDATE_DISPLAY_CALLBACK:
        display=static_cast<retro_core_options_update_display_callback*>(data)->callback; return true;
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_DISPLAY: {
        auto *d=static_cast<retro_core_option_display*>(data);
        visibility[d->key]=d->visible; return true;
    }
    default:return false;
    }
}
static void check_destination_nvram_routes(bool model2c_only) {
    using namespace sm2::libretro;
    int count=0;const auto *games=m2_game_list(&count);
    size_t routes=0,variants=0,metadata=0,unseeded=0;
    for(int index=0;index<count;++index) {
        const auto &game=games[index];
        if(model2c_only && std::strcmp(game.board,"Model 2C"))continue;
        std::string title=game.title;
        std::transform(title.begin(),title.end(),title.begin(),[](unsigned char c){return std::tolower(c);});
        if(std::string_view(game.name)=="daytona93" || title.find("prototype")!=std::string::npos) {
            ++metadata;std::cout<<"NVRAM_ADAPTER "<<game.name<<" metadata_only\n";continue;
        }
        values.clear();
        values["model2emuex_initial_nvram_setup"]="disabled";
        values["model2emuex_nvram_settings"]="disabled";
        sm2lr_nvram_game(game.name,game.parent);
        const auto catalog=nvram::catalog_for_game(game.name,game.parent?game.parent:"");
        const auto options=nvram::options_for_game(catalog);
        std::array<uint8_t,0x10000> backup;backup.fill(0x5a);
        for(size_t i=kBackupRamSize;i<backup.size();++i)backup[i]=uint8_t(i*37+index);
        std::array<uint8_t,128> eeprom;eeprom.fill(0xa5);
        const auto untouched=backup;const auto untouched_e=eeprom;
        assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_UNCHANGED);
        assert(backup==untouched && eeprom==untouched_e);
        values["model2emuex_initial_nvram_setup"]="enabled";
        auto seeded=sm2lr_initial_nvram(backup.data(),eeprom.data());
        if(seeded==SM2LR_INITIAL_NVRAM_UNCHANGED) {
            assert(backup==untouched && eeprom==untouched_e);
            ++unseeded;std::cout<<"NVRAM_ADAPTER "<<game.name<<" no_template_preserves_data\n";continue;
        }
        assert(seeded==SM2LR_INITIAL_NVRAM_LOADED);
        assert(nvram::valid_layout(catalog,std::span(backup).first(kBackupRamSize),eeprom));
        auto saved=backup;auto saved_e=eeprom;
        assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==0);
        assert(backup==saved && eeprom==saved_e); // Gate disabled preserves a frontend image.
        std::vector<std::string> selected;
        for(const auto &o:options) {
            selected.emplace_back(o.default_value);
            values["model2emuex_nvram_"+std::string(o.game)+"_"+o.suffix]=o.default_value;
        }
        values["model2emuex_nvram_settings"]="enabled";
        auto expected=backup;auto expected_e=eeprom;
        (void)nvram::apply(catalog,std::span(expected).first(kBackupRamSize),expected_e,selected);
        assert(sm2lr_apply_nvram(backup.data(),eeprom.data())>=0);
        assert(backup==expected && eeprom==expected_e);
        saved=backup;saved_e=eeprom;
        size_t route_variants=0;
        for(size_t field=0;field<options.size();++field) {
            const auto &o=options[field];
            const std::string key="model2emuex_nvram_"+std::string(o.game)+"_"+o.suffix;
            for(size_t value=0;value<o.value_count;++value) {
                backup=saved;eeprom=saved_e;expected=saved;expected_e=saved_e;
                values[key]=o.values[value].key;selected[field]=o.values[value].key;
                // Adapter comparison: the imported engine (including documented
                // M29 native Sonic correction) with explicit
                // selections; destination: frontend keys through our bridge.
                const auto wanted=nvram::apply(catalog,std::span(expected).first(kBackupRamSize),expected_e,selected);
                assert(wanted==nvram::ApplyResult::Changed || wanted==nvram::ApplyResult::Unchanged);
                assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==(wanted==nvram::ApplyResult::Changed?1:0));
                assert(backup==expected && eeprom==expected_e);
                assert(nvram::valid_layout(catalog,std::span(backup).first(kBackupRamSize),eeprom));
                assert(std::equal(backup.begin()+kBackupRamSize,backup.end(),untouched.begin()+kBackupRamSize));
                const auto repeated=sm2lr_apply_nvram(backup.data(),eeprom.data());
                if(repeated!=0) {
                    const auto reference_repeat=nvram::apply(catalog,std::span(expected).first(kBackupRamSize),expected_e,selected);
                    std::cerr<<"NVRAM repeat: "<<game.name<<" "<<o.suffix<<"="<<o.values[value].key
                             <<" destination="<<repeated<<" reference="<<int(reference_repeat)<<'\n';
                }
                assert(repeated==0);
                assert(backup==expected && eeprom==expected_e);
                ++route_variants;
            }
            values[key]=o.default_value;selected[field]=o.default_value;
        }
        ++routes;variants+=route_variants;
        std::cout<<"NVRAM_ADAPTER "<<game.name<<' '<<catalog<<' '<<options.size()<<' '<<route_variants<<" values_match_sm2\n";
    }
    sm2lr_nvram_game(nullptr,nullptr);
    std::cout<<"PASS: destination bridge routes="<<routes<<", value cases="<<variants
             <<", unseeded="<<unseeded<<", prototype metadata only="<<metadata<<"; no ROM/game execution\n";
}
int main(int argc,char **argv) {
    assert(argc==1 || (argc==2 && std::strcmp(argv[1],"--model2c")==0));
    const bool model2c_only=argc==2;
    using namespace sm2::libretro;
    // Every prepared destination role must map to existing reviewed fields and
    // values, including boards which cannot execute yet. No guessed encoding.
    for(const auto &g:model2lr::network_games) {
        const auto options=nvram::options_for_game(g.mapping);
        assert(!options.empty());
        for(const auto &choice:network::choices(g.mapping,g.maximum)) {
            const auto mappings=network::managed_values(g.mapping,g.maximum,choice.key);
            for(const auto &target:mappings) {
                auto o=std::find_if(options.begin(),options.end(),[&](const auto &v){return target.suffix==v.suffix;});
                assert(o!=options.end());
                assert(std::any_of(o->values,o->values+o->value_count,[&](const auto &v){return target.key==v.key;}));
            }
        }
    }
    retro_core_option_v2_definition native[]={{}};
    retro_core_option_v2_category cats[]={{"system","System",nullptr},{}};
    assert(sm2lr_register_options(environment,native,cats));
    assert(!visibility.at("model2emuex_nvram_settings")); // No active catalogue yet.
    sm2lr_nvram_game("vf2","model2");
    assert(visibility.at("model2emuex_nvram_settings"));
    for (const auto &[key,visible]:visibility)
        if (std::string_view(key).starts_with("model2emuex_nvram_") && key!="model2emuex_nvram_settings") assert(!visible); // Gate disabled.
    assert(display && !display()); // Unchanged state must not request another refresh.
    std::array<uint8_t,0x10000> backup; backup.fill(0xa5);
    std::array<uint8_t,128> eeprom{};
    assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_LOADED);
    assert(nvram::valid_layout("vf2",std::span(backup).first(kBackupRamSize),eeprom));
    for(size_t i=kBackupRamSize;i<backup.size();i++) assert(backup[i]==0xa5);
    const auto initial=backup; const auto initial_e=eeprom;
    const auto opts=nvram::options_for_game("vf2");
    const nvram::Option *target=nullptr; const char *target_value=nullptr;
    for (const auto &o:opts) {
        for(size_t i=0;i<o.value_count;i++) {
            auto b=backup;auto e=eeprom;std::vector<std::string> s(opts.size());
            s[&o-opts.data()]=o.values[i].key;
            if(nvram::apply("vf2",std::span(b).first(kBackupRamSize),e,s)==nvram::ApplyResult::Changed) {
                target=&o;target_value=o.values[i].key;break;
            }
        }
        if(target)break;
    }
    assert(target);
    const std::string key="model2emuex_nvram_vf2_"+std::string(target->suffix);
    values[key]=target_value;
    assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==0);
    assert(backup==initial && eeprom==initial_e); // Disabled preserves native choices.
    values["model2emuex_nvram_settings"]="enabled";
    changed=true;assert(display);display(); // Paused reads must retain update.
    assert(visibility.at(key));
    for (const auto &[option,visible]:visibility) {
        if (!std::string_view(option).starts_with("model2emuex_nvram_") || option=="model2emuex_nvram_settings") continue;
        assert(visible==std::string_view(option).starts_with("model2emuex_nvram_vf2_"));
    }
    assert(sm2lr_options_changed());
    assert(!sm2lr_options_changed());
    assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==1);
    assert(nvram::valid_layout("vf2",std::span(backup).first(kBackupRamSize),eeprom));
    assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==0); // No repeated reset.
    for(size_t i=kBackupRamSize;i<backup.size();i++) assert(backup[i]==0xa5);
    values["model2emuex_nvram_settings"]="disabled";
    const auto before=backup;const auto before_e=eeprom;
    values[key]="invalid";
    assert(sm2lr_apply_nvram(backup.data(),eeprom.data())==0);
    assert(backup==before && eeprom==before_e);
    values["model2emuex_initial_nvram_setup"]="disabled";
    backup.fill(0x5a);eeprom.fill(0x5a);
    assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_UNCHANGED);
    assert(backup.front()==0x5a && eeprom.front()==0x5a);
    values["model2emuex_initial_nvram_setup"]="enabled";
    // No guessed parent template or native Daytona setup for unmatched hacks.
    for (const char *game:{"daytonat","daytonata"}) {
        sm2lr_nvram_game(game,"daytona");
        backup.fill(0x5a);eeprom.fill(0x5a);
        const auto untouched=backup;const auto untouched_e=eeprom;
        assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_UNCHANGED);
        assert(backup==untouched && eeprom==untouched_e);
    }
    sm2lr_nvram_game("daytonam","daytona"); // Explicitly compatible SM2 parent.
    assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_LOADED);
    assert(nvram::valid_layout("daytona",std::span(backup).first(kBackupRamSize),eeprom));
    sm2lr_nvram_game("daytona93","daytona"); // Exact template under canonical MAME ID.
    assert(sm2lr_initial_nvram(backup.data(),eeprom.data())==SM2LR_INITIAL_NVRAM_LOADED);
    assert(nvram::valid_layout("daytona93",std::span(backup).first(kBackupRamSize),eeprom));
    values["model2emuex_nvram_settings"]="enabled";
    sm2lr_nvram_game("unsupported",nullptr);
    assert(!visibility.at("model2emuex_nvram_settings"));
    for (const auto &[option,visible]:visibility) if(std::string_view(option).starts_with("model2emuex_nvram_")) assert(!visible);
    sm2lr_nvram_game("vf2","model2");
    assert(visibility.at("model2emuex_nvram_settings") && visibility.at(key));
    sm2lr_nvram_game(nullptr,nullptr);
    assert(!visibility.at("model2emuex_nvram_settings"));
    check_destination_nvram_routes(model2c_only);
    std::cout<<"PASS: SM2 default labels/master visibility, complete reference catalogue ("<<sm2lr_nvram_option_count()
        <<" options), SM2-only exact/compatible-parent seeding, unmatched-save preservation, gate, paused update retention, apply-once and tail preservation\n";
}
