// SPDX-License-Identifier: BSD-3-Clause
#include "power_sled_standalone.h"
#include <algorithm>
#include <array>
#include <vector>

namespace sm2::libretro {
namespace {
u32 word(std::span<const u8> data, usize at) {
    return u32{data[at]} | u32{data[at+1]} << 8 | u32{data[at+2]} << 16 | u32{data[at+3]} << 24;
}
void put(std::span<u8> data, usize at, u32 value) {
    for (unsigned i=0;i<4;++i) data[at+i]=static_cast<u8>(value>>(i*8));
}
u32 branch(u32 from, u32 to) { return 0x08000000u | ((to-from)&0x00ffffffu); }
}
bool prepare_power_sled_standalone(std::span<u8> program)
{
    constexpr u32 assignment=0x1f0800, mapping=0x1f0880, table=0x1f0a00, roster=0x1f0a40, service_exit=0x1f0a80;
    constexpr std::array<u32,24> addresses{0x24370,0xcd350,0xcd1f8,0xcd248,0xcd284,0xcd28c,0xcd294,0x43e74,
        0x24a90,0x41744,0x41748,0x417a0,0x417a4,
        0x44240,0x44334,0x45510,0x45618,0x45650,0x45810,0xd0498,0xd0588,0x18c30,0x1c4a0,0x24e8c};
    constexpr std::array<u32,24> expected{0x80a03000,0xc0a03000,0x5ca81e03,0x5ca81e02,0x5ca01e03,0x5ca01e08,0x5ca01e06,0x3b0d2014,
        0x5a003087,0xc0803000,0x52949e,0xc0903000,0x52949e,
        0x59a50901,0x59a50901,0x59a50901,0x59a50901,0x59a50901,0x59a50901,0x59a50d01,0x59a50d01,0x90a03000,0x90a03000,0x08000010};
    const std::array<u32,24> replacement{branch(0x24370,assignment),branch(0xcd350,mapping),
        // Every native roster case must own exactly the same four local sleds.
        0x5ca81e04,0x5ca81e04,0x5ca01e04,0x5ca01e04,0x5ca01e04,
        // A single node otherwise selects 0x43840, which never constructs the
        // full race or initializes its timer. Keep the ordinary race path.
        branch(0x43e74,0x43e78),branch(0x24a90,roster),
        // Include AI in the finish order and HUD rank, without changing the
        // physical human-node count used by controls and collision handling.
        0x5c801e04,branch(0x41748,0x4174c),0x5c901e04,branch(0x417a4,0x417a8),
        // The attract scene normally reserves the last owned slot. All four
        // slots here are actual sleds: construct, collide and advance all four.
        branch(0x44240,0x44244),branch(0x44334,0x44338),
        branch(0x45510,0x45514),branch(0x45618,0x4561c),
        branch(0x45650,0x45654),branch(0x45810,0x45814),
        // The boarding/countdown constructor halves the distributed field.
        // All four colors are local here, including Black and Yellow: their
        // native camera and countdown tasks must also be constructed.
        branch(0xd0498,0xd049c),branch(0xd0588,0xd058c),
        // Four locally owned colors are not four physical screens. Retain the
        // native single-screen camera path instead of the panoramic offset.
        branch(0x18c30,0x18c40),
        // Exit must retire the local Test command before the native restart.
        branch(0x1c4a0,service_exit),
        // B_CRX counts physical rider boards. Our Master also hosts the human
        // rider: keep its Master-presence flag, then count this real board once.
        // Relay remains excluded; the three local AI do not become fake boards.
        branch(0x24e8c,0x24e9c)};
    if (program.size()<service_exit+20
        || !std::all_of(program.begin()+assignment,program.begin()+service_exit+20,[](u8 b){return b==0;})) return false;
    for (usize i=0;i<addresses.size();++i)
        if (word(program,addresses[i])!=expected[i]) return false;

    if (word(program,0x1c4a4)!=0x53e744) return false;

    // Retire command 0x1000 so our one-node ring cannot re-enter Test after
    // Exit. Replay the displaced phase load and keep native cleanup/restart.
    const std::array<u32,5> exit{
        0x8af03000,0x5293f4, // stos g14 (native zero), outgoing operator command
        0x90a03000,0x53e744, // displaced ld phase,g4
        branch(service_exit+16,0x1c4a8)};
    for (usize i=0;i<exit.size();++i) put(program,service_exit+i*4,exit[i]);

    // Native Ride color is the human slot; the other three use the existing AI.
    const std::array<u32,19> assign{
        0x80a03000,0x01d00008, // ldob native Ride,g4
        0xb0803a14,table,      // ldq table[g4*16],g0
        0xb2803000,0x5030e0,  // stq g0,ownership slots
        0x92f03000,0x5030f0,  // clear unused ownership slots
        0x92f03000,0x5030f4,
        0x92f03000,0x5030f8,
        0x92f03000,0x5030fc,
        0x92f03000,0x5030d4,  // preserve the native assignment tail
        0x92f03000,0x51aca8,
        0x0a000000};
    for (usize i=0;i<assign.size();++i) put(program,assignment+i*4,assign[i]);
    for (u32 color=0;color<4;++color)
        for (u32 slot=0;slot<4;++slot) put(program,table+color*16+slot*4,(color+slot)%4);

    // Every competitor comes from our own four published records, returned by
    // the existing one-node ring. No fabricated Slave role or peer process.
    std::vector<u32> map;
    for (u32 slot=0;slot<4;++slot) {
        const std::array<u32,6> record{0x90a03000,0x5030e0+slot*4,
            0x8ca83000,0x1a021d0+slot*0x30,0x92a83914,0x505530};
        map.insert(map.end(),record.begin(),record.end());
    }
    map.insert(map.end(),{0x8ca83000,0x1a02180});
    for (u32 at:{0x529450u,0x529454u,0x529458u,0x52945cu,0x529464u})
        map.insert(map.end(),{0x92a83000,at});
    map.push_back(0x0a000000);
    for (usize i=0;i<map.size();++i) put(program,mapping+i*4,map[i]);

    // Startup validates Ride presence from physical packet headers. In this
    // mode all four colors are local owners (one human, three AI), including
    // Silver when the human chose another color. Preserve the native roster
    // checks and diagnostics with those ownership counts, not fake nodes.
    const std::array<u32,13> local_roster{
        0x5cb81e01,0x5c881e01,0x5c901e01,0x5c981e01, // g7,g1,g2,g3: colors present
        0x5c201e04,                                  // r4: four Ride owners
        0x5c281e01,0x5c301e01,0x5c401e01,0x5c501e01, // one owner per color
        0x5c481e01,0x5c381e00,                       // Master present, no Relay
        0x5a003087,branch(roster+48,0x24a94)};        // displaced compare and resume
    for (usize i=0;i<local_roster.size();++i) put(program,roster+i*4,local_roster[i]);
    for (usize i=0;i<addresses.size();++i) put(program,addresses[i],replacement[i]);
    return true;
}
bool prepare_power_sled_relay_attract(std::span<u8> program)
{
    constexpr u32 assignment = 0x1f1000, mapping = 0x1f1080, roster = 0x1f1180,
                  service_exit = 0x1f11a0, idle_master = 0x1f1400;
    struct Patch { u32 at, before, after; };
    const std::array patches{
        // The local link board initiates its one-node ring. The game program
        // still publishes Relay header 0x0100 in its unchanged initializer.
        Patch{0x11d20, 0x3a0d2028, branch(0x11d20, 0x11d48)},
        // Local link initiation uses the controller-Master branch, but this
        // application's identity remains Relay throughout startup.
        Patch{0x11d58, 0x00011950, 0x00011920},
        Patch{0x24370, 0x80a03000, branch(0x24370, assignment)},
        Patch{0xcd350, 0xc0a03000, branch(0xcd350, mapping)},
        Patch{0x246fc, 0x090002c4, 0x09000000u | ((roster - 0x246fc) & 0x00ffffffu)},
        // The isolated Relay is the only physical B-CRX board. Preserve its
        // Relay-presence flag, then count that real board once for the boot
        // diagnostic. No rider header or remote Master/Slave is fabricated.
        Patch{0x24e98, 0x08000008, branch(0x24e98, 0x24e9c)},
        Patch{0xcd1f8, 0x5ca81e03, 0x5ca81e04},
        Patch{0xcd248, 0x5ca81e02, 0x5ca81e04},
        Patch{0xcd284, 0x5ca01e03, 0x5ca01e04},
        Patch{0xcd28c, 0x5ca01e08, 0x5ca01e04},
        Patch{0xcd294, 0x5ca01e06, 0x5ca01e04},
        Patch{0x44240, 0x59a50901, branch(0x44240, 0x44244)},
        Patch{0x44334, 0x59a50901, branch(0x44334, 0x44338)},
        Patch{0x45510, 0x59a50901, branch(0x45510, 0x45514)},
        Patch{0x45618, 0x59a50901, branch(0x45618, 0x4561c)},
        Patch{0x45650, 0x59a50901, branch(0x45650, 0x45654)},
        Patch{0x45810, 0x59a50901, branch(0x45810, 0x45814)},
        // Keep Test available, but do not issue selection/race/operator commands.
        Patch{0xbd4e0, 0x30452010, branch(0xbd4e0, 0xbd500)},
        Patch{0xbd510, 0x305d2010, branch(0xbd510, 0xbd550)},
        Patch{0xbd5e4, 0x529464, 0x529450}, // Test follows this local Relay packet.
        Patch{0x1c4a0, 0x90a03000, branch(0x1c4a0, service_exit)},
    };
    if (program.size() < idle_master + 0x180
        || !std::all_of(program.begin() + assignment, program.begin() + service_exit + 20,
                        [](u8 b) { return b == 0; })
        || !std::all_of(program.begin() + idle_master, program.begin() + idle_master + 0x180,
                        [](u8 b) { return b == 0; })) return false;
    for (const auto& patch : patches)
        if (word(program, patch.at) != patch.before) return false;
    if (word(program, 0x1c4a4) != 0x53e744 || word(program, 0x1584c) != 0x58a81988
        || word(program, 0x15850) != 0x8aa83000 || word(program, 0x15854) != 0x5293f0)
        return false;

    // All four actors are local native attract actors; the board stays Relay.
    std::vector<u32> assign;
    for (u32 color = 0; color < 4; ++color)
        assign.insert(assign.end(), {0x5ca01e00u | color, 0x92a03000u, 0x5030e0u + color * 4});
    for (u32 at : {0x5030f0u, 0x5030f4u, 0x5030f8u, 0x5030fcu, 0x5030d4u, 0x51aca8u})
        assign.insert(assign.end(), {0x92f03000, at});
    assign.push_back(0x0a000000);
    for (usize i = 0; i < assign.size(); ++i) put(program, assignment + i * 4, assign[i]);
    std::vector<u32> map;
    for (u32 slot = 0; slot < 4; ++slot)
        map.insert(map.end(), {0x8ca83000u, 0x1a021d0u + slot * 0x30,
                              0x92a83000u, 0x505530u + slot * 4});
    map.insert(map.end(), {0x8ca83000, 0x1a02180});
    for (u32 at : {0x529450u, 0x529454u, 0x529458u, 0x52945cu})
        map.insert(map.end(), {0x92a83000, at});
    // A Relay record has different status fields from a Master record. Supply
    // an inert Master command/status view instead of misreading our own header.
    map.insert(map.end(), {0x8ca83000, idle_master, 0x92a83000, 0x529464});
    map.push_back(0x0a000000);
    for (usize i = 0; i < map.size(); ++i) put(program, mapping + i * 4, map[i]);
    // The presentation's virtual layout has four colors and a Relay. This is
    // not a physical network roster and never emits a start-game command.
    const std::array<u32, 5> layout{0x5ca01e07, 0x92a03000, 0x51aca4, 0x5c801e00, 0x0a000000};
    for (usize i = 0; i < layout.size(); ++i) put(program, roster + i * 4, layout[i]);
    put(program, idle_master, 0x0200);
    // Command zero is neutral, including during local Test. A persistent
    // command 1 would repeatedly request a return to Attract from Test.
    // Exit retires local Test and resumes the native Attract constructor.
    // The ordinary Exit increments phase 15 to 16; in this isolated candidate
    // it remains at phase 18. Return directly to native phase 4 instead.
    const std::array<u32, 5> exit{0x8af03000, 0x5293f4, 0x5ca01e03,
                                branch(service_exit + 12, 0x1c4a8), 0x0a000000};
    for (usize i = 0; i < exit.size(); ++i) put(program, service_exit + i * 4, exit[i]);
    for (const auto& patch : patches) put(program, patch.at, patch.after);
    return true;
}
bool prepare_power_sled_ai_finish_speed_fix(std::span<u8> program, std::string_view game)
{
    if (game != "powsledm" && game != "powsled" && game != "powsledr") return false;
    const u32 at = game == "powsled" ? 0x3d278 : 0x3d288;
    // Preserve preceding magnitude calculation and every following AI update.
    // The independent final-stop block is earlier and is never patched.
    if (program.size() < at + 0xa4 || word(program, at) != 0x1600009c
        || word(program, at - 16) != 0x90a12130
        || word(program, at - 12) != 0x8c900305
        || word(program, at + 0x9c) != 0x8c983000
        || word(program, at + 0xa0) != 0x3e4ccccd) return false;
    put(program, at, branch(at, at + 0x9c));
    return true;
}

}
