"""The matrix unit per the proposed specification (rtl PR #32, docs/compute/matrix_unit_spec.md),
bit-exact: retained native sums across chained commands, logical M/N masks, a zero-padded
final scale block, the five output encodings and the version-1 command record.

The per-block arithmetic is hwmode.py's (the arithmetic of rtl #31, which the spec keeps).
This module adds what the spec adds. Everything is exact integer or Fraction arithmetic; no
float rounding is borrowed from the host, so the float paths are independent of fp.py.

Two points the original spec left open, agreed with Zeb on 2026-11-08 and now in the BPU
copy of the spec:
- FP16 NaN is 0x7E00. FP32's canonical NaN is 0x7FC00000.
- INT32 output saturates to [-2^31, 2^31 - 1]. INT8 is symmetric, [-127, 127].

Native state of one C element (spec "Output representations"):
- integer command: the sum, wrapped to AccW bits, as a signed int; v = a.
- block-scaled command: the signed Q23.24 code a with sticky NaN and overflow flags;
  v = a / 2^24.
"""

from dataclasses import dataclass
from fractions import Fraction

from .hwmode import BLOCK_K, FX_FRAC, FX_MAX, FX_MIN, contribution, round_half_even

FMT_LEGACY, FMT_INT32, FMT_FP32, FMT_FP16, FMT_INT8 = range(5)
ELEMENT_BYTES = (4, 4, 4, 2, 1)
F32_NAN = 0x7FC00000
F16_NAN = 0x7E00
I32_MAX = (1 << 31) - 1
I32_MIN = -(1 << 31)


@dataclass(frozen=True)
class Native:
    """One retained C element: integer (scaled=False) or Q23.24 with flags (scaled=True)."""

    scaled: bool
    value: int = 0
    ovf: bool = False
    nan: bool = False


ZERO_INT = Native(False)
ZERO_FX = Native(True)


# --- accumulation -------------------------------------------------------------------------


def wrap(v, acc_w):
    """A Python int wrapped to a signed acc_w-bit value."""
    v &= (1 << acc_w) - 1
    return v - (1 << acc_w) if v >> (acc_w - 1) else v


def integer_step(state, a_codes, b_codes, acc_w=32):
    """One integer command's contribution to one element. state: the retained Native, or
    None for clear_acc = 1. An odd K in INT4 mode pads its final pair with zero, which adds
    nothing, so the pair structure does not show here."""
    base = 0 if state is None else state.value
    return Native(False, wrap(base + sum(a * b for a, b in zip(a_codes, b_codes)), acc_w))


