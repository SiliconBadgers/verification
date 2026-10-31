"""Activation quantization, bit-exact: q8_K (for q4_K/q5_K/q6_K weights) and q8_0 (for q8_0
weights). SEMANTICS.md section 4.

Sources (llama.cpp f46bc30): quantize_row_q8_K_ref (ggml-quants.c:2768), nearest_int
(ggml-quants.c:621), quantize_row_q8_0_ref (ggml-quants.c:276). The CPU backend's
quantize_row_q8_K / _q8_0 call these on the generic path (ggml-cpu/quants.c:49, 121).
"""

import math
import struct

from .blocks import QK8_0, QK_K
from .fp import add, div, f32_bits, f32_to_f16, mul

MAGIC = 12582912.0  # 1.5 * 2^23


def nearest_int(fval):
    """ggml's nearest_int: add 1.5*2^23 in binary32 and read the low mantissa bits. Round to
    nearest, ties to even, for |fval| <= 4194303."""
    return (f32_bits(add(fval, MAGIC)) & 0x007FFFFF) - 0x00400000


def roundf(x):
    """C roundf: nearest integer, ties away from zero (x is binary32, so x + 0.5 is exact in
    double)."""
    if math.isnan(x) or math.isinf(x):
        return x
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def to_int8(v):
    """C conversion of a float to int8_t through int32 the way x86 does it: out-of-range
    and NaN become INT32_MIN, whose low byte is 0. Only pathological inputs reach this."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v) or abs(v) >= 2**31):
        return 0
    v = int(v)
    return ((v + 128) & 0xFF) - 128


def quantize_block_q8_K(x):
    """256 binary32 values -> (d, qs[256], bsums[16]); bsums is None for an all-zero block,
    which C leaves unwritten (the result never depends on it)."""
    amax = 0.0
    mx = 0.0
    for v in x:
        ax = abs(v)
        if ax > amax:  # strict: the first index of the largest magnitude wins
            amax = ax
            mx = v
    if not amax:
        return 0.0, [0] * QK_K, None
    iscale = div(-127.0, mx)
    # qs is int8_t: C keeps the low byte of MIN(127, v). Only pathological inputs (an
    # overflowing iscale) give a v outside -127..127. bsums sums the stored bytes.
    qs = [to_int8(min(127, nearest_int(mul(iscale, v)))) for v in x]
    bsums = [sum(qs[16 * g : 16 * g + 16]) for g in range(QK_K // 16)]
    return div(1.0, iscale), qs, bsums


def quantize_block_q8_0(x):
    """32 binary32 values -> (d as fp16 bits, qs[32])."""
    amax = 0.0
    for v in x:
        a = abs(v)
        amax = amax if amax > a else a  # MAX(amax, fabsf(v)): a NaN is replaced by the next value
    d = div(amax, 127.0)
    inv = div(1.0, d) if d != 0 else 0.0  # NaN is "true" in C, so 1/NaN
    qs = [to_int8(roundf(mul(v, inv))) for v in x]
    return f32_to_f16(d), qs


def quantize_row_q8_K(x):
    """Values -> raw block_q8_K bytes (bsums written as 0 for all-zero blocks)."""
    if len(x) % QK_K:
        raise ValueError("q8_K rows are whole 256-element blocks")
    out = bytearray()
    for i in range(0, len(x), QK_K):
        d, qs, bsums = quantize_block_q8_K(x[i : i + QK_K])
        out += struct.pack("<f256b16h", d, *qs, *(bsums or [0] * 16))
    return bytes(out)


def quantize_row_q8_0(x):
    """Values -> raw block_q8_0 bytes."""
    if len(x) % QK8_0:
        raise ValueError("q8_0 rows are whole 32-element blocks")
    out = bytearray()
    for i in range(0, len(x), QK8_0):
        d, qs = quantize_block_q8_0(x[i : i + QK8_0])
        out += struct.pack("<H32b", d, *qs)
    return bytes(out)
