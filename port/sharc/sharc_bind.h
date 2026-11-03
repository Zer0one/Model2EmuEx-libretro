#ifndef M2_SHARC_BIND_H
#define M2_SHARC_BIND_H
#include "sharc_compute.h"
#include "sharc_memory.h"
#include "sharc_control.h"
/* Bind the original 27-word decoded record, retaining 32-bit guest tokens.
 * Resolver is a side-effect-free address lookup. Unused fields can contain
 * arbitrary allocator data and may resolve to NULL; only pointers actually
 * consumed by the selected native path must be valid. No speculative guest
 * loads are performed. Memory records retain their stable-binding contract;
 * control records must be rebound whenever the control resolver is called,
 * including after delay slots. Unsupported handlers/conditions leave out intact.
 * Operation contains the original entry address, for the complete backend.
 */
bool m2_sharc_bind_memory(const uint32_t record[27],m2_sharc_word_resolver word,
    void *opaque,m2_sharc_memory_record *out);
bool m2_sharc_bind_control(const uint32_t record[27],m2_sharc_word_resolver word,
    void *opaque,m2_sharc_control_record *out);
#endif
