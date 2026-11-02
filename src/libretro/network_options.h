// SM2 current per-program limits and F14 choices, restricted to destination sets.
#pragma once
#include <string_view>
namespace model2lr {
struct NetworkGame { const char *name,*mapping;unsigned maximum; };
inline constexpr NetworkGame network_games[]{
    {"daytona","daytona",8},{"daytonas","daytonas",8},{"daytonagtx","daytonagtx",8},
    {"daytonase","daytona",8},{"daytonam","daytona",8},
    {"srallyc","srallyc",5},{"srallycb","srallyc",5},
    {"motoraid","motoraid",5},{"manxtt","manxtt",3},{"manxttc","manxtt",3},
    {"overrev","overrev",4},{"overrevb","overrev",4},
    {"skisuprg","skisuprg",4},{"waverunr","waverunr",4}
};
inline const NetworkGame *network_game(std::string_view name) {
    for(const auto &g:network_games)if(name==g.name)return &g;
    return nullptr;
}
inline constexpr const char *linked_help=
    "Select the total number of linked cabinets, including a Relay where supported. "
    "1 Cabinet / Disabled disconnects optional communication boards or keeps required boards in local loopback; "
    "it does not change the selected native role. Supported totals and role combinations depend on the game. "
    "Effective changes reset automatically on the next running frame. In a paused menu this is Resume; a non-pausing Netplay menu can apply changes while open.";
inline constexpr const char *role_help=
    "Apply the native role and game identity independently of Linked Cabinets, even with NVRAM Settings (Service Menu) disabled. "
    "Disabled restores manual management. Managed native fields are hidden; unrelated settings are preserved. "
    "Effective changes reset automatically on the next running frame. In a paused menu this is Resume; a non-pausing Netplay menu can apply changes while open.";
}
