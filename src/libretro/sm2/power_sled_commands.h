// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "core/types.h"
#include <span>
namespace sm2::libretro {
/// Experimental Master-only native operator remap and departure completion.
[[nodiscard]] bool prepare_power_sled_commands(std::span<u8> program);
}
