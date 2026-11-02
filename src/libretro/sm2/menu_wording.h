// SPDX-License-Identifier: BSD-3-Clause
// Functions imported from SM2 core_options.h without algorithm changes.
#pragma once
#include "nvram_settings.h"
#include <algorithm>
#include <cctype>
#include <iterator>
#include <string>
#include <string_view>
namespace sm2::libretro {
inline std::string retroarch_option_label(std::string_view label)
{
    static constexpr std::string_view acronyms[] = {
        "BGM", "CRT", "DX", "EUR", "EXP", "GT", "ID", "JPN", "NG", "OK", "PK", "SD",
        "SP", "TT", "URL", "US", "USA", "VJCOM", "VJMAN", "VS",
    };
    std::string result;
    result.reserve(label.size() + 2);
    for (size_t i = 0; i < label.size();) {
        const unsigned char current = static_cast<unsigned char>(label[i]);
        if (!std::isalnum(current)) {
            if (label[i] == '(' && !result.empty() && result.back() != ' ')
                result.push_back(' ');
            result.push_back(label[i++]);
            continue;
        }
        size_t end = i;
        bool has_digit = false;
        while (end < label.size() && std::isalnum(static_cast<unsigned char>(label[end]))) {
            has_digit |= std::isdigit(static_cast<unsigned char>(label[end])) != 0;
            ++end;
        }
        const std::string_view word = label.substr(i, end - i);
        const bool acronym = has_digit || std::find(std::begin(acronyms), std::end(acronyms), word)
                                           != std::end(acronyms);
        for (size_t offset = 0; offset < word.size(); ++offset) {
            const unsigned char character = static_cast<unsigned char>(word[offset]);
            result.push_back(static_cast<char>(acronym ? character
                : offset == 0 ? std::toupper(character) : std::tolower(character)));
        }
        i = end;
    }
    return result;
}

inline std::string retroarch_option_info(const nvram::Option& option,
                                         std::string_view display_label)
{
    std::string result = option.description;
    const auto replace_all = [&](std::string_view from, std::string_view to) {
        for (size_t position = 0; (position = result.find(from, position)) != std::string::npos;
             position += to.size())
            result.replace(position, from.size(), to);
    };
    replace_all(option.label, display_label);
    replace_all(std::string(option.game) + "'s", "the game's");
    replace_all("NVRAM Settings is", "NVRAM Settings (Service Menu) is");
    return result;
}
}
