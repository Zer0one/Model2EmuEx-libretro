#include "tgpx4_fp.h"
#include "../x87/x87_binary32.h"

static number load_value(uint32_t bits, uint16_t *sw)
{
    if (issnan32(bits)) *sw |= 1;
    if ((bits & 0x7fffffffu) && !(bits & 0x7f800000u)) *sw |= 2;
    return unpack(bits);
}

static bool negative(number n)
{
    return n.kind != NAN_VALUE && n.sign && (n.kind != FINITE || n.sig);
}

static bool zero(number n)
{
    return n.kind == FINITE && !n.sig;
}

static void nz(number n, uint32_t *status, unsigned shift, uint16_t *sw)
{
    /* FCOM zero,value is ordered and raises invalid for QNaN too. FUCOMPP
     * later compares value,zero; NaN is neither native N nor native Z. */
    if (n.kind == NAN_VALUE) *sw |= 1;
    *status = (*status & ~(0x18u << shift)) | (negative(n) ? 0x10u << shift : 0)
        | (zero(n) ? 8u << shift : 0);
    *sw = (uint16_t)((*sw & ~0x4700u) | (n.kind == NAN_VALUE ? 0x4500 :
        zero(n) ? 0x4000 : negative(n) ? 0x100 : 0));
}

static uint32_t truncate64_low(number n, uint16_t *sw)
{
    if (n.kind != FINITE || n.exponent > 63 ||
        (n.exponent == 63 && (!n.sign || n.sig != 0x800000u))) {
        *sw |= 1;
        return 0; /* FISTP qword indefinite is 0x8000000000000000. */
    }
    if (!n.sig) return 0;
    uint64_t value;
    if (n.exponent >= 23) value = (uint64_t)n.sig << (n.exponent - 23);
    else {
        unsigned shift = (unsigned)(23 - n.exponent);
        value = shift >= 32 ? 0 : n.sig >> shift;
        if (shift >= 32 || (n.sig & ((1u << shift) - 1u))) *sw |= 0x20;
    }
    return n.sign ? 0u - (uint32_t)value : (uint32_t)value;
}

/* Integer fixed-point evaluation for the native FLDLN2/FYL2X/FMUL sequence.
 * Q96 keeps a guard interval well beyond the final 24-bit precision. The
 * transcendental's extended rounding is applied before the native multiply.
 * Qualification against original x87 sequences is tracked separately; do not
 * replace this sequence with host logf or reinterpret its scale constant. */
typedef __uint128_t qwide;
static qwide q96_multiply(qwide a, qwide b)
{
    qwide lo = (qwide)(uint64_t)a * (uint64_t)b;
    qwide cross_a = (qwide)(uint64_t)a * (uint64_t)(b >> 64);
    qwide cross_b = (qwide)(uint64_t)(a >> 64) * (uint64_t)b;
    qwide mid = (lo >> 64) + (uint64_t)cross_a + (uint64_t)cross_b;
    qwide high = (a >> 64) * (b >> 64) + (cross_a >> 64) + (cross_b >> 64) + (mid >> 64);
    return (high << 32) | ((uint64_t)mid >> 32);
}

static qwide q96_fraction(qwide numerator, qwide denominator)
{
    qwide quotient = 0;
    for (unsigned i = 0; i < 96; ++i) {
        numerator <<= 1;
        quotient <<= 1;
        if (numerator >= denominator) { numerator -= denominator; quotient |= 1; }
    }
    return quotient;
}

static bool q96_increment(unsigned mode, unsigned sign, qwide q, qwide residue, unsigned shift)
{
    if (!residue) return false;
    if (mode == 1) return sign != 0;
    if (mode == 2) return sign == 0;
    if (mode == 3) return false;
    qwide half = (qwide)1 << (shift - 1);
    return residue > half || (residue == half && (q & 1));
}

