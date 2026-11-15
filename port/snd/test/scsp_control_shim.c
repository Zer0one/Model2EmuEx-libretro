/* ROM-free access to the actual SCSP control paths; no production exports. */
#include "../scsp.c"
#ifdef SCSP_A68K_BIND_TEST
#include "../../a68k/scsp_bus.h"
static a68k_page bound_data[A68K_PAGE_COUNT],bound_writes[A68K_PAGE_COUNT];

int scsp_idle_write_probe(unsigned offset, unsigned width, uint32_t flags, uint32_t *scratch)
{
    static scsp baseline, chip;
    if (!a68k_scsp_bind_pages(bound_data, bound_writes, &chip)) return 0;
    a68k_host_state host = {0, flags, 1};
    if (!a68k_write_observed(bound_writes, 0x100000 + offset, width, 0x1234abcd, &host)) return 0;
    scratch[0] = host.eax;
    scratch[1] = host.control_flags;
    return memcmp(&baseline, &chip, sizeof chip) == 0;
}

int scsp_ring_write_probe(unsigned offset, unsigned width, uint32_t value,
                          uint32_t flags, uint16_t *ring, uint32_t *scratch)
{
    static scsp chip;
    if (!a68k_scsp_bind_pages(bound_data, bound_writes, &chip)) return 0;
    memcpy(chip.RINGBUF, ring, sizeof chip.RINGBUF);
    memcpy(&chip.ring_cursor, ring + 64, 4);
    memcpy(&chip.master, ring + 68, 4);
    memcpy(&chip.voice_ram_address, ring + 66, 4);
    memcpy(&chip.DSP.context.ram_address, ring + 70, 4);
    memcpy(&chip.DSP.context.RBP, ring + 72, 4);
    memcpy(&chip.DSP.context.RBL, ring + 74, 4);
    memcpy(chip.DSP.context.COEF, ring + 76, 104);
    a68k_host_state host = {0, flags, 1};
    int ok = a68k_write_observed(bound_writes, 0x100000 + offset, width, value, &host);
    memcpy(ring, chip.RINGBUF, sizeof chip.RINGBUF);
    memcpy(ring + 64, &chip.ring_cursor, 4);
    memcpy(ring + 68, &chip.master, 4);
    memcpy(ring + 66, &chip.voice_ram_address, 4);
    memcpy(ring + 70, &chip.DSP.context.ram_address, 4);
    memcpy(ring + 72, &chip.DSP.context.RBP, 4);
    memcpy(ring + 74, &chip.DSP.context.RBL, 4);
    memcpy(ring + 76, chip.DSP.context.COEF, 104);
    scratch[0] = host.eax;
    scratch[1] = host.control_flags;
    return ok;
}

/* Image spans COEF, MADRS, MPRO and the first TEMP word, as in the PE. */
int scsp_dsp_write_probe(unsigned offset, unsigned width, uint32_t value, uint32_t flags,
                         unsigned backend, uint32_t wrapper_sp, uint8_t *image, size_t size, uint32_t *scratch)
{
    scsp *s = calloc(1, sizeof *s);
    size_t first = offsetof(scsp_dsp_context, COEF);
    size_t end = offsetof(scsp_dsp_context, TEMP) + sizeof(int32_t);
    if (!s || size != end - first || !a68k_scsp_bind_pages(bound_data, bound_writes, s)) {
        free(s);
        return -1;
    }
    s->dsp_backend = backend;
    scsp_bind_cpu_write_frame(s, &wrapper_sp, 0x77000000);
    s->DSP.context.Stopped = 1;
    s->DSP.context.ram_address = SCSP_DSP_RAM_ADDRESS;
    uint8_t *registers = (uint8_t *)&s->DSP.context + first;
    memcpy(registers, image, size);
    a68k_host_state host = {0x1234, flags, 1};
    int accepted = a68k_write_observed(bound_writes, 0x100000 + offset, width, value, &host);
    memcpy(image, registers, size);
    scratch[0] = host.eax;
    scratch[1] = host.control_flags;
    scratch[2] = s->DSP.context.Stopped;
    scratch[3] = (uint32_t)s->DSP.context.LastStep;
    free(s);
    return accepted;
}

