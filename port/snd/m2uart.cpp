#include "m2uart.h"
#include "hw/i8251.h"
#include "core/archive.h"
#include <new>
struct m2_uart { sm2::hw::I8251 uart; };
extern "C" m2_uart *m2uart_create(unsigned clock,void (*ready)(void *,int,int),void (*tx)(void *,uint8_t),void *user) {
    auto *u=new(std::nothrow)m2_uart;if(!u)return nullptr;
    u->uart.set_ready_handler([=]{if(ready)ready(user,u->uart.txrdy(),u->uart.rxrdy());});
    u->uart.set_tx_handler([=](auto byte){if(tx)tx(user,byte);});
    u->uart.configure(clock,31250,10);u->uart.reset();return u;
}
extern "C" void m2uart_destroy(m2_uart *u) { delete u; }
extern "C" void m2uart_reset(m2_uart *u) { u->uart.reset(); }
extern "C" uint8_t m2uart_read(m2_uart *u,unsigned r) { return u->uart.read(r); }
extern "C" void m2uart_write(m2_uart *u,unsigned r,uint8_t v) { u->uart.write(r,v); }
extern "C" void m2uart_receive(m2_uart *u,uint8_t v) { u->uart.write_rxd(v); }
extern "C" void m2uart_run(m2_uart *u,unsigned c) { u->uart.run(c); }
extern "C" void m2uart_state_archive(m2_uart *u,m2_state *a) {
    auto candidate=u->uart;sm2::Archive ar(a);candidate.serialize(ar);
    if(a->mode==M2_STATE_LOAD && !a->failed)u->uart=std::move(candidate);
}
