/* POSIX subprocess qualification: never raise a fault in the test driver. */
#include "../divs_error_policy.h"
#include <assert.h>
#include <signal.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    a68k_cpu cpu = {0};
    assert(a68k_divs_error_policy_parse(NULL) == A68K_DIVS_STOP_CONTENT);
    assert(a68k_divs_error_policy_parse("stop_content") == A68K_DIVS_STOP_CONTENT);
    assert(a68k_divs_error_policy_parse("invalid") == A68K_DIVS_STOP_CONTENT);
    assert(a68k_divs_error_policy_parse("original") == A68K_DIVS_ORIGINAL);
    for (unsigned boundary = 0; boundary <= A68K_DIVS_HOST_OVERFLOW; ++boundary) {
        cpu.fault.boundary = (a68k_boundary)boundary;
        cpu.r.d[1] = 0x80000000u; cpu.flags = 0xffffffffu;
        a68k_cpu saved = cpu;
        assert(a68k_apply_divs_error_policy(&cpu, A68K_DIVS_STOP_CONTENT) == (a68k_boundary)boundary);
        assert(!memcmp(&cpu, &saved, sizeof cpu));
        if (boundary != A68K_DIVS_HOST_OVERFLOW)
            assert(a68k_apply_divs_error_policy(&cpu, A68K_DIVS_ORIGINAL) == (a68k_boundary)boundary);
    }
    pid_t child = fork(); assert(child >= 0);
    if (!child) {
        struct rlimit limit = {0, 0}; assert(!setrlimit(RLIMIT_CORE, &limit));
        signal(SIGFPE, SIG_DFL);
        a68k_apply_divs_error_policy(&cpu, A68K_DIVS_ORIGINAL);
        _exit(99);
    }
    int status; assert(waitpid(child, &status, 0) == child);
    assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGFPE);
    return 0;
}
