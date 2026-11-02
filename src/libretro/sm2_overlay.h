#pragma once
#include "libretro.h"
#ifdef __cplusplus
#include "sm2/crosshair.h"
void sm2lr_overlay_draw(const sm2::libretro::CrosshairGeometry&,unsigned,unsigned);
extern "C" {
#endif
bool sm2lr_overlay_reset(retro_hw_get_proc_address_t);
void sm2lr_overlay_destroy(void);
void sm2lr_overlay_abandon(void);
#ifdef __cplusplus
}
#endif
