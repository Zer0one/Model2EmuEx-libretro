// Frontend-neutral C boundary for SM2's unchanged I8251 implementation.
#pragma once
#include <stdint.h>
#include "../state.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct m2_uart m2_uart;
m2_uart *m2uart_create(unsigned clock,void (*ready)(void *,int,int),void (*tx)(void *,uint8_t),void *user);
void m2uart_destroy(m2_uart *u);
void m2uart_reset(m2_uart *u);
uint8_t m2uart_read(m2_uart *u,unsigned reg);
void m2uart_write(m2_uart *u,unsigned reg,uint8_t value);
void m2uart_receive(m2_uart *u,uint8_t value);
void m2uart_run(m2_uart *u,unsigned cycles);
void m2uart_state_archive(m2_uart *u,m2_state *a);
#ifdef __cplusplus
}
#endif
