#include "tgpx4_execute.h"
#include "tgpx4_fp.h"
#include <stdbool.h>

enum {
    STATE = 0x10edef0, BASE = 0x10481f0, ACTIVE = 0x10481f4,
    RECORD = 0x104824c, STOPPED = 0x10f0040,
    EFFECT_COUNT = 0x1048248, WRITE_COUNT = 0x1048240,
    EFFECTS = 0x1048200, WRITES = 0x1048120, DELAY = 0x10ed9a4
};

static uint32_t read32(const m2_tgpx4_execution_bus *bus, uint32_t at)
{
    return bus->read(bus->opaque, at, 32);
}

static void write32(const m2_tgpx4_execution_bus *bus, uint32_t at, uint32_t value)
{
    bus->write(bus->opaque, at, value, 32);
}

/* Track original CALL versus tail-JMP stack positions. PUSH/POP do not set
 * FLAGS, but downstream FP prologues do SUB/ADD ESP and expose those flags to
 * operand callbacks. Never derive these tokens from the host C call stack. */
static void call_at(const m2_tgpx4_execution_bus *bus, uint32_t entry,
    m2_tgpx4_execution_registers *r, uint32_t stack)
{
    const uint32_t saved = r->esp;
    r->esp = stack;
    bus->call(bus->opaque, entry, r);
    r->esp = saved;
}

/* CMP flags are observable by indirect callbacks before their own arithmetic.
 * Keep x86 parity/auxiliary carry as well as the usual Z/S/C/O flags. */
static void arithmetic_flags(m2_tgpx4_execution_registers *r, uint32_t result,
    bool carry, uint32_t auxiliary, bool overflow)
{
    uint32_t parity = result & 255u;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    r->flags = (r->flags & ~0x8d5u) | (carry ? 1u : 0)
        | (!(parity & 1u) ? 4u : 0) | (auxiliary & 0x10u)
        | (result == 0 ? 0x40u : 0) | ((result >> 24) & 0x80u)
        | (overflow ? 0x800u : 0);
}

static void compare(m2_tgpx4_execution_registers *r, uint32_t a, uint32_t b)
{
    const uint32_t result = a - b;
    arithmetic_flags(r, result, a < b, a ^ b ^ result,
                      (a ^ b) & (a ^ result) & 0x80000000u);
}

static void drain(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r, bool delayed, uint32_t stack)
{
    r->eax = read32(bus, EFFECT_COUNT);
    compare(r, r->eax, 0);
    if (r->eax)
        r->esi = 0;
    for (uint32_t i = 0; i < read32(bus, EFFECT_COUNT);) {
        uint32_t entry = read32(bus, EFFECTS + i * 4u);
        if (delayed)
            r->edx = entry;
        else
            r->eax = entry;
        call_at(bus, entry, r, stack);
        ++i;
        r->esi = i;
        compare(r, i, read32(bus, EFFECT_COUNT));
    }
    r->eax = read32(bus, WRITE_COUNT);
    compare(r, r->eax, 0);
    if (r->eax) {
        if (delayed)
            r->ebx = 0;
        else
            r->edi = 0;
        r->esi = WRITES + 4;
    }
    for (uint32_t i = 0; i < read32(bus, WRITE_COUNT);) {
        r->edx = read32(bus, WRITES + i * 12u + 4u);
        r->ecx = read32(bus, WRITES + i * 12u);
        r->eax = read32(bus, WRITES + i * 12u + 8u);
        call_at(bus, r->eax, r, stack);
        ++i;
        if (delayed)
            r->ebx = i;
        else
            r->edi = i;
        r->esi += 12;
        compare(r, i, read32(bus, WRITE_COUNT));
    }
}

static void execute_batches(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r, bool single_batch)
{
    const uint32_t saved_ebp = r->ebp, saved_ebx = r->ebx;
    const uint32_t saved_esi = r->esi, saved_edi = r->edi;
    r->ebp = 0;
    compare(r, read32(bus, STOPPED), 0);
    if (!single_batch && read32(bus, STOPPED)) {
        r->ebp = saved_ebp;
        return;
    }

    unsigned batch_remaining = 1000;
    do {
        r->fp_control = 0x3f;
        r->eax = read32(bus, STATE + 0x140);
        r->ecx = read32(bus, 0x10f0044);
        uint32_t cursor = read32(bus, STATE + 0x144);
        r->edi = cursor;
        r->edx = read32(bus, 0x10f0048);
        write32(bus, BASE, r->eax);
        r->eax = read32(bus, STATE + 0x14c);
        write32(bus, 0x10481e8, r->ecx);
        r->ecx = read32(bus, STATE + 0x148);
        write32(bus, ACTIVE, STATE);
        write32(bus, RECORD, cursor);
        write32(bus, 0x10481f8, 0x10ee040);
        write32(bus, 0x10481fc, 0x10ef040);
        write32(bus, 0x10481e0, r->edx);
        write32(bus, 0x1048244, r->eax);
        write32(bus, 0x10481ec, r->ecx);

        for (unsigned remaining = 1000; remaining; --remaining) {
            batch_remaining = remaining - 1u;
            r->ebx = batch_remaining;
            r->eax = 1;
            if (read32(bus, cursor + 0x84)) {
                r->edx = read32(bus, 0x10f0048);
                if (read32(bus, r->edx + 0x88) == 32)
                    write32(bus, STOPPED, r->eax);
            }
            if (read32(bus, cursor + 0x88)) {
                r->ecx = read32(bus, 0x10f0044);
                if (!read32(bus, r->ecx + 0x88)) {
                    write32(bus, STOPPED, r->eax);
                    break;
                }
            }
            compare(r, read32(bus, STOPPED), 0);
            if (read32(bus, STOPPED))
                break;
            r->edx = read32(bus, cursor + 0x80);
            write32(bus, EFFECT_COUNT, 0);
            write32(bus, WRITE_COUNT, 0);
            call_at(bus, r->edx, r, r->esp - (single_batch ? 24u : 28u));
            drain(bus, r, false, r->esp - (single_batch ? 24u : 28u));

            r->eax = read32(bus, DELAY);
            compare(r, r->eax, 0);
            if (r->eax) {
                r->ecx = read32(bus, ACTIVE);
                const uint32_t saved_pc = read32(bus, r->ecx + 0x114);
                r->edi = saved_pc;
                write32(bus, r->ecx + 0x114, r->eax);
                const uint32_t offset = r->eax * 0x94u;
                const uint32_t base = read32(bus, BASE);
                r->eax = offset + base;
                /* ADD overwrites IMUL flags, including the carry bits. */
                arithmetic_flags(r, r->eax, r->eax < offset, offset ^ base ^ r->eax,
                                  ~(offset ^ base) & (offset ^ r->eax) & 0x80000000u);
                write32(bus, EFFECT_COUNT, 0);
                r->ecx = read32(bus, r->eax + 0x80);
                write32(bus, RECORD, r->eax);
                write32(bus, WRITE_COUNT, 0);
                call_at(bus, r->ecx, r, r->esp - (single_batch ? 24u : 28u));
                drain(bus, r, true, r->esp - (single_batch ? 24u : 28u));
                r->eax = read32(bus, ACTIVE);
                r->ebx = remaining - 1u;
                write32(bus, r->eax + 0x114, saved_pc);
                cursor = saved_pc * 0x94u + read32(bus, BASE);
                write32(bus, DELAY, 0);
                write32(bus, RECORD, cursor);
            } else {
                r->eax = read32(bus, ACTIVE);
                cursor = read32(bus, RECORD);
            }
            r->edi = cursor;

            r->ecx = read32(bus, r->eax + 0x110);
            if (r->ecx & 0x4000u) {
                r->edx = 0xffff;
                const uint16_t count = (uint16_t)(bus->read(bus->opaque, r->eax + 0x122, 16) - 1u);
                bus->write(bus->opaque, r->eax + 0x122, count, 16);
                if (!count) {
                    r->ecx &= ~0x4000u;
                    write32(bus, r->eax + 0x110, r->ecx);
                }
            } else {
                cursor += 0x94u;
                r->edi = cursor;
                write32(bus, r->eax + 0x114, read32(bus, r->eax + 0x114) + 1u);
                write32(bus, RECORD, cursor);
            }
        }
        write32(bus, STATE + 0x144, cursor);
        compare(r, read32(bus, STOPPED), 0);
    } while (!single_batch && !read32(bus, STOPPED));
    if (single_batch)
        r->ecx = batch_remaining; /* Native POP ECX reads its reused counter slot. */
    r->ebp = saved_ebp;
    r->ebx = saved_ebx;
    r->esi = saved_esi;
    r->edi = saved_edi;
}

