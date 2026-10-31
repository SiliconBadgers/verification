"""ggml block formats used by Qwen3.5-2B Q4_K_M, and their dequantization (bit-exact).

Layouts: ggml-common.h at llama.cpp f46bc30 (SEMANTICS.md section 3). Dequantization:
ggml-quants.c dequantize_row_q4_K (1529), _q5_K (1731), _q6_K (1939), _q8_0 (553), each
reproduced with its exact sequence of binary32 roundings.
"""

import struct

from .fp import f16_to_f32, f32, mul, sub

QK_K = 256
QK8_0 = 32

# type name -> (ggml type id, elements per block, bytes per block)
TYPES = {
    "q8_0": (8, QK8_0, 34),
    "q4_K": (12, QK_K, 144),
    "q5_K": (13, QK_K, 176),
    "q6_K": (14, QK_K, 210),
    "q8_K": (15, QK_K, 292),
}
TYPE_BY_ID = {v[0]: k for k, v in TYPES.items()}


def get_scale_min_k4(j, s):
    """6-bit scale and min of sub-block j (0..7) from the 12 packed bytes s
    (ggml-quants.c:880)."""
    if j < 4:
        return s[j] & 63, s[j + 4] & 63
    return (s[j + 4] & 0xF) | ((s[j - 4] >> 6) << 4), (s[j + 4] >> 4) | ((s[j] >> 6) << 4)


def get_scale_min_kmask(s):
    """The same 8 scales and 8 mins, unpacked the way the dot products do it
    (ggml-cpu/quants.c:736, kmask1..3 on 32-bit words). Must equal get_scale_min_k4."""
    kmask1, kmask2, kmask3 = 0x3F3F3F3F, 0x0F0F0F0F, 0x03030303
    u = list(struct.unpack("<3I", bytes(s))) + [0]
    u[3] = ((u[2] >> 4) & kmask2) | (((u[1] >> 6) & kmask3) << 4)
    uaux = u[1] & kmask1
    u[1] = (u[2] & kmask2) | (((u[0] >> 6) & kmask3) << 4)
    u[2] = uaux
    u[0] &= kmask1
    raw = struct.pack("<4I", *u)
    return list(raw[0:8]), list(raw[8:16])


# --- decoders: one block's bytes -> its fields --------------------------------------


def decode_q4_K(b):
    d, dmin = struct.unpack_from("<HH", b, 0)
    scales = b[4:16]
    qs = b[16:144]
    q = [0] * QK_K
    for c in range(4):
        for l in range(32):
            byte = qs[32 * c + l]
            q[64 * c + l] = byte & 0xF
            q[64 * c + 32 + l] = byte >> 4
    sc_m = [get_scale_min_k4(j, scales) for j in range(8)]
    return {"d": d, "dmin": dmin, "q": q, "sc": [x[0] for x in sc_m], "m": [x[1] for x in sc_m]}


def decode_q5_K(b):
    d, dmin = struct.unpack_from("<HH", b, 0)
    scales = b[4:16]
    qh = b[16:48]
    qs = b[48:176]
    q = [0] * QK_K
    for c in range(4):
        for l in range(32):
            byte = qs[32 * c + l]
            q[64 * c + l] = (byte & 0xF) + (16 if qh[l] & (1 << (2 * c)) else 0)
            q[64 * c + 32 + l] = (byte >> 4) + (16 if qh[l] & (1 << (2 * c + 1)) else 0)
    sc_m = [get_scale_min_k4(j, scales) for j in range(8)]
    return {"d": d, "dmin": dmin, "q": q, "sc": [x[0] for x in sc_m], "m": [x[1] for x in sc_m]}


def decode_q6_K(b):
    ql = b[0:128]
    qh = b[128:192]
    scales = list(struct.unpack_from("<16b", b, 192))
    (d,) = struct.unpack_from("<H", b, 208)
    q = [0] * QK_K
    for h in range(2):
        L = ql[64 * h : 64 * h + 64]
        for l in range(32):
            H = qh[32 * h + l]
            q[128 * h + l] = ((L[l] & 0xF) | ((H & 3) << 4)) - 32
            q[128 * h + 32 + l] = ((L[l + 32] & 0xF) | (((H >> 2) & 3) << 4)) - 32
            q[128 * h + 64 + l] = ((L[l] >> 4) | (((H >> 4) & 3) << 4)) - 32
            q[128 * h + 96 + l] = ((L[l + 32] >> 4) | (((H >> 6) & 3) << 4)) - 32
    return {"d": d, "q": q, "sc": scales}


def decode_q8_0(b):
    (d,) = struct.unpack_from("<H", b, 0)
    return {"d": d, "q": list(struct.unpack_from("<32b", b, 2))}


def decode_q8_K(b):
    (d,) = struct.unpack_from("<f", b, 0)
    return {
        "d": d,
        "q": list(struct.unpack_from("<256b", b, 4)),
        "bsums": list(struct.unpack_from("<16h", b, 260)),
    }


DECODE = {"q4_K": decode_q4_K, "q5_K": decode_q5_K, "q6_K": decode_q6_K,
          "q8_0": decode_q8_0, "q8_K": decode_q8_K}


def blocks(type_name, data):
    """Split raw bytes into blocks of one type."""
    _, _, size = TYPES[type_name]
    if len(data) % size:
        raise ValueError(f"{len(data)} bytes is not a whole number of {type_name} blocks")
    return [data[i : i + size] for i in range(0, len(data), size)]


# --- dequantization -------------------------------------------------------------------


def dequantize_block(type_name, b):
    """One block's values as binary32 floats, in element order."""
    x = DECODE[type_name](b)
    q = x["q"]
    if type_name in ("q4_K", "q5_K"):
        # y = d1 * q - m1, with d1 = d * sc and m1 = dmin * m (two roundings, no FMA).
        d = f16_to_f32(x["d"])
        dmin = f16_to_f32(x["dmin"])
        out = []
        for j in range(8):
            d1 = mul(d, x["sc"][j])
            m1 = mul(dmin, x["m"][j])
            out.extend(sub(mul(d1, v), m1) for v in q[32 * j : 32 * j + 32])
        return out
    if type_name == "q6_K":
        # y = (d * sc) * q, left to right.
        d = f16_to_f32(x["d"])
        return [mul(mul(d, x["sc"][e // 16]), q[e]) for e in range(QK_K)]
    if type_name == "q8_0":
        d = f16_to_f32(x["d"])
        return [mul(v, d) for v in q]
    raise ValueError(f"no dequantization for {type_name}")


def dequantize(type_name, data):
    out = []
    for b in blocks(type_name, data):
        out.extend(dequantize_block(type_name, b))
    return out


__all__ = ["QK_K", "QK8_0", "TYPES", "TYPE_BY_ID", "get_scale_min_k4", "get_scale_min_kmask",
           "DECODE", "blocks", "dequantize_block", "dequantize", "f32"]
