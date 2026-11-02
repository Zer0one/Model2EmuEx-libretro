#pragma once
#include "libretro.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
bool sm2lr_register_options(retro_environment_t environment,
    const struct retro_core_option_v2_definition *native_options,
    const struct retro_core_option_v2_category *categories);
bool sm2lr_options_changed(void);
void sm2lr_publish_option_corrections(void);
void sm2lr_nvram_game(const char *game, const char *parent);
typedef enum {
    SM2LR_INITIAL_NVRAM_UNCHANGED = 0,
    SM2LR_INITIAL_NVRAM_LOADED = 1,
    SM2LR_INITIAL_NVRAM_INVALID_TEMPLATE = -1,
    SM2LR_INITIAL_NVRAM_INVALID_LAYOUT = -2
} sm2lr_initial_nvram_result;
sm2lr_initial_nvram_result sm2lr_initial_nvram(uint8_t *backup, uint8_t *eeprom);
/* 1 changed; 0 unchanged/disabled/unsupported; -1 layout not ready. */
int sm2lr_apply_nvram(uint8_t *backup, uint8_t *eeprom);
size_t sm2lr_nvram_option_count(void);
unsigned sm2lr_linked_cabinets(void);
#ifdef __cplusplus
}
#endif
