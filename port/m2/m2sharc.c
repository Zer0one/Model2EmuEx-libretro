#include "m2sharc.h"
#include "m2board.h"
#include "../sharc/sharc_device.h"
#include "../sharc/sharc_upload.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct m2_sharc_binding {
    m2_sharc_device device; /* First: bus callbacks receive &device. */
    m2_board *board;
    uint32_t input[35],output[35];
    m2_sharc_write native_write;
    size_t allocation_bytes;
    bool single_word_fifo_upload;
    /* Snapshot of the upload that produced the current predecode. Guest
     * writes to program RAM deliberately do not update this metadata. */
    uint8_t decoded_source[0x40000];
};
static void copy_fifo_to_native(uint32_t dst[35],const tgp_fifo *src) {
    memcpy(dst,src->buf,128);dst[32]=src->rd;dst[33]=src->wr;dst[34]=(uint32_t)src->free;
}
static void copy_fifo_to_board(tgp_fifo *dst,const uint32_t src[35]) {
    memcpy(dst->buf,src,128);dst->rd=src[32];dst->wr=src[33];dst->free=(int32_t)src[34];
}
static void pull(m2_sharc_binding *binding) {
    m2_sharc_host *h=&binding->device.host;tgp *t=&binding->board->tgp;
    h->program_control=t->prog_upload_ctrl;h->program_offset=t->prog_upload_off;
    h->data_control=t->data_upload_ctrl;h->data_offset=t->data_upload_off;
    h->shared_write=t->ext_ptr;h->reg_801008=t->reg_801008_read;h->reg_803008=t->reg_803008;
}
static void push(m2_sharc_binding *binding) {
    m2_sharc_host *h=&binding->device.host;tgp *t=&binding->board->tgp;
    t->prog_upload_ctrl=h->program_control;t->prog_upload_off=h->program_offset;
    t->data_upload_ctrl=h->data_control;t->data_upload_off=h->data_offset;
    t->ext_ptr=h->shared_write;t->reg_801008_read=h->reg_801008;t->reg_803008=h->reg_803008;
    copy_fifo_to_board(&t->in,binding->input);copy_fifo_to_board(&t->out,binding->output);
}
static void failure(void *opaque,uint32_t entry,uint32_t record) {
    m2_sharc_binding *b=opaque;
    fprintf(stderr,"SHARC reconstruction failure: handler %08x record %08x PC %08x\n",entry,record,b->device.core.execution.state[2]);
    abort(); /* Explicit failure in opt-in reconstruction builds, never a NOP. */
}
static void diagnostic(void *opaque,const char *format,uint32_t pc) {
    (void)opaque;fprintf(stderr,format,pc);fputc('\n',stderr);
}
static void release(void *opaque,uint32_t *allocation,uint32_t token) {
    m2_sharc_binding *b=opaque;
    (void)token;free(allocation);b->allocation_bytes=0;
}
static uint32_t *allocate(void *opaque,uint32_t bytes,uint32_t *token) {
    uint32_t *p=malloc(bytes?bytes:1);
    if(!p)failure(opaque,0x4bf610,0);
    ((m2_sharc_binding *)opaque)->allocation_bytes=bytes;
    *token=0x74000000u;return p;
}
static void render(void *opaque) {
    /* Rendering is already driven by m2pipe/m2geo at its existing frame point.
     * This callback is never invoked by the i960 port mapping installed here. */
    failure(opaque,0x4c6460,0);
}
static void write(void *opaque,uint32_t address,uint32_t value) {
    m2_sharc_binding *b=opaque;
    b->native_write(&b->device,address,value);
    if(address>>16==0x140)memset(b->board->bufram_dirty,0xff,sizeof b->board->bufram_dirty);
}
m2_sharc_binding *m2sharc_create(m2_board *b) {
    m2_sharc_binding *p=calloc(1,sizeof *p);
    if(!p)return NULL;
    const char *name=b->game->name;
    p->single_word_fifo_upload=!strcmp(name,"powsled") || !strcmp(name,"powsledr")
        || !strcmp(name,"powsledm");
    p->board=b;p->device.board.ram0=b->tgp_prog;p->device.board.ram1=b->coproram;
    p->device.board.shared=b->bufram;p->device.board.rom=b->rom.ptr[2];
    p->device.board.input_fifo=p->input;p->device.board.output_fifo=p->output;
    p->device.host.data=b->tgp_data;p->device.core.selected_state=0x10edc30;
    p->device.fp.control=0x37f;p->device.opaque=p;
    p->device.diagnostic=diagnostic;p->device.failure=failure;p->device.render=render;
    p->device.memory=(m2_sharc_program_memory){p,release,allocate};
    m2_sharc_device_bind(&p->device,0x10edc30,0x72000000);
    p->native_write=p->device.bus.write;p->device.bus.write=write;
    return p;
}
void m2sharc_destroy(m2_sharc_binding *b) {
    if(!b)return;
    free(b->device.core.program.allocation);free(b);
}
void m2sharc_debug(const m2_sharc_binding *b,char *text,size_t size) {
    const m2_sharc_execution *s=&b->device.core.execution;
    snprintf(text,size,"pc %04x stop %u astat %08x record %08x | FIFO free in %u out %u",
        s->state[2],s->stop,s->state[0x240/4],s->current_record,b->input[34],b->output[34]);
}
static uint64_t hash_bytes(uint64_t hash,const void *data,size_t bytes) {
    const unsigned char *p=data;
    while(bytes--)hash=(hash^*p++)*UINT64_C(1099511628211);
    return hash;
}
uint64_t m2sharc_hash(const m2_sharc_binding *b) {
    uint64_t h=UINT64_C(1469598103934665603);
    const m2_sharc_device *d=&b->device;
#define HASH(value) h=hash_bytes(h,&(value),sizeof(value))
    HASH(d->core.execution);HASH(d->core.source_binding);HASH(d->core.source_next);
    HASH(d->core.selected_state);HASH(d->core.program.count);
    HASH(d->event_queue);HASH(d->fp.control);HASH(d->fp.status);
    HASH(b->input);HASH(b->output);
#undef HASH
    h=hash_bytes(h,b->board->tgp_prog,0x40000);
    h=hash_bytes(h,b->board->coproram,0x20000);
    h=hash_bytes(h,b->board->bufram,0x80000);
    h=hash_bytes(h,b->board->tgp_data,0x40000);
    return h;
}
void m2sharc_reset(m2_board *b) {
    m2_sharc_binding *p=b->sharc;
    pull(p);copy_fifo_to_native(p->input,&b->tgp.in);copy_fifo_to_native(p->output,&b->tgp.out);
    m2_sharc_device_power_on(&p->device,b->game->name,0);push(p);
    memcpy(p->decoded_source,b->tgp_prog,p->device.core.program.count*6u);
}
uint32_t m2sharc_access(m2_board *b,uint32_t entry,uint32_t address,uint32_t value) {
    uint32_t result=0;m2_sharc_binding *p=b->sharc;
    pull(p);
    /* Power Sled is absent from ElSemi's catalogue. Its FIFO upload uses one
     * word per host write, as verified against SM2. Keep ElSemi's 16-bit
     * fall-through everywhere else, including normal FIFO writes. */
    if(p->single_word_fifo_upload && entry==0x4c6310
       && address-0x884000u<0x4000u && (p->device.host.program_control&0x80000000u))
        entry=0x4c6220;
    if(!m2_sharc_device_host_access(&p->device,entry,address,value,&result))failure(p,entry,0);
    push(p);
    if(entry==0x4c5eb0)memset(b->bufram_dirty,0xff,sizeof b->bufram_dirty);
    return result;
}
static void program_complete(void *opaque) {
    m2_sharc_device *d=opaque;
    m2_sharc_binding *p=d->opaque;
    m2_sharc_device_upload_complete(d);
    if(d->core.program.count>sizeof(p->decoded_source)/6)failure(p,0x4bf610,0);
    memcpy(p->decoded_source,d->board.ram0,d->core.program.count*6u);
}
static void data_complete(void *opaque) {
    uint32_t unused;
    /* Native Model 2B driver entry 16 is the literal RET at 004c5ea0. */
    m2_sharc_device_host_access(opaque,0x4c5ea0,0,0,&unused);
}
void m2sharc_upload_write(m2_board *b,uint32_t address,uint32_t value) {
    m2_sharc_binding *p=b->sharc;
    pull(p);
    m2_sharc_upload_control(&p->device.host,&b->tgp.reg_98000c,address,value,
        &p->device,program_complete,data_complete);
    push(p);
}

