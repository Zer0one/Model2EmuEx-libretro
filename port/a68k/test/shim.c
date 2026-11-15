/* ROM-free ABI for the original/portable boundary comparison. Test only. */
#include "../a68k.h"
#include <assert.h>
#include <string.h>

typedef struct {
    a68k_cpu cpu;
    uint32_t events[32][3], count, target, sp, reset_pc, fetch_tag;
    int32_t ack;
    uint32_t bus_value,bus_context[33],write_context[33],written_value;
    uint32_t script[32][3],script_count,script_cursor,script_context[32][33];
    uint32_t script_edx[32];
    unsigned scripted;
    uint32_t reset_flags, bus_edx;
    unsigned reset_mutate;
} fixture;
static fixture f;
static a68k_page pages[A68K_PAGE_COUNT];
static a68k_page data_pages[A68K_PAGE_COUNT];
static uint8_t operand_data[4],destination_data[4];
static a68k_page write_pages[A68K_PAGE_COUNT];
static a68k_page script_pages[A68K_PAGE_COUNT];
static unsigned script_pages_ready;
static void operand_write8(void *,uint32_t,uint32_t);
static void operand_write16(void *,uint32_t,uint32_t);
static void operand_write32(void *,uint32_t,uint32_t);
static uint32_t operand8(void *,uint32_t);
static uint32_t operand16(void *,uint32_t);
static uint32_t operand32(void *,uint32_t);
static a68k_read_result observed16(void *,uint32_t);
static a68k_read_result observed8(void *,uint32_t);
static a68k_read_result observed32(void *,uint32_t);
static uint8_t reset_data[8];
static a68k_page instruction_page;
static uint8_t instruction_data[10];
static void event(unsigned kind,uint32_t address,uint32_t value) {
    assert(f.count<32);f.events[f.count][0]=kind;f.events[f.count][1]=address;
    f.events[f.count++][2]=value;
}
static uint32_t vector_read(void *user,uint32_t address) {
    (void)user;event(0,address,0);return f.target;
}
static uint32_t reset_read(void *user,uint32_t address) {
    (void)user;event(0,address,0);return address==0?f.sp:f.reset_pc;
}
static void stack_word(void *user,uint32_t address,uint32_t value) {(void)user;event(1,address,value&65535);}
static void stack_long(void *user,uint32_t address,uint32_t value) {(void)user;event(2,address,value);}
static void bind(void *user,uint32_t address) {(void)user;event(3,address,0);f.fetch_tag=0x73000000;}
static int32_t ack(void *user,unsigned level) {(void)user;event(4,level,0);return f.ack;}
static void reset_output(void *user) {
    (void)user;event(11,0,0);memcpy(f.bus_context,&f.cpu.r,sizeof f.bus_context);
    if(f.reset_mutate) {
        f.cpu.r.pc=f.reset_pc;f.cpu.r.flags=f.reset_flags;
        /* Overwrite the prefetched instruction as well: RESET must retain it. */
        instruction_data[2]^=255;instruction_data[3]^=255;
    }
}
static void word(uint8_t *p,uint32_t value) {p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);}

/* input: native-prefix words[33], live PC/flags/cycles, opcode or vector,
 * vector target, acknowledge result, reset-direct flag, host control flags.
 * output: prefix[33], live PC/flags/cycles, boundary, fetch tag, event count,
 * then fixed-size event triples. */
