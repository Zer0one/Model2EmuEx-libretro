/* Recovered ElSemi SHARC decoder helpers; independent of any frontend. */
#ifndef M2_SHARC_BITS_H
#define M2_SHARC_BITS_H

#include <stdint.h>

/* Original EMULATOR.EXE 1.1a: 0x004bcd10, input EAX/DL, result EAX.
 * Preserve its x86 shift-count behavior, including encoded widths 0 and 32.
 * This is a decoder helper, not a general-purpose mathematical sign extension.
 */
uint32_t m2_sharc_extend_immediate(uint32_t value, uint8_t encoded_width);

/* Original controls: position in bits 0..5, width in bits 6..11. The x86
 * shifts mask both to five bits. Only status bit 0x1000 is changed, based on
 * the extracted/masked field before shifting or combining it with a base.
 * The three deposit entry points have identical machine code.
 */
uint32_t m2_sharc_field_deposit(uint32_t value, uint32_t control, uint32_t *status);
uint32_t m2_sharc_field_extract(uint32_t value, uint32_t control, uint32_t *status);

/* 0x004bc4c0 / 0x004bc560: caller resolves direct/indirect source before the
 * call. Read *base AFTER updating *status: base is permitted to alias status.
 * This is an OR merge; the original does not first clear a destination field.
 */
uint32_t m2_sharc_field_merge(uint32_t value, const uint32_t *base,
                             uint32_t control, uint32_t *status);

#endif
