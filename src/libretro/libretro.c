/* Frontend-owned Libretro integration; optional machine hooks remain frontend-neutral. */
#include "libretro.h"
#include "m2/m2board.h"
#include "m2/m2input.h"
#include "m2/m2gl.h"
#include "m2/m2glapi.h"
#include "snd/m2snd.h"
#include "m2/m2pipe.h"
#include "sm2_bridge.h"
#include "sm2_input_bridge.h"
#include "sm2_overlay.h"
#include "sm2_timing.h"
#include "net_bridge.h"
#include "manxtt_bridge.h"
#include <pthread.h>
#include <math.h>
#include <zlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static retro_environment_t env;
static retro_video_refresh_t video;
static retro_audio_sample_t audio;
static retro_audio_sample_batch_t audio_batch;
static retro_input_poll_t poll_input;
static retro_input_state_t input;
static retro_log_printf_t logger;
static struct retro_hw_render_callback hw;
static m2_board *board;
static m2_tilegen *tiles;
static m2_geo *geo;
static m2_gl *renderer;
static m2_mesh *mesh;
static m2_snd *sound;
static m2_link external_link;
static unsigned linked_cabinets=1;
static int logged_link_state=-1;
static bool configure_network(void);
static m2_input_state controls;
static uint8_t nvram[M2_NVRAM_SIZE];
static bool first_frame, sm2_profile;
static unsigned devices[2] = { RETRO_DEVICE_JOYPAD, RETRO_DEVICE_JOYPAD };
static double sample_debt;
static bool native_timing, audio_failed, state_options_pending, state_had_frame;
static bool content_failed, nvram_pending, network_reset_pending;
static unsigned nvram_wait_frames;
static uint32_t state_rom_crc;
static bool state_trace;
static unsigned state_trace_remaining;
static void state_trace_event(const char *event)
{
    if(!state_trace || !board)return;
    char line[128];snprintf(line,sizeof line,"M2_STATE_TRACE %s %llu",event,(unsigned long long)board->frame);
    if(logger)logger(RETRO_LOG_INFO,"%s\n",line);else fprintf(stderr,"%s\n",line);
    /* The isolated frame-step runner reads this opt-in trace while paused.
     * A frontend can buffer its console logger until process exit. */
    fflush(stdout);fflush(stderr);
}
static unsigned output_sample_remainder;
static size_t audio_pending;
static int16_t audio_queue[M2SND_RATE * 2];
static int resolution = 1;
static int texture_filter = M2_TEX_NEAREST;
static int mesh_blend = 1;
static float saturation = 1.0f;
static float gamma_rgb[3] = {1, 1, 1};
static int aspect_ratio; /* 0 Auto; 1 4:3; 2 16:9; 3 16:10 */
static bool expand_3d;
static bool pipeline_enabled = true, frame_skip_enabled = true;
static bool audio_underrun;
static unsigned skips_in_row, timing_font_pixels;
static double machine_frame_ms, frame_video_ms;
static unsigned output_width = 496, output_height = 384;
static float output_aspect = 4.0f/3.0f;
static m2_pipe *frame_pipe;
static const m2_board *video_board;
static m2_hooks replay_hooks;
static m2_pipe_frame pipe_frame;
static pthread_t worker_thread;
static pthread_mutex_t worker_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t worker_cond = PTHREAD_COND_INITIALIZER;
static bool worker_running, worker_quit, worker_job, worker_done;
#define COLOUR_VALUES {"0.50", NULL}, {"0.55", NULL}, {"0.60", NULL}, {"0.65", NULL}, \
 {"0.70", NULL}, {"0.75", NULL}, {"0.80", NULL}, {"0.85", NULL}, {"0.90", NULL}, \
 {"0.95", NULL}, {"1.00", NULL}, {"1.05", NULL}, {"1.10", NULL}, {"1.15", NULL}, \
 {"1.20", NULL}, {"1.25", NULL}, {"1.30", NULL}, {"1.35", NULL}, {"1.40", NULL}, \
 {"1.45", NULL}, {"1.50", NULL}, {"1.55", NULL}, {"1.60", NULL}, {"1.65", NULL}, \
 {"1.70", NULL}, {"1.75", NULL}, {"1.80", NULL}, {"1.85", NULL}, {"1.90", NULL}, \
 {"1.95", NULL}, {"2.00", NULL}
#define GAIN_VALUES {"auto", "Auto"}, {"0", "Mute"}, {"10", "10%"}, {"20", "20%"}, \
 {"30", "30%"}, {"40", "40%"}, {"50", "50%"}, {"60", "60%"}, \
 {"70", "70%"}, {"80", "80%"}, {"90", "90%"}, {"100", "100%"}
#define GAIN_OPTION(key, label, help) {"model2emuex_" key, label, NULL, \
 help " Auto preserves the emulator's native mix. Mute silences this source while emulation continues. Applies on return to the game without a reset. Has no effect on boards without this sound source.", \
 NULL, "audio", {GAIN_VALUES, {NULL, NULL}}, "auto"}
#define COLOUR_LEGACY "1.00|0.50|0.55|0.60|0.65|0.70|0.75|0.80|0.85|0.90|0.95|1.05|1.10|1.15|1.20|1.25|1.30|1.35|1.40|1.45|1.50|1.55|1.60|1.65|1.70|1.75|1.80|1.85|1.90|1.95|2.00"
static void (M2GL_APIENTRY *bind_framebuffer)(GLenum, GLuint);

