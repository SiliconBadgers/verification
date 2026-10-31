"""IEEE binary32 and binary16 helpers, exact.

Each reference fp32 operation is computed in double and rounded once to binary32. For
+, -, *, / of binary32 inputs that equals the true binary32 result (53 >= 2*24 + 2), so the
model never fuses or reorders anything. Integers are Python ints and convert exactly while
below 2^24 (SEMANTICS.md section 5).
"""

import math
import struct

_F32 = struct.Struct("<f")
_F16 = struct.Struct("<e")
_U32 = struct.Struct("<I")


def f32(x):
    """Round a double to the nearest binary32 (ties to even), returned as a Python float.
    Overflow gives +-infinity, as in C: struct raises only when the rounded value is
    infinite, so the rounding decision is already IEEE's."""
    try:
        return _F32.unpack(_F32.pack(x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def add(a, b):
    return f32(a + b)


def sub(a, b):
    return f32(a - b)


def mul(a, b):
    return f32(a * b)


def div(a, b):
    """IEEE division: x/0 is +-infinity (sign of a xor sign of b); 0/0 and NaN/0 are NaN.
    Python raises instead, so zero divisors are handled here."""
    if b == 0:
        if a == 0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a) * math.copysign(1.0, b)
    return f32(a / b)


def f16_to_f32(h):
    """A binary16 bit pattern (int) as a float. Exact, subnormals included."""
    return _F16.unpack(struct.pack("<H", h))[0]


def f32_to_f16(x):
    """A binary32 value to binary16 bits, round to nearest even, overflow to infinity,
    NaN to 0x7E00 with the sign kept (ggml_compute_fp32_to_fp16, ggml-impl.h:419)."""
    bits = f32_bits(x)
    sign = (bits >> 16) & 0x8000
    if math.isnan(x):
        return sign | 0x7E00
    try:
        return struct.unpack("<H", _F16.pack(x))[0]
    except OverflowError:
        return sign | 0x7C00


def f32_bits(x):
    """The binary32 bit pattern of a value that is already binary32."""
    return _U32.unpack(_F32.pack(x))[0]


def bits_f32(u):
    """A binary32 bit pattern as a float."""
    return _F32.unpack(_U32.pack(u & 0xFFFFFFFF))[0]
