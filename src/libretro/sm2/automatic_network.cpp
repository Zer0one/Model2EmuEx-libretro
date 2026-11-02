// SPDX-License-Identifier: BSD-3-Clause
#include "automatic_network.h"

#include <algorithm>
#include <charconv>

namespace sm2::libretro::network {
namespace {
bool daytona(std::string_view game)
{
    return game == "daytona" || game == "daytonas" || game == "daytonagtx";
}
bool car_role(std::string_view game)
{
    return game == "stcc" || game == "stcca" || game == "stccb"
        || game == "stcco" || game == "srallyc";
}
bool role_id(std::string_view game)
{
    return game == "indy500" || game == "indy500d" || game == "motoraid"
        || game == "motoraiddx" || game == "waverunr" || game == "skisuprg";
}
bool sled(std::string_view game) { return game == "powsled" || game == "powsledm"; }
bool has_relay(std::string_view game)
{
    return car_role(game) || game == "manxtt" || game == "motoraid" || game == "motoraiddx";
}
unsigned playable_limit(std::string_view game, unsigned maximum)
{
    return has_relay(game) || game == "von" ? maximum - 1 : maximum;
}
std::string offline_key(std::string_view game)
{
    if (daytona(game)) return "single";
    if (car_role(game)) return game == "srallyc" ? "notlink" : "stand_alone";
    if (role_id(game)) return game == "skisuprg" ? "no_link" : "stand_alone";
    if (game == "manxtt" || game == "sgt24h" || game == "overrev") return "not_link";
    return "no_link";
}
std::string offline_label(std::string_view game)
{
    if (daytona(game)) return "Single";
    if (car_role(game)) return game == "srallyc" ? "Notlink" : "Stand Alone";
    if (role_id(game)) return game == "skisuprg" ? "No Link" : "Stand Alone";
    if (game == "manxtt" || game == "sgt24h" || game == "overrev") return "Not Link";
    return "No Link";
}
}  // namespace

std::string_view default_preset(std::string_view /*game*/)
{
    return "-1";
}

std::vector<Choice> choices(std::string_view game, unsigned maximum)
{
    if (game.empty() || maximum < 2) return {};
    if (game == "powsledr" || game == "vonr") return {{"-1", "Disabled"}, {"r", "Relay"}};
    if (sled(game))
        return {{"-1", "Disabled"}, {"1", "Silver"}, {"2", "Red"}, {"3", "Black"}, {"4", "Yellow"}};
    std::vector<Choice> result{{"-1", "Disabled"}, {"0", offline_label(game)}};
    for (unsigned n = 1; n <= playable_limit(game, maximum); ++n) {
        const std::string id = std::to_string(n);
        const std::string role = n == 1 ? "Master" : "Slave";
        std::string label;
        if (daytona(game) || car_role(game)) label = "Car " + id + " (" + role + ")";
        else if (game == "overrev") label = "Carno." + id + " (" + role + ")";
        else if (game == "sgt24h") label = "Car NO" + id + " (" + role + ")";
        else if (role_id(game)) label = "Cabinet " + id + " (" + role + ")";
        else label = role;
        result.push_back({id, std::move(label)});
    }
    if (has_relay(game)) result.push_back({"r", game == "motoraid" || game == "motoraiddx" ? "Live" : "Relay"});
    return result;
}

std::vector<ManagedValue> managed_values(std::string_view game,
                                        unsigned cabinets, std::string_view preset)
{
    if (preset.empty() || preset == "-1" || game == "powsledr") return {};
    if (game == "vonr") return {{"network_link_attribute", "no_link"}};
    if (sled(game)) {
        constexpr std::string_view colors[]{"silver", "red", "black", "yellow"};
        if (preset.size() == 1 && preset[0] >= '1' && preset[0] <= '4')
            return {{"ride_id", std::string(colors[preset[0] - '1'])}};
        return {};
    }
    const bool relay = preset == "r";
    unsigned number = 0;
    if (!relay) {
        const auto parsed = std::from_chars(preset.data(), preset.data() + preset.size(), number);
        if (parsed.ec != std::errc{} || parsed.ptr != preset.data() + preset.size()
            || number > 8 || std::to_string(number) != preset) return {};
    }
    if (!relay && number == 0) {
        if (daytona(game)) return {{"link_id", "single"}, {"car_number", "1"}};
        if (car_role(game) || game == "manxtt" || game == "sgt24h")
            return {{"link_type", offline_key(game)}};
        if (role_id(game)) return {{"network_type", offline_key(game)}, {"cabinet_id", "1"}};
        if (game == "overrev") return {{"link_max", "not_link"}};
        if (game == "von") return {{"network_link_attribute", "no_link"}};
        return {};
    }
    const std::string role = number == 1 ? "master" : "slave";
    if (daytona(game)) return {{"link_id", role}, {"car_number", std::to_string(number)}};
    if (car_role(game)) return {{"link_type", relay ? "relay" : "car_" + std::to_string(number)}};
    if (role_id(game))
        return {{"network_type", relay ? "live" : role},
                {"cabinet_id", std::to_string(relay ? std::clamp(cabinets, 1u, 4u) : number)}};
    if (game == "manxtt") return {{"link_type", relay ? "relay" : role}};
    if (game == "sgt24h")
        return {{"link_type", "car_no" + std::to_string(number) + (number == 1 ? "_master" : "_slave")},
                {"link_max", std::to_string(std::max({2u, cabinets, number}))}};
    if (game == "overrev")
        return {{"link_type", role + "_carno_" + std::to_string(number)},
                {"link_max", std::to_string(std::max({2u, cabinets, number})) + "_links"}};
    if (game == "von") return {{"network_link_attribute", role}};
    return {};
}

bool managed_field(std::string_view game, std::string_view suffix)
{
    if (sled(game)) return suffix == "ride_id";
    if (game == "powsledr") return false;
    if (daytona(game)) return suffix == "link_id" || suffix == "car_number";
    if (role_id(game)) return suffix == "network_type" || suffix == "cabinet_id";
    if (game == "von" || game == "vonr") return suffix == "network_link_attribute";
    return suffix == "link_type" || ((game == "sgt24h" || game == "overrev") && suffix == "link_max");
}
}  // namespace sm2::libretro::network
