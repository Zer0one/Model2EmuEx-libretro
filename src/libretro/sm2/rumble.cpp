// SPDX-License-Identifier: BSD-3-Clause
#include "rumble.h"

#include <algorithm>
#include <cstdlib>

namespace sm2::libretro {
namespace {
constexpr int kCorneringMinimum = 32767 * 5 / 100;
constexpr int kHoldFrames = 12;
}

bool GamepadRumble::init(retro_environment_t environment)
{
    stop();
    m_set_state = nullptr;
    retro_rumble_interface interface{};
    if (!environment
        || !environment(RETRO_ENVIRONMENT_GET_RUMBLE_INTERFACE, &interface)
        || !interface.set_rumble_state)
        return false;
    m_set_state = interface.set_rumble_state;
    return true;
}

void GamepadRumble::apply(u16 strong, u16 weak)
{
    if (strong == m_strong && weak == m_weak) return;
    if (m_set_state) {
        m_set_state(0, RETRO_RUMBLE_STRONG, strong);
        m_set_state(0, RETRO_RUMBLE_WEAK, weak);
    }
    m_strong = strong;
    m_weak = weak;
}

void GamepadRumble::clear_state()
{
    m_level = 0;
    m_direction = 0;
    m_hold = 0;
    m_drive_command = {};
}

void GamepadRumble::stop()
{
    if (m_set_state) {
        m_set_state(0, RETRO_RUMBLE_STRONG, 0);
        m_set_state(0, RETRO_RUMBLE_WEAK, 0);
    }
    m_strong = 0;
    m_weak = 0;
    clear_state();
}

void GamepadRumble::update(const rom::GameSpec& game, std::span<const u8> drive_writes,
                           s16 steering, bool enabled)
{
    for (const u8 value : drive_writes) {
        const osd::DriveCommand command = osd::decode_drive_command(game.drive_protocol, value);
        if (command.effect == osd::DriveCommand::Effect::Other) continue;
        if (command.effect == osd::DriveCommand::Effect::Spring && !command.held
            && m_drive_command.held)
            continue;
        m_drive_command = command;
    }

    constexpr int ceiling = 65535;
    const bool active = enabled && game.has_steering();
    if (!active) {
        apply(0, 0);
        clear_state();
        return;
    }

    // Short directional pushes and center-relative kicks become gamepad jolts.
    int impact = 0;
    if (m_drive_command.strength > 0 && !m_drive_command.held
        && m_drive_command.is_push()) {
        const int minimum_felt = ceiling / 4;
        impact = minimum_felt
               + (ceiling - minimum_felt) * m_drive_command.strength / osd::kDriveFull;
        if (m_drive_command.is_push()) {
            const int direction =
                m_drive_command.effect == osd::DriveCommand::Effect::Kick
                    ? (steering > 2 * 256 ? -1 : 1)
                    : (m_drive_command.effect == osd::DriveCommand::Effect::PushLeft ? 1 : -1);
            if (direction != m_direction) {
                impact = std::min(impact * 3 / 2, 65535);
                m_direction = direction;
            }
        }
    }

    // The frontend has already applied its deadzone to this analog callback.
    // Keep a small, deliberate 5% onset threshold for synthetic cornering only.
    // Rescale the remaining travel to preserve the existing maximum strength.
    const int deflection = std::min(std::abs(static_cast<int>(steering)), 32767);
    const int travel = std::max(0, deflection - kCorneringMinimum);
    const int cornering = (ceiling * 2 / 5) * travel / (32767 - kCorneringMinimum);

    const int target = std::max(impact, cornering);
    if (target > 0) {
        m_level = target;
        m_hold = kHoldFrames;
    } else if (m_hold > 0 && --m_hold == 0) {
        m_level = 0;
        m_direction = 0;
    }

    const auto strong = static_cast<u16>(std::clamp(m_level, 0, 65535));
    const auto weak = static_cast<u16>(std::clamp(m_level / 2, 0, 65535));
    apply(strong, weak);
}

}  // namespace sm2::libretro
