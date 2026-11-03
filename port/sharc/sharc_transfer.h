#ifndef M2_SHARC_TRANSFER_H
#define M2_SHARC_TRANSFER_H
#include "sharc_memory.h"
/* Ten native register/address/transfer primitives. No condition or compute
 * helper is involved. Record metadata stays stable across bus callbacks;
 * pointed-to registers may alias each other or status. */
bool m2_sharc_transfer(uint32_t handler,const m2_sharc_memory_record *r,
                       const m2_sharc_memory_bus *bus,uint32_t *status);
#endif