int a68k_probe_cpu(unsigned operation,const uint32_t *input,const uint8_t *costs,uint32_t *output) {
    memset(&f,0,sizeof f);memcpy(&f.cpu.r,input,sizeof f.cpu.r);
    f.cpu.pc=input[33];f.cpu.flags=input[34];f.cpu.cycles=input[35];
    f.target=input[37];memcpy(&f.ack,input+38,sizeof f.ack);
    f.cpu.read_pages=pages;f.cpu.exception_cycles=costs;f.cpu.address_mask=0xffffff;
    f.cpu.vector_read=vector_read;f.cpu.stack_word=stack_word;f.cpu.stack_long=stack_long;
    f.cpu.bind=bind;f.cpu.ack=ack;f.fetch_tag=0x73000000;
    if(operation==9) {
        f.cpu.reset_output=reset_output;f.reset_pc=input[44];f.reset_flags=input[45];f.reset_mutate=input[46];
    }
    memset(&instruction_page,0,sizeof instruction_page);
    word(instruction_data,input[36]);word(instruction_data+2,input[42]);word(instruction_data+4,input[43]);
    word(instruction_data+6,input[49]);word(instruction_data+8,input[50]);instruction_page.data=instruction_data;
    instruction_page.size=sizeof instruction_data;instruction_page.guest_base=f.cpu.pc;
    f.cpu.fetch_page=&instruction_page;
    a68k_boundary status;uint8_t *output_data=operand_data;
    if(operation==0) {
        f.sp=input[36];f.reset_pc=input[37];
        unsigned page=f.reset_pc>>12;if(page>=A68K_PAGE_COUNT)return 0;
        memset(&pages[page],0,sizeof pages[page]);
        pages[page].user=(void *)(uintptr_t)0x73800000;
        memset(&pages[0],0,sizeof pages[0]);
        if(input[39]) {
            pages[0].data=reset_data;pages[0].size=sizeof reset_data;
            word(reset_data,f.sp>>16);word(reset_data+2,f.sp);
            word(reset_data+4,f.reset_pc>>16);word(reset_data+6,f.reset_pc);
        } else pages[0].read[2]=reset_read;
        pages[0].user=(void *)(uintptr_t)(input[39]?0x72000000:0);
        status=a68k_reset(&f.cpu);
        if(status==A68K_RETURN)f.fetch_tag=(uint32_t)(uintptr_t)f.cpu.fetch_page->user;
    } else if(operation==1)status=a68k_exception_frame(&f.cpu,input[36]);
    else if(operation==2)status=a68k_interrupt_entry(&f.cpu);
    else if(operation==3)status=a68k_moveq(&f.cpu,(uint16_t)input[36],input[40]);
    else if(operation>=4 && operation<=13) {
        if(operation==13){f.cpu.entry_eax=input[54];f.cpu.entry_eax_valid=1;}
        if(operation==8 || operation==12) {
            assert(input[54]<=32);f.scripted=1;f.script_count=input[54];
            memcpy(f.script,input+55,f.script_count*sizeof f.script[0]);
            if(operation==12)memcpy(f.script_edx,input+55+3*f.script_count,f.script_count*sizeof f.script_edx[0]);
            if(!script_pages_ready) {
                a68k_page page={0};page.read[0]=operand8;page.read[1]=operand16;page.read[2]=operand32;
                page.write[0]=operand_write8;page.write[1]=operand_write16;page.write[2]=operand_write32;
                page.read_observed[0]=observed8;page.read_observed[1]=observed16;page.read_observed[2]=observed32;
                for(unsigned i=0;i<A68K_PAGE_COUNT;i++)script_pages[i]=page;
                script_pages_ready=1;
            }
            /* Dedicated immutable table: other fixture operations own their
             * separate mutable maps and cannot contaminate scripted cases. */
            f.cpu.read_pages=script_pages;f.cpu.data_pages=script_pages;f.cpu.write_pages=script_pages;
        }
        if(operation==5 || operation==6 || operation==7 || operation==10 || operation==11 || operation==13) {
            memset(pages,0,sizeof pages);memset(data_pages,0,sizeof data_pages);
            f.cpu.data_pages=data_pages;f.bus_value=input[44];
            uint32_t address=input[45]&0xffffff;unsigned width=input[47];
            if(width==1)operand_data[1]=input[44];
            else if(width==2)word(operand_data,input[44]);
            else {word(operand_data,input[44]>>16);word(operand_data+2,input[44]);}
            a68k_page page={0};page.guest_base=width==1?address^1u:address;
            page.size=width;page.data=input[46]?operand_data:NULL;
            if(width==1)page.data=input[46]?operand_data+1:NULL;
            page.read[0]=operand8;page.read[1]=operand16;page.read[2]=operand32;
            if(operation==10 || operation==11) {
                f.bus_edx=input[54];page.native_base=f.bus_edx;page.native_base_valid=1;
                page.read_observed[0]=observed8;page.read_observed[1]=observed16;page.read_observed[2]=observed32;
            }
            pages[address>>12]=page;data_pages[address>>12]=page;
            if(operation==6 || operation==7 || operation==11 || operation==13) {
                memset(write_pages,0,sizeof write_pages);f.cpu.write_pages=write_pages;
                uint32_t write_address=operation==7?input[51]&0xffffff:address;
                if(operation==7 && input[53]) {
                    output_data=destination_data;
                    if(width==1)output_data[1]=input[52];
                    else if(width==2)word(output_data,input[52]);
                    else {word(output_data,input[52]>>16);word(output_data+2,input[52]);}
                }
                page.guest_base=width==1?write_address^1u:write_address;
                page.data=input[48]?(width==1?output_data+1:output_data):NULL;
                page.write[0]=operand_write8;page.write[1]=operand_write16;page.write[2]=operand_write32;
                write_pages[write_address>>12]=page;
            }
        }
        status=a68k_dispatch_target(&f.cpu,input[41],(uint16_t)input[36],input[40]);
    }
    else return 0;
    memcpy(output,&f.cpu.r,sizeof f.cpu.r);
    output[33]=f.cpu.pc;output[34]=f.cpu.flags;output[35]=f.cpu.cycles;
    output[36]=status;output[37]=f.fetch_tag;output[38]=f.count;
    memcpy(output+39,f.events,f.count*sizeof f.events[0]);
    output[135]=f.cpu.illegal_opcode;output[136]=f.cpu.illegal_pc;
    output[137]=f.cpu.fault.boundary;output[138]=f.cpu.fault.native_pc;
    output[139]=f.cpu.fault.vector;output[140]=f.cpu.fault.exception_pc;
    output[141]=f.cpu.fault.target;output[142]=f.cpu.fault.cycles;
    output[143]=f.cpu.fault.flags;
    memcpy(output+144,f.bus_context,sizeof f.bus_context);
    if(operation==9)output[212]=f.cpu.prefetched_opcode;
    if(operation==8 || operation==12) {
        assert(f.script_cursor==f.script_count);output[212]=f.script_cursor;
        memcpy(output+213,f.script_context,f.script_cursor*sizeof f.script_context[0]);
    }
    if(operation==6 || operation==7 || operation==11 || operation==13) {
        memcpy(output+177,f.write_context,sizeof f.write_context);
        output[210]=f.written_value;
        output[211]=input[47]==1?output_data[1]:input[47]==2?
            output_data[0]|((uint32_t)output_data[1]<<8):
            ((uint32_t)output_data[0]<<16)|((uint32_t)output_data[1]<<24)|
            output_data[2]|((uint32_t)output_data[3]<<8);
    }
    return 1;
}
static uint32_t operand_read(unsigned width,uint32_t address) {
    event(width==1?5:width==2?6:7,address,0);
    memcpy(f.bus_context,&f.cpu.r,sizeof f.bus_context);
    if(f.scripted) {
        unsigned i=f.script_cursor++;assert(i<f.script_count);
        assert(f.script[i][0]==(width==1?5u:width==2?6u:7u) && f.script[i][1]==address);
        memcpy(f.script_context[i],&f.cpu.r,sizeof f.cpu.r);return f.script[i][2];
    }
    return f.bus_value;
}
static uint32_t operand8(void *u,uint32_t a){(void)u;return operand_read(1,a);}
static uint32_t operand16(void *u,uint32_t a){(void)u;return operand_read(2,a);}
static uint32_t operand32(void *u,uint32_t a){(void)u;return operand_read(4,a);}
static a68k_read_result observed16(void *u,uint32_t a) {
    (void)u;uint32_t value=operand_read(2,a);
    return (a68k_read_result){value,f.scripted?f.script_edx[f.script_cursor-1]:f.bus_edx};
}
static a68k_read_result observed8(void *u,uint32_t a) {
    (void)u;uint32_t value=operand_read(1,a);
    return (a68k_read_result){value,f.scripted?f.script_edx[f.script_cursor-1]:f.bus_edx};
}
static a68k_read_result observed32(void *u,uint32_t a) {
    (void)u;uint32_t value=operand_read(4,a);
    return (a68k_read_result){value,f.scripted?f.script_edx[f.script_cursor-1]:f.bus_edx};
}
static void operand_write(unsigned width,uint32_t address,uint32_t value) {
    event(width==1?8:width==2?9:10,address,value);f.written_value=value;
    memcpy(f.write_context,&f.cpu.r,sizeof f.write_context);
    if(f.scripted) {
        unsigned i=f.script_cursor++;assert(i<f.script_count);
        assert(f.script[i][0]==(width==1?8u:width==2?9u:10u) && f.script[i][1]==address && f.script[i][2]==value);
        memcpy(f.script_context[i],&f.cpu.r,sizeof f.cpu.r);
    }
}
static void operand_write8(void *u,uint32_t a,uint32_t v){(void)u;operand_write(1,a,v);}
static void operand_write16(void *u,uint32_t a,uint32_t v){(void)u;operand_write(2,a,v);}
static void operand_write32(void *u,uint32_t a,uint32_t v){(void)u;operand_write(4,a,v);}
unsigned a68k_probe_fault_latch(void) {
    /* Run immediately after a CPU probe. A retry must not alter any CPU field,
     * callback trace or fetch binding, even through a different public entry. */
    if(!f.cpu.fault.boundary) {assert(!a68k_fault_message(&f.cpu));return 0;}
    fixture saved;memcpy(&saved,&f,sizeof saved);
    const char *message=f.cpu.fault.boundary==A68K_DIVS_HOST_OVERFLOW?
        "A68K halted: original DIVS overflows the host divider (INT32_MIN / -1).":
        "A68K halted: odd exception vector reaches an unsafe original host-stack path.";
    assert(strcmp(a68k_fault_message(&f.cpu),message)==0);
    a68k_boundary fault=f.cpu.fault.boundary;
    for(unsigned repeat=0;repeat<2;repeat++) {
        assert(a68k_reset(&f.cpu)==fault);
        assert(a68k_exception_frame(&f.cpu,3)==fault);
        assert(a68k_interrupt_entry(&f.cpu)==fault);
        assert(a68k_moveq(&f.cpu,0x7fff,0x202)==fault);
        assert(a68k_dispatch_target(&f.cpu,0x48b568,0xffff,0x202)==fault);
        assert(a68k_dispatch_target(&f.cpu,0,0,0)==fault);
        assert(!a68k_bind_pc(&f.cpu,0x8000));
        assert(memcmp(&f,&saved,sizeof f)==0);
    }
    return 14;
}
static uint32_t read8(void *u,uint32_t a) {(void)u;event(5,a,0);return 0xa1b2c3d4;}
static uint32_t read16(void *u,uint32_t a) {(void)u;event(6,a,0);return 0xa1b2c3d4;}
static uint32_t read32(void *u,uint32_t a) {(void)u;event(7,a,0);return 0xa1b2c3d4;}
static void write8(void *u,uint32_t a,uint32_t v) {(void)u;event(5,a,v);}
static void write16(void *u,uint32_t a,uint32_t v) {(void)u;event(6,a,v);}
static void write32(void *u,uint32_t a,uint32_t v) {(void)u;event(7,a,v);}
int a68k_probe_memory(unsigned space,unsigned width,unsigned direct,uint32_t address,uint32_t value,uint8_t *ram,uint32_t *output) {
    f.count=0;a68k_page *p=&pages[(address&0xffffff)>>12];memset(p,0,sizeof *p);
    if(direct) {p->data=ram;p->guest_base=0x123000;p->size=8192;}
    p->read[0]=read8;p->read[1]=read16;p->read[2]=read32;
    p->write[0]=write8;p->write[1]=write16;p->write[2]=write32;
    output[0]=0;
    int ok=space==2?a68k_write(pages,address,width,value):a68k_read(pages,(a68k_read_space)space,address,width,output);
    output[1]=f.count;memcpy(output+2,f.events,f.count*sizeof f.events[0]);return ok;
}

