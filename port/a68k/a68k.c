/* Original entries: memory 004b30a0..004b3250, reset 004b33a0,
 * exception 00462be0, IRQ 00462b1c, MOVEQ 00478438.
 * Preserve ElSemi behavior separately from potential original-code fixes.
 * Historical source: Mike Coates / Darren Olafson Make68K 0.30. Its dispatch
 * grouping matches all 65536 original entries; individual ElSemi bodies,
 * not a later library revision, remain authoritative. See PROVENANCE.md. */
#include "a68k.h"
#include <string.h>

/* Make68K CodeSegmentBegin emits this RLE decoder. Use the actual ElSemi
 * table rather than regenerating it with a possibly different source version.
 * Targets remain integer identities for the portable dispatcher. */
static const uint8_t dispatch_rle[]={
#include "dispatch_rle.inc"
};
/* 00528ff0: native vector numbers are reduced to a byte. The 48
 * explicit costs end immediately before the packed opcode dispatch.
 * Preserve the adjacent bytes observable through larger vector numbers. */
void a68k_init_exception_cycles(uint8_t costs[256])
{
    static const uint8_t vector_costs[48] = {
        0, 0, 0, 0, 38, 42, 44, 38, 38, 0, 38, 38, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 46, 46, 46, 46, 46, 46, 46, 46,
        38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38
    };
    memcpy(costs, vector_costs, sizeof vector_costs);
    memcpy(costs + sizeof vector_costs, dispatch_rle, 256 - sizeof vector_costs);
}

int a68k_init_dispatch(uint32_t *table,size_t capacity) {
    if(!table || capacity<A68K_OPCODE_COUNT)return 0;
    uint32_t base=0;
    for(unsigned i=0;i<4;i++)base|=(uint32_t)dispatch_rle[i]<<(8*i);
    size_t cursor=4,n=0;
    while(cursor+4<=sizeof dispatch_rle) {
        uint32_t run=0;
        for(unsigned i=0;i<4;i++)run|=(uint32_t)dispatch_rle[cursor+i]<<(8*i);
        cursor+=4;unsigned count=run>>24;
        if(!count) {
            if(cursor+2>sizeof dispatch_rle)return 0;
            count=dispatch_rle[cursor]|((unsigned)dispatch_rle[cursor+1]<<8);cursor+=2;
        }
        if(!count)return n==A68K_OPCODE_COUNT && cursor==sizeof dispatch_rle;
        if(count>A68K_OPCODE_COUNT-n)return 0;
        uint32_t target=base+(run&0xffffffu);
        while(count--)table[n++]=target;
    }
    return 0;
}

_Static_assert(sizeof(a68k_registers)==0x84,"Native context prefix");
_Static_assert(offsetof(a68k_registers,sr_high)==0x44,"Native status offset");
_Static_assert(offsetof(a68k_registers,pc)==0x50,"Native PC offset");
_Static_assert(offsetof(a68k_registers,usp)==0x70,"Native USP offset");

static int width_index(unsigned width) {
    return width==1?0:width==2?1:width==4?2:-1;
}
static uint32_t word(const uint8_t *p) {return p[0]|((uint32_t)p[1]<<8);}
static void put_word(uint8_t *p,uint32_t value) {p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);}
const char *a68k_fault_message(const a68k_cpu *s) {
    if(s->fault.boundary==A68K_ODD_VECTOR)
        return "A68K halted: odd exception vector reaches an unsafe original host-stack path.";
    if(s->fault.boundary==A68K_DIVS_HOST_OVERFLOW)
        return "A68K halted: original DIVS overflows the host divider (INT32_MIN / -1).";
    return NULL;
}
static int direct_span(const a68k_page *p,uint32_t address,unsigned width,size_t *at) {
    /* Word/long accesses intentionally retain odd addresses. The original
     * selects only the starting page, even when the longword crosses it. */
    uint32_t offset=(width==1?address^1u:address)-p->guest_base;
    *at=offset;
    return offset<=p->size && width<=p->size-offset;
}
int a68k_map_pages(a68k_page *pages,a68k_map_kind kind,uint32_t start,uint32_t end,const a68k_page *binding) {
    if(!pages || !binding || kind>A68K_MAP_WRITE || (int)kind<0 ||
       start>end || end>0xffffffu)return 0;
    /* Original count is based on length, NOT separately rounded endpoints.
     * Preserve this for unaligned ranges. Reject malformed host ranges before
     * mutation rather than reproducing native out-of-table pointer writes. */
    unsigned first=start>>12,count=((end-start)>>12)+1;
    if(count>A68K_PAGE_COUNT-first)return 0;
    a68k_page page=*binding;page.guest_base=start;
    if(kind==A68K_MAP_FETCH) {
        for(unsigned i=0;i<3;i++){page.read[i]=NULL;page.read_observed[i]=NULL;page.read_live[i]=NULL;page.write[i]=NULL;page.write_observed[i]=NULL;}
    } else if(kind==A68K_MAP_DATA) {
        for(unsigned i=0;i<3;i++){page.write[i]=NULL;page.write_observed[i]=NULL;}
    } else {
        for(unsigned i=0;i<3;i++){page.read[i]=NULL;page.read_observed[i]=NULL;page.read_live[i]=NULL;}
    }
    for(unsigned i=0;i<count;i++)pages[first+i]=page;
    return 1;
}
int a68k_read(const a68k_page *pages,a68k_read_space space,uint32_t address,unsigned width,uint32_t *value) {
    int index=width_index(width);if(!pages || !value || index<0 || (space!=A68K_READ_SPACE && space!=A68K_DATA_SPACE))return 0;
    address&=0xffffffu;const a68k_page *p=&pages[address>>12];
    if(!p->data) {
        if(!p->read[index])return 0;
        *value=p->read[index](p->user,address);return 1;
    }
    size_t at;if(!direct_span(p,address,width,&at))return 0;
    *value=width==1?p->data[at]:width==2?word(p->data+at):
        (word(p->data+at)<<16)|word(p->data+at+2);
    /* 004b3190/31c0 and 004b3220/3250 load AX/AL, NOT zero-extended EAX.
     * The high bits retain the original descriptor address. Preserve this
     * Windows-address-derived value as an integer token; it is never a host
     * pointer. Whether guest handlers depend on it needs separate review. */
    if(width<4) {
        uint32_t descriptor=(space==A68K_READ_SPACE?0x10682d0u:0x10482d0u)+(address>>12)*16;
        *value|=descriptor&~(width==1?255u:65535u);
    }
    return 1;
}
int a68k_read_observed(const a68k_page *pages,a68k_read_space space,uint32_t address,unsigned width,a68k_read_result *result) {
    int index=width_index(width);
    if(!pages || !result || index<0 || (space!=A68K_READ_SPACE && space!=A68K_DATA_SPACE))return 0;
    address&=0xffffffu;const a68k_page *p=&pages[address>>12];
    if(!p->data) {
        if(!p->read_observed[index])return 0;
        *result=p->read_observed[index](p->user,address);return 1;
    }
    uint32_t value;
    if(!p->native_base_valid || !a68k_read(pages,space,address,width,&value))return 0;
    /* Original direct wrappers leave their descriptor's base in EDX. This
     * may depend on the Windows allocation: never derive it from a Mac pointer.
     * Callback paths instead supply their actual return-register observation. */
    *result=(a68k_read_result){value,p->native_base};return 1;
}
int a68k_read_live(const a68k_page *pages,a68k_read_space space,uint32_t address,unsigned width,
                   a68k_read_result *result,a68k_host_state *host) {
    int index=width_index(width);
    if(!pages || !result || !host || !host->valid || index<0 ||
       (space!=A68K_READ_SPACE && space!=A68K_DATA_SPACE))return 0;
    address&=0xffffffu;const a68k_page *p=&pages[address>>12];
    if(p->data) {
        a68k_read_result read;
        if(!a68k_read_observed(pages,space,address,width,&read))return 0;
        *result=read;host->eax=read.value;return 1;
    }
    if(!p->read_live[index])return 0;
    a68k_read_observation read=p->read_live[index](p->user,address,host->control_flags);
    if(!read.valid)return 0;
    *result=read.registers;host->eax=read.registers.value;host->control_flags=read.control_flags;
    return 1;
}
/* Shared bus connection only: ordinary single-handler APIs retain their
 * value-only bindings, while live execution requires explicit observations. */
static int read_operand_live(const a68k_page *pages,a68k_read_space space,uint32_t address,
                              unsigned width,uint32_t *value,a68k_host_state *host) {
    if(!host)return a68k_read(pages,space,address,width,value);
    a68k_read_result result;
    if(!a68k_read_live(pages,space,address,width,&result,host))return 0;
    *value=result.value;return 1;
}
/* depth includes the x86 CALL's return address and the words saved by
 * this instruction family. SCSP and Model 1 callbacks can observe it. */
static int write_operand_live(a68k_cpu *cpu, uint32_t address, unsigned width,
                              uint32_t value, a68k_host_state *host, unsigned depth)
{
    if (!host) return a68k_write(cpu->write_pages,address,width,value);
    cpu->write_wrapper_sp = cpu->dispatch_sp ? cpu->dispatch_sp - depth : 0;
    int ok = a68k_write_observed(cpu->write_pages,address,width,value,host);
    cpu->write_wrapper_sp = 0;
    return ok;
}
int a68k_write(const a68k_page *pages,uint32_t address,unsigned width,uint32_t value) {
    int index=width_index(width);if(!pages || index<0)return 0;
    address&=0xffffffu;const a68k_page *p=&pages[address>>12];
    if(!p->data) {
        if(!p->write[index])return 0;
        p->write[index](p->user,address,value);return 1;
    }
    size_t at;if(!direct_span(p,address,width,&at))return 0;
    if(width==1)p->data[at]=(uint8_t)value;
    else if(width==2)put_word(p->data+at,value);
    else {put_word(p->data+at,value>>16);put_word(p->data+at+2,value);}
    return 1;
}
int a68k_write_observed(const a68k_page *pages,uint32_t address,unsigned width,uint32_t value,a68k_host_state *host) {
    int index=width_index(width);
    if(!pages || !host || !host->valid || index<0)return 0;
    address&=0xffffffu;const a68k_page *p=&pages[address>>12];
    if(!p->data) {
        if(!p->write_observed[index])return 0;
        a68k_host_state result=p->write_observed[index](p->user,address,value,host->control_flags);
        if(!result.valid)return 0;
        *host=result;return 1;
    }
    if(width==4 && !p->native_base_valid)return 0;
    if(!a68k_write(pages,address,width,value))return 0;
    host->eax=width==4?p->native_base:0x10582d0u+(address>>12)*16;
    /* All three direct wrappers preserve control bits. Never turn their
     * original descriptor/base integer into a portable host pointer. */
    return 1;
}
int a68k_bind_pc(a68k_cpu *s,uint32_t pc) {
    if(s->fault.boundary)return 0;
    /* 004b30a0 does not mask PC itself. Its caller owns that operation. */
    if(!s->read_pages || (pc>>12)>=A68K_PAGE_COUNT)return 0;
    s->fetch_page=&s->read_pages[pc>>12];s->r.fetch_bank=pc>>16;return 1;
}
a68k_boundary a68k_reset(a68k_cpu *s) {
    if(s->fault.boundary)return s->fault.boundary;
    uint32_t sp,pc;
    if(!a68k_read(s->read_pages,A68K_READ_SPACE,0,4,&sp) || !a68k_read(s->read_pages,A68K_READ_SPACE,4,4,&pc))return A68K_BINDING_ERROR;
    s->r.pc=pc;
    if(!a68k_bind_pc(s,pc))return A68K_BINDING_ERROR;
    s->r.a[7]=sp;s->r.sr_high=0x27;
    /* Native reset deliberately leaves Dn/other An, saved SSP, X/flags and
     * pending IRQ untouched. Live dispatcher registers are loaded at entry. */
    return A68K_RETURN;
}
static a68k_boundary exit_dispatch(a68k_cpu *s) {
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(s->r.sr_high&0x20)s->r.ssp=s->r.a[7];else s->r.usp=s->r.a[7];
    return A68K_EXIT;
}
static a68k_boundary stack_exception(a68k_cpu *s,unsigned vector,a68k_host_state *observation,unsigned depth) {
    if(s->fault.boundary)return s->fault.boundary;
    if(!s->exception_cycles)return A68K_BINDING_ERROR;
    if(observation) {
        if(!observation->valid || !s->write_pages || !s->data_pages || !s->bind_observed)return A68K_BINDING_ERROR;
    } else if(!s->stack_word || !s->stack_long || !s->vector_read || !s->bind)return A68K_BINDING_ERROR;
    uint32_t exception_pc=s->pc;
    vector&=255;s->cycles-=s->exception_cycles[vector];
    uint32_t flags=s->flags;
    uint32_t sr=((s->r.sr_high&255)<<8)|(flags&1)|((flags>>4)&12)|
        ((flags>>10)&2)|((s->r.x&1)<<4);
    uint32_t stack=s->r.a[7];
    if(!(s->r.sr_high&0x20)) {s->r.sr_high|=0x20;s->r.usp=stack;stack=s->r.ssp;}
    stack-=6;s->r.a[7]=stack;
    /* Publishing PC before EACH callback is native behavior. The callback
     * may inspect/change the context; do not batch these writes. */
    s->r.pc=s->pc;
    if(observation) {
        if(!write_operand_live(s,stack,2,sr,observation,depth))return A68K_BINDING_ERROR;
    } else s->stack_word(s->user,stack,sr);
    s->r.pc=s->pc;
    if(observation) {
        if(!write_operand_live(s,stack+2,4,s->pc,observation,depth))return A68K_BINDING_ERROR;
    } else s->stack_long(s->user,stack+2,s->pc);
    s->r.pc=s->pc;
    if(observation) {
        a68k_read_result result;
        /* Native slot +12 is DATA-long, not the PC-relative READ table. */
        if(!a68k_read_live(s->data_pages,A68K_DATA_SPACE,s->r.vbr+vector*4,4,&result,observation))return A68K_BINDING_ERROR;
        s->pc=result.value;
    } else s->pc=s->vector_read(s->user,s->r.vbr+vector*4);
    s->flags=flags;
    if(s->pc&1) {
        /* 00462c89 enters recursive vector 3, then bypasses pending native
         * CALL frames. An IRQ budget exit can RET to saved ECX. Stop at the
         * verified prefix, retaining its effects and the unmasked target;
         * do not fabricate a return, vector, bus value or normal cycle exit.
         * This explicit stop was approved on 2026-11-04; game reachability
         * is unknown. See AUDIO_RE_ANALYSIS.md and native stack probes. */
        s->fault=(a68k_fault){A68K_ODD_VECTOR,0x462c89,vector,exception_pc,
                              s->pc,s->cycles,s->flags};
        return s->fault.boundary;
    }
    s->r.raw_pc=s->pc;s->pc&=s->address_mask;
    s->r.flags=s->flags;
    if(observation) {
        a68k_host_state result=s->bind_observed(s->user,s->pc,observation->control_flags);
        if(!result.valid)return A68K_BINDING_ERROR;
        *observation=result;
    } else s->bind(s->user,s->pc);
    s->flags=s->r.flags;
    return A68K_RETURN;
}
/* CALL 00462be0, PUSH EDX/EAX and the bus CALL use four stack words. */
static a68k_boundary exception_frame(a68k_cpu *s,unsigned vector,a68k_host_state *observation) {
    return stack_exception(s,vector,observation,16);
}
a68k_boundary a68k_exception_frame(a68k_cpu *s,unsigned vector) {
    return exception_frame(s,vector,NULL);
}
a68k_boundary a68k_exception_observed(a68k_cpu *s,unsigned vector,a68k_host_state *host) {
    if(!host || !host->valid)return A68K_BINDING_ERROR;
    return exception_frame(s,vector,host);
}
/* 00462b7c also receives live PC/flags from RTE. Do not reload the published
 * context there: it can still contain the status word read from the stack. */
