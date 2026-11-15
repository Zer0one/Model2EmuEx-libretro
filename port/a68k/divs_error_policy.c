#include "divs_error_policy.h"
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <signal.h>
#endif

a68k_divs_error_policy a68k_divs_error_policy_parse(const char *value)
{
    return value && !strcmp(value, "original") ? A68K_DIVS_ORIGINAL : A68K_DIVS_STOP_CONTENT;
}

a68k_boundary a68k_apply_divs_error_policy(const a68k_cpu *cpu,
                                         a68k_divs_error_policy policy)
{
    a68k_boundary fault = cpu->fault.boundary;
    if (fault != A68K_DIVS_HOST_OVERFLOW || policy != A68K_DIVS_ORIGINAL)
        return fault;
#ifdef _WIN32
    /* Native Windows process probe: first/second chance and process exit
     * all carry C0000095. Original CRT/main-loop handlers do not recover it.
     * Keep host delivery outside the CPU; do not synthesize guest V or a
     * quotient. An external debugger may intercept this deliberate mode. */
    RaiseException(EXCEPTION_INT_OVERFLOW, 0, 0, NULL);
#else
    raise(SIGFPE);
#endif
    /* If an external handler returns, never resume an unrecovered CPU or
     * silently turn Original into Stop Content. No global handlers changed. */
    abort();
}