void m2_tgpx4_execute(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    execute_batches(bus, r, false);
}

/* 004b4660 binds the machine even when already stopped, executes at most
 * 1000 instructions and returns the remaining count in ECX. It is not the
 * stop-gated, continuously reloading driver entry at 004b6010. */
void m2_tgpx4_execute_batch(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    execute_batches(bus, r, true);
}

void m2_tgpx4_execute_wrapper(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    const uint32_t ebx = r->ebx, ebp = r->ebp, esi = r->esi, edi = r->edi;
    const uint32_t depth = entry == 0x4b36e0u ? 20u : entry == 0x4b35a0u ? 12u : 16u;
    if (entry == 0x4b3550u) {
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x60);
        r->eax = read32(bus, r->eax + 0x2c);
        call_at(bus, r->eax, r, r->esp);
        return;
    }
    if (entry == 0x4b3560u || entry == 0x4b3630u) {
        r->eax = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->eax + 0x110);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x0c);
        write32(bus, 0x10481e4, r->ecx);
        call_at(bus, r->eax, r, r->esp - (entry == 0x4b3560u ? 4u : 12u));
        if (entry == 0x4b3560u) {
            r->edx = read32(bus, RECORD);
            r->ecx = r->eax;
            r->eax = read32(bus, r->edx + 0x08);
            call_at(bus, r->eax, r, r->esp - 4u);
            r->ecx = read32(bus, RECORD);
            r->edx = read32(bus, r->ecx + 0x68);
            call_at(bus, r->edx, r, r->esp);
            return;
        }
        r->ecx = read32(bus, RECORD);
        r->edx = read32(bus, r->ecx + 0x20);
        r->esi = r->eax;
        call_at(bus, r->edx, r, r->esp - 12u);
        r->edi = r->eax;
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + 0x08);
        r->ecx = r->esi;
        call_at(bus, r->edx, r, r->esp - 12u);
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + 0x1c);
        r->ecx = r->edi;
        call_at(bus, r->edx, r, r->esp - 12u);
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x68);
        r->esi = esi;
        r->edi = edi;
        call_at(bus, r->ecx, r, r->esp);
        return;
    }

    r->eax = read32(bus, RECORD);
    r->ecx = read32(bus, r->eax + 0x0c);
    call_at(bus, r->ecx, r, r->esp - depth);
    r->edx = read32(bus, RECORD);
    r->esi = r->eax;
    const bool dual_alu = entry == 0x4b3690u || entry == 0x4b36e0u;
    r->eax = read32(bus, r->edx + (dual_alu ? 0x20u : 0x28u));
    call_at(bus, r->eax, r, r->esp - depth);
    if (entry == 0x4b35a0u) {
        r->edx = read32(bus, RECORD);
        r->edi = r->eax;
        r->eax = read32(bus, r->edx + 0x08);
        r->ecx = r->esi;
        call_at(bus, r->eax, r, r->esp - 12u);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x2c);
        r->ecx = r->edi;
        r->edi = edi;
        r->esi = esi;
        call_at(bus, r->eax, r, r->esp);
        return;
    }
    r->ecx = read32(bus, RECORD);
    r->edx = read32(bus, r->ecx + (dual_alu ? 0x28u : 0x44u));
    r->edi = r->eax;
    call_at(bus, r->edx, r, r->esp - depth);
    r->ebx = r->eax;
    if (entry == 0x4b36e0u) {
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x44);
        call_at(bus, r->ecx, r, r->esp - 20u);
        r->edx = read32(bus, RECORD);
        r->ebp = r->eax;
        r->eax = read32(bus, r->edx + 0x08);
        r->ecx = r->esi;
        call_at(bus, r->eax, r, r->esp - 20u);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x1c);
        r->ecx = r->edi;
        call_at(bus, r->eax, r, r->esp - 20u);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x2c);
        r->ecx = r->ebx;
        call_at(bus, r->eax, r, r->esp - 20u);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x48);
        r->ecx = r->ebp;
    } else {
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + 0x08);
        r->ecx = r->esi;
        call_at(bus, r->edx, r, r->esp - 16u);
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + (dual_alu ? 0x1cu : 0x2cu));
        r->ecx = r->edi;
        call_at(bus, r->edx, r, r->esp - 16u);
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + (dual_alu ? 0x2cu : 0x48u));
        r->ecx = r->ebx;
    }
    r->edi = edi;
    r->esi = esi;
    r->ebp = ebp;
    r->ebx = ebx;
    call_at(bus, entry == 0x4b36e0u ? r->eax : r->edx, r, r->esp);
}

static void logical_flags(m2_tgpx4_execution_registers *r, uint32_t result)
{
    /* AF is undefined for x86 logical instructions. Unicorn's deterministic
     * value is zero; no architectural auxiliary-carry behavior is inferred. */
    arithmetic_flags(r, result, false, 0, false);
}

