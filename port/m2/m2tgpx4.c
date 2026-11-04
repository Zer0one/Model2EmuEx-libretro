#include "m2tgpx4.h"
#include "m2board.h"
#include "../tgpx4/tgpx4_device.h"
#include "../tgpx4/tgpx4_host.h"
#include "../tgpx4/tgpx4_motion.h"
#include "../tgpx4/tgpx4_protection.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Research-only binding. All values below are original x86 tokens, never host
 * addresses. The virtual stack preserves CALL/prologue FLAGS independently of
 * ARM64/x86-64 host ABI. CPU and renderer logic remain frontend-neutral. */
enum { STATE=0x10edef0, INPUT=0x74000000, OUTPUT=0x74000100,
       PROGRAM=0x75000000, SOURCE=0x72000000, SHARED=0x76000000, ROM=0x78000000, STACK=0x710ffff0 };
struct m2_tgpx4_binding {
    m2_tgpx4_device device;
    m2_tgpx4_host host;
    m2_board *board;
    uint8_t cpu[0x2164], scratch[0x150], geometry[0x200], configuration[0x30];
    uint32_t delay, crt_sse2, xoffset, yoffset;
    uint32_t motion_phase, motion_countdown;
    /* Native response buffer ends at the distinct 005aa870 upload global. */
    uint8_t protection_response[0x100];
    uint32_t protection_index, protection_selector, protection_toggle;
    uint32_t *allocation;
    size_t allocation_bytes;
    uint32_t decoded_count;
    uint8_t decoded_source[0x40000];
};
static uint32_t load(const uint8_t *p,unsigned bytes) {
    uint32_t v=0;for(unsigned i=0;i<bytes;i++)v|=(uint32_t)p[i]<<(i*8);return v;
}
static void store(uint8_t *p,uint32_t value,unsigned bytes) {
    for(unsigned i=0;i<bytes;i++)p[i]=(uint8_t)(value>>(i*8));
}
static void failure(struct m2_tgpx4_binding *p,const char *kind,uint32_t address) {
    fprintf(stderr,"TGPX4 reconstruction %s at %08x, PC %08x record %08x\n",
        kind,address,load(p->cpu+0x114,4),load(p->cpu+0x144,4));
    abort(); /* No silent unmapped-memory, unknown-opcode or geometry fallback. */
}
static uint8_t *region(struct m2_tgpx4_binding *p,uint32_t at,unsigned bytes) {
#define REGION(token,ptr,len) if(at>=(uint32_t)(token) && (uint64_t)at+bytes<=(uint64_t)(token)+(len))return (uint8_t *)(ptr)+(at-(token))
    REGION(0x5aa770,p->protection_response,sizeof p->protection_response);
    REGION(STATE,p->cpu,sizeof p->cpu);
    REGION(0x1048100,p->scratch,sizeof p->scratch);
    REGION(0x573300,p->geometry,sizeof p->geometry);
    REGION(0x10ed950,p->configuration,sizeof p->configuration);
    REGION(SOURCE,p->board->tgp_prog,0x40000);
    REGION(SHARED,p->board->bufram,0x80000);
#undef REGION
    return NULL;
}
static uint32_t *words(struct m2_tgpx4_binding *p,uint32_t at,size_t *length,uint32_t *offset) {
    uint32_t base=0;uint32_t *result=NULL;
    if(at>=PROGRAM && (uint64_t)at<PROGRAM+p->allocation_bytes) {
        base=PROGRAM;*length=p->allocation_bytes;result=p->allocation+0x2c/4;
    } else if(at>=INPUT && at<INPUT+sizeof(tgp_fifo)) {
        base=INPUT;*length=sizeof(tgp_fifo);result=(uint32_t *)&p->board->tgp.in;
    } else if(at>=OUTPUT && at<OUTPUT+sizeof(tgp_fifo)) {
        base=OUTPUT;*length=sizeof(tgp_fifo);result=(uint32_t *)&p->board->tgp.out;
    } else {
        *length=4;
        switch(at&~3u) {
        case 0x10ed908:base=0x10ed908;result=&p->protection_index;break;
        case 0x10ed90c:base=0x10ed90c;result=&p->protection_selector;break;
        case 0x10f01b0:base=0x10f01b0;result=&p->protection_toggle;break;
        case 0x10ed9a4:base=0x10ed9a4;result=&p->delay;break;
        case 0x10f1fec:base=0x10f1fec;result=&p->crt_sse2;break;
        case 0xdcec58:base=0xdcec58;result=&p->xoffset;break;
        case 0x5aeb90:base=0x5aeb90;result=&p->yoffset;break;
        }
    }
    *offset=at-base;return result;
}
static uint32_t read(void *opaque,uint32_t at,unsigned bits) {
    struct m2_tgpx4_binding *p=opaque;unsigned bytes=bits/8;
    if(bits!=8 && bits!=16 && bits!=32)failure(p,"read width",at);
    uint8_t *raw=region(p,at,bytes);if(raw)return load(raw,bytes);
    if(at>=ROM && (uint64_t)at+bytes<=(uint64_t)ROM+p->board->rom.size[2])return load(p->board->rom.ptr[2]+(at-ROM),bytes);
    uint32_t constant;
    if(m2_tgpx4_protection_constant(at,bits,&constant))return constant;
    if(bits==32) {
        if(at==0x5aa724)return INPUT;
        if(at==0x5aa738)return OUTPUT;
        if(at==0x5aa87c)return SOURCE;
        if(at==0x5aa700)return SHARED;
        if(at==0x5aa8dc)return ROM;
    }
    size_t size;uint32_t offset;uint32_t *w=words(p,at,&size,&offset);
    if(!w || (uint64_t)offset+bytes>size)failure(p,"unmapped read",at);
    uint32_t value=0;
    for(unsigned i=0;i<bytes;i++)value|=((w[(offset+i)/4]>>(((offset+i)&3)*8))&255u)<<(i*8);
    return value;
}
static void write(void *opaque,uint32_t at,uint32_t value,unsigned bits) {
    struct m2_tgpx4_binding *p=opaque;unsigned bytes=bits/8;
    if(bits!=8 && bits!=16 && bits!=32)failure(p,"write width",at);
    uint8_t *raw=region(p,at,bytes);if(raw){
        store(raw,value,bytes);
        if(at>=SHARED && at<SHARED+0x80000)memset(p->board->bufram_dirty,0xff,sizeof p->board->bufram_dirty);
        return;
    }
    size_t size;uint32_t offset;uint32_t *w=words(p,at,&size,&offset);
    if(!w || (uint64_t)offset+bytes>size)failure(p,"unmapped write",at);
    for(unsigned i=0;i<bytes;i++) {
        unsigned shift=((offset+i)&3)*8;
        w[(offset+i)/4]=(w[(offset+i)/4]&~(255u<<shift))|(((value>>(i*8))&255u)<<shift);
    }
}
static void external(void *opaque,uint32_t entry,m2_tgpx4_execution_registers *r) {
    struct m2_tgpx4_binding *p=opaque;
    (void)r;
    failure(p,"callback",entry);
}
static void release(void *opaque,uint32_t token) {
    struct m2_tgpx4_binding *p=opaque;
    if(token!=PROGRAM)failure(p,"allocation token",token);
    free(p->allocation);p->allocation=NULL;p->allocation_bytes=0;
}
static uint32_t *allocate(void *opaque,uint32_t bytes,uint32_t *token) {
    struct m2_tgpx4_binding *p=opaque;
    p->allocation=malloc((size_t)bytes+0x2c);
    if(!p->allocation)failure(p,"allocation",bytes);
    p->allocation_bytes=bytes;*token=PROGRAM;
    /* Keep native malloc contents, including the accessible rewrite prefix.
     * Class 3 does not initialize a wrapper in the original either. */
    return p->allocation+0x2c/4;
}
static void run(void *opaque) {
    struct m2_tgpx4_binding *p=opaque;
    store(p->cpu+0x2150,p->host.stopped,4);
    m2_tgpx4_device_run(&p->device,STACK,false);
    p->host.stopped=load(p->cpu+0x2150,4);
}
static void complete(void *opaque,uint32_t bytes) {
    struct m2_tgpx4_binding *p=opaque;
    if(bytes>0x40000)failure(p,"program upload boundary",bytes);
    m2_tgpx4_device_load(&p->device,p->board->tgp_prog,bytes);
    p->decoded_count=bytes/8;
    memcpy(p->decoded_source,p->board->tgp_prog,(size_t)p->decoded_count*8);
}
static void pull(struct m2_tgpx4_binding *p) {
    tgp *t=&p->board->tgp;m2_tgpx4_host *h=&p->host;
    h->upload_control=t->prog_upload_ctrl;h->upload_offset=t->prog_upload_off;
    h->data_control=t->data_upload_ctrl;h->data_offset=t->data_upload_off;
    h->shared_write=t->ext_ptr;h->shared_read=t->reg_801008_read;h->reg_803008=t->reg_803008;
    h->stopped=load(p->cpu+0x2150,4);
}
static void push(struct m2_tgpx4_binding *p) {
    tgp *t=&p->board->tgp;m2_tgpx4_host *h=&p->host;
    t->prog_upload_ctrl=h->upload_control;t->prog_upload_off=h->upload_offset;
    t->data_upload_ctrl=h->data_control;t->data_upload_off=h->data_offset;
    t->ext_ptr=h->shared_write;t->reg_801008_read=h->shared_read;t->reg_803008=h->reg_803008;
}
struct m2_tgpx4_binding *m2tgpx4_create(m2_board *board) {
    struct m2_tgpx4_binding *p=calloc(1,sizeof *p);if(!p)return NULL;
    p->board=board;p->device.machine=(m2_tgpx4_execution_bus){p,read,write,external};
    p->device.memory=(m2_tgpx4_program_memory){p,release,allocate};
    p->device.registers.fp_control=0x37f;
    p->host=(m2_tgpx4_host){.program=board->tgp_prog,.input=&board->tgp.in,.output=&board->tgp.out,
        .opaque=p,.run=run,.shared=board->bufram,.data=board->tgp_data,.external=board->rom.ptr[2],
        .decode_uploaded_program=complete};
    m2_tgpx4_device_bind(&p->device);return p;
}
void m2tgpx4_destroy(struct m2_tgpx4_binding *p) {
    if(p){free(p->allocation);free(p);}
}
void m2tgpx4_reset(m2_board *b) {
    struct m2_tgpx4_binding *p=b->tgpx4;pull(p);
    /* The original House of the Dead program is MAME hotdo. Its native
     * driver identity was hotd; keep the original per-game configuration. */
    const char *native_name=!strcmp(b->game->name,"hotdo")?"hotd":b->game->name;
    m2_tgpx4_device_initialize(&p->device,native_name);
    p->decoded_count=0x100/8;memcpy(p->decoded_source,b->tgp_prog,0x100);push(p);
}
uint32_t m2tgpx4_center_mode(const m2_board *b) {
    return b->tgpx4 ? load(b->tgpx4->configuration+0x28,4) : b->tgpx4_geometry_center_mode;
}
int m2tgpx4_dual_matrix(const m2_board *b) {
    /* 010ed95a, set by the original Top Skater driver initialization. */
    return b->tgpx4 ? b->tgpx4->configuration[0x0a] != 0 : b->tgpx4_geometry_dual;
}
void m2tgpx4_input_step(m2_board *b) {
    /* Recover only the device handshake following native input conversion.
     * Frontend control profiles still own analog/digital input mapping.
     * The original input_fn also selects this path for Sega Water Ski.
     * Phase/countdown are native globals: game command FF resets the phase;
     * a machine reset must not invent an additional counter reset. */
    if(b->game->input_fn!=0x4c9dc0)return;
    struct m2_tgpx4_binding *p=b->tgpx4;
    m2_tgpx4_motion s={b->reg_574cf0,p->motion_phase,p->motion_countdown,b->port[2]};
    m2_tgpx4_motion_step(&s);
    b->reg_574cf0=s.command;b->port[2]=s.reply;
    p->motion_phase=s.phase;p->motion_countdown=s.countdown;
}
uint32_t m2tgpx4_access(m2_board *b,uint32_t entry,uint32_t address,uint32_t value) {
    struct m2_tgpx4_binding *p=b->tgpx4;pull(p);uint32_t result=0;
    if((entry==0x4c5ac0 || entry==0x4c5a30) && (p->host.upload_control&0x80000000u)
        && (uint64_t)p->host.upload_offset+(entry==0x4c5a30?2:4)>0x40000)
        failure(p,"program upload boundary",address);
    if(entry==0x4c58d0 && (address&0xfffff000u)==0x804000 && (p->host.data_control&0x80000000u)
        && (uint64_t)p->host.data_offset+4>0x40000)failure(p,"data upload boundary",address);
    if(!m2_tgpx4_host_access(&p->host,entry,address,value,&result))failure(p,"host callback",entry);
    push(p);if(entry==0x4c58d0)memset(b->bufram_dirty,0xff,sizeof b->bufram_dirty);
    return result;
}
uint32_t m2tgpx4_protection_access(m2_board *b,uint32_t address,uint32_t value,unsigned bits,int writing) {
    if(writing) {
        m2_tgpx4_protection_write(&b->tgpx4->device.machine,address,value,bits);
        return 0;
    }
    return m2_tgpx4_protection_read(&b->tgpx4->device.machine,address,bits);
}
void m2tgpx4_upload_write(m2_board *b,uint32_t address,uint32_t value) {
    struct m2_tgpx4_binding *p=b->tgpx4;pull(p);m2_tgpx4_host *h=&p->host;
    /* Shared native 004c79c0 control ordering, also recovered for SHARC. */
    if(address==0x980000) {
        if((h->upload_control^value)==0x80000000u) {
            if(value&0x80000000u)h->upload_offset=0;
            else complete(p,h->upload_offset);
        }
        h->upload_control=value;
    } else if(address==0x980008) {
        if((h->data_control^value)==0x80000000u && (value&0x80000000u))h->data_offset=0;
        h->data_control=value; /* Native Model 2C entry 16: RET at 004c5a60. */
    } else if(address==0x98000c)b->tgp.reg_98000c=value;
    push(p);
}
void m2tgpx4_debug(const struct m2_tgpx4_binding *p,char *text,size_t size) {
    snprintf(text,size,"pc %08x record %08x stopped %u | FIFO free in %d out %d",
        load(p->cpu+0x114,4),load(p->cpu+0x144,4),load(p->cpu+0x2150,4),
        p->board->tgp.in.free,p->board->tgp.out.free);
}