int scsp_slot_write_probe(unsigned offset, unsigned width, uint32_t value,
                          uint32_t flags, uint32_t wrapper_sp, uint16_t *registers, uint32_t *result)
{
    scsp *s = calloc(1, sizeof *s);
    if (!s || !a68k_scsp_bind_pages(bound_data, bound_writes, s)) { free(s); return 0; }
    scsp_bind_cpu_write_frame(s, &wrapper_sp, 0x77000000);
    for (int i = 0; i < 64; ++i) { s->ARTABLE[i] = 100+i; s->DRTABLE[i] = 200+i; }
    for (unsigned i = 0; i < 32; i++) {
        memcpy(s->Slots[i].u.data, registers + 16*i, 32);
        s->Slots[i].EG.state = i % 4;
        s->Slots[i].active = i % 4 != RELEASE;
    }
    a68k_host_state host = {0xa5a5, flags, 1};
    result[0] = a68k_write_observed(bound_writes, 0x100000+offset, width, value, &host);
    result[1] = host.eax;
    result[2] = host.control_flags;
    for (unsigned i = 0; i < 32; i++) {
        memcpy(registers + 16*i, s->Slots[i].u.data, 32);
        result[3+i*11] = s->Slots[i].active;
        result[4+i*11] = s->Slots[i].EG.state;
        result[5+i*11] = s->Slots[i].sample_base;
        result[6+i*11] = s->Slots[i].step;
        const eg_t *eg = &s->Slots[i].EG;
        result[7+i*11] = eg->volume;
        result[8+i*11] = eg->AR;
        result[9+i*11] = eg->D1R;
        result[10+i*11] = eg->D2R;
        result[11+i*11] = eg->RR;
        result[12+i*11] = eg->DL;
        result[13+i*11] = eg->EGHOLD;
    }
    result[3 + 11*32] = s->Slots[offset/32].PLFO.phase_step;
    result[4 + 11*32] = s->Slots[offset/32].ALFO.phase_step;
    free(s);
    return 1;
}

int scsp_voice_sample_probe(uint8_t *ram, unsigned control, unsigned base,
                            unsigned live_low, unsigned cursor, unsigned step,
                            int32_t previous, unsigned loop_end, int32_t *sample, uint32_t *fault,
                            int32_t *history, uint32_t *next_cursor)
{
    scsp *s = calloc(1, sizeof *s);
    if (!s) return 0;
    s->ram = ram;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_ram_size = 0x100000;
    s->ram_mask = 0x7ffff;
    slot_t *slot = &s->Slots[0];
    slot->EG.state = RELEASE;
    scsp_write16(s, 2, base, 0xffff);
    scsp_write16(s, 6, loop_end, 0xffff);
    scsp_write16(s, 0xc, 0x300, 0xffff); /* Direct sample, inhibit ring write. */
    scsp_write16(s, 0, control, 0xffff);
    scsp_write16(s, 2, live_low, 0xffff);
    slot->step = step;
    slot->Prev = (int16_t)previous;
    slot->cur_addr = cursor;
    slot->nxt_addr = cursor + (1 << SHIFT);
    *sample = advance_voice_sample(s, slot);
    *fault = s->voice_fault_address;
    *history = slot->Prev;
    *next_cursor = slot->cur_addr;
    free(s);
    return 1;
}

/* Keep one synthetic chip for repeated envelope tests with production tables. */
static scsp envelope_chip;

void scsp_envelope_tables(uint32_t *dest)
{
    init_tables(&envelope_chip);
    for (int i = 0; i < 64; ++i) {
        dest[i] = envelope_chip.ARTABLE[i];
        dest[64+i] = envelope_chip.DRTABLE[i];
    }
}

void scsp_gain_tables(int32_t *out)
{
    scsp *s = &envelope_chip;
    memcpy(out, s->EG_TABLE, sizeof s->EG_TABLE);
    out += 1024;
    for (unsigned row = 0; row < 8; ++row) {
        memcpy(out, s->PSCALES[row], 256 * sizeof *out);
        out += 256;
    }
    memcpy(out, s->ASCALES, sizeof s->ASCALES);
}

/* Each row captures all 32 slots at power-on or after a single guest store. */
void scsp_cold_key_scans(uint32_t *out)
{
    scsp *s = &envelope_chip;
    scsp_original_power_on(s);
    const uint16_t scans[] = {0x1800, 0x1000, 0x1800};
    for (unsigned phase = 0; phase < 4; ++phase) {
        if (phase) scsp_write16(s, 0, scans[phase-1], 0xffff);
        for (unsigned i = 0; i < 32; ++i) {
            slot_t *v = &s->Slots[i];
            *out++ = v->slot;
            *out++ = v->active;
            *out++ = v->EG.state;
            *out++ = v->u.data[0];
            *out++ = v->EG.volume;
        }
    }
}

