/* Shared ElSemi protection exchanges; no hardware decryptor substitution. */
#ifndef M2_PROTECTION_H
#define M2_PROTECTION_H
#include <stdint.h>
struct m2_board;
int m2_protection_present(const struct m2_board *b);
uint32_t m2_protection_access(struct m2_board *b,uint32_t address,uint32_t value,unsigned bits,int writing);
void m2_protection_install(struct m2_board *b);
#endif
