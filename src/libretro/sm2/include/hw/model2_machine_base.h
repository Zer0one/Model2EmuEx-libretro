//  ____  __  __  ____         _____ __  __ _   _
// / ___||  \/  ||___ \       | ____|  \/  | | | |
// \___ \| |\/| |  __) |_____ |  _| | |\/| | | | |
//  ___) | |  | | / __/|_____|| |___| |  | | |_| |
// |____/|_|  |_||_____|      |_____|_|  |_|\___/
//
// A Sega Model 2 arcade emulator.
// Copyright (c) 2025+ Daniel Martin (dmanlfc)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This header must not be removed. sm2-emu is licensed under the GNU General
// Public License, version 3 or later, with additional terms under section 7 of
// that licence. See LICENSE and NOTICE.
//
//
// The board-agnostic call surface every Model 2 machine variant presents to
// main.cpp, the debug dump functions (hw/model2_debug.cpp) and the renderer
// (render/vk/poly3d_pass.cpp).
//
// This interface is deliberately narrower than any one board's own class: it
// covers exactly what those three consumers call on a machine instance today,
// which is init/reset/run_frame, the input latch, the produced render list,
// NVRAM persistence, and the handful of video and diagnostic accessors the
// debug dumps and the 3D pass read. It does not cover the geometry coprocessor,
// the concrete sound board or sound link (Model2::copro()/sound()/uart()): those
// return board-specific hardware types (CoproTgp, Model2Sound, I8251) that do
// not generalise across boards -- Model 2B's coprocessor is a SHARC wrapped in
// a CoproSharc, Model 2C's is an MB86235 wrapped in a CoproTgpx4, and the
// original Model 2's sound board is YM3438 + MultiPCM, not 68000/SCSP. Code
// that needs those stays against the concrete board class.
//
// -- CPU state reporting across differing core types ------------------------
//
// main.cpp's boot-test report reads the main CPU's state through
// Model2::cpu(): faulted(), fault_message(), state_string(), halted() and
// instructions(). Every board this project will add runs a different core
// there (i960 on Model 2 and 2A, SHARC on Model 2B, MB86235 on Model 2C), so
// this interface needs some way to ask for that without knowing which.
//
// Two shapes were considered:
//
//   1. A type-erased CpuStatus snapshot struct (below), built by each board's
//      main_cpu_status() from whichever concrete core it owns.
//   2. A virtual base class every CPU core implements, so the interface could
//      just return a reference to it.
//
// (1) was chosen. cpu::i960::I960 and cpu::mb86233::MB86233 -- and every core
// this project ports the same way in later waves (SHARC, MB86235) -- are kept
// textually close to their MAME originals on purpose, so that upstream fixes
// stay diffable (see sm2_warnings_ported's rationale in src/CMakeLists.txt).
// Retrofitting a virtual interface onto them would touch code whose entire
// value is reading like upstream, for a feature (polymorphic status reporting)
// that only the boot-test's summary print actually needs. A type-erased struct
// costs one small allocation-bearing copy per report, which happens at most
// once a frame, and touches none of the ported cores.
#pragma once
#include "core/types.h"
#include "rom/game.h"
#include <array>
#include <iterator>
namespace sm2::hw {
struct Inputs {
    /// Coins, service, test and start. Bit 0 coin 1, bit 1 coin 2, bit 2 test,
    /// bit 3 service, bit 4 start 1, bit 5 start 2.
    u8 in0 = 0xff;

    /// Player 1: bits 0-3 buttons, bit 4 down, bit 5 up, bit 6 right, bit 7 left.
    u8 in1 = 0xff;

    /// Player 2, same layout.
    u8 in2 = 0xff;

    /// Air Walkers players 3 and 4. Its port-F matrix selects either in1/in2
    /// or this second pair on the same two physical I/O lanes.
    /// Power Sled also uses in3 for its port-E cabinet inputs.
    u8 in3 = 0xff;
    u8 in4 = 0xff;

    /// Air Walkers Start 1-4, active low in bits 0-3. The selected pair is
    /// presented on the ordinary Start 1/2 lines by the same matrix.
    u8 player_starts = 0xff;

    [[nodiscard]] u8 player_port(unsigned player) const
    {
        const u8* ports[] = {&in1, &in2, &in3, &in4};
        return player < std::size(ports) ? *ports[player] : 0xff;
    }

    [[nodiscard]] u8 start_pair(bool second_pair) const
    {
        const unsigned shift = second_pair ? 2 : 0;
        return static_cast<u8>(((player_starts >> shift) & 0x03) << 4);
    }

    /// The CPU board's eight-position SW3.
    u8 dipswitches = 0xff;

    /// Eight analogue channels behind the I/O controller's mux. Unused by games
    /// with digital controls only.
    ///
    /// These are filled from the per-title channel assignment in
    /// rom::GameSpec::analog rather than by a fixed convention, because the
    /// channel a control sits on differs between titles. A machine with no
    /// analogue controls leaves them at their rest values.
    std::array<u8, 8> analog{};

    /// Gear selector, one bit per shifter position, active high. Only read by a
    /// title whose GameSpec sets `gearbox`.
    u8 gears = 0;

    /// Lightgun position, 10-bit, in the coordinate space the title calibrates
    /// for in rom::GameSpec::lightgun. These do not go through the analogue mux:
    /// the gun interface board is a serial device.
    u16 gun_p1x = 0;
    u16 gun_p1y = 0;
    u16 gun_p2x = 0;
    u16 gun_p2y = 0;

    /// Off-screen status reported by the gun interface board: bit 0 is player 1,
    /// bit 1 is player 2. The host input adapter supplies this independently of
    /// the coordinates, as the real serial interface does.
    u8 gun_offscreen = 0;
};
}
