/* Model 2 Emulator 1.1a MPEG-1 Layer II decoder, 004eb0f0. */
#include "dsb_original.h"


typedef struct {
    const uint8_t *data;
    size_t bytes;
    unsigned bit;
    int failed;
} bit_reader;

static unsigned read_bits(bit_reader *r, unsigned width)
{
    unsigned value = 0;
    while (width) {
        unsigned shift = r->bit & 7;
        unsigned take = width < 8-shift ? width : 8-shift;
        if (r->bit / 8 >= r->bytes) { r->failed = 1; return 0; }
        value = (value << take) |
                ((r->data[r->bit / 8] >> (8-shift-take)) & ((1u << take)-1));
        r->bit += take;
        width -= take;
    }
    return value;
}

static int allocation_table(unsigned rate, unsigned channels, unsigned bitrate)
{
    static const int classes[2][16] = {
        {0,1,2,3,4,5,6,7,8,9,10,-1,-1,-1,-1,0},
        {0,-1,-1,-1,1,-1,2,3,4,5,6,7,8,9,10,0}
    };
    static const int tables[3][11] = {
        {1,2,2,0,0,0,1,1,1,1,1}, {0,2,2,0,0,0,0,0,0,0,0}, {1,3,3,0,0,0,1,1,1,1,1}
    };
    int c = classes[channels-1][bitrate];
    return c < 0 ? -1 : tables[rate][c];
}

/* Class zero is unallocated. The original loader also leaves the unmatched
 * 4195 entry at class zero (table 0, first three bands, allocation 11). */
static const unsigned char quantizer[6][16] = {
    {0,1,3,5,6,7,8,9,10,11,12,13,14,15,16,17},
    {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,17},
    {0,1,2,3,4,5,6,17},
    {0,1,2,17},
    {0,1,2,4,5,6,7,8,9,10,11,12,13,14,15,16},
    {0,1,2,4,5,6,7,8}
};
static const unsigned char alloc_bits[] = {4,4,3,2,4,3};
static const unsigned char code_bits[] = {0,5,7,3,10,4,5,6,7,8,9,10,11,12,13,14,15,16};
static const unsigned char grouped_levels[] = {0,3,5,0,9};

static unsigned layout(unsigned table, unsigned band)
{
    if (table >= 2) return band < 2 ? 4 : 5;
    if (band < 3) return 0;
    if (band < 11) return 1;
    return band < 23 ? 2 : 3;
}

static const double factor[] = {
    1.33333333333, 1.6, 1.14285714286, 1.77777777777,
    1.06666666666, 1.03225806452, 1.01587301587, 1.00787401575,
    1.00392156863, 1.00195694716, 1.00097751711, 1.00048851979,
    1.00024420024, 1.00012208522, 1.00006103888, 1.00003051851,
    1.00001525902,
};

static const double bias[] = {
    0.5, 0.5, 0.25, 0.5,
    0.125, 0.0625, 0.03125, 0.015625,
    0.0078125, 0.00390625, 0.001953125, 0.0009765625,
    0.00048828125, 0.00024414063, 0.00012207031, 6.103516e-05,
    3.051758e-05,
};

static const double scale[] = {
    2.0, 1.5874010519682, 1.25992104989487, 1.0,
    0.7937005259841, 0.62996052494744, 0.5, 0.39685026299205,
    0.31498026247372, 0.25, 0.19842513149602, 0.15749013123686,
    0.125, 0.09921256574801, 0.07874506561843, 0.0625,
    0.04960628287401, 0.03937253280921, 0.03125, 0.024803141437,
    0.01968626640461, 0.015625, 0.0124015707185, 0.0098431332023,
    0.0078125, 0.00620078535925, 0.00492156660115, 0.00390625,
    0.00310039267963, 0.00246078330058, 0.001953125, 0.00155019633981,
    0.00123039165029, 0.0009765625, 0.00077509816991, 0.00061519582514,
    0.00048828125, 0.00038754908495, 0.00030759791257, 0.000244140625,
    0.00019377454248, 0.00015379895629, 0.0001220703125, 9.688727124e-05,
    7.689947814e-05, 6.103515625e-05, 4.844363562e-05, 3.844973907e-05,
    3.051757813e-05, 2.422181781e-05, 1.922486954e-05, 1.525878906e-05,
    1.21109089e-05, 9.61243477e-06, 7.62939453e-06, 6.05545445e-06,
    4.80621738e-06, 3.81469727e-06, 3.02772723e-06, 2.40310869e-06,
    1.90734863e-06, 1.51386361e-06, 1.20155435e-06, 0.0,
};

static void read_scales(bit_reader *r, unsigned select, unsigned char indices[3])
{
    indices[0] = read_bits(r,6);
    indices[1] = select == 0 || select == 3 ? read_bits(r,6) : indices[0];
    indices[2] = select <= 1 ? read_bits(r,6) : indices[1];
}

static int grouped(unsigned q)
{
    return q < sizeof grouped_levels && grouped_levels[q];
}

static void codes(bit_reader *r, unsigned q, unsigned values[3])
{
    if (grouped(q)) {
        unsigned packed = read_bits(r,code_bits[q]);
        for (unsigned i=0; i<3; i++) {
            values[i] = packed % grouped_levels[q];
            packed /= grouped_levels[q];
        }
    } else {
        for (unsigned i=0; i<3; i++) values[i] = read_bits(r,code_bits[q]);
    }
}