static uint32_t add(m2_tgpx4_execution_registers *r, uint32_t a, uint32_t b)
{
    const uint32_t result = a + b;
    arithmetic_flags(r, result, result < a, a ^ b ^ result,
                      ~(a ^ b) & (a ^ result) & 0x80000000u);
    return result;
}

static uint32_t increment(m2_tgpx4_execution_registers *r, uint32_t before, bool down)
{
    const uint32_t carry = r->flags & 1u;
    uint32_t result;
    if (down) {
        compare(r, before, 1);
        result = before - 1u;
    } else {
        result = add(r, before, 1);
    }
    r->flags = (r->flags & ~1u) | carry;
    return result;
}

static void integer_nz(const m2_tgpx4_execution_bus *bus, m2_tgpx4_execution_registers *r)
{
    r->ecx = read32(bus, ACTIVE);
    r->edx = read32(bus, r->ecx + 0x110) & ~0x18u;
    write32(bus, r->ecx + 0x110, r->edx);
    if (r->eax & 0x80000000u) {
        r->edx |= 0x10;
        write32(bus, r->ecx + 0x110, r->edx);
    }
    logical_flags(r, r->eax);
    if (!r->eax) {
        write32(bus, r->ecx + 0x110, r->edx | 8u);
        logical_flags(r, r->edx | 8u);
    }
}

static void integer_clamp(const m2_tgpx4_execution_bus *bus, m2_tgpx4_execution_registers *r)
{
    r->ecx = read32(bus, ACTIVE);
    r->edx = read32(bus, r->ecx + 0x110) & ~0x100u;
    write32(bus, r->ecx + 0x110, r->edx);
    logical_flags(r, r->eax);
    if (r->eax & 0x80000000u) {
        r->edx |= 0x100;
        write32(bus, r->ecx + 0x110, r->edx);
        r->eax = 0;
        logical_flags(r, 0);
    }
}

bool m2_tgpx4_execute_integer(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    bool binary = false, multiply = false;
    switch (entry) {
    case 0x4b38e0:
        r->eax = 0;
        logical_flags(r, 0);
        return true;
    case 0x4b4df0: multiply = true; /* fall through */
    case 0x4b50b0: case 0x4b5100: case 0x4b5150: case 0x4b51e0:
    case 0x4b5230: case 0x4b52a0: case 0x4b52f0: case 0x4b5360:
        binary = true;
        break;
    case 0x4b3890: case 0x4b38d0: case 0x4b4f30: case 0x4b4f80:
    case 0x4b4fd0: case 0x4b5020: case 0x4b5070: case 0x4b51a0:
    case 0x4b5590: case 0x4b55e0:
        break;
    default:
        return false;
    }
    const uint32_t esi = r->esi;
    r->eax = read32(bus, RECORD);
    r->ecx = read32(bus, r->eax + (multiply ? 0x14u : 0));
    call_at(bus, r->ecx, r, r->esp - (entry == 0x4b38d0 ? 0u : binary ? 8u : 4u));
    if (entry == 0x4b38d0)
        return true;
    if (binary) {
        r->edx = read32(bus, RECORD);
        r->esi = r->eax;
        r->eax = read32(bus, r->edx + (multiply ? 0x18u : 4u));
        call_at(bus, r->eax, r, r->esp - 8u);
        switch (entry) {
        case 0x4b4df0: r->eax *= r->esi; break; /* Low 32 bits of signed IMUL. */
        case 0x4b50b0: r->eax ^= r->esi; break;
        case 0x4b5100: r->eax |= r->esi; break;
        case 0x4b5150: r->eax &= r->esi; break;
        case 0x4b52f0: case 0x4b5360: r->eax += r->esi; break;
        default: r->eax -= r->esi; break; /* The second reader is the minuend. */
        }
        r->esi = esi;
    } else if (entry >= 0x4b4f30 && entry <= 0x4b5020) {
        r->edx = read32(bus, RECORD);
        r->ecx = (read32(bus, r->edx + 0x10) >> 15) & 31u;
        if (entry == 0x4b4f80) {
            const uint32_t sign = r->eax & 0x80000000u;
            r->eax >>= r->ecx;
            if (sign && r->ecx)
                r->eax |= 0xffffffffu << (32u - r->ecx);
        } else if (entry == 0x4b5020) {
            r->eax >>= r->ecx;
        } else {
            r->eax <<= r->ecx; /* Both original left-shift entries are identical. */
        }
    } else if (entry == 0x4b5070) {
        r->eax = ~r->eax;
    } else if (entry == 0x4b51a0) {
        r->eax &= 0x7fffffffu; /* Native sign-bit clear, not signed integer abs. */
    } else if (entry == 0x4b5590 || entry == 0x4b55e0) {
        r->edx = read32(bus, RECORD);
        const uint32_t amount = ((read32(bus, r->edx + 0x10) >> 15) & 31u) << 23;
        r->eax = ((entry == 0x4b5590 ? r->eax - amount : r->eax + amount) | r->eax) & 0x7f800000u;
    }

    if (multiply) {
        r->ecx = read32(bus, ACTIVE);
        r->edx = read32(bus, r->ecx + 0x110) & ~0x100000u;
        write32(bus, r->ecx + 0x110, r->edx);
        if (r->eax & 0x80000000u) {
            r->edx |= 0x100000;
            write32(bus, r->ecx + 0x110, r->edx);
        }
        r->edx &= ~0x80000u;
        write32(bus, r->ecx + 0x110, r->edx);
        logical_flags(r, r->eax);
        if (!r->eax) {
            r->edx |= 0x80000;
            write32(bus, r->ecx + 0x110, r->edx);
            logical_flags(r, r->edx);
        }
        return true;
    }
    if (entry == 0x4b3890 || entry == 0x4b5230 || entry == 0x4b52f0) {
        integer_clamp(bus, r);
        if (entry == 0x4b3890)
            return true;
    }
    integer_nz(bus, r);
    if (entry == 0x4b51e0) {
        r->eax = 0;
        logical_flags(r, 0);
    }
    return true;
}

void m2_tgpx4_enqueue_write(const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r, uint32_t address, uint32_t value)
{
    r->ecx = read32(bus, WRITE_COUNT);
    r->eax = r->ecx * 3u;
    r->eax = add(r, r->eax, r->eax);
    r->eax = add(r, r->eax, r->eax);
    write32(bus, WRITES + r->eax + 8u, r->edx);
    r->edx = address;
    write32(bus, WRITES + r->eax, r->edx);
    r->edx = value;
    r->ecx = increment(r, r->ecx, false);
    write32(bus, WRITES + r->eax + 4u, r->edx);
    write32(bus, WRITE_COUNT, r->ecx);
}

