"""Quantized dot products, bit-exact: what llama.cpp computes for one output element of a
matrix x vector product. SEMANTICS.md section 5.

Sources (llama.cpp f46bc30, generic CPU path, one row per call):
ggml_vec_dot_q8_0_q8_0 (ggml-cpu/quants.c:451), ggml_vec_dot_q4_K_q8_K (696),
ggml_vec_dot_q5_K_q8_K (771), ggml_vec_dot_q6_K_q8_K (851).

The integer parts are exact Python ints. Each int -> float conversion is rounded to binary32
as C does (it is exact for real inputs, below 2^24, but not for arbitrary bsums), and every
float operation is one binary32 rounding, in C's order.
"""

from .blocks import DECODE, TYPES, blocks
from .fp import add, f16_to_f32, f32, mul, sub

# weight type -> activation type llama.cpp quantizes the vector to (vec_dot_type)
VEC_DOT_TYPE = {"q4_K": "q8_K", "q5_K": "q8_K", "q6_K": "q8_K", "q8_0": "q8_0"}


def _pairs(wtype, w, y):
    wb = blocks(wtype, w)
    yb = blocks(VEC_DOT_TYPE[wtype], y)
    if len(wb) != len(yb):
        raise ValueError(f"{len(wb)} weight blocks against {len(yb)} activation blocks")
    return zip(wb, yb)


def vec_dot_q8_0_q8_0(w, y):
    sumf = 0.0
    for wb, yb in _pairs("q8_0", w, y):
        x, a = DECODE["q8_0"](wb), DECODE["q8_0"](yb)
        sumi = sum(p * q for p, q in zip(x["q"], a["q"]))
        # sumf += sumi * (dx * dy)
        sumf = add(sumf, mul(f32(sumi), mul(f16_to_f32(x["d"]), f16_to_f32(a["d"]))))
    return sumf


def _vec_dot_k(wtype, w, y):
    """q4_K / q5_K / q6_K against q8_K: eight interleaved integer lanes per super-block
    (lane = element index mod 8), scaled into eight fp32 accumulators that run across the
    whole row and are added to sumf at the end; q4_K and q5_K also subtract the min term."""
    sums = [0.0] * 8
    sumf = 0.0
    group = 16 if wtype == "q6_K" else 32  # elements per scale
    for wb, yb in _pairs(wtype, w, y):
        x, a = DECODE[wtype](wb), DECODE["q8_K"](yb)
        aux32 = [0] * 8
        for e in range(256):
            aux32[e % 8] += x["sc"][e // group] * (a["q"][e] * x["q"][e])
        d = mul(f16_to_f32(x["d"]), a["d"])
        for lane in range(8):
            sums[lane] = add(sums[lane], mul(d, f32(aux32[lane])))
        if wtype != "q6_K":
            sumi = sum(a["bsums"][g] * x["m"][g // 2] for g in range(16))
            dmin = mul(f16_to_f32(x["dmin"]), a["d"])
            sumf = sub(sumf, mul(dmin, f32(sumi)))
    for lane in range(8):
        sumf = add(sumf, sums[lane])
    return sumf


def vec_dot(wtype, w, y):
    """One weight row (raw blocks of wtype) dotted with one activation row (raw blocks of
    VEC_DOT_TYPE[wtype]), as binary32."""
    if wtype == "q8_0":
        return vec_dot_q8_0_q8_0(w, y)
    if wtype in ("q4_K", "q5_K", "q6_K"):
        return _vec_dot_k(wtype, w, y)
    raise ValueError(f"no dot product for {wtype}")


def row_bytes(wtype, n):
    """Bytes of an n-element row of wtype."""
    _, per, size = TYPES[wtype]
    return n // per * size
