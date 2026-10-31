"""Matrix x vector as llama.cpp computes it for one token (M = 1), bit-exact.

ggml_compute_forward_mul_mat (generic CPU path) quantizes the activation row once to the
weight type's vec_dot_type, then each output element is one vec_dot over the whole weight
row; results are copied out with no further arithmetic (ggml-cpu/ggml-cpu.c:1165,
SEMANTICS.md section 1).
"""

from .dot import VEC_DOT_TYPE, row_bytes, vec_dot
from .quant import quantize_row_q8_0, quantize_row_q8_K


def quantize_activation(wtype, x):
    """Activation values -> raw blocks of the type wtype's dot product takes."""
    return quantize_row_q8_K(x) if VEC_DOT_TYPE[wtype] == "q8_K" else quantize_row_q8_0(x)


def matvec(wtype, w, x):
    """w: raw rows of wtype, each len(x) elements; x: binary32 activations.
    Returns one binary32 per row."""
    y = quantize_activation(wtype, x)
    rb = row_bytes(wtype, len(x))
    if len(w) % rb:
        raise ValueError("weights are not whole rows of len(x) elements")
    return [vec_dot(wtype, w[r : r + rb], y) for r in range(0, len(w), rb)]


def matvec_tensor(gguf, name, x, first=0, count=None):
    """matvec over rows first .. first + count - 1 of a GGUF tensor (all rows by default)."""
    t = gguf.tensors[name]
    if t.dims[0] != len(x):
        raise ValueError(f"{name} reduces over {t.dims[0]} elements, x has {len(x)}")
    count = t.rows - first if count is None else count
    return matvec(t.type_name, gguf.read_rows(name, first, count), x)