bool m2_tgpx4_execute_control(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    switch (entry) {
    case 0x4b44b0:
        return true;
    case 0x4b44c0:
        r->eax = 0;
        logical_flags(r, r->eax);
        return true;
    case 0x4b4510: case 0x4b4520:
        r->eax = entry == 0x4b4510 ? read32(bus, r->ecx) - r->edx : read32(bus, r->ecx) + r->edx;
        r->eax &= 0x3fff;
        logical_flags(r, r->eax);
        write32(bus, r->ecx, r->eax);
        return true;
    case 0x4b4530:
        write32(bus, r->ecx, add(r, read32(bus, r->ecx), r->edx));
        return true;
    case 0x4b4540:
        r->eax = read32(bus, EFFECT_COUNT);
        write32(bus, EFFECTS + r->eax * 4u, r->ecx);
        r->eax = increment(r, r->eax, false);
        write32(bus, EFFECT_COUNT, r->eax);
        return true;
    case 0x4b4560:
        write32(bus, STOPPED, r->eax);
        return true;
    case 0x4b4570:
        r->eax = read32(bus, ACTIVE);
        r->ecx = increment(r, read32(bus, r->eax + 0x124), true);
        write32(bus, r->eax + 0x124, r->ecx);
        r->eax = read32(bus, r->eax + 0x128u + r->ecx * 4u);
        return true;
    case 0x4b4590:
        r->eax = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->eax + 0x124);
        write32(bus, r->eax + 0x128u + r->ecx * 4u, r->edx);
        write32(bus, r->eax + 0x124, increment(r, read32(bus, r->eax + 0x124), false));
        return true;
    case 0x4b45b0:
        r->edx = read32(bus, ACTIVE);
        r->eax &= 0xfff;
        r->ecx = add(r, r->eax * 0x94u, read32(bus, BASE));
        write32(bus, r->edx + 0x114, r->eax);
        write32(bus, RECORD, r->ecx);
        return true;
    case 0x4b45e0:
        r->eax = read32(bus, ACTIVE);
        r->ecx = increment(r, read32(bus, r->eax + 0x114), false);
        write32(bus, DELAY, r->ecx);
        return true;
    case 0x4b4600: case 0x4b4610: case 0x4b4620: case 0x4b4630:
        r->ecx = read32(bus, entry < 0x4b4620 ? 0x10481fc : 0x10481f8);
        r->eax &= 0x3ff;
        logical_flags(r, r->eax);
        if (entry & 16u)
            write32(bus, r->ecx + r->eax * 4u, r->edx);
        else
            r->eax = read32(bus, r->ecx + r->eax * 4u);
        return true;
    case 0x4b4640: case 0x4b4650:
        call_at(bus, read32(bus, entry == 0x4b4640 ? 0x1048244 : 0x10481ec), r, r->esp);
        return true;
    case 0x4b48c0:
        r->ecx = read32(bus, ACTIVE);
        r->eax = increment(r, read32(bus, r->ecx + 0x114), false);
        write32(bus, DELAY, r->eax);
        r->eax = read32(bus, r->ecx + 0x124) - 1u;
        write32(bus, r->ecx + 0x124, r->eax);
        r->eax = (read32(bus, r->ecx + 0x128u + r->eax * 4u) - 1u) & 0xfffu;
        r->edx = add(r, r->eax * 0x94u, read32(bus, BASE));
        write32(bus, r->ecx + 0x114, r->eax);
        write32(bus, RECORD, r->edx);
        return true;
    case 0x4b4910: case 0x4b4970: case 0x4b49e0:
    case 0x4b4b60: case 0x4b4ba0: case 0x4b4bf0: {
        r->eax = read32(bus, RECORD);
        const bool conditional = entry != 0x4b4910 && entry != 0x4b4b60;
        if (conditional) {
            r->ecx = read32(bus, 0x10481e4);
            const bool set = (read32(bus, r->eax + 0x6c) & r->ecx) != 0;
            logical_flags(r, read32(bus, r->eax + 0x6c) & r->ecx);
            if (set != (entry == 0x4b49e0 || entry == 0x4b4bf0))
                return true;
            r->edx = read32(bus, r->eax + 0x7c);
            call_at(bus, r->edx, r, r->esp - (entry < 0x4b4b60 ? 8u : 4u));
        } else {
            r->ecx = read32(bus, r->eax + 0x7c);
            call_at(bus, r->ecx, r, r->esp - (entry < 0x4b4b60 ? 8u : 4u));
        }
        const uint32_t esi = r->esi;
        r->ecx = read32(bus, ACTIVE);
        r->edx = read32(bus, r->ecx + 0x114);
        write32(bus, DELAY, r->edx + 1u);
        if (entry == 0x4b4910 || entry == 0x4b4970 || entry == 0x4b49e0) {
            r->edx += 2u;
            r->esi = read32(bus, r->ecx + 0x124);
            write32(bus, r->ecx + 0x128u + r->esi * 4u, r->edx);
            write32(bus, r->ecx + 0x124, read32(bus, r->ecx + 0x124) + 1u);
        }
        r->eax = (r->eax - 1u) & 0xfffu;
        r->edx = add(r, r->eax * 0x94u, read32(bus, BASE));
        write32(bus, r->ecx + 0x114, r->eax);
        write32(bus, RECORD, r->edx);
        r->esi = esi;
        return true;
    }
    case 0x4b4a50: case 0x4b4aa0: {
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x74);
        r->edx = read32(bus, r->ecx);
        const uint32_t test = read32(bus, r->eax + 0x6c) & r->edx;
        logical_flags(r, test);
        if ((test != 0) != (entry == 0x4b4a50))
            return true;
        r->edx = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->edx + 0x114);
        r->eax = (read32(bus, r->eax + 0x70) + r->ecx) & 0xfffu;
        const uint32_t delay = r->ecx + 1u;
        r->ecx = add(r, r->eax * 0x94u, read32(bus, BASE));
        write32(bus, DELAY, delay);
        write32(bus, RECORD, r->ecx);
        write32(bus, r->edx + 0x114, r->eax);
        return true;
    }
    case 0x4b4af0: {
        logical_flags(r, read32(bus, 0x10481e4) & 0x8000u);
        if (!(read32(bus, 0x10481e4) & 0x8000u))
            return true;
        r->ecx = read32(bus, ACTIVE);
        r->edx = read32(bus, r->ecx + 0x114);
        write32(bus, DELAY, r->edx + 1u);
        r->eax = read32(bus, RECORD);
        r->eax = (read32(bus, r->eax + 0x70) + r->edx) & 0xfffu;
        r->edx = r->eax * 0x94u + read32(bus, BASE);
        write32(bus, r->ecx + 0x114, r->eax);
        r->eax = 0xffff;
        const uint16_t count = (uint16_t)(bus->read(bus->opaque, r->ecx + 0x120, 16) - 1u);
        bus->write(bus->opaque, r->ecx + 0x120, count, 16);
        const uint16_t result = (uint16_t)(count - 1u);
        arithmetic_flags(r, result, count < 1, count ^ 1u ^ result,
                          (count ^ 1u) & (count ^ result) & 0x8000u);
        r->flags = (r->flags & ~0x80u) | ((result >> 8) & 0x80u);
        write32(bus, RECORD, r->edx);
        /* Original clears the loop bit when the decremented counter equals
         * ONE, not zero. Preserve this unusual native termination rule. */
        if (count == 1) {
            const uint32_t status = read32(bus, r->ecx + 0x110) & ~0x8000u;
            write32(bus, r->ecx + 0x110, status);
            logical_flags(r, status);
        }
        return true;
    }
    case 0x4b4c40:
        r->edx = read32(bus, ACTIVE);
        r->eax = read32(bus, r->edx + 0x118);
        r->ecx = r->eax & 0x3ffu;
        logical_flags(r, r->ecx);
        r->ecx = read32(bus, read32(bus, 0x10481fc) + r->ecx * 4u);
        r->eax = increment(r, r->eax, false);
        write32(bus, r->edx + 0x118, r->eax);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x6c);
        call_at(bus, r->eax, r, r->esp);
        return true;
    case 0x4b4c80:
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x6c);
        call_at(bus, r->ecx, r, r->esp - 4u);
        r->ecx = read32(bus, ACTIVE);
        write32(bus, r->ecx + 0x118, read32(bus, r->ecx + 0x118) - 1u);
        r->ecx = read32(bus, r->ecx + 0x118) & 0x3ffu;
        r->edx = read32(bus, 0x10481fc);
        logical_flags(r, r->ecx);
        write32(bus, r->edx + r->ecx * 4u, r->eax);
        return true;
    case 0x4b4cb0: case 0x4b4ce0: case 0x4b4d00: case 0x4b4d30: {
        const bool relative = entry == 0x4b4cb0 || entry == 0x4b4d00;
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x74);
        r->edx = read32(bus, r->ecx) & 0x3ffu;
        r->eax = read32(bus, entry < 0x4b4d00 ? 0x10481fc : 0x10481f8);
        logical_flags(r, r->edx);
        if (relative) {
            r->ecx = read32(bus, r->eax + r->edx * 4u);
            r->edx = read32(bus, ACTIVE);
            r->eax = read32(bus, r->edx + 0x114) + r->ecx + 1u;
        } else {
            r->eax = read32(bus, r->eax + r->edx * 4u);
        }
        return true;
    }
    case 0x4b4d50: case 0x4b4d80: case 0x4b4da0: case 0x4b4dd0:
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x70) & 0x3ffu;
        r->edx = read32(bus, entry < 0x4b4da0 ? 0x10481fc : 0x10481f8);
        logical_flags(r, r->ecx);
        r->eax = read32(bus, r->edx + r->ecx * 4u);
        if (entry == 0x4b4d50 || entry == 0x4b4da0) {
            r->ecx = read32(bus, ACTIVE);
            r->edx = read32(bus, r->ecx + 0x114);
            r->eax += r->edx + 1u;
        }
        return true;
    default:
        return false;
    }
}

