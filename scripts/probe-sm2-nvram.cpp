// Reuse probe: compile the reference SM2 NVRAM implementation unchanged.
// No game execution, sample acquisition or user save mutation occurs here.
#include <cstddef>
#include "libretro/nvram_settings.h"
#include "libretro/initial_nvram.h"
#include "libretro/save_ram.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
int main(int argc, char **argv) {
    using sm2::u8;
    using namespace sm2::libretro;
    if (argc != 3) return 2;
    const std::string game = argv[1];
    std::ifstream file(argv[2], std::ios::binary);
    std::vector<u8> original((std::istreambuf_iterator<char>(file)), {});
    if (original.size() != 0x10080) return 3;
    auto working = original;
    auto backup = std::span(working).first(kBackupRamSize);
    auto eeprom = std::span(working).subspan(0x10000, kEepromSize);
    bool native_valid = nvram::valid_layout(game, backup, eeprom);
    auto result = initial_nvram::seed(game, backup, eeprom);
    bool seed_valid = result == initial_nvram::SeedResult::Loaded && nvram::valid_layout(game, backup, eeprom);
    if (!seed_valid) return 4;
    auto seeded = working;
    const auto options = nvram::options_for_game(game);
    size_t values = 0, changed = 0;
    for (size_t i = 0; i < options.size(); ++i) {
        for (size_t v = 0; v < options[i].value_count; ++v) {
            working = seeded;
            std::vector<std::string> selections(options.size());
            selections[i] = options[i].values[v].key;
            const auto applied = nvram::apply(game, backup, eeprom, selections);
            if (applied != nvram::ApplyResult::Changed && applied != nvram::ApplyResult::Unchanged) return 5;
            if (!nvram::valid_layout(game, backup, eeprom)) return 6;
            if (!std::equal(original.begin()+kBackupRamSize, original.begin()+0x10000, working.begin()+kBackupRamSize)) return 7;
            if (applied == nvram::ApplyResult::Changed) changed++;
            values++;
        }
    }
    std::cout << "{\"game\":\"" << game << "\",\"native_capture_layout_valid\":" << (native_valid?"true":"false")
              << ",\"reference_template_valid\":true,\"options\":" << options.size()
              << ",\"values_checked\":" << values << ",\"changed\":" << changed
              << ",\"extra_backup_preserved\":true}\n";
}