static struct retro_core_option_v2_category categories[] = {
    {"system", "System", "Machine And NVRAM Settings"},
    {"video", "Video", "Rendering And Image Presentation"},
    {"audio", "Audio", "Sound Source Levels"},
    {"input", "Input", "Controller Profiles And Input Response"},
    {NULL, NULL, NULL}
};
static struct retro_core_option_v2_definition definitions[] = {
    {"model2emuex_rom_crc_verification", "ROM CRC Verification (Restart Required)", NULL,
     "Verify ROM-chip contents against their declared CRC32 checksums. Disabled skips CRC matching, while size and decompression checks remain active. Applies after closing and reloading content.",
     NULL, "system", {{"enabled", "Enabled"}, {"disabled", "Disabled"}, {NULL, NULL}}, "enabled"},
    {"model2emuex_internal_resolution", "Internal Resolution", NULL,
     "Select the internal rendering resolution to balance image quality and GPU load. Changes apply when returning to the game without a reset.",
     NULL, "video", {{"1", "1x (496 x 384)"}, {"2", "2x (992 x 768)"},
                      {"3", "3x (1488 x 1152)"}, {"4", "4x (1984 x 1536)"}, {NULL, NULL}}, "1"},
    {"model2emuex_texture_filter", "3D Texture Filtering", NULL,
     "Select the texture-sampling filter used by the 3D renderer. Uses the emulator's native Nearest, Bilinear or Trilinear filtering. Changes apply when returning to the game without a reset. If a filter shader is unavailable, the renderer uses the next supported filter.",
     NULL, "video", {{"nearest", "Nearest"}, {"bilinear", "Bilinear"},
                      {"trilinear", "Trilinear"}, {NULL, NULL}}, "nearest"},
    {"model2emuex_aspect_ratio", "Aspect Ratio", NULL,
     "Select the displayed aspect ratio. Auto follows Widescreen Mode. Explicit 4:3 suppresses expansion; 16:9 or 16:10 with Widescreen Mode Disabled stretches the original image. Changes apply when returning to the game without a reset.",
     NULL, "video", {{"auto", "Auto"}, {"4_3", "4:3"}, {"16_9", "16:9"}, {"16_10", "16:10"}, {NULL, NULL}}, "auto"},
    {"model2emuex_widescreen_mode", "Widescreen Mode", NULL,
     "Expand the 3D field of view using native per-game geometry and layer rules. Requires Aspect Ratio Auto, 16:9 or 16:10; explicit 4:3 suppresses expansion. Auto reports 16:9 when enabled. Disabled preserves Aspect Ratio and original rendering. Changes apply when returning to the game without a reset.",
     NULL, "video", {{"stretch", "Disabled"}, {"expand_3d", "Expand 3D View Only"}, {NULL, NULL}}, "stretch"},
    {"model2emuex_av_timing", "A/V Timing (Restart Required)", NULL,
     "Select the video cadence and corresponding audio timing. 60 Hz adapts native audio to the frontend cadence using the SM2-Emu interpolation policy; 58 Hz preserves the cadence declared by Model2EmuEx. Each callback still executes one complete native machine frame. Applies after closing and reloading content.",
     NULL, "video", {{"60hz", "60 Hz (Default)"}, {"native", "58 Hz (Native Model2EmuEx)"}, {NULL, NULL}}, "60hz"},
    {"model2emuex_timing_overlay", "Timing / FPS Overlay", NULL,
     "Display 61-frame averages for machine, video, audio/pacing, retro_run and worst-frame time, plus actual frontend cadence and estimated processing capacity. Auto uses 13 px. CPU wall times include graphics submission, not GPU execution queries. Applies on return to the game without a reset.",
     NULL, "video", {{"disabled", "Off"}, {"auto", "Auto"}, {"11", "On (11 px)"}, {"12", "On (12 px)"},
        {"13", "On (13 px)"}, {"14", "On (14 px)"}, {NULL,NULL}}, "disabled"},
    {"model2emuex_pipeline", "Pipeline", NULL,
     "Emulate the next frame on another processor core while rendering the previous frame. Enabled can improve performance on multi-core systems, at the cost of one extra frame of video latency (about 17 ms). Disabled emulates and renders in turn for lower latency. Changes apply when returning to the game without a reset.",
     NULL, "video", {{"enabled", "Enabled"}, {"disabled", "Disabled"}, {NULL, NULL}}, "enabled"},
    {"model2emuex_frame_skip", "Frame Skip", NULL,
     "Skip drawing when the frontend reports an imminent audio underrun, at most two frames in a row. Emulation, sound and inputs continue. If audio-buffer status is unavailable, frames are not skipped. Applies on return to the game without a reset.",
     NULL, "video", {{"enabled", "Enabled"}, {"disabled", "Disabled"}, {NULL, NULL}}, "enabled"},
    {"model2emuex_mesh", "Shadows And Fences", NULL,
     "Select native mesh transparency: Blend draws 50% transparency; Checker preserves the hardware checkerboard. Changes apply on return to the game without a reset.",
     NULL, "video", {{"blend", "Blend (50% See-Through)"}, {"checker", "Checker (As The Hardware)"}, {NULL, NULL}}, "blend"},
    {"model2emuex_saturation", "Saturation", NULL,
     "Adjust native colour saturation from 0.50 to 2.00. 1.00 preserves native colours. Changes apply on return to the game without a reset.",
     NULL, "video", {COLOUR_VALUES, {NULL, NULL}}, "1.00"},
    {"model2emuex_gamma_r", "Gamma (Red)", NULL,
     "Adjust the native red-channel brightness curve from 0.50 to 2.00. Above 1.00 brightens mid-tones; below 1.00 darkens them. Applies on return to the game without a reset.",
     NULL, "video", {COLOUR_VALUES, {NULL, NULL}}, "1.00"},
    {"model2emuex_gamma_g", "Gamma (Green)", NULL,
     "Adjust the native green-channel brightness curve from 0.50 to 2.00. Above 1.00 brightens mid-tones; below 1.00 darkens them. Applies on return to the game without a reset.",
     NULL, "video", {COLOUR_VALUES, {NULL, NULL}}, "1.00"},
    {"model2emuex_gamma_b", "Gamma (Blue)", NULL,
     "Adjust the native blue-channel brightness curve from 0.50 to 2.00. Above 1.00 brightens mid-tones; below 1.00 darkens them. Applies on return to the game without a reset.",
     NULL, "video", {COLOUR_VALUES, {NULL, NULL}}, "1.00"},
    {"model2emuex_manxtt_cabinet_audio", "Manx TT: Cabinet Audio", NULL,
     "Select cabinet-appropriate sound ROMs and the additional sound board based on the selected cabinet configuration.",
     NULL, "audio", {{"enabled", "Enabled"}, {"disabled", "Disabled"}, {NULL, NULL}}, "enabled"},
    GAIN_OPTION("scsp_gain", "SCSP Gain", "Adjust the SCSP sound source."),
    GAIN_OPTION("multipcm1_gain", "MultiPCM 1 Gain", "Adjust the first MultiPCM sound source."),
    GAIN_OPTION("multipcm2_gain", "MultiPCM 2 Gain", "Adjust the second MultiPCM sound source."),
    GAIN_OPTION("ym3438_gain", "FM (YM3438) Gain", "Adjust the YM3438 FM sound source."),
    {0}
};
static const struct retro_variable legacy[] = {
    {"model2emuex_internal_resolution", "Internal Resolution; 1|2|3|4"},
    {"model2emuex_texture_filter", "3D Texture Filtering; nearest|bilinear|trilinear"},
    {"model2emuex_aspect_ratio", "Aspect Ratio; auto|4_3|16_9|16_10"},
    {"model2emuex_widescreen_mode", "Widescreen Mode; stretch|expand_3d"},
    {"model2emuex_pipeline", "Pipeline; enabled|disabled"},
    {"model2emuex_frame_skip", "Frame Skip; enabled|disabled"},
    {"model2emuex_mesh", "Shadows And Fences; blend|checker"},
    {"model2emuex_saturation", "Saturation; " COLOUR_LEGACY},
    {"model2emuex_gamma_r", "Gamma (Red); " COLOUR_LEGACY},
    {"model2emuex_gamma_g", "Gamma (Green); " COLOUR_LEGACY},
    {"model2emuex_gamma_b", "Gamma (Blue); " COLOUR_LEGACY},
    {NULL, NULL}
};
static void logmsg(const char *s)
{
    if (logger) logger(RETRO_LOG_INFO, "%s\n", s);
    else fprintf(stderr, "Model2EmuEx: %s\n", s);
}
static void failure(const char *text)
{
    m2lr_net_error(text);
    sm2lr_input_stop_rumble();
    content_failed = true;
    if (env) env(RETRO_ENVIRONMENT_SHUTDOWN, NULL);
}
static bool load_error(const char *text)
{
    m2lr_net_error(text);
    retro_unload_game();
    return false;
}
static char rom_detail[512];
static void rom_log(const char *text)
{
    snprintf(rom_detail, sizeof rom_detail, "%s", text);
    logmsg(text);
}
/* Upstream renders its final pass to framebuffer zero. Translate that binding
 * at the adapter boundary to the frontend's current framebuffer, including
 * nonzero FBOs; never create a window, swap buffers or replace the context. */