bool m2_tgpx4_execute_register(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    static const uint32_t special_offsets[] = {
        0xa0, 0xa4, 0x13c, 0x138, 0x120, 0x11c, 0x110, 0x118, 0x108
    };
    if (entry >= 0x4b3ba0 && entry <= 0x4b3c20 && !(entry & 15u)) {
        const unsigned i = (entry - 0x4b3ba0) / 16;
        r->eax = read32(bus, ACTIVE);
        bus->write(bus->opaque, r->eax + special_offsets[i], r->ecx, i == 4 ? 16 : 32);
        return true;
    }
    if (entry >= 0x4b4060 && entry <= 0x4b40e0 && !(entry & 15u)) {
        const unsigned i = (entry - 0x4b4060) / 16;
        r->eax = read32(bus, ACTIVE);
        r->eax = bus->read(bus->opaque, r->eax + special_offsets[i], i == 4 ? 16 : 32);
        return true;
    }
    if (entry >= 0x4b3da0 && entry <= 0x4b3f90 && !(entry & 15u)) {
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + (0x4b3f90u - entry) / 4u, r->ecx);
        return true;
    }
    if (entry >= 0x4b42b0 && entry <= 0x4b44a0 && !(entry & 15u)) {
        r->eax = read32(bus, ACTIVE);
        r->eax = read32(bus, r->eax + (0x4b44a0u - entry) / 4u);
        return true;
    }
    if (entry >= 0x4b3ca0 && entry <= 0x4b3d80 && !(entry & 31u)) {
        r->eax = read32(bus, ACTIVE);
        r->ecx &= 0x3fff;
        logical_flags(r, r->ecx);
        write32(bus, r->eax + 0x80 + (0x4b3d80u - entry) / 8u, r->ecx);
        return true;
    }
    if (entry >= 0x4b41b0 && entry <= 0x4b4290 && (entry & 31u) == 16) {
        r->eax = read32(bus, ACTIVE);
        r->eax = read32(bus, r->eax + 0x80 + (0x4b4290u - entry) / 8u) & 0x3fff;
        logical_flags(r, r->eax);
        return true;
    }
    switch (entry) {
    case 0x4b3750: case 0x4b3760: case 0x4b37a0: case 0x4b3820:
    case 0x4b3b80: case 0x4b3b90:
        /* Original RET-only bodies, including architecturally named controls. */
        return true;
    case 0x4b3b70:
        r->ecx = read32(bus, ACTIVE);
        r->eax = r->ecx + 0x80u + r->eax * 4u;
        return true;
    case 0x4b3770:
        r->ecx = read32(bus, RECORD);
        r->edx = ~read32(bus, r->ecx + 0x78);
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + 0x11c, read32(bus, r->eax + 0x11c) & r->edx);
        r->ecx = read32(bus, r->ecx + 0x70) | read32(bus, r->eax + 0x11c);
        logical_flags(r, r->ecx);
        write32(bus, r->eax + 0x11c, r->ecx);
        return true;
    case 0x4b37b0:
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x74);
        r->edx = (r->edx & 0xffff0000u) | bus->read(bus->opaque, r->ecx, 16);
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + 0x110, read32(bus, r->eax + 0x110) | 0x8000u);
        logical_flags(r, read32(bus, r->eax + 0x110));
        bus->write(bus->opaque, r->eax + 0x120, r->edx & 0xffffu, 16);
        return true;
    case 0x4b37e0: {
        r->ecx = read32(bus, RECORD);
        r->eax = read32(bus, r->ecx + 0x74);
        r->edx = (r->edx & 0xffff0000u) | bus->read(bus->opaque, r->eax, 16);
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + 0x110, read32(bus, r->eax + 0x110) | 0x4000u);
        write32(bus, r->eax + 0x114, read32(bus, r->eax + 0x114) + 1u);
        const uint32_t before = r->ecx;
        r->ecx += 0x94u;
        arithmetic_flags(r, r->ecx, r->ecx < before, before ^ 0x94u ^ r->ecx,
                          ~(before ^ 0x94u) & (before ^ r->ecx) & 0x80000000u);
        bus->write(bus->opaque, r->eax + 0x122, r->edx & 0xffffu, 16);
        write32(bus, RECORD, r->ecx);
        return true;
    }
    case 0x4b3830:
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x74);
        r->eax = read32(bus, ACTIVE);
        r->edx = read32(bus, r->ecx);
        r->ecx = read32(bus, r->eax + 0x114);
        r->eax = r->edx + r->ecx + 1u;
        return true;
    case 0x4b3850:
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + 0x74);
        r->eax = read32(bus, r->ecx);
        return true;
    case 0x4b3860:
        r->eax = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->eax + 0x114);
        r->edx = read32(bus, RECORD);
        r->eax = read32(bus, r->edx + 0x70) + r->ecx + 1u;
        return true;
    case 0x4b3880: case 0x4b3fa0:
        r->eax = read32(bus, RECORD);
        r->eax = read32(bus, r->eax + (entry == 0x4b3880 ? 0x70 : 0x60));
        return true;
    case 0x4b4030: case 0x4b4050:
        r->eax = entry == 0x4b4030 ? 0xffffffffu : 0;
        logical_flags(r, r->eax);
        return true;
    case 0x4b4040:
        r->eax = 1;
        return true;
    case 0x4b3c30: case 0x4b3c50: {
        r->eax = read32(bus, ACTIVE);
        const uint32_t before = read32(bus, r->eax + 0x10c);
        uint32_t after;
        if (entry == 0x4b3c30) {
            r->ecx = ((r->ecx << 14) ^ before) & 0xffc000u;
            after = before ^ r->ecx;
        } else {
            r->edx = (before ^ r->ecx) & 0x3fffu;
            after = before ^ r->edx;
        }
        logical_flags(r, after);
        write32(bus, r->eax + 0x10c, after);
        return true;
    }
    case 0x4b3c70:
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + 0x10c, r->ecx);
        return true;
    case 0x4b40f0: case 0x4b4110: case 0x4b4130:
        r->eax = read32(bus, ACTIVE);
        r->eax = read32(bus, r->eax + 0x10c);
        if (entry != 0x4b4130) {
            r->eax = entry == 0x4b40f0 ? (r->eax >> 14) & 0x3ffu : r->eax & 0x3fffu;
            logical_flags(r, r->eax);
        }
        return true;
    case 0x4b4140:
        r->eax = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->eax + 0xa4);
        r->eax = read32(bus, r->eax + 0xa8u + r->ecx * 4u);
        return true;
    case 0x4b4160:
        r->eax = read32(bus, ACTIVE);
        write32(bus, r->eax + 0xa4, 0);
        return true;
    case 0x4b4170: {
        r->eax = read32(bus, ACTIVE);
        uint32_t count = read32(bus, r->eax + 0xa4);
        compare(r, count, 0);
        if (!count)
            count = 24;
        const uint32_t carry = r->flags & 1u;
        const uint32_t result = count - 1u;
        compare(r, count, 1);
        r->flags = (r->flags & ~1u) | carry; /* DEC preserves CF. */
        write32(bus, r->eax + 0xa4, result);
        return true;
    }
    case 0x4b3c80: case 0x4b4190: {
        r->eax = read32(bus, ACTIVE);
        const uint32_t offset = entry == 0x4b3c80 ? 0xa0u : 0xa4u;
        const uint32_t count = read32(bus, r->eax + offset) + 1u;
        write32(bus, r->eax + offset, count);
        compare(r, count, 24);
        if (count == 24)
            write32(bus, r->eax + offset, 0);
        return true;
    }
    default:
        return false;
    }
}

