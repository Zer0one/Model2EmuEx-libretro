// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include "core/types.h"
#include <span>
#include <vector>
#include "libretro.h"

#include <optional>
#include <string_view>

namespace sm2::libretro {

/// Official Libretro Netpacket wire for a linked Model 2 cabinet ring.
/// The emulated ring remains in hw::M2Comm; this class only carries complete
/// communication-board frames to the next frontend instance in the roster.
class NetpacketTransport {
public:
    // Power Sled program tags 1/2/3 identify Main/Relay/Slave ROMs,
    // independently of the emulated communication board role or link ID.
    void configure(std::string_view game, unsigned cabinets, unsigned program_role = 0);

    [[nodiscard]] bool ready() const;
    void send(std::span<const u8> frame);
    [[nodiscard]] std::optional<std::vector<u8>> recv();
    [[nodiscard]] bool connected() const;
    void reset();
};

[[nodiscard]] bool register_netpacket_interface(retro_environment_t environment,
                                                retro_log_printf_t logger);
[[nodiscard]] bool netpacket_interface_supported();
void set_netpacket_offline();
void shutdown_netpacket_interface();

}  // namespace sm2::libretro