static void M2GL_APIENTRY frontend_bind(GLenum target, GLuint fbo)
{
    bind_framebuffer(target, fbo ? fbo : (GLuint)hw.get_current_framebuffer());
}
static void *getproc(const char *name)
{
    retro_proc_address_t proc = hw.get_proc_address(name);
    void *p = NULL;
    memcpy(&p, &proc, sizeof p);
    return p;
}
static void context_destroy(void)
{
    sm2lr_timing_gl_destroy();
    sm2lr_overlay_destroy();
    if (renderer) m2gl_destroy(renderer);
    renderer = NULL;
}
static void context_reset(void)
{
    const char *missing = NULL;
    /* Like SM2, reset can follow unannounced context loss: old GL names may
     * identify unrelated objects in the new context. Release CPU state only. */
    sm2lr_timing_gl_abandon();
    sm2lr_overlay_abandon();
    m2gl_abandon(renderer); renderer = NULL;
    if (!hw.get_proc_address || !hw.get_current_framebuffer) {
        failure("Frontend did not supply the required OpenGL callbacks");return;
    }
    if (!m2glapi_load(getproc, &missing)) {
        char text[256];snprintf(text,sizeof text,"OpenGL initialization failed: %s",missing?missing:"entry points unavailable");
        failure(text);
        return;
    }
    bind_framebuffer = m2_glBindFramebuffer;
    m2_glBindFramebuffer = frontend_bind;
    renderer = m2gl_create(0);
    sm2lr_timing_gl_proc(hw.get_proc_address);
    if (!renderer) { failure("OpenGL renderer initialization failed");return; }
    if (!sm2lr_overlay_reset(hw.get_proc_address)) m2lr_net_message("Crosshair overlay initialization failed");
    if (tiles) memset(tiles->row_dirty, 1, sizeof tiles->row_dirty);
}
static void on_tile(void *u, uint32_t o) { (void)u; m2tile_tile_written(tiles, o); }
static void on_cg(void *u) { (void)u; m2tile_cg_written(tiles); }
static void on_xlat(void *u) { (void)u; m2tile_xlat_written(tiles); if (renderer) m2gl_xlat_written(renderer); }
static void on_pal(void *u, uint32_t o) { (void)u; m2tile_palette_written(tiles, o); if (renderer) m2gl_palette_written(renderer, o); }
static void on_tex(void *u, int bank, uint32_t o) { (void)u; if (renderer) m2gl_texture_written(renderer, bank, o); }
static void on_luma(void *u) { (void)u; if (renderer) m2gl_luma_written(renderer); }
static void on_drive_raw(void *u, uint8_t value) { (void)u; sm2lr_input_drive_write(value); }
static void on_sound(void *u, uint8_t cmd) { (void)u; if (sound) m2snd_command(sound, cmd); m2lr_manxtt_command(cmd); }
static void save_memory(void)
{
    memcpy(nvram, board->back, 0x10000);
    memcpy(nvram + 0x10000, board->eeprom.data, 128);
}
static void load_memory(void)
{
    memcpy(board->back, nvram, 0x10000);
    memcpy(board->eeprom.data, nvram + 0x10000, 128);
}
static float colour_option(const char *key)
{
    struct retro_variable v = {key, NULL};
    if (env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value) {
        static const struct retro_core_option_value levels[] = {COLOUR_VALUES};
        for (unsigned i = 0; i < sizeof levels / sizeof levels[0]; i++)
            if (!strcmp(v.value, levels[i].value)) return 0.5f + i * 0.05f;
    }
    return 1.0f;
}
static bool option_is(const char *key, const char *value)
{
    struct retro_variable v = {key, NULL};
    return env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value && !strcmp(v.value, value);
}
static unsigned gain_option(const char *key)
{
    struct retro_variable v = {key, NULL};
    if (env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value) {
        static const struct retro_core_option_value values[] = {GAIN_VALUES};
        for (unsigned i = 1; i < sizeof values / sizeof values[0]; i++)
            if (!strcmp(v.value, values[i].value)) return (unsigned)atoi(v.value);
    }
    return 100;
}
static void clear_audio(void)
{
    sample_debt = 0; output_sample_remainder = 0;
    audio_pending = 0; audio_failed = false;
}
/* Same endpoint interpolation and retained-batch policy as SM2-Emu's
 * collect_fast_audio/send_audio. Native mode bypasses interpolation entirely. */
