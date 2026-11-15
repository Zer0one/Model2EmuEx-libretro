#pragma once
#include "libretro.h"
#include "m2/m2wide.h"
struct m2_board;
#ifdef __cplusplus
extern "C" {
#endif
void m2lr_lua_open(struct m2_board *, const char *system, const char *game, void (*message)(const char *));
void m2lr_lua_close(void);
void m2lr_lua_reload(void);
int m2lr_lua_active(void);
const struct retro_core_option_v2_definition *m2lr_lua_options(void);
void m2lr_lua_sync(retro_environment_t env);
void m2lr_lua_event(const char *event);
void m2lr_lua_input(retro_input_state_t input);
void m2lr_lua_size(unsigned width,unsigned height);
void m2lr_lua_wide(m2_wide_state *state);
void m2lr_lua_draw(unsigned width,unsigned height);
void m2lr_lua_discard_draw(void);
void m2lr_lua_context(int destroy);
#ifdef __cplusplus
}
#endif
