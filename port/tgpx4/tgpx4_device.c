#include "tgpx4_device.h"

enum { STATE = 0x10edef0, BASE = 0x10481f0, ACTIVE = 0x10481f4, RECORD = 0x104824c };

static uint32_t read(void *opaque, uint32_t address, unsigned bits)
{
    m2_tgpx4_device *d = opaque;
    return d->machine.read(d->machine.opaque, address, bits);
}

static void write(void *opaque, uint32_t address, uint32_t value, unsigned bits)
{
    m2_tgpx4_device *d = opaque;
    d->machine.write(d->machine.opaque, address, value, bits);
}

static void call(void *opaque, uint32_t entry, m2_tgpx4_execution_registers *r)
{
    m2_tgpx4_device *d = opaque;
    if (!m2_tgpx4_dispatch(entry, &d->bus, r)
        && !m2_tgpx4_execute_board_memory(entry, &d->bus, r)
        && !m2_tgpx4_driver_primitive(entry, &d->bus, r))
        d->machine.call(d->machine.opaque, entry, r);
}

void m2_tgpx4_device_bind(m2_tgpx4_device *d)
{
    d->bus = (m2_tgpx4_execution_bus){ d, read, write, call };
}

void m2_tgpx4_device_load(m2_tgpx4_device *d, const uint8_t *source, uint32_t bytes)
{
    /* The bus is authoritative: an earlier run or restored archive can have
     * changed the CPU state and allocation binding since the previous upload. */
    for (unsigned i = 0; i < sizeof d->program.state; ++i)
        d->program.state[i] = (uint8_t)read(d, STATE + i, 8);
    m2_tgpx4_load_program(&d->program, source, bytes, STATE, &d->memory, d->registration);
    for (unsigned i = 0; i < sizeof d->program.state; ++i)
        write(d, STATE + i, d->program.state[i], 8);
    write(d, BASE, d->program.active_base, 32);
    write(d, ACTIVE, d->program.active_state, 32);
    write(d, RECORD, d->program.active_record, 32);
}

static void bootstrap(void *opaque, uint32_t registration_list, uint32_t bytes)
{
    m2_tgpx4_device *d = opaque;
    /* Driver 004c5c80 requests exactly 0x100 bytes from its native bootstrap
     * token. This is a transient CPU-program snapshot, never a ROM copy. */
    (void)registration_list; /* Already represented by d->registration. */
    const uint32_t source = read(d, 0x5aa87c, 32);
    uint8_t code[0x100];
    for (unsigned i = 0; i < sizeof code; ++i)
        code[i] = (uint8_t)read(d, source + i, 8);
    m2_tgpx4_device_load(d, code, bytes);
}

void m2_tgpx4_device_initialize(m2_tgpx4_device *d, const char *native_game)
{
    m2_tgpx4_driver_initialize(&d->bus, d, bootstrap, native_game,
                               d->registration ? d->registration->list : 0);
}

void m2_tgpx4_device_run(m2_tgpx4_device *d, uint32_t entry_stack, bool single_batch)
{
    d->registers.esp = entry_stack;
    if (single_batch)
        m2_tgpx4_execute_batch(&d->bus, &d->registers);
    else
        m2_tgpx4_execute(&d->bus, &d->registers);
}