static bool send_audio(const int16_t *source, size_t source_frames)
{
    size_t count = source_frames;
    if (!native_timing) {
        output_sample_remainder += M2SND_RATE;
        count = output_sample_remainder / 60;
        output_sample_remainder %= 60;
    }
    if (count + audio_pending > M2SND_RATE) {
        failure("Frontend audio stalled for more than one second");
        audio_failed = true;
        return false;
    }
    int16_t *out = audio_queue + audio_pending * 2;
    if (native_timing) memcpy(out, source, count * 2 * sizeof *out);
    else {
        const size_t denominator = count > 1 ? count - 1 : 1;
        for (size_t frame = 0; frame < count; frame++) {
            const size_t position = frame * (source_frames - 1);
            const size_t left = position / denominator;
            const size_t right = left + 1 < source_frames ? left + 1 : left;
            const int64_t fraction = position % denominator;
            for (unsigned ch = 0; ch < 2; ch++)
                out[frame * 2 + ch] = (int16_t)((source[left * 2 + ch] *
                    ((int64_t)denominator - fraction) + source[right * 2 + ch] * fraction)
                    / (int64_t)denominator);
        }
    }
    audio_pending += count;
    size_t accepted = audio_pending;
    if (audio_batch) accepted = audio_batch(audio_queue, audio_pending);
    else if (audio)
        for (size_t i = 0; i < audio_pending; i++) audio(audio_queue[i*2], audio_queue[i*2+1]);
    if (accepted > audio_pending) {
        failure("Frontend returned an invalid audio batch size");
        audio_failed = true;
        return false;
    }
    audio_pending -= accepted;
    memmove(audio_queue, audio_queue + accepted * 2, audio_pending * 2 * sizeof *audio_queue);
    return true;
}
static void read_options(void)
{
    struct retro_variable v = {"model2emuex_internal_resolution", NULL};
    resolution = 1;
    if (env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value &&
        v.value[0] >= '1' && v.value[0] <= '4' && !v.value[1]) resolution = v.value[0] - '0';
    texture_filter = M2_TEX_NEAREST;
    v = (struct retro_variable){"model2emuex_texture_filter", NULL};
    if (env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value) {
        if (!strcmp(v.value, "bilinear")) texture_filter = M2_TEX_BILINEAR;
        else if (!strcmp(v.value, "trilinear")) texture_filter = M2_TEX_TRILINEAR;
    }
    aspect_ratio = option_is("model2emuex_aspect_ratio", "4_3") ? 1 :
        option_is("model2emuex_aspect_ratio", "16_9") ? 2 :
        option_is("model2emuex_aspect_ratio", "16_10") ? 3 : 0;
    expand_3d = option_is("model2emuex_widescreen_mode", "expand_3d") && aspect_ratio != 1;
    timing_font_pixels = 0;
    v = (struct retro_variable){"model2emuex_timing_overlay",NULL};
    if (env(RETRO_ENVIRONMENT_GET_VARIABLE,&v) && v.value) {
        if (!strcmp(v.value,"auto")) timing_font_pixels=13;
        for (unsigned font=11;font<=14;font++) {
            char key[3];snprintf(key,sizeof key,"%u",font);
            if (!strcmp(v.value,key)) timing_font_pixels=font;
        }
    }
    sm2lr_timing_config(timing_font_pixels,native_timing,board && native_timing?board->game->fps:60.0);
    pipeline_enabled = !option_is("model2emuex_pipeline", "disabled");
    frame_skip_enabled = !option_is("model2emuex_frame_skip", "disabled");
    if (sound) m2snd_set_gains(sound, gain_option("model2emuex_scsp_gain"),
        gain_option("model2emuex_multipcm1_gain"), gain_option("model2emuex_multipcm2_gain"),
        gain_option("model2emuex_ym3438_gain"));
    m2lr_manxtt_gains(gain_option("model2emuex_multipcm1_gain"),gain_option("model2emuex_multipcm2_gain"),gain_option("model2emuex_ym3438_gain"));
    mesh_blend = !option_is("model2emuex_mesh", "checker");
    saturation = colour_option("model2emuex_saturation");
    float next_gamma[3] = {colour_option("model2emuex_gamma_r"),
        colour_option("model2emuex_gamma_g"), colour_option("model2emuex_gamma_b")};
    bool gamma_changed = memcmp(next_gamma, gamma_rgb, sizeof gamma_rgb) != 0;
    memcpy(gamma_rgb, next_gamma, sizeof gamma_rgb);
    if (tiles && gamma_changed) {
        m2tile_init(tiles, gamma_rgb[0], gamma_rgb[1], gamma_rgb[2]);
        if (renderer) { m2gl_xlat_written(renderer); m2gl_luma_written(renderer); }
    }

}
static void board_step(void)
{
    double start = timing_font_pixels ? sm2lr_timing_clock() : 0;
    m2_run_frame(board);
    m2pipe_capture(frame_pipe, board);
    machine_frame_ms = timing_font_pixels ? sm2lr_timing_clock()-start : 0;
}
static void *worker_main(void *unused)
{
    (void)unused;
    pthread_mutex_lock(&worker_mutex);
    for (;;) {
        while (!worker_job && !worker_quit) pthread_cond_wait(&worker_cond, &worker_mutex);
        if (worker_quit) break;
        worker_job = false;
        pthread_mutex_unlock(&worker_mutex);
        board_step();
        pthread_mutex_lock(&worker_mutex);
        worker_done = true;
        pthread_cond_broadcast(&worker_cond);
    }
    pthread_mutex_unlock(&worker_mutex);
    return NULL;
}
static bool worker_start_frame(void)
{
    if (!worker_running) {
        worker_quit = worker_job = worker_done = false;
        if (pthread_create(&worker_thread, NULL, worker_main, NULL)) {
            logmsg("Pipeline worker unavailable; using synchronous execution");
            return false;
        }
        worker_running = true;
    }
    pthread_mutex_lock(&worker_mutex);
    worker_done = false; worker_job = true;
    pthread_cond_broadcast(&worker_cond);
    pthread_mutex_unlock(&worker_mutex);
    return true;
}
static void worker_wait(void)
{
    pthread_mutex_lock(&worker_mutex);
    while (!worker_done) pthread_cond_wait(&worker_cond, &worker_mutex);
    pthread_mutex_unlock(&worker_mutex);
}
static void worker_stop(void)
{
    if (!worker_running) return;
    pthread_mutex_lock(&worker_mutex);
    worker_quit = true;
    pthread_cond_broadcast(&worker_cond);
    pthread_mutex_unlock(&worker_mutex);
    pthread_join(worker_thread, NULL);
    worker_running = worker_quit = worker_job = worker_done = false;
}
static void audio_buffer_status(bool active, unsigned occupancy, bool underrun_likely)
{
    (void)occupancy;
    audio_underrun = active && underrun_likely;
}
static void draw_frame_impl(bool previous_frame)
{
    if (!renderer || !video_board) return;
    double ratio = aspect_ratio == 3 ? 16.0/10.0 :
        (aspect_ratio == 2 || (aspect_ratio == 0 && expand_3d)) ? 16.0/9.0 : 4.0/3.0;
    int width = expand_3d ? ((int)(M2_SCREEN_W * ratio * 0.75 + 0.5) + 1) & ~1 : M2_SCREEN_W;
    unsigned w = (unsigned)(width * resolution), h = 384u * resolution;
    if (w != output_width || h != output_height || (float)ratio != output_aspect) {
        output_width = w; output_height = h; output_aspect = (float)ratio;
        struct retro_game_geometry geometry = {w, h, 2656, 1536, (float)ratio};
        env(RETRO_ENVIRONMENT_SET_GEOMETRY, &geometry);
    }
    bool skip = frame_skip_enabled && audio_underrun && skips_in_row < 2;
    if (skip) {
        skips_in_row++;
        if (video) video(NULL, w, h, 0);
        return;
    }
    skips_in_row = 0;
    geo->wide_extra = (width - M2_SCREEN_W) * 0.5f;
    geo->wide_fov = expand_3d && pipe_frame.wide.widescreen;
    m2tile_render(tiles, video_board); m2geo_run(geo, video_board);
    m2_geo_frame frame = m2geo_frame(geo);
    if (!m2gl_mesh_build(mesh, &frame, width)) {
        if (video) video(NULL, w, h, 0);
        return;
    }
    m2gl_upload(renderer, video_board, tiles, 1);
    m2_view view = {.frame_w=width, .scale=resolution, .tex_filter=texture_filter,
        .mesh_blend=mesh_blend, .saturation=saturation, .fill=1,
        .stretch=expand_3d ? pipe_frame.wide.stretch : 0};
    m2gl_draw(renderer, mesh, &view, (int)w, (int)h);
    sm2lr_input_video(w,h,previous_frame);
    sm2lr_timing_draw(w,h);
    if (video) video(RETRO_HW_FRAME_BUFFER_VALID, w, h, 0);
}
static void draw_frame(bool previous_frame)
{
    double start = timing_font_pixels ? sm2lr_timing_clock() : 0;
    draw_frame_impl(previous_frame);
    if (timing_font_pixels) frame_video_ms += sm2lr_timing_clock()-start;
}
static bool fighting(void)
{
    return board && !strncmp(board->game->name, "vf2", 3);
}
static void descriptors(void)
{
    static struct retro_input_descriptor d[40];
    static const unsigned ids[] = { RETRO_DEVICE_ID_JOYPAD_UP, RETRO_DEVICE_ID_JOYPAD_DOWN,
        RETRO_DEVICE_ID_JOYPAD_LEFT, RETRO_DEVICE_ID_JOYPAD_RIGHT, RETRO_DEVICE_ID_JOYPAD_A,
        RETRO_DEVICE_ID_JOYPAD_B, RETRO_DEVICE_ID_JOYPAD_Y, RETRO_DEVICE_ID_JOYPAD_X,
        RETRO_DEVICE_ID_JOYPAD_START, RETRO_DEVICE_ID_JOYPAD_SELECT,
        RETRO_DEVICE_ID_JOYPAD_L, RETRO_DEVICE_ID_JOYPAD_R };
    const char *labels[] = {"Up", "Down", "Left", "Right", "Button 1", "Button 2", "Button 3", "Button 4",
                           "Start", "Coin", "Shift Down", "Shift Up"};
    if (fighting()) { labels[4] = "Punch"; labels[5] = "Kick"; labels[6] = "Guard"; }
    unsigned n = 0;
    memset(d, 0, sizeof d);
    for (unsigned p = 0; p < 2; p++)
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++)
            d[n++] = (struct retro_input_descriptor){p, RETRO_DEVICE_JOYPAD, 0, ids[i], labels[i]};
    env(RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS, d);
}
static void read_input(void)
{
    static const unsigned map[M2PAD_BUTTONS] = {
        RETRO_DEVICE_ID_JOYPAD_Y, RETRO_DEVICE_ID_JOYPAD_A, RETRO_DEVICE_ID_JOYPAD_B,
        RETRO_DEVICE_ID_JOYPAD_X, RETRO_DEVICE_ID_JOYPAD_SELECT, 0, RETRO_DEVICE_ID_JOYPAD_START,
        RETRO_DEVICE_ID_JOYPAD_L3, RETRO_DEVICE_ID_JOYPAD_R3, RETRO_DEVICE_ID_JOYPAD_L,
        RETRO_DEVICE_ID_JOYPAD_R, RETRO_DEVICE_ID_JOYPAD_UP, RETRO_DEVICE_ID_JOYPAD_DOWN,
        RETRO_DEVICE_ID_JOYPAD_LEFT, RETRO_DEVICE_ID_JOYPAD_RIGHT
    };
    if (poll_input) poll_input();
    if (sm2_profile) { sm2lr_input_poll(board,input); return; }
    memset(controls.key, 0, sizeof controls.key);
    memset(controls.pad, 0, sizeof controls.pad);
    memset(controls.axis, 0, sizeof controls.axis);
    if (!input) return;
    for (unsigned p = 0; p < 2; p++) {
        if (devices[p] == RETRO_DEVICE_NONE) continue;
        for (unsigned i = 0; i < M2PAD_BUTTONS; i++)
            if (i != M2PAD_GUIDE) controls.pad[p][i] = input(p, RETRO_DEVICE_JOYPAD, 0, map[i]) != 0;
        if (!fighting()) { /* upstream generic layout until profiles are reviewed */
            controls.pad[p][M2PAD_A] = input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_A) != 0;
            controls.pad[p][M2PAD_B] = input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_B) != 0;
            controls.pad[p][M2PAD_X] = input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_X) != 0;
            controls.pad[p][M2PAD_Y] = input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_Y) != 0;
        }
        for (unsigned i = 0; i < 4; i++)
            controls.axis[p][i] = input(p, RETRO_DEVICE_ANALOG, i / 2, i % 2);
        controls.axis[p][M2PAD_LT] = input(p, RETRO_DEVICE_ANALOG, RETRO_DEVICE_INDEX_ANALOG_BUTTON, RETRO_DEVICE_ID_JOYPAD_L2);
        controls.axis[p][M2PAD_RT] = input(p, RETRO_DEVICE_ANALOG, RETRO_DEVICE_INDEX_ANALOG_BUTTON, RETRO_DEVICE_ID_JOYPAD_R2);
        if (input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_L2)) controls.axis[p][M2PAD_LT] = 32767;
        if (input(p, RETRO_DEVICE_JOYPAD, 0, RETRO_DEVICE_ID_JOYPAD_R2)) controls.axis[p][M2PAD_RT] = 32767;
    }

}

