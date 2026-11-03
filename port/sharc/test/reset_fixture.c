/* Test-only exception boundary, so longjmp never unwinds a Python callback. */
#include "../sharc_reset.h"
#include <setjmp.h>
#include <string.h>
static jmp_buf exception;
static int message_ok;
static void fatal(void *opaque,const char *message) {
    (void)opaque;message_ok=strcmp(message,"list<T> too long")==0;longjmp(exception,1);
}
int m2_sharc_test_reset(m2_sharc_reset_context *c,const uint8_t *source,
    uint32_t token,uint32_t bytes,uint32_t fixed,const m2_sharc_program_memory *memory,
    const m2_sharc_registration *registration)
{
    m2_sharc_registration copy;
    if(registration){copy=*registration;copy.fatal=fatal;registration=&copy;}
    message_ok=0;
    if(setjmp(exception))return message_ok?1:-1;
    m2_sharc_reset(c,source,token,bytes,fixed,memory,registration);return 0;
}
