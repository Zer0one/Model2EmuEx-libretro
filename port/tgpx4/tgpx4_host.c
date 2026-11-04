#include "tgpx4_host.h"

static void resume(m2_tgpx4_host *host)
{
    host->stopped = 0;
    host->run(host->opaque);
}

static void store(uint8_t *memory, uint32_t value, unsigned bytes)
{
    for (unsigned byte = 0; byte < bytes; ++byte)
        memory[byte] = (uint8_t)(value >> (byte * 8));
}

static uint32_t load_word(const uint8_t *memory)
{
    return (uint32_t)memory[0] | (uint32_t)memory[1] << 8
        | (uint32_t)memory[2] << 16 | (uint32_t)memory[3] << 24;
}

static void upload(m2_tgpx4_host *host, uint32_t value, unsigned bytes)
{
    store(host->program + host->upload_offset, value, bytes);
    host->upload_offset += bytes;
}

static void write_shared(m2_tgpx4_host *host, uint32_t address, uint32_t value)
{
    if (address == 0x801008u) {
        host->shared_write = value;
        return;
    }
    if (address == 0x803008u) {
        host->reg_803008 = value;
        return;
    }
    if ((address & 0xfffff000u) == 0x804000u && (host->data_control & 0x80000000u)) {
        store(host->data + host->data_offset, value, 4);
        host->data_offset += 4;
        return;
    }

    address &= 0xffffu;
    if (address < 0x3ff0u && !(address & 15u))
        value |= (address & 0x3f0u) << 19;
    else if (address - 0x4000u >= 0x4000u)
        return;
    const uint32_t offset = host->shared_write & 0x7ffffu;
    store(host->shared + offset, value, 4);
    host->shared_write = (offset + 4) & 0x7ffffu;
}

static void push(m2_tgpx4_host *host, uint32_t value)
{
    tgp_fifo *fifo = host->input;
    fifo->buf[fifo->wr] = value;
    fifo->wr = (fifo->wr + 1) & 31;
    fifo->free = (int32_t)((uint32_t)fifo->free - 1u);
    resume(host);
}

static uint32_t pop(m2_tgpx4_host *host)
{
    tgp_fifo *fifo = host->output;
    const uint32_t value = fifo->buf[fifo->rd];
    fifo->rd = (fifo->rd + 1) & 31;
    /* The native INC/JZ tests the new counter against zero, not 32. */
    fifo->free = (int32_t)((uint32_t)fifo->free + 1u);
    if (fifo->free != 0)
        resume(host);
    return value;
}

bool m2_tgpx4_host_access(m2_tgpx4_host *host, uint32_t entry, uint32_t address,
                         uint32_t value, uint32_t *result)
{
    const bool fifo_port = address - 0x884000u < 0x4000u;
    switch (entry) {
    case 0x4c58d0:
        write_shared(host, address, value);
        return true;
    case 0x4c5990:
        /* The native low-12-bit mask makes its 0x804000 comparison unreachable. */
        return true;
    case 0x4c59e0:
        if (address == 0x801008u)
            *result = host->shared_read;
        else if (address == 0x802008u)
            *result = host->shared_write;
        else
            *result = address == 0x803008u ? host->reg_803008 : 0;
        return true;
    case 0x4c5a70:
        if (address - 0x400000u < 0x400000u)
            store(host->shared + (address - 0x400000u) * 4u, value, 4);
        return true;
    case 0x4c5a90:
        /* The original shared read window includes a 16 MiB bias that the
         * write window lacks. Preserve both offsets from the same base. */
        if (address < 0x400000u)
            *result = 0;
        else if (address < 0x800000u)
            *result = load_word(host->shared + address * 4u);
        else
            *result = load_word(host->external + (address - 0x800000u) * 4u);
        return true;
    case 0x4c5c70:
        host->decode_uploaded_program(host->opaque, host->upload_offset);
        return true;
    case 0x4c5a30:
        /* Model 2C writes one low halfword, with no SHARC fall-through. */
        if (host->upload_control & 0x80000000u)
            upload(host, value, 2);
        return true;
    case 0x4c5ac0:
        if (address - 0x880000u < 0x4000u && !(address & 15u))
            push(host, value | ((address & 0xff0u) << 19));
        else if (host->upload_control & 0x80000000u)
            upload(host, value, 4);
        else if (host->upload_offset && fifo_port)
            push(host, value);
        return true;
    case 0x4c5b70:
        *result = fifo_port ? pop(host) : 0;
        return true;
    case 0x4c5bc0:
        *result = fifo_port ? pop(host) & 0xffffu : 0xffffu;
        return true;
    case 0x4c5c10:
        *result = fifo_port ? pop(host) & 0xffu : 0xffu;
        return true;
    default:
        return false;
    }
}