static uint32_t logarithm(number n, unsigned mode)
{
    const qwide ln2 = ((qwide)UINT64_C(0xb17217f7d1cf79ab) << 32) | 0xc9e3b398u;
    qwide ratio = ((qwide)(n.sig - 0x800000u) << 96) / (n.sig + 0x800000u);
    qwide squared = q96_multiply(ratio, ratio), term = ratio, sum = ratio;
    for (unsigned denominator = 3; term; denominator += 2) {
        term = q96_multiply(term, squared);
        sum += term / denominator;
    }
    qwide fractional_log2 = q96_fraction(sum * 2, ln2);
    bool sign = n.exponent < 0;
    qwide log2 = sign ? ((qwide)(-n.exponent) << 96) - fractional_log2
                     : ((qwide)n.exponent << 96) + fractional_log2;
    if (!log2) return 0;
    /* FLDLN2 rounds its 66-bit constant according to RC, independently of PC. */
    uint64_t constant = UINT64_C(0xb17217f7d1cf79ab) + (mode == 0 || mode == 2);
    qwide value = q96_multiply(log2, (qwide)constant << 32);
    unsigned top = 127;
    while (!(value & ((qwide)1 << top))) --top;
    unsigned shift = top - 63;
    qwide q = value >> shift, residue = value & (((qwide)1 << shift) - 1);
    if (q96_increment(mode, sign, q, residue, shift)) ++q;
    value = (q << shift) * 0xd49a78u; /* Original binary32 0x40549a78. */
    top = 127;
    while (!(value & ((qwide)1 << top))) --top;
    shift = top - 23;
    q = value >> shift;
    residue = value & (((qwide)1 << shift) - 1);
    if (q96_increment(mode, sign, q, residue, shift)) ++q;
    int exponent = (int)top - 118;
    if (q == 0x1000000u) { q >>= 1; ++exponent; }
    return ((uint32_t)sign << 31) | ((uint32_t)(exponent + 127) << 23) | ((uint32_t)q & 0x7fffffu);
}