/* Native address generators defer modifier writes until the instruction's
 * queue is drained. Do not fold these writes into address calculation. */
bool m2_tgpx4_execute_address(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    switch (entry) {
    case 0x4b3a70: case 0x4b3a80:
    case 0x4b3a90: case 0x4b3aa0: case 0x4b3ab0: case 0x4b3ac0: {
        const bool second = entry == 0x4b3a80 || entry == 0x4b3aa0 || entry == 0x4b3ac0;
        r->eax = read32(bus, read32(bus, RECORD) + (second ? 0x40 : 0x5c));
        if (entry >= 0x4b3a90)
            r->eax = add(r, r->eax, read32(bus, r->ecx));
        if (entry == 0x4b3a90 || entry == 0x4b3aa0)
            r->eax = add(r, r->eax, read32(bus, r->edx));
        return true;
    }
    case 0x4b3ad0: case 0x4b3ae0:
        r->eax = read32(bus, r->edx);
        r->eax = entry == 0x4b3ad0 ? r->eax & 127u : r->eax >> 7;
        r->eax = add(r, r->eax, read32(bus, r->ecx));
        return true;
    case 0x4b3af0:
        r->eax = add(r, read32(bus, r->ecx), read32(bus, r->edx));
        return true;
    case 0x4b3b00:
        r->eax = read32(bus, r->ecx);
        return true;
    case 0x4b3b10:
        r->eax = 0;
        logical_flags(r, 0);
        return true;
    default: break;
    }

    unsigned shift = 0, immediate = 0;
    bool base_only = false, subtract = false;
    switch (entry) {
    case 0x4b58c0: shift = 8; immediate = 0x5c; break;
    case 0x4b5920: shift = 12; immediate = 0x40; break;
    case 0x4b5980: shift = 8; subtract = true; break;
    case 0x4b59e0: shift = 8; break;
    case 0x4b5a40: shift = 12; subtract = true; break;
    case 0x4b5aa0: shift = 12; break;
    case 0x4b5b00: immediate = 0x5c; break;
    case 0x4b5b40: immediate = 0x40; break;
    case 0x4b5b80: subtract = true; break;
    case 0x4b5bc0: break;
    case 0x4b5c00: base_only = true; immediate = 0x5c; break;
    case 0x4b5c40: base_only = true; immediate = 0x40; break;
    case 0x4b5c80: base_only = true; subtract = true; break;
    case 0x4b5cc0: base_only = true; break;
    default: return false;
    }
    uint32_t modifier = base_only ? 0 : read32(bus, r->edx);
    if (shift) {
        const uint32_t status = read32(bus, read32(bus, ACTIVE) + 0x11c);
        modifier &= (1u << (((status >> shift) & 7u) + 2u)) - 1u;
    }
    r->eax = read32(bus, r->ecx) + modifier;
    const uint32_t value = immediate ? read32(bus, read32(bus, RECORD) + immediate) : 1;
    const uint32_t address = base_only ? r->ecx : r->edx;
    const uint32_t count = read32(bus, WRITE_COUNT);
    uint32_t offset = count * 3u;
    offset = add(r, offset, offset);
    offset = add(r, offset, offset);
    if (base_only)
        r->edx = offset;
    else
        r->ecx = offset;
    write32(bus, WRITES + offset + 8, subtract ? 0x4b4510 : 0x4b4520);
    write32(bus, WRITES + offset, address);
    write32(bus, WRITES + offset + 4, value);
    write32(bus, WRITE_COUNT, increment(r, count, false));
    return true;
}