void scsp_lfo_reference(uint32_t *steps, int32_t *waves, uint32_t *saw_gain, uint32_t *noise_gain)
{
    scsp *s = &envelope_chip;
    init_tables(s);
    slot_t *slot = &s->Slots[0];
    for (unsigned rate = 0; rate < 32; rate++) {
        scsp_write16(s, 0x12, (rate << 10) | 0xe7, 0xffff);
        steps[rate] = slot->PLFO.phase_step;
    }
    for (unsigned wave = 0; wave < 4; wave++) {
        scsp_write16(s, 0x12, (wave << 8) | (wave << 3) | 0xe7, 0xffff);
        memcpy(waves + wave * 512, slot->PLFO.table, 256 * sizeof(*waves));
        memcpy(waves + wave * 512 + 256, slot->ALFO.table, 256 * sizeof(*waves));
    }
    scsp_write16(s, 0x12, 0xe0, 0xffff);
    for (unsigned phase = 0; phase < 256; phase++) {
        slot->PLFO.phase = (uint16_t)(phase << 8);
        saw_gain[phase] = PLFO_Step(&slot->PLFO);
    }
    for (unsigned depth = 1; depth <= 7; ++depth) {
        scsp_write16(s, 0x12, (3 << 8) | (depth << 5) | (3 << 3) | depth, 0xffff);
        for (unsigned phase = 0; phase < 256; ++phase) {
            slot->PLFO.phase = slot->ALFO.phase = (uint16_t)(phase << 8);
            unsigned i = ((depth - 1) * 256 + phase) * 2;
            noise_gain[i] = PLFO_Step(&slot->PLFO);
            noise_gain[i + 1] = ALFO_Step(&slot->ALFO);
        }
    }
}

void scsp_envelope_step(uint16_t first, uint16_t second, uint16_t pitch,
                        unsigned state, unsigned volume, uint32_t *out)
{
    slot_t *slot = &envelope_chip.Slots[0];
    slot->active = 1;
    slot->u.data[0] = 0x800;
    slot->u.data[5] = second;
    slot->u.data[8] = pitch;
    slot->EG.state = state;
    slot->EG.volume = (int)volume;
    scsp_write16(&envelope_chip, 8, first, 0xffff);
    out[0] = slot->EG.AR;
    out[1] = slot->EG.D1R;
    out[2] = slot->EG.D2R;
    out[3] = slot->EG.RR;
    out[4] = slot->EG.DL;
    out[5] = slot->EG.EGHOLD;
    out[6] = EG_Update(slot);
    out[7] = slot->EG.volume;
    out[8] = slot->EG.state;
    out[9] = slot->active;
    out[10] = slot->u.data[0];
}

/* Observe the same one-sample SCSP entry point used by the sound board. */
static scsp *setup_block_probe(unsigned backend, unsigned end, unsigned history,
                            unsigned adjacent, unsigned inhibit, unsigned mode, unsigned source)
{
    static uint8_t ram[1 << 20];
    scsp *s = &envelope_chip;
    scsp_reset(s);
    s->ram = ram;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_ram_size = sizeof ram;
    scsp_set_dsp_backend(s, backend);
    scsp_set_interleaved_mixer(s, mode);
    s->u.data[0] = 15;
    for (unsigned i = 0; i < 8; ++i) ram[i] = (i & 1) ? 32 : adjacent;
    slot_t *slot = &s->Slots[0];
    slot->u.data[0] = 0x810 | (source << 7);
    slot->u.data[2] = 16;
    slot->u.data[3] = end;
    slot->u.data[5] = 0x4000;
    slot->u.data[6] = 0x108 | (inhibit << 9);
    slot->u.data[10] = 7;
    slot->u.data[11] = 7 << 13;
    slot->active = 1;
    slot->step = 4096;
    slot->EG.state = ATTACK;
    slot->EG.volume = 0x3ff00;
    slot->EG.EGHOLD = 0x20;
    slot->Prev = (int16_t)history;
    slot->cached_tl_gain = 4096;
    return s;
}