void retro_set_environment(retro_environment_t cb)
{
    env = cb;
    if (!sm2lr_register_options(env, definitions, categories)) {
        logmsg("Common option registration failed; using native legacy options");
        env(RETRO_ENVIRONMENT_SET_VARIABLES, (void *)legacy);
    }
    bool no_game = false;
    env(RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME, &no_game);
}
void retro_set_video_refresh(retro_video_refresh_t cb) { video = cb; }
void retro_set_audio_sample(retro_audio_sample_t cb) { audio = cb; }
void retro_set_audio_sample_batch(retro_audio_sample_batch_t cb) { audio_batch = cb; }
void retro_set_input_poll(retro_input_poll_t cb) { poll_input = cb; }
void retro_set_input_state(retro_input_state_t cb) { input = cb; }
void retro_init(void)
{
    struct retro_log_callback log = {0};
    if (env && env(RETRO_ENVIRONMENT_GET_LOG_INTERFACE, &log)) logger = log.log;
    sm2lr_timing_logger(logger);
    m2lr_net_init(env,logger);
}
unsigned retro_api_version(void) { return RETRO_API_VERSION; }
void retro_get_system_info(struct retro_system_info *info)
{
    *info = (struct retro_system_info){"Model2EmuEx", "0.2.0", "zip", true, true};
}
void retro_get_system_av_info(struct retro_system_av_info *info)
{
    *info = (struct retro_system_av_info){{output_width, output_height, 2656, 1536, output_aspect},
        {board && native_timing ? board->game->fps : 60.0, M2SND_RATE}};
}
void retro_set_controller_port_device(unsigned port, unsigned device)
{
    if (port < 2) devices[port] = device & RETRO_DEVICE_MASK;
    sm2lr_input_device(port,device);
}
void retro_unload_game(void)
{
    /* GL resources are released by the frontend's context_destroy callback.
     * Do not issue GL calls here: the context need not be current. */
    worker_stop();
    m2lr_net_offline();linked_cabinets=1;logged_link_state=-1;memset(&external_link,0,sizeof external_link);
    sm2lr_timing_shutdown();
    sm2lr_input_clear(); sm2_profile=false;
    if (frame_pipe) m2pipe_destroy(frame_pipe);
    frame_pipe = NULL; video_board = NULL;
    m2lr_manxtt_destroy();
    if (sound) m2snd_destroy(sound);
    if (mesh) m2gl_mesh_destroy(mesh);
    if (geo) m2geo_destroy(geo);
    if (board) m2_destroy(board);
    free(tiles);
    sound = NULL; mesh = NULL; geo = NULL; board = NULL; tiles = NULL;
    sm2lr_nvram_game(NULL, NULL);
    content_failed = nvram_pending = network_reset_pending = false; nvram_wait_frames = 0;
    clear_audio(); first_frame = false; audio_underrun = false; skips_in_row = 0;
    output_width = 496; output_height = 384; output_aspect = 4.0f/3.0f;
}
static void update_state_rom_crc(void)
{
    state_rom_crc=0;
    for(unsigned i=0;i<sizeof board->rom.ptr/sizeof board->rom.ptr[0];i++)
        if(board->rom.ptr[i] && board->rom.size[i])
            state_rom_crc=(uint32_t)crc32(state_rom_crc,board->rom.ptr[i],board->rom.size[i]);
}
void retro_deinit(void) { retro_unload_game(); m2lr_net_shutdown(); logger = NULL; sm2lr_timing_logger(NULL); }
bool retro_load_game(const struct retro_game_info *info)
{
    if (!env || !info || !info->path || board) return false;
    content_failed = false;
    char dir[4096], name[128];
    const char *base = strrchr(info->path, '/');
#ifdef _WIN32
    const char *backslash = strrchr(info->path, '\\');
    if (backslash && (!base || backslash > base))
        base = backslash;
#endif
    base = base ? base + 1 : info->path;
    size_t n = strlen(base);
    if (n < 5 || strcmp(base + n - 4, ".zip") || n - 4 >= sizeof name)
        return load_error("Content must be a supported ROM set ZIP archive");
    memcpy(name, base, n - 4); name[n - 4] = 0;
    size_t dn = (size_t)(base - info->path);
    if (dn >= sizeof dir) return load_error("Content directory path is too long");
    if (dn) { memcpy(dir, info->path, dn); dir[dn] = 0; } else strcpy(dir, ".");
    const m2_game *game = m2_find_game(name);
    if (!game) return load_error("Unknown ROM set name");
    const char *system = NULL;
    env(RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY, &system);
    const char *dirs[] = {dir, system ? system : dir, NULL};
    unsigned rom_policy = option_is("model2emuex_rom_crc_verification", "disabled")
        ? 0 : M2_ROM_CRC_METADATA | M2_ROM_CRC_CONTENTS;
    if(!strcmp(game->name,"manxtt") || !strcmp(game->name,"manxttc"))
        rom_policy|=M2_ROM_OPTIONAL_AUXILIARY_SOUND;
    rom_detail[0] = 0;
    board = m2_create_with_rom_policy(game, dirs, rom_log, rom_policy);
    if (!board) return load_error(rom_detail[0] ? rom_detail : "ROM set loading failed");
    tiles = calloc(1, sizeof *tiles); geo = m2geo_create(); mesh = m2gl_mesh_create();
    if (!tiles || !geo || !mesh) return load_error("Machine resource allocation failed");
    m2tile_init(tiles, gamma_rgb[0], gamma_rgb[1], gamma_rgb[2]);
    sound = m2snd_create(board);
    if (!sound) return load_error("Sound board initialization failed");
    if(!m2lr_manxtt_prepare(board,sound,dirs)) {
        return load_error("Manx TT audio initialization failed");
    }
    board->hooks = (m2_hooks){.tilemap_written=on_tile, .palette_written=on_pal,
        .xlat_written=on_xlat, .texture_written=on_tex, .luma_written=on_luma,
        .cg_written=on_cg, .sound_command=on_sound, .drive_raw_command=on_drive_raw};
    frame_pipe = m2pipe_create();
    if (!frame_pipe) return load_error("Frame pipeline allocation failed");
    replay_hooks = board->hooks;
    m2pipe_attach(frame_pipe, board);
    sm2lr_nvram_game(game->name, game->parent);
    sm2lr_register_options(env, definitions, categories);
#ifdef M2_ENABLE_SHARC
    if (!sm2lr_prepare_power_sled(board->rom.ptr[0],board->rom.size[0]))
        return load_error("Cannot Prepare Guarded Power Sled Program Patches");
#endif
    /* Fresh saves follow only the shared SM2 template/compatible-parent policy. */
    const sm2lr_initial_nvram_result initial_nvram=sm2lr_initial_nvram(board->back, board->eeprom.data);
    if(initial_nvram<0) {
        const char *error=initial_nvram==SM2LR_INITIAL_NVRAM_INVALID_TEMPLATE
            ? "Invalid embedded initial NVRAM template"
            : "Embedded initial NVRAM template has an unsupported layout";
        return load_error(error);
    }
    if(initial_nvram==SM2LR_INITIAL_NVRAM_LOADED)
        (void)m2_nvram_sync_settings_io(board);
    save_memory(); /* RetroArch may replace this with its .srm after load. */
    memset(&controls, 0, sizeof controls); m2input_init(&controls); sm2lr_input_reset();
    native_timing = option_is("model2emuex_av_timing", "native");
    read_options(); sm2_profile=sm2lr_input_bind(board);
    if (!sm2_profile) descriptors();
    enum retro_pixel_format format = RETRO_PIXEL_FORMAT_XRGB8888;
    if (!env(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT, &format))
        return load_error("Frontend rejected the required XRGB8888 pixel format");
    memset(&hw, 0, sizeof hw);
    hw.context_type = RETRO_HW_CONTEXT_OPENGL;
    hw.context_reset = context_reset; hw.context_destroy = context_destroy;
    hw.depth = false; hw.stencil = false; hw.bottom_left_origin = true;
    hw.version_major = 2; hw.version_minor = 1; hw.cache_context = false;
    if (!env(RETRO_ENVIRONMENT_SET_HW_RENDER, &hw)) {
        return load_error("Frontend requires desktop OpenGL support for this core");
    }
    struct retro_audio_buffer_status_callback status = {audio_buffer_status};
    env(RETRO_ENVIRONMENT_SET_AUDIO_BUFFER_STATUS_CALLBACK, &status);
    state_trace=getenv("MODEL2EMUEX_STATE_TRACE")!=NULL;state_trace_remaining=0;
    update_state_rom_crc();
    state_options_pending=false;
    first_frame = true; clear_audio(); sm2lr_timing_clear(); video_board = NULL;
    output_width = 496u * resolution; output_height = 384u * resolution;
    output_aspect = 4.0f/3.0f;
    (void)configure_network();
    sm2lr_publish_option_corrections();
    return true;
}
static bool configure_network(void)
{
    unsigned cabinets=sm2lr_linked_cabinets();
    /* SM2 keeps the board fitted for every set, including games without
       external-link controls. The native program still owns its enable bit. */
    int mode=cabinets>1?M2_NET_EXTERNAL:M2_NET_LOOPBACK;
    if(cabinets==linked_cabinets && board->net_enabled==mode)return false;
#ifdef M2_ENABLE_SHARC
    if(sm2lr_select_power_sled(board->rom.ptr[0],cabinets))update_state_rom_crc();
#endif
    linked_cabinets=cabinets;board->net_enabled=mode;
    logged_link_state=-1;
    if(cabinets>1) {
        m2lr_net_configure(board->game->name,cabinets);
        m2link_init(&external_link,cabinets,m2lr_net_transport());
    } else {
        m2lr_net_offline();
        m2link_init(&external_link,1,(m2_link_transport){0});
    }
    return true;
}
static void reset_machine(void)
{
    worker_stop();
    save_memory();
    m2_reset(board); load_memory(); m2snd_reset(sound); m2lr_manxtt_reset(); sm2lr_timing_clear();
    if(board->net_enabled) { m2link_reset(&external_link);logged_link_state=-1; }
    m2pipe_invalidate(frame_pipe); video_board = NULL; skips_in_row = 0;
    m2tile_init(tiles, gamma_rgb[0], gamma_rgb[1], gamma_rgb[2]); m2input_init(&controls); sm2lr_input_reset();
    if (renderer) {
        m2gl_xlat_written(renderer); m2gl_luma_written(renderer);
        for (int bank = 0; bank < 2; bank++)
            for (unsigned band = 0; band < 64; band++)
                m2gl_texture_written(renderer, bank, band * 16384);
    }
    clear_audio();
}
static void apply_pending_options(bool notify)
{
    int changed = 0;
    if (nvram_pending) {
        changed = sm2lr_apply_nvram(board->back,board->eeprom.data);
        if (changed < 0) return;
        nvram_pending = false;
        if (changed > 0) (void)m2_nvram_sync_settings_io(board);
    }
    if (changed > 0 || network_reset_pending) {
        network_reset_pending = false;
        reset_machine();
        if (notify) m2lr_net_notice(changed > 0 ? "NVRAM Settings Applied; Game Reset" : "Network Settings Applied; Game Reset");
    }
    sm2lr_publish_option_corrections();
}
void retro_reset(void)
{
    if (!board) return;
    if (first_frame) load_memory();
    (void)configure_network();
    nvram_pending = network_reset_pending = true; nvram_wait_frames = 0;
    apply_pending_options(!first_frame);
}
void retro_run(void)
{
    if (!board || audio_failed || content_failed) return;
    double run_start = sm2lr_timing_clock();
    frame_video_ms = 0;
    bool changed = sm2lr_options_changed() || state_options_pending;
    state_options_pending = false;
    if (changed) read_options();
    bool initial = first_frame;
    if (first_frame) { load_memory(); first_frame = false; }
    if (changed || initial) {
        network_reset_pending |= configure_network() && !initial;
        nvram_pending = true; nvram_wait_frames = 0;
    }
    apply_pending_options(!initial);
    sm2lr_publish_option_corrections();
    bool cabinet_changed=false;
    const char *cabinet_notice=m2lr_manxtt_update(!option_is("model2emuex_manxtt_cabinet_audio","disabled"),&cabinet_changed);
    if(cabinet_changed)clear_audio();
    if(cabinet_notice)m2lr_net_notice(cabinet_notice);
    read_input(); sm2lr_input_presentation(1.0 / (native_timing ? board->game->fps : 60.0));
    if (!sm2_profile) m2input_apply(&controls, board);
    /* Match upstream m2run: synthesize the pending sound slice before the
     * next board frame queues commands. Both use the native game cadence. */
    double audio_start = timing_font_pixels ? sm2lr_timing_clock() : 0;
    sample_debt += (double)M2SND_RATE / board->game->fps;
    int count = (int)sample_debt; sample_debt -= count;
    int16_t samples[4096];
    if (count > 2048) count = 2048;
    m2snd_render(sound, samples, count);
    m2lr_manxtt_mix(samples,(unsigned)count);
    if (!send_audio(samples, (size_t)count)) return;
    double audio_ms = timing_font_pixels ? sm2lr_timing_clock()-audio_start : 0;
    bool had_frame = video_board != NULL;
    bool asynchronous = pipeline_enabled && worker_start_frame();
    if (asynchronous) {
        if (had_frame) draw_frame(true);
        worker_wait();
    } else board_step();
    /* Frontend callbacks never run on the pipeline worker. */
    if(board->net_enabled) {
        if(linked_cabinets>1)m2lr_net_pump();
        m2link_frame(&external_link,board);
        if(logger && logged_link_state!=external_link.state) {
            logged_link_state=external_link.state;
            logger(RETRO_LOG_INFO,"[Model2EmuEx] Native link: state=%d id=%u count=%u\n",
                external_link.state,board->zshared[0x8002],board->zshared[0x8003]);
        }
    }
    double apply_start = timing_font_pixels ? sm2lr_timing_clock() : 0;
    video_board = m2pipe_apply(frame_pipe, &replay_hooks, &pipe_frame);
    if (timing_font_pixels) frame_video_ms += sm2lr_timing_clock()-apply_start;
    if (!asynchronous || !had_frame) draw_frame(false);
    sm2lr_input_feedback(input);
    save_memory();
    // SM2 retries both before and after execution, timing out once per frame.
    if (nvram_pending) {
        apply_pending_options(true);
        if (nvram_pending && ++nvram_wait_frames == 600) {
            nvram_pending = false;
            m2lr_net_message("NVRAM layout did not become ready; core options were not applied");
        }
    }
    if(state_trace_remaining) { state_trace_event("Run");state_trace_remaining--; }
    if (timing_font_pixels) sm2lr_timing_sample(machine_frame_ms,frame_video_ms,audio_ms,
        sm2lr_timing_clock()-run_start,run_start);

}
unsigned retro_get_region(void) { return RETRO_REGION_NTSC; }
void *retro_get_memory_data(unsigned id)
{
    if (!board) return NULL;
    return id == RETRO_MEMORY_SAVE_RAM ? nvram : id == RETRO_MEMORY_SYSTEM_RAM ? board->ram : NULL;
}
size_t retro_get_memory_size(unsigned id)
{
    if (!board) return 0;
    return id == RETRO_MEMORY_SAVE_RAM ? sizeof nvram : id == RETRO_MEMORY_SYSTEM_RAM ? 0x100000 : 0;
}
/* Fixed before content load, like SM2. Version 1 is a separate destination
 * format, not a reader for SM2/standalone snapshots. */
