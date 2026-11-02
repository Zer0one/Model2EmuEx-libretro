#pragma once
#include "libretro.h"
#ifdef __cplusplus
#include "sm2/timing_overlay.h"
const sm2::libretro::TimingOverlayData& sm2lr_timing_data();
extern "C" {
#endif
void sm2lr_timing_config(unsigned font_pixels,bool native_timing,double fps);
void sm2lr_timing_clear(void);
void sm2lr_timing_shutdown(void); /* CPU only; no context required. */
void sm2lr_timing_gl_proc(retro_hw_get_proc_address_t);
void sm2lr_timing_gl_destroy(void); /* Context current. */
void sm2lr_timing_gl_abandon(void); /* Lost context; CPU only. */
void sm2lr_timing_draw(unsigned width,unsigned height);
void sm2lr_timing_logger(retro_log_printf_t);
double sm2lr_timing_clock(void);
void sm2lr_timing_sample(double machine_ms,double video_ms,double audio_ms,double run_ms,double callback_start_ms);
#ifdef __cplusplus
}
#endif
