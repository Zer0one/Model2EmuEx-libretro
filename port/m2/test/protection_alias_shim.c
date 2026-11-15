/* Private ROM-free oracle shim; never linked/exported by the core. */
#include "../m2board.h"
#include "../m2protection.h"
#include <string.h>
void protection_alias_case(unsigned selector,unsigned command,unsigned fps,
                           const uint8_t *initial,uint8_t *response,uint32_t *state) {
    static m2_board b;
    static const m2_game game={.hook=M2_HOOK_UNKNOWN,.hook_addr=0x4c8000};
    b.game=&game;b.type=1;b.prev_fps=fps;b.net_enabled=M2_NET_LOOPBACK;
    b.rom.option[1]=0;b.protection_index=19;b.protection_selector=selector;
    b.protection_fault=0;b.protection_fault_address=0;
    memcpy(b.protection_response,initial,256);
    m2_protection_access(&b,0x1d9000c,command,16,1);
    memcpy(response,b.protection_response,256);
    state[0]=b.protection_index;state[1]=b.protection_selector;
    state[2]=b.protection_fault;state[3]=b.protection_fault_address;
}
