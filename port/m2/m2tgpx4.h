#ifndef M2_TGPX4_BINDING_H
#define M2_TGPX4_BINDING_H
#include <stdint.h>
#include <stddef.h>
#include "../state.h"
struct m2_board;
struct m2_tgpx4_binding;
struct m2_tgpx4_binding *m2tgpx4_create(struct m2_board *board);
void m2tgpx4_destroy(struct m2_tgpx4_binding *binding);
void m2tgpx4_reset(struct m2_board *board);
void m2tgpx4_input_step(struct m2_board *board);
uint32_t m2tgpx4_center_mode(const struct m2_board *board);
int m2tgpx4_dual_matrix(const struct m2_board *board);
uint32_t m2tgpx4_access(struct m2_board *board, uint32_t entry, uint32_t address, uint32_t value);
uint32_t m2tgpx4_protection_access(struct m2_board *board, uint32_t address, uint32_t value, unsigned bits, int writing);
void m2tgpx4_upload_write(struct m2_board *board, uint32_t address, uint32_t value);
void m2tgpx4_debug(const struct m2_tgpx4_binding *binding, char *text, size_t size);
void m2tgpx4_state_archive(struct m2_tgpx4_binding *binding, m2_state *archive);
#endif