void scsp_mixer_block_probe(unsigned mode, unsigned end, unsigned history, unsigned adjacent,
                           unsigned inhibit, unsigned cursor, unsigned frames, uint32_t *out)
{
    scsp *s = setup_block_probe(0, end, history, adjacent, inhibit, mode, 0);
    scsp_cpu_write_ring(s, 0x680, 2, cursor);
    int32_t pcm[6] = {0};
    if (!frames || frames > 3) return;
    scsp_render_clocked(s, pcm, (int)frames);
    for (unsigned i = 0; i < 2 * frames; ++i) out[i] = (uint32_t)pcm[i];
    out[6] = s->DSP.context.MIXS[0];
    out[7] = (uint8_t)s->ring_cursor;
    out[8] = s->Slots[0].active;
    if (cursor < 64) out[9] = (uint16_t)s->RINGBUF[cursor];
    else if (cursor < 76)
        out[9] = (uint16_t)(*ring_control_word(s, cursor) >> ((cursor & 1u) * 16));
    else if (cursor < 140) out[9] = (uint16_t)s->DSP.context.COEF[cursor-76];
    else if (cursor < 172) out[9] = s->DSP.context.MADRS[cursor-140];
    else out[9] = s->DSP.context.MPRO[cursor-172];
}

void scsp_source_block_probe(unsigned route, unsigned selector, unsigned source, int32_t *out)
{
    static const int waveform[256] = {0};
    static const int scale[257] = {[0] = 256, [128] = 256};
    scsp *s = setup_block_probe(0, 32, 8192, 32, 0, route, source);
    slot_t *v = &s->Slots[0];
    v->u.data[0] = 0x800 | ((selector & 3) << 5) | (selector & 16) | (source << 7);
    v->u.data[9] = ((selector & 8) ? 0x20 : 0) | ((selector & 4) ? 1 : 0);
    v->PLFO = (lfo_t){.phase_step = 256, .table = waveform, .scale = scale};
    v->ALFO = v->PLFO;
    scsp_render_clocked(s, out, 3);
    out[6] = s->DSP.context.MIXS[0];
    out[7] = v->cur_addr;
    out[8] = v->Prev;
    out[9] = v->active;
    out[10] = s->ring_cursor;
    out[11] = (uint16_t)s->RINGBUF[0];
    out[12] = (uint16_t)s->RINGBUF[32];
    out[13] = v->PLFO.phase;
    out[14] = v->ALFO.phase;
}

static scsp secondary_chip;

void scsp_dual_returns_probe(unsigned mode, unsigned dual, int first, int second, int32_t *out)
{
    scsp *s = &envelope_chip, *t = &secondary_chip;
    scsp_reset(s); scsp_reset(t);
    scsp_set_interleaved_mixer(s, mode);
    s->Slots[0].u.data[11] = t->Slots[0].u.data[11] = 7 << 5;
    s->DSP.context.EFREG[0] = (int16_t)first;
    t->DSP.context.EFREG[0] = (int16_t)second;
    if (dual) scsp_render_pair_clocked(s, t, out, 2);
    else scsp_render_clocked(s, out, 2);
}

void scsp_ring_voices_probe(unsigned mode, unsigned frames, unsigned dual, unsigned modulation, int32_t *out)
{
    scsp *chips[] = {&envelope_chip, &secondary_chip};
    static uint8_t ram[2][0x100000];
    for (int chip = 0; chip <= (int)dual; ++chip) {
        scsp *s = chips[chip]; scsp_reset(s);
        s->ram = ram[chip]; s->voice_ram_size = sizeof ram[chip];
        s->ring_cursor = chip ? 53 : 3;
        for (unsigned i = 0; i < (dual ? 512u : 0x10000u); ++i)
            ram[chip][i] = (uint8_t)(i * (3 + chip * 2) + (i >> 8) * 11 + 17);
        if (!dual)
            for (unsigned i = 0; i < 64; ++i)
                s->RINGBUF[i] = (int16_t)((i * 1907u + 13u) & 0xffff);
        for (int sl = 0; sl < 2; ++sl) {
            slot_t *v = &s->Slots[sl];
            v->u.data[0] = 0x810; v->u.data[2] = 16; v->u.data[3] = 64;
            v->u.data[5] = 0x4000; v->u.data[6] = 0x108;
            v->u.data[7] = (dual ? chip : sl) ? modulation : 0;
            v->u.data[10] = 7 | (sl << 3); v->u.data[11] = 0xe000;
            v->sample_base = (dual ? 128 : 0x8000) + 32*sl; v->active = 1; v->step = 4096;
            v->EG.state = ATTACK; v->EG.volume = 0x3ff00; v->EG.EGHOLD = 0x20;
            v->Prev = (int16_t)((chip*2+sl+1)*137); v->cached_tl_gain = 4096;
        }
    }
    scsp_set_interleaved_mixer(chips[0], mode);
    if (dual) scsp_render_pair_clocked(chips[0], chips[1], out, (int)frames);
    else scsp_render_clocked(chips[0], out, (int)frames);
    out += frames*2;
    for (int chip = 0; chip <= (int)dual; ++chip) {
        scsp *s = chips[chip];
        for (unsigned i = 0; i < 64; ++i) *out++ = s->RINGBUF[i];
        *out++ = s->DSP.context.MIXS[0];
        *out++ = s->DSP.context.MIXS[1];
        *out++ = s->ring_cursor;
    }
}

