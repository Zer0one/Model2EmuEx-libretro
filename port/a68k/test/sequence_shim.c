/* ROM-free execution-chain fixture, deliberately not a production executor. */
#include "../a68k.h"
#include <string.h>

enum { MAX_STEPS=128, RECORD_WORDS=41 };
static uint32_t write_value,write_address,write_count,write_events[MAX_STEPS][2];
static uint32_t callback_eax,callback_control_xor;
static unsigned live_reads,script_count;
static uint32_t read_script[8];
void a68k_probe_set_read_script(const uint32_t *values,unsigned count) {
    script_count=count<8?count:8;memcpy(read_script,values,script_count*sizeof(uint32_t));
}
static uint32_t read_value,read_edx,read_control_xor,read_count,read_events[MAX_STEPS][4];
static a68k_cpu *read_cpu;
static unsigned live_binding,live_irq,live_reset,reset_mutate,reset_count;
static uint32_t reset_eax,reset_xor;
void a68k_probe_set_reset(uint32_t eax,uint32_t control_xor,unsigned mutate) {
    live_reset=1;reset_eax=eax;reset_xor=control_xor;reset_mutate=mutate;
}
unsigned a68k_probe_reset_count(void){return reset_count;}
static a68k_host_state reset_observed(void *u,uint32_t control) {
    a68k_cpu *s=u;++reset_count;
    if(reset_mutate) {
        s->fetch_page->data[2]=0x71;s->fetch_page->data[3]=0x4e;
        s->r.pc+=2;s->r.flags=0xa43;
    }
    return (a68k_host_state){reset_eax,control^reset_xor,1};
}
static uint32_t ack_vector,ack_control_xor;
static uint8_t irq_costs[256];
void a68k_probe_set_irq(uint32_t vector,uint32_t control_xor,const uint8_t *costs) {
    live_irq=1;ack_vector=vector;ack_control_xor=control_xor;memcpy(irq_costs,costs,256);
}
static a68k_host_state ack_observed(void *u,unsigned level,uint32_t control) {
    (void)u;(void)level;return (a68k_host_state){ack_vector,control^ack_control_xor,1};
}
void a68k_probe_enable_binding(void){live_binding=1;}
static a68k_host_state bind_observed(void *u,uint32_t pc,uint32_t control) {
    a68k_cpu *s=u;s->r.fetch_bank=pc>>16;
    /* This fixture maps one bounded code buffer across the same native page.
     * 004b30a0 returns the descriptor offset, not a portable pointer. */
    return (a68k_host_state){(pc>>12)*16,control,1};
}
void a68k_probe_set_reads(uint32_t value,uint32_t edx,uint32_t control_xor) {
    live_reads=1;read_value=value;read_edx=edx;read_control_xor=control_xor;
}
static a68k_read_observation load_observed(void *user,uint32_t address,uint32_t control) {
    unsigned kind=(unsigned)(uintptr_t)user;
    if(read_count<MAX_STEPS) {
        read_events[read_count][0]=address;read_events[read_count][1]=kind;
        read_events[read_count][2]=read_cpu->r.pc;read_events[read_count][3]=read_cpu->r.flags;
    }
    uint32_t value=read_count<script_count?read_script[read_count]:read_value;
    ++read_count;
    return (a68k_read_observation){{value,read_edx},control^read_control_xor,1};
}
unsigned a68k_probe_get_reads(uint32_t *out) {
    if(read_count>MAX_STEPS)return MAX_STEPS+1;
    memcpy(out,read_events,read_count*sizeof read_events[0]);return read_count;
}
static void store8(void *user,uint32_t address,uint32_t value) {
    (void)user;write_value=value;write_address=address;
    if(write_count<MAX_STEPS){write_events[write_count][0]=address;write_events[write_count][1]=value;}
    ++write_count;
}
static a68k_host_state store8_observed(void *user,uint32_t address,uint32_t value,uint32_t control) {
    store8(user,address,value);return (a68k_host_state){callback_eax,control^callback_control_xor,1};
}
static void record(uint32_t *out,const a68k_cpu *s,const a68k_host_state *host,unsigned boundary) {
    memcpy(out,&s->r,sizeof s->r);out[33]=s->pc;out[34]=s->flags;out[35]=s->cycles;
    out[36]=host->eax;out[37]=host->control_flags&~0x8d5u;
    out[38]=host->valid;out[39]=boundary;out[40]=s->entry_eax_valid;
}
/* input: context[33], cycles, caller EAX, caller EFLAGS; output: header[4],
 * entry snapshots and final snapshot. Last optional Scc performs a synthetic
 * callback; its outgoing scratch is deliberately not claimed or continued. */