bool m2_tgpx4_execute_transfer(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    switch (entry) {
    case 0x4b5d00: case 0x4b5e50: {
        const uint32_t state = read32(bus, ACTIVE);
        const uint32_t count = read32(bus, WRITE_COUNT);
        uint32_t step = read32(bus, read32(bus, RECORD) + 0x64);
        if (entry == 0x4b5d00)
            r->edx = r->ecx;
        else {
            /* Native read sign-extends bit 5, write uses the raw increment.
             * Preserve this asymmetry rather than normalizing the two paths. */
            if (step & 0x20u)
                step |= 0xffffffe0u;
            r->edx = step;
        }
        r->ecx = read32(bus, state + 0x10c) + read32(bus, state + 0x108);
        r->eax = count * 3u;
        r->eax = add(r, r->eax, r->eax);
        r->eax = add(r, r->eax, r->eax);
        write32(bus, WRITES + r->eax + 8, 0x4b4530);
        write32(bus, WRITES + r->eax, state + 0x108);
        write32(bus, WRITES + r->eax + 4, step);
        write32(bus, WRITE_COUNT, increment(r, count, false));
        call_at(bus, read32(bus, entry == 0x4b5d00 ? 0x10481ec : 0x1048244), r, r->esp);
        return true;
    }
    case 0x4b5d60: case 0x4b5d90: case 0x4b5dc0:
    case 0x4b5eb0: case 0x4b5ed0:
    case 0x4b66a0: case 0x4b66d0: case 0x4b6700: {
        const uint32_t saved_esi = r->esi;
        const bool write = entry == 0x4b5d60 || entry == 0x4b5d90 || entry == 0x4b5dc0
            || entry == 0x4b66a0 || entry == 0x4b66d0;
        const bool bank_b = entry == 0x4b5d60 || entry == 0x4b5dc0 || entry == 0x4b5eb0;
        const bool external = entry >= 0x4b66a0;
        const bool write_pointer = entry == 0x4b5d60 || entry == 0x4b5d90 || entry == 0x4b66a0;
        r->eax = read32(bus, RECORD);
        r->edx = read32(bus, r->eax + (bank_b ? 0x58 : 0x3c));
        if (write)
            r->esi = r->ecx;
        r->ecx = read32(bus, r->eax + (bank_b ? 0x50 : 0x34) + (write_pointer ? 4 : 0));
        /* 004b5d90 deliberately calls the second address-generator slot,
         * despite loading the first bank's pointers. This is original code. */
        r->eax = read32(bus, r->eax + (bank_b || entry == 0x4b5d90 ? 0x4c : 0x30));
        call_at(bus, r->eax, r, r->esp - (write ? 8u : 4u));
        if (external) {
            compare(r, r->eax, 0x3ff);
            if (r->eax > 0x3ff) {
                if (write) {
                    r->edx = r->esi;
                    r->esi = saved_esi;
                }
                r->ecx = r->eax;
                call_at(bus, read32(bus, write ? 0x10481ec : 0x1048244), r, r->esp);
                return true;
            }
        }
        r->ecx = read32(bus, bank_b ? 0x10481fc : 0x10481f8);
        if (!external) {
            r->eax &= 0x3ff;
            logical_flags(r, r->eax);
        }
        if (write) {
            write32(bus, r->ecx + r->eax * 4u, r->esi);
            r->esi = saved_esi;
        } else
            r->eax = read32(bus, r->ecx + r->eax * 4u);
        return true;
    }
    case 0x4b5fd0: case 0x4b5ff0:
        compare(r, r->ecx, 0x3ff);
        if (r->ecx > 0x3ff)
            call_at(bus, read32(bus, entry == 0x4b5fd0 ? 0x1048244 : 0x10481ec), r, r->esp);
        else {
            r->eax = read32(bus, 0x10481f8);
            if (entry == 0x4b5fd0)
                r->eax = read32(bus, r->eax + r->ecx * 4u);
            else
                write32(bus, r->eax + r->ecx * 4u, r->edx);
        }
        return true;
    case 0x4b5df0:
        r->eax = read32(bus, 0x10481e8);
        r->edx = read32(bus, r->eax + 0x84);
        write32(bus, r->eax + r->edx * 4u, r->ecx);
        r->ecx = read32(bus, r->eax + 0x84);
        write32(bus, r->eax + 0x88, read32(bus, r->eax + 0x88) - 1u);
        r->ecx = (r->ecx + 1u) & 31u;
        logical_flags(r, r->ecx);
        write32(bus, r->eax + 0x84, r->ecx);
        return true;
    case 0x4b5ef0: {
        r->ecx = read32(bus, 0x10481e0);
        const uint32_t state = read32(bus, ACTIVE);
        write32(bus, state + 0x110, read32(bus, state + 0x110) & ~0x08000000u);
        r->edx = read32(bus, r->ecx + 0x80);
        r->eax = read32(bus, r->ecx + r->edx * 4u);
        write32(bus, r->ecx + 0x88, read32(bus, r->ecx + 0x88) + 1u);
        r->edx = (r->edx + 1u) & 31u;
        compare(r, read32(bus, r->ecx + 0x88), 32);
        write32(bus, r->ecx + 0x80, r->edx);
        if (read32(bus, r->ecx + 0x88) == 32) {
            const uint32_t status = read32(bus, state + 0x110) | 0x08000000u;
            logical_flags(r, status);
            write32(bus, state + 0x110, status);
        }
        return true;
    }
    case 0x4b5e20:
        r->eax = read32(bus, ACTIVE);
        r->edx = read32(bus, r->eax + 0xa0);
        write32(bus, r->eax + 0xa8 + r->edx * 4u, r->ecx);
        r->eax = read32(bus, EFFECT_COUNT);
        write32(bus, EFFECTS + r->eax * 4u, 0x4b3c80);
        r->eax = increment(r, r->eax, false);
        write32(bus, EFFECT_COUNT, r->eax);
        return true;
    case 0x4b5f40: case 0x4b5f70: case 0x4b5fa0:
        r->eax = read32(bus, EFFECT_COUNT);
        write32(bus, EFFECTS + r->eax * 4u,
            entry == 0x4b5f40 ? 0x4b4160 : entry == 0x4b5f70 ? 0x4b4170 : 0x4b4190);
        r->eax = increment(r, r->eax, false);
        write32(bus, EFFECT_COUNT, r->eax);
        r->eax = read32(bus, ACTIVE);
        r->ecx = read32(bus, r->eax + 0xa4);
        r->eax = read32(bus, r->eax + 0xa8 + r->ecx * 4u);
        return true;
    default: return false;
    }
}