void scsp_active_effect_probe(unsigned mode, unsigned send, unsigned effect,
                             unsigned listen, const uint16_t *program,
                             const unsigned *blocks, unsigned count, int32_t *out)
{
    scsp *s = setup_block_probe(0, 2, 8192, 32, 0, mode, 0);
    s->Slots[0].u.data[10] = (send << 3) | 7;
    s->Slots[0].u.data[11] = 0;
    s->Slots[listen].u.data[11] = 7 << 5;
    s->DSP.context.COEF[0] = 0x4000;
    memcpy(s->DSP.context.MPRO, program, 16);
    scsp_dsp_original_start(&s->DSP);
    for (unsigned i = 0; i < count; ++i) {
        scsp_render_clocked(s, out, (int)blocks[i]);
        out += 2 * blocks[i];
    }
    memcpy(out, s->DSP.context.MIXS, sizeof s->DSP.context.MIXS);
    out[16] = s->DSP.context.EFREG[effect];
}

void scsp_block_route_probe(unsigned backend, unsigned end, unsigned history, unsigned adjacent,
                            unsigned inhibit, unsigned mode, unsigned source, uint32_t *out)
{
    scsp *s = setup_block_probe(backend, end, history, adjacent, inhibit, mode, source);
    slot_t *slot = &s->Slots[0];
    uint32_t previous = 0;
    for (int i = 0; i < 3; ++i) {
        unsigned at = (uint8_t)s->ring_cursor;
        int32_t pcm[2];
        scsp_render(s, pcm, 1);
        uint32_t mix = (uint32_t)s->DSP.context.MIXS[0];
        *out++ = at;
        *out++ = (uint16_t)s->RINGBUF[at];
        *out++ = (mix - previous) * (backend == SCSP_DSP_MAME ? 16u : 1u);
        *out++ = pcm[0];
        *out++ = pcm[1];
        previous = mix;
    }
    *out++ = slot->cur_addr;
    *out++ = slot->EG.volume;
    *out++ = (uint16_t)slot->Prev;
    *out = slot->active;
}

uint32_t scsp_direct_envelope_probe(unsigned direct)
{
    static uint8_t ram[0x100000];
    scsp *s = &envelope_chip;
    s->ram = ram;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_ram_size = sizeof ram;
    slot_t *slot = &s->Slots[0];
    memset(slot, 0, sizeof *slot);
    slot->u.data[0] = 0x810;
    slot->u.data[3] = 8;
    slot->u.data[6] = 0x200 | (direct << 8);
    slot->active = 1;
    slot->EG.state = DECAY2;
    slot->EG.volume = 31 << EG_SHIFT;
    UpdateSlot(s, s, slot, 0);
    return slot->active;
}

void scsp_decay2_boundary(unsigned level, uint32_t *result)
{
    slot_t slot = {0};
    slot.active = 1;
    slot.u.data[0] = 0x800;
    slot.EG.state = DECAY2;
    slot.EG.volume = (int)(level << EG_SHIFT);
    result[0] = EG_Update(&slot);
    result[1] = slot.active;
    result[2] = slot.u.data[0];
}