int a68k_probe_sequence(const uint32_t *input,const uint16_t *code,const uint32_t *targets,
                        unsigned count,unsigned terminal_scc,uint32_t *output) {
    if(count>MAX_STEPS || !count)return 0;
    a68k_cpu s={0};memcpy(&s.r,input,sizeof s.r);s.cycles=input[33];
    a68k_host_state host={input[34],input[35],1};
    uint8_t instructions[MAX_STEPS*2];
    for(unsigned i=0;i<count;i++){instructions[2*i]=(uint8_t)code[i];instructions[2*i+1]=(uint8_t)(code[i]>>8);}
    a68k_page page={0};page.data=instructions;page.size=count*2;page.guest_base=s.r.pc;s.fetch_page=&page;
    static a68k_page writes[A68K_PAGE_COUNT];
    static unsigned ready;
    if(!ready){for(unsigned i=0;i<A68K_PAGE_COUNT;i++)for(unsigned w=0;w<3;w++){writes[i].write[w]=store8;writes[i].write_observed[w]=store8_observed;}ready=1;}
    s.write_pages=writes;
    write_count=write_value=write_address=0;callback_eax=input[36];callback_control_xor=input[37];
    a68k_boundary result=a68k_begin_observed(&s,&host);unsigned n=0;
    while(result==A68K_FETCH && n<count && s.pc!=page.guest_base+count*2) {
        uint32_t offset=s.pc-page.guest_base;
        if((offset&1) || offset/2>=count)return 0;
        unsigned slot=offset/2;
        record(output+4+n*RECORD_WORDS,&s,&host,result);
        if(terminal_scc && slot+1==count) {
            result=a68k_dispatch_target(&s,targets[slot],code[slot],host.control_flags);
            host.valid=0;s.entry_eax_valid=0;
        } else result=a68k_step_observed(&s,targets[slot],code[slot],&host);
        ++n;
    }
    record(output+4+n*RECORD_WORDS,&s,&host,result);
    if(write_count>MAX_STEPS)return 0;
    memcpy(output+4+(count+1)*RECORD_WORDS,write_events,write_count*sizeof write_events[0]);
    output[0]=n;output[1]=write_count;output[2]=write_address;output[3]=write_value;
    return 1;
}

