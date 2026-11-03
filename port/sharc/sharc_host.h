#ifndef M2_SHARC_HOST_H
#define M2_SHARC_HOST_H
#include <stdbool.h>
#include <stdint.h>
/* Model 2B i960-facing coprocessor driver. Buffers, FIFO indices and upload
 * offsets obey native caller bounds; no ROM or machine allocation occurs here.
 * Scalar fields correspond to the original globals, pointers to shared storage.
 * Callbacks are explicit native continuous-SHARC/shared-renderer boundaries. */
typedef struct {
    uint8_t *program,*data,*shared;
    uint32_t *input,*output,*astat,*stop,*selected;
    uint32_t fixed,program_control,program_offset,data_control,data_offset;
    uint32_t shared_write,reg_801008,reg_803008;
    void *opaque;
    void (*run)(void *opaque);
    void (*render)(void *opaque);
} m2_sharc_host;
/* Original entry address selects access width/operation. Read results are
 * normalized to the i960 access width, not undefined upper x86 return bits.
 * Writes/no-op callbacks leave result intact. Unknown entries return false. */
bool m2_sharc_host_access(uint32_t entry,m2_sharc_host *host,uint32_t address,
    uint32_t value,uint32_t *result);
#endif
