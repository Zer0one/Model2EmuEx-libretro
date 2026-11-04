#ifndef M2_TGPX4_HOST_H
#define M2_TGPX4_HOST_H

#include <stdbool.h>
#include <stdint.h>
#include "../tgp/tgp.h"

typedef struct {
    uint8_t *program;
    tgp_fifo *input, *output;
    uint32_t upload_control, upload_offset, stopped;
    void *opaque;
    void (*run)(void *opaque);
    uint8_t *shared, *data;
    const uint8_t *external;
    uint32_t data_control, data_offset, shared_write, shared_read, reg_803008;
    void (*decode_uploaded_program)(void *opaque, uint32_t bytes);
} m2_tgpx4_host;

/* Direct host access handlers. Memory and FIFO indices follow native caller
 * bounds. A read result contains only the bits visible to the i960. */
bool m2_tgpx4_host_access(m2_tgpx4_host *host, uint32_t entry, uint32_t address,
                         uint32_t value, uint32_t *result);

#endif