int scsp_pitch_survey(uint32_t *steps)
{
    scsp *s = calloc(1, sizeof *s);
    if (!s || !a68k_scsp_bind_pages(bound_data, bound_writes, s)) { free(s); return 0; }
    slot_t *slot = &s->Slots[0];
    for (unsigned octave = 0; octave < 16; ++octave) {
        for (unsigned fine = 0; fine < 1024; ++fine) {
            uint16_t pitch = (uint16_t)((octave << 11) | fine);
            slot->EG.state = RELEASE;
            scsp_write16(s, 0x10, pitch, 0xffff);
            slot->step = UINT32_MAX;
            scsp_write16(s, 0, 0x1800, 0xffff);
            *steps++ = slot->step;
            slot->step = UINT32_MAX;
            scsp_write16(s, 0x10, pitch, 0xffff);
            *steps++ = slot->step;
            a68k_host_state host = {0xa5a5, 0xed7, 1};
            if (!a68k_write_observed(bound_writes, 0x100010, 2, pitch, &host)) {
                free(s);
                return 0;
            }
            *steps++ = host.eax;
            *steps++ = host.control_flags;
        }
    }
    free(s);
    return 1;
}

/* Consecutive PCM steps through the production voice updater. LFO gain in
 * the x86 fixture is unity so the supplied effective step is identical. */
/* Inspect the voice before amplitude LFO, envelope attenuation and mixing. */
void scsp_pcm_fetch_probe(uint8_t *ram, unsigned route, unsigned control, uint32_t base,
                          uint32_t cursor, uint32_t step, unsigned backwards,
                          int tap, unsigned modulate, uint32_t *out)
{
    scsp *s = &envelope_chip;
    slot_t *v = &s->Slots[0];
    memset(v, 0, sizeof *v);
    s->ram = ram;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_ram_size = 1 << 20;
    s->voice_fault = 0;
    s->voice_fault_address = 0;
    scsp_set_interleaved_mixer(s, route);
    s->ring_cursor = 62;
    s->RINGBUF[63] = s->RINGBUF[0] = (int16_t)tap;
    v->u.data[0] = control;
    v->u.data[2] = 3;
    v->u.data[3] = 8;
    v->u.data[5] = 0x4000;
    v->u.data[7] = modulate ? 0xf042 : 0;
    v->active = 1;
    v->Backwards = backwards;
    v->sample_base = base;
    v->cur_addr = cursor;
    v->step = step;
    v->Prev = -1234;
    out[0] = (uint32_t)advance_voice_sample(s, v);
    out[1] = v->cur_addr;
    out[2] = v->Backwards;
    out[3] = v->active;
    out[4] = (uint16_t)v->Prev;
    out[5] = v->EG.state;
    out[6] = v->u.data[0];
    out[7] = s->voice_fault;
    out[8] = s->voice_fault_address;
}

