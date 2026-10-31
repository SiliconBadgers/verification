"""Phase 3: the four quantized dot products, bit for bit against llama.cpp (f46bc30).

For each weight type: random rows against activations the model quantized (byte-exact
since phase 2) and against raw random activation blocks (arbitrary bsums and scales,
beyond what real data reaches); special fp16 weight scales; and real rows from the model
against a real activation (dequantized token embeddings).

Every result must have C's binary32 bits; two NaNs match whatever their payloads.
"""

import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from golden.blocks import dequantize  # noqa: E402
from golden.dot import VEC_DOT_TYPE, row_bytes, vec_dot  # noqa: E402
from golden.fp import f32, f32_bits  # noqa: E402
from golden.gguf import GGUF  # noqa: E402
from golden.quant import quantize_row_q8_0, quantize_row_q8_K  # noqa: E402
from test_dequant import SPECIAL_F16, random_block  # noqa: E402

HARNESS = os.environ.get("GM_HARNESS", os.path.expanduser("~/gm_build/gm_harness"))
MODEL = os.environ.get(
    "GM_GGUF", os.path.expanduser("~/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf"))
SEED = int(os.environ.get("GM_SEED", "1"))
N = 2048  # row length: the model's hidden size


def c_dot(wtype, w, y):
    with tempfile.TemporaryDirectory() as d:
        wp, yp, op = Path(d, "w.bin"), Path(d, "y.bin"), Path(d, "out.bin")
        wp.write_bytes(w)
        yp.write_bytes(y)
        subprocess.run([HARNESS, "dot", wtype, str(wp), str(yp), str(op)], check=True)
        raw = op.read_bytes()
    return list(struct.unpack(f"<{len(raw) // 4}I", raw))


