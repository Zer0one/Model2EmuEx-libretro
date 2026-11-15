#ifndef M2LR_TEXTURE_MATERIALS_H
#define M2LR_TEXTURE_MATERIALS_H
#include <stdint.h>
struct m2_board;
#ifdef __cplusplus
extern "C" {
#endif
void m2lr_material_load(const char *system, const char *game, int replacements, void (*message)(const char *));
void m2lr_material_unload(void);
void m2lr_material_context(int destroy);
void m2lr_material_dirty(int bank);
int m2lr_material_frame(const struct m2_board *board, int automip, int gouraud, int filter, int scale, int mesh_blend);
int m2lr_material_bind(void *unused, const uint16_t th[4]);
#ifdef __cplusplus
}
#endif
#endif