int scsp_loop_trace(uint8_t *ram, unsigned control, unsigned start, unsigned end,
                    uint32_t cursor, uint32_t step, unsigned backwards,
                    unsigned dispatch, unsigned frames, uint32_t *rows)
{
    scsp *s = calloc(1, sizeof *s);
    if (!s) return 0;
    s->ram = ram;
    s->voice_ram_address = SCSP_SOUND_RAM_ADDRESS;
    s->voice_ram_size = 1 << 20;
    slot_t *slot = &s->Slots[0];
    slot->EG.state = RELEASE;
    scsp_write16(s, 2, 0x4000, 0xffff);
    scsp_write16(s, 4, start, 0xffff);
    scsp_write16(s, 6, end, 0xffff);
    scsp_write16(s, 0xc, 0x300, 0xffff);
    scsp_write16(s, 0, control, 0xffff);
    slot->cur_addr = cursor;
    slot->step = step;
    slot->Prev = -1234;
    slot->Backwards = backwards;
    if (dispatch & 8) {
        scsp_write16(s, 0x12, 1u << 5, 0xffff);
        s->PSCALES[1][128] = 256; /* Zero waveform, unity pitch gain. */
    }
    for (unsigned i = 0; i < frames; ++i) {
        int32_t pcm = slot->active ? advance_voice_sample(s, slot) : 0;
        *rows++ = (uint16_t)pcm;
        *rows++ = slot->cur_addr;
        *rows++ = slot->Backwards;
        *rows++ = slot->active;
        *rows++ = (uint16_t)slot->Prev;
        *rows++ = slot->u.data[0];
    }
    int success = !s->voice_fault;
    free(s);
    return success;
}
#endif
static unsigned pending;
void scsp_dma_cpu_probe(uint32_t *out) {
    scsp *s=calloc(1,sizeof *s);uint8_t ram[4096]={0};
    if(!s){out[0]=0xffffffffu;return;}
    s->ram=ram;s->ram_mask=sizeof ram-1;ram[0x100]=0x22;ram[0x101]=0x11;
    s->DSP.context.COEF[0]=0x369a;
    scsp_write16(s,0x412,0x100,0xffff);
    scsp_write16(s,0x414,0x700,0xffff);
    scsp_write16(s,0x416,0x1002,0xffff);
    out[0]=(uint16_t)s->DSP.context.COEF[0];
    for(unsigned i=0;i<3;i++)out[i+1]=s->u.data[0x12/2+i];
    /* Independent inherited chip-internal interface remains functional. */
    w16(s,0x412,0x100);w16(s,0x414,0x700);w16(s,0x416,0x1002);
    out[4]=(uint16_t)s->DSP.context.COEF[0];
    w16(s,0x412,0x102);w16(s,0x414,0x700);w16(s,0x416,0x3002);
    out[5]=read_word(s,0x102);out[6]=s->u.data[0x16/2];
    free(s);
}
static void observe_irq(void *user,int level,int asserted) {
    (void)user;
    if(asserted)pending=(unsigned)level;
    else if(pending==(unsigned)level)pending=0;
}
int scsp_control_probe(unsigned op,const uint32_t *in,const uint8_t *fifo,uint32_t *out) {
    scsp *s=calloc(1,sizeof *s);if(!s)return 0;
    s->master = 1;
    memcpy(s->MidiStack,fifo,128);s->MidiR=(uint8_t)in[0];s->MidiW=(uint8_t)in[1];s->MidiCount=(uint8_t)in[2];
    s->cpu_irq_level=(uint8_t)in[3];pending=in[3];s->irq=observe_irq;
    s->u.data[0x20/2]=(uint16_t)in[4];s->u.data[0x1e/2]=(uint16_t)in[5];
    s->IrqTimA=in[6];s->IrqTimBC=in[7];s->IrqMidi=in[8];
    s->u.data[2]=(uint16_t)in[9];s->u.data[4]=(uint16_t)in[10];
    for(unsigned i=0;i<3;i++){s->TimCnt[i]=in[14+i];s->TimExpired[i]=(uint8_t)in[17+i];s->u.data[12+i]=(uint16_t)in[20+i];}
    for(unsigned i=0;i<32;i++)s->Slots[i].cur_addr=in[24+i];
    s->u.data[0x22/2]=(uint16_t)in[56];unsigned value=0;
    switch(op) {
    case 0:scsp_midi_in(s,(uint8_t)in[12]);break;
    case 1:value=in[13]==1?scsp_cpu_read8(s,0x400+in[11]):scsp_cpu_read16(s,0x400+in[11]);break;
    case 2:CheckPendingIRQ(s);break;
    case 3: /* Isolated configured callback 004aeac0, distinct from the live autovector. */
        scsp_cpu_ack_irq(s);CheckPendingIRQ(s);break;
    case 4:scsp_clock_tick(s);break;
    case 5:case 6:UpdateReg(s,(int)in[11]);break;
    case 7:
        scsp_write16(s,0x400+in[11],
            (uint16_t)(in[12]<<(in[13]==1 && !(in[11]&1)?8:0)),
            in[13]==2?0xffff:(in[11]&1?0xff:0xff00));break;
    case 8: {
        for(unsigned slot=0;slot<32;slot++) {
            for(unsigned i=0;i<16;i++)s->Slots[slot].u.data[i]=
                (uint16_t)(((2*i+slot*7)&255)|(((2*i+1+slot*7)&255)<<8));
            slot_t *v = &s->Slots[slot];
            v->active_high = 0xc7;
            v->EG = (eg_t){.volume=0x18800, .state=DECAY2, .AR=101, .D1R=23, .D2R=17,
                           .RR=5, .DL=12, .EGHOLD=32};
            v->Prev = -4521;
            v->slot = slot;
            v->cached_tl_gain = 2899;
            v->cached_left_gain = 8211;
            v->cached_right_gain = 16384;
            LFO_ComputeStep(s,&v->PLFO,0,2,7,0);
            LFO_ComputeStep(s,&v->ALFO,0,3,4,1);
            v->PLFO.phase=0x9876; v->ALFO.phase=0xabc1;
            v->PLFO.phase_step=38; v->ALFO.phase_step=51;
            s->Slots[slot].active=1;
            s->Slots[slot].sample_base=0x12345 + slot;
            s->Slots[slot].step=0x13579bdfu - slot;
            s->Slots[slot].Backwards=slot & 1;
        }
        for(unsigned i=0;i<128;i++)s->RINGBUF[i]=(int16_t)(2*i|((2*i+1)<<8));
        memcpy(s->DSP.context.COEF, s->RINGBUF + 76, 104);
        memcpy(&s->ring_cursor, s->RINGBUF + 64, 4);
        memcpy(&s->master, s->RINGBUF + 68, 4);
        memcpy(&s->voice_ram_address, s->RINGBUF + 66, 4);
        memcpy(&s->DSP.context.ram_address, s->RINGBUF + 70, 4);
        memcpy(&s->DSP.context.RBP, s->RINGBUF + 72, 4);
        memcpy(&s->DSP.context.RBL, s->RINGBUF + 74, 4);
        scsp_cpu_observation observed={0};
#ifdef SCSP_A68K_BIND_TEST
        if(!a68k_scsp_bind_pages(bound_data,bound_writes,s)){free(s);return 0;}
        a68k_host_state host={0,in[59],1};a68k_read_result result;
        out[78]=(uint32_t)a68k_read_live(bound_data,A68K_DATA_SPACE,0x100000+in[57],in[58],&result,&host);
        if(out[78])observed=(scsp_cpu_observation){result.value,result.edx,host.control_flags};
#else
        out[78]=(uint32_t)scsp_cpu_read_observed(s,0x100000+in[57],in[58],in[59],&observed);
#endif
        value=observed.eax;out[76]=observed.edx;out[77]=observed.flags;break;
    }
    case 9: case 10: case 11: {
        if (op == 11) scsp_cpu_write_ring(s, 0x688, 2, 0x100);
        memcpy(s->cpu_midi_output, fifo, 128);
        s->cpu_midi_cursor = in[63] & 127;
        s->cpu_midi_count = (uint8_t)in[63];
        s->u.data[1]=(uint16_t)in[60];
        s->DSP.context.RBP=in[61];
        s->DSP.context.RBL=in[62];
#ifdef SCSP_A68K_BIND_TEST
        bound_data[0].native_base=0x12345678;bound_writes[0x110].native_base=0x87654321;
        if(!a68k_scsp_bind_pages(bound_data,bound_writes,s) ||
           bound_data[0].native_base!=0x12345678 || bound_writes[0x110].native_base!=0x87654321) {free(s);return 0;}
        a68k_host_state host={0,in[59],1};
        if(op!=10)out[77]=(uint32_t)a68k_write_observed(bound_writes,0x100400+in[11],in[13],in[12],&host);
        else {host=a68k_scsp_ack(s,6,in[59]);out[77]=host.valid;}
        value=out[77]?host.eax:0;out[76]=out[77]?host.control_flags:0;
#else
        scsp_cpu_completion completion={0};
        out[77]=op!=10?scsp_cpu_write_observed(s,0x100400+in[11],in[13],in[12],in[59],&completion):
            scsp_cpu_ack_observed(s,in[59],&completion);
        value=completion.eax;out[76]=completion.flags;
#endif
        out[78]=s->DSP.context.RBP;
        out[79]=s->DSP.context.RBL;
        memcpy(out + 80, s->cpu_midi_output, 128);
        out[112] = s->cpu_midi_cursor;
        out[113] = s->cpu_midi_count;
        break;
    }
    default:free(s);return 0;
    }
    out[0]=value;out[1]=s->MidiR;out[2]=s->MidiW;out[3]=s->MidiCount;
    out[4]=pending;out[5]=s->u.data[0x20/2];out[6]=s->u.data[2];out[7]=s->u.data[4];
    for(unsigned i=0;i<3;i++){out[8+i]=s->TimCnt[i];out[11+i]=s->TimExpired[i];out[14+i]=s->u.data[12+i];}
    memcpy(out+17,s->MidiStack,128);
    for(unsigned i=0;i<24;i++)out[49+i]=s->u.data[i];
    out[73]=s->IrqTimA;out[74]=s->IrqTimBC;out[75]=s->IrqMidi;
    free(s);return 1;
}
