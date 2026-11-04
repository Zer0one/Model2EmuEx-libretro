#!/bin/bash
# Run the existing bridge and native-wiring checks against the actual build objects.
set -euo pipefail
cd "$(dirname "$0")/.."
make -j4
build=port/build-libretro-macos
objects=("$build/sm2_bridge.o" "$build/net_bridge.o" "$build/sm2_input_bridge.o" "$build/sm2_overlay.o" "$build/stb_image.o" "$build/sm2_timing.o" "$build"/imgui/*.o "$build/m2/m2glapi.o" "$build"/sm2/*.o
         "$build"/sm2/rom/*.o "$build"/sm2/core/*.o "$build"/sm2/osd/*.o
         "$build"/sm2/pugixml/*.o "$build/m2/m2rom.o")
for check in bridge input timing sonic; do
    clang++ -std=c++20 -O2 -Iport -Isrc/libretro -Isrc/libretro/include -Isrc/libretro/sm2/include \
        "scripts/check-sm2-$check.cpp" "${objects[@]}" -lz -o "$build/check-sm2-$check"
    "$build/check-sm2-$check"
done
clang++ -std=c++20 -O2 -Isrc/libretro/include -Isrc/libretro/sm2 -Isrc/libretro/sm2/include \
    -DSM2_GAMES_XML_PATH='"src/libretro/sm2/data/games.xml"' \
    src/libretro/sm2/checks/input.cpp "${objects[@]}" -lz -o "$build/check-sm2-reference-input"
"$build/check-sm2-reference-input"
clang++ -std=c++20 -O2 -Isrc/libretro/sm2 -Isrc/libretro/sm2/include -Isrc/libretro/include -Iport/imgui \
    src/libretro/sm2/checks/timing_overlay.cpp "${objects[@]}" -lz -o "$build/check-sm2-reference-timing"
"$build/check-sm2-reference-timing"
clang -O2 -Iport scripts/check-state-native.c "$build/i960/i960.o" -lm -o "$build/check-state-native"
"$build/check-state-native"
python3 scripts/check-abi.py "$build/model2emuex_libretro.dylib"
