#ifndef M2_SHARC_BINDING_H
#define M2_SHARC_BINDING_H
#include <stdint.h>
#include <stddef.h>
#include "../state.h"
struct m2_board;
typedef struct m2_sharc_binding m2_sharc_binding;
/* Opt-in native-machine reconstruction build (M2_ENABLE_SHARC). No frontend
 * option or published compatibility claim is attached to this build switch. */
struct m2_sharc_binding *m2sharc_create(struct m2_board *board);
void m2sharc_destroy(struct m2_sharc_binding *binding);
void m2sharc_reset(struct m2_board *board);
uint32_t m2sharc_access(struct m2_board *board,uint32_t entry,uint32_t address,uint32_t value);
void m2sharc_upload_write(struct m2_board *board,uint32_t address,uint32_t value);
/* Read-only diagnostics for the isolated research runner. */
void m2sharc_debug(const struct m2_sharc_binding *binding,char *text,size_t size);
/* Host-pointer-free fingerprint for little-endian research comparisons.
 * Excludes unused allocator words in predecoded records and ROM contents. */
uint64_t m2sharc_hash(const struct m2_sharc_binding *binding);
void m2sharc_state_archive(struct m2_sharc_binding *binding,m2_state *archive);
#endif
