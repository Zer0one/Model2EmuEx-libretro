#ifndef M2_SHARC_UPLOAD_H
#define M2_SHARC_UPLOAD_H
#include "sharc_host.h"
/* Shared original i960 upload controller, 004c79c0. Completion callbacks are
 * native driver entries 15 and 16. Neither callback may retain these pointers. */
void m2_sharc_upload_control(m2_sharc_host *host,uint32_t *reg_98000c,
    uint32_t address,uint32_t value,void *opaque,
    void (*program_complete)(void *),void (*data_complete)(void *));
#endif
