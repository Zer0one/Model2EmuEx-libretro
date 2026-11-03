// SPDX-License-Identifier: BSD-3-Clause
#include "power_sled_commands.h"
#include <algorithm>
#include <array>

namespace sm2::libretro {
namespace {
u32 word(std::span<const u8> bytes, usize at) {
    return u32{bytes[at]} | u32{bytes[at+1]} << 8 | u32{bytes[at+2]} << 16 | u32{bytes[at+3]} << 24;
}
void put(std::span<u8> bytes, usize at, u32 value) {
    for (unsigned i=0; i<4; ++i) bytes[at+i]=static_cast<u8>(value>>(8*i));
}
u32 branch(u32 from, u32 to) { return 0x08000000u | ((to-from)&0x00ffffffu); }
}
bool prepare_power_sled_commands(std::span<u8> program)
{
    constexpr u32 decoder=0x1f0b00, result=0x1f0b90, departure=0x1f0c00;
    // The database's existing Test-ownership guard stays in front of this
    // decoder. Admit only that reconstructed Master and known native task.
    constexpr std::array<u32,8> addresses{0x1f0400,0x1f0404,0x1f0414,0x33564,
        0x33118,0xe5a4c,0xe5dd8,0xe6150};
    constexpr std::array<u32,8> expected{0x90a03000,0x53e744,0x08ecd0cc,0x599bde08,
        0x92f12004,0x8cb00f00,0x8cb00f00,0x8cb00f00};
    if (program.size()<departure+52
        || !std::all_of(program.begin()+decoder,program.begin()+departure+52,[](u8 b){return b==0;})) return false;
    for (usize i=0;i<addresses.size();++i)
        if (word(program,addresses[i])!=expected[i]) return false;
    if (word(program,0xe64a4)!=0x8cb00f00 || word(program,0x3311c)!=0x0a000000) return false;

    // Native input edges: Coin (IN0 0/1) or Start opens selection from attract;
    // Entry (IN1 0/2) confirms locally or requests race in pre-race;
    // Start (IN1 4) also requests race there. Call (IN1 1/3) has priority
    // and issues native Emergency Stop 0x100. Coin/Start recovers a stopped group
    // through its native attract receiver; another Coin/Start opens selection.
    // In results, Start or Select (Coin) requests attract directly.
    constexpr std::array<u32,34> commands{
        0x90b03000,0x0053e744,0x3a7da07c,0x88a03000,0x00529368,
        0x304d2008,0x08000060,0x305d2008,0x08000058,0x30052008,
        0x08000018,0x300d2008,0x08000010,0x3a35a024,0x3065204c,
        0x08000004,0x3a75a010,0x3d25a040,0x5ca81e02,0x08000030,
        0x5ca81e01,0x08000028,0x3d35a02c,0x30452008,0x08000010,
        0x30552008,0x08000008,0x30652018,0x5ca81e05,0x08000008,
        0x58a81988,0x8aa83000,0x005293f4,0x08ecc9cc,
    };
    // The native departure sound task retires itself after its final command
    // (11), following the model's last frame. Hook that completion, rather
    // than a frontend delay or a scan of scheduler memory. Preserve any
    // pending Emergency Stop instead of overwriting it with command 4.
    constexpr std::array<u32,13> complete{
        0x92f12004,                    // displaced st zero,4(r4)
        0x90a03000,0x53e744,          // ld phase,g4
        0x3d2d2024,                   // cmpibne 5,g4,ret
        0x88a03000,0x5293f4,          // ldos outgoing command,g4
        0x30452008,                   // bbc 8,g4,send
        0x0a000000,                   // preserve pending emergency
        0x5ca81e04,                   // native boarding command 4
        0x8aa83000,0x5293f4,
        0x0a000000,0x0a000000};
    for (usize i=0;i<commands.size();++i) put(program,decoder+i*4,commands[i]);
    // Extend the existing Coin/Start phase dispatch, preserving Call priority.
    put(program,decoder+0x40,branch(decoder+0x40,result));
    put(program,result,0x3a45bfc0);   // cmpibe 8,g6,decoder+0x50
    put(program,result+4,0x3a75bfbc); // cmpibe 14,g6,decoder+0x50
    put(program,result+8,branch(result+8,decoder+0x44));
    for (usize i=0;i<complete.size();++i) put(program,departure+i*4,complete[i]);
    put(program,0x1f0414,branch(0x1f0414,decoder));
    // Confirmation and moving-arm tasks now consume only Entry, not Call.
    put(program,0x33564,0x59995e08); // shlo 8,5,g3
    for (u32 at:{0xe5a4cu,0xe5dd8u,0xe6150u,0xe64a4u}) put(program,at,0x8cb00500);
    put(program,0x33118,branch(0x33118,departure));
    return true;
}
}
