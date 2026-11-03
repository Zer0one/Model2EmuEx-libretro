#include "sharc_execute.h"
#include "sharc_condition.h"
#include "sharc_flow.h"

#define W(s, offset) ((s)->state[(uint32_t)(offset) / 4u])

static uint32_t test_flags(uint32_t value)
{
    uint32_t flags;
    m2_sharc_flow_flags(M2_SHARC_FLOW_CONTINUOUS_FIRST, value, &flags);
    return flags;
}

static uint32_t compare_flags(uint32_t lhs, uint32_t rhs)
{
    uint32_t value = lhs - rhs;
    return test_flags(value) | (lhs < rhs ? 1u : 0u) |
        (((lhs ^ rhs) & (lhs ^ value) & 0x80000000u) ? 0x800u : 0u);
}

void m2_sharc_events(m2_sharc_execution *s, const m2_sharc_execution_hooks *h)
{
    if (s->event_delay == 0 && s->event_count != 0) {
        uint32_t index = 0, flags = test_flags(s->event_count);
        do {
            h->event(h->opaque, s, index, flags);
            ++index;
            /* Original reloads the live count after every callback. */
            flags = compare_flags(index, s->event_count);
        } while (index < s->event_count);
        s->event_count = 0;
    } else {
        /* Includes delay=0/count=0 -> 0xffffffff. Preserve the original. */
        --s->event_delay;
    }
}

void m2_sharc_delay_slots(m2_sharc_execution *s, const m2_sharc_execution_hooks *h)
{
    uint32_t flags, record = s->current_record;
    m2_sharc_flow_flags(M2_SHARC_FLOW_DELAY, record, &flags);
    s->current_record = record + 0x6cu;
    s->in_delay = 1;
    h->dispatch(h->opaque, s, s->current_record, flags);
    m2_sharc_events(s, h);
    record = s->current_record; /* Events/handlers may have changed it. */
    --s->budget;
    m2_sharc_flow_flags(M2_SHARC_FLOW_DELAY, record, &flags);
    s->current_record = record + 0x6cu;
    h->dispatch(h->opaque, s, s->current_record, flags);
    m2_sharc_events(s, h);
    --s->budget;
    /* Subtract from the CURRENT record, not a saved entry pointer. Stop is
     * deliberately not checked between slots, nor is budget clamped at zero. */
    s->current_record -= 0xd8u;
    s->in_delay = 0;
}

static void prepare(m2_sharc_execution *s)
{
    s->active_read = s->read_binding;
    s->active_write = s->write_binding;
    s->active_base = s->program_base;
    /* 0x460f20 binds ASTAT and writes 16 bits of the x87 control storage.
     * ASTAT is state[0x240/4] in this representation; no host fenv is changed. */
    s->fp_control = (s->fp_control & 0xffff0000u) | 0x3fu;
    s->current_record = s->saved_record;
}

static void run_batch(m2_sharc_execution *s, const m2_sharc_execution_hooks *h,
                       unsigned first_origin)
{
    uint32_t flags;
    prepare(s);
    m2_sharc_flow_flags(first_origin, s->budget, &flags);
    while (s->budget != 0) {
        uint32_t pc, record, descriptor, condition = 0;
        h->dispatch(h->opaque, s, s->current_record, flags);
        m2_sharc_events(s, h);
        descriptor = W(s, 0x14);
        pc = W(s, 8);
        record = s->current_record;
        if (pc == (descriptor & 0xffffffu)) {
            if ((descriptor >> 30) != 0) {
                --W(s, 0x9cu + W(s, 0xd4) * 4u);
                --W(s, 0x18);
                condition = W(s, 0x18) == 0;
            } else {
                m2_sharc_condition(1, (descriptor >> 24) & 31u,
                    W(s, 0x240), W(s, 0x18), &s->stop, &condition);
            }
            if (condition != 0) {
                uint32_t index;
                --W(s, 0xd4);
                index = W(s, 0xd4);
                W(s, 0x18) = W(s, 0x9cu + index * 4u);
                W(s, 0x14) = W(s, 0xb8u + index * 4u);
                index = W(s, 0x10);
                W(s, 0xc) = W(s, 0x20u + index * 4u);
                W(s, 0x10) = index - 1u;
                pc = W(s, 8);
            } else {
                uint32_t target = W(s, 0x20u + W(s, 0x10) * 4u);
                pc = target - 1u;
                W(s, 8) = pc;
                /* This path uses the configured base, not active_base. */
                record = s->program_base + target * 0x6cu - 0x6cu;
            }
        }
        s->current_record = record + 0x6cu;
        W(s, 8) = pc + 1u;
        if (s->stop != 0)
            break; /* Original advances PC/record but does NOT charge budget. */
        m2_sharc_flow_flags(M2_SHARC_FLOW_NEXT, s->budget, &flags);
        --s->budget;
    }
    s->saved_record = s->current_record;
}

void m2_sharc_run_bounded(m2_sharc_execution *s, const m2_sharc_execution_hooks *h)
{
    /* Unlike the continuous entry, an already-set stop does not skip dispatch. */
    run_batch(s, h, M2_SHARC_FLOW_BOUNDED_FIRST);
}

void m2_sharc_run_continuous(m2_sharc_execution *s, const m2_sharc_execution_hooks *h)
{
    if (s->stop != 0)
        return;
    do {
        s->budget = 100000u;
        run_batch(s, h, M2_SHARC_FLOW_CONTINUOUS_FIRST);
    } while (s->stop == 0);
}
