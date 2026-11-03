#include "sharc_runtime.h"
#include "sharc_mode.h"
#include "sharc_transfer.h"
#include <stdlib.h>

static bool load_record(m2_sharc_runtime *r,uint32_t token,uint32_t out[27]) {
    unsigned i;
    for(i=0;i<27;i++) {
        const uint32_t *word = r->word(r->opaque,token+4u*i);
        if(!word)return false;
        out[i]=*word;
    }
    return true;
}
static m2_sharc_compute_context compute_context(m2_sharc_runtime *r) {
    m2_sharc_execution *s=r->execution;
    m2_sharc_compute_context c={r->opaque,r->word,r->diagnostic,
        &s->state[0x240/4],&s->state[2],&s->state[0x18/4],&s->stop,
        &s->current_record,r->fp};
    return c;
}
static void fail(m2_sharc_runtime *r,uint32_t entry) {
    r->failure(r->opaque,entry,r->execution->current_record);
    abort(); /* Enforce the documented non-returning failure boundary. */
}
static void dispatch(void *opaque,m2_sharc_execution *s,uint32_t record,uint32_t flags) {
    m2_sharc_runtime *r=opaque;
    (void)s;
    if(!m2_sharc_runtime_dispatch(r,flags)) {
        const uint32_t *entry = r->word(r->opaque,record);
        fail(r,entry?*entry:0);
    }
}
static void event(void *opaque,m2_sharc_execution *s,uint32_t index,uint32_t flags) {
    m2_sharc_runtime *r=opaque;
    (void)s;(void)flags;
    if(!m2_sharc_runtime_event(r,index))fail(r,r->event_queue[index]);
}
static m2_sharc_execution_hooks hooks(m2_sharc_runtime *r) {
    m2_sharc_execution_hooks h={dispatch,event,r};return h;
}
typedef struct {m2_sharc_runtime *runtime;uint32_t handler,condition;m2_sharc_control_record record;} control_frame;
static const m2_sharc_control_record *control_record(void *opaque,uint32_t token) {
    control_frame *f=opaque;uint32_t raw[27];
    if(!load_record(f->runtime,token,raw))fail(f->runtime,f->handler);
    /* A delayed instruction can redirect the active record. The native outer
     * handler still interprets its fields with the ORIGINAL handler layout;
     * it does not dispatch or validate the replacement record's entry word. */
    raw[0]=f->handler;
    /* The condition was already evaluated before the slots; a replacement
     * record's unused condition word need not even contain a function token. */
    raw[2]=f->condition;
    if(!m2_sharc_bind_control(raw,f->runtime->word,f->runtime->opaque,&f->record))
        fail(f->runtime,raw[0]);
    return &f->record;
}
bool m2_sharc_runtime_dispatch(m2_sharc_runtime *r,uint32_t flags) {
    m2_sharc_execution *s=r->execution;
    uint32_t raw[27],offset,old_offset,result;
    m2_sharc_compute_context c=compute_context(r);
    m2_sharc_operation_hooks operation=m2_sharc_compute_hooks(&c);
    m2_sharc_memory_record memory;
    if(!load_record(r,s->current_record,raw))return false;
    switch(raw[0]) {
    case 0x4bca40:return true;
    case 0x4bcb50:case 0x4bcb10:return m2_sharc_dispatch_compute(&c,raw[0]==0x4bcb10);
    case 0x4bd550:case 0x4bd5d0:
        return m2_sharc_state_helper(raw[0],s,r->word(r->opaque,raw[9]),raw[7],0,
            r->event_queue,r->bus,&result);
    case 0x4bca50:case 0x4bca80:case 0x4bcab0:case 0x4bcac0:case 0x4bd540:
    case 0x4bd650:case 0x4bd680:case 0x4bd6a0:case 0x4bd6c0:case 0x4bd6e0:
        if(!m2_sharc_bind_memory(raw,r->word,r->opaque,&memory))return false;
        return m2_sharc_transfer(raw[0],&memory,r->bus,c.astat);
    case 0x4bd810:case 0x4bd890:case 0x4bd910:case 0x4bd990:
    case 0x4bddb0:case 0x4bde20:case 0x4bdea0:case 0x4bdf20:
    case 0x4bdad0:case 0x4bdb10:case 0x4bdb60:case 0x4bdbb0:case 0x4bdc00:
    case 0x4bdc60:case 0x4bdcb0:case 0x4bdd00:case 0x4bdd50:
        if(!m2_sharc_bind_memory(raw,r->word,r->opaque,&memory))return false;
        old_offset=offset=s->current_record-s->active_base;
        if(!m2_sharc_dispatch_memory_ex(raw[0],&memory,r->bus,flags,*c.loop_count,
            c.astat,c.stop,c.pc,&offset,&operation))return false;
        if(offset!=old_offset)s->current_record=s->active_base+offset;
        return true;
    case 0x4bcad0:case 0x4bd700:case 0x4bd750:case 0x4bd7b0:
    case 0x4bda10:case 0x4bda60:case 0x4be2a0:case 0x4be310:
    case 0x4be380:case 0x4be460:case 0x4be540:case 0x4be610:
    case 0x4be6f0:case 0x4be750:case 0x4be7c0: {
        control_frame f={r,raw[0],raw[2],{0}};
        m2_sharc_execution_hooks h=hooks(r);
        /* Preflight the initial record so direct dispatch can report failure.
         * Subsequent delayed records must obey the native valid-record contract. */
        if(!m2_sharc_bind_control(raw,r->word,r->opaque,&f.record))return false;
        return m2_sharc_dispatch_control_ex(raw[0],s,&h,control_record,&f,&operation);
    }
    default:return false;
    }
}
bool m2_sharc_runtime_event(m2_sharc_runtime *r,uint32_t index) {
    uint32_t entry=r->event_queue[index],result;
    switch(entry) {
    case 0x4bce10:case 0x4bce60:case 0x4bceb0:case 0x4bcf00:
        return m2_sharc_state_helper(entry,r->execution,0,0,0,r->event_queue,r->bus,&result);
    default:return false;
    }
}
void m2_sharc_runtime_run_bounded(m2_sharc_runtime *r) {
    m2_sharc_execution_hooks h=hooks(r);
    /* FLDCW 003f: reserved bit 6 reads back as one. Existing status survives. */
    r->fp->control=0x7f;
    m2_sharc_run_bounded(r->execution,&h);
}
void m2_sharc_runtime_run_continuous(m2_sharc_runtime *r) {
    m2_sharc_execution_hooks h=hooks(r);
    if(r->execution->stop==0)r->fp->control=0x7f;
    m2_sharc_run_continuous(r->execution,&h);
}
