/* SM2 Manx TT cabinet policy over frontend-neutral destination sound hardware. */
#pragma once
#include "m2/m2board.h"
#include "snd/m2snd.h"
#ifdef __cplusplus
extern "C" {
#endif
bool m2lr_manxtt_prepare(m2_board *,m2_snd *,const char *const *dirs);
void m2lr_manxtt_destroy(void);
void m2lr_manxtt_command(uint8_t);
/* Return a source-equivalent notice, or NULL. Changes clear frontend audio. */
const char *m2lr_manxtt_update(bool enabled,bool *changed);
void m2lr_manxtt_reset(void);
void m2lr_manxtt_gains(unsigned,unsigned,unsigned);
void m2lr_manxtt_mix(int16_t *,unsigned);
bool m2lr_manxtt_present(void);
void m2lr_manxtt_state_header(uint8_t reserved[20]);
bool m2lr_manxtt_state_compatible(const uint8_t reserved[20]);
void m2lr_manxtt_state_bind(const uint8_t *reserved);
void m2lr_manxtt_state_archive(m2_state *);
#ifdef __cplusplus
}
#endif
