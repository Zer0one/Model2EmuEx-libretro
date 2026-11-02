#pragma once
#include "libretro.h"
#include "m2/m2link.h"
#ifdef __cplusplus
extern "C" {
#endif
void m2lr_net_init(retro_environment_t env, retro_log_printf_t log);
void m2lr_net_shutdown(void);
void m2lr_net_configure(const char *game, unsigned cabinets);
void m2lr_net_offline(void);
void m2lr_net_pump(void);
m2_link_transport m2lr_net_transport(void);
void m2lr_net_message(const char *text);
void m2lr_net_error(const char *text);
void m2lr_net_notice(const char *text);
#ifdef __cplusplus
}
#endif
