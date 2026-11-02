#pragma once
#include "libretro.h"
#include <stdbool.h>
#include <stdint.h>
struct m2_board;
#ifdef __cplusplus
#include <vector>
void sm2lr_add_input_options(std::vector<retro_core_option_v2_definition>& definitions);
extern "C" {
#endif
void sm2lr_input_environment(retro_environment_t environment);
bool sm2lr_input_bind(struct m2_board *board);
void sm2lr_input_reset(void);
void sm2lr_input_clear(void);
void sm2lr_input_stop_rumble(void);
void sm2lr_input_device(unsigned port, unsigned device);
bool sm2lr_input_refresh(void);
void sm2lr_input_poll(struct m2_board *board, retro_input_state_t input);
const char *sm2lr_input_profile(void);
/* Called on the emulation worker; feedback drains only after that frame joins. */
void sm2lr_input_drive_write(uint8_t value);
void sm2lr_input_feedback(retro_input_state_t input);
void sm2lr_input_presentation(double seconds);
void sm2lr_input_video(unsigned width,unsigned height,bool previous_frame);
#ifdef __cplusplus
}
#endif
/* Pointer-free SM2 continuation values, independent of active frontend options. */
#include "state.h"
#ifdef __cplusplus
extern "C" {
#endif
void sm2lr_input_state_archive(m2_state *archive);
void sm2lr_input_after_state_load(void);
#ifdef __cplusplus
}
#endif
