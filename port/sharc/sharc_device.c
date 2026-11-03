#include "sharc_device.h"
static uint32_t *word(void *opaque,uint32_t token) {
    m2_sharc_device *d=opaque;
    uint32_t offset=token-d->fixed_state;
    if(!(offset&3u) && offset<sizeof(d->core.execution.state))return d->core.execution.state+offset/4;
    offset=token-d->core.program.allocation_token;
    if(!(offset&3u) && offset<(uint64_t)d->core.program.count*108u)return d->core.program.allocation+offset/4;
    return 0; /* Unused record fields can contain non-address allocator data. */
}
static void mirror_configuration(m2_sharc_device *d) {
    m2_sharc_execution *s=&d->core.execution;
    d->configuration.astat=s->state[0x240/4];d->configuration.stop=s->stop;
    d->configuration.selected_state=d->core.selected_state;
    d->configuration.read_binding=s->read_binding;d->configuration.write_binding=s->write_binding;
}
static uint32_t read(void *opaque,uint32_t address) {
    m2_sharc_device *d=opaque;uint32_t result;
    d->board.active_state=d->core.selected_state;d->board.stop=d->core.execution.stop;
    result=m2_sharc_board_read(&d->board,address);
    d->core.selected_state=d->board.active_state;d->core.execution.stop=d->board.stop;
    return result;
}
static void write(void *opaque,uint32_t address,uint32_t value) {
    m2_sharc_device *d=opaque;
    d->board.active_state=d->core.selected_state;d->board.stop=d->core.execution.stop;
    m2_sharc_board_write(&d->board,address,value);
    d->core.selected_state=d->board.active_state;d->core.execution.stop=d->board.stop;
}
static void diagnostic(void *opaque,const char *format,uint32_t pc) {
    m2_sharc_device *d=opaque;d->diagnostic(d->opaque,format,pc);
}
static void failure(void *opaque,uint32_t entry,uint32_t record) {
    m2_sharc_device *d=opaque;d->failure(d->opaque,entry,record);
}
static void run(void *opaque){m2_sharc_device_run_continuous(opaque);}
static void render(void *opaque){m2_sharc_device *d=opaque;d->render(d->opaque);}
static void reset(void *opaque,uint32_t bytes) {
    m2_sharc_device *d=opaque;
    m2_sharc_reset(&d->core,d->board.ram0,d->source_token,bytes,d->fixed_state,&d->memory,d->registration);
    /* Board initialization reads reset's ASTAT, not the pre-reset snapshot. */
    mirror_configuration(d);
}
void m2_sharc_device_bind(m2_sharc_device *d,uint32_t fixed_state,uint32_t source_token) {
    m2_sharc_execution *s=&d->core.execution;
    d->fixed_state=fixed_state;d->source_token=source_token;
    d->board.astat=&s->state[0x240/4];d->board.fixed_state=fixed_state;
    d->host.program=d->board.ram0;d->host.shared=d->board.shared;
    d->host.input=d->board.input_fifo;d->host.output=d->board.output_fifo;
    d->host.astat=d->board.astat;d->host.stop=&s->stop;d->host.selected=&d->core.selected_state;
    d->host.fixed=fixed_state;d->host.opaque=d;d->host.run=run;d->host.render=render;
    d->bus.read=read;d->bus.write=write;d->bus.opaque=d;
    d->runtime.execution=s;d->runtime.fp=&d->fp;d->runtime.word=word;d->runtime.opaque=d;
    d->runtime.diagnostic=diagnostic;d->runtime.bus=&d->bus;d->runtime.event_queue=d->event_queue;d->runtime.failure=failure;
}
void m2_sharc_device_power_on(m2_sharc_device *d,const char *game,const m2_sharc_registration *registration) {
    d->registration=registration;mirror_configuration(d);
    m2_sharc_board_initialize(&d->configuration,game,d->fixed_state,&d->fp,reset,d);
    d->registration=0;
    d->core.execution.state[0x240/4]=d->configuration.astat;
    d->core.execution.stop=d->configuration.stop;d->core.selected_state=d->configuration.selected_state;
    d->core.execution.read_binding=d->configuration.read_binding;d->core.execution.write_binding=d->configuration.write_binding;
}
void m2_sharc_device_upload_complete(m2_sharc_device *d) {
    m2_sharc_upload_complete(&d->core,d->board.ram0,d->source_token,d->host.program_offset,d->fixed_state,&d->memory);
    mirror_configuration(d);
}
void m2_sharc_device_run_bounded(m2_sharc_device *d,uint32_t budget) {
    d->core.execution.budget=budget;m2_sharc_runtime_run_bounded(&d->runtime);mirror_configuration(d);
}
void m2_sharc_device_run_continuous(m2_sharc_device *d) {
    m2_sharc_runtime_run_continuous(&d->runtime);mirror_configuration(d);
}
bool m2_sharc_device_host_access(m2_sharc_device *d,uint32_t entry,uint32_t address,uint32_t value,uint32_t *result) {
    bool ok=m2_sharc_host_access(entry,&d->host,address,value,result);mirror_configuration(d);return ok;
}
