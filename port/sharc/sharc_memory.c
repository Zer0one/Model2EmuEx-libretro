#include "sharc_memory.h"
#include "sharc_condition.h"
#include "sharc_integer.h"
#include "sharc_flow.h"

static bool supported(const m2_sharc_operation_hooks *h,uint32_t operation) {
    return h?h->supported(h->opaque,operation):m2_sharc_integer_supported(operation);
}
static bool run(const m2_sharc_operation_hooks *h,uint32_t op,uint32_t lhs,uint32_t rhs,
    uint32_t flags,uint32_t *status,uint32_t *result) {
    return h?h->run(h->opaque,op,lhs,rhs,flags,status,result):
        m2_sharc_integer_compute(op,lhs,rhs,flags,status,result);
}
static void read_word(const m2_sharc_memory_record *r,
                      const m2_sharc_memory_bus *bus, unsigned n, bool mirror)
{
    uint32_t value = bus->read(bus->opaque, *r->address[n]);
    *r->data[n] = value;
    /* Reload the modifier after the callback AND destination store. */
    *r->address[n] += *r->step[n];
    if (mirror && (r->flags & (1u << n)))
        *r->mirror[n] = *r->data[n];
}

static void write_word(const m2_sharc_memory_record *r,
                       const m2_sharc_memory_bus *bus, unsigned n, uint32_t value)
{
    bus->write(bus->opaque, *r->address[n], value);
    *r->address[n] += *r->step[n];
}

/* Conditional compute plus one address operation. The condition TEST is the
 * helper flag producer; write data is captured before the compute destination
 * store, while effective addresses/modifiers are read afterwards. */
static bool single_transfer(uint32_t handler, const m2_sharc_memory_record *r,
                            const m2_sharc_memory_bus *bus, uint32_t loop_count,
                            uint32_t *status, uint32_t *stop,const m2_sharc_operation_hooks *operation)
{
    uint32_t condition, flags, saved = 0, value, address, lhs, rhs;
    bool write = handler == 0x4bdbb0 || handler == 0x4bdc00 ||
                 handler == 0x4bdd00 || handler == 0x4bdd50;
    bool post = handler == 0x4bdb60 || handler == 0x4bdc00 ||
                handler == 0x4bdcb0 || handler == 0x4bdd50;
    bool immediate = handler == 0x4bdb10 || handler == 0x4bdb60 ||
                     handler == 0x4bdbb0 || handler == 0x4bdc00;
    if (r->condition > 31 || !supported(operation,r->operation))
        return false;
    m2_sharc_condition(0, r->condition, *status, loop_count, stop, &condition);
    if (condition == 0)
        return true;
    m2_sharc_flow_flags(M2_SHARC_FLOW_CONTINUOUS_FIRST, condition, &flags);
    if (write)
        saved = *r->data[0];
    rhs = *r->rhs;
    lhs = *r->lhs;
    if(!run(operation,r->operation,lhs,rhs,flags,status,&value))return false;
    *r->destination = value;
    if (handler == 0x4bdad0) {
        *r->address[0] += *r->step[0];
        return true;
    }
    address = *r->address[0];
    if (!post)
        address += immediate ? r->immediate : *r->step[0];
    if (write)
        bus->write(bus->opaque, address, saved);
    else {
        value = bus->read(bus->opaque, address);
        *r->data[0] = value;
    }
    if (post)
        *r->address[0] += immediate ? r->immediate : *r->step[0];
    return true;
}

bool m2_sharc_dispatch_memory_ex(uint32_t handler,
    const m2_sharc_memory_record *r, const m2_sharc_memory_bus *bus,
    uint32_t entry_eflags, uint32_t loop_count, uint32_t *status,
    uint32_t *stop, uint32_t *pc, uint32_t *record_offset,const m2_sharc_operation_hooks *operation)
{
    bool conditional, first_write, second_write;
    uint32_t condition, target, first = 0, second = 0, lhs, rhs, value;
    switch (handler) {
    case 0x4bdad0: case 0x4bdb10: case 0x4bdb60: case 0x4bdbb0:
    case 0x4bdc00: case 0x4bdc60: case 0x4bdcb0: case 0x4bdd00: case 0x4bdd50:
        return single_transfer(handler, r, bus, loop_count, status, stop, operation);
    case 0x4bd810: case 0x4bd890: case 0x4bd910: case 0x4bd990:
        conditional = true;
        first_write = handler == 0x4bd810 || handler == 0x4bd890;
        second_write = false;
        break;
    case 0x4bddb0: case 0x4bde20: case 0x4bdea0: case 0x4bdf20:
        conditional = false;
        first_write = handler == 0x4bddb0 || handler == 0x4bde20;
        second_write = handler == 0x4bddb0 || handler == 0x4bdea0;
        break;
    default:
        return false;
    }
    if (!supported(operation,r->operation) || (conditional && r->condition > 31))
        return false;
    if (conditional) {
        m2_sharc_condition(0, r->condition, *status, loop_count, stop, &condition);
        if (condition) {
            if (handler == 0x4bd810 || handler == 0x4bd910)
                target = r->immediate;
            else {
                target = *r->step[1] + *r->address[1];
                /* 0x4bd990 alone reads the computed address as a jump target. */
                if (handler == 0x4bd990)
                    target = bus->read(bus->opaque, target);
            }
            *pc = target - 1u;
            *record_offset = target * 0x6cu - 0x6cu;
            return true;
        }
        /* TEST EAX,EAX of a false condition: CF/SF/OF=0, ZF/PF=1.
         * In particular NOT must copy this ZF, not its result's zero flag. */
        entry_eflags = 0x46u;
    }
    /* Unconditional handlers have only MOV/PUSH before compute and retain
     * caller flags. Snapshot outgoing values before ALU/result side effects. */
    if (first_write)
        first = *r->data[0];
    if (!conditional && second_write)
        second = *r->data[1];
    rhs = *r->rhs;
    lhs = *r->lhs;
    if(!run(operation,r->operation,lhs,rhs,entry_eflags,status,&value))return false;
    *r->destination = value;
    if (first_write)
        write_word(r, bus, 0, first);
    else
        read_word(r, bus, 0, !conditional);
    if (conditional)
        return true;
    if (second_write)
        write_word(r, bus, 1, second);
    else if (handler == 0x4bdf20) {
        read_word(r, bus, 1, false);
        /* Preservation quirk at 0x4bdf95: bit 1 tests the SECOND transfer,
         * but the original reloads record+0x24 (FIRST data pointer), then
         * copies that current word to its -0x80 mirror. Do not 'fix' to data[1]. */
        if (r->flags & 2u)
            *r->mirror[0] = *r->data[0];
    } else
        read_word(r, bus, 1, true);
    return true;
}

bool m2_sharc_dispatch_memory(uint32_t handler,
    const m2_sharc_memory_record *r,const m2_sharc_memory_bus *bus,
    uint32_t entry_eflags,uint32_t loop_count,uint32_t *status,
    uint32_t *stop,uint32_t *pc,uint32_t *record_offset)
{
    return m2_sharc_dispatch_memory_ex(handler,r,bus,entry_eflags,loop_count,
        status,stop,pc,record_offset,0);
}
