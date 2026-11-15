#include "model1_board.h"
#include "divs_error_policy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct a68k_m1_board {
    a68k_cpu cpu;
    a68k_m1_bus bus;
    a68k_page fetch[A68K_PAGE_COUNT], data[A68K_PAGE_COUNT], writes[A68K_PAGE_COUNT];
    uint32_t dispatch[A68K_OPCODE_COUNT];
    uint8_t costs[256];
    a68k_boundary status;
    a68k_divs_error_policy divs_policy;
    unsigned trace_line;
    int trace;
};

static a68k_host_state bind(void *user,uint32_t pc,uint32_t flags)
{
    a68k_m1_board *b=user;
    return a68k_bind_pc_observed(&b->cpu,pc,flags);
}
static a68k_host_state ack(void *user,unsigned level,uint32_t flags)
{
    a68k_m1_board *b=user;
    if (b->trace) fprintf(stderr,"A68K_IRQ %u %u\n",b->trace_line,level);
    return (a68k_host_state){UINT32_MAX,m1_logic_flags(flags,UINT32_MAX,32),1};
}
static a68k_host_state guest_reset(void *user,uint32_t flags)
{
    (void)user;
    return (a68k_host_state){0,m1_logic_flags(flags,0,32),1};
}

void a68k_m1_free(a68k_m1_board *b)
{
    if (!b) return;
    m2_original_m1_free(b->bus.sound);
    free(b);
}

a68k_m1_board *a68k_m1_create(uint8_t *ram,const uint8_t *program,size_t prog_size,
                               const uint8_t *samples,size_t size,int original_divs)
{
    a68k_m1_board *b=calloc(1,sizeof *b);
    if (!b) return NULL;
    b->trace=getenv("MODEL2EMUEX_SOUND_TRACE")!=NULL;
    b->bus.cpu=&b->cpu;
    b->bus.sound=m2_original_m1_create(samples,size);
    if (!b->bus.sound || !a68k_init_dispatch(b->dispatch,A68K_OPCODE_COUNT) ||
        !a68k_m1_bind_pages(&b->bus,b->fetch,b->data,b->writes,
                            (uint8_t *)program,prog_size,ram,65536)) goto failed;
    b->divs_policy=original_divs ? A68K_DIVS_ORIGINAL : A68K_DIVS_STOP_CONTENT;
    b->cpu.read_pages=b->fetch;
    b->cpu.data_pages=b->data;
    b->cpu.write_pages=b->writes;
    b->cpu.address_mask=0xffffff;
    b->cpu.exception_cycles=b->costs;
    a68k_init_exception_cycles(b->costs);
    b->cpu.user=b;
    b->cpu.bind_observed=bind;
    b->cpu.ack_observed=ack;
    b->cpu.reset_observed=guest_reset;
    b->cpu.r.ack_token=0x4b3090;
    b->cpu.r.opaque24[1]=0x572ab8;
    if (a68k_reset(&b->cpu)==A68K_RETURN) return b;
failed:
    a68k_m1_free(b);
    return NULL;
}

void a68k_m1_reset(a68k_m1_board *b)
{
    /* 004cad8c copies both vector longs into sound RAM on machine reset.
     * It preserves the remaining bytes, the UART and all sound generators. */
    memcpy(b->data[0xf00].data,b->fetch[0].data,8);
    if (!b->status) b->status=a68k_reset(&b->cpu);
}
void a68k_m1_command(a68k_m1_board *b,uint8_t command)
{
    if (b->trace) fprintf(stderr,"A68K_COMMAND %u %u\n",b->trace_line+1,command);
    m2_original_m1_command(b->bus.sound,command);
}
void a68k_m1_scanline(a68k_m1_board *b)
{
    if (b->trace) b->trace_line++;
    if (b->status) return;
    uint32_t eax=A68K_M1_MACHINE;
    for (unsigned tick=0;tick<10;tick++) {
        /* 004cc720 compares the template (zero after initialization) with
         * 0x80. The live CPU can independently be stopped on a guest STOP. */
        a68k_host_state host={eax,0x283,1};
        b->cpu.cycles=79;
        b->cpu.dispatch_sp=0x71008000-40;
        a68k_boundary status=a68k_begin_observed(&b->cpu,&host);
        while (status==A68K_FETCH) {
            unsigned steps;
            status=a68k_run_live(&b->cpu,b->dispatch,&host,256,&steps);
        }
        b->cpu.dispatch_sp=0;
        if (status!=A68K_EXIT) { b->status=status; return; }
        eax=m2_original_m1_tick(b->bus.sound);
    }
    if (m2_original_m1_irq_pending(b->bus.sound)) b->cpu.r.irq=2;
}

int a68k_m1_begin(a68k_m1_board *b,unsigned frames)
{
    return m2_original_m1_begin(b->bus.sound,frames);
}
int a68k_m1_output_frames(a68k_m1_board *b,unsigned frames)
{
    return m2_original_m1_output_frames(b->bus.sound,frames);
}
void a68k_m1_finish(a68k_m1_board *b,int16_t *out,const unsigned gain[4])
{
    m2_original_m1_finish(b->bus.sound,out,gain[1],gain[2],gain[3]);
}
int a68k_m1_error(const a68k_m1_board *b,char *text,size_t size)
{
    const char *reason=m2_original_m1_error(b->bus.sound);
    if (!reason && !b->status) return 0;
    if (b->status==A68K_DIVS_HOST_OVERFLOW)
        a68k_apply_divs_error_policy(&b->cpu,b->divs_policy);
    if (!reason) reason=a68k_fault_message(&b->cpu);
    snprintf(text,size,"%s at Model 1 sound PC %08x (boundary %u)",
             reason ? reason : "Sound CPU stopped", b->cpu.r.pc,(unsigned)b->status);
    return 1;
}
void a68k_m1_archive(a68k_m1_board *b,m2_state *a)
{
    a68k_cpu c=b->cpu;
    uint32_t page=(uint32_t)(c.fetch_page-b->fetch);
    m2_state_value(a,&c.r,sizeof c.r);
#define VALUE(field) m2_state_value(a,&c.field,sizeof c.field)
    VALUE(pc); VALUE(flags); VALUE(cycles); VALUE(illegal_opcode); VALUE(illegal_pc);
    VALUE(prefetched_opcode); VALUE(prefetched_valid); VALUE(entry_eax); VALUE(entry_eax_valid);
#undef VALUE
    m2_state_value(a,&page,sizeof page);
    if (b->status || page>=A68K_PAGE_COUNT || c.prefetched_valid>1 || c.entry_eax_valid>1 ||
        c.prefetched_opcode>0xffff || (c.r.irq&~0x87u)) a->failed=1;
    m2_original_m1_archive(b->bus.sound,a);
    if (!a->failed && a->mode==M2_STATE_LOAD) {
        c.fetch_page=&b->fetch[page];
        b->cpu=c;
    }
}
