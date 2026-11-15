/* MAME-derived alternative extracted from scsp.c before native DSP
 * integration. BSD-3-Clause: ElSemi, R. Belmont; thanks to kingshriek.
 * Baseline file SHA-256: 6689809c6b8a3a6e8bda13b6be1c4917c79fc2fa084f148545aa272630215f10
 * Explicit user-selected backend only; never an automatic fallback. */
static int32_t sext(int32_t v,int bits) {return (int32_t)((uint32_t)v<<(32-bits))>>(32-bits);}
static uint16_t PACK(int32_t val)
{
    int sign = (val >> 23) & 1;
    uint32_t temp = (uint32_t)(val ^ (val << 1)) & 0xFFFFFF;
    int exponent = 0;
    for (int k = 0; k < 12; k++) {
        if (temp & 0x800000)
            break;
        temp <<= 1;
        exponent++;
    }
    if (exponent < 12)
        val = (val << exponent) & 0x3FFFFF;
    else
        val <<= 11;
    val >>= 11;
    val &= 0x7FF;
    val |= sign << 15;
    val |= exponent << 11;
    return (uint16_t)val;
}

static int32_t UNPACK(uint16_t val)
{
    int sign = (val >> 15) & 1;
    int exponent = (val >> 11) & 0xF;
    int mantissa = val & 0x7FF;
    int32_t uval = mantissa << 11;
    if (exponent > 11) {
        exponent = 11;
        uval |= sign << 22;
    } else {
        uval |= (sign ^ 1) << 22;
    }
    uval |= sign << 23;
    uval = sext(uval, 24);
    uval >>= exponent;
    return uval;
}

static void dsp_mame_step(scsp *s)
{
    dsp_t *d = &s->DSP.context;
    if (d->Stopped)
        return;
    memset(d->EFREG, 0, sizeof d->EFREG);
    int32_t ACC = 0, MEMVAL = 0, FRC_REG = 0, Y_REG = 0;
    uint32_t ADRS_REG = 0;

    for (int step = 0; step < d->LastStep; ++step) {
        const uint16_t *IPtr = d->MPRO + step * 4;
        uint32_t TRA = (IPtr[0] >> 8) & 0x7f, TWT = (IPtr[0] >> 7) & 1, TWA = IPtr[0] & 0x7f;
        uint32_t XSEL = (IPtr[1] >> 15) & 1, YSEL = (IPtr[1] >> 13) & 3, IRA = (IPtr[1] >> 6) & 0x3f;
        uint32_t IWT = (IPtr[1] >> 5) & 1, IWA = IPtr[1] & 0x1f;
        uint32_t TABLE = (IPtr[2] >> 15) & 1, MWT = (IPtr[2] >> 14) & 1, MRD = (IPtr[2] >> 13) & 1;
        uint32_t EWT = (IPtr[2] >> 12) & 1, EWA = (IPtr[2] >> 8) & 0xf, ADRL = (IPtr[2] >> 7) & 1;
        uint32_t FRCL = (IPtr[2] >> 6) & 1, SHIFTV = (IPtr[2] >> 4) & 3, YRL = (IPtr[2] >> 3) & 1;
        uint32_t NEGB = (IPtr[2] >> 2) & 1, ZERO = (IPtr[2] >> 1) & 1, BSEL = IPtr[2] & 1;
        uint32_t NOFL = (IPtr[3] >> 15) & 1, COEF = (IPtr[3] >> 9) & 0x3f, MASA = (IPtr[3] >> 2) & 0x1f;
        uint32_t ADREB = (IPtr[3] >> 1) & 1, NXADR = IPtr[3] & 1;

        int32_t INPUTS;
        if (IRA <= 0x1f)
            INPUTS = d->MEMS[IRA];
        else if (IRA <= 0x2f)
            INPUTS = d->MIXS[IRA - 0x20] << 4;
        else if (IRA <= 0x31)
            INPUTS = d->EXTS[IRA - 0x30] << 8;
        else
            return;
        INPUTS = sext(INPUTS, 24);
        if (IWT) {
            d->MEMS[IWA] = MEMVAL;
            if (IRA == IWA)
                INPUTS = MEMVAL;
        }

        int32_t B;
        if (!ZERO) {
            B = BSEL ? ACC : sext(d->TEMP[(TRA + d->DEC) & 0x7f], 24);
            if (NEGB)
                B = 0 - B;
        } else {
            B = 0;
        }
        int32_t X = XSEL ? INPUTS : sext(d->TEMP[(TRA + d->DEC) & 0x7f], 24);
        int32_t Y = 0;
        if (YSEL == 0) Y = FRC_REG;
        else if (YSEL == 1) Y = d->COEF[COEF] >> 3;
        else if (YSEL == 2) Y = (Y_REG >> 11) & 0x1fff;
        else Y = (Y_REG >> 4) & 0x0fff;
        if (YRL)
            Y_REG = INPUTS;

        int32_t SHIFTED;
        if (SHIFTV == 0) SHIFTED = clampi(ACC, -0x00800000, 0x007fffff);
        else if (SHIFTV == 1) SHIFTED = clampi(ACC * 2, -0x00800000, 0x007fffff);
        else if (SHIFTV == 2) SHIFTED = sext(ACC * 2, 24);
        else SHIFTED = sext(ACC, 24);

        Y = sext(Y, 13);
        int64_t v = ((int64_t)X * (int64_t)Y) >> 12;
        ACC = (int32_t)(v + B);

        if (TWT)
            d->TEMP[(TWA + d->DEC) & 0x7f] = SHIFTED;
        if (FRCL)
            FRC_REG = SHIFTV == 3 ? (SHIFTED & 0x0fff) : ((SHIFTED >> 11) & 0x1fff);

        if (MRD || MWT) {
            uint32_t ADDR = d->MADRS[MASA];
            if (!TABLE) ADDR += d->DEC;
            if (ADREB) ADDR += ADRS_REG & 0x0FFF;
            if (NXADR) ADDR++;
            if (!TABLE) ADDR &= d->RBL - 1;
            else ADDR &= 0xffff;
            ADDR += d->RBP << 12;
            ADDR <<= 1;
            if (MRD && (step & 1))
                MEMVAL = NOFL ? (int32_t)read_word(s, ADDR) << 8 : UNPACK(read_word(s, ADDR));
            if (MWT && (step & 1))
                write_word(s, ADDR, NOFL ? (uint16_t)(SHIFTED >> 8) : PACK(SHIFTED));
        }
        if (ADRL)
            ADRS_REG = SHIFTV == 3 ? (uint32_t)((SHIFTED >> 12) & 0xfff) : (uint32_t)(INPUTS >> 16);
        if (EWT)
            d->EFREG[EWA] = (int16_t)(d->EFREG[EWA] + (SHIFTED >> 8));
    }
    --d->DEC;
    memset(d->MIXS, 0, sizeof d->MIXS);
}

