// Destination glue; the SM2 catalogue, patch/checksum engine and templates are unchanged.
#include "sm2_bridge.h"
#include "sm2_input_bridge.h"
#include "sm2/nvram_settings.h"
#include "sm2/initial_nvram.h"
#include "sm2/save_ram.h"
#include "sm2/menu_wording.h"
#include "sm2/automatic_network.h"
#include "network_options.h"
#include "net_bridge.h"
#include <algorithm>
#include <deque>
#include <span>
#include <string>
#include <vector>
#include <map>
#include <utility>

namespace {
using namespace sm2::libretro;
retro_environment_t env;
bool pending;
bool master_visible_cached, game_visible_cached;
std::string game_name, parent_name, catalogue;
std::vector<retro_core_option_v2_definition> definitions;
std::vector<retro_variable> legacy;
std::deque<std::string> strings;
std::vector<std::pair<std::string,std::string>> operator_keys;
std::vector<std::pair<std::string,std::string>> network_keys;
std::vector<network::ManagedValue> managed_applied;
std::map<std::string,std::string> handover;
std::map<std::string,std::string> handover_observed;
std::string network_visible, automation_visible;
std::vector<std::pair<std::string,std::string>> invalid_values;
std::vector<std::pair<std::string,std::string>> option_corrections;
std::vector<std::string> option_warnings;
const char *keep(std::string value) { strings.push_back(std::move(value)); return strings.back().c_str(); }
void retain_updates() {
    bool updated=false;
    if (env && env(RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE,&updated)) pending |= updated;
}
const char *variable(const char *key) {
    retain_updates();
    retro_variable v{key,nullptr};
    return env && env(RETRO_ENVIRONMENT_GET_VARIABLE,&v) ? v.value : nullptr;
}
void invalid(const std::string &key,const std::string &value) {
    const auto pair=std::make_pair(key,value);
    if(std::find(invalid_values.begin(),invalid_values.end(),pair)!=invalid_values.end())return;
    invalid_values.push_back(pair);
    option_corrections.emplace_back(key,"-1");
    option_warnings.push_back("Invalid "+key+" value '"+value+"'; using -1");
}
std::string role() {
    const auto *game=model2lr::network_game(game_name);
    if(!game)return "-1";
    const std::string key="model2emuex_automatic_network_"+game_name;
    const char *v=variable(key.c_str());
    std::string value=v?v:"-1";
    if(value=="l" || value=="s")value="r";
    for(const auto &c:network::choices(game->mapping,game->maximum))if(c.key==value)return value;
    invalid(key,value);return "-1";
}
bool managed(const nvram::Option &o) {
    const auto *g=model2lr::network_game(game_name);
    return g && network::managed_field(g->mapping,o.suffix);
}
bool enabled(const char *key, bool fallback=false) {
    const char *v=variable(key);
    if (v && std::string_view(v)=="enabled") return true;
    if (v && std::string_view(v)=="disabled") return false;
    return fallback;
}
bool update_visibility() {
    retain_updates();
    const bool master_visible=!nvram::options_for_game(catalogue).empty();
    const bool active=master_visible && enabled("model2emuex_nvram_settings");
    const std::string preset=role();
    const bool automated=preset!="-1";
    const std::string network=model2lr::network_game(game_name)?game_name:"unsupported";
    for(const auto &[key,name]:network_keys) {
        retro_core_option_display d{key.c_str(),name==network};env(RETRO_ENVIRONMENT_SET_CORE_OPTIONS_DISPLAY,&d);
    }
    retro_core_option_display master{"model2emuex_nvram_settings",master_visible};
    env(RETRO_ENVIRONMENT_SET_CORE_OPTIONS_DISPLAY,&master);
    for (const auto &[key,cat]:operator_keys) {
        bool hidden=false;
        for(const auto &o:nvram::options_for_game(catalogue))
            if(key=="model2emuex_nvram_"+std::string(o.game)+"_"+o.suffix)hidden=automated && managed(o);
        retro_core_option_display d{key.c_str(), active && cat==catalogue && !hidden};
        env(RETRO_ENVIRONMENT_SET_CORE_OPTIONS_DISPLAY,&d);
    }
    const bool changed=master_visible!=master_visible_cached || active!=game_visible_cached
        || network_visible!=network || automation_visible!=preset;
    network_visible=network;automation_visible=preset;
    master_visible_cached=master_visible; game_visible_cached=active;
    return sm2lr_input_refresh() || changed;
}
std::string option_key(const nvram::Option &o) {
    return "model2emuex_nvram_"+std::string(o.game)+"_"+o.suffix;
}
}

