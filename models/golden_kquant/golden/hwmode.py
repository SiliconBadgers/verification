"""The matrix unit as built (SiliconBadgers/rtl adam/systolic-array, 3be9a15): its arithmetic
contract, bit-exact, plus the software step that turns real tensors into its operands.

Contract (docs/compute/matrix_unit_io_scheme.md, "Arithmetic"):
- Block-scaled: for each K block g of BLOCK_K elements,
    isum = sum(A[i][k] * B[k][j])                            exact integer
    contribution = round_half_even(isum * sA[i][g] * sB[g][j] * 2^24)
    acc += contribution                                      48-bit Q23.24, saturating
  with bf16 scales: exponent 0 counts as zero; exponent 255 makes the element NaN; a
  contribution or sum outside 48 bits saturates acc and makes C +-infinity (acc's sign).
  C = acc / 2^24 rounded to nearest even binary32, or NaN 0x7FC00000, +-inf, +0.
- Unscaled: C = sum(A * B) wrapped to AccW bits, sign-extended to int32.

The PE computes the contribution as +-(isum * ma * mb) shifted by ea + eb - 244 with
round-half-even (bpu_sa_pe.sv stages 1-3); for in-range inputs that is exactly the
rounding below, which works on the exact rational value.

Requantization (an ASSUMPTION, not a team decision): each block of 16 values along K gets
the bf16 scale RNE(max|x| / q) with q = 7 (INT4) or 127 (INT8), and codes
round_half_even(x / scale) clamped to [-q, q]; an all-zero block gets scale 0.
"""

from fractions import Fraction

from .fp import div, f32, f32_bits

BLOCK_K = 16
FX_W = 48
FX_FRAC = 24
FX_MAX = (1 << (FX_W - 1)) - 1
FX_MIN = -(1 << (FX_W - 1))
SHIFT_BIAS = 2 * (127 + 7) - FX_FRAC  # 244, bpu_sa_pkg::SCALE_SHIFT_BIAS
F32_NAN = 0x7FC00000


# --- bf16 --------------------------------------------------------------------------------


def f32_to_bf16(x):
    """binary32 -> bf16 bits, round to nearest even (NaN stays a quiet NaN)."""
    b = f32_bits(x)
    if (b & 0x7F800000) == 0x7F800000 and (b & 0x7FFFFF):
        return (b >> 16) | 0x0040
    b += 0x7FFF + ((b >> 16) & 1)
    return (b >> 16) & 0xFFFF


def bf16_value(h):
    """bf16 bits -> exact value as a Fraction (None for inf/NaN); exponent 0 counts as 0."""
    e, m = (h >> 7) & 0xFF, h & 0x7F
    if e == 0xFF:
        return None
    if e == 0:
        return Fraction(0)
    v = Fraction(128 + m) * Fraction(2) ** (e - 127 - 7)
    return -v if h & 0x8000 else v


def round_half_even(q):
    """Fraction -> nearest integer, ties to even."""
    fl = q.numerator // q.denominator
    rem = q - fl
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl % 2):
        fl += 1
    return fl


# --- requantization (software side, assumption) ---------------------------------------


def requantize(values, bits):
    """Values (binary32, a multiple of BLOCK_K long) -> (codes, bf16 scales per block)."""
    q = 7 if bits == 4 else 127
    codes, scales = [], []
    for g in range(0, len(values), BLOCK_K):
        block = values[g : g + BLOCK_K]
        amax = max(abs(v) for v in block)
        s = f32_to_bf16(div(amax, float(q))) if amax else 0
        sv = bf16_value(s)
        if not sv:
            scales.append(s)
            codes.extend([0] * len(block))
            continue
        scales.append(s)
        codes.extend(max(-q, min(q, round_half_even(Fraction(v) / sv))) for v in block)
    return codes, scales


# --- the contract -------------------------------------------------------------------------


def _parts(h):
    return h >> 15, (h >> 7) & 0xFF, 128 | (h & 0x7F)


def contribution(isum, sa, sb):
    """One block's contribution as the PE computes it: (value, overflowed, bad scale)."""
    sa_s, ea, ma = _parts(sa)
    sb_s, eb, mb = _parts(sb)
    if ea == 0xFF or eb == 0xFF:
        return 0, False, True
    if ea == 0 or eb == 0:
        return 0, False, False
    prod = isum * ma * mb
    if sa_s ^ sb_s:
        prod = -prod
    sh = ea + eb - SHIFT_BIAS
    if sh >= 0:
        c = prod << sh
        if c > FX_MAX or c < FX_MIN:
            return (FX_MIN if prod < 0 else FX_MAX), True, False
        return c, False, False
    quot, rem = divmod(prod, 1 << -sh)  # floor; rem >= 0
    half = 1 << (-sh - 1)
    if rem > half or (rem == half and quot & 1):
        quot += 1
    return quot, False, False


def scaled_element(a_codes, b_codes, sa, sb):
    """One C element of a block-scaled command: a_codes / b_codes are the K codes of A's
    row and B's column, sa / sb their per-block bf16 scales. Returns binary32 bits."""
    acc, ovf, nan = 0, False, False
    for g in range(len(sa)):
        lo = g * BLOCK_K
        isum = sum(a * b for a, b in zip(a_codes[lo : lo + BLOCK_K], b_codes[lo : lo + BLOCK_K]))
        c, c_ovf, bad = contribution(isum, sa[g], sb[g])
        nan = nan or bad
        if c_ovf:
            acc, ovf = c, True
            continue
        total = acc + c
        if total > FX_MAX or total < FX_MIN:
            acc, ovf = (FX_MAX if total > 0 else FX_MIN), True
        else:
            acc = total
    if nan:
        return F32_NAN
    if ovf:
        return 0xFF800000 if acc < 0 else 0x7F800000
    if acc == 0:
        return 0
    return f32_bits(f32(acc / (1 << FX_FRAC)))  # |acc| < 2^48: exact in double, one rounding


def unscaled_element(a_codes, b_codes, acc_w=32):
    """One C element of an unscaled command: the integer sum wrapped to acc_w bits, as int32
    bits (the wrapper sign-extends the AccW-bit row to 32)."""
    v = sum(a * b for a, b in zip(a_codes, b_codes)) & ((1 << acc_w) - 1)
    if v >> (acc_w - 1):
        v -= 1 << acc_w
    return v & 0xFFFFFFFF


def scaled_value(bits):
    """binary32 bits -> float, for the accuracy study."""
    import struct

    return struct.unpack("<f", struct.pack("<I", bits))[0]
