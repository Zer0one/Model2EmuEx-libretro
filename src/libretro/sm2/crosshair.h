// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include "input.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace sm2::libretro {

enum class CrosshairStyle {
    Sm2,
    Supermodel,
    Auto,
    Custom,
};

struct CrosshairAim {
    bool active = false;
    float x = 0.5f;
    float y = 0.5f;
};

struct CrosshairImage {
    unsigned width = 0;
    unsigned height = 0;
    std::vector<std::uint32_t> pixels; // ARGB, including PNG alpha.
};

struct CrosshairState {
    std::array<CrosshairAim, 2> aims{};
    CrosshairStyle style = CrosshairStyle::Sm2;
    std::array<std::shared_ptr<const CrosshairImage>, 2> images{};
};

struct CrosshairRect {
    int x = 0;
    int y = 0;
    int width = 0;
    int height = 0;
    std::uint32_t colour = 0;
};

struct CrosshairGeometry {
    std::vector<CrosshairRect> rectangles;
    bool custom = false;
    std::size_t count = 0;
};

// Presentation-only state: timers and user artwork never modify game input or NVRAM.
class CrosshairPresentation {
public:
    void configure(const rom::GameSpec& game, const std::filesystem::path& directory);
    void reset_activity();
    CrosshairState update(const rom::GameSpec& game, const InputRuntime& runtime,
                          unsigned mask, CrosshairStyle style, unsigned timeout,
                          double seconds);
    std::string take_notice();
private:
    std::filesystem::path directory_;
    std::string game_, parent_, notice_;
    CrosshairStyle previous_style_ = CrosshairStyle::Sm2;
    bool loaded_ = false;
    unsigned missing_ = 0;
    unsigned notified_ = 0;
    std::array<std::shared_ptr<const CrosshairImage>, 2> images_{};
    std::array<double, 2> idle_seconds_{};
    std::array<bool, 2> used_{};
};

/// Build the visible aims selected for any recognised gun profile. The
/// Automatic core-option mask keeps positional-gun reticles hidden by default.
CrosshairState crosshair_state(const rom::GameSpec& game, const InputRuntime& runtime,
                               unsigned mask, CrosshairStyle style = CrosshairStyle::Sm2);

/// Rasterise the selected reticle into a backend-neutral list of clipped
/// rectangles.
CrosshairGeometry crosshair_geometry(const CrosshairState& state, unsigned width,
                                     unsigned height);

/// Composite the same geometry into a Libretro XRGB8888 software frame.
void draw_crosshairs(std::span<std::uint32_t> frame, unsigned width, unsigned height,
                     const CrosshairState& state);

}  // namespace sm2::libretro
