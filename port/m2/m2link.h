/* External transport seam for the native Model 2 communication-board ring.
 * No socket, frontend or threading ownership belongs to the machine. */
#ifndef M2LINK_H
#define M2LINK_H
#include "m2board.h"
#ifdef __cplusplus
extern "C" {
#endif
#define M2LINK_PACKET_MAX (0xe00 + 1)
typedef struct {
    void *user;
    int (*ready)(void *user);
    void (*send)(void *user, const uint8_t *data, size_t size);
    size_t (*receive)(void *user, uint8_t *data, size_t capacity);
    void (*clear)(void *user);
} m2_link_transport;
typedef struct {
    int state, master;
    unsigned cabinets, retry;
    m2_link_transport transport;
} m2_link;
void m2link_init(m2_link *link, unsigned cabinets, m2_link_transport transport);
void m2link_reset(m2_link *link);
/* Call on the frontend thread between completed machine frames. */
void m2link_frame(m2_link *link, m2_board *board);
#ifdef __cplusplus
}
#endif
#endif
