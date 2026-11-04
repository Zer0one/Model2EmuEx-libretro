#include "tgpx4_geometry.h"
#include <string.h>

bool m2_tgpx4_geometry_command(m2_tgpx4_geometry_control *s,
    uint32_t entry, const uint32_t *input)
{
    switch (entry) {
    case 0x4bc040: /* Tail-call 004bb280 follows in the original. */
        s->special_object = 1;
        return true;
    case 0x4ba010:
        for (unsigned row = 0; row < 4; ++row) {
            memcpy(s->alternate + row * 4, input + row * 3, 3 * sizeof(uint32_t));
            s->alternate[row * 4 + 3] = row == 3 ? 0x3f800000u : 0;
        }
        s->list_position += 48;
        return true;
    case 0x4b94a0:
        memcpy(s->alternate, s->primary, sizeof s->alternate);
        return true;
    case 0x4b9460: /* Prepass object: four arguments. */
        s->list_position += 16;
        return true;
    case 0x4b93e0: /* Prepass alternate matrix: twelve arguments. */
        s->list_position += 48;
        return true;
    case 0x4b9900: /* Prepass matrix restore: no arguments. */
        return true;
    default:
        return false;
    }
}

uint32_t m2_tgpx4_geometry_center(uint32_t command, uint32_t native_mode)
{
    /* 004bb30c..004bb326. ECX is the full list word: the dispatch shifts
     * a separate EAX copy. Model 2C initialization selects mode 3. */
    return (command >> (native_mode == 3 ? 6 : 29)) & 3;
}