unsigned a68k_probe_host_contract(void) {
    /* These are adapter-supplied host-binding guards, NOT original CPU
     * equivalence cases or an emulated missing-memory policy. */
    uint32_t value=0x12345678;uint8_t ram[2]={0xab,0xcd};
    memset(pages,0,sizeof pages);a68k_page *p=&pages[0xfff];
    p->data=ram;p->guest_base=0xfffffe;p->size=2;
    assert(!a68k_read(NULL,A68K_READ_SPACE,0,2,&value));
    assert(!a68k_read(pages,A68K_READ_SPACE,0,2,&value));
    assert(!a68k_read(pages,A68K_READ_SPACE,0xfffffe,3,&value));
    assert(!a68k_read(pages,A68K_READ_SPACE,0xfffffe,4,&value) && value==0x12345678);
    assert(!a68k_write(pages,0xfffffe,4,0) && ram[0]==0xab && ram[1]==0xcd);
    assert(a68k_read(pages,A68K_READ_SPACE,0xfffffe,2,&value) && value==0x107cdab);
    a68k_cpu cpu={0};assert(a68k_reset(&cpu)==A68K_BINDING_ERROR);
    assert(a68k_exception_frame(&cpu,3)==A68K_BINDING_ERROR);
    cpu.read_pages=pages;assert(!a68k_bind_pc(&cpu,0x1000000));
    uint8_t next_opcode[2]={0x71,0x4e};a68k_page fetch={0};
    fetch.data=next_opcode;fetch.guest_base=2;fetch.size=2;
    a68k_cpu reset={0};reset.fetch_page=&fetch;reset.r.sr_high=0x20;reset.r.opaque24[1]=1;
    assert(a68k_dispatch_target(&reset,0x486e48,0x4e70,0x202)==A68K_BINDING_ERROR);
    assert(reset.prefetched_opcode==0x4e71); /* Original token is never a host pointer. */
    a68k_read_result observation={0x12345678,0x87654321};
    assert(!a68k_read_observed(pages,A68K_READ_SPACE,0xfffffe,2,&observation));
    assert(observation.value==0x12345678 && observation.edx==0x87654321);
    p->native_base=0x76543210;p->native_base_valid=1;
    assert(a68k_read_observed(pages,A68K_READ_SPACE,0xfffffe,2,&observation));
    assert(observation.value==0x107cdab && observation.edx==0x76543210);
    assert(!a68k_read_observed(pages,A68K_READ_SPACE,0xfffffe,4,&observation));
    p->data=NULL;p->read[1]=read16;f.count=0;
    assert(!a68k_read_observed(pages,A68K_READ_SPACE,0xfffffe,2,&observation) && f.count==0);
    p->read_observed[1]=observed16;f.bus_value=0xdeadbeef;f.bus_edx=0x89abcdef;
    assert(a68k_read_observed(pages,A68K_READ_SPACE,0xfffffe,2,&observation));
    assert(observation.value==0xdeadbeef && observation.edx==0x89abcdef && f.count==1);
    a68k_cpu conditional={0};conditional.pc=0x123456;
    assert(a68k_dispatch_target(&conditional,0x472fcc,0x50d0,0x202)==A68K_BINDING_ERROR);
    assert(conditional.pc==0x123456); /* Missing entry EAX is not assumed zero. */
    return 16;
}