def check_rows(test, wtype, w, y, label):
    """Model vec_dot of every row of w against y, compared with C."""
    n_row = len(y) // (292 if VEC_DOT_TYPE[wtype] == "q8_K" else 34) * (256 if wtype != "q8_0" else 32)
    rb = row_bytes(wtype, n_row)
    want = c_dot(wtype, w, y)
    test.assertEqual(len(want), len(w) // rb, label)
    bad = []
    for r, wv in enumerate(want):
        g = vec_dot(wtype, w[r * rb : (r + 1) * rb], y)
        w_nan = (wv & 0x7F800000) == 0x7F800000 and (wv & 0x7FFFFF) != 0
        if (math.isnan(g) and w_nan) or f32_bits(g) == wv:
            continue
        bad.append(f"row {r}: model {f32_bits(g):08x} C {wv:08x}")
        if len(bad) == 4:
            break
    test.assertFalse(bad, f"{label}: " + "; ".join(bad))
    return len(want)


def quantize_activation(wtype, x):
    return quantize_row_q8_K(x) if VEC_DOT_TYPE[wtype] == "q8_K" else quantize_row_q8_0(x)


def random_q8_K_block(rng):
    d = struct.unpack("<f", struct.pack("<I", rng.getrandbits(32)))[0] if rng.random() < 0.1 \
        else f32(rng.choice((-1, 1)) * 2.0 ** rng.uniform(-20, 4))
    qs = [rng.randrange(-128, 128) for _ in range(256)]
    bsums = [rng.randrange(-32768, 32768) for _ in range(16)]
    return struct.pack("<f256b16h", d, *qs, *bsums)


def random_q8_0_block(rng):
    return struct.pack("<H32b", rng.getrandbits(16), *[rng.randrange(-128, 128) for _ in range(32)])


class Dot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access(HARNESS, os.X_OK):
            raise unittest.SkipTest(f"no C harness at {HARNESS}; run harness/build.sh")

    def weight_rows(self, rng, wtype, rows, specials):
        per = 32 if wtype == "q8_0" else 256

        def f16():
            if specials and rng.random() < 0.05:
                return rng.choice(SPECIAL_F16)
            return rng.getrandbits(1) << 15 | rng.randrange(0x1000, 0x5000)

        return b"".join(random_block(rng, wtype, f16) for _ in range(rows * N // per))

    def test_quantized_activations(self):
        rng = random.Random(SEED)
        for wtype in ("q4_K", "q5_K", "q6_K", "q8_0"):
            for scale in (1e-3, 1.0, 1e3):
                x = [f32(rng.gauss(0.0, 1.0) * scale) for _ in range(N)]
                y = quantize_activation(wtype, x)
                check_rows(self, wtype, self.weight_rows(rng, wtype, 24, False), y,
                           f"{wtype} quantized activation x{scale:g}")

    def test_raw_activations(self):
        rng = random.Random(SEED + 1)
        for wtype in ("q4_K", "q5_K", "q6_K", "q8_0"):
            for _ in range(3):
                if VEC_DOT_TYPE[wtype] == "q8_K":
                    y = b"".join(random_q8_K_block(rng) for _ in range(N // 256))
                else:
                    y = b"".join(random_q8_0_block(rng) for _ in range(N // 32))
                check_rows(self, wtype, self.weight_rows(rng, wtype, 16, False), y,
                           f"{wtype} raw activation blocks")

    def test_special_weight_scales(self):
        rng = random.Random(SEED + 2)
        for wtype in ("q4_K", "q5_K", "q6_K", "q8_0"):
            x = [f32(rng.gauss(0.0, 1.0)) for _ in range(N)]
            check_rows(self, wtype, self.weight_rows(rng, wtype, 32, True),
                       quantize_activation(wtype, x), f"{wtype} special scales")

    def test_min_term_rounding(self):
        """Directed: only the min term survives (all q8_K codes 0), and the bsums make
        sumi odd and above 2^24, so its int -> float conversion must round as C does.
        Real data never gets there (bsums <= 2032), but the model must stay exact."""
        rng = random.Random(SEED + 3)
        weights, acts = [], []
        for _ in range(64):
            dmin = rng.getrandbits(1) << 15 | rng.randrange(0x1000, 0x5000)
            d = rng.randrange(0x1000, 0x5000)
            # scale bytes 0xFF: every 6-bit scale and min is 63
            weights.append(struct.pack("<HH", d, dmin) + b"\xff" * 12 + bytes(rng.getrandbits(8) for _ in range(128)))
            bsums = [32767] * 15 + [rng.choice((32766, 32765, 32763))]
            acts.append(struct.pack("<f256b16h", f32(2.0 ** rng.uniform(-8, 8)), *([0] * 256), *bsums))
        for k in range(64):  # one super-block per dot, so each result is -dmin*d8*sumi
            check_rows(self, "q4_K", weights[k], acts[k], f"min-term rounding {k}")

    def test_real_rows(self):
        if not os.path.exists(MODEL):
            self.skipTest(f"no model at {MODEL}")
        g = GGUF(MODEL)
        # A real activation: dequantized token embeddings (the model's own input vectors).
        emb = g.tensors["token_embd.weight"]
        tokens = (151644, 872, 9707, 1879)
        emb_rows = [dequantize("q6_K", g.read_rows("token_embd.weight", t, 1)) for t in tokens]
        picks = {"q4_K": "blk.0.ffn_gate.weight", "q5_K": "blk.0.attn_qkv.weight",
                 "q6_K": "blk.0.ffn_down.weight", "q8_0": "blk.0.ssm_alpha.weight"}
        self.assertEqual(emb.dims[0], N)
        for wtype, name in picks.items():
            t = g.tensors[name]
            k = t.dims[0]
            x = [v for row in emb_rows for v in row][:k] if k > N else emb_rows[0]
            if k > N:  # ffn_down reduces over 6144: three embedding rows end to end
                x = (emb_rows[0] + emb_rows[1] + emb_rows[2])[:k]
            y = quantize_activation(wtype, x)
            rows = sorted({0, 1, t.rows // 2, t.rows - 1})
            w = b"".join(g.read_rows(name, r, 1) for r in rows)
            check_rows(self, wtype, w, y, f"{name} rows {rows}")


if __name__ == "__main__":
    unittest.main()
