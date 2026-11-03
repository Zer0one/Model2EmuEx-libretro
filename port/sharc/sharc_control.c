#include "sharc_control.h"
#include "sharc_condition.h"
#include "sharc_integer.h"
#include "sharc_flow.h"
#define W(s,o) ((s)->state[(uint32_t)(o)/4u])

static void push_pc(m2_sharc_execution *s, uint32_t advance)
{
    uint32_t pc = W(s,8) + advance;
    ++W(s,0x10);
    W(s,0xc) = pc;
    W(s,0x20u + W(s,0x10)*4u) = pc;
}
static uint32_t pop_pc(m2_sharc_execution *s)
{
    uint32_t index = W(s,0x10), pc = W(s,0x20u+index*4u);
    W(s,0x10) = index-1u;
    W(s,0xc) = pc;
    return pc;
}
static void pop_loop(m2_sharc_execution *s)
{
    uint32_t index = W(s,0x10), pc = W(s,0x20u+index*4u);
    --W(s,0xd4);
    W(s,0x10) = index-1u;
    index = W(s,0xd4);
    W(s,0xc) = pc;
    W(s,0x18) = W(s,0x9cu+index*4u);
    W(s,0x14) = W(s,0xb8u+index*4u);
}
static void jump(m2_sharc_execution *s, uint32_t target)
{
    W(s,8) = target-1u;
    s->current_record = s->active_base+target*0x6cu-0x6cu;
}
static bool compute(const m2_sharc_control_record *r, m2_sharc_execution *s, uint32_t condition,
    const m2_sharc_operation_hooks *operation)
{
    uint32_t flags, value, rhs = *r->rhs, lhs = *r->lhs;
    m2_sharc_flow_flags(M2_SHARC_FLOW_CONTINUOUS_FIRST,condition,&flags);
    bool ok=operation?operation->run(operation->opaque,r->operation,lhs,rhs,flags,&W(s,0x240),&value):
        m2_sharc_integer_compute(r->operation,lhs,rhs,flags,&W(s,0x240),&value);
    if(!ok)return false;
    *r->destination = value;
    return true;
}
bool m2_sharc_dispatch_control_ex(uint32_t handler, m2_sharc_execution *s,
    const m2_sharc_execution_hooks *h, m2_sharc_control_resolver resolve, void *opaque,
    const m2_sharc_operation_hooks *operation)
{
    const m2_sharc_control_record *r;
    uint32_t condition, count, descriptor;
    bool alternate, together, general;
    switch(handler) {
    case 0x4bd700: case 0x4bd750: case 0x4bd7b0:
        r=resolve(opaque,s->current_record);
        if (handler!=0x4bd700) {
            count=handler==0x4bd750 ? *r->value : r->count;
            /* Counter capture precedes PC-stack writes, including aliases. */
            ++W(s,0x10);
            W(s,0x1c)=count;
            W(s,0xc)=W(s,8)+1u;
            W(s,0x20u+W(s,0x10)*4u)=W(s,0xc);
            count=W(s,0x1c);
        } else {
            push_pc(s,1);
            count=0;
        }
        descriptor=r->immediate;
        ++W(s,0xd4);
        W(s,0x18)=count;
        W(s,0x14)=descriptor;
        W(s,0x9cu+W(s,0xd4)*4u)=count;
        W(s,0xb8u+W(s,0xd4)*4u)=descriptor;
        return true;
    case 0x4bcad0: case 0x4bda10: case 0x4bda60:
    case 0x4be2a0: case 0x4be310: case 0x4be380: case 0x4be460:
    case 0x4be540: case 0x4be610: case 0x4be6f0: case 0x4be750: case 0x4be7c0:
        break;
    default:return false;
    }
    r=resolve(opaque,s->current_record);
    alternate=handler==0x4be2a0 || handler==0x4be380 || handler==0x4be460;
    together=handler==0x4be310 || handler==0x4be540 || handler==0x4be610;
    general=handler==0x4be380 || handler==0x4be460 || handler==0x4be540 || handler==0x4be610;
    if (r->condition>31 || ((alternate||together) && !(operation?operation->supported(operation->opaque,r->operation):m2_sharc_integer_supported(r->operation))))
        return false;
    m2_sharc_condition(0,r->condition,W(s,0x240),W(s,0x18),&s->stop,&condition);
    if (condition==0) {
        if (alternate && !compute(r,s,condition,operation))return false;
        return true;
    }
    if (together && !compute(r,s,condition,operation))return false;
    if (handler==0x4be6f0) push_pc(s,3); /* Before delay slots, unlike general CALL. */
    if ((handler>=0x4be6f0) || ((general||handler==0x4be2a0||handler==0x4be310) && (r->flags&1u))) {
        m2_sharc_delay_slots(s,h);
        r=resolve(opaque,s->current_record);
    }
    if (handler==0x4be2a0 || handler==0x4be310) {
        jump(s,pop_pc(s));
        return true;
    }
    if (handler==0x4bda10) push_pc(s,1);
    if (handler==0x4bda60 || handler==0x4be750) pop_loop(s);
    if (general) {
        /* Call bit wins over loop-exit bit. PC and flags are read AFTER slots. */
        if (r->flags&4u) push_pc(s,(r->flags&1u)?3u:1u);
        else if (r->flags&2u) pop_loop(s);
    }
    if (handler==0x4be460 || handler==0x4be610)
        jump(s,*r->step+*r->address);
    else
        jump(s,r->immediate);
    return true;
}

bool m2_sharc_dispatch_control(uint32_t handler,m2_sharc_execution *s,
    const m2_sharc_execution_hooks *h,m2_sharc_control_resolver resolve,void *opaque)
{
    return m2_sharc_dispatch_control_ex(handler,s,h,resolve,opaque,0);
}