/* M12/M2A complete-snapshot policy around the recovered CPU copy callbacks.
 * No Windows .STA compatibility: decoded program and continuation are explicit. */
void m2tgpx4_state_archive(struct m2_tgpx4_binding *p,m2_state *a) {
    uint32_t tag=0x33584754u,count=p->decoded_count; /* TGX3: native protection continuation */
    uint8_t cpu[sizeof p->cpu],scratch[sizeof p->scratch];
    uint8_t geometry[sizeof p->geometry],configuration[sizeof p->configuration];
    uint32_t delay=p->delay,crt=p->crt_sse2,x=p->xoffset,y=p->yoffset;
    uint32_t motion_phase=p->motion_phase,motion_countdown=p->motion_countdown;
    uint8_t protection_response[sizeof p->protection_response];
    memcpy(protection_response,p->protection_response,sizeof protection_response);
    uint32_t protection_index=p->protection_index,protection_selector=p->protection_selector;
    uint32_t protection_toggle=p->protection_toggle;
    m2_tgpx4_execution_registers registers=p->device.registers;
    if(a->failed)return;
    memcpy(cpu,p->cpu,sizeof cpu);memcpy(scratch,p->scratch,sizeof scratch);
    memcpy(geometry,p->geometry,sizeof geometry);memcpy(configuration,p->configuration,sizeof configuration);
    if(a->mode==M2_STATE_SAVE)m2_tgpx4_state_save(cpu,p->cpu,M2_TGPX4_STATE_BYTES);
#define V(value) m2_state_value(a,&(value),sizeof(value))
    V(tag);V(count);V(cpu);V(scratch);V(geometry);V(configuration);
    V(delay);V(crt);V(x);V(y);V(registers);
    V(motion_phase);V(motion_countdown);
    V(protection_response);V(protection_index);V(protection_selector);V(protection_toggle);
#undef V
    if(a->failed)return;
    const uint32_t pc=load(cpu+0x114,4),record=load(cpu+0x144,4);
    const uint32_t active_record=load(scratch+0x14c,4);
    if(tag!=0x33584754u || motion_phase>3 || motion_countdown>9
        || protection_index>128 || protection_selector>0xffff || protection_toggle>1
        || count>sizeof p->decoded_source/8 || pc>count
        || load(cpu+0x140,4)!=PROGRAM || record!=PROGRAM+pc*0x94u
        || (active_record && (active_record-PROGRAM>count*0x94u || (active_record-PROGRAM)%0x94u))
        || load(cpu+0x148,4)!=0x4c5a70 || load(cpu+0x14c,4)!=0x4c5a90
        || load(cpu+0x2154,4)!=OUTPUT || load(cpu+0x2158,4)!=INPUT
        || load(cpu+0x2150,4)>1 || delay || crt>1
        || load(cpu+0xa0,4)>=24 || load(cpu+0xa4,4)>=24 || load(cpu+0x124,4)>6
        || load(scratch+0x140,4)>16 || load(scratch+0x148,4)>16
        || (registers.fp_control&0x3f)!=0x3f) {a->failed=1;return;}
    const uint32_t offsets[]={0xe0,0xe8,0xec,0xf0,0xf4,0xf8,0xfc,0x144};
    const uint32_t tokens[]={INPUT,OUTPUT,0x4c5a70,PROGRAM,STATE,0x10ee040,0x10ef040,0x4c5a90};
    for(unsigned i=0;i<sizeof offsets/sizeof offsets[0];i++) {
        uint32_t v=load(scratch+offsets[i],4);
        if(v && v!=tokens[i]){a->failed=1;return;}
    }
    for(uint32_t i=0;i<load(scratch+0x148,4);i++) {
        uint32_t op=load(scratch+0x100+i*4,4);
        if(op!=0x4b3c80 && op!=0x4b4160 && op!=0x4b4170 && op!=0x4b4190){a->failed=1;return;}
    }
    for(uint32_t i=0;i<load(scratch+0x140,4);i++) {
        uint32_t at=load(scratch+0x20+i*12,4),op=load(scratch+0x28+i*12,4);
        if(at<STATE || at>STATE+0x13c || (at&3)
            || (op!=0x4b4510 && op!=0x4b4520 && op!=0x4b4530)){a->failed=1;return;}
    }
    const size_t source_bytes=(size_t)count*8,record_bytes=(size_t)count*0x94;
    if(a->pos>a->size || source_bytes+record_bytes>a->size-a->pos){a->failed=1;return;}
    const uint8_t *source=a->mode==M2_STATE_SAVE?p->decoded_source:a->data+a->pos;
    const void *records=a->mode==M2_STATE_SAVE?(const void *)(p->allocation+0x2c/4):a->data+a->pos+source_bytes;
    if(!m2_tgpx4_program_matches(source,records,count,STATE,PROGRAM)){a->failed=1;return;}
    if(a->mode==M2_STATE_LOAD) {
        uint32_t *allocation=p->allocation;
        if(record_bytes>p->allocation_bytes)allocation=malloc(record_bytes+0x2c);
        if(!allocation){a->failed=1;return;}
        memcpy(allocation+0x2c/4,records,record_bytes);
        memcpy(p->decoded_source,source,source_bytes);
        uint8_t native[0x148]={0};store(native+0x140,PROGRAM,4);
        m2_tgpx4_state_restore(native,cpu,M2_TGPX4_STATE_BYTES);
        memcpy(cpu,native,sizeof native);
        if(allocation!=p->allocation){free(p->allocation);p->allocation_bytes=record_bytes;}
        p->allocation=allocation;p->decoded_count=count;
        memcpy(p->cpu,cpu,sizeof cpu);memcpy(p->scratch,scratch,sizeof scratch);
        memcpy(p->geometry,geometry,sizeof geometry);memcpy(p->configuration,configuration,sizeof configuration);
        p->delay=delay;p->crt_sse2=crt;p->xoffset=x;p->yoffset=y;p->device.registers=registers;
        p->motion_phase=motion_phase;p->motion_countdown=motion_countdown;
        memcpy(p->protection_response,protection_response,sizeof protection_response);
        p->protection_index=protection_index;p->protection_selector=protection_selector;
        p->protection_toggle=protection_toggle;
        m2_tgpx4_device_bind(&p->device);pull(p);
    } else if(a->mode==M2_STATE_SAVE) {
        memcpy(a->data+a->pos,source,source_bytes);
        memcpy(a->data+a->pos+source_bytes,records,record_bytes);
    }
    a->pos+=source_bytes+record_bytes;
}
