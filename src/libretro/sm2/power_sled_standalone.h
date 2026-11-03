// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "core/types.h"
#include <span>
#include <string_view>

namespace sm2::libretro {
/// Guarded Master-only reconstruction. The caller supplies isolated loopback.
[[nodiscard]] bool prepare_power_sled_standalone(std::span<u8> program);
/// Isolated Relay presentation with local attract actors and no race commands.
[[nodiscard]] bool prepare_power_sled_relay_attract(std::span<u8> program);
/// Bypass only the native late-course AI speed clamp in known Power Sled programs.
[[nodiscard]] bool prepare_power_sled_ai_finish_speed_fix(std::span<u8> program, std::string_view game);
}
