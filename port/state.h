/* Frontend-neutral bounded state archive. Fields contain values, never host pointers.
 * Native scalar representation is intentional; the container guards ABI/endian/version. */
#ifndef M2_STATE_H
#define M2_STATE_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { M2_STATE_SAVE, M2_STATE_CHECK, M2_STATE_LOAD };
typedef struct { uint8_t *data; size_t size, pos; int mode, failed; } m2_state;
static inline void m2_state_bytes(m2_state *a, void *value, size_t size) {
    if (a->failed || a->pos > a->size || size > a->size-a->pos) { a->failed=1; return; }
    if (a->mode==M2_STATE_SAVE) memcpy(a->data+a->pos,value,size);
    else if (a->mode==M2_STATE_LOAD) memcpy(value,a->data+a->pos,size);
    a->pos+=size;
}
/* Read a scalar into a local even during validation, without mutating the machine. */
static inline void m2_state_value(m2_state *a, void *value, size_t size) {
    if(a->mode!=M2_STATE_CHECK) { m2_state_bytes(a,value,size); return; }
    int mode=a->mode; a->mode=M2_STATE_LOAD; m2_state_bytes(a,value,size); a->mode=mode;
}
#define M2_FIELD(a, obj, member) m2_state_bytes(a, &(obj)->member, sizeof (obj)->member)
#ifdef __cplusplus
}
#endif
#endif