/* M12-style complete archive around the original 004bc0d0/004bc0f0 CPU
 * callbacks. Explicitly includes the session context their Windows caller
 * keeps alive. No host allocation address, callback or board pointer is serialized. */
void m2sharc_state_archive(m2_sharc_binding *b,m2_state *a) {
    m2_sharc_device *d=&b->device;
    m2_sharc_execution s=d->core.execution;
    m2_sharc_board_configuration config=d->configuration;
    m2_sharc_fp_state fp=d->fp;
    uint32_t tag=0x31524853u; /* SHR1 */
    uint32_t count=d->core.program.count,queue[8];
    uint32_t selected=d->core.selected_state,source=d->core.source_binding,next=d->core.source_next;
    uint32_t token=d->core.program.allocation_token,base=d->core.program.program_base;
    uint32_t end=d->core.program.current_record;
    memcpy(queue,d->event_queue,sizeof queue);
    if(a->failed)return;
#define V(value) m2_state_value(a,&(value),sizeof(value))
    V(tag);V(count);V(token);V(base);V(end);V(selected);V(source);V(next);
    /* Save uses the recovered original copy callback, with its exact block
     * length. The execution tail is additional frontend continuation state. */
    if(a->mode==M2_STATE_SAVE)m2_sharc_state_save(s.state,d->core.execution.state,sizeof s.state);
    V(s);V(config);V(fp);V(queue);
#undef V
    if(a->failed)return;
    const uint32_t expected_token=0x74000000u,expected_base=expected_token-0xd80000u;
    uint32_t current_offset=s.current_record-token,saved_offset=s.saved_record-token;
    if(tag!=0x31524853u || count>sizeof(b->decoded_source)/6 || token!=expected_token
        || base!=expected_base || end!=token+count*108u || s.program_base!=base
        || selected!=d->fixed_state || source!=d->source_token || next!=source+24
        || (s.active_base && s.active_base!=base)
        || s.read_binding!=0x4c6100 || s.write_binding!=0x4c6020
        || (s.active_read && s.active_read!=s.read_binding)
        || (s.active_write && s.active_write!=s.write_binding)
        || current_offset%108 || current_offset>count*108u
        || saved_offset%108 || saved_offset>count*108u
        || s.saved_record!=base+s.state[2]*108u
        || s.event_count>8 || s.in_delay || s.state[0x10/4]>30 || s.state[0xd4/4]>6
        || config.astat!=s.state[0x240/4] || config.stop!=s.stop
        || config.selected_state!=selected || config.read_binding!=s.read_binding
        || config.write_binding!=s.write_binding) {a->failed=1;return;}
    for(uint32_t i=0;i<s.event_count;i++)
        if(queue[i]!=0x4bce10 && queue[i]!=0x4bce60 && queue[i]!=0x4bceb0 && queue[i]!=0x4bcf00)
            {a->failed=1;return;}
    size_t source_bytes=(size_t)count*6,record_bytes=(size_t)count*108;
    if(a->pos>a->size || source_bytes+record_bytes>a->size-a->pos) {a->failed=1;return;}
    const uint8_t *upload=a->mode==M2_STATE_SAVE?b->decoded_source:a->data+a->pos;
    const void *records=a->mode==M2_STATE_SAVE?(const void *)d->core.program.allocation:a->data+a->pos+source_bytes;
    if(!m2_sharc_program_matches(upload,records,count,selected,d->fixed_state,token)) {a->failed=1;return;}
    if(a->mode==M2_STATE_LOAD) {
        /* Allocate before replacing the old allocation; failure leaves this
         * device intact and the enclosing M12 loader rolls back the board. */
        uint32_t *allocation=d->core.program.allocation;
        if(record_bytes>b->allocation_bytes)allocation=malloc(record_bytes);
        if(!allocation){a->failed=1;return;}
        memcpy(allocation,records,record_bytes);
        memcpy(b->decoded_source,upload,source_bytes);
        uint32_t native[172]={0};native[0x2ac/4]=base;
        m2_sharc_state_restore(native,s.state,sizeof s.state);
        memcpy(s.state,native,sizeof s.state);s.saved_record=native[0x2a8/4];
        if(allocation!=d->core.program.allocation) {
            free(d->core.program.allocation);b->allocation_bytes=record_bytes;
        }
        /* Never shrink on restore: a later payload failure can restore the
         * preceding archive without needing another allocation for rollback. */
        d->core.program=(m2_sharc_program){allocation,token,count,base,end};
        d->core.execution=s;d->configuration=config;d->fp=fp;
        d->core.selected_state=selected;d->core.source_binding=source;d->core.source_next=next;
        memcpy(d->event_queue,queue,sizeof queue);
        m2_sharc_device_bind(d,d->fixed_state,d->source_token);
        b->native_write=d->bus.write;d->bus.write=write;
        /* Board RAM and scalar FIFO archives have already been loaded. */
        pull(b);copy_fifo_to_native(b->input,&b->board->tgp.in);copy_fifo_to_native(b->output,&b->board->tgp.out);
    } else if(a->mode==M2_STATE_SAVE) {
        memcpy(a->data+a->pos,upload,source_bytes);
        memcpy(a->data+a->pos+source_bytes,records,record_bytes);
    }
    a->pos+=source_bytes+record_bytes;
}
