#include "dsb_original.h"

static uint32_t word(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8);
}

static uint32_t address24(const uint8_t *p)
{
    return ((uint32_t)p[0] << 16) | ((uint32_t)p[1] << 8) | p[2];
}

/* Native MPEG-1 tables at 00512190, 005121d0 and 00512210.
 * No sync search: the board supplies the exact next compressed offset. */
int m2_dsb_frame_header(const uint8_t *p, size_t size, m2_dsb_header *h)
{
    static const unsigned rates[] = {44100, 48000, 32000};
    static const unsigned kbps[3][16] = {
        {0,32,64,96,128,160,192,224,256,288,320,352,384,416,448,0},
        {0,32,48,56,64,80,96,112,128,160,192,224,256,320,384,0},
        {0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0}
    };
    if (size < 4 || p[0] != 0xff || (p[1] & 0xf8) != 0xf8) return 0;
    unsigned rate_code = (p[2] >> 2) & 3;
    unsigned layer = 4 - ((p[1] >> 1) & 3);
    if (rate_code == 3) return 0;
    unsigned rate = rates[rate_code];
    /* Reserved layer 4 indexes the adjacent constants at 00512250.
     * IMUL wraps at 32 bits before the signed division at 004e9fb0. */
    static const uint32_t adjacent[16] = {
        44100,48000,32000,0,4,8,12,16,0,0,
        0x7eda0be1,0xbef0000e,0x7eda0be1,0xbef0000e,0x7eda0be1,0xbef0000e
    };
    unsigned bitrate = layer == 4 ? adjacent[p[2] >> 4] : kbps[layer-1][p[2] >> 4];
    unsigned padding = (p[2] >> 1) & 1;
    unsigned mode = p[3] >> 6;
    h->layer = layer;
    h->rate = rate;
    h->channels = mode == 3 ? 1 : 2;
    h->joint_bands = mode == 1 ? 4 * (1 + ((p[3] >> 4) & 3)) : 32;
    h->bytes = layer == 1 ? 4 * (12000 * bitrate / rate + padding)
                          : (uint32_t)((int32_t)(144000u * bitrate) / (int32_t)rate) + padding;
    h->payload_bit = p[1] & 1 ? 32 : 48;
    return 1;
}

static uint32_t dsb2_address(const uint8_t *p)
{
    return ((uint32_t)p[2] << 16) | ((uint32_t)p[5] << 8) | p[4];
}

/* 004b2960 sign-extends the segment index only after reading the table base. */
static int segment_bounds(m2_dsb_state *s, const uint8_t *p, size_t size, uint8_t index)
{
    if (size < 0x1004) return 0;
    int base = (word(p + 0x1002) + 0x7000) & 0xfffe;
    int at = base + 6 * (int8_t)index;
    if (at < 0 || (size_t)at + 6 > size) return 0;
    s->position = address24(p + at);
    s->end = address24(p + at + 3);
    return 1;
}

static int start_track(m2_dsb_state *s, unsigned kind, const uint8_t *p,
                       size_t size, unsigned track)
{
    uint32_t at, desc;
    if (kind == 1) {
        if (size < 0x1006) return 0;
        if (track > word(p + 0x1004) - 1u) return 1;
        at = ((word(p + 0x1000) + 0x7000) & 0xfffe) + 2 * (track - 1);
        if (at + 2 > size) return 0;
        desc = (word(p + at) + 0x7000) & 0xffff;
        if (desc + 5 > size || !segment_bounds(s, p, size, p[desc+4])) return 0;
        s->route = p[desc+3];
    } else {
        if (size < 0x800c) return 0;
        if (track > word(p + 0x800a) - 1u) return 1;
        at = (word(p + 0x8002) & 0xfffe) + 4 * track - 2;
        if (at + 2 > size) return 0;
        desc = word(p + at);
        if (desc + 10 > size) return 0;
        const uint8_t *record = p + desc;
        if ((record[1] & 0x80) && desc + 18 > size) return 0;
        s->position = dsb2_address(record);
        s->end = dsb2_address(record + 4);
        s->loop = record[1] & 0x80 ? dsb2_address(record + 12) : 0;
        s->route = 0;
    }
    s->descriptor = desc;
    s->segment = 0;
    s->phase = 1152u << 8;
    s->previous[0] = s->previous[1] = 0;
    s->active = 1;
    return 1;
}

/* 004b2bc0 / 004b2aa0. A new A-prefix abandons the incomplete packet.
 * FF is stored in the pending packet before its write cursor is reset. */
int m2_dsb_command(m2_dsb_state *s, unsigned kind, const uint8_t *p, size_t size,
                   uint8_t value)
{
    if ((value & 0xf0) == 0xa0) s->used = 0;
    s->packet[s->used++] = value;
    if (value != 0xff && s->used < 3) return 1;
    s->used = 0;
    if (value == 0xff) return 1;
    unsigned prefix = s->packet[0], cmd = s->packet[1];
    if (kind == 2 && prefix == 0xa0 && cmd == 0 && value == 1) s->active = 0;
    if ((kind == 1 && prefix == 0xaf) || (kind == 2 && prefix == 0xae)) {
        if (cmd == 3 || (cmd == 0x6f && !value)) s->active = 0;
        if (value && cmd == (kind == 1 ? 0x6f : 0x10))
            return start_track(s, kind, p, size, value);
    }
    return 1;
}

int m2_dsb_next_segment(m2_dsb_state *s, unsigned kind, const uint8_t *p, size_t size)
{
    if (kind == 2) {
        if (s->loop) s->position = s->loop;
        else s->active = 0;
        return 1;
    }
    size_t at = (size_t)s->descriptor + 5 + s->segment;
    if (at >= size) return 0;
    uint8_t next = p[at];
    if (next >= 0xf0 && !(next & 1)) {
        s->active = 0;
        return 1;
    }
    uint8_t index = next >= 0xf0 ? 0 : (uint8_t)(s->segment + 1);
    if (!segment_bounds(s, p, size, p[s->descriptor + 4 + index])) return 0;
    s->segment = index;
    return 1;
}

/* 004b2d10. History advances only when the integer source index changes.
 * The DSB mixes with the existing signed SCSP output even for silent music. */
size_t m2_dsb_mix_decoded(m2_dsb_state *s, unsigned kind, const int16_t *left,
                          const int16_t *right, int16_t *stereo, size_t count)
{
    size_t i = 0;
    for (; s->active && i < count && s->phase < (1152u << 8); ++i) {
        unsigned index = s->phase >> 8;
        int weight = s->phase & 255;
        int l = (left[index]*weight + s->previous[0]*(256-weight)) >> 8;
        int r = (right[index]*weight + s->previous[1]*(256-weight)) >> 8;
        if (kind == 2 || (kind == 1 && s->route <= 2)) {
            if (kind == 1 && s->route == 1) r = l;
            if (kind == 1 && s->route == 2) l = r;
            stereo[2*i] = (int16_t)((stereo[2*i] + l) >> 1);
            stereo[2*i+1] = (int16_t)((stereo[2*i+1] + r) >> 1);
        }
        uint32_t phase = s->phase + s->step;
        if ((phase ^ s->phase) >> 8) {
            s->previous[0] = left[index];
            s->previous[1] = right[index];
        }
        s->phase = phase;
    }
    return i;
}