static float requantize(unsigned q, unsigned code, unsigned scalefactor)
{
    unsigned bits = grouped(q) ? (q == 1 ? 2 : q == 2 ? 3 : 4) : code_bits[q];
    unsigned half = 1u << (bits-1);
    float normalized = (float)(code & (half-1)) / half + ((code & half) ? 0 : -1);
    float offset = (float)((double)normalized + bias[q-1]);
    float value = (float)((double)offset * factor[q-1]);
    return (float)((double)value * scale[scalefactor]);
}

int m2_dsb_layer2(m2_dsb_synthesis *f, const uint8_t *data, size_t size,
                  const m2_dsb_header *h, int16_t pcm[2][1152])
{
    if (!h || h->layer != 2 || size < 4) return M2_DSB_INVALID_FRAME;
    int table = allocation_table((data[2] >> 2) & 3,h->channels,data[2] >> 4);
    if (table < 0) return M2_DSB_NO_ALLOCATION_TABLE;
    static const unsigned limits[] = {27,30,8,12};
    const unsigned limit = limits[table];
    bit_reader r = {data,size,h->payload_bit,0};
    unsigned char allocated[2][32] = {{0}}, qclass[2][32] = {{0}};
    unsigned char select[2][32] = {{0}}, scales[2][32][3] = {{{0}}};
    for (unsigned b=0; b<limit; b++) {
        unsigned row = layout((unsigned)table,b);
        for (unsigned ch=0; ch<h->channels; ch++) {
            unsigned a = ch && b>=h->joint_bands ? allocated[0][b] : read_bits(&r,alloc_bits[row]);
            allocated[ch][b] = a;
            qclass[ch][b] = table==0 && b<3 && a==11 ? 0 : quantizer[row][a];
        }
    }
    for (unsigned b=0; b<limit; b++)
        for (unsigned ch=0; ch<h->channels; ch++)
            if (allocated[ch][b]) select[ch][b] = read_bits(&r,2);
    for (unsigned b=0; b<limit; b++)
        for (unsigned ch=0; ch<h->channels; ch++)
            if (allocated[ch][b]) read_scales(&r,select[ch][b],scales[ch][b]);
    for (unsigned block=0; block<12; block++) {
        double bands[3][2][32] = {{{0}}};
        for (unsigned b=0; b<limit; b++) {
            unsigned values[3] = {0};
            for (unsigned ch=0; ch<h->channels; ch++) {
                if (!allocated[ch][b]) continue;
                unsigned q = qclass[ch][b];
                if (b >= h->joint_bands && grouped(q)) return M2_DSB_NATIVE_STALL;
                if (ch == 0 || b < h->joint_bands) codes(&r,q,values);
                for (unsigned i=0; i<3; i++) {
                    /* Unmatched allocation has a zero bit width and the
                     * zero-initialized native parameter struct (class index 0). */
                    bands[i][ch][b] = q ? requantize(q, values[i], scales[ch][b][block/4])
                                         : (float)((float)(-0.5 * factor[0]) * scale[scales[ch][b][block/4]]);
                }
            }
        }
        if (r.failed) return M2_DSB_INVALID_FRAME;
        for (unsigned i=0; i<3; i++)
            for (unsigned ch=0; ch<h->channels; ch++)
                m2_dsb_synthesize(f,ch,bands[i][ch],pcm[ch]+32*(block*3+i));
    }
    return M2_DSB_DECODED;
}

/* 004eba50 writes 384 samples, leaving the rest of the previous block
 * untouched. The outer board always uses its original 1152-sample clock. */
int m2_dsb_layer1(m2_dsb_synthesis *f, const uint8_t *data, size_t size,
                  const m2_dsb_header *h, int16_t pcm[2][1152])
{
    if (!h || h->layer != 1 || size < 4) return M2_DSB_INVALID_FRAME;
    bit_reader r = {data,size,h->payload_bit,0};
    unsigned char alloc[2][32], scale_id[2][32];
    for (unsigned b=0; b<32; b++)
        for (unsigned ch=0; ch<h->channels; ch++)
            alloc[ch][b] = ch && b>=h->joint_bands ? alloc[0][b] : read_bits(&r,4);
    for (unsigned b=0; b<32; b++)
        for (unsigned ch=0; ch<h->channels; ch++)
            scale_id[ch][b] = alloc[ch][b] ? read_bits(&r,6) : 63;
    for (unsigned k=0; k<12; k++) {
        double bands[2][32] = {{0}};
        for (unsigned b=0; b<32; b++) {
            unsigned code = 0;
            for (unsigned ch=0; ch<h->channels; ch++) {
                unsigned n = alloc[ch][b];
                if (!n) continue;
                if (!ch || b<h->joint_bands) code = read_bits(&r,n==15 ? 0 : n+1);
                unsigned half = 1u << n;
                float value = (float)((code & (half-1))+1) / half + (code & half ? 0 : -1);
                value = (value * (2*half)) / (2*half-1);
                bands[ch][b] = (float)((double)value * scale[scale_id[ch][b]]);
            }
        }
        if (r.failed) return M2_DSB_INVALID_FRAME;
        for (unsigned ch=0; ch<h->channels; ch++)
            m2_dsb_synthesize(f,ch,bands[ch],pcm[ch]+32*k);
    }
    return M2_DSB_DECODED;
}
