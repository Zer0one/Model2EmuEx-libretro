#ifndef M2_SHARC_RESET_H
#define M2_SHARC_RESET_H
#include "sharc_execute.h"
#include "sharc_program.h"
typedef struct {
    uint32_t flag,state,bytes,restore,save;
    const char *name;
} m2_sharc_state_descriptor;
typedef struct {
    void *opaque;
    uint32_t list;
    uint32_t (*read)(void *opaque,uint32_t address);
    void (*write)(void *opaque,uint32_t address,uint32_t value);
    uint32_t (*create)(void *opaque,uint32_t head,uint32_t next,
                       const m2_sharc_state_descriptor *descriptor);
    /* Native exception boundary: this callback MUST NOT return. */
    void (*fatal)(void *opaque,const char *message);
} m2_sharc_registration;
typedef struct {
    m2_sharc_execution execution;
    m2_sharc_program program;
    uint32_t source_binding,source_next,selected_state;
} m2_sharc_reset_context;
/* 004c0230: optional native serializer registration precedes machine reset.
 * Source is captured before callbacks; selected-state binding is read at decode.
 * Registration list and allocation invariants are the native caller contract. */
void m2_sharc_reset(m2_sharc_reset_context *context,const uint8_t *source,
    uint32_t source_token,uint32_t bytes,uint32_t fixed_state,
    const m2_sharc_program_memory *memory,const m2_sharc_registration *registration);
/* 004c6470 upload completion: same native reset/decode, uploaded byte count,
 * without serializer registration. This is not the board power-on 0x100 size. */
void m2_sharc_upload_complete(m2_sharc_reset_context *context,const uint8_t *source,
    uint32_t source_token,uint32_t bytes,uint32_t fixed_state,
    const m2_sharc_program_memory *memory);
#endif