bool m2_tgpx4_execute_fp(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r, uint32_t stack)
{
    bool constant = false, binary = false, aligned = false;
    unsigned allocation = 0;
    switch (entry) {
    case 0x4b3fb0: case 0x4b3fc0: case 0x4b3fd0: case 0x4b3fe0:
    case 0x4b3ff0: case 0x4b4000: case 0x4b4010: case 0x4b4020:
        constant = true; break;
    case 0x4b4e60: binary = true; allocation = 16; break;
    case 0x4b53b0: allocation = 12; break;
    case 0x4b5630: case 0x4b56a0: case 0x4b5740: case 0x4b57b0: case 0x4b5850:
        binary = true; allocation = 8; break;
    case 0x4b65c0: binary = true; /* fall through */
    case 0x4b6530: case 0x4b6630: aligned = true; break;
    case 0x4b5460: case 0x4b54b0: case 0x4b5510: case 0x4b64a0: break;
    default: return false;
    }
    if ((r->fp_control & 0x33fu) != 0x3fu) return false;
    uint32_t first = 0, second = 0, scratch = 0, result = 0;
    const uint32_t saved_ebp = r->ebp;
    if (aligned) {
        r->ebp = stack - 4u;
        compare(r, r->ebp & ~7u, 8);
    } else if (allocation) {
        /* SUB ESP is observable by the first operand reader. It is not a
         * guest arithmetic operation, but replacing it with neutral FLAGS
         * would change the recovered native callback contract. */
        compare(r, stack, allocation);
    }
    const uint32_t operand_stack = aligned ? ((stack - 4u) & ~7u) - 12u
        : stack - (allocation ? allocation : 4u) - 4u
            - (entry == 0x4b53b0 ? 4u : 0u); /* PUSH ESI after SUB ESP,12. */
    if (!constant) {
        r->eax = read32(bus, RECORD);
        r->ecx = read32(bus, r->eax + (entry == 0x4b4e60 ? 0x14u : 0));
        call_at(bus, r->ecx, r, operand_stack);
        first = r->eax;
        if (binary) {
            /* The first reader can change the active decoded record. */
            r->edx = read32(bus, RECORD);
            r->eax = read32(bus, r->edx + (entry == 0x4b4e60 ? 0x18u : 4u));
            call_at(bus, r->eax, r, operand_stack);
            second = r->eax;
        }
    }
    m2_tgpx4_fp_state fp = {r->fp_control, r->fp_status,
        entry == 0x4b5460 ? read32(bus, 0x10f1fec) : 0};
    uint32_t status = 0;
    if (!constant) {
        r->ecx = read32(bus, ACTIVE);
        status = read32(bus, r->ecx + 0x110);
    }
    if (!m2_tgpx4_fp_operation_details(entry, first, second, &status, &fp, &result, &scratch)) {
        r->ebp = saved_ebp;
        return false;
    }
    r->fp_control = fp.control;
    r->fp_status = fp.status;
    r->eax = result;
    if (constant) {
        r->ecx = result; /* POP ECX reads the overwritten local slot. */
        return true;
    }
    write32(bus, r->ecx + 0x110, status);
    r->edx = entry == 0x4b53b0 ? scratch : status & ~(entry == 0x4b4e60 ? 0x80000u : 8u);
    if (allocation) {
        /* ADD ESP in the native epilogue replaces the arithmetic FLAGS. */
        const uint32_t before = stack - allocation;
        arithmetic_flags(r, stack, stack < before, before ^ allocation ^ stack,
            (~(before ^ allocation) & (before ^ stack) & 0x80000000u) != 0);
    } else if (entry == 0x4b65c0) {
        logical_flags(r, 0); /* XOR EAX,EAX before restoring EBP. */
    } else if (entry == 0x4b5460) {
        logical_flags(r, result ? result : status);
    } else {
        /* Final TEST AH,44, unless the equal branch ORs the guest Z bit.
         * The following FSTP may change C1, which TEST does not inspect. */
        logical_flags(r, status & 8u ? status : (fp.status >> 8) & 0x44u);
    }
    if (entry == 0x4b5460) r->ecx = first;
    else if (entry == 0x4b54b0 || entry == 0x4b5510 || entry == 0x4b64a0) r->ecx = result;
    if (aligned) r->ebp = saved_ebp;
    return true;
}

bool m2_tgpx4_execute_board_memory(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    if (entry == 0x4c5a70) {
        r->eax = r->ecx - 0x400000u;
        compare(r, r->eax, 0x3fffff);
        if (r->eax <= 0x3fffffu) {
            r->eax = read32(bus, 0x5aa700);
            write32(bus, r->eax + r->ecx * 4u - 0x1000000u, r->edx);
        }
    } else if (entry == 0x4c5a90) {
        compare(r, r->ecx, 0x400000);
        if (r->ecx < 0x400000) {
            r->eax = 0;
            logical_flags(r, 0);
        } else {
            compare(r, r->ecx, 0x800000);
            if (r->ecx < 0x800000) {
                r->eax = read32(bus, 0x5aa700);
                r->eax = read32(bus, r->eax + r->ecx * 4u);
            } else {
                r->edx = read32(bus, 0x5aa8dc);
                r->eax = read32(bus, r->edx + r->ecx * 4u - 0x2000000u);
            }
        }
    } else return false;
    return true;
}

bool m2_tgpx4_dispatch(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    switch (entry) {
    case 0x4b3550: case 0x4b3560: case 0x4b35a0: case 0x4b35e0:
    case 0x4b3630: case 0x4b3690: case 0x4b36e0:
        m2_tgpx4_execute_wrapper(entry, bus, r);
        return true;
    default:
        return m2_tgpx4_execute_register(entry, bus, r)
            || m2_tgpx4_execute_integer(entry, bus, r)
            || m2_tgpx4_execute_control(entry, bus, r)
            || m2_tgpx4_execute_address(entry, bus, r)
            || m2_tgpx4_execute_transfer(entry, bus, r)
            || m2_tgpx4_execute_fp(entry, bus, r, r->esp);
    }
}
