#!/usr/bin/env python3
"""Accuracy study (phase 6): how far each arithmetic lands from the ideal, on real tensors.

For one weight matrix of each format in Qwen3.5-2B Q4_K_M, against real activations (the
dequantized embeddings of four real tokens):

  ideal      the stored weights (dequantized, exact) times the float activations, in double
  llama.cpp  the golden model: activation quantized to q8_K / q8_0, bit-exact llama.cpp
  matrix     the matrix unit as built: weights requantized to INT4 (q4_K) or INT8, the
             activation to INT8, bf16 scales per 16 (assumed rule, golden/hwmode.py), the
             unit's arithmetic contract

Error metric: relative RMS error over the output vector, ||y - ideal|| / ||ideal||, averaged
over the tokens; also the worst token. Writes ACCURACY.md next to this tool's directory.

Usage: python3 tools/accuracy_study.py MODEL.gguf [ROWS_PER_TENSOR]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.blocks import dequantize  # noqa: E402
from golden.gguf import GGUF  # noqa: E402
from golden.hwmode import requantize, scaled_element, scaled_value  # noqa: E402
from golden.matvec import matvec  # noqa: E402

TOKENS = (151644, 872, 9707, 1879)
TENSORS = [  # name, matrix-unit weight width, what it is
    ("blk.0.ffn_gate.weight", 4, "FFN gate, q4_K as INT4"),
    ("blk.0.ffn_gate.weight", 8, "FFN gate, q4_K as INT8"),
    ("blk.0.attn_qkv.weight", 8, "attention QKV, q5_K"),
    ("blk.0.ffn_down.weight", 8, "FFN down, q6_K"),
    ("blk.0.ssm_alpha.weight", 8, "DeltaNet alpha, q8_0"),
    ("token_embd.weight", 8, "output head, q6_K"),
]


def rel_rms(y, ref):
    num = math.fsum((a - b) ** 2 for a, b in zip(y, ref))
    den = math.fsum(b * b for b in ref)
    return math.sqrt(num / den) if den else float("nan")


def main():
    g = GGUF(sys.argv[1])
    rows_cap = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    emb = [dequantize("q6_K", g.read_rows("token_embd.weight", t, 1)) for t in TOKENS]
    lines = []
    results = []
    for name, bits, what in TENSORS:
        t = g.tensors[name]
        k = t.dims[0]
        rows = min(t.rows, rows_cap)
        # Spread the sampled rows over the whole matrix.
        picks = sorted({r * t.rows // rows for r in range(rows)})
        raw = b"".join(g.read_rows(name, r, 1) for r in picks)
        w = [dequantize(t.type_name, raw[i * t.row_bytes : (i + 1) * t.row_bytes])
             for i in range(len(picks))]
        wq = [requantize(row, bits) for row in w]
        e_llama, e_unit = [], []
        for tok in range(len(TOKENS)):
            x = [v for row in emb for v in row]
            x = (x[tok * 2048 :] + x)[:k]  # this token's embedding first, padded with the others
            ideal = [math.fsum(a * b for a, b in zip(row, x)) for row in w]
            y_llama = matvec(t.type_name, raw, x)
            xc, xs = requantize(x, 8)
            y_unit = [scaled_value(scaled_element(xc, rq[0], xs, rq[1])) for rq in wq]
            e_llama.append(rel_rms(y_llama, ideal))
            e_unit.append(rel_rms(y_unit, ideal))
        r = (what, name, len(picks), k, sum(e_llama) / len(e_llama), max(e_llama),
             sum(e_unit) / len(e_unit), max(e_unit))
        results.append(r)
        print(f"{what:24s} rows={len(picks):4d} K={k:5d} llama.cpp {r[4]:.2e} (max {r[5]:.2e})"
              f"  matrix unit {r[6]:.2e} (max {r[7]:.2e})  ratio {r[6] / r[4]:.1f}x", flush=True)

    lines.append("# Accuracy study (phase 6)")
    lines.append("")
    lines.append("This is the relative RMS error of each arithmetic against the ideal, on real "
                 "Qwen3.5-2B Q4_K_M tensors with real activations (the dequantized embeddings of "
                 f"four tokens: {', '.join(map(str, TOKENS))}).")
    lines.append("")
    lines.append("- **Ideal:** the stored weights (dequantized, exact) times the float "
                 "activations, computed in double.")
    lines.append("- **llama.cpp:** the bit-exact golden model. Its error comes from quantizing "
                 "the activation (q8_K, or q8_0 for q8_0 weights).")
    lines.append("- **Matrix unit:** the unit as built. Weights are requantized to INT4 (q4_K) or "
                 "INT8, and activations to INT8, with bf16 scales per 16 (an assumed rule, "
                 "`golden/hwmode.py`), then run through the unit's arithmetic contract.")
    lines.append("")
    lines.append(f"`tools/accuracy_study.py`, up to {rows_cap} output rows per tensor, spread "
                 "over the matrix.")
    lines.append("")
    lines.append("| Tensor | Rows | K | llama.cpp error (mean / worst) | Matrix unit error "
                 "(mean / worst) | Matrix unit ÷ llama.cpp |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for what, name, rows, k, ml, xl, mu, xu in results:
        lines.append(f"| {what} (`{name}`) | {rows} | {k} | {ml:.2e} / {xl:.2e} | "
                     f"{mu:.2e} / {xu:.2e} | {mu / ml:.1f}× |")
    lines.append("")
    by = {r[0]: r for r in results}
    i4, i8 = by["FFN gate, q4_K as INT4"], by["FFN gate, q4_K as INT8"]
    others = [r for r in results if not r[0].startswith("FFN gate")]
    lo = min(r[6] / r[4] for r in others + [i8])
    hi = max(r[6] / r[4] for r in others + [i8])
    lines += [
        "## What it shows",
        "",
        f"- **INT8 costs nothing.** Every tensor run through the unit as INT8 (Q5_K, Q6_K, Q8_0, "
        f"and Q4_K too) lands within {lo:.1f}–{hi:.1f}× of llama.cpp's own error.",
        f"- **INT4 costs a lot.** Q4_K requantized to symmetric INT4 with bf16 scales per 16 has "
        f"{i4[6] / i4[4]:.0f}× llama.cpp's error ({100 * i4[6]:.1f}% against "
        f"{100 * i4[4]:.2f}%).",
        f"  - The control row is the same tensor as INT8 ({i8[6] / i8[4]:.1f}×), so the INT4 "
        "grid is the cause.",
        "  - Q4_K's asymmetric grid (6-bit scale and min per 32, fp16 per 256) cannot be "
        "expressed in symmetric INT4.",
        "  - Requantizing therefore adds a full 4-bit step of quantization noise: about "
        "step/√12 ≈ 8% for Gaussian-like weights in groups of 16.",
        "- **What it means for D2 (the weight format).** 98 of the model's 187 matrix "
        "weights (49% of the weights) are Q4_K. Three options:",
        "  1. **Support Q4_K natively** (integer sub-block scales and the min term, as in "
        "llama.cpp). It's exact and keeps INT4 throughput.",
        "  2. **Run Q4_K tensors as INT8 on today's unit.** It's accurate, but runs at half the "
        "INT4 rate and moves twice the weight bytes.",
        "  3. **Keep symmetric INT4** and accept about 12× the error on half the weights. That "
        "needs an end-to-end check (perplexity) before anyone signs off on it.",
        "",
        "## Caveats",
        "",
        "- **Not a real forward pass.** These are layer-0 tensors (and the output head) "
        "against raw token embeddings, not RMS-normed hidden states.",
        "- **A sample.** At most 256 output rows per tensor.",
        "- **Not model quality.** The metric is relative RMS error over the output vector, "
        "not perplexity.",
        "- **The requantization rule is an assumption.** A smarter rule (for example, "
        "MSE-optimal scales) can reduce the INT4 gap but not remove it, because the two grids "
        "differ.",
        "",
    ]
    out = Path(__file__).resolve().parents[1] / "ACCURACY.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