static a68k_boundary interrupt_live(a68k_cpu *s,a68k_host_state *observation) {
    unsigned level=s->r.irq&7;
    if(observation && level)observation->eax=level;
    if(level && (level==7 || level>(s->r.sr_high&7))) {
        if(observation?!s->ack_observed:!s->ack)return A68K_BINDING_ERROR;
        s->r.irq&=0xffffff78u;s->r.flags=s->flags;
        int32_t vector;
        if(observation) {
            a68k_host_state ack=s->ack_observed(s->user,level,observation->control_flags);
            if(!ack.valid)return A68K_BINDING_ERROR;
            *observation=ack;vector=(int32_t)ack.eax;
        } else vector=s->ack(s->user,level);
        s->flags=s->r.flags;
        a68k_boundary result=stack_exception(s,vector<0?24+level:(unsigned)vector,observation,20);
        if(result!=A68K_RETURN)return result;
        if(observation)observation->eax=level; /* Native POP EAX restores the saved IRQ level. */
        s->r.sr_high=(s->r.sr_high&~7u)|level;
    }
    /* Original IRQ precedes budget testing; zero still reaches opcode fetch. */
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
a68k_boundary a68k_interrupt_entry(a68k_cpu *s) {
    if(s->fault.boundary)return s->fault.boundary;
    s->pc=s->r.pc;s->flags=s->r.flags;
    return interrupt_live(s,NULL);
}
a68k_boundary a68k_moveq(a68k_cpu *s,uint16_t opcode,uint32_t host_control_flags) {
    if(s->fault.boundary)return s->fault.boundary;
    s->pc+=2;
    uint32_t value=(opcode&0x80)?0xffffff00u|(opcode&255u):opcode&255u;
    unsigned parity=value&255u;parity^=parity>>4;parity^=parity>>2;parity^=parity>>1;
    /* TEST supplies C/Z/N/V (and parity); X lives elsewhere and is untouched.
     * Control bits come from the original host-flags input, not guest CCR.
     * AF is undefined by TEST and is not an equivalence claim. */
    s->flags=(host_control_flags&~0x8d5u)|(value==0?0x40u:0)|
        (value&0x80000000u?0x80u:0)|((parity&1)?0:4u);
    s->r.d[(opcode>>9)&7]=value;s->cycles-=4;
    /* All 7xxx aliases, including bit 8 set, reach this original body. */
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}

static uint32_t logical_flags(uint32_t value,unsigned bits,uint32_t host) {
    unsigned parity=value&255u;parity^=parity>>4;parity^=parity>>2;parity^=parity>>1;
    return (host&~0x8d5u)|(value==0?0x40u:0)|
        ((value>>(bits-1))&1?0x80u:0)|((parity&1)?0:4u);
}
/* 004b30a0 returns the descriptor byte offset. SHR ECX,16 is the last
 * flag producer. Carry takes bit 15 of PC; the observed OF/AF are clear. */
a68k_host_state a68k_bind_pc_observed(a68k_cpu *cpu, uint32_t pc, uint32_t control)
{
    if (!a68k_bind_pc(cpu, pc)) return (a68k_host_state){0};
    uint32_t flags = logical_flags(pc >> 16, 32, control) | ((pc >> 15) & 1);
    return (a68k_host_state){(pc >> 12) * 16, flags, 1};
}

/* Native NBCD uses SBB/DAS and PUSHFD, unlike ABCD/SBCD's saved-flag
 * merge: no sticky Z; full result flags are copied into X. DAS's undefined
 * x86 OF is observed clear for every byte/X pair in both the original
 * Windows process and Unicorn. Do not infer this from architectural 68000
 * NBCD or claim all x86 processors: see the retained Windows probe. */
static uint32_t nbcd_value(uint32_t operand,unsigned x,uint32_t host,uint32_t *flags) {
    operand&=255u;
    uint32_t raw=(0u-operand-x)&255u;
    unsigned carry=operand+x!=0,adjust=(raw&15)>9 || (operand&15)+x!=0;
    uint32_t value=(raw-(adjust?6u:0)-(raw>0x99 || carry?0x60u:0))&255u;
    *flags=logical_flags(value,8,host)|carry|(adjust?0x10u:0);
    return value;
}
enum reg_op { SWAP,NEGX,CLR,NEG,NOT,EXG_DD,EXG_AA,EXG_DA,NOP,EXT_BW,EXT_WL,TST,TAS,TST_A,NBCD };
static uint32_t negate_value(a68k_cpu *s,uint32_t old,unsigned bits,uint32_t host,int extend) {
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1,prior_flags=s->flags;
    /* Native NEGX uses ADC width,0 then NEG width; ADC overflow is discarded.
     * Preserve wrap-before-negation and save full X before merging sticky Z. */
    uint32_t input=((old&mask)+(extend?(s->r.x&1):0))&mask,value=(0u-input)&mask;
    s->flags=logical_flags(value,bits,host)|(input!=0)|
        (input==(1u<<(bits-1))?0x800u:0)|((input&15)?0x10u:0);
    s->r.x=s->flags;
    if(extend && !value)s->flags=(s->flags&~0x40u)|(prior_flags&0x40);
    return (old&~mask)|value;
}
static a68k_boundary register_op(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                enum reg_op op,unsigned bits,unsigned cost) {
    unsigned reg=opcode&7,other=(opcode>>9)&7;
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1;
    uint32_t old=op==TST_A?s->r.a[reg]:s->r.d[reg],value=old&mask;
    s->pc+=2;
    switch(op) {
    case NOP:break;
    case EXG_DD:case EXG_AA:case EXG_DA: {
        uint32_t *a=op==EXG_AA?&s->r.a[other]:&s->r.d[other];
        uint32_t *b=op==EXG_DD?&s->r.d[reg]:&s->r.a[reg];
        uint32_t tmp=*a;*a=*b;*b=tmp;break;
    }
    default:
        switch(op) {
        case SWAP:value=(old<<16)|(old>>16);break;
        case EXT_BW:value=(old&0x80)?0xff00u|(old&255u):old&255u;break;
        case EXT_WL:value=(old&0x8000)?0xffff0000u|(old&65535u):old&65535u;break;
        case CLR:value=0;break;
        case NOT:value^=mask;break;
        case NEG:case NEGX:value=negate_value(s,value,bits,host,op==NEGX);break;
        default:break;
        }
        if(op==CLR)s->flags=0x40; /* Native assigns EDX, not a TEST result. */
        else if(op!=NEG && op!=NEGX)s->flags=logical_flags(value,bits,host);
        /* TAS captures TEST flags before setting bit 7, as native PUSHFD/OR. */
        if(op==TAS)value|=0x80u;
        if(op!=TST && op!=TST_A)s->r.d[reg]=(old&~mask)|value;
        break;
    }
    s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}

static a68k_boundary trap(a68k_cpu *s,unsigned vector,unsigned return_adjust,a68k_host_state *observation) {
    a68k_boundary result=exception_frame(s,vector,observation);
    if(result!=A68K_RETURN)return result;
    /* Line-A/F and generic ILLEGAL use TEST/JLE: zero exits, unlike ordinary
     * MOVEQ's JS. Do not unify the two budget contracts. */
    if(!s->cycles || (s->cycles&0x80000000u))return exit_dispatch(s);
    s->pc+=return_adjust;return A68K_FETCH;
}
static int condition(a68k_cpu *s,unsigned cc) {
    /* Signed conditions restore EFLAGS through POPFD and explicitly OR IF
     * into the saved live word. Preserve that observable EDX mutation. */
    if(cc>=12)s->flags|=0x200;
    unsigned c=s->flags&1,z=(s->flags>>6)&1,n=(s->flags>>7)&1,v=(s->flags>>11)&1;
    switch(cc) {
    case 0:return 1;case 1:return 0;case 2:return !(c|z);case 3:return c|z;
    case 4:return !c;case 5:return c;case 6:return !z;case 7:return z;
    case 8:return !v;case 9:return v;case 10:return !n;case 11:return n;
    case 12:return n==v;case 13:return n!=v;case 14:return !z && n==v;
    default:return z || n!=v;
    }
}
static int fetch_word(a68k_cpu *s,uint32_t address,uint32_t *value) {
    size_t at;
    /* Original instruction stream reads use the current EBP binding directly,
     * without invoking the data bus or looking up a new page at a boundary. */
    if(!s->fetch_page || !s->fetch_page->data ||
       !direct_span(s->fetch_page,address,2,&at))return 0;
    *value=word(s->fetch_page->data+at);return 1;
}
static uint32_t signed_word(uint32_t value) {return value&0x8000?value|0xffff0000u:value;}
enum binary_op { OR,AND,ADD,SUB,CMP,EOR,ADDX,SUBX,ADDA,SUBA,CMPA,MOVE,MOVEA };
static void binary_value(a68k_cpu *s,uint32_t *destination,uint32_t right,
                         unsigned bits,enum binary_op op,uint32_t host) {
    if(op==ADDA || op==SUBA || op==CMPA || op==MOVEA) {
        if(bits==16)right=signed_word(right&65535u);
        bits=32;
    }
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1,sign=1u<<(bits-1);
    uint32_t old=*destination,left=old&mask,result,prior_flags=s->flags;
    right&=mask;
    if(op==MOVE || op==MOVEA) {
        result=right;if(op==MOVE)s->flags=logical_flags(result,bits,host);
    } else if(op==OR || op==AND || op==EOR) {
        result=op==OR?left|right:op==AND?left&right:left^right;
        s->flags=logical_flags(result,bits,host);
    } else {
        unsigned carry=op==ADDX || op==SUBX?s->r.x&1:0;
        int subtract=op==SUB || op==SUBX || op==CMP || op==CMPA || op==SUBA;
        uint64_t wide_right=(uint64_t)right+carry;
        uint64_t wide=subtract?(uint64_t)left-wide_right:(uint64_t)left+wide_right;
        result=(uint32_t)wide&mask;
        if(op!=ADDA && op!=SUBA) {
            uint32_t overflow=(subtract?(left^right):~(left^right))&(left^result)&sign;
            s->flags=logical_flags(result,bits,host)|
                (subtract?left<wide_right:wide>mask)|(overflow?0x800u:0)|((left^right^result)&0x10);
            if(op==ADD || op==SUB || op==ADDX || op==SUBX)s->r.x=s->flags;
            /* ADC/SBB save full X before combining zero with the prior Z. */
            if((op==ADDX || op==SUBX) && !result)s->flags=(s->flags&~0x40u)|(prior_flags&0x40);
        }
    }
    if(op!=CMP && op!=CMPA)*destination=(old&~mask)|result;
}
static a68k_boundary binary_op(a68k_cpu *s,uint16_t opcode,uint32_t host,
                              enum binary_op op,unsigned bits,unsigned cost,unsigned source_mask) {
    unsigned source=opcode&source_mask,dest=(opcode>>9)&7;
    uint32_t right=source<8?s->r.d[source]:s->r.a[source-8];
    uint32_t *destination=op==ADDA || op==SUBA || op==CMPA?&s->r.a[dest]:&s->r.d[dest];
    if(op==EOR){right=s->r.d[dest];destination=&s->r.d[source];}
    s->pc+=2;binary_value(s,destination,right,bits,op,host);
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
enum operand_source { REGISTER_HIGH,IMMEDIATE_HIGH,IMMEDIATE_LOW,QUICK_LOW,REGISTER_LOW };
static a68k_boundary operand_op(a68k_cpu *s,uint16_t opcode,uint32_t host,
                               enum binary_op op,unsigned bits,unsigned cost,enum operand_source source) {
    unsigned reg=source==REGISTER_HIGH || source==IMMEDIATE_HIGH?(opcode>>9)&7:opcode&7;
    uint32_t value;uint32_t *destination=op==MOVEA || op==ADDA || op==SUBA || op==CMPA?&s->r.a[reg]:&s->r.d[reg];
    s->pc+=2;
    if(source==REGISTER_HIGH) {
        unsigned src=opcode&15;value=src<8?s->r.d[src]:s->r.a[src-8];
    } else if(source==QUICK_LOW)value=(((opcode>>9)-1)&7)+1;
    else {
        if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
        if(bits==32) {
            uint32_t low;if(!fetch_word(s,s->pc+2,&low))return A68K_BINDING_ERROR;
            value=(value<<16)|low;s->pc+=4;
        } else s->pc+=2;
    }
    binary_value(s,destination,value,bits,op,host);
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
enum control_op { SCC,DBCC,BR_WORD,BR_BYTE };
enum ea_mode { INDIRECT,POSTINC,PREDEC,DISP16,INDEXED,ABS16,ABS32,PCDISP,PCINDEX,REGISTER,IMMEDIATE };
static int effective_address(a68k_cpu *,unsigned,unsigned,enum ea_mode,uint32_t *);
static a68k_boundary check_bounds(a68k_cpu *s,uint16_t opcode,enum ea_mode mode,unsigned cost,a68k_host_state *observation) {
    uint32_t bound;s->pc+=2;
    if(mode==IMMEDIATE) {
        if(!fetch_word(s,s->pc,&bound))return A68K_BINDING_ERROR;s->pc+=2;
    } else if(mode==REGISTER)bound=s->r.d[opcode&7];
    else {
        uint32_t address;a68k_read_result read;
        if(!effective_address(s,opcode&7,2,mode,&address))return A68K_BINDING_ERROR;
        s->r.pc=s->pc;
        a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
        const a68k_page *pages=space==A68K_READ_SPACE?s->read_pages:s->data_pages;
        if(observation) {
            if(!a68k_read_live(pages,space,address,2,&read,observation))return A68K_BINDING_ERROR;
        } else if(!a68k_read_observed(pages,space,address,2,&read))return A68K_BINDING_ERROR;
        /* Unlike register CHK, the original does not restore guest flags after
         * reading. Even its non-trapping tail retains the wrapper/callback EDX.
         * Preserve this peculiarity for later original-behavior review. */
        bound=read.value;s->flags=read.edx;
    }
    uint32_t value=s->r.d[(opcode>>9)&7]&65535u;bound&=65535u;
    if(observation)observation->eax=signed_word(bound);
    if((value&0x8000) || (bound&0x8000) || value>bound) {
        /* Native upper-bound failure uses AND EDX,0x7f (not merely ~N).
         * Negative values instead OR N, retaining all high flag bits. */
        s->flags=value&0x8000?s->flags|0x80u:s->flags&0x7fu;
        a68k_boundary status=exception_frame(s,6,observation);if(status!=A68K_RETURN)return status;
    }
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary divide_operation(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                               unsigned is_signed,unsigned cost,enum ea_mode mode,
                                               uint32_t native_idiv,a68k_host_state *observation) {
    uint32_t instruction_pc=s->pc,divisor;
    s->pc+=2;s->flags&=~1u;s->r.flags=s->flags;s->cycles-=cost;
    if(mode==REGISTER)divisor=s->r.d[opcode&7];
    else if(mode==IMMEDIATE) {
        if(!fetch_word(s,s->pc,&divisor))return A68K_BINDING_ERROR;
        s->pc+=2;
    } else {
        uint32_t address;a68k_read_result read;
        if(!effective_address(s,opcode&7,2,mode,&address))return A68K_BINDING_ERROR;
        s->r.pc=s->pc;
        a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
        const a68k_page *pages=space==A68K_READ_SPACE?s->read_pages:s->data_pages;
        if(observation) {
            if(!a68k_read_live(pages,space,address,2,&read,observation))return A68K_BINDING_ERROR;
        } else if(!a68k_read_observed(pages,space,address,2,&read))return A68K_BINDING_ERROR;
        /* Zero divisors enter vector 5 with the read-return EDX. Nonzero
         * division replaces it, while quotient overflow reloads saved flags. */
        divisor=read.value;s->flags=read.edx;
    }
    if(observation)host=observation->control_flags;
    divisor&=65535u;
    if(!divisor) {
        /* Make68K divides(): native zero-divisor exception is distinct from
         * host IDIV overflow. Keep its refund, PC and TEST/JLE boundary. */
        s->cycles+=is_signed?112:95;
        return trap(s,5,0,observation);
    }
    unsigned reg=(opcode>>9)&7;uint32_t dividend=s->r.d[reg],quotient,remainder;
    int overflow;
    if(is_signed) {
        if(dividend==0x80000000u && divisor==0xffffu) {
            /* Historical Make68K and ElSemi execute CDQ/IDIV before checking
             * the 16-bit quotient. Windows filter audit found no recovery.
             * Preserve the prefix (including live EDX=-1 from CDQ), then
             * latch the approved host diagnostic instead of crashing the
             * frontend. Do not pretend this is the ordinary guest V path. */
            s->flags=0xffffffffu;
            if(observation)observation->eax=dividend;
            s->fault=(a68k_fault){A68K_DIVS_HOST_OVERFLOW,native_idiv,0,
                instruction_pc,0xffffffffu,s->cycles,s->flags};
            return s->fault.boundary;
        }
        /* Wide signed arithmetic avoids implementation-defined uint32_t to
         * int32_t conversion and C's INT_MIN/-1 undefined behavior. */
        int64_t left=dividend&0x80000000u?(int64_t)dividend-0x100000000LL:dividend;
        int64_t right=divisor&0x8000u?(int64_t)divisor-65536:divisor;
        int64_t q=left/right;
        quotient=(uint32_t)q;remainder=(uint32_t)(left%right);
        overflow=q < -32768 || q > 32767;
    } else {
        quotient=dividend/divisor;remainder=dividend%divisor;
        overflow=quotient>65535u;
    }
    if(observation)observation->eax=quotient;
    if(overflow)s->flags=s->r.flags|0x800u;
    else {
        s->r.d[reg]=(remainder<<16)|(quotient&65535u);
        s->flags=logical_flags(quotient&65535u,16,host);
    }
    /* Every native DIV tail exits at zero, not just a negative budget. */
    return !s->cycles || s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static int effective_address(a68k_cpu *s,unsigned reg,unsigned width,enum ea_mode mode,uint32_t *address) {
    uint32_t ext,low,base=s->r.a[reg];unsigned step=width==1 && reg==7?2:width;
    switch(mode) {
    case INDIRECT:*address=base;return 1;
    case POSTINC:*address=base;s->r.a[reg]+=step;return 1;
    case PREDEC:s->r.a[reg]-=step;*address=s->r.a[reg];return 1;
    default:break;
    }
    if(mode==PCDISP || mode==PCINDEX)base=s->pc;
    if(!fetch_word(s,s->pc,&ext))return 0;
    if(mode==ABS32) {
        if(!fetch_word(s,s->pc+2,&low))return 0;
        *address=(ext<<16)|low;s->pc+=4;return 1;
    }
    s->pc+=2;
    if(mode==ABS16){*address=signed_word(ext);return 1;}
    if(mode==DISP16 || mode==PCDISP){*address=base+signed_word(ext);return 1;}
    /* Native brief index ignores scale/full-format bits. It selects one of
     * all 16 Dn/An registers, sign-extends word indexes and the low byte. */
    unsigned index=ext>>12;uint32_t value=index<8?s->r.d[index]:s->r.a[index-8];
    if(!(ext&0x800))value=signed_word(value&65535u);
    uint32_t displacement=ext&0x80?(ext&255)|0xffffff00u:ext&255;
    *address=base+value+displacement;return 1;
}
static a68k_boundary memory_source(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                 enum binary_op op,unsigned bits,unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t address,value;s->pc+=2;
    if(!effective_address(s,opcode&7,bits/8,mode,&address))return A68K_BINDING_ERROR;
    a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
    /* Match native publishing before the bus callback; An updates have already
     * happened. Do not reload the live PC from the published context afterward. */
    int address_op=op==MOVEA || op==ADDA || op==SUBA || op==CMPA;
    s->r.pc=s->pc;
    /* These native handlers save live EDX into the public context before the
     * read and reload it afterward. Device-observed flags differ from Dn ops. */
    if(address_op)s->r.flags=s->flags;
    if(observation) {
        a68k_read_result read;
        if(!a68k_read_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,bits/8,&read,observation))return A68K_BINDING_ERROR;
        value=read.value;host=observation->control_flags;
        /* Native operations write Dn/An in memory, leaving read EAX live.
         * Word address operations first use CWDE, changing the full EAX. */
        if(address_op && bits==16)observation->eax=signed_word(value&65535u);
    } else if(!a68k_read(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,bits/8,&value))return A68K_BINDING_ERROR;
    if(address_op)s->flags=s->r.flags;
    binary_value(s,address_op?&s->r.a[(opcode>>9)&7]:&s->r.d[(opcode>>9)&7],value,bits,op,host);
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary scc_memory(a68k_cpu *s,uint16_t opcode,unsigned cc,unsigned cost,enum ea_mode mode,a68k_host_state *host) {
    /* Native ST and most conditional stores retain EAX's high bytes. SF
     * clears all of EAX; displacement/index modes produce EAX themselves. */
    if(cc!=1 && mode!=DISP16 && mode!=INDEXED && !s->entry_eax_valid)return A68K_BINDING_ERROR;
    uint32_t value=s->entry_eax,address,ext;s->pc+=2;
    if(mode==DISP16 || mode==INDEXED) {
        if(!fetch_word(s,s->pc,&ext))return A68K_BINDING_ERROR;
        if(mode==DISP16)value=signed_word(ext);
        else {
            unsigned index=ext>>12;value=index<8?s->r.d[index]:s->r.a[index-8];
            if(!(ext&0x800))value=signed_word(value&65535u);
        }
    }
    if(!effective_address(s,opcode&7,1,mode,&address))return A68K_BINDING_ERROR;
    int taken=condition(s,cc);
    if(cc==1)value=0;
    else {
        /* Only SHI/SLS use MOV AH,DL / SAHF. The single-flag conditions
         * use TEST, and signed conditions POPFD: neither overwrites AH. */
        if(cc==2 || cc==3)value=(value&0xffff00ffu)|((s->flags&255u)<<8);
        value=(value&~255u)|(taken?255u:0);
    }
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(host) {
        if(cc>=12)host->control_flags=(s->flags&0x400u)|0x202u;
        if(!write_operand_live(s,address,1,value,host,4))return A68K_BINDING_ERROR;
    } else if(!a68k_write(s->write_pages,address,1,value))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary memory_destination(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                      enum binary_op op,unsigned bits,unsigned cost,
                                      enum ea_mode mode,enum operand_source source,a68k_host_state *observation) {
    uint32_t address,value,right=0;s->pc+=2;
    if(source==IMMEDIATE_LOW) {
        if(!fetch_word(s,s->pc,&right))return A68K_BINDING_ERROR;
        s->pc+=2;
        if(bits==32) {
            uint32_t low;if(!fetch_word(s,s->pc,&low))return A68K_BINDING_ERROR;
            right=(right<<16)|low;s->pc+=2;
        }
    }
    if(!effective_address(s,opcode&7,bits/8,mode,&address))return A68K_BINDING_ERROR;
    s->r.pc=s->pc;
    if(observation) {
        a68k_read_result read;
        if(!a68k_read_live(s->data_pages,A68K_DATA_SPACE,address,bits/8,&read,observation))return A68K_BINDING_ERROR;
        value=read.value;host=observation->control_flags;
    } else if(!a68k_read(s->data_pages,A68K_DATA_SPACE,address,bits/8,&value))return A68K_BINDING_ERROR;
    if(source==REGISTER_HIGH)right=s->r.d[(opcode>>9)&7];
    else if(source==QUICK_LOW)right=(((opcode>>9)-1)&7)+1;
    uint32_t old_flags=s->flags,old_x=s->r.x;
    binary_value(s,&value,right,bits,op,host);
    uint32_t result_flags=s->flags,result_x=s->r.x;
    if(op!=CMP) {
        /* Native PUSHFD holds arithmetic flags across the write callback.
         * ADD/SUB publish X afterward; partial AL/AX results retain read
         * EAX's high bits in the callback argument. Immediate values are
         * fetched before EA calculation, quick values after the bus read. */
        s->flags=old_flags;s->r.x=old_x;s->r.pc=s->pc;
        if(observation) {
            if(!write_operand_live(s,address,bits/8,value,observation,8))return A68K_BINDING_ERROR;
        } else if(!a68k_write(s->write_pages,address,bits/8,value))return A68K_BINDING_ERROR;
    }
    s->flags=result_flags;if(op==ADD || op==SUB)s->r.x=result_x;
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary memory_unary(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                enum reg_op op,unsigned bits,unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t address,value=0;s->pc+=2;
    if(!effective_address(s,opcode&7,bits/8,mode,&address))return A68K_BINDING_ERROR;
    s->r.pc=s->pc;
    if(op==NEGX)s->r.flags=s->flags;
    if(observation && op!=CLR) {
        a68k_read_result read;
        if(!a68k_read_live(s->data_pages,A68K_DATA_SPACE,address,bits/8,&read,observation))return A68K_BINDING_ERROR;
        value=read.value;host=observation->control_flags;
        if(op==NEG || op==NOT)s->flags=read.edx;
    } else if(op==NEG || op==NOT) {
        a68k_read_result read;
        if(!a68k_read_observed(s->data_pages,A68K_DATA_SPACE,address,bits/8,&read))return A68K_BINDING_ERROR;
        value=read.value;s->flags=read.edx;
    } else if(op!=CLR && !a68k_read(s->data_pages,A68K_DATA_SPACE,address,bits/8,&value))return A68K_BINDING_ERROR;
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1,result_flags;
    if(op==CLR)result_flags=0x40; /* Original has no dummy read. */
    else if(op==NEGX) {
        s->flags=s->r.flags;value=negate_value(s,value,bits,host,1);
        result_flags=s->flags;
        /* Unlike ADD/SUB memory forms, NEGX publishes both X and merged flags
         * before its write, then reloads the published flags after the device. */
        s->r.flags=result_flags;
    } else if(op==NEG || op==NOT) {
        /* Native saves arithmetic EFLAGS on the host stack, but publishes
         * read-return EDX before writing. NEG publishes X only AFTER writing.
         * Keep callback-visible state and narrow-write high bits unchanged. */
        s->r.flags=s->flags;
        if(op==NEG) {
            uint32_t old_x=s->r.x;
            value=negate_value(s,value,bits,host,0);result_flags=s->flags;
            s->r.x=old_x;s->flags=s->r.flags;
        } else {value^=mask;result_flags=logical_flags(value&mask,bits,host);}
    } else if(op==NBCD)value=nbcd_value(value,s->r.x&1,host,&result_flags);
    else {result_flags=logical_flags(value&mask,bits,host);if(op==TAS)value|=0x80;}
    if(op!=TST) {
        s->r.pc=s->pc;
        if(observation) {
            unsigned depth = op==CLR || op==NEGX ? 4 : 8;
            int ok=write_operand_live(s,address,bits/8,value,observation,depth);
            if(!ok)return A68K_BINDING_ERROR;
        } else if(!a68k_write(s->write_pages,address,bits/8,value))return A68K_BINDING_ERROR;
    }
    s->flags=op==NEGX?s->r.flags:result_flags;
    if(op==NBCD || op==NEG)s->r.x=result_flags; /* Native POP EDX / MOV X follows write. */
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static int observe_address_eax(a68k_cpu *s,enum ea_mode mode,a68k_host_state *observation) {
    /* Native displacement/index calculations use EAX; absolute forms write
     * EDI directly. This matters for LEA and empty MOVEM masks. */
    if(observation && (mode==DISP16 || mode==PCDISP || mode==INDEXED || mode==PCINDEX)) {
        uint32_t ext;if(!fetch_word(s,s->pc,&ext))return 0;
        if(mode==DISP16 || mode==PCDISP)observation->eax=signed_word(ext);
        else {
            unsigned reg=ext>>12;uint32_t value=reg<8?s->r.d[reg]:s->r.a[reg-8];
            observation->eax=ext&0x800?value:signed_word(value&65535u);
        }
    }
    return 1;
}
enum address_op { LEA,PEA,LINK,UNLK };
static a68k_boundary address_operation(a68k_cpu *s,uint16_t opcode,enum address_op op,
                                     unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t address,value;unsigned reg=opcode&7;s->pc+=2;
    if(op==UNLK) {
        address=s->r.a[reg];s->r.pc=s->pc;s->r.flags=s->flags;
        if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,4,&value,observation))return A68K_BINDING_ERROR;
        s->flags=s->r.flags;s->r.a[reg]=value;s->r.a[7]=address+4;
    } else {
        if(op==LINK) {
            /* LINK A7 reads An after decrementing SP, as the original does. */
            s->r.a[7]-=4;value=s->r.a[reg];address=s->r.a[7];s->r.a[reg]=address;
        } else {
            if(!observe_address_eax(s,mode,observation))return A68K_BINDING_ERROR;
            if(!effective_address(s,reg,4,mode,&value))return A68K_BINDING_ERROR;
            if(op==LEA)s->r.a[(opcode>>9)&7]=value;
            else {s->r.a[7]-=4;address=s->r.a[7];}
        }
        if(op!=LEA) {
            s->r.pc=s->pc;s->r.flags=s->flags;
            if(!write_operand_live(s,address,4,value,observation,4))return A68K_BINDING_ERROR;
            s->flags=s->r.flags;
            if(op==LINK) {
                /* Fetch displacement only after the stack write callback. */
                if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
                s->pc+=2;s->r.a[7]+=signed_word(value);
                if(observation)observation->eax=signed_word(value);
            }
        }
    }
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
enum bit_op { BTST,BCHG,BCLR,BSET };
static a68k_boundary bit_operation(a68k_cpu *s,uint16_t opcode,enum bit_op op,
                                  unsigned cost,enum ea_mode mode,enum operand_source source,a68k_host_state *observation) {
    uint32_t count,value,address=0;unsigned reg=opcode&7;s->pc+=2;
    if(source==IMMEDIATE_LOW) {
        if(!fetch_word(s,s->pc,&count))return A68K_BINDING_ERROR;
        s->pc+=2;
    } else count=s->r.d[(opcode>>9)&7];
    uint32_t mask=1u<<(count&(mode==REGISTER?31:7));
    if(mode==REGISTER)value=s->r.d[reg];
    else if(mode==IMMEDIATE) {
        /* Native BTST Dn,#word tests only the low byte; this is a dispatch
         * capability of the original, not a normalized instruction decoder. */
        if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
        s->pc+=2;if(observation)observation->eax=value;
    } else {
        if(!effective_address(s,reg,1,mode,&address))return A68K_BINDING_ERROR;
        s->r.pc=s->pc;s->r.flags=s->flags;
        a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
        if(!read_operand_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,1,&value,observation))return A68K_BINDING_ERROR;
        s->flags=s->r.flags;
    }
    /* Native OR/XOR updates Z in saved EDX, not a fresh x86 arithmetic CCR. */
    s->flags=(s->flags&~0x40u)|((value&mask)?0:0x40u);
    if(op!=BTST) {
        value=op==BCHG?value^mask:op==BCLR?value&~mask:value|mask;
        if(mode==REGISTER)s->r.d[reg]=value;
        else {
            s->r.pc=s->pc;s->r.flags=s->flags;
            if(!write_operand_live(s,address,1,value,observation,4))return A68K_BINDING_ERROR;
            s->flags=s->r.flags;
        }
    }
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary move_destination(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                     unsigned bits,unsigned cost,enum ea_mode mode,enum operand_source source,
                                     a68k_host_state *observation) {
    uint32_t value,address;s->pc+=2;
    if(source==IMMEDIATE_LOW) {
        if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
        s->pc+=2;
        if(bits==32) {
            uint32_t low;if(!fetch_word(s,s->pc,&low))return A68K_BINDING_ERROR;
            value=(value<<16)|low;s->pc+=2;
        }
    } else {
        unsigned reg=opcode&15;value=reg<8?s->r.d[reg]:s->r.a[reg-8];
    }
    /* Source and TEST flags are captured before destination EA side effects.
     * Native byte/word writes pass full EAX to callbacks, including high bits. */
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1;
    uint32_t result_flags=logical_flags(value&mask,bits,host);
    if(!effective_address(s,(opcode>>9)&7,bits/8,mode,&address))return A68K_BINDING_ERROR;
    s->r.pc=s->pc;
    /* Make68K movecodes passes "---DS-B" to Memory_Write: EAX is not
     * saved. ElSemi likewise leaves the wrapper/callback return in EAX,
     * while POP EDX restores the pre-write TEST flags from its own stack.
     * Host DF after the write can therefore differ from those guest flags. */
    if(observation) {
        if(!write_operand_live(s,address,bits/8,value,observation,8))return A68K_BINDING_ERROR;
    } else if(!a68k_write(s->write_pages,address,bits/8,value))return A68K_BINDING_ERROR;
    s->flags=result_flags;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary move_memory(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                unsigned bits,unsigned cost,enum ea_mode source,enum ea_mode destination,a68k_host_state *observation) {
    uint32_t address,value;s->pc+=2;
    if(!effective_address(s,opcode&7,bits/8,source,&address))return A68K_BINDING_ERROR;
    a68k_read_space space=source==PCDISP || source==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
    s->r.pc=s->pc;
    if(observation) {
        a68k_read_result read;
        if(!a68k_read_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,bits/8,&read,observation))return A68K_BINDING_ERROR;
        value=read.value;host=observation->control_flags;
    } else if(!a68k_read(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,bits/8,&value))return A68K_BINDING_ERROR;
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1;
    uint32_t result_flags=logical_flags(value&mask,bits,host);
    /* Destination addressing observes source An updates and callback effects.
     * Preserve the full read EAX while calculating the second effective address. */
    if(!effective_address(s,(opcode>>9)&7,bits/8,destination,&address))return A68K_BINDING_ERROR;
    s->r.pc=s->pc;
    if(observation) {
        if(!write_operand_live(s,address,bits/8,value,observation,8))return A68K_BINDING_ERROR;
    } else if(!a68k_write(s->write_pages,address,bits/8,value))return A68K_BINDING_ERROR;
    s->flags=result_flags;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary multiply(a68k_cpu *s,uint16_t opcode,uint32_t host,
                              unsigned is_signed,unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t value,address;s->pc+=2;
    if(mode==REGISTER)value=s->r.d[opcode&7];
    else if(mode==IMMEDIATE) {
        if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
        s->pc+=2;
    } else {
        if(!effective_address(s,opcode&7,2,mode,&address))return A68K_BINDING_ERROR;
        a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
        s->r.pc=s->pc;
        if(observation) {
            a68k_read_result read;
            if(!a68k_read_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,2,&read,observation))return A68K_BINDING_ERROR;
            value=read.value;host=observation->control_flags;
        } else if(!a68k_read(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,2,&value))return A68K_BINDING_ERROR;
    }
    /* Make68K mul(): native MUL/IMUL word produces DX:AX, reconstructed as a
     * full 32-bit Dn. TEST of that product supplies flags; X is untouched.
     * Preserve ElSemi's fixed costs, including its 54-cycle immediate form,
     * rather than substituting hardware operand-dependent multiplication time. */
    unsigned reg=(opcode>>9)&7;
    int64_t left=s->r.d[reg]&65535u,right=value&65535u;
    if(is_signed){if(left&0x8000)left-=65536;if(right&0x8000)right-=65536;}
    uint32_t product=(uint32_t)(left*right);
    if(observation)observation->eax=(value&0xffff0000u)|(product&65535u);
    s->r.d[reg]=product;s->flags=logical_flags(product,32,host);s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary rotate_register(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                     unsigned bits,unsigned left,unsigned extend,unsigned variable,unsigned cost) {
    unsigned reg=opcode&7;
    unsigned count=variable?s->r.d[(opcode>>9)&7]&63u:(((opcode>>9)-1)&7)+1;
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1;
    uint32_t value=s->r.d[reg]&mask;
    /* Make68K rol_ror()/roxl_roxr(): the guest count is masked to 63 for
     * timing, then x86 masks it to 31 for execution. For ROR/ROL count 32,
     * the rotate leaves CF from the preceding cycle-budget SUB intact.
     * Keep that original host-flag dependency explicit, not a guest-CPU fix. */
    unsigned carry=extend?s->r.x&1u:count!=0 && s->cycles<count*2;
    unsigned actual=count&31u;
    if(extend && bits<32)actual%=bits+1;
    for(unsigned i=0;i<actual;i++) {
        unsigned out=left?value>>(bits-1):value&1u;
        unsigned in=extend?carry:out;
        value=left?((value<<1)|in)&mask:(value>>1)|(in<<(bits-1));
        carry=out;
    }
    s->pc+=2;s->cycles-=count*2;
    s->r.d[reg]=(s->r.d[reg]&~mask)|value;
    s->flags=logical_flags(value,bits,host)|carry;
    /* Native ROX writes DL only, preserving the other three bytes of X.
     * Zero guest count copies X into C without writing X at all. */
    if(extend && count)s->r.x=(s->r.x&0xffffff00u)|(s->flags&255u);
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
enum shift_op { ASR,ASL,LSR,LSL,ROXR,ROXL,ROR,ROL };
static a68k_boundary shift_register(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                     enum shift_op op,unsigned bits,unsigned variable,unsigned cost,unsigned special) {
    unsigned reg=opcode&7,count=variable?s->r.d[(opcode>>9)&7]&63u:(((opcode>>9)-1)&7)+1;
    uint32_t mask=bits==32?0xffffffffu:(1u<<bits)-1,sign=1u<<(bits-1);
    uint32_t value=s->r.d[reg]&mask,result=value,flags;unsigned carry=0;
    s->pc+=2;
    if(!count) {
        /* Native ASL alone retains old C on zero guest count. */
        flags=logical_flags(value,bits,host)|(op==ASL?s->flags&1u:0);
    } else {
        if(!special)s->cycles-=2*count;
        if(op==ASR) {
            unsigned actual=count>=32?31:count;
            for(unsigned i=0;i<actual;i++){carry=result&1u;result=(result>>1)|(result&sign);}
            /* Make68K asl_asr() captures LAHF only on this path. */
            flags=(logical_flags(result,bits,host)&255u)|carry;s->r.x=flags;
        } else if(op==ASL) {
            if(special) {
                carry=value>>(bits-1);result=(value<<1)&mask;
                flags=logical_flags(result,bits,host)|carry|(((result^value)&sign)?0x800u:0);
                s->r.x=flags;
            } else {
                unsigned actual=count&31u;uint32_t overflow_mask=sign;
                for(unsigned i=0;i<actual;i++)overflow_mask=(overflow_mask>>1)|sign;
                uint32_t selected=value&overflow_mask;
                unsigned overflow=selected && selected!=overflow_mask?0x800u:0;
                if(bits==32 && count>=32) {
                    /* Native long big-shift tail writes Z/V but does not update X. */
                    result=0;flags=overflow|0x40u;
                } else {
                    for(unsigned i=0;i<actual;i++){carry=result>>(bits-1);result=(result<<1)&mask;}
                    /* Narrow count 32 leaves the shift untouched: LAHF observes
                     * the equal/zero overflow-mask comparison, not TEST(result). */
                    flags=(actual?logical_flags(result,bits,host)&255u:0x46u)|carry|overflow;
                    s->r.x=flags;
                }
            }
        } else {
            unsigned actual=count;
            for(unsigned i=0;i<actual;i++) {
                carry=op==LSL?result>>(bits-1):result&1u;
                result=op==LSL?(result<<1)&mask:result>>1;
            }
            /* Original handles 32..63 with two shifts by 16 before CL. This
             * yields the same value/carry here; XOR DH,DH removes bits 8..15. */
            flags=(logical_flags(result,bits,host)|carry)&~0xff00u;s->r.x=flags;
        }
    }
    s->r.d[reg]=(s->r.d[reg]&~mask)|result;s->flags=flags;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary shift_memory(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                  enum shift_op op,unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t address,value;s->pc+=2;
    if(!effective_address(s,opcode&7,2,mode,&address))return A68K_BINDING_ERROR;
    s->r.pc=s->pc;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,2,&value,observation))return A68K_BINDING_ERROR;
    if(observation)host=observation->control_flags;
    unsigned left=op&1,carry=left?(value>>15)&1u:value&1u;
    unsigned incoming=op==ASR?(value>>15)&1u:
        op==ROXR || op==ROXL?s->r.x&1u:op==ROR || op==ROL?carry:0;
    uint32_t result=left?((value<<1)|incoming)&65535u:((value&65535u)>>1)|(incoming<<15);
    uint32_t result_flags=logical_flags(result,16,host)|carry;
    if(op==ASL || op==LSL)result_flags|=(((result>>15)^carry)&1u)<<11;
    else if(op==LSR)result_flags|=((value>>15)&1u)<<11;
    /* Historical *_ea generators intentionally have different publication:
     * arithmetic shifts hold flags/X until after the write; logical shifts
     * save full X first, then XOR DH,DH (all saved bits 8..15, not only V).
     * ROX reloads flags after the write before copying them into full X. */
    if(op==LSR || op==LSL){s->r.x=result_flags;result_flags&=~0xff00u;}
    if(op!=ASR && op!=ASL)s->r.flags=result_flags;
    s->r.pc=s->pc;
    if(!write_operand_live(s,address,2,(value&0xffff0000u)|result,observation,
                           op==ASR || op==ASL ? 8 : 4))return A68K_BINDING_ERROR;
    s->flags=op==ASR || op==ASL?result_flags:s->r.flags;
    if(op==ASR || op==ASL || op==ROXR || op==ROXL)s->r.x=s->flags;
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary transfer_control(a68k_cpu *s,uint32_t target,a68k_host_state *observation) {
    s->pc=target;
    if(target&1) {
        s->pc-=2;return exception_frame(s,3,observation);
    }
    if(observation?!s->bind_observed:!s->bind)return A68K_BINDING_ERROR;
    s->r.raw_pc=s->pc;s->pc&=s->address_mask;s->r.flags=s->flags;
    if(observation) {
        a68k_host_state result=s->bind_observed(s->user,s->pc,observation->control_flags);
        if(!result.valid)return A68K_BINDING_ERROR;
        *observation=result;
    } else s->bind(s->user,s->pc);
    s->flags=s->r.flags;
    return A68K_RETURN;
}
/* Make68K abcd_sbcd(): native ADC/DAA or SBB/DAS, followed by SETC DL.
 * Preserve all high flag bytes (including V), sticky Z and N copied from C;
 * these are the original emitter's choices, not corrected 68000 semantics. */
static uint32_t bcd_value(a68k_cpu *s,uint32_t left,uint32_t right,int subtract) {
    left&=255u;right&=255u;uint32_t x=s->r.x&1;
    uint32_t raw=subtract?(left-right-x)&255u:(left+right+x)&255u;
    unsigned carry=subtract?left<right+x:left+right+x>255;
    unsigned auxiliary=subtract?(left&15)<(right&15)+x:(left&15)+(right&15)+x>15;
    uint32_t value=raw;unsigned old_carry=carry;
    if((raw&15)>9 || auxiliary) {
        if(subtract){carry=old_carry || raw<6;value=(value-6)&255u;}
        else {carry=old_carry || raw+6>255;value=(value+6)&255u;}
    }
    if(raw>0x99 || old_carry){value=(value+(subtract?0xa0u:0x60u))&255u;carry=1;}
    else if(!subtract)carry=0;
    s->flags=(s->flags&~255u)|(carry?0x81u:0)|(!value?s->flags&0x40u:0);
    s->r.x=s->flags;return value;
}
static a68k_boundary bcd_register(a68k_cpu *s,uint16_t opcode,int subtract) {
    unsigned reg=(opcode>>9)&7;
    uint32_t value=bcd_value(s,s->r.d[reg],s->r.d[opcode&7],subtract);
    s->r.d[reg]=(s->r.d[reg]&~255u)|value;
    s->pc+=2;s->cycles-=6;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Native memory BCD publishes/reloads saved flags around both reads, unlike
 * memory ADDX/SUBX's explicit host-scratch dependency. Retain the destination
 * read's high bytes in the write argument and publish X before that write. */
static a68k_boundary bcd_memory(a68k_cpu *s,uint16_t opcode,int subtract,a68k_host_state *observation) {
    unsigned src=opcode&7,dst=(opcode>>9)&7;uint32_t right,left,address;s->pc+=2;
    s->r.a[src]-=src==7?2:1;s->r.pc=s->pc;s->r.flags=s->flags;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,s->r.a[src],1,&right,observation))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;s->r.a[dst]-=dst==7?2:1;address=s->r.a[dst];
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,1,&left,observation))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;uint32_t value=(left&~255u)|bcd_value(s,left,right,subtract);
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(!write_operand_live(s,address,1,value,observation,4))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;s->cycles-=18;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary extend_memory(a68k_cpu *s,uint16_t opcode,uint32_t host,
                                    enum binary_op op,unsigned bits,unsigned cost,a68k_host_state *observation) {
    unsigned src=opcode&7,dst=(opcode>>9)&7,width=bits/8;
    uint32_t right,address;a68k_read_result left;s->pc+=2;
    s->r.a[src]-=width==1 && src==7?2:width;s->r.pc=s->pc;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,s->r.a[src],width,&right,observation))return A68K_BINDING_ERROR;
    s->r.a[dst]-=width==1 && dst==7?2:width;address=s->r.a[dst];s->r.pc=s->pc;
    if(observation) {
        if(!a68k_read_live(s->data_pages,A68K_DATA_SPACE,address,width,&left,observation))return A68K_BINDING_ERROR;
        host=observation->control_flags;
    } else if(!a68k_read_observed(s->data_pages,A68K_DATA_SPACE,address,width,&left))return A68K_BINDING_ERROR;
    /* Original ADC/SBB merges sticky Z from the second read's EDX, not the
     * incoming guest flags or the first read. X receives full arithmetic
     * flags before that merge. The shared arithmetic helper preserves both. */
    s->flags=left.edx;uint32_t value=left.value;
    binary_value(s,&value,right,bits,op,host);
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(!write_operand_live(s,address,width,value,observation,4))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary nbcd_register(a68k_cpu *s,uint16_t opcode,uint32_t host,unsigned cost) {
    unsigned reg=opcode&7;
    uint32_t value=nbcd_value(s->r.d[reg],s->r.x&1,host,&s->flags);
    s->r.x=s->flags;s->r.d[reg]=(s->r.d[reg]&~255u)|value;
    s->pc+=2;s->cycles-=cost;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Native RTS reads after incrementing A7, and publishes the current PC
 * without first adding two. Return binding preserves raw-PC high bits. */
static a68k_boundary return_subroutine(a68k_cpu *s,a68k_host_state *observation) {
    uint32_t address=s->r.a[7],target;s->r.a[7]+=4;
    s->r.pc=s->pc;s->r.flags=s->flags;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,4,&target,observation))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;
    a68k_boundary result=transfer_control(s,target,observation);
    if(result!=A68K_RETURN)return result;
    s->cycles-=16;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Later-CPU entries are gated by the original context+0x7c field. RTD lacks
 * the usual ADD ESI,2: it reads the displacement at the opcode address. This
 * is preserved, not repaired to standard 68010 semantics. */
static a68k_boundary return_deallocate(a68k_cpu *s,uint16_t opcode,a68k_host_state *observation) {
    if(!s->r.opaque31) {
        s->illegal_opcode=opcode;s->illegal_pc=s->pc;s->pc-=2;return trap(s,4,2,observation);
    }
    uint32_t target,displacement;s->r.pc=s->pc;s->r.flags=s->flags;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,s->r.a[7],4,&target,observation))return A68K_BINDING_ERROR;
    s->flags=s->r.flags;
    if(!fetch_word(s,s->pc,&displacement))return A68K_BINDING_ERROR;
    s->r.a[7]+=signed_word(displacement)+4;
    a68k_boundary status=transfer_control(s,target,observation);if(status!=A68K_RETURN)return status;
    s->cycles-=16;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary move_control(a68k_cpu *s,uint16_t opcode,int to_control,a68k_host_state *observation) {
    if(!s->r.opaque31) {
        s->illegal_opcode=opcode;s->illegal_pc=s->pc;s->pc-=2;return trap(s,4,2,observation);
    }
    if(!(s->r.sr_high&0x20)) {
        /* Native privilege path subtracts two without a preceding increment. */
        s->pc-=2;a68k_boundary status=exception_frame(s,8,observation);
        if(status!=A68K_RETURN)return status;
    } else {
        uint32_t ext;s->pc+=2;if(!fetch_word(s,s->pc,&ext))return A68K_BINDING_ERROR;s->pc+=2;
        unsigned reg=ext>>12,control=(ext&1)|((ext>>10)&2);
        uint32_t *general=reg<8?&s->r.d[reg]:&s->r.a[reg-8];
        uint32_t *special=control<2?&s->r.opaque24[control+2]:control==2?&s->r.usp:&s->r.vbr;
        /* Only selector bits 11 and 0 are decoded. Other bits alias these
         * four slots rather than generating an illegal-control exception. */
        uint32_t value=to_control?(control<2?*general&7u:*general):*special;
        if(to_control)*special=value;else *general=value;
        if(observation)observation->eax=value;
    }
    s->cycles-=4;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Make68K ReturnandRestore, original RTR 00485c40 / RTE 00487008.
 * Both publish the full first read as PC before the second stack read.
 * X receives the table's entire high byte (including V), not just X bit 0.
 * RTE restores only the low byte of sr_high and rechecks IRQ after charging
 * its own cycles; RTR neither changes supervisor state nor rechecks IRQ. */
static void import_status(a68k_cpu *s,uint32_t sr,int entire_sr) {
    if(entire_sr) {
        if(!(sr&0x2000)) {s->r.ssp=s->r.a[7];s->r.a[7]=s->r.usp;}
        s->r.sr_high=(s->r.sr_high&~255u)|((sr>>8)&255u);
    }
    uint32_t table=(sr&1)|((sr&12)<<4)|((sr&2)<<10)|((sr&16)<<4);
    s->r.x=(s->r.x&~255u)|(table>>8);s->flags=table&0xeffu;
}
static a68k_boundary return_restore(a68k_cpu *s,int entire_sr,a68k_host_state *observation) {
    s->pc+=2;
    a68k_boundary status;
    if(entire_sr && !(s->r.sr_high&0x20)) {
        s->pc-=2;status=exception_frame(s,8,observation);
    } else {
        uint32_t address=s->r.a[7],sr,target;s->r.a[7]+=6;
        s->r.pc=s->pc;
        if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,2,&sr,observation))return A68K_BINDING_ERROR;
        s->pc=sr;s->r.pc=s->pc;
        if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address+2,4,&target,observation))return A68K_BINDING_ERROR;
        import_status(s,sr,entire_sr);
        status=transfer_control(s,target,observation);
    }
    if(status!=A68K_RETURN)return status;
    s->cycles-=20;
    if(s->cycles&0x80000000u)return exit_dispatch(s);
    return entire_sr && (s->r.irq&7)?interrupt_live(s,observation):A68K_FETCH;
}
static uint32_t export_status(const a68k_cpu *s,int entire_sr) {
    uint32_t ccr=(s->flags&1)|((s->flags>>4)&12)|((s->flags>>10)&2)|((s->r.x&1)<<4);
    return ccr|(entire_sr?(s->r.sr_high&255)<<8:0);
}
static a68k_boundary status_logic(a68k_cpu *s,enum binary_op op,int entire_sr,a68k_host_state *observation) {
    s->pc+=2;
    if(entire_sr && !(s->r.sr_high&0x20)) {
        s->pc-=2;a68k_boundary status=exception_frame(s,8,observation);
        if(status!=A68K_RETURN)return status;
        /* Native logical-immediate privilege tail does NOT recheck IRQ. */
        s->cycles-=20;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
    }
    uint32_t value;if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;
    s->pc+=2;uint32_t old=export_status(s,entire_sr);
    uint32_t result=op==OR?old|value:op==AND?old&value:old^value;
    import_status(s,result,entire_sr);
    if(observation)observation->eax=result&31u; /* Native WriteCCR AND EAX,1f. */
    s->cycles-=20;if(s->cycles&0x80000000u)return exit_dispatch(s);
    return entire_sr && (s->r.irq&7)?interrupt_live(s,observation):A68K_FETCH;
}
enum status_move_op { FROM_SR,FROM_CCR,TO_CCR,TO_SR };
static a68k_boundary status_move(a68k_cpu *s,uint16_t opcode,enum status_move_op op,
                                 unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    s->pc+=2;
    /* Original context+0x7c gates the later-CPU CCR export encodings. Preserve
     * the native ILLEGAL entry's advanced-PC metadata and subsequent PC-2. */
    if(op==FROM_CCR && !s->r.opaque31) {
        s->illegal_opcode=opcode;s->illegal_pc=s->pc;s->pc-=2;return trap(s,4,2,observation);
    }
    if(op==TO_SR && !(s->r.sr_high&0x20)) {
        s->pc-=2;a68k_boundary status=exception_frame(s,8,observation);
        if(status!=A68K_RETURN)return status;
    } else {
        unsigned reg=opcode&7;uint32_t value,address;
        if(op==FROM_SR || op==FROM_CCR) {
            value=export_status(s,op==FROM_SR);
            if(observation)observation->eax=value;
            if(mode==REGISTER)s->r.d[reg]=(s->r.d[reg]&0xffff0000u)|value;
            else {
                if(!effective_address(s,reg,2,mode,&address))return A68K_BINDING_ERROR;
                s->r.pc=s->pc;s->r.flags=s->flags;
                if(!write_operand_live(s,address,2,value,observation,4))return A68K_BINDING_ERROR;
                s->flags=s->r.flags;
            }
        } else {
            if(mode==REGISTER)value=s->r.d[reg];
            else if(mode==IMMEDIATE) {
                if(!fetch_word(s,s->pc,&value))return A68K_BINDING_ERROR;s->pc+=2;
            } else {
                if(!effective_address(s,reg,2,mode,&address))return A68K_BINDING_ERROR;
                a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
                s->r.pc=s->pc;
                if(!read_operand_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,2,&value,observation))return A68K_BINDING_ERROR;
            }
            import_status(s,value,op==TO_SR);
            if(observation)observation->eax=value&31u;
        }
    }
    s->cycles-=cost;if(s->cycles&0x80000000u)return exit_dispatch(s);
    /* Unlike immediate logic, MOVE-to-SR also rechecks IRQ after privilege. */
    return op==TO_SR && (s->r.irq&7)?interrupt_live(s,observation):A68K_FETCH;
}
/* Native STOP enters an accepted IRQ before charging four cycles. Otherwise
 * it discards the remaining budget, marks bit 7 in IRQ and exits at -4.
 * This is the original scheduling contract, not a generic 68000 idle model. */
static a68k_boundary stop_instruction(a68k_cpu *s,a68k_host_state *observation) {
    s->pc+=2;
    if(!(s->r.sr_high&0x20)) {
        s->pc-=2;a68k_boundary status=exception_frame(s,8,observation);
        if(status!=A68K_RETURN)return status;
        s->cycles-=4;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
    }
    uint32_t sr;if(!fetch_word(s,s->pc,&sr))return A68K_BINDING_ERROR;
    s->pc+=2;import_status(s,sr,1);
    unsigned irq=s->r.irq&7;
    if(observation)observation->eax=irq;
    if(irq==7 || irq>(s->r.sr_high&7))return interrupt_live(s,observation);
    s->r.irq|=0x80;s->cycles=0xfffffffcu;return exit_dispatch(s);
}
static a68k_boundary reset_instruction(a68k_cpu *s,a68k_host_state *observation) {
    s->pc+=2;
    if(!(s->r.sr_high&0x20)) {
        s->pc-=2;a68k_boundary status=exception_frame(s,8,observation);
        if(status!=A68K_RETURN)return status;
        s->cycles-=132;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
    }
    /* Original fetches before invoking RESET output, then jumps directly to
     * the saved opcode. Callback changes to PC/flags/binding do not discard
     * this prefetch, and a negative budget does not cause an exit here. */
    if(!fetch_word(s,s->pc,&s->prefetched_opcode))return A68K_BINDING_ERROR;
    if(observation)observation->eax=s->r.opaque24[1];
    if(s->r.opaque24[1]) {
        if(observation?!s->reset_observed:!s->reset_output)return A68K_BINDING_ERROR;
        s->r.pc=s->pc;s->r.flags=s->flags;
        if(observation) {
            a68k_host_state result=s->reset_observed(s->user,observation->control_flags);
            if(!result.valid)return A68K_BINDING_ERROR;
            *observation=result;
        } else s->reset_output(s->user);
        s->pc=s->r.pc;s->flags=s->r.flags;
    }
    s->cycles-=132;return A68K_PREFETCHED;
}
/* Native MOVEP captures flags before any bus call and rotates the whole Dn
 * into the byte-write argument. Do not truncate callback values to a byte. */
static a68k_boundary move_peripheral(a68k_cpu *s,uint16_t opcode,unsigned size,int write,a68k_host_state *observation) {
    uint32_t ext,address,value=0,flags=s->flags;unsigned reg=(opcode>>9)&7;
    s->pc+=2;if(!fetch_word(s,s->pc,&ext))return A68K_BINDING_ERROR;
    address=s->r.a[opcode&7]+signed_word(ext);s->pc+=2;
    if(write)value=s->r.d[reg];
    for(unsigned i=0;i<size;i++,address+=2) {
        s->r.pc=s->pc;
        if(write) {
            unsigned shift=((size==2?3u:1u)+i)%4*8;
            uint32_t rotated=shift?(value<<shift)|(value>>(32-shift)):value;
            if(!write_operand_live(s,address,1,rotated,observation,i+1==size ? 12 : 16))return A68K_BINDING_ERROR;
        } else {
            uint32_t byte;
            if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,1,&byte,observation))return A68K_BINDING_ERROR;
            value=(value<<8)|(byte&255u);
        }
    }
    /* movep's A---S-B write mask restores EAX around every byte write.
     * Both sequences finish after a total rotation of 32, retaining Dn. */
    if(write && observation)observation->eax=value;
    if(!write)s->r.d[reg]=size==2?(s->r.d[reg]&0xffff0000u)|value:value;
    s->flags=flags;s->cycles-=size==2?28:36;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* CMPM increments each address register immediately before its own read.
 * Aliasing source and destination therefore observes two successive addresses.
 * No flags are published before either read; X is untouched by native CMP. */