/* Refusals must precede every mutation, not merely return an error code. */
unsigned a68k_probe_sequence_guards(void) {
    a68k_cpu s={0},before; a68k_host_state h={0x12345678,0x202,1},prior;
    unsigned n=0;
    s.r.irq=7;s.r.sr_high=0x27;s.cycles=100;before=s;prior=h;
    if(a68k_begin_observed(&s,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    s.r.irq=0;before=s;
    if(a68k_step_observed(&s,0xffffffffu,0x4e70,&h)!=A68K_UNRECOVERED || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    h.valid=0;prior=h;
    if(a68k_begin_observed(&s,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    if(a68k_step_observed(&s,0x478438,0x7001,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    h.valid=1;h.control_flags=0x302;prior=h;
    if(a68k_begin_observed(&s,&h)!=A68K_UNRECOVERED || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    h.control_flags=0x202;s.flags=0x10000;before=s;prior=h;
    if(a68k_step_observed(&s,0x476220,0x5cc0,&h)!=A68K_UNRECOVERED || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++n;
    h.control_flags=0x200;prior=h;
    if(a68k_begin_observed(&s,&h)!=A68K_UNRECOVERED || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    return n+1;
}

/* Original write wrapper outputs and memory, independent of CPU handlers.
 * Modes: 0 callback, 1 direct, 2 missing observed callback, 3 short direct,
 * 4 direct without base provenance, 5 invalid callback observation. */
static a68k_host_state observed_result;
static unsigned ordinary_writes;
static void ordinary_write(void *u,uint32_t a,uint32_t v){(void)u;(void)a;(void)v;++ordinary_writes;}
static a68k_host_state observed_write(void *u,uint32_t a,uint32_t v,uint32_t control) {
    (void)control;store8(u,a,v);return observed_result;
}
int a68k_probe_observed_write(const uint32_t *input,uint8_t *memory,uint32_t *output) {
    unsigned width=input[0],mode=input[1];uint32_t address=input[2]&0xffffffu;
    static a68k_page map[A68K_PAGE_COUNT];
    a68k_page page={0};page.guest_base=address&~4095u;page.size=mode==3?0:8192;
    page.native_base=input[4];page.native_base_valid=mode!=4;
    if(mode && mode!=2 && mode!=5)page.data=memory;
    for(unsigned i=0;i<3;i++){page.write[i]=ordinary_write;if(mode!=2)page.write_observed[i]=observed_write;}
    map[address>>12]=page;
    a68k_host_state host={0xa5c3e791,input[7],1};
    observed_result=(a68k_host_state){input[5],input[6],mode!=5};
    write_count=ordinary_writes=0;
    int ok=a68k_write_observed(map,input[2],width,input[3],&host);
    output[0]=ok;output[1]=host.eax;output[2]=host.control_flags;output[3]=host.valid;
    output[4]=write_count;output[5]=write_address;output[6]=write_value;output[7]=ordinary_writes;
    return 1;
}

/* Targeted execution-loop fixture. The final NOP sentinel is fetched only by
 * the native oracle; portable research pauses happen before that fetch. */
int a68k_probe_loop(const uint32_t *input,const uint16_t *code,unsigned word_count,
                    unsigned instruction_count,unsigned chunk,uint32_t *output) {
    if(!word_count || word_count>MAX_STEPS || !chunk)return 0;
    a68k_cpu s={0};memcpy(&s.r,input,sizeof s.r);s.cycles=input[33];
    a68k_host_state host={input[34],input[35],1};
    uint8_t instructions[MAX_STEPS*2];
    for(unsigned i=0;i<word_count;i++){instructions[2*i]=(uint8_t)code[i];instructions[2*i+1]=(uint8_t)(code[i]>>8);}
    a68k_page page={0};page.data=instructions;page.size=word_count*2;page.guest_base=s.r.pc;s.fetch_page=&page;
    static a68k_page writes[A68K_PAGE_COUNT];
    for(unsigned i=0;i<A68K_PAGE_COUNT;i++)for(unsigned w=0;w<3;w++)writes[i].write_observed[w]=store8_observed;
    s.write_pages=writes;
    static a68k_page reads[2][A68K_PAGE_COUNT];read_count=0;read_cpu=&s;
    if(live_binding){s.bind_observed=bind_observed;s.user=&s;s.address_mask=0xffffffu;}
    if(live_irq){s.ack_observed=ack_observed;s.exception_cycles=irq_costs;}
    reset_count=0;if(live_reset)s.reset_observed=reset_observed;
    if(live_reads) {
        for(unsigned kind=0;kind<2;kind++)for(unsigned i=0;i<A68K_PAGE_COUNT;i++) {
            reads[kind][i].user=(void *)(uintptr_t)kind;
            for(unsigned w=0;w<3;w++)reads[kind][i].read_live[w]=load_observed;
        }
        s.data_pages=reads[0];s.read_pages=reads[1];
    }
    uint32_t table[A68K_OPCODE_COUNT];if(!a68k_init_dispatch(table,A68K_OPCODE_COUNT))return 0;
    write_count=write_value=write_address=0;callback_eax=input[36];callback_control_xor=input[37];
    a68k_boundary result=a68k_begin_observed(&s,&host);unsigned total=0;
    while(result==A68K_FETCH && total<instruction_count) {
        unsigned n=0,limit=instruction_count-total;if(limit>chunk)limit=chunk;
        result=a68k_run_live(&s,table,&host,limit,&n);total+=n;
        if(result==A68K_FETCH && n!=limit)return 0;
    }
    output[0]=total;output[1]=write_count;record(output+2,&s,&host,result);
    if(write_count>MAX_STEPS)return 0;
    memcpy(output+2+RECORD_WORDS,write_events,write_count*sizeof write_events[0]);
    return 1;
}

unsigned a68k_probe_loop_guards(void) {
    uint32_t table[A68K_OPCODE_COUNT];unsigned n=99,passed=0;
    if(a68k_init_dispatch(NULL,A68K_OPCODE_COUNT))return 0;++passed;
    memset(table,0x5a,sizeof table);
    if(a68k_init_dispatch(table,A68K_OPCODE_COUNT-1))return 0;
    for(unsigned i=0;i<A68K_OPCODE_COUNT;i++)if(table[i]!=0x5a5a5a5a)return 0;
    ++passed;if(!a68k_init_dispatch(table,A68K_OPCODE_COUNT))return 0;
    a68k_cpu s={0},before; a68k_host_state h={0x12345678,0x202,1},prior=h;
    s.pc=0x1000;s.flags=0x602;s.r.pc=0x9000;s.r.flags=0x202;s.cycles=100;before=s;
    if(a68k_run_live(&s,table,&h,0,&n)!=A68K_FETCH || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++passed;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++passed;
    if(a68k_run_live(&s,NULL,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s))return 0;
    ++passed;
    if(a68k_run_live(&s,table,&h,1,NULL)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s))return 0;
    ++passed;
    table[0xa000]=0xffffffffu; /* Unknown token guard; Line A itself is now connected. */
    uint8_t code[]={0x00,0xa0};a68k_page page={0};page.data=code;page.size=2;page.guest_base=s.pc;s.fetch_page=&page;before=s;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_UNRECOVERED || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    ++passed;
    page.size=1;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s))return 0;
    ++passed;
    h.valid=0;prior=h;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    return passed+1;
}

/* Direct/callback read bridge only. A missing live observation must never
 * fall back to an older value-only or EAX/EDX callback. */
static a68k_read_observation read_observation;
static unsigned read_calls,old_read_calls;
static a68k_read_observation probe_read_live(void *u,uint32_t address,uint32_t control) {
    (void)u;(void)address;(void)control;++read_calls;return read_observation;
}
static uint32_t probe_old_read(void *u,uint32_t address) {
    (void)u;(void)address;++old_read_calls;return 0;
}
static a68k_read_result probe_old_observed(void *u,uint32_t address) {
    (void)u;(void)address;++old_read_calls;return (a68k_read_result){0,0};
}
int a68k_probe_read_live(const uint32_t *input,uint8_t *memory,uint32_t *out) {
    unsigned width=input[0],mode=input[3];uint32_t address=input[2]&0xffffffu;
    static a68k_page map[A68K_PAGE_COUNT];a68k_page page={0};
    page.data=mode==1 || mode==3 || mode==4?memory:NULL;
    page.guest_base=address&~4095u;page.size=mode==3?0:8192;
    page.native_base=0x72000000u-page.guest_base;page.native_base_valid=mode!=4;
    for(unsigned i=0;i<3;i++) {
        page.read[i]=probe_old_read;page.read_observed[i]=probe_old_observed;
        if(mode!=2)page.read_live[i]=probe_read_live;
    }
    map[address>>12]=page;
    read_observation=(a68k_read_observation){{input[4],input[5]},input[7]^input[6],mode!=5};
    a68k_host_state host={0xa5c3e791,input[7],1};a68k_read_result result={0x11111111,0x22222222};
    read_calls=old_read_calls=0;
    int ok=a68k_read_live(map,(a68k_read_space)input[1],input[2],width,&result,&host);
    out[0]=ok;out[1]=host.eax;out[2]=host.control_flags;out[3]=host.valid;
    out[4]=result.value;out[5]=result.edx;out[6]=read_calls;out[7]=old_read_calls;return 1;
}
unsigned a68k_probe_read_mapping(void) {
    static a68k_page map[A68K_PAGE_COUNT];a68k_page binding={0};
    for(unsigned i=0;i<3;i++)binding.read_live[i]=probe_read_live;
    unsigned n=0;
    for(unsigned kind=0;kind<3;kind++) {
        if(!a68k_map_pages(map,(a68k_map_kind)kind,0x1000,0x1fff,&binding))return 0;
        for(unsigned i=0;i<3;i++)if(map[1].read_live[i]!=(kind==A68K_MAP_DATA?probe_read_live:NULL))return 0;
        ++n;
    }
    return n;
}
unsigned a68k_probe_jump_guards(void) {
    a68k_cpu s={0},before; a68k_host_state h={0x12345678,0x202,1},prior=h;
    uint32_t table[A68K_OPCODE_COUNT];if(!a68k_init_dispatch(table,A68K_OPCODE_COUNT))return 0;
    s.pc=0x1000;s.flags=0x202;s.cycles=100;s.r.a[0]=0x1003;
    s.user=&s;s.bind_observed=bind_observed;s.address_mask=0xffffff;before=s;
    if(a68k_step_observed(&s,table[0x4ed0],0x4ed0,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    s.r.a[0]=0x1002;s.bind_observed=NULL;before=s;
    if(a68k_step_observed(&s,table[0x4ed0],0x4ed0,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    return 2;
}

/* Pending RESET successor is not a fresh fetch or a native budget boundary. */
unsigned a68k_probe_prefetch_guards(void) {
    uint32_t table[A68K_OPCODE_COUNT];if(!a68k_init_dispatch(table,A68K_OPCODE_COUNT))return 0;
    a68k_cpu s={0},before;a68k_host_state h={0x12345678,0x202,1},prior=h;
    s.pc=0x1000;s.flags=0x202;s.cycles=100;s.prefetched_valid=1;s.prefetched_opcode=0x4e71;
    before=s;unsigned n=99;
    if(a68k_run_live(&s,table,&h,0,&n)!=A68K_FETCH || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    s.prefetched_opcode=65536;before=s;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    s.prefetched_opcode=0x4e7a;before=s;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_BINDING_ERROR || n || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    s.prefetched_opcode=0x4e71;s.cycles=0;
    if(a68k_run_live(&s,table,&h,1,&n)!=A68K_EXIT || n!=1 || s.prefetched_valid || s.pc!=0x1002 || s.cycles!=0xfffffffcu || h.valid)return 0;
    memset(&s,0,sizeof s);s.r.sr_high=0x27;s.r.opaque24[1]=1;h=prior;before=s;
    if(a68k_step_observed(&s,table[0x4e70],0x4e70,&h)!=A68K_BINDING_ERROR || memcmp(&s,&before,sizeof s) || memcmp(&h,&prior,sizeof h))return 0;
    return 5;
}
