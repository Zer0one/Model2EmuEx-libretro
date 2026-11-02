# Independent Libretro adapter; upstream's port/Makefile stays unchanged.
platform ?= auto
ifeq ($(platform),auto)
  ifeq ($(shell uname -s),Darwin)
    platform := osx
  else ifneq (,$(findstring MINGW,$(shell uname -s)))
    platform := win
  else
    platform := unix
  endif
endif
ifeq ($(platform),osx)
  CC := clang
  CXX := clang++
  EXT := dylib
  SHARED := -dynamiclib -Wl,-exported_symbols_list,src/libretro/exports-macos.list
  LIBS := -lz -lm
  RELEASE_BUILD := port/build-release-macos
else ifeq ($(platform),win)
  CC := gcc
  CXX := g++
  EXT := dll
  SHARED := -shared -static-libgcc -static-libstdc++ -Wl,--exclude-all-symbols
  LIBS := -Wl,-Bstatic -lz -lwinpthread -Wl,-Bdynamic -lm
  RELEASE_BUILD := port/build-release-windows
else
  CC := gcc
  CXX := g++
  EXT := so
  SHARED := -shared -static-libgcc -static-libstdc++ -Wl,--version-script=src/libretro/exports.map
  LIBS := -lz -lm -pthread
  RELEASE_BUILD := port/build-release-linux
endif
BUILD ?= port/build-libretro-macos
TARGET := $(BUILD)/model2emuex_dev_libretro.$(EXT)
CPPFLAGS += -Isrc/libretro/include -Isrc/libretro/data -Iport -D_DEFAULT_SOURCE -DM2_ROMSET_MAME
CPPFLAGS += -DM2_CABINET_AUDIO
CFLAGS := -O2 -g -std=c11 -fPIC -fvisibility=hidden -Wall -Wextra -MMD -MP
CXXFLAGS := -O2 -g -std=c++14 -fPIC -fvisibility=hidden -MMD -MP
CORE_C := i960/i960.c tgp/tgp.c m2/m2board.c m2/m2link.c m2/m2rom.c m2/m2tile.c m2/m2input.c m2/m2geo.c m2/m2gl.c m2/m2glapi.c m2/m2pipe.c m2/m2wide.c snd/m2snd.c snd/scsp.c snd/multipcm.c m68k/m68kcpu.c m68k/m68kops.c m68k/softfloat/softfloat.c
CORE_CXX := snd/ym3438.cpp ymfm/ymfm_opn.cpp ymfm/ymfm_adpcm.cpp ymfm/ymfm_ssg.cpp
CORE_CXX += snd/m2uart.cpp snd/sm2/hw/i8251.cpp
SM2_CXX := nvram_settings.cpp initial_nvram.cpp save_ram.cpp automatic_network.cpp netpacket.cpp input.cpp rumble.cpp crosshair.cpp timing_overlay.cpp rom/game.cpp rom/game_db.cpp core/log.cpp osd/drive_command.cpp pugixml/pugixml.cpp
SM2_OBJ := $(addprefix $(BUILD)/sm2/,$(SM2_CXX:.cpp=.o)) $(BUILD)/sm2_bridge.o $(BUILD)/net_bridge.o $(BUILD)/sm2_input_bridge.o $(BUILD)/sm2_overlay.o $(BUILD)/stb_image.o $(BUILD)/sm2_timing.o $(addprefix $(BUILD)/imgui/,imgui.o imgui_draw.o imgui_widgets.o imgui_tables.o)
OBJ := $(addprefix $(BUILD)/,$(CORE_C:.c=.o) $(CORE_CXX:.cpp=.o)) $(BUILD)/adapter.o $(BUILD)/manxtt_bridge.o $(SM2_OBJ)
.PHONY: all standalone check-sound check-eeprom check-render-background check-network
all: $(TARGET)
.PHONY: release
release:
	MACOSX_DEPLOYMENT_TARGET=13.0 $(MAKE) platform=$(platform) BUILD=$(RELEASE_BUILD) TARGET=$(RELEASE_BUILD)/model2emuex_libretro.$(EXT) all
