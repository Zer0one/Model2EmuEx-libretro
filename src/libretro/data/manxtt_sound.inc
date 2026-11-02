/* Sound-only metadata from the pinned MAME catalogue; raw native word layout.
 * Zero-filled region sizes match current SM2 games.xml, including empty sockets. */
static const m2_rom_entry twin_roms[] = {
    {0,nullptr,5,0x80000,0,0,0},
    {1,"epr-18826.30",0,0x0,0x40000,0xed9fe4c1,1},
    {0,nullptr,6,0x800000,0,0,0},
    {1,"mpr-18827.31",0,0x0,0x200000,0x58d78ca1,1},
    {1,"mpr-18764.32",0,0x200000,0x200000,0x0dc6a860,1},
    {1,"mpr-18765.36",0,0x400000,0x200000,0xca4a803c,1},
    {1,"mpr-18766.37",0,0x600000,0x200000,0xe41892ea,1},
    {-1,nullptr,0,0,0,0,0}
};
static const m2_rom_entry deluxe_roms[] = {
    {0,nullptr,5,0x80000,0,0,0},
    {1,"epr-18924a.30",0,0x0,0x40000,0xad6f40ec,1},
    {0,nullptr,6,0x800000,0,0,0},
    {1,"mpr-18763.31",0,0x0,0x200000,0x1bcb2283,1},
    {1,"mpr-18764.32",0,0x200000,0x200000,0x0dc6a860,1},
    {1,"mpr-18765.36",0,0x400000,0x200000,0xca4a803c,1},
    {1,"mpr-18766.37",0,0x600000,0x200000,0xe41892ea,1},
    {-1,nullptr,0,0,0,0,0}
};
static const m2_rom_entry auxiliary_roms[] = {
    {0,nullptr,5,0xc0000,0,0,0},
    {1,"epr-18742.7",0,0x0,0x20000,0x1b78da74,1},
    {0,nullptr,6,0x400000,0,0,0},
    {1,"mpr-18743.32",0,0x0,0x200000,0x17e84e15,1},
    {-1,nullptr,0,0,0,0,0}
};