def scaled_step(state, a_codes, b_codes, sa, sb, block_k=BLOCK_K):
    """One block-scaled command's contribution to one element. a_codes / b_codes hold the
    command's K codes; sa / sb its G = ceil(K / block_k) bf16 scales in increasing block
    order. A partial final block uses only the actual K codes (zero padding). Each command
    starts a new block. state: the retained Native, or None for clear_acc = 1."""
    k = len(a_codes)
    g_count = -(-k // block_k)
    if len(b_codes) != k or len(sa) != g_count or len(sb) != g_count:
        raise ValueError("need K codes in each operand and ceil(K / BlockK) scales")
    acc, ovf, nan = (0, False, False) if state is None else (state.value, state.ovf, state.nan)
    for g in range(g_count):
        lo, hi = g * block_k, min(k, (g + 1) * block_k)
        isum = sum(a * b for a, b in zip(a_codes[lo:hi], b_codes[lo:hi]))
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
    return Native(True, acc, ovf, nan)


# --- output conversion --------------------------------------------------------------------


def round_float(q, exp_bits, man_bits):
    """A nonzero Fraction -> IEEE bits with exp_bits / man_bits, round to nearest even,
    subnormals kept, overflow to infinity."""
    bias = (1 << (exp_bits - 1)) - 1
    sign = 1 if q < 0 else 0
    q = abs(q)
    e = q.numerator.bit_length() - q.denominator.bit_length()
    if Fraction(2) ** e > q:
        e -= 1
    e = max(e, 1 - bias)  # below the normal range: the subnormal quantum
    m = round_half_even(q / Fraction(2) ** (e - man_bits))
    if m == 1 << (man_bits + 1):  # rounding carried into the next binade
        m >>= 1
        e += 1
    top = sign << (exp_bits + man_bits)
    if e > bias:
        return top | (((1 << exp_bits) - 1) << man_bits)
    biased = e + bias if m >> man_bits else 0
    return top | (biased << man_bits) | (m & ((1 << man_bits) - 1))


def real_value(x):
    """The element's exact value v (ignores the flags)."""
    return Fraction(x.value, 1 << FX_FRAC) if x.scaled else Fraction(x.value)


def to_fp(x, exp_bits, man_bits, nan_bits):
    """FP32 or FP16 of an element: NaN, signed infinity on overflow, +0 for zero."""
    if x.scaled and x.nan:
        return nan_bits
    sign = 1 << (exp_bits + man_bits)
    if x.scaled and x.ovf:
        return (sign if x.value < 0 else 0) | (((1 << exp_bits) - 1) << man_bits)
    if x.value == 0:
        return 0
    return round_float(real_value(x), exp_bits, man_bits)


def to_int32_fixed(x, frac):
    """saturate32(RNE(v * 2^frac)); NaN gives 0, overflow the endpoint with acc's sign."""
    if x.scaled and x.nan:
        return 0
    if x.scaled and x.ovf:
        r = I32_MIN if x.value < 0 else I32_MAX
    else:
        r = max(I32_MIN, min(I32_MAX, round_half_even(real_value(x) * (1 << frac))))
    return r & 0xFFFFFFFF


def to_int8(x, mul, shift):
    """clamp(RNE(a * mul / 2^shift), -127, 127) of the native code a; NaN gives 0, overflow
    the endpoint with acc's sign. a is AccW (integer) or 48 (scaled) bits and mul 32 bits
    unsigned, so the hardware's product needs 80 bits."""
    if x.scaled and x.nan:
        r = 0
    elif x.scaled and x.ovf:
        r = -127 if x.value < 0 else 127
    else:
        r = max(-127, min(127, round_half_even(Fraction(x.value * mul, 1 << shift))))
    return r & 0xFF


def convert(x, fmt, frac=0, mul=0, shift=0):
    """One element in output encoding fmt, as an unsigned int of ELEMENT_BYTES[fmt] bytes."""
    if fmt == FMT_LEGACY:
        return to_fp(x, 8, 23, F32_NAN) if x.scaled else x.value & 0xFFFFFFFF
    if fmt == FMT_INT32:
        return to_int32_fixed(x, frac)
    if fmt == FMT_FP32:
        return to_fp(x, 8, 23, F32_NAN)
    if fmt == FMT_FP16:
        return to_fp(x, 5, 10, F16_NAN)
    if fmt == FMT_INT8:
        return to_int8(x, mul, shift)
    raise ValueError(f"unsupported output encoding {fmt}")


# --- a whole command ----------------------------------------------------------------------


def command(state, a, b, sa=None, sb=None, m=None, n=None, scaled=False, acc_w=32,
            block_k=BLOCK_K):
    """One command on the physical tile. a[i][k] is Rows x K, b[k][j] is K x Cols, as stored
    (inactive lanes may hold any bytes); sa[i][g] and sb[g][j] the scale tables when scaled.
    state: the retained Rows x Cols Natives, or None for clear_acc = 1. Lanes outside the
    logical m x n read as zero, scales included. Returns the new retained state."""
    rows, cols = len(a), len(b[0])
    m = rows if m is None else m
    n = cols if n is None else n
    k = len(b)
    out = []
    for i in range(rows):
        row = []
        for j in range(cols):
            on = i < m and j < n
            ac = [a[i][kk] if on else 0 for kk in range(k)]
            bc = [b[kk][j] if on else 0 for kk in range(k)]
            prev = None if state is None else state[i][j]
            if scaled:
                g_count = -(-k // block_k)
                sai = [sa[i][g] if on else 0 for g in range(g_count)]
                sbj = [sb[g][j] if on else 0 for g in range(g_count)]
                row.append(scaled_step(prev, ac, bc, sai, sbj, block_k))
            else:
                row.append(integer_step(prev, ac, bc, acc_w))
        out.append(row)
    return out


def output_bytes(state, fmt, m=None, n=None, frac=0, mul=0, shift=0):
    """The bytes a writing command stores at c_base: element (i, j) at
    ELEMENT_BYTES[fmt] * (i * Cols + j), little-endian; inactive elements are zero."""
    rows, cols = len(state), len(state[0])
    m = rows if m is None else m
    n = cols if n is None else n
    eb = ELEMENT_BYTES[fmt]
    out = bytearray()
    for i in range(rows):
        for j in range(cols):
            v = convert(state[i][j], fmt, frac, mul, shift) if i < m and j < n else 0
            out += v.to_bytes(eb, "little")
    return bytes(out)


# --- the version-1 command record ---------------------------------------------------------

RECORD_WORDS = 16
KIND_MATRIX = 1
RECORD_VERSION = 1


def encode_record(a_addr=0, b_addr=0, c_addr=0, sa_addr=0, sb_addr=0, m=1, n=1, k=1,
                  trans_a=0, trans_b=0, clear=1, write=1, int4=0, scaled=0, fmt=0, frac=0,
                  mul=0, shift=0, mem_wait=0, vec_wait=0, kind=KIND_MATRIX,
                  version=RECORD_VERSION):
    """Fields -> the 512-bit record as an int (word w in bits 32w+31 .. 32w)."""
    w = [0] * RECORD_WORDS
    w[0] = (kind & 3) | ((version & 0xFF) << 8)
    w[1], w[2] = mem_wait, vec_wait
    w[3:8] = [a_addr, b_addr, c_addr, sa_addr, sb_addr]
    w[8] = (m & 0xFFFF) | ((n & 0xFFFF) << 16)
    w[9] = ((k & 0xFFFF) | (trans_a & 1) << 16 | (trans_b & 1) << 17 | (clear & 1) << 18
            | (write & 1) << 19 | (int4 & 1) << 20 | (scaled & 1) << 21 | (fmt & 7) << 22
            | (frac & 0x3F) << 25)
    w[10] = mul
    w[11] = shift & 0x7F
    return sum((x & 0xFFFFFFFF) << (32 * i) for i, x in enumerate(w))


def decode_record(rec):
    """The 512-bit record -> (fields, malformed). Malformed (the decoder's rule, agreed with
    Zeb 2026-11-08): kind or version not 1, any reserved bit set, output format above 4,
    fractional bits above 31, or a transpose bit set (transpose is out of version 1).
    Range checks against the array (M, N, K, alignment) belong to the wrapper."""
    w = [(rec >> (32 * i)) & 0xFFFFFFFF for i in range(RECORD_WORDS)]
    f = dict(
        kind=w[0] & 3, version=(w[0] >> 8) & 0xFF, mem_wait=w[1], vec_wait=w[2],
        a_addr=w[3], b_addr=w[4], c_addr=w[5], sa_addr=w[6], sb_addr=w[7],
        m=w[8] & 0xFFFF, n=w[8] >> 16, k=w[9] & 0xFFFF,
        trans_a=(w[9] >> 16) & 1, trans_b=(w[9] >> 17) & 1, clear=(w[9] >> 18) & 1,
        write=(w[9] >> 19) & 1, int4=(w[9] >> 20) & 1, scaled=(w[9] >> 21) & 1,
        fmt=(w[9] >> 22) & 7, frac=(w[9] >> 25) & 0x3F, mul=w[10], shift=w[11] & 0x7F)
    reserved = ((w[0] & ~0xFF03 & 0xFFFFFFFF) or (w[9] >> 31) or (w[11] >> 7)
                or any(w[12:16]))
    malformed = bool(f["kind"] != KIND_MATRIX or f["version"] != RECORD_VERSION or reserved
                     or f["fmt"] > FMT_INT8 or f["frac"] > 31 or f["trans_a"]
                     or f["trans_b"])
    return f, malformed