$(TARGET): $(OBJ) Makefile src/libretro/exports.map src/libretro/exports-macos.list
	$(CXX) $(SHARED) -o $@ $(OBJ) $(LIBS)
$(BUILD)/sm2/%.o: src/libretro/sm2/%.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -Iport/imgui -c $< -o $@
$(BUILD)/manxtt_bridge.o: src/libretro/manxtt_bridge.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -c $< -o $@
$(BUILD)/sm2_input_bridge.o: src/libretro/sm2_input_bridge.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -Iport/imgui -c $< -o $@
$(BUILD)/sm2_overlay.o: src/libretro/sm2_overlay.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -Iport/imgui -c $< -o $@
$(BUILD)/sm2_timing.o: src/libretro/sm2_timing.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -Iport/imgui -c $< -o $@
$(BUILD)/stb_image.o: src/libretro/stb_image.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/net_bridge.o: src/libretro/net_bridge.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -c $< -o $@
$(BUILD)/sm2_bridge.o: src/libretro/sm2_bridge.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Isrc/libretro/sm2/include -Iport/imgui -c $< -o $@
$(BUILD)/snd/m2uart.o: port/snd/m2uart.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Iport/snd/sm2 -Isrc/libretro/sm2/include -c $< -o $@
$(BUILD)/snd/sm2/hw/i8251.o: port/snd/sm2/hw/i8251.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 -Iport/snd/sm2 -Isrc/libretro/sm2/include -c $< -o $@
$(BUILD)/adapter.o: src/libretro/libretro.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/%.o: port/%.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/%.o: port/%.cpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
standalone:
	$(MAKE) -C port BUILD=build-macos
$(BUILD)/check-sound-scheduling.o: scripts/check-sound-scheduling.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/check-sound-scheduling: $(BUILD)/check-sound-scheduling.o $(filter $(BUILD)/snd/% $(BUILD)/m68k/% $(BUILD)/ymfm/%,$(OBJ)) $(BUILD)/sm2/core/log.o
	$(CXX) -o $@ $^ -lm
$(BUILD)/check-audio-gains.o: scripts/check-audio-gains.c src/libretro/libretro.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/check-audio-gains: $(BUILD)/check-audio-gains.o $(filter-out $(BUILD)/adapter.o,$(OBJ))
	$(CXX) -o $@ $^ -lz -lm
check-sound: $(BUILD)/check-sound-scheduling $(BUILD)/check-audio-gains
	$(BUILD)/check-sound-scheduling
	$(BUILD)/check-audio-gains
-include $(BUILD)/check-audio-gains.d
$(BUILD)/check-eeprom-native: scripts/check-eeprom-native.c port/m2/m2board.c $(BUILD)/i960/i960.o $(BUILD)/tgp/tgp.o $(BUILD)/m2/m2rom.o $(BUILD)/snd/m2uart.o $(BUILD)/snd/sm2/hw/i8251.o $(BUILD)/sm2/core/log.o
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $< $(BUILD)/i960/i960.o $(BUILD)/tgp/tgp.o $(BUILD)/m2/m2rom.o $(BUILD)/snd/m2uart.o $(BUILD)/snd/sm2/hw/i8251.o $(BUILD)/sm2/core/log.o -lz -lm -lc++
check-eeprom: $(BUILD)/check-eeprom-native
	$<
$(BUILD)/check-render-background: scripts/check-render-background.c $(BUILD)/m2/m2gl.o $(BUILD)/m2/m2glapi.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $(shell pkg-config --cflags sdl2) -o $@ $^ $(shell pkg-config --libs sdl2) -lm
check-render-background: $(BUILD)/check-render-background
	$<
-include $(OBJ:.o=.d)

$(BUILD)/check-network: scripts/check-network.cpp $(BUILD)/sm2/netpacket.o $(BUILD)/m2/m2link.o
	$(CXX) -std=c++20 -O2 -Isrc/libretro/sm2 -Isrc/libretro/sm2/include -Isrc/libretro/include -Iport $^ -o $@
check-network: $(BUILD)/check-network
	$<
