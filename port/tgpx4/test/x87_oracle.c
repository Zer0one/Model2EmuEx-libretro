/* Independent transcription of the M2C x87 numerical sequences. Build for
 * x86_64 and execute under Rosetta. This supplements original 32-bit execution
 * in Unicorn, whose exception/SNaN behavior is incomplete. Not physical x86.
 * Protocol: seven uint32 inputs -> six uint32 outputs, little endian. */
#include <stdint.h>
#include <stdio.h>

int main(void)
{
    uint32_t in[7], out[6];
    while (fread(in, sizeof(in), 1, stdin) == 1) {
        uint32_t env[7] = {in[4], in[5], 0xffff, 0, 0, 0, 0};
        uint32_t a = in[1], b = in[2], status = in[3], result = 0;
        uint16_t sw, cw, neg = 0, eq = 0, captured = 0;
        uint32_t unflushed = 0;
        __asm__ volatile("fninit; fldenv %0" :: "m"(env) : "st", "memory");
        switch (in[0]) {
        case 0x4b3fb0: case 0x4b3fc0: case 0x4b3fd0: case 0x4b3fe0:
        case 0x4b3ff0: case 0x4b4000: case 0x4b4010: case 0x4b4020: {
            static const uint32_t constants[] = {0x40a00000, 0x40400000, 0x40000000, 0x3fc00000,
                0x3f800000, 0x3f000000, 0, 0xbf800000};
            uint32_t value = constants[(in[0] - 0x4b3fb0) / 16];
            __asm__ volatile("flds %1; fstps %0" : "=m"(result) : "m"(value) : "st", "memory");
            break;
        }
        case 0x4b54b0:
            __asm__ volatile("fildl %1; fldz; fcom %%st(1); fnstsw %0"
                : "=m"(neg) : "m"(a) : "st", "memory");
            goto compare_and_store;
        case 0x4b5460:
            __asm__ volatile("flds %0" :: "m"(a) : "st", "memory");
            if (in[6]) {
                double spill;
                __asm__ volatile("fstpl %1; cvttsd2si %1, %0" : "=r"(result), "=m"(spill) :: "st", "memory");
            } else {
                uint64_t integer;
                uint32_t saved, residue;
                __asm__ volatile("fld %%st(0); fsts %1; fistpll %0; fildll %0"
                    : "=m"(integer), "=m"(saved) :: "st", "memory");
                if ((uint32_t)integer || ((integer >> 32) & 0x7fffffff)) {
                    __asm__ volatile(".byte 0xde,0xe9; fstps %0" : "=m"(residue) :: "st", "memory");
                    uint32_t bits = residue ^ (saved & 0x80000000);
                    unsigned carry = (uint64_t)bits + 0x7fffffff > 0xffffffffu;
                    integer = saved >> 31 ? integer + carry : integer - carry;
                } else {
                    __asm__ volatile("fstps %0; fstps %0" : "=m"(residue) :: "st", "memory");
                }
                result = (uint32_t)integer;
            }
            status = (status & ~0x18u) | (result >> 31 ? 0x10 : 0) | (!result ? 8 : 0);
            break;
        case 0x4b64a0: {
            const uint32_t scale = 0x40549a78;
            __asm__ volatile("fldz; flds %1; fcom %%st(1); fnstsw %0"
                : "=m"(eq) : "m"(a) : "st", "memory");
            status &= ~0x200u;
            if ((eq & 0x4100) == 0x100 || (eq & 0x4100) == 0x4000) status |= 0x200;
            __asm__ volatile("fldln2; fxch %%st(1); fyl2x; fmuls %1; fcom %%st(1); fnstsw %0"
                : "=m"(neg) : "m"(scale) : "st", "memory");
            status = (status & ~0x18u) | ((neg & 0x500) == 0x100 ? 0x10 : 0);
            __asm__ volatile("fld %%st(0); fucomp %%st(2); fnstsw %0; fstp %%st(1); fstps %1"
                : "=m"(eq), "=m"(result) :: "st", "memory");
            if ((eq & 0x4400) == 0x4000) status |= 8;
            break;
        }
        case 0x4b4e60:
            __asm__ volatile("fnclex; flds %2; fmuls %3; fnstsw %0; fstps %1"
                : "=m"(captured), "=m"(result) : "m"(a), "m"(b) : "st", "memory");
            unflushed = result;
            status &= ~0x10000u;
            if (captured & 2) { status |= 0x10000; result = 0; }
            if (captured & 8) status |= 0x40000;
            if (captured & 16) status |= 0x20000;
            __asm__ volatile("fldz; fcoms %2; fnstsw %0; flds %2; fucompp; fnstsw %1; flds %2; fstps %2"
                : "=m"(neg), "=m"(eq), "+m"(result) :: "st", "memory");
            status = (status & ~0x180000u) | (!(neg & 0x4100) ? 0x100000u : 0)
                | ((eq & 0x4400) == 0x4000 ? 0x80000u : 0);
            break;
        case 0x4b53b0: {
            int64_t integer;
            uint16_t old, trunc;
            __asm__ volatile("flds %1; fnstcw %0" : "=m"(old) : "m"(a) : "st", "memory");
            trunc = old | 0xc00;
            __asm__ volatile("fld %%st(0); fldcw %2; fistpll %0; fldcw %3; fldz; fcompp; fnstsw %1"
                : "=m"(integer), "=m"(neg) : "m"(trunc), "m"(old) : "st", "memory");
            result = (uint32_t)integer;
            status &= ~2u;
            if (!(neg & 0x4100)) { status |= 2; result = 0; }
            status = (status & ~0xcu) | (!result ? 8 : 0) | (result > 255 ? 4 : 0);
            if (result > 255) result = 255;
            break;
        }
        case 0x4b5630: case 0x4b56a0: case 0x4b5740: case 0x4b57b0: case 0x4b5850:
            if (in[0] == 0x4b57b0 || in[0] == 0x4b5850)
                __asm__ volatile("flds %0; fadds %1" :: "m"(b), "m"(a) : "st", "memory");
            else
                __asm__ volatile("flds %0; fsubs %1" :: "m"(b), "m"(a) : "st", "memory");
            __asm__ volatile("fldz; fcom %%st(1); fnstsw %0" : "=m"(neg) :: "st", "memory");
            if (in[0] == 0x4b56a0 || in[0] == 0x4b57b0) {
                status &= ~0x100u;
                if (!(neg & 0x4100)) {
                    status |= 0x100;
                    __asm__ volatile("fstp %%st(1); fld %%st(0); fxch %%st(1)" ::: "st", "memory");
                }
                __asm__ volatile("fcom %%st(1); fnstsw %0" : "=m"(neg) :: "st", "memory");
            }
            goto compare_and_store;
        case 0x4b6630:
            __asm__ volatile("flds %1; fabs; fldz; fcom %%st(1); fnstsw %0"
                : "=m"(neg) : "m"(a) : "st", "memory");
            goto compare_and_store;
        case 0x4b65c0:
            __asm__ volatile("flds %1; fabs; flds %2; fabs; .byte 0xde,0xe9; fldz; fcom %%st(1); fnstsw %0"
                : "=m"(neg) : "m"(b), "m"(a) : "st", "memory");
            goto compare_and_store;
        case 0x4b5510:
            __asm__ volatile("flds %1; fld %%st(0); fldz; fld %%st(0); fucomp %%st(2); fnstsw %0; fstp %%st(1)"
                : "=m"(eq) : "m"(a) : "st", "memory");
            status = (status & ~0x800u) | ((eq & 0x4400) == 0x4000 ? 0x800 : 0);
            __asm__ volatile("fld1; .byte 0xde,0xf2; fcom %%st(1); fnstsw %0"
                : "=m"(neg) :: "st", "memory");
            goto compare_and_store;
        case 0x4b6530:
            __asm__ volatile("fldz; flds %1; fcom %%st(1); fnstsw %0"
                : "=m"(eq) : "m"(a) : "st", "memory");
            status &= ~0x400u;
            if ((eq & 0x4100) == 0x100 || (eq & 0x4100) == 0x4000) status |= 0x400;
            __asm__ volatile("fsqrt; fld1; .byte 0xde,0xf1; fcom %%st(1); fnstsw %0"
                : "=m"(neg) :: "st", "memory");
            /* Here ST0 is result and ST1 zero, unlike the other common path. */
            status = (status & ~0x18u) | ((neg & 0x500) == 0x100 ? 0x10 : 0);
            __asm__ volatile("fld %%st(0); fucomp %%st(2); fnstsw %0; fstp %%st(1); fstps %1"
                : "=m"(eq), "=m"(result) :: "st", "memory");
            if ((eq & 0x4400) == 0x4000) status |= 8;
            break;
        default: return 2;
        }
        goto done;
compare_and_store:
        status = (status & ~0x18u) | (!(neg & 0x4100) ? 0x10 : 0);
        if (in[0] == 0x4b5630 || in[0] == 0x4b65c0) {
            __asm__ volatile("fucompp; fnstsw %0" : "=m"(eq) :: "st", "memory");
            result = 0;
        } else {
            __asm__ volatile("fld %%st(1); fucompp; fnstsw %0; fstps %1"
                : "=m"(eq), "=m"(result) :: "st", "memory");
        }
        if ((eq & 0x4400) == 0x4000) status |= 8;
done:
        __asm__ volatile("fnstsw %0; fnstcw %1; fninit" : "=m"(sw), "=m"(cw) :: "st", "memory");
        out[0] = result; out[1] = status; out[2] = cw; out[3] = sw; out[4] = unflushed; out[5] = captured;
        if (fwrite(out, sizeof(out), 1, stdout) != 1) return 3;
    }
    return ferror(stdin) ? 4 : 0;
}
