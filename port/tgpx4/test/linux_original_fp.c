/* ROM-free Linux i386 oracle: execute unchanged original PE numerical bodies.
 * No Windows imports/application entry point, libc, or translated execution.
 * Build freestanding at 0x20000000; fixed PE pages use MAP_FIXED_NOREPLACE.
 * The enclosing runner MUST verify the pinned executable SHA-256 first.
 * argv[1]: original EXE. stdin: seven words; stdout: four words per vector. */
typedef unsigned int u32;
typedef unsigned char u8;
extern int syscall6(u32, u32, u32, u32, u32, u32, u32);
extern void original_fp(u32 *, u32 *);
static u32 word(const u8 *p) { return p[0] | (u32)p[1]<<8 | (u32)p[2]<<16 | (u32)p[3]<<24; }
static u32 half(const u8 *p) { return p[0] | (u32)p[1]<<8; }
static int io(u32 nr, u32 fd, void *data, u32 count) {
    return syscall6(nr, fd, (u32)data, count, 0, 0, 0);
}
static void copy(u8 *to, const u8 *from, u32 bytes) { while (bytes--) *to++ = *from++; }
static int failed(u32 address) { return address >= 0xfffff001u; }
static int allocate(u32 at, u32 bytes) {
    return (u32)syscall6(192, at, bytes, 7, 0x100022, -1u, 0) == at;
}
static int exact(u32 nr, u32 fd, void *data, u32 count) {
    u8 *p = data;
    u32 done = 0;
    while (done < count) {
        int n = io(nr, fd, p + done, count - done);
        if (!n && !done && nr == 3) return 0;
        if (n <= 0) return -1;
        done += (u32)n;
    }
    return 1;
}
int probe_main(u32 *stack) {
    if (stack[0] != 2) return 2;
    int fd = syscall6(5, stack[2], 0, 0, 0, 0, 0);
    if (fd < 0) return 3;
    int length = syscall6(19, (u32)fd, 0, 2, 0, 0, 0);
    if (length < 0x1000) return 4;
    u8 *exe = (u8 *)syscall6(192, 0, (u32)length, 1, 2, (u32)fd, 0);
    if (failed((u32)exe)) return 5;
    u32 pe = word(exe + 0x3c);
    if (pe > (u32)length - 256 || word(exe + pe) != 0x4550 || half(exe + pe + 4) != 0x14c) return 6;
    u32 opt = pe + 24, sections = half(exe + pe + 6), table = opt + half(exe + pe + 20);
    if (word(exe + opt + 28) != 0x400000 || sections > 64 || table + sections * 40 > (u32)length) return 7;
    const u32 pages[] = {0x4b0000, 0x500000, 0x510000};
    for (u32 i = 0; i < 3; ++i) {
        u32 page = pages[i];
        if (!allocate(page, 0x10000)) return 8;
        for (u32 n = 0; n < sections; ++n) {
            const u8 *s = exe + table + n * 40;
            u32 va = 0x400000 + word(s + 12), size = word(s + 16), offset = word(s + 20);
            if (size > (u32)length || offset > (u32)length - size) return 9;
            u32 begin = page > va ? page : va, end = page + 0x10000 < va + size ? page + 0x10000 : va + size;
            if (end > begin) copy((u8 *)begin, exe + offset + begin - va, end - begin);
        }
    }
    if (!allocate(0x1040000, 0x10000) || !allocate(0x10f0000, 0x10000) || !allocate(0x30000000, 0x2000)) return 10;
    *(u32 *)0x10481f4 = 0x30000200;
    *(u32 *)0x104824c = 0x30000000;
    *(u32 *)0x30000000 = *(u32 *)0x30000014 = 0x30001240;
    *(u32 *)0x30000004 = *(u32 *)0x30000018 = 0x30001250;
    const u8 first[] = {0xa1,0,0x12,0,0x30,0xc3}, second[] = {0xa1,4,0x12,0,0x30,0xc3};
    copy((u8 *)0x30001240, first, 6); copy((u8 *)0x30001250, second, 6);
    *(u32 *)0x30001300 = 0x1f80;
    u32 *input = (u32 *)0x30001600, *output = (u32 *)0x30001680;
    const u32 entries[] = {0x4b4e60,0x4b53b0,0x4b5630,0x4b56a0,0x4b5740,0x4b57b0,
        0x4b5850,0x4b54b0,0x4b5460,0x4b6630,0x4b65c0,0x4b5510,0x4b6530,0x4b64a0,
        0x4b3fb0,0x4b3fc0,0x4b3fd0,0x4b3fe0,0x4b3ff0,0x4b4000,0x4b4010,0x4b4020};
    for (;;) {
        int got = exact(3, 0, input, 28);
        if (!got) return 0;
        if (got < 0) return 11;
        u32 found = 0;
        for (u32 i = 0; i < sizeof entries / sizeof entries[0]; ++i) found |= entries[i] == input[0];
        if (!found || (input[4] & 0x33f) != 0x3f || (input[5] & ~0x473fu)) return 12;
        input[7] = input[4]; input[8] = input[5]; input[9] = 0xffff;
        original_fp(input, output);
        if (exact(4, 1, output, 16) != 1) return 13;
    }
}
