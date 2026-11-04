#ifndef M2_TGPX4_MOTION_H
#define M2_TGPX4_MOTION_H
#include <stdint.h>
typedef struct {
    uint32_t command, phase, countdown;
    uint8_t reply;
} m2_tgpx4_motion;
/* Handshake fragment of original Ski Super G input routine 004c9dc0.
 * The board binding calls this after frontend input conversion each frame. */
void m2_tgpx4_motion_step(m2_tgpx4_motion *state);
#endif
