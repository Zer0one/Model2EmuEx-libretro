/* Model 2 Emulator 1.1a optional digital sound board. Addresses in this
 * state are byte offsets in ROM. No host pointer belongs to the machine. */
#ifndef M2_DSB_ORIGINAL_H
#define M2_DSB_ORIGINAL_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint8_t packet[3], used, segment;
    uint32_t descriptor, position, end, loop, active, route;
    uint32_t phase, step;
    int32_t previous[2];
} m2_dsb_state;

typedef struct {
    unsigned layer, rate, channels, joint_bands, bytes, payload_bit;
} m2_dsb_header;

/* Read a frame at the supplied compressed offset, as at 004e9e50. */
int m2_dsb_frame_header(const uint8_t *data, size_t size, m2_dsb_header *header);

typedef struct {
    double cosine[64][32];
    float history[2][1024];
    unsigned cursor[2];
} m2_dsb_synthesis;

void m2_dsb_synthesis_init(m2_dsb_synthesis *filter);
void m2_dsb_synthesize(m2_dsb_synthesis *filter, unsigned channel,
                       const double bands[32], int16_t pcm[32]);

enum { M2_DSB_INVALID_FRAME, M2_DSB_DECODED, M2_DSB_NATIVE_STALL, M2_DSB_NO_ALLOCATION_TABLE };
int m2_dsb_layer1(m2_dsb_synthesis *filter, const uint8_t *data, size_t size,
                  const m2_dsb_header *header, int16_t pcm[2][1152]);
int m2_dsb_layer2(m2_dsb_synthesis *filter, const uint8_t *data, size_t size,
                  const m2_dsb_header *header, int16_t pcm[2][1152]);

/* Return zero for a descriptor read outside the supplied program region. */
int m2_dsb_command(m2_dsb_state *s, unsigned kind, const uint8_t *program,
                   size_t size, uint8_t value);
int m2_dsb_next_segment(m2_dsb_state *s, unsigned kind, const uint8_t *program,
                        size_t size);
/* Mix a decoded stereo frame up to the next native refill or block end. */
size_t m2_dsb_mix_decoded(m2_dsb_state *s, unsigned kind, const int16_t *left,
                          const int16_t *right, int16_t *stereo, size_t count);
#endif