extern "C" bool sm2lr_register_options(retro_environment_t cb,
    const retro_core_option_v2_definition *native, const retro_core_option_v2_category *categories) {
    if(env!=cb) { invalid_values.clear();option_corrections.clear();option_warnings.clear(); }
    env=cb; sm2lr_input_environment(cb); pending=false; definitions.clear(); legacy.clear(); strings.clear(); operator_keys.clear(); network_keys.clear();
    try {
        // SM2 places general System controls before initial/operator NVRAM.
        for (size_t i=0;native[i].key;i++)
            if (native[i].category_key && std::string_view(native[i].category_key)=="system")
                definitions.push_back(native[i]);
        retro_core_option_v2_definition initial{};
        initial.key="model2emuex_initial_nvram_setup";
        initial.desc="Automatic Initial NVRAM Setup (Restart Required)";
        initial.info="Initialize missing save data from a validated NVRAM template and apply approved initial settings while preserving existing valid saves.";
        initial.category_key="system";
        initial.values[0]={"enabled","Enabled"}; initial.values[1]={"disabled","Disabled"}; initial.default_value="enabled";
        definitions.push_back(initial);
        for(const auto &g:model2lr::network_games) {
            retro_core_option_v2_definition d{};
            d.key=keep("model2emuex_linked_cabinets_"+std::string(g.name));d.desc="Linked Cabinets";
            d.info=model2lr::linked_help;d.category_key="system";d.default_value="-1";
            d.values[0]={"-1","1 Cabinet / Disabled"};
            for(unsigned n=2;n<=g.maximum;n++)d.values[n-1]={keep(std::to_string(n)),keep(std::to_string(n)+" Cabinets")};
            definitions.push_back(d);network_keys.emplace_back(d.key,g.name);
            d={};d.key=keep("model2emuex_automatic_network_"+std::string(g.name));d.desc="Auto Network Role Settings";
            d.info=model2lr::role_help;d.category_key="system";d.default_value="-1";
            size_t i=0;for(const auto &c:network::choices(g.mapping,g.maximum))d.values[i++]={keep(c.key),keep(c.label)};
            definitions.push_back(d);network_keys.emplace_back(d.key,g.name);
        }
        for(const char *prefix:{"linked_cabinets_","automatic_network_"}) {
            retro_core_option_v2_definition d{};d.key=keep("model2emuex_"+std::string(prefix)+"unsupported");
            d.desc=std::string_view(prefix)=="linked_cabinets_"?"Linked Cabinets":"Auto Network Role Settings";
            d.info="Networking is not supported for this game. This setting has no effect.";
            d.category_key="system";d.default_value="unsupported";d.values[0]={"unsupported","Not Supported"};
            definitions.push_back(d);network_keys.emplace_back(d.key,"unsupported");
        }
        retro_core_option_v2_definition master{};
        master.key="model2emuex_nvram_settings"; master.desc="NVRAM Settings (Service Menu)";
        master.info="Apply reviewed operator overrides to saved NVRAM while preserving unrelated fields and calibration. Effective changes apply on return to the game with one automatic reset.";
        master.category_key="system";
        master.values[0]={"disabled","Disabled"}; master.values[1]={"enabled","Enabled"}; master.default_value="disabled";
        definitions.push_back(master);
        for (const auto &o:nvram::all_options()) {
            retro_core_option_v2_definition d{};
            const std::string key=option_key(o);
            d.key=keep(key); d.desc=keep(retroarch_option_label(o.label));
            d.info=keep(retroarch_option_info(o,d.desc)); d.category_key="system"; d.default_value=o.default_value;
            if (o.value_count>=RETRO_NUM_CORE_OPTION_VALUES_MAX) return false;
            for (size_t i=0;i<o.value_count;i++) {
                std::string label=retroarch_option_label(o.values[i].label);
                if (std::string_view(o.values[i].key)==o.default_value) label+=" (Default)";
                d.values[i]={o.values[i].key,keep(std::move(label))};
            }
            definitions.push_back(d); operator_keys.emplace_back(key,o.game);
        }
        for (size_t i=0;native[i].key;i++)
            if (!native[i].category_key || std::string_view(native[i].category_key)!="system")
                definitions.push_back(native[i]);
        sm2lr_add_input_options(definitions);
        definitions.push_back({});
        unsigned version=0;
        if (env(RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION,&version) && version>=2) {
            retro_core_options_v2 options{const_cast<retro_core_option_v2_category *>(categories),definitions.data()};
            env(RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2,&options);
            retro_core_options_update_display_callback callback{update_visibility};
            env(RETRO_ENVIRONMENT_SET_CORE_OPTIONS_UPDATE_DISPLAY_CALLBACK,&callback);
            update_visibility();
        } else {
            // Legacy API cannot hide per-game fields: register just the active catalogue
            // (or no operator fields before content identification) and rebuild on load.
            for (const auto &d:definitions) {
                if (!d.key) break;
                const auto found=std::find_if(operator_keys.begin(),operator_keys.end(),[&](const auto &v){return v.first==d.key;});
                if (found!=operator_keys.end() && found->second!=catalogue) continue;
                const auto net=std::find_if(network_keys.begin(),network_keys.end(),[&](const auto &v){return v.first==d.key;});
                const std::string visible=model2lr::network_game(game_name)?game_name:"unsupported";
                if(net!=network_keys.end() && net->second!=visible)continue;
                std::string value=std::string(d.desc)+"; "+d.default_value;
                for (const auto &v:d.values) {
                    if (!v.value) break;
                    if (std::string_view(v.value)!=d.default_value) value+="|"+std::string(v.value);
                }
                legacy.push_back({d.key,keep(value)});
            }
            legacy.push_back({nullptr,nullptr}); env(RETRO_ENVIRONMENT_SET_VARIABLES,legacy.data());
        }
        return true;
    } catch (...) { return false; }
}
extern "C" bool sm2lr_options_changed() {
    retain_updates(); const bool value=pending; pending=false; return value;
}
extern "C" void sm2lr_publish_option_corrections() {
    // SM2: move queues before frontend calls, which may re-enter option readers.
    const auto corrections=std::exchange(option_corrections,{});
    const auto warnings=std::exchange(option_warnings,{});
    if(env)for(const auto &[key,value]:corrections) {
        retro_variable v{key.c_str(),value.c_str()};env(RETRO_ENVIRONMENT_SET_VARIABLE,&v);
    }
    for(const auto &warning:warnings)m2lr_net_message(warning.c_str());
}
extern "C" void sm2lr_nvram_game(const char *game,const char *parent) {
    game_name=game?game:""; parent_name=parent?parent:"";
    managed_applied.clear();handover.clear();handover_observed.clear();invalid_values.clear();
    option_corrections.clear();option_warnings.clear();
    catalogue=nvram::catalog_for_game(game_name,parent_name);
    if (env) update_visibility();
}
extern "C" sm2lr_initial_nvram_result sm2lr_initial_nvram(uint8_t *backup,uint8_t *eeprom) {
    retain_updates();
    if (!enabled("model2emuex_initial_nvram_setup",true)) return SM2LR_INITIAL_NVRAM_UNCHANGED;
    auto b=std::span<sm2::u8>(backup,kBackupRamSize), e=std::span<sm2::u8>(eeprom,kEepromSize);
    const std::string_view source=initial_nvram::has_template(game_name) ? std::string_view(game_name) :
        initial_nvram::can_use_parent_template(game_name) ? std::string_view(parent_name) : std::string_view{};
    const auto seeded=initial_nvram::seed(source,b,e);
    if (seeded==initial_nvram::SeedResult::InvalidTemplate)
        return SM2LR_INITIAL_NVRAM_INVALID_TEMPLATE;
    if (seeded!=initial_nvram::SeedResult::Loaded) return SM2LR_INITIAL_NVRAM_UNCHANGED;
    if (!catalogue.empty()) {
        const auto values=nvram::initial_values(catalogue);
        const auto applied=nvram::apply(catalogue,b,e,values);
        if (applied==nvram::ApplyResult::Unsupported || applied==nvram::ApplyResult::LayoutNotReady)
            return SM2LR_INITIAL_NVRAM_INVALID_LAYOUT;
    }
    return SM2LR_INITIAL_NVRAM_LOADED;
}
extern "C" int sm2lr_apply_nvram(uint8_t *backup,uint8_t *eeprom) {
    retain_updates();
    if(catalogue.empty())return 0;
    const bool manual=enabled("model2emuex_nvram_settings");
    const auto *g=model2lr::network_game(game_name);
    const bool automated=g && role()!="-1";
    auto targets=automated?network::managed_values(g->mapping,sm2lr_linked_cabinets(),role()):managed_applied;
    std::vector<std::string> values;
    const auto options=nvram::options_for_game(catalogue);
    for (const auto &o:options) {
        const char *value=variable(option_key(o).c_str());
        bool valid=value && std::any_of(o.values,o.values+o.value_count,[&](const auto &v){return std::string_view(v.key)==value;});
        const std::string key=option_key(o);
        if(auto it=handover.find(key);it!=handover.end()) {
            const std::string observed=value?value:"";
            if(it->second==observed || handover_observed[key]!=observed) {
                handover.erase(it);handover_observed.erase(key);
            }
        }
        values.emplace_back(manual?(handover.count(key)?handover.at(key):valid?value:o.default_value):"");
        for(const auto &target:targets)if(target.suffix==o.suffix && (manual || automated))values.back()=target.key;
    }
    if(!manual && !automated) { managed_applied.clear();return 0; }
    const auto result=nvram::apply(catalogue,{backup,kBackupRamSize},{eeprom,kEepromSize},values);
    if(result==nvram::ApplyResult::Changed || result==nvram::ApplyResult::Unchanged) {
        // Publish outside machine/transport locks; SET_VARIABLE may re-enter the display callback.
        for(const auto &target:targets)for(const auto &o:options)if(target.suffix==o.suffix) {
            const std::string key=option_key(o);const char *old=variable(key.c_str());
            if(!old || target.key!=old) {
                handover[key]=target.key;handover_observed[key]=old?old:"";
                retro_variable v{key.c_str(),target.key.c_str()};env(RETRO_ENVIRONMENT_SET_VARIABLE,&v);
            }
        }
        managed_applied=automated?targets:std::vector<network::ManagedValue>{};
    }
    return result==nvram::ApplyResult::Changed?1:result==nvram::ApplyResult::LayoutNotReady?-1:0;
}
extern "C" size_t sm2lr_nvram_option_count() { return nvram::all_options().size(); }
extern "C" unsigned sm2lr_linked_cabinets() {
    const auto *g=model2lr::network_game(game_name);if(!g)return 1;
    const std::string key="model2emuex_linked_cabinets_"+game_name;
    const char *v=variable(key.c_str());
    if(!v || std::string_view(v)=="-1" || std::string_view(v)=="0" || std::string_view(v)=="1")return 1;
    for(unsigned n=2;n<=g->maximum;n++)if(std::to_string(n)==v)return n;
    invalid(key,v);return 1;
}
