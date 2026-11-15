/* OpenGL functions loaded at run time; see m2glapi.h. */
#include "m2glapi.h"

#include <string.h>

#define M2GL_DEFINE(ret, name, args) ret (M2GL_APIENTRY *m2_##name) args;
M2GL_FUNCTIONS(M2GL_DEFINE)
M2GL_MULTISAMPLE_FUNCTIONS(M2GL_DEFINE)
#undef M2GL_DEFINE

int m2glapi_load(void *(*getproc)(const char *name), const char **missing)
{
    void *p;
#define M2GL_LOAD(ret, name, args)                                  \
    p = getproc(#name);                                             \
    if (!p) { if (missing) *missing = #name; return 0; }            \
    memcpy(&m2_##name, &p, sizeof p);   /* object -> function pointer */
    M2GL_FUNCTIONS(M2GL_LOAD)
#undef M2GL_LOAD
#define M2GL_OPTIONAL(ret, name, args) \
    p = getproc(#name); \
    if (!p) p = getproc(#name "EXT"); \
    if (!p) p = getproc(#name "ANGLE"); \
    memcpy(&m2_##name, &p, sizeof p);
    M2GL_MULTISAMPLE_FUNCTIONS(M2GL_OPTIONAL)
#undef M2GL_OPTIONAL
    return 1;
}
