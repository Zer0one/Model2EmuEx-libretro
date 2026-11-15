/* Optional ElSemi digital board, called at the i960 port and after the SCSP mix. */
#include "dsb_board.h"
#include <math.h>
#include <stdlib.h>

struct m2_dsb_board {
    unsigned kind;
    const uint8_t *program, *music;
    size_t program_size, music_size;
    m2_dsb_state state;
    m2_dsb_synthesis filter;
    int16_t pcm[2][1152];
    uint32_t decoded_buffers_bound;
    const char *error;
};

m2_dsb_board *m2_dsb_board_create(unsigned kind, const uint8_t *program, size_t program_size,
                                  const uint8_t *music, size_t music_size)
{
    if ((kind != 1 && kind != 2) || !program || !program_size || !music || !music_size)
        return NULL;
    m2_dsb_board *b = calloc(1,sizeof *b);
    if (!b) return NULL;
    b->kind = kind;
    b->program = program;
    b->program_size = program_size;
    b->music = music;
    b->music_size = music_size;
    m2_dsb_synthesis_init(&b->filter);
    return b;
}

void m2_dsb_board_command(m2_dsb_board *b, uint8_t byte)
{
    if (!b->error && !m2_dsb_command(&b->state,b->kind,b->program,b->program_size,byte))
        b->error = "track descriptor outside program ROM";
}

static int refill(m2_dsb_board *b)
{
    m2_dsb_state *s = &b->state;
    if ((int32_t)s->position >= (int32_t)s->end) {
        if (!m2_dsb_next_segment(s,b->kind,b->program,b->program_size)) {
            b->error = "segment descriptor outside program ROM";
            return 0;
        }
        if (!s->active) return 0;
    }
    if (s->position >= b->music_size) {
        b->error = "compressed address outside music ROM";
        return 0;
    }
    const uint8_t *frame = b->music + s->position;
    size_t remaining = b->music_size - s->position;
    m2_dsb_header h;
    if (remaining < 4) {
        b->error = "header crosses music ROM boundary";
        return 0;
    }
    if (!m2_dsb_frame_header(frame,remaining,&h)) {
        /* EAX=-1, rate=1, output pointers retain their previous values. */
        if (!b->decoded_buffers_bound) {
            b->error = "native decoder returned unbound PCM buffers";
            return 0;
        }
        --s->position;
        s->step = 0;
        s->phase = 0;
        return 1;
    }
    b->decoded_buffers_bound = 1;
    int result = M2_DSB_DECODED;
    if (h.layer == 1) result = m2_dsb_layer1(&b->filter,frame,remaining,&h,b->pcm);
    if (h.layer == 2) result = m2_dsb_layer2(&b->filter,frame,remaining,&h,b->pcm);
    if (result == M2_DSB_NO_ALLOCATION_TABLE) h.bytes = 0;
    else if (result != M2_DSB_DECODED) {
        b->error = result == M2_DSB_NATIVE_STALL ? "native joint-stereo decoder stalled"
                                                  : "invalid MPEG payload";
        return 0;
    }
    /* 004e9e50 leaves rate=1 and both PCM buffers untouched for Layer III. */
    s->step = (h.layer >= 3 ? 1 : h.rate) * 256 / 44100;
    s->position += h.bytes;
    s->phase = 0;
    return 1;
}

void m2_dsb_board_mix(m2_dsb_board *b, int16_t *stereo, size_t frames)
{
    while (frames && b->state.active && !b->error) {
        if (b->state.phase >= (1152u << 8) && !refill(b)) break;
        size_t mixed = m2_dsb_mix_decoded(&b->state,b->kind,b->pcm[0],b->pcm[1],stereo,frames);
        stereo += mixed * 2;
        frames -= mixed;
    }
}

const char *m2_dsb_board_error(const m2_dsb_board *b, uint32_t *position)
{
    if (position) *position = b->state.position;
    return b->error;
}

void m2_dsb_board_archive(m2_dsb_board *b, m2_state *a)
{
    unsigned tag = 0x31425344, kind = b->kind; /* DSB1 */
    m2_dsb_state s = b->state;
    uint32_t bound = b->decoded_buffers_bound;
    unsigned cursor[2];
    memcpy(cursor,b->filter.cursor,sizeof cursor);
    m2_state_value(a,&tag,sizeof tag);
    m2_state_value(a,&kind,sizeof kind);
    m2_state_value(a,&s,sizeof s);
    m2_state_value(a,cursor,sizeof cursor);
    m2_state_value(a,&bound,sizeof bound);
    if (tag != 0x31425344 || kind != b->kind || bound > 1 || s.used > 2 || s.active > 1 ||
        s.descriptor >= b->program_size || s.route > 255 || s.step > 278 ||
        s.phase >= (1152u << 8) + 278 ||
        cursor[0] > 960 || cursor[1] > 960 || ((cursor[0] | cursor[1]) & 63) ||
        s.previous[0] != (int16_t)s.previous[0] || s.previous[1] != (int16_t)s.previous[1])
        a->failed = 1;
    m2_state_bytes(a,b->pcm,sizeof b->pcm);
    for (unsigned ch = 0; ch < 2; ++ch) {
        float history[1024];
        memcpy(history,b->filter.history[ch],sizeof history);
        m2_state_value(a,history,sizeof history);
        for (unsigned i = 0; i < 1024; ++i)
            if (!isfinite(history[i]) || fabsf(history[i]) > 256) a->failed = 1;
        if (a->mode == M2_STATE_LOAD && !a->failed)
            memcpy(b->filter.history[ch],history,sizeof history);
    }
    if (a->mode == M2_STATE_LOAD && !a->failed) {
        b->state = s;
        b->decoded_buffers_bound = bound;
        memcpy(b->filter.cursor,cursor,sizeof cursor);
        b->error = NULL;
    }
}
