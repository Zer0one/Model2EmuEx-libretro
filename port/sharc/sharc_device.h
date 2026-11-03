#ifndef M2_SHARC_DEVICE_H
#define M2_SHARC_DEVICE_H
#include "sharc_runtime.h"
#include "sharc_reset.h"
#include "sharc_board.h"
#include "sharc_board_init.h"
#include "sharc_host.h"
/* Frontend-neutral composition. Caller owns board buffers/FIFOs, decoded
 * allocation policy, native serializer list and application diagnostics.
 * This object does not create an i960 machine or enable a catalog entry. */
typedef struct {
    m2_sharc_reset_context core;
    m2_sharc_board_configuration configuration;
    m2_sharc_fp_state fp;
    m2_sharc_board_bus board;
    m2_sharc_host host;
    m2_sharc_runtime runtime;
    m2_sharc_memory_bus bus;
    m2_sharc_program_memory memory;
    uint32_t event_queue[8],fixed_state,source_token;
    void *opaque;
    m2_sharc_diagnostic_hook diagnostic;
    void (*failure)(void *opaque,uint32_t entry,uint32_t record);
    void (*render)(void *opaque);
    const m2_sharc_registration *registration;
} m2_sharc_device;
/* Before binding, populate board.ram0/ram1/shared/rom/input_fifo/output_fifo,
 * host.data (separate native upload buffer), callbacks and memory policy.
 * Initial selected-state token follows the native caller contract. Buffer
 * initialization and FIFO reset belong to the enclosing native board. */
void m2_sharc_device_bind(m2_sharc_device *device,uint32_t fixed_state,uint32_t source_token);
void m2_sharc_device_power_on(m2_sharc_device *device,const char *native_game,
    const m2_sharc_registration *registration);
void m2_sharc_device_upload_complete(m2_sharc_device *device);
void m2_sharc_device_run_bounded(m2_sharc_device *device,uint32_t budget);
void m2_sharc_device_run_continuous(m2_sharc_device *device);
bool m2_sharc_device_host_access(m2_sharc_device *device,uint32_t entry,
    uint32_t address,uint32_t value,uint32_t *result);
#endif