/* Normalize host-bound descriptors to original integer tokens for comparison.
 * Token pointers are never dereferenced. Include sentinel pages unchanged. */
int a68k_probe_maps(unsigned kind,uint32_t start,uint32_t end,unsigned direct,uint32_t *out) {
    a68k_page marker={0},binding={0};
    marker.data=reset_data;marker.guest_base=0xfeed1234;marker.size=sizeof reset_data;
    marker.user=(void *)(uintptr_t)0x12340000;
    for(unsigned i=0;i<A68K_PAGE_COUNT;i++)pages[i]=marker;
    binding.data=direct?reset_data:NULL;binding.size=sizeof reset_data;
    binding.user=(void *)(uintptr_t)0x72000000;
    binding.read[0]=read8;binding.read[1]=read16;binding.read[2]=read32;
    binding.write[0]=write8;binding.write[1]=write16;binding.write[2]=write32;
    int ok=a68k_map_pages(pages,(a68k_map_kind)kind,start,end,&binding);
    for(unsigned i=0;i<A68K_PAGE_COUNT;i++) {
        a68k_page *p=&pages[i];
        out[i*4]=p->data?(uint32_t)(uintptr_t)p->user-p->guest_base:0;
        for(unsigned j=0;j<3;j++)out[i*4+j+1]=
            p->read[j]||p->write[j]?0x71000100+j*16:0;
    }
    return ok;
}