static a68k_boundary compare_memory_pair(a68k_cpu *s,uint16_t opcode,unsigned bits,uint32_t host,a68k_host_state *observation) {
    unsigned src=opcode&7,dst=(opcode>>9)&7,width=bits/8;
    uint32_t address=s->r.a[src],right,left;s->pc+=2;
    s->r.a[src]+=width==1 && src==7?2:width;s->r.pc=s->pc;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,width,&right,observation))return A68K_BINDING_ERROR;
    address=s->r.a[dst];s->r.a[dst]+=width==1 && dst==7?2:width;s->r.pc=s->pc;
    if(!read_operand_live(s->data_pages,A68K_DATA_SPACE,address,width,&left,observation))return A68K_BINDING_ERROR;
    if(observation)host=observation->control_flags;
    binary_value(s,&left,right,bits,CMP,host);s->cycles-=bits==32?20:12;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Historical movem emitter keeps its register mask in EDX and publishes that
 * mask, not guest flags, around each bus call. Flags are saved separately.
 * Predecrement stores the original base-register value; the final address is
 * committed only at the end. Native postincrement temporarily adds four even
 * for word transfers and exits on zero budget as well as negative budget. */
static a68k_boundary move_multiple(a68k_cpu *s,uint16_t opcode,unsigned bits,
                                   int read,unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    unsigned base=opcode&7,width=bits/8;uint32_t mask,address,flags=s->flags;
    s->pc+=2;if(!fetch_word(s,s->pc,&mask))return A68K_BINDING_ERROR;s->pc+=2;
    if(!observe_address_eax(s,mode,observation))return A68K_BINDING_ERROR;
    if(mode==PREDEC || mode==POSTINC) {
        address=s->r.a[base];if(mode==POSTINC)s->r.a[base]+=4;
    } else if(!effective_address(s,base,width,mode,&address))return A68K_BINDING_ERROR;
    a68k_read_space space=mode==PCDISP || mode==PCINDEX?A68K_READ_SPACE:A68K_DATA_SPACE;
    for(unsigned i=0;i<16;i++) {
        if(!(mask&(1u<<i)))continue;
        unsigned reg=mode==PREDEC?15-i:i;
        uint32_t *destination=reg<8?&s->r.d[reg]:&s->r.a[reg-8],value=*destination;
        if(mode==PREDEC)address-=width;
        s->r.pc=s->pc;s->r.flags=mask;
        if(read) {
            if(!read_operand_live(space==A68K_READ_SPACE?s->read_pages:s->data_pages,space,address,width,&value,observation))return A68K_BINDING_ERROR;
            mask=s->r.flags;*destination=bits==16?signed_word(value&65535u):value;
            if(observation)observation->eax=*destination;
        } else {
            if(!write_operand_live(s,address,width,value,observation,mode==PREDEC ? 20 : 16))return A68K_BINDING_ERROR;
            mask=s->r.flags;
        }
        if(mode!=PREDEC)address+=width;
        s->cycles-=bits==16?4:8;
    }
    if(mode==PREDEC || mode==POSTINC)s->r.a[base]=address;
    s->flags=flags;s->cycles-=cost;
    return (s->cycles&0x80000000u) || (mode==POSTINC && !s->cycles)?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary jump(a68k_cpu *s,uint16_t opcode,unsigned subroutine,
                           unsigned cost,enum ea_mode mode,a68k_host_state *observation) {
    uint32_t address;s->pc+=2;
    if(!effective_address(s,opcode&7,4,mode,&address))return A68K_BINDING_ERROR;
    if(subroutine) {
        if(!observation && !s->stack_long)return A68K_BINDING_ERROR;
        s->r.a[7]-=4;s->r.pc=s->pc;s->r.flags=s->flags;
        /* Historical PushPC/KEEPHIGHPC: keep the previous raw-PC high byte.
         * The target EA is captured before the stack update, including A7. */
        uint32_t return_pc=s->pc|(s->r.raw_pc&0xff000000u);
        if(observation) {
            if(!write_operand_live(s,s->r.a[7],4,return_pc,observation,8))return A68K_BINDING_ERROR;
        } else s->stack_long(s->user,s->r.a[7],return_pc);
        s->flags=s->r.flags;
    }
    a68k_boundary status=transfer_control(s,address,observation);
    if(status!=A68K_RETURN)return status;
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
static a68k_boundary control_op(a68k_cpu *s,uint16_t opcode,enum control_op op,unsigned cc,a68k_host_state *observation) {
    unsigned reg=opcode&7,cost;uint32_t displacement;
    if(op==SCC) {
        s->pc+=2;int take=condition(s,cc);
        s->r.d[reg]=(s->r.d[reg]&0xffffff00u)|(take?255u:0);cost=take?6:4;
    } else if(op==DBCC) {
        int take=condition(s,cc);uint32_t old=s->r.d[reg];
        if(!take)s->r.d[reg]=(old&0xffff0000u)|((old-1)&65535u);
        if(take || !(old&65535u)){s->pc+=4;cost=12;}
        else {
            s->pc+=2;if(!fetch_word(s,s->pc,&displacement))return A68K_BINDING_ERROR;
            /* Native DBcc neither checks odd targets nor rebinds/masks PC. */
            s->pc+=signed_word(displacement);cost=10;
        }
    } else {
        s->pc+=2;int take=cc==1?1:condition(s,cc);
        if(observation) {
            if(cc==2 || cc==3)observation->eax=(observation->eax&~0xff00u)|((s->flags&255u)<<8);
            if(cc>=12)observation->control_flags=(s->flags&0x400u)|0x202u;
        }
        if(!take){if(op==BR_WORD)s->pc+=2;cost=8;}
        else {
            if(op==BR_WORD) {
                if(!fetch_word(s,s->pc,&displacement))return A68K_BINDING_ERROR;
                displacement=signed_word(displacement);
            } else displacement=(opcode&0x80)?0xffffff00u|(opcode&255u):opcode&255u;
            uint32_t target=s->pc+displacement;
            if(cc==1) {
                if(!observation && !s->stack_long)return A68K_BINDING_ERROR;
                if(op==BR_WORD)s->pc+=2;
                s->r.a[7]-=4;s->r.pc=s->pc;s->r.flags=s->flags;
                /* Original retains the last raw-PC high byte in BSR's return
                 * address even when current live PC has been masked. */
                uint32_t return_pc=s->pc|(s->r.raw_pc&0xff000000u);
                if(observation) {
                    if(!write_operand_live(s,s->r.a[7],4,return_pc,observation,op==BR_WORD ? 4 : 8))return A68K_BINDING_ERROR;
                } else s->stack_long(s->user,s->r.a[7],return_pc);
                s->flags=s->r.flags;
            }
            cost=cc==1?18:10;
            a68k_boundary status=transfer_control(s,target,observation);
            if(status!=A68K_RETURN)return status;
        }
    }
    s->cycles-=cost;return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* TRAP advances its saved exception PC; native TRAPV with V set backs up
 * that increment. Its post-exception charge uses JS, not TRAP's TEST/JLE. */
static a68k_boundary software_trap(a68k_cpu *s,uint16_t opcode,int overflow_only,a68k_host_state *observation) {
    s->pc+=2;
    if(!overflow_only)return trap(s,32+(opcode&15),0,observation);
    if(s->flags&0x800u) {
        s->pc-=2;
        a68k_boundary result=exception_frame(s,7,observation);
        if(result!=A68K_RETURN)return result;
    }
    s->cycles-=4;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
/* Historical Make68K moveusp() structure; native targets determine timing
 * and PC: user mode traps at the instruction, then charges four cycles. */
static a68k_boundary move_usp(a68k_cpu *s,uint16_t opcode,int from_usp,a68k_host_state *observation) {
    s->pc+=2;
    if(!(s->r.sr_high&0x20)) {
        s->pc-=2;
        a68k_boundary result=exception_frame(s,8,observation);
        if(result!=A68K_RETURN)return result;
    } else {
        uint32_t value=from_usp?s->r.usp:s->r.a[opcode&7];
        if(from_usp)s->r.a[opcode&7]=value;else s->r.usp=value;
        if(observation)observation->eax=value;
    }
    s->cycles-=4;
    return s->cycles&0x80000000u?exit_dispatch(s):A68K_FETCH;
}
a68k_boundary a68k_dispatch_target(a68k_cpu *s,uint32_t target,uint16_t opcode,uint32_t host_control_flags) {
    if(s->fault.boundary)return s->fault.boundary;
    switch(target) {
#define A68K_CHK(address,mode,cost) case address:return check_bounds(s,opcode,mode,cost,NULL);
#include "chk_ops.inc"
#undef A68K_CHK
#define A68K_BCD_MEMORY(address,subtract) case address:return bcd_memory(s,opcode,subtract,NULL);
#include "bcd_memory_ops.inc"
#undef A68K_BCD_MEMORY
#define A68K_STATUS_MOVE(address,op,cost,mode) case address:return status_move(s,opcode,op,cost,mode,NULL);
#define A68K_STATUS_LOGIC(address,op,full) case address:return status_logic(s,op,full,NULL);
#include "status_ops.inc"
#undef A68K_STATUS_MOVE
#undef A68K_STATUS_LOGIC
#define A68K_MOVEM(address,bits,read,cost,mode) case address:return move_multiple(s,opcode,bits,read,cost,mode,NULL);
#include "movem_ops.inc"
#undef A68K_MOVEM
#define A68K_MOVEP(address,size,write) case address:return move_peripheral(s,opcode,size,write,NULL);
#define A68K_CMPM(address,bits) case address:return compare_memory_pair(s,opcode,bits,host_control_flags,NULL);
#include "memory_sequence_ops.inc"
#undef A68K_MOVEP
#undef A68K_CMPM
#define A68K_NBCD(address,cost) case address:return nbcd_register(s,opcode,host_control_flags,cost);
#include "nbcd_ops.inc"
#undef A68K_NBCD
#define A68K_BCD_REGISTER(address,subtract) case address:return bcd_register(s,opcode,subtract);
#include "bcd_register_ops.inc"
#undef A68K_BCD_REGISTER
#define A68K_RTS(address) case address:return return_subroutine(s,NULL);
#define A68K_RESTORE(address,entire_sr) case address:return return_restore(s,entire_sr,NULL);
#define A68K_STOP(address) case address:return stop_instruction(s,NULL);
#define A68K_RESET_INSTRUCTION(address) case address:return reset_instruction(s,NULL);
#define A68K_RTD(address) case address:return return_deallocate(s,opcode,NULL);
#define A68K_MOVEC(address,to_control) case address:return move_control(s,opcode,to_control,NULL);
#include "return_ops.inc"
#undef A68K_RTS
#undef A68K_RESTORE
#undef A68K_STOP
#undef A68K_RESET_INSTRUCTION
#undef A68K_RTD
#undef A68K_MOVEC
#define A68K_USP(address,from_usp) case address:return move_usp(s,opcode,from_usp,NULL);
#include "usp_ops.inc"
#undef A68K_USP
#define A68K_SOFTWARE_TRAP(address,overflow_only) case address:return software_trap(s,opcode,overflow_only,NULL);
#include "software_trap_ops.inc"
#undef A68K_SOFTWARE_TRAP
#define A68K_REG(address,op,bits,cost) case address:return register_op(s,opcode,host_control_flags,op,bits,cost);
#include "register_ops.inc"
#undef A68K_REG
#define A68K_CONTROL(address,op,cc) case address:return control_op(s,opcode,op,cc,NULL);
#include "control_ops.inc"
#undef A68K_CONTROL
#define A68K_BINARY(address,op,bits,cost,mask) case address:return binary_op(s,opcode,host_control_flags,op,bits,cost,mask);
#include "binary_ops.inc"
#undef A68K_BINARY
#define A68K_OPERAND(address,op,bits,cost,source) case address:return operand_op(s,opcode,host_control_flags,op,bits,cost,source);
#include "operand_ops.inc"
#undef A68K_OPERAND
#define A68K_MEMORY_MOVE(address,bits,cost,mode) case address:return memory_source(s,opcode,host_control_flags,MOVE,bits,cost,mode,NULL);
#include "memory_move_ops.inc"
#undef A68K_MEMORY_MOVE
#define A68K_MEMORY_BINARY(address,op,bits,cost,mode) case address:return memory_source(s,opcode,host_control_flags,op,bits,cost,mode,NULL);
#include "memory_binary_ops.inc"
#undef A68K_MEMORY_BINARY
#define A68K_MEMORY_ADDRESS(address,op,bits,cost,mode) case address:return memory_source(s,opcode,host_control_flags,op,bits,cost,mode,NULL);
#include "memory_address_ops.inc"
#undef A68K_MEMORY_ADDRESS
#define A68K_MEMORY_DEST(address,op,bits,cost,mode) case address:return memory_destination(s,opcode,host_control_flags,op,bits,cost,mode,REGISTER_HIGH,NULL);
#include "memory_dest_ops.inc"
#undef A68K_MEMORY_DEST
#define A68K_MEMORY_OPERAND(address,op,bits,cost,mode,source) case address:return memory_destination(s,opcode,host_control_flags,op,bits,cost,mode,source,NULL);
#include "memory_operand_ops.inc"
#undef A68K_MEMORY_OPERAND
#define A68K_MEMORY_UNARY(address,op,bits,cost,mode) case address:return memory_unary(s,opcode,host_control_flags,op,bits,cost,mode,NULL);
#include "memory_unary_ops.inc"
#undef A68K_MEMORY_UNARY
#define A68K_MEMORY_SCRATCH(address,op,bits,cost,mode) case address:return memory_unary(s,opcode,host_control_flags,op,bits,cost,mode,NULL);
#include "memory_scratch_ops.inc"
#undef A68K_MEMORY_SCRATCH
#define A68K_SCC_MEMORY(address,cc,cost,mode) case address:return scc_memory(s,opcode,cc,cost,mode,NULL);
#include "scc_memory_ops.inc"
#undef A68K_SCC_MEMORY
#define A68K_EXTEND_MEMORY(address,op,bits,cost) case address:return extend_memory(s,opcode,host_control_flags,op,bits,cost,NULL);
#include "extend_memory_ops.inc"
#undef A68K_EXTEND_MEMORY
#define A68K_ADDRESS(address,op,bits,cost,mode) case address:return address_operation(s,opcode,op,cost,mode,NULL);
#include "address_ops.inc"
#undef A68K_ADDRESS
#define A68K_BIT(address,op,bits,cost,mode,source) case address:return bit_operation(s,opcode,op,cost,mode,source,NULL);
#include "bit_ops.inc"
#undef A68K_BIT
#define A68K_MOVE_DEST(address,op,bits,cost,mode,source) case address:return move_destination(s,opcode,host_control_flags,bits,cost,mode,source,NULL);
#include "move_dest_ops.inc"
#undef A68K_MOVE_DEST
#define A68K_MOVE_MEMORY(address,bits,cost,source,destination) case address:return move_memory(s,opcode,host_control_flags,bits,cost,source,destination,NULL);
#include "move_memory_ops.inc"
#undef A68K_MOVE_MEMORY
#define A68K_MULTIPLY(address,is_signed,cost,mode) case address:return multiply(s,opcode,host_control_flags,is_signed,cost,mode,NULL);
#include "multiply_ops.inc"
#undef A68K_MULTIPLY
#define A68K_ROTATE(address,bits,left,extend,variable,cost) case address:return rotate_register(s,opcode,host_control_flags,bits,left,extend,variable,cost);
#include "rotate_ops.inc"
#undef A68K_ROTATE
#define A68K_SHIFT_MEMORY(address,op,bits,cost,mode) case address:return shift_memory(s,opcode,host_control_flags,op,cost,mode,NULL);
#include "shift_memory_ops.inc"
#undef A68K_SHIFT_MEMORY
#define A68K_SHIFT_REGISTER(address,op,bits,variable,cost,special) case address:return shift_register(s,opcode,host_control_flags,op,bits,variable,cost,special);
#include "shift_register_ops.inc"
#undef A68K_SHIFT_REGISTER
#define A68K_JUMP(address,subroutine,cost,mode) case address:return jump(s,opcode,subroutine,cost,mode,NULL);
#include "jump_ops.inc"
#undef A68K_JUMP
#define A68K_DIVIDE(address,is_signed,cost,mode,idiv) case address:return divide_operation(s,opcode,host_control_flags,is_signed,cost,mode,idiv,NULL);
#include "divide_ops.inc"
#undef A68K_DIVIDE
#define A68K_DIVIDE_MEMORY(address,sign,cost,mode,fault) case address:return divide_operation(s,opcode,host_control_flags,sign,cost,mode,fault,NULL);
#include "divide_memory_ops.inc"
#undef A68K_DIVIDE_MEMORY
    case 0x478438:return a68k_moveq(s,opcode,host_control_flags);
    case 0x48b518:return trap(s,10,0,NULL); /* Native ADD 2 / SUB 2 leaves PC. */
    case 0x48b540:return trap(s,11,0,NULL);
    case 0x48b568:
        s->illegal_opcode=opcode;s->illegal_pc=s->pc;
        /* 004b3360 is XOR EAX,EAX / RET in the pinned original. No invented
         * callback or "handled" branch. Native stacks PC-2, then adds 2 to
         * the VECTOR target only if the exception leaves positive cycles. */
        s->pc-=2;return trap(s,4,2,NULL);
    default:return A68K_UNRECOVERED;
    }
}

a68k_boundary a68k_begin_observed(a68k_cpu *s,a68k_host_state *host) {
    if(s->fault.boundary)return s->fault.boundary;
    if(!host || !host->valid)return A68K_BINDING_ERROR;
    if((host->control_flags&~0xed7u) || !(host->control_flags&2u))return A68K_UNRECOVERED;
    unsigned level=s->r.irq&7;
    if(level && (level==7 || level>(s->r.sr_high&7)) &&
       (!s->ack_observed || !s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
    if(level)host->eax=level; /* No IRQ leaves caller EAX unchanged. */
    s->pc=s->r.pc;s->flags=s->r.flags;
    a68k_boundary result=interrupt_live(s,host);
    if(result!=A68K_FETCH)host->valid=0;
    s->entry_eax=host->eax;s->entry_eax_valid=host->valid;
    return result;
}

a68k_boundary a68k_step_observed(a68k_cpu *s,uint32_t target,uint16_t opcode,a68k_host_state *host) {
    if(s->fault.boundary)return s->fault.boundary;
    if(!host || !host->valid)return A68K_BINDING_ERROR;
    if((host->control_flags&~0xed7u) || !(host->control_flags&2u))return A68K_UNRECOVERED;
    enum reg_op op=NOP;int scc=-1,operand_scratch=0,post_data=-1,lahf=0,multiply_result=0;
    int memory_cc=-1;unsigned memory_cost=0;enum ea_mode memory_mode=INDIRECT;
    unsigned move_bits=0;enum operand_source move_source=REGISTER_LOW;
    unsigned read_bits=0,read_cost=0,read_kind=0,read_signed=0;uint32_t observed_idiv=0;
    enum binary_op read_op=MOVE;enum ea_mode read_mode=INDIRECT,write_mode=INDIRECT;
    enum reg_op memory_reg_op=NOP;enum operand_source rmw_source=REGISTER_HIGH;
    enum address_op observed_address_op=LEA;int dbcc=-1,branch_cc=-1;enum control_op branch_op=BR_BYTE;
    enum bit_op memory_bit_op=BTST;enum shift_op memory_shift_op=ASR;
    uint32_t post_mask=0xffffffffu;
    uint32_t next_eax=host->eax;
    switch(target) {
#define A68K_REG(address,operation,bits,cost) case address:op=operation;break;
#include "register_ops.inc"
#undef A68K_REG
#define A68K_CONTROL(address,operation,cc) \
    case address:if(operation==SCC)scc=cc;else if(operation==DBCC)dbcc=cc;else {branch_cc=cc;branch_op=operation;read_kind=15;}break;
#include "control_ops.inc"
#undef A68K_CONTROL
#define A68K_SCC_MEMORY(address,cc,cost,mode) case address:memory_cc=cc;memory_cost=cost;memory_mode=mode;break;
#include "scc_memory_ops.inc"
#undef A68K_SCC_MEMORY
#define A68K_MOVE_DEST(address,operation,bits,cost,mode,source) \
    case address:move_bits=bits;memory_cost=cost;memory_mode=mode;move_source=source;break;
#include "move_dest_ops.inc"
#undef A68K_MOVE_DEST
#define A68K_MEMORY_MOVE(address,bits,cost,mode) \
    case address:read_kind=1;read_bits=bits;read_cost=cost;read_mode=mode;read_op=MOVE;break;
#include "memory_move_ops.inc"
#undef A68K_MEMORY_MOVE
#define A68K_MEMORY_BINARY(address,operation,bits,cost,mode) \
    case address:read_kind=1;read_bits=bits;read_cost=cost;read_mode=mode;read_op=operation;break;
#include "memory_binary_ops.inc"
#define A68K_MEMORY_ADDRESS A68K_MEMORY_BINARY
#include "memory_address_ops.inc"
#undef A68K_MEMORY_ADDRESS
#undef A68K_MEMORY_BINARY
#define A68K_MOVE_MEMORY(address,bits,cost,source,destination) \
    case address:read_kind=2;read_bits=bits;read_cost=cost;read_mode=source;write_mode=destination;break;
#include "move_memory_ops.inc"
#undef A68K_MOVE_MEMORY
#define A68K_MEMORY_DEST(address,operation,bits,cost,mode) \
    case address:read_kind=4;read_bits=bits;read_cost=cost;read_mode=mode;read_op=operation;break;
#include "memory_dest_ops.inc"
#undef A68K_MEMORY_DEST
#define A68K_MEMORY_OPERAND(address,operation,bits,cost,mode,source) \
    case address:read_kind=4;read_bits=bits;read_cost=cost;read_mode=mode;read_op=operation;rmw_source=source;break;
#include "memory_operand_ops.inc"
#undef A68K_MEMORY_OPERAND
#define A68K_MEMORY_UNARY(address,operation,bits,cost,mode) \
    case address:read_kind=5;read_bits=bits;read_cost=cost;read_mode=mode;memory_reg_op=operation;break;
#include "memory_unary_ops.inc"
#define A68K_MEMORY_SCRATCH A68K_MEMORY_UNARY
#include "memory_scratch_ops.inc"
#undef A68K_MEMORY_SCRATCH
#undef A68K_MEMORY_UNARY
#define A68K_SHIFT_MEMORY(address,operation,bits,cost,mode) \
    case address:read_kind=7;read_cost=cost;read_mode=mode;memory_shift_op=operation;break;
#include "shift_memory_ops.inc"
#undef A68K_SHIFT_MEMORY
#define A68K_BCD_MEMORY(address,subtract) case address:read_kind=8;read_signed=subtract;break;
#include "bcd_memory_ops.inc"
#undef A68K_BCD_MEMORY
#define A68K_EXTEND_MEMORY(address,operation,bits,cost) \
    case address:read_kind=9;read_bits=bits;read_cost=cost;read_op=operation;break;
#include "extend_memory_ops.inc"
#undef A68K_EXTEND_MEMORY
#define A68K_MOVEP(address,size,write) case address:read_kind=10;read_bits=size;read_signed=write;break;
#define A68K_CMPM(address,bits) case address:read_kind=11;read_bits=bits;break;
#include "memory_sequence_ops.inc"
#undef A68K_MOVEP
#undef A68K_CMPM
#define A68K_MOVEM(address,bits,read,cost,mode) \
    case address:read_kind=12;read_bits=bits;read_signed=read;read_cost=cost;read_mode=mode;break;
#include "movem_ops.inc"
#undef A68K_MOVEM
#define A68K_ADDRESS(address,operation,bits,cost,mode) \
    case address:read_kind=13;read_cost=cost;read_mode=mode;observed_address_op=operation;break;
#include "address_ops.inc"
#undef A68K_ADDRESS
#define A68K_JUMP(address,subroutine,cost,mode) \
    case address:read_kind=14;read_signed=subroutine;read_cost=cost;read_mode=mode;break;
#include "jump_ops.inc"
#undef A68K_JUMP
#define A68K_BINARY(address,operation,bits,cost,mask) \
    case address: { \
        operand_scratch=1; \
        if(operation==ADDX || operation==SUBX)break; \
        if(operation==EOR){post_data=opcode&7;break;} \
        unsigned source=opcode&mask; \
        next_eax=source<8?s->r.d[source]:s->r.a[source-8]; \
        if(bits==16 && (operation==ADDA || operation==SUBA || operation==CMPA)) \
            next_eax=signed_word(next_eax&65535u); \
        break; \
    }
#include "binary_ops.inc"
#undef A68K_BINARY
#define A68K_OPERAND(address,operation,bits,cost,source) \
    case address: { \
        operand_scratch=1; \
        if(source==QUICK_LOW)break; \
        if(source==IMMEDIATE_LOW){post_data=opcode&7;break;} \
        if(source==REGISTER_HIGH) { \
            unsigned reg=opcode&15;next_eax=reg<8?s->r.d[reg]:s->r.a[reg-8]; \
        } else { \
            if(!fetch_word(s,s->pc+2,&next_eax))return A68K_BINDING_ERROR; \
            if(bits==32) { \
                uint32_t low;if(!fetch_word(s,s->pc+4,&low))return A68K_BINDING_ERROR; \
                next_eax=(next_eax<<16)|low; \
            } \
        } \
        if(bits==16 && (operation==MOVEA || operation==ADDA || operation==SUBA || operation==CMPA)) \
            next_eax=signed_word(next_eax&65535u); \
        break; \
    }
#include "operand_ops.inc"
#undef A68K_OPERAND
#define A68K_ROTATE(address,bits,left,extend,variable,cost) \
    case address:operand_scratch=1;post_data=opcode&7;break;
#include "rotate_ops.inc"
#undef A68K_ROTATE
#define A68K_SHIFT_REGISTER(address,operation,bits,variable,cost,special) \
    case address: { \
        operand_scratch=1;if(special)break; \
        unsigned count=variable?s->r.d[(opcode>>9)&7]&63u:(((opcode>>9)-1)&7)+1; \
        post_data=opcode&7; \
        lahf=count && (operation==ASR || operation==ASL) && !(operation==ASL && bits==32 && count>=32); \
        break; \
    }
#include "shift_register_ops.inc"
#undef A68K_SHIFT_REGISTER
#define A68K_BIT(address,operation,bits,cost,mode,source) \
    case address: { \
        if(mode!=REGISTER) { \
            read_kind=6;read_cost=cost;read_mode=mode;memory_bit_op=operation;rmw_source=source;break; \
        } \
        operand_scratch=1;uint32_t count; \
        if(source==IMMEDIATE_LOW){if(!fetch_word(s,s->pc+2,&count))return A68K_BINDING_ERROR;} \
        else count=s->r.d[(opcode>>9)&7]; \
        next_eax=1u<<(count&31);break; \
    }
#include "bit_ops.inc"
#undef A68K_BIT
#define A68K_BCD_REGISTER(address,subtract) \
    case address:operand_scratch=1;post_data=(opcode>>9)&7;break;
#include "bcd_register_ops.inc"
#undef A68K_BCD_REGISTER
#define A68K_NBCD(address,cost) \
    case address:operand_scratch=1;post_data=opcode&7;post_mask=255u;break;
#include "nbcd_ops.inc"
#undef A68K_NBCD
#define A68K_MULTIPLY(address,sign,cost,mode) \
    case address: { \
        if(mode!=REGISTER && mode!=IMMEDIATE) { \
            read_kind=3;read_signed=sign;read_cost=cost;read_mode=mode;break; \
        } \
        operand_scratch=1;multiply_result=1;post_data=(opcode>>9)&7; \
        if(mode==REGISTER)next_eax=s->r.d[opcode&7]; \
        else if(!fetch_word(s,s->pc+2,&next_eax))return A68K_BINDING_ERROR; \
        break; \
    }
#include "multiply_ops.inc"
#undef A68K_MULTIPLY
    case 0x478438:break;
#define A68K_SOFTWARE_TRAP(address,overflow_only) case address:read_kind=16;read_signed=overflow_only;break;
#include "software_trap_ops.inc"
#undef A68K_SOFTWARE_TRAP
#define A68K_USP(address,from_usp) case address:read_kind=17;read_signed=from_usp;break;
#include "usp_ops.inc"
#undef A68K_USP
    case 0x48b518:read_kind=18;read_cost=10;break;
    case 0x48b540:read_kind=18;read_cost=11;break;
    case 0x48b568:read_kind=18;read_cost=4;break;
    case 0x485cf8:read_kind=19;break;
    case 0x485c40:read_kind=20;read_signed=0;break;
    case 0x487008:read_kind=20;read_signed=1;break;
    case 0x48b5b4:read_kind=21;break;
#define A68K_STATUS_MOVE(address,operation,cost,mode) case address:read_kind=22;read_signed=operation;read_cost=cost;read_mode=mode;break;
#define A68K_STATUS_LOGIC(address,operation,full) case address:read_kind=23;read_op=operation;read_signed=full;break;
#include "status_ops.inc"
#undef A68K_STATUS_MOVE
#undef A68K_STATUS_LOGIC
#define A68K_CHK(address,mode,cost) case address:read_kind=24;read_mode=mode;read_cost=cost;break;
#include "chk_ops.inc"
#undef A68K_CHK
#define A68K_DIVIDE(address,sign,cost,mode,idiv) case address:read_kind=25;read_signed=sign;read_cost=cost;read_mode=mode;observed_idiv=idiv;break;
#define A68K_DIVIDE_MEMORY A68K_DIVIDE
#include "divide_ops.inc"
#include "divide_memory_ops.inc"
#undef A68K_DIVIDE_MEMORY
#undef A68K_DIVIDE
    case 0x48b65c:read_kind=26;read_signed=0;break;
    case 0x48b6dc:read_kind=26;read_signed=1;break;
    case 0x486ee0:read_kind=27;break;
    case 0x486e48:read_kind=28;break;
    default:return A68K_UNRECOVERED;
    }
    /* Signed Scc restores host EFLAGS from EDX. Qualify the ordinary
     * arithmetic/IF/DF domain first; other control, privileged, reserved or
     * trap bits require original Windows evidence, not silent masking. */
    if((scc>=12 || memory_cc>=12 || dbcc>=12 || branch_cc>=12) && (s->flags&~0xed7u))return A68K_UNRECOVERED;
    if(dbcc>=0) {
        a68k_cpu probe=*s;int take=condition(&probe,(unsigned)dbcc);
        operand_scratch=1;
        if(dbcc==2 || dbcc==3)next_eax=(next_eax&~0xff00u)|((s->flags&255u)<<8);
        if(!take) {
            uint32_t old=s->r.d[opcode&7]&65535u;next_eax=(next_eax&0xffff0000u)|old;
            if(old) {if(!fetch_word(s,s->pc+2,&next_eax))return A68K_BINDING_ERROR;next_eax=signed_word(next_eax);}
        }
    }
    if(read_kind==14 || read_kind==15) {
        /* Preflight the actual branch on a copy: an odd destination needs
         * the original vector-3 bus/binder path before any stack mutation. */
        a68k_cpu probe=*s;uint32_t destination=0;int take=1;
        probe.pc+=2;
        if(read_kind==14) {
            if(!effective_address(&probe,opcode&7,4,read_mode,&destination))return A68K_BINDING_ERROR;
        } else {
            take=branch_cc==1 || condition(&probe,(unsigned)branch_cc);
            if(take) {
                uint32_t displacement;
                if(branch_op==BR_WORD) {
                    if(!fetch_word(&probe,probe.pc,&displacement))return A68K_BINDING_ERROR;
                    displacement=signed_word(displacement);
                } else displacement=opcode&0x80u?(opcode&255u)|0xffffff00u:opcode&255u;
                destination=probe.pc+displacement;
            }
        }
        if(take && (destination&1) && (!s->exception_cycles || !s->write_pages || !s->data_pages))return A68K_BINDING_ERROR;
        if(take && !s->bind_observed)return A68K_BINDING_ERROR;
    }
    if(read_kind>=19 && read_kind<=21) {
        /* Return destinations are bus results, so bind all possible native
         * exception paths before consuming the stack. RTE may unmask IRQ. */
        if(!s->data_pages || !s->bind_observed || !s->exception_cycles || !s->write_pages)return A68K_BINDING_ERROR;
        if(read_kind==20 && read_signed && (s->r.irq&7) && !s->ack_observed)return A68K_BINDING_ERROR;
    }
    if(read_kind>=16 && read_kind<=18) {
        int needs_exception=read_kind==18 || (read_kind==17?!(s->r.sr_high&0x20):!read_signed || (s->flags&0x800));
        if(needs_exception && (!s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
    }
    if(read_kind==22 || read_kind==23) {
        int full=read_kind==23?read_signed:read_signed==TO_SR;
        int exception=(full && !(s->r.sr_high&0x20)) || (read_kind==22 && read_signed==FROM_CCR && !s->r.opaque31);
        if(exception && (!s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
        if(full && (s->r.irq&7) && (!s->ack_observed || !s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
    }
    if((read_kind==24 || read_kind==25) && (!s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
    if(read_kind>=26) {
        int exception=!(s->r.sr_high&0x20) || (read_kind==26 && !s->r.opaque31);
        if(exception && (!s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
        if(read_kind==27 && (s->r.irq&7) && (!s->ack_observed || !s->exception_cycles || !s->write_pages || !s->data_pages || !s->bind_observed))return A68K_BINDING_ERROR;
        if(read_kind==28 && !exception && s->r.opaque24[1] && !s->reset_observed)return A68K_BINDING_ERROR;
    }
    /* Do not reuse a previous EAX after an unqualified handler/callback. This
     * API is intentionally separate from the complete single-handler API:
     * dispatch coverage does not prove host-scratch coverage. */
    s->entry_eax=host->eax;s->entry_eax_valid=1;
    if(read_kind==18 && read_cost==4){s->illegal_opcode=opcode;s->illegal_pc=s->pc;s->pc-=2;}
    a68k_boundary result=read_kind==1?memory_source(s,opcode,host->control_flags,read_op,read_bits,read_cost,read_mode,host):
        read_kind==2?move_memory(s,opcode,host->control_flags,read_bits,read_cost,read_mode,write_mode,host):
        read_kind==3?multiply(s,opcode,host->control_flags,read_signed,read_cost,read_mode,host):
        read_kind==4?memory_destination(s,opcode,host->control_flags,read_op,read_bits,read_cost,read_mode,rmw_source,host):
        read_kind==5?memory_unary(s,opcode,host->control_flags,memory_reg_op,read_bits,read_cost,read_mode,host):
        read_kind==6?bit_operation(s,opcode,memory_bit_op,read_cost,read_mode,rmw_source,host):
        read_kind==7?shift_memory(s,opcode,host->control_flags,memory_shift_op,read_cost,read_mode,host):
        read_kind==8?bcd_memory(s,opcode,(int)read_signed,host):
        read_kind==9?extend_memory(s,opcode,host->control_flags,read_op,read_bits,read_cost,host):
        read_kind==10?move_peripheral(s,opcode,read_bits,(int)read_signed,host):
        read_kind==11?compare_memory_pair(s,opcode,read_bits,host->control_flags,host):
        read_kind==12?move_multiple(s,opcode,read_bits,(int)read_signed,read_cost,read_mode,host):
        read_kind==13?address_operation(s,opcode,observed_address_op,read_cost,read_mode,host):
        read_kind==14?jump(s,opcode,read_signed,read_cost,read_mode,host):
        read_kind==15?control_op(s,opcode,branch_op,(unsigned)branch_cc,host):
        read_kind==16?software_trap(s,opcode,(int)read_signed,host):
        read_kind==17?move_usp(s,opcode,(int)read_signed,host):
        read_kind==18?trap(s,read_cost,read_cost==4?2:0,host):
        read_kind==19?return_subroutine(s,host):
        read_kind==20?return_restore(s,(int)read_signed,host):
        read_kind==21?return_deallocate(s,opcode,host):
        read_kind==22?status_move(s,opcode,(enum status_move_op)read_signed,read_cost,read_mode,host):
        read_kind==23?status_logic(s,read_op,(int)read_signed,host):
        read_kind==24?check_bounds(s,opcode,read_mode,read_cost,host):
        read_kind==25?divide_operation(s,opcode,host->control_flags,read_signed,read_cost,read_mode,observed_idiv,host):
        read_kind==26?move_control(s,opcode,(int)read_signed,host):
        read_kind==27?stop_instruction(s,host):
        read_kind==28?reset_instruction(s,host):
        move_bits?move_destination(s,opcode,host->control_flags,move_bits,memory_cost,memory_mode,move_source,host):
        memory_cc>=0?scc_memory(s,opcode,(unsigned)memory_cc,memory_cost,memory_mode,host):
        a68k_dispatch_target(s,target,opcode,host->control_flags);
    if(result==A68K_PREFETCHED) {
        s->prefetched_valid=1;s->entry_eax=host->eax;return result;
    }
    if(result!=A68K_FETCH) {
        host->valid=0;s->entry_eax_valid=0;return result;
    }
    unsigned reg=opcode&7;
    if(dbcc>=12)host->control_flags=(s->flags&0x400u)|0x202u;
    if(operand_scratch) {
        /* Original register binary operations usually leave the SOURCE in
         * EAX while changing Dn in memory. EOR and immediate-low forms use
         * EAX as the destination; ADDX/SUBX and quick forms do not touch it.
         * Capture source before dispatch so source/destination aliases work. */
        host->eax=post_data>=0?s->r.d[post_data]&post_mask:next_eax;
        /* Word MUL/IMUL modifies AX, preserving the source EAX high word.
         * The full 32-bit product is assembled separately in EDX/Dn. */
        if(multiply_result)host->eax=(next_eax&0xffff0000u)|(host->eax&65535u);
        /* ASR/ordinary ASL write Dn before LAHF overwrites AH. Zero-count,
         * long ASL big-shift and immediate-one special tails do not LAHF. */
        if(lahf)host->eax=(host->eax&~0xff00u)|((s->flags&255u)<<8);
    } else if(scc>=0) {
        /* The original uses EAX for its variable cycle charge after SETcc:
         * AND EAX,2; ADD EAX,4. It is 4 or 6, never the destination Dn. */
        host->eax=(s->r.d[reg]&2u)+4;
        if(scc>=12)host->control_flags=(s->flags&0x400u)|0x202u;
    } else if(target==0x478438)host->eax=s->r.d[(opcode>>9)&7];
    else switch(op) {
    case NOP:break; /* Native body never touches EAX. */
    case CLR:host->eax=0;break; /* Full MOV EAX,0 even for CLR.B/W. */
    case EXG_AA:case EXG_DA:host->eax=s->r.a[reg];break;
    case TST_A:host->eax=s->r.a[reg];break;
    case EXT_BW:
        /* MOVSX EAX,byte source, then only AX is written back to Dn. */
        host->eax=signed_word(s->r.d[reg]&65535u);break;
    default:
        /* EXG.DD leaves the old first operand in its second Dn. Narrow
         * unary operations load all of Dn and modify AL/AX; TST leaves the
         * loaded Dn intact. Their EAX therefore equals the resulting Dn. */
        host->eax=s->r.d[reg];break;
    }
    /* Register producers preserve control bits. Signed Scc's POPFD above
     * can change DF for a later PUSHFD-based guest operation, even though
     * guest condition evaluation itself uses only NZVC. */
    s->entry_eax=host->eax;
    return result;
}

a68k_boundary a68k_run_live(a68k_cpu *s,const uint32_t *table,a68k_host_state *host,
                           unsigned max_steps,unsigned *steps) {
    if(!steps)return A68K_BINDING_ERROR;
    *steps=0;
    if(!s || !table || !host || !host->valid)return A68K_BINDING_ERROR;
    if(s->fault.boundary)return s->fault.boundary;
    while(*steps<max_steps) {
        unsigned pending=s->prefetched_valid;uint32_t opcode=s->prefetched_opcode;
        if(!pending && !fetch_word(s,s->pc,&opcode))return A68K_BINDING_ERROR;
        if(opcode>=A68K_OPCODE_COUNT)return A68K_BINDING_ERROR;
        a68k_boundary result=a68k_step_observed(s,table[opcode],(uint16_t)opcode,host);
        if(result==A68K_BINDING_ERROR || result==A68K_UNRECOVERED)return result;
        ++*steps;
        if(pending && result!=A68K_PREFETCHED)s->prefetched_valid=0;
        if(result==A68K_PREFETCHED)continue; /* RESET owns this unconditional dispatch. */
        if(result!=A68K_FETCH)return result;
        /* Completed() owns each native JS/JLE cycle tail. Do not insert a
         * generic <=0 check or reload published PC/flags here. A research
         * pause is not a native exit: live state and host scratch survive. */
    }
    return A68K_FETCH;
}
