"""Phase 4: matrix x vector over whole real tensors, bit for bit against llama.cpp.

One full weight matrix per format from the pinned model, against a real activation (the
dequantized embeddings of real tokens), every output element compared with C's vec_dot on
the same quantized activation. C quantizes the activation itself here, so this also
re-checks phase 2 on real data.

The output head (248,320 rows) runs only with GM_FULL=1: about four minutes in Python.
"""

import math
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.blocks import dequantize  # noqa: E402
from golden.dot import VEC_DOT_TYPE  # noqa: E402
from golden.fp import f32_bits  # noqa: E402
from golden.gguf import GGUF  # noqa: E402
from golden.matvec import matvec_tensor, quantize_activation  # noqa: E402

HARNESS = os.environ.get("GM_HARNESS", os.path.expanduser("~/gm_build/gm_harness"))
MODEL = os.environ.get(
    "GM_GGUF", os.path.expanduser("~/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf"))
FULL = os.environ.get("GM_FULL") == "1"
TOKENS = (151644, 872, 9707, 1879)  # rows of token_embd.weight used as activations


def c_matvec(wtype, w, x):
    """C: quantize x with llama.cpp's own quantizer, then vec_dot every row."""
    with tempfile.TemporaryDirectory() as d:
        xp, yp, wp, op = (Path(d, n) for n in ("x.bin", "y.bin", "w.bin", "out.bin"))
        xp.write_bytes(struct.pack(f"<{len(x)}f", *x))
        subprocess.run([HARNESS, "quant", VEC_DOT_TYPE[wtype], str(xp), str(yp)], check=True)
        wp.write_bytes(w)
        subprocess.run([HARNESS, "dot", wtype, str(wp), str(yp), str(op)], check=True)
        y = yp.read_bytes()
        raw = op.read_bytes()
    return y, list(struct.unpack(f"<{len(raw) // 4}I", raw))


class MatVec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access(HARNESS, os.X_OK):
            raise unittest.SkipTest(f"no C harness at {HARNESS}; run harness/build.sh")
        if not os.path.exists(MODEL):
            raise unittest.SkipTest(f"no model at {MODEL}")
        cls.g = GGUF(MODEL)
        cls.emb = [dequantize("q6_K", cls.g.read_rows("token_embd.weight", t, 1)) for t in TOKENS]

    def activation(self, k):
        x = [v for row in self.emb for v in row]
        while len(x) < k:
            x += x
        return x[:k]

    def check_tensor(self, name):
        t = self.g.tensors[name]
        x = self.activation(t.dims[0])
        w = self.g.read_rows(name, 0, t.rows)
        y_c, want = c_matvec(t.type_name, w, x)
        self.assertEqual(quantize_activation(t.type_name, x), y_c, f"{name}: activation blocks")
        got = matvec_tensor(self.g, name, x)
        self.assertEqual(len(got), t.rows)
        bad = [r for r, (g, wv) in enumerate(zip(got, want))
               if f32_bits(g) != wv and not math.isnan(g)]
        self.assertFalse(bad, f"{name}: {len(bad)} of {t.rows} outputs differ, first rows {bad[:5]}")
        self.assertTrue(any(v != 0 for v in got), f"{name}: all outputs zero")

    def test_q4_K_attn_gate(self):
        self.check_tensor("blk.0.attn_gate.weight")  # 2048 x 2048

    def test_q5_K_attn_qkv(self):
        self.check_tensor("blk.0.attn_qkv.weight")  # 2048 -> 6144

    def test_q6_K_ffn_down(self):
        self.check_tensor("blk.0.ffn_down.weight")  # 6144 -> 2048

    def test_q8_0_ssm_alpha(self):
        self.check_tensor("blk.0.ssm_alpha.weight")  # 2048 -> 16

    @unittest.skipUnless(FULL, "set GM_FULL=1 for the 248,320-row output head")
    def test_q6_K_output_head(self):
        self.check_tensor("token_embd.weight")


if __name__ == "__main__":
    unittest.main()