/* SHARC adds up to 0x40000/6 decoded records of 108 bytes plus their
 * original upload. Keep the established Model 2/2A capacity unchanged. */
static size_t state_capacity(void) {
#ifdef M2_ENABLE_SHARC
    if(board && board->sharc)return 16u*1024u*1024u;
#endif
    return 12u*1024u*1024u;
}
#define STATE_CAPACITY state_capacity()
#if defined(__aarch64__) || defined(__arm64__)
#define STATE_ARCH 1u
#elif defined(__x86_64__)
#define STATE_ARCH 2u
#else
#define STATE_ARCH 0u
#endif
#define STATE_ABI (0x01020000u | (STATE_ARCH<<8) | (uint32_t)sizeof(void *))
/* A header-only extension preserves the payload and 12 MiB capacity. Old
 * readers reject the feature bit rather than silently losing local state. */
#define STATE_LOCAL_LINK_ABI 0x80000000u
#define STATE_CABINET_AUDIO_ABI 0x40000000u
#define STATE_SHARC_ABI 0x20000000u
typedef struct {
    char magic[8];
    uint32_t version, used, crc, abi, type, timing;
    char game[32], hardware[32];
    uint32_t rom_crc, frame_low, frame_high;
    uint8_t reserved[20];
} state_header;
_Static_assert(sizeof(state_header)==128, "State header size");
static uint32_t state_checksum(const uint8_t *data)
{
    uint32_t crc=(uint32_t)crc32(0,data,offsetof(state_header,crc));
    return (uint32_t)crc32(crc,data+offsetof(state_header,abi),STATE_CAPACITY-offsetof(state_header,abi));
}
static void state_payload(m2_state *a,bool cabinet_audio)
{
    m2_state_archive(board,a); m2snd_state_archive(sound,a); m2geo_state_archive(geo,a);
    sm2lr_input_state_archive(a);
    M2_FIELD(a,&controls,key); M2_FIELD(a,&controls,pad); M2_FIELD(a,&controls,axis);
    M2_FIELD(a,&controls,steer); M2_FIELD(a,&controls,gear); M2_FIELD(a,&controls,gear_up_held);
    M2_FIELD(a,&controls,gear_down_held); M2_FIELD(a,&controls,shift_keys_prev);
    M2_FIELD(a,&controls,steer_u); M2_FIELD(a,&controls,accel_u); M2_FIELD(a,&controls,brake_u);
    m2_state_bytes(a,nvram,sizeof nvram);
    double debt=sample_debt;unsigned remainder=output_sample_remainder;
    uint8_t initial=first_frame?1:0, have_frame=video_board?1:0;
    m2_state_value(a,&debt,sizeof debt); m2_state_value(a,&remainder,sizeof remainder);
    m2_state_value(a,&initial,sizeof initial);m2_state_value(a,&have_frame,sizeof have_frame);
    if(!isfinite(debt) || debt<0 || debt>=1 || remainder>=60 || initial>1 || have_frame>1)a->failed=1;
    if(a->mode==M2_STATE_LOAD && !a->failed) {
        sample_debt=debt;output_sample_remainder=remainder;first_frame=initial!=0;state_had_frame=have_frame!=0;
    }
    if(cabinet_audio)m2lr_manxtt_state_archive(a);
}
size_t retro_serialize_size(void) {
    return STATE_CAPACITY;
}
bool retro_serialize(void *data, size_t size)
{
    if(linked_cabinets>1) { m2lr_net_message("Save states are unavailable during a Linked Cabinets session");return false; }
    if(!board || !sound || !data || size<STATE_CAPACITY || board->cpu_execute
        || (board->net_enabled && board->net_enabled!=M2_NET_LOOPBACK))return false;
    worker_stop();
    memset(data,0,STATE_CAPACITY);
    state_header h={0};memcpy(h.magic,"M2EXSTAT",8);h.version=1;h.abi=STATE_ABI;
#ifdef M2_ENABLE_SHARC
    if(board->sharc)h.abi|=STATE_SHARC_ABI;
#endif
    h.type=(uint32_t)board->type;h.timing=native_timing?1:0;h.rom_crc=state_rom_crc;
    h.frame_low=(uint32_t)board->frame;h.frame_high=(uint32_t)(board->frame>>32);
    snprintf(h.game,sizeof h.game,"%s",board->game->name);
    snprintf(h.hardware,sizeof h.hardware,"%s",board->game->board);
    if(board->net_enabled==M2_NET_LOOPBACK) {
        h.abi|=STATE_LOCAL_LINK_ABI;memcpy(h.reserved,"LNK1",4);
        h.reserved[4]=(uint8_t)external_link.state;h.reserved[5]=(uint8_t)external_link.master;
    }
    bool cabinet_audio=m2lr_manxtt_present();
    if(cabinet_audio) { h.abi|=STATE_CABINET_AUDIO_ABI;m2lr_manxtt_state_header(h.reserved); }
    m2_state a={(uint8_t *)data,STATE_CAPACITY,sizeof h,M2_STATE_SAVE,0};
    state_payload(&a,cabinet_audio); if(a.failed)return false;
    h.used=(uint32_t)a.pos;memcpy(data,&h,sizeof h);
    h.crc=state_checksum(data);memcpy(data,&h,sizeof h);
    state_trace_event("Save");if(state_trace)state_trace_remaining=16;return true;
}
bool retro_unserialize(const void *data, size_t size)
{
    if(linked_cabinets>1) { m2lr_net_message("Save states are unavailable during a Linked Cabinets session");return false; }
    if(!board || !sound || !data || size<STATE_CAPACITY || board->cpu_execute
        || (board->net_enabled && board->net_enabled!=M2_NET_LOOPBACK))return false;
    state_header h;memcpy(&h,data,sizeof h);
    bool sharc_state=(h.abi&STATE_SHARC_ABI)!=0,sharc_machine=false;
#ifdef M2_ENABLE_SHARC
    sharc_machine=board->sharc!=NULL;
#endif
    if(sharc_state!=sharc_machine) {
        m2lr_net_error("Save State rejected: incompatible SHARC machine payload");return false;
    }
    bool cabinet_audio=(h.abi&STATE_CABINET_AUDIO_ABI)!=0;
    uint32_t base_abi=h.abi&~(STATE_CABINET_AUDIO_ABI|STATE_SHARC_ABI);
    bool local_state=base_abi==(STATE_ABI|STATE_LOCAL_LINK_ABI);
    const uint8_t zero[20]={0};
    bool valid_local=local_state && board->net_enabled==M2_NET_LOOPBACK
        && !memcmp(h.reserved,"LNK1",4) && (h.reserved[4]==0 || h.reserved[4]==1 || h.reserved[4]==3)
        && h.reserved[5]<=1 && (cabinet_audio?m2lr_manxtt_state_compatible(h.reserved):!memcmp(h.reserved+6,zero,14));
    if(memcmp(h.magic,"M2EXSTAT",8) || h.version!=1
        || (local_state?!valid_local:(base_abi!=STATE_ABI || memcmp(h.reserved,zero,cabinet_audio?6:20) || (cabinet_audio && !m2lr_manxtt_state_compatible(h.reserved)))) || h.type!=(uint32_t)board->type
        || h.timing>1 || h.rom_crc!=state_rom_crc
        || !memchr(h.game,0,sizeof h.game) || strcmp(h.game,board->game->name)
        || !memchr(h.hardware,0,sizeof h.hardware) || strcmp(h.hardware,board->game->board)
        || h.used<sizeof h || h.used>STATE_CAPACITY || h.crc!=state_checksum(data)) {
        m2lr_net_error("Save State rejected: incompatible identity, timing, version or damaged data");return false;
    }
    worker_stop();
    m2_state a={(uint8_t *)data,h.used,sizeof h,M2_STATE_CHECK,0};
    state_payload(&a,cabinet_audio);
    if(a.failed || a.pos!=h.used) { m2lr_net_error("Save State rejected: invalid machine payload");return false; }
    uint8_t *backup=malloc(STATE_CAPACITY);
    if(!backup || !retro_serialize(backup,STATE_CAPACITY)) {
        free(backup);m2lr_net_error("Save State load failed: could not preserve the current machine snapshot");return false;
    }
    m2lr_manxtt_state_bind(cabinet_audio?h.reserved:NULL);
    a=(m2_state){(uint8_t *)data,h.used,sizeof h,M2_STATE_LOAD,0};state_payload(&a,cabinet_audio);
    if(board->frame!=((uint64_t)h.frame_high<<32 | h.frame_low))a.failed=1;
    if(a.failed) {
        state_header previous;memcpy(&previous,backup,sizeof previous);
        bool previous_audio=(previous.abi&STATE_CABINET_AUDIO_ABI)!=0;
        m2lr_manxtt_state_bind(previous_audio?previous.reserved:NULL);
        a=(m2_state){backup,previous.used,sizeof previous,M2_STATE_LOAD,0};state_payload(&a,previous_audio);
        free(backup);m2lr_net_error("Save State load failed; restored previous machine snapshot");return false;
    }
    free(backup);
    if(board->net_enabled==M2_NET_LOOPBACK) {
        m2link_init(&external_link,1,(m2_link_transport){0});
        if(local_state) { external_link.state=h.reserved[4];external_link.master=h.reserved[5]; }
        /* Older zero-reserved headers load with a fresh local protocol. */
        logged_link_state=-1;
    }
    if(h.timing!=(native_timing?1u:0u))output_sample_remainder=0;
    /* Invalidate presentation without making GL calls: the frontend context
     * need not be current in a Save State callback. Rebuild on next retro_run. */
    m2pipe_invalidate(frame_pipe);video_board=NULL;
    if(state_had_frame) {
        m2pipe_capture(frame_pipe,board);video_board=m2pipe_apply(frame_pipe,&replay_hooks,&pipe_frame);
    }
    m2tile_init(tiles,gamma_rgb[0],gamma_rgb[1],gamma_rgb[2]);
    if(renderer) {
        m2gl_invalidate(renderer);
        m2gl_xlat_written(renderer);m2gl_luma_written(renderer);
        for(int bank=0;bank<2;bank++)for(unsigned band=0;band<64;band++)m2gl_texture_written(renderer,bank,band*16384);
    }
    /* Discard stale frontend samples, keeping native scheduling remainders. */
    audio_pending=0;audio_failed=false;audio_underrun=false;skips_in_row=0;
    sm2lr_input_after_state_load();sm2lr_timing_clear();
    state_trace_event("Load");if(state_trace)state_trace_remaining=16;
    state_options_pending=true; /* Current enabled operator overrides win on Resume, with one reset if changed. */
    return true;
}
void retro_cheat_reset(void) {}
void retro_cheat_set(unsigned i, bool enabled, const char *code) { (void)i; (void)enabled; (void)code; }
bool retro_load_game_special(unsigned type, const struct retro_game_info *info, size_t n)
{ (void)type; (void)info; (void)n; return false; }
