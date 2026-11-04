#include "tgpx4_motion.h"

/* 004c9f19..004ca16d, reached after analog input conversion. Preserve the
 * native command-driven countdown: an absent command does not consume time.
 * FF resets phase but leaves countdown intact. Unlike the SM2 stationary
 * acknowledgement stub, CE/FF/echo depend on the original transition history. */
void m2_tgpx4_motion_step(m2_tgpx4_motion *s)
{
    if (s->command == UINT32_MAX) return;
    uint32_t command = s->command & 255u;
    if (command == 255) s->phase = 0;
    else if (command == 0 && s->phase == 0) {
        s->phase = 1;
        s->countdown = 10;
        goto decrement;
    }
    if (s->countdown != 0) goto decrement;
    if (s->phase == 1) {
        s->phase = 2;
        s->countdown = 10;
decrement:
        --s->countdown;
    } else if (s->phase == 2) s->phase = 3;
    if (s->phase == 1) s->reply = 0xce;
    else if (s->phase == 2) s->reply = 0xff;
    else if (s->phase == 3) s->reply = (uint8_t)command;
    s->command = UINT32_MAX;
}
