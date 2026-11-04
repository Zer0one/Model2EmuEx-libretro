#include "tgpx4_driver.h"
/* The native CRT uses _stricmp/_strnicmp, not strcmp/strncmp. Game IDs
 * compare against ASCII literals; avoid inheriting the host's locale. */
static int name_diff(const char *name, const char *reference, unsigned limit)
{
    for (unsigned i = 0; !limit || i < limit; ++i) {
        unsigned a = (unsigned char)name[i], b = (unsigned char)reference[i];
        if (a >= 'A' && a <= 'Z') a += 'a' - 'A';
        if (a != b) return 1;
        if (!a) return 0;
    }
    return 0;
}

static void word(const m2_tgpx4_execution_bus *bus, uint32_t at, uint32_t value)
{
    bus->write(bus->opaque, at, value, 32);
}

void m2_tgpx4_driver_initialize(const m2_tgpx4_execution_bus *bus,
    void *opaque, m2_tgpx4_bootstrap prepare, const char *game, uint32_t registration_list)
{
    prepare(opaque, registration_list, 0x100);
    word(bus, 0xdcec58, 0);
    word(bus, 0x5aeb90, 0);
    word(bus, 0x10f0048, bus->read(bus->opaque, 0x5aa724, 32));
    word(bus, 0x10f0044, bus->read(bus->opaque, 0x5aa738, 32));
    word(bus, 0x10f0040, 1);
    word(bus, 0x10ee03c, 0x4c5a90);
    word(bus, 0x10ee038, 0x4c5a70);
    word(bus, 0x10ed974, 0);
    word(bus, 0x10ed95c, 1);
    /* The native discarded _strnicmp(game,"stcc",4) has no side effects.
     * Remaining tests use ASCII-insensitive exact names or prefixes. */
    if (name_diff(game, "hotd", 0) && name_diff(game, "overrev", 0) && name_diff(game, "skisuprg", 0)
        && name_diff(game, "dyn", 3) && name_diff(game, "waverunr", 0) && name_diff(game, "segawski", 0)) {
        word(bus, 0x5aeb90, 0x41000000); /* 8.0f, exact original constant. */
        word(bus, 0xdcec58, 0xc2180000); /* -38.0f */
    }
    if (!name_diff(game, "tops", 4)) {
        word(bus, 0x573384, 0x4bc040);
        word(bus, 0x5733ac, 0x4ba010);
        word(bus, 0x5733b0, 0x4b94a0);
        word(bus, 0x57342c, 0x4b9460);
        word(bus, 0x573454, 0x4b93e0);
        word(bus, 0x573458, 0x4b9900);
        bus->write(bus->opaque, 0x10ed95a, 1, 8);
        word(bus, 0x10ed95c, 1);
    }
    if (!name_diff(game, "dyn", 3) || !name_diff(game, "tops", 4))
        word(bus, 0x10ed974, 1);
    word(bus, 0x10ed978, 3);
    if (!name_diff(game, "hotd", 0))
        word(bus, 0x10ed974, 2);
}

bool m2_tgpx4_driver_primitive(uint32_t entry, const m2_tgpx4_execution_bus *bus,
    m2_tgpx4_execution_registers *r)
{
    switch (entry) {
    case 0x4c5850: case 0x4c5870: case 0x4c5890: case 0x4c58a0:
    case 0x4c58b0: case 0x4c58c0: case 0x4c59d0: case 0x4c5a60:
        return true;
    case 0x4c5860:
        word(bus, 0x573320, 1);
        return true;
    case 0x4c5880:
        r->eax = (r->eax & ~255u) | (r->edx & 255u);
        return true;
    case 0x4c5a10: case 0x4c5a20:
        r->eax = entry == 0x4c5a10 ? 0 : r->eax & ~255u;
        r->flags = (r->flags & ~0x8d5u) | 0x44u;
        return true;
    case 0x4c5c60:
        bus->call(bus->opaque, 0x4baa60, r);
        return true;
    default: return false;
    }
}
