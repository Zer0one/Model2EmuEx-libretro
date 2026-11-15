/* Host policy, separate from recovered CPU arithmetic and serialized state. */
#ifndef M2_A68K_DIVS_ERROR_POLICY_H
#define M2_A68K_DIVS_ERROR_POLICY_H
#include "a68k.h"

typedef enum {
    A68K_DIVS_STOP_CONTENT = 0, /* Default: caller reports fault and stops content. */
    A68K_DIVS_ORIGINAL = 1     /* Propagate a host arithmetic error. */
} a68k_divs_error_policy;

/* Selector contract in A68K-enabled builds.
 * Key: model2emuex_a68k_divs_error_handling
 * Label: A68K DIVS Error Handling
 * stop_content: Stop Content (Default)
 * original: Original
 * Help: Stop Content reports the original DIVS host overflow and stops the
 * content. Original propagates the arithmetic error to the host process and
 * can terminate the frontend. Neither mode changes the guest result or flags.
 * Lifecycle: read on content load; A68K only. Not a guest overflow correction.
 */
a68k_divs_error_policy a68k_divs_error_policy_parse(const char *value);
/* Call at the sound/frontend boundary after a CPU fault. Zero-initialized
 * policy is safe. Returning a fault requires the caller to stop content.
 * Original mode raises Windows STATUS_INTEGER_OVERFLOW, observed in ElSemi
 * 1.1a on Windows 11 ARM64, or SIGFPE on POSIX. It does not deliberately invoke
 * undefined signed C division. CPU state and the verified prefix stay intact.
 * Platform signal/exception delivery is not binary-identical to x86 IDIV.
 */
a68k_boundary a68k_apply_divs_error_policy(const a68k_cpu *cpu,
                                         a68k_divs_error_policy policy);
#endif
