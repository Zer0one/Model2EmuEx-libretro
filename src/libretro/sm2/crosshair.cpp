// SPDX-License-Identifier: BSD-3-Clause
#include "crosshair.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <stb_image.h>
#include <utility>

namespace sm2::libretro {
namespace {

constexpr std::array<std::uint32_t, 2> kSupermodelColours = {
    0x00ff0000u, // Player 1: red, matching Supermodel's vector crosshair.
    0x0000ff00u, // Player 2: green.
};

constexpr std::array<std::uint32_t, 2> kSm2Colours = {
    0x0000ff00u, // Player 1: green, matching upstream SM2-Emu.
    0x0000c8ffu, // Player 2: cyan.
};

void add_clipped(CrosshairGeometry& geometry, int x, int y, int width, int height,
                 unsigned frame_width, unsigned frame_height, std::uint32_t colour)
{
    const int x0 = std::clamp(x, 0, static_cast<int>(frame_width));
    const int y0 = std::clamp(y, 0, static_cast<int>(frame_height));
    const int x1 = std::clamp(x + width, 0, static_cast<int>(frame_width));
    const int y1 = std::clamp(y + height, 0, static_cast<int>(frame_height));
    if (x1 <= x0 || y1 <= y0) return;
    geometry.rectangles.push_back({x0, y0, x1 - x0, y1 - y0, colour});
    geometry.count = geometry.rectangles.size();
}

void add_sm2_crosshair(CrosshairGeometry& geometry, int cx, int cy, int scale,
                       unsigned frame_width, unsigned frame_height,
                       std::uint32_t colour)
{
    // Upstream draws an eight-pixel radius circle with four cardinal lines.
    // Scale it with the core's internal raster so it retains the same apparent
    // size after the frontend presents an upscaled frame.
    const int radius = 8 * scale;
    const int thickness = 2 * scale;
    const int outer = radius + thickness / 2;
    const int inner = std::max(0, radius - (thickness + 1) / 2);
    for (int dy = -outer; dy <= outer; ++dy) {
        const int outer_x = static_cast<int>(std::floor(std::sqrt(
            static_cast<double>(outer * outer - dy * dy))));
        int inner_x = -1;
        if (std::abs(dy) < inner) {
            inner_x = static_cast<int>(std::floor(std::sqrt(
                static_cast<double>(inner * inner - dy * dy))));
        }
        if (inner_x < 0) {
            add_clipped(geometry, cx - outer_x, cy + dy, 2 * outer_x + 1, 1,
                        frame_width, frame_height, colour);
        } else {
            add_clipped(geometry, cx - outer_x, cy + dy, outer_x - inner_x, 1,
                        frame_width, frame_height, colour);
            add_clipped(geometry, cx + inner_x + 1, cy + dy, outer_x - inner_x, 1,
                        frame_width, frame_height, colour);
        }
    }

    const int near = (radius * 2) / 5;
    const int far = (radius * 8) / 5;
    const int half = thickness / 2;
    add_clipped(geometry, cx - far, cy - half, far - near, thickness,
                frame_width, frame_height, colour);
    add_clipped(geometry, cx + near, cy - half, far - near, thickness,
                frame_width, frame_height, colour);
    add_clipped(geometry, cx - half, cy - far, thickness, far - near,
                frame_width, frame_height, colour);
    add_clipped(geometry, cx - half, cy + near, thickness, far - near,
                frame_width, frame_height, colour);
}

void add_supermodel_crosshair(CrosshairGeometry& geometry, int cx, int cy, int scale,
                              unsigned frame_width, unsigned frame_height,
                              std::uint32_t colour)
{
    constexpr int layers = 8;
    constexpr int base_half_width = 3;
    const int gap = 2 * scale;
    for (int layer = 0; layer < layers; ++layer) {
        const int distance = gap + layer * scale;
        const int half_width = std::max(scale,
            ((layer + 1) * base_half_width * scale + layers - 1) / layers);
        const int span = 2 * half_width + 1;
        add_clipped(geometry, cx - half_width, cy - distance - scale + 1,
                    span, scale, frame_width, frame_height, colour);
        add_clipped(geometry, cx - half_width, cy + distance,
                    span, scale, frame_width, frame_height, colour);
        add_clipped(geometry, cx - distance - scale + 1, cy - half_width,
                    scale, span, frame_width, frame_height, colour);
        add_clipped(geometry, cx + distance, cy - half_width,
                    scale, span, frame_width, frame_height, colour);
    }
}

}  // namespace

void CrosshairPresentation::configure(const rom::GameSpec& game,
                                      const std::filesystem::path& directory)
{
    directory_ = directory;
    game_ = game.name;
    parent_ = game.parent;
    images_ = {};
    loaded_ = false;
    notice_.clear();
    reset_activity();
}

void CrosshairPresentation::reset_activity()
{
    idle_seconds_ = {};
    used_ = {};
}

std::string CrosshairPresentation::take_notice()
{
    return std::exchange(notice_, {});
}

CrosshairState CrosshairPresentation::update(const rom::GameSpec& game,
    const InputRuntime& runtime, unsigned mask, CrosshairStyle style,
    unsigned timeout, double seconds)
{
    const auto profile = recognize_profile(game);
    if (profile != InputProfile::Gun && profile != InputProfile::GunBehindEnemyLines)
        return {};
    if ((style == CrosshairStyle::Auto || style == CrosshairStyle::Custom)
        && (!loaded_ || style != previous_style_)) {
        images_ = {};
        missing_ = notified_ = 0;
        for (unsigned player = 0; player < images_.size(); ++player) {
            for (const auto& stem : {game_, parent_, std::string("default")}) {
                // Database names must never escape the frontend system directory.
                if (stem.empty() || stem == "." || stem == ".."
                    || stem.find_first_of("/\\") != std::string::npos) continue;
                const std::string suffix = "-p" + std::to_string(player + 1);
                for (const auto& name : {stem + suffix, stem}) {
                    const auto path = directory_ / (name + ".png");
                    std::ifstream file(path, std::ios::binary | std::ios::ate);
                    if (!file) continue;
                    const auto size = file.tellg();
                    if (size < 8 || size > 16 * 1024 * 1024) continue;
                    std::vector<stbi_uc> bytes(static_cast<std::size_t>(size));
                    file.seekg(0);
                    if (!file.read(reinterpret_cast<char*>(bytes.data()), size)) continue;
                    constexpr std::array<stbi_uc, 8> signature{137, 80, 78, 71, 13, 10, 26, 10};
                    if (!std::equal(signature.begin(), signature.end(), bytes.begin())) continue;
                    int w = 0, h = 0, channels = 0;
                    // Decode the same bounded buffer inspected here. Native path
                    // streams also support Unicode system directories on Windows.
                    if (!stbi_info_from_memory(bytes.data(), static_cast<int>(size), &w, &h, &channels)
                        || w <= 0 || h <= 0 || w > 1024 || h > 1024) continue;
                    const std::unique_ptr<stbi_uc, decltype(&stbi_image_free)> rgba(
                        stbi_load_from_memory(bytes.data(), static_cast<int>(size), &w, &h, &channels, 4),
                        stbi_image_free);
                    if (!rgba) continue;
                    auto image = std::make_shared<CrosshairImage>();
                    image->width = static_cast<unsigned>(w);
                    image->height = static_cast<unsigned>(h);
                    image->pixels.resize(static_cast<std::size_t>(w) * h);
                    for (std::size_t i = 0; i < image->pixels.size(); ++i)
                        image->pixels[i] = (std::uint32_t(rgba.get()[4*i+3]) << 24)
                            | (std::uint32_t(rgba.get()[4*i]) << 16)
                            | (std::uint32_t(rgba.get()[4*i+1]) << 8) | rgba.get()[4*i+2];
                    images_[player] = std::move(image);
                    break;
                }
                if (images_[player]) break;
            }
            if (!images_[player]) missing_ |= 1u << player;
        }
        loaded_ = true;
    }
    const unsigned report = missing_ & mask & ~notified_ & 3u;
    if (style == CrosshairStyle::Custom && report) {
        notice_ = "Custom crosshair PNG missing or invalid for "
            + std::string(report == 3 ? "P1/P2" : report == 1 ? "P1" : "P2")
            + ". Add PNGs to system/sm2-emu/crosshairs/ and reload content.";
        notified_ |= report;
    }
    previous_style_ = style;
    auto result = crosshair_state(game, runtime, mask, style);
    if (style == CrosshairStyle::Auto || style == CrosshairStyle::Custom)
        result.images = images_;
    for (unsigned player = 0; player < used_.size(); ++player) {
        if (runtime.gun_activity[player]) {
            used_[player] = true;
            idle_seconds_[player] = 0;
        } else {
            idle_seconds_[player] += std::max(0.0, seconds);
        }
        if (timeout && (!used_[player] || idle_seconds_[player] >= timeout))
            result.aims[player].active = false;
    }
    return result;
}

CrosshairState crosshair_state(const rom::GameSpec& game, const InputRuntime& runtime,
                               unsigned mask, CrosshairStyle style)
{
    CrosshairState state{};
    state.style = style;
    const InputProfile profile = recognize_profile(game);
    if (profile != InputProfile::Gun && profile != InputProfile::GunBehindEnemyLines)
        return state;
    mask &= 3u;
    for (unsigned player = 0; player < state.aims.size(); ++player) {
        auto& aim = state.aims[player];
        aim.active = (mask & (1u << player)) && runtime.gun_aim_active[player]
            && !runtime.gun_aim_offscreen[player];
        aim.x = static_cast<float>(runtime.gun_cursor_x[player]) / 495.0f;
        aim.y = static_cast<float>(runtime.gun_cursor_y[player]) / 383.0f;
    }
    return state;
}

CrosshairGeometry crosshair_geometry(const CrosshairState& state, unsigned width,
                                     unsigned height)
{
    CrosshairGeometry geometry{};
    if (!width || !height || std::none_of(state.aims.begin(), state.aims.end(),
            [](const auto& aim) { return aim.active; })) return geometry;
    geometry.rectangles.reserve(128);
    const int scale = std::max(1, std::min(static_cast<int>(width / 496u),
                                           static_cast<int>(height / 384u)));
    for (unsigned player = 0; player < state.aims.size(); ++player) {
        const auto& aim = state.aims[player];
        if (!aim.active) continue;
        const int cx = static_cast<int>(std::lround(
            std::clamp(aim.x, 0.0f, 1.0f) * static_cast<float>(width - 1)));
        const int cy = static_cast<int>(std::lround(
            std::clamp(aim.y, 0.0f, 1.0f) * static_cast<float>(height - 1)));
        if (state.images[player]) {
            geometry.custom = true;
            const auto& image = *state.images[player];
            // Match upstream's PNG size at 1080 lines; use integer boundaries
            // shared by Software and both GPU renderers, including clipping.
            const double factor = static_cast<double>(height) / 1080.0;
            const double left = cx - image.width * factor / 2.0;
            const double top = cy - image.height * factor / 2.0;
            for (unsigned y = 0; y < image.height; ++y) {
                const int y0 = static_cast<int>(std::lround(top + y * factor));
                const int y1 = static_cast<int>(std::lround(top + (y + 1) * factor));
                if (y0 == y1) continue;
                for (unsigned x = 0; x < image.width;) {
                    const auto colour = image.pixels[y * image.width + x];
                    const unsigned start = x++;
                    while (x < image.width && image.pixels[y * image.width + x] == colour) ++x;
                    if (!(colour >> 24)) continue;
                    const int x0 = static_cast<int>(std::lround(left + start * factor));
                    const int x1 = static_cast<int>(std::lround(left + x * factor));
                    add_clipped(geometry, x0, y0, x1 - x0, y1 - y0, width, height, colour);
                }
            }
            continue;
        }
        if (state.style == CrosshairStyle::Custom) continue;
        if (state.style != CrosshairStyle::Supermodel)
            add_sm2_crosshair(geometry, cx, cy, scale, width, height,
                              0xff000000u | kSm2Colours[player]);
        else
            add_supermodel_crosshair(geometry, cx, cy, scale, width, height,
                                     0xff000000u | kSupermodelColours[player]);
    }
    return geometry;
}

void draw_crosshairs(std::span<std::uint32_t> frame, unsigned width, unsigned height,
                     const CrosshairState& state)
{
    if (frame.size() < static_cast<std::size_t>(width) * height) return;
    const CrosshairGeometry geometry = crosshair_geometry(state, width, height);
    for (std::size_t i = 0; i < geometry.count; ++i) {
        const auto& rect = geometry.rectangles[i];
        for (int y = rect.y; y < rect.y + rect.height; ++y) {
            auto row = frame.begin() + static_cast<std::ptrdiff_t>(y) * width + rect.x;
            const unsigned alpha = rect.colour >> 24;
            if (alpha == 255) {
                std::fill_n(row, rect.width, rect.colour & 0xffffffu);
                continue;
            }
            for (int x = 0; x < rect.width; ++x) {
                std::uint32_t result = 0;
                for (unsigned shift : {0u, 8u, 16u}) {
                    const unsigned source = (rect.colour >> shift) & 255;
                    const unsigned destination = (row[x] >> shift) & 255;
                    result |= ((source * alpha + destination * (255 - alpha) + 127) / 255) << shift;
                }
                row[x] = result;
            }
        }
    }
}

}  // namespace sm2::libretro
