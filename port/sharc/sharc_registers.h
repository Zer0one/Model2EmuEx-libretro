#ifndef M2_SHARC_REGISTERS_H
#define M2_SHARC_REGISTERS_H

#include <stdint.h>

/* Recovered register-location helper, original 0x004bcb80.
 * These are logical 32-bit word views of the original 0x2a4-byte state and
 * 0x6c-byte decoded record, not serialized host-pointer structures. Returned
 * locations belong to one of those views. Group 4 sets record flag 0x80;
 * unsupported encodings return the original scratch slot at record + 0x30.
 * State and record must be distinct, writable, suitably aligned arrays.
 */
uint32_t *m2_sharc_register_location(uint32_t state[169], uint32_t record[27],
                                     uint8_t code);
/* Same location selection in the decoder's explicit virtual address space. */
uint32_t m2_sharc_register_token(uint32_t state_base,uint32_t record_base,
    uint32_t record[27],uint8_t code);

#endif