bool m2_tgpx4_fp_operation_details(uint32_t entry, uint32_t first, uint32_t second,
    uint32_t *status, m2_tgpx4_fp_state *fp, uint32_t *result, uint32_t *scratch)
{
    if ((fp->control & 0x33fu) != 0x3fu) return false;
    unsigned mode = (fp->control >> 10) & 3;
    uint16_t sw = fp->status & ~0x200u;
    number n;
    switch (entry) {
    case 0x4b3fb0: case 0x4b3fc0: case 0x4b3fd0: case 0x4b3fe0:
    case 0x4b3ff0: case 0x4b4000: case 0x4b4010: case 0x4b4020: {
        static const uint32_t constants[8] = {0x40a00000, 0x40400000, 0x40000000, 0x3fc00000,
            0x3f800000, 0x3f000000, 0, 0xbf800000};
        *result = constants[(entry - 0x4b3fb0) / 16];
        break;
    }
    case 0x4b54b0: {
        const unsigned sign = first >> 31;
        uint32_t magnitude = sign ? 0u - first : first;
        *status = (*status & ~0x18u) | (sign ? 0x10 : 0) | (!first ? 8 : 0);
        sw = (uint16_t)((sw & ~0x4700u) | (!first ? 0x4000 : sign ? 0x100 : 0));
        if (!magnitude) { *result = 0; break; }
        unsigned exponent = 31;
        while (!(magnitude & (1u << exponent))) --exponent;
        uint32_t sig;
        if (exponent <= 23) sig = magnitude << (23 - exponent);
        else {
            unsigned shift = exponent - 23;
            uint32_t residue = magnitude & ((1u << shift) - 1u);
            sig = magnitude >> shift;
            if (residue) sw |= 0x20;
            if (increment(mode, sign, sig, residue, shift)) { ++sig; sw |= 0x200; }
            if (sig == 0x1000000u) { sig >>= 1; ++exponent; }
        }
        *result = (sign << 31) | ((exponent + 127) << 23) | (sig & 0x7fffffu);
        break;
    }
    case 0x4b64a0:
        n = load_value(first, &sw);
        *status &= ~0x200u;
        if (negative(n) || zero(n)) *status |= 0x200u;
        if (n.kind == NAN_VALUE) { sw |= 1; *result = n.nan; }
        else if (negative(n)) { sw |= 1; *result = 0xffc00000u; }
        else if (zero(n)) { sw |= 4; *result = 0xff800000u; }
        else if (n.kind == INFINITY_VALUE) *result = 0x7f800000u;
        else {
            *result = logarithm(n, mode);
            if (first != 0x3f800000u) sw |= 0x20;
        }
        nz(unpack(*result), status, 0, &sw);
        break;
    case 0x4b4e60: {
        sw &= ~0x80ffu; /* FNCLEX before FLD/FMUL. */
        n = binary(first, second, true, false, mode, &sw);
        const uint16_t captured = sw; /* FNSTSW precedes binary32 store. */
        uint32_t stored = store32(n, mode, &sw);
        *status &= ~0x10000u;
        if (captured & 2) { *status |= 0x10000u; stored = 0; }
        if (captured & 8) *status |= 0x40000u;
        if (captured & 16) *status |= 0x20000u;
        n = load_value(stored, &sw);
        nz(n, status, 16, &sw);
        *result = stored;
        sw &= ~0x200u; /* Final FLD/FSTP is an exact binary32 copy. */
        break;
    }
    case 0x4b5630: case 0x4b56a0: case 0x4b5740: case 0x4b57b0: case 0x4b5850:
        n = binary(second, first, false, entry != 0x4b57b0 && entry != 0x4b5850, mode, &sw);
        if (entry == 0x4b56a0 || entry == 0x4b57b0) {
            *status &= ~0x100u;
            if (negative(n)) { *status |= 0x100u; n = unpack(0); }
        }
        nz(n, status, 0, &sw);
        if (entry == 0x4b5630) {
            /* Final FUCOMPP here compares zero,result (opposite to the
             * storing variants). The guest N/Z check remains the same. */
            if (n.kind != NAN_VALUE && !zero(n))
                sw = (uint16_t)((sw & ~0x4700u) | (negative(n) ? 0 : 0x100));
            *result = 0;
        } else *result = store32(n, mode, &sw);
        break;
    case 0x4b6630:
        n = load_value(first, &sw);
        n.sign = 0; n.nan &= 0x7fffffffu;
        nz(n, status, 0, &sw);
        *result = store32(n, mode, &sw);
        break;
    case 0x4b65c0: {
        number a = load_value(first, &sw), b = load_value(second, &sw);
        /* Both FLDs quiet SNaNs before the register-register subtraction. */
        uint32_t x = a.kind == NAN_VALUE ? a.nan : first;
        uint32_t y = b.kind == NAN_VALUE ? b.nan : second;
        n = binary(y & 0x7fffffffu, x & 0x7fffffffu, false, true, mode, &sw);
        nz(n, status, 0, &sw);
        if (n.kind != NAN_VALUE && !zero(n))
            sw = (uint16_t)((sw & ~0x4700u) | (negative(n) ? 0 : 0x100));
        *result = 0;
        break;
    }
    case 0x4b5510: case 0x4b6530:
        n = load_value(first, &sw);
        if (entry == 0x4b5510) {
            *status &= ~0x800u;
            if (zero(n)) *status |= 0x800u;
        } else {
            if (n.kind == NAN_VALUE) sw |= 1; /* Initial ordered FCOM. */
            *status &= ~0x400u;
            if (zero(n) || negative(n)) *status |= 0x400u;
            n = square_root(n, mode, &sw);
        }
        n = reciprocal(n, mode, &sw);
        nz(n, status, 0, &sw);
        *result = store32(n, mode, &sw);
        break;
    case 0x4b53b0: case 0x4b5460: {
        n = load_value(first, &sw);
        uint32_t value = truncate64_low(n, &sw);
        if (entry == 0x4b53b0) {
            *status &= ~2u;
            if (negative(n)) { *status |= 2u; value = 0; }
            *status = (*status & ~0xcu) | (!value ? 8u : 0) | (value > 255u ? 4u : 0);
            *scratch = value;
            if (n.kind == NAN_VALUE) sw |= 1;
            sw = (uint16_t)((sw & ~0x4700u) | (n.kind == NAN_VALUE ? 0x4500 :
                zero(n) ? 0x4000 : negative(n) ? 0 : 0x100));
            *result = value > 255u ? 255u : value;
        } else {
            if (fp->crt_sse2) {
                /* FLD/FSTP double precedes CVTTSD2SI. SSE exception flags do
                 * not become x87 exceptions; only the earlier FLD contributes.
                 * The instruction's indefinite int32 differs from int64 low. */
                sw = fp->status & ~0x200u;
                (void)load_value(first, &sw);
                if (n.kind != FINITE || n.exponent > 31 ||
                    (n.exponent == 31 && (!n.sign || n.sig != 0x800000u)))
                    value = 0x80000000u;
            }
            *status = (*status & ~0x18u) | ((value & 0x80000000u) ? 0x10 : 0) | (!value ? 8 : 0);
            *result = value;
        }
        break;
    }
    default: return false;
    }
    fp->status = sw;
    return true;
}

bool m2_tgpx4_fp_operation(uint32_t entry, uint32_t first, uint32_t second,
    uint32_t *status, m2_tgpx4_fp_state *fp, uint32_t *result)
{
    uint32_t scratch = 0;
    return m2_tgpx4_fp_operation_details(entry, first, second, status, fp, result, &scratch);
}
