/* Owned Windows child only. Suppress this child's WER dialog, not global WER. */
#include "../divs_error_policy.h"
#include <assert.h>
#include <string.h>
#include <windows.h>

int main(int argc, char **argv)
{
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    a68k_cpu cpu = {0};
    cpu.fault.boundary = A68K_DIVS_HOST_OVERFLOW;
    cpu.r.d[1] = 0x80000000u; cpu.flags = 0xffffffffu;
    a68k_cpu saved = cpu;
    a68k_boundary result = a68k_apply_divs_error_policy(&cpu,
        a68k_divs_error_policy_parse(argc > 1 ? argv[1] : NULL));
    assert(result == A68K_DIVS_HOST_OVERFLOW);
    assert(!memcmp(&cpu, &saved, sizeof cpu));
    return 0;
}
