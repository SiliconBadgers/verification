"""Phase 1: block decoding and dequantization, bit for bit against llama.cpp (f46bc30).

Needs the C harness (harness/build.sh) and, for the real-tensor test, the pinned GGUF:
  GM_HARNESS  default ~/gm_build/gm_harness
  GM_GGUF     default ~/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf
Run from the golden_model directory: python3 -m unittest discover -s tests -v

Every value must have the same binary32 bits as the C result, signed zeros included. The
one exception: two NaNs match whatever their payloads (payload bits are platform noise).
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

from golden.blocks import (TYPES, dequantize, get_scale_min_k4,  # noqa: E402
                           get_scale_min_kmask)
from golden.fp import f32_bits  # noqa: E402
from golden.gguf import GGUF  # noqa: E402

HARNESS = os.environ.get("GM_HARNESS", os.path.expanduser("~/gm_build/gm_harness"))
MODEL = os.environ.get(
    "GM_GGUF", os.path.expanduser("~/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf"))
SEED = int(os.environ.get("GM_SEED", "1"))

# fp16 scale patterns that must appear: subnormal, zero, -0, negative, largest, inf, NaN
SPECIAL_F16 = [0x0001, 0x03FF, 0x0000, 0x8000, 0xBC00, 0x7BFF, 0x7C00, 0x7E00]


def c_dequant(type_name, data):
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d, "in.bin"), Path(d, "out.bin")
        src.write_bytes(data)
        subprocess.run([HARNESS, "deq", type_name, str(src), str(dst)], check=True)
        raw = dst.read_bytes()
    return list(struct.unpack(f"<{len(raw) // 4}I", raw))


def assert_same(test, type_name, data, label):
    want = c_dequant(type_name, data)
    got = dequantize(type_name, data)
    test.assertEqual(len(got), len(want), label)
    bad = []
    for i, (g, w) in enumerate(zip(got, want)):
        gb = f32_bits(g)
        w_nan = (w & 0x7F800000) == 0x7F800000 and (w & 0x007FFFFF) != 0
        if (math.isnan(g) and w_nan) or gb == w:
            continue
        bad.append(f"element {i}: model {gb:08x} C {w:08x}")
        if len(bad) == 5:
            break
    test.assertFalse(bad, f"{label}: " + "; ".join(bad))
    return len(got)


def random_block(rng, type_name, f16):
    _, _, size = TYPES[type_name]
    b = bytearray(rng.getrandbits(8) for _ in range(size))
    if type_name in ("q4_K", "q5_K"):
        struct.pack_into("<HH", b, 0, f16(), f16())
    elif type_name == "q6_K":
        struct.pack_into("<H", b, 208, f16())
    else:
        struct.pack_into("<H", b, 0, f16())
    return bytes(b)


class Dequant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access(HARNESS, os.X_OK):
            raise unittest.SkipTest(f"no C harness at {HARNESS}; run harness/build.sh")

    def test_random_blocks(self):
        rng = random.Random(SEED)
        used = set()

        def f16():
            if rng.random() < 0.15:
                h = rng.choice(SPECIAL_F16)
                used.add(h)
                return h
            # normal values of either sign around the sizes real scales have
            return rng.getrandbits(1) << 15 | rng.randrange(0x0400, 0x7C00)

        for type_name in ("q4_K", "q5_K", "q6_K", "q8_0"):
            data = b"".join(random_block(rng, type_name, f16) for _ in range(1500))
            n = assert_same(self, type_name, data, f"random {type_name}")
            self.assertGreater(n, 0)
        self.assertEqual(used, set(SPECIAL_F16), "every special fp16 scale must occur")

    def test_adversarial_blocks(self):
        blocks = {t: [] for t in ("q4_K", "q5_K", "q6_K", "q8_0")}
        for scale_byte in (0x00, 0x3F, 0x40, 0x80, 0xC0, 0xFF):
            for code_byte in (0x00, 0x0F, 0xF0, 0xFF):
                for d in (0x3C00, 0x0001, 0x7BFF):
                    s = bytes([scale_byte] * 12)
                    q = bytes([code_byte] * 128)
                    blocks["q4_K"].append(struct.pack("<HH", d, d) + s + q)
                    blocks["q5_K"].append(struct.pack("<HH", d, d) + s + bytes([code_byte] * 32) + q)
                    blocks["q6_K"].append(q + bytes([code_byte] * 64) + bytes([scale_byte] * 16)
                                          + struct.pack("<H", d))
                    blocks["q8_0"].append(struct.pack("<H", d) + bytes([code_byte] * 32))
        for t, bs in blocks.items():
            assert_same(self, t, b"".join(bs), f"adversarial {t}")

    def test_real_tensors(self):
        if not os.path.exists(MODEL):
            self.skipTest(f"no model at {MODEL}")
        g = GGUF(MODEL)
        picks = {"q4_K": "blk.0.ffn_gate.weight", "q5_K": "blk.0.attn_qkv.weight",
                 "q6_K": "token_embd.weight", "q8_0": "blk.0.ssm_alpha.weight"}
        for t, name in picks.items():
            tensor = g.tensors[name]
            self.assertEqual(tensor.type_name, t)
            rows = sorted({0, 1, tensor.rows // 2, tensor.rows - 1})
            data = b"".join(g.read_rows(name, r, 1) for r in rows)
            assert_same(self, t, data, f"{name} rows {rows}")


class ScaleUnpack(unittest.TestCase):
    def test_kmask_matches_get_scale_min_k4(self):
        rng = random.Random(SEED)
        patterns = [bytes([b] * 12) for b in range(256)]
        patterns += [bytes(rng.getrandbits(8) for _ in range(12)) for _ in range(20000)]
        for s in patterns:
            sc, mn = get_scale_min_kmask(s)
            ref = [get_scale_min_k4(j, s) for j in range(8)]
            self.assertEqual(sc, [r[0] for r in ref], s.hex())
            self.assertEqual(mn, [r[1] for r in ref], s.hex())


if __name__ == "__main__":
    unittest.main()
