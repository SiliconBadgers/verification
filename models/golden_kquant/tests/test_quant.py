"""Phase 2: activation quantization (q8_K, q8_0), bit for bit against llama.cpp (f46bc30).

Every output byte must match, with one documented exception: for an all-zero q8_K block the
reference leaves bsums unwritten (the harness shows its 0xA5 fill), and the dot products
never read them (d = 0). There the test compares d and qs only, and checks the fill.
Stimulus is aimed at each trap in SEMANTICS.md section 4; each must actually occur.
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

from golden.fp import div, f32, mul  # noqa: E402
from golden.quant import quantize_row_q8_0, quantize_row_q8_K, roundf  # noqa: E402

HARNESS = os.environ.get("GM_HARNESS", os.path.expanduser("~/gm_build/gm_harness"))
SEED = int(os.environ.get("GM_SEED", "1"))


def c_quant(type_name, values):
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d, "in.bin"), Path(d, "out.bin")
        src.write_bytes(struct.pack(f"<{len(values)}f", *values))
        subprocess.run([HARNESS, "quant", type_name, str(src), str(dst)], check=True)
        return dst.read_bytes()


def gauss_block(rng, n, scale):
    return [f32(rng.gauss(0.0, 1.0) * scale) for _ in range(n)]


class QuantQ8K(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access(HARNESS, os.X_OK):
            raise unittest.SkipTest(f"no C harness at {HARNESS}; run harness/build.sh")

    def test_q8_K(self):
        rng = random.Random(SEED)
        blocks, tags = [], []

        def add(tag, b):
            assert len(b) == 256
            blocks.append(b)
            tags.append(tag)

        for e in range(-6, 7):
            for _ in range(15):
                add("random", gauss_block(rng, 256, 10.0**e))
        # Ties for nearest_int: the max is -127 (iscale = 1) or 254 (iscale = -0.5).
        add("ties", [-127.0] + [k + 0.5 for k in range(-126, 126)] + [0.5, -0.5, 1.5])
        add("ties", [254.0] + [float(2 * k + 1) for k in range(-127, 127)] + [1.0])
        # The largest magnitude twice, opposite signs: the first index decides the sign.
        for first, second in ((7.0, -7.0), (-7.0, 7.0)):
            b = gauss_block(rng, 256, 1.0)
            b[3], b[200] = first, second
            add("first_index", b)
        add("zero", [0.0] * 256)
        add("zero", [-0.0] * 256)
        b = [0.0] * 256
        b[255] = 3.0
        add("single", b)
        add("subnormal", [f32(rng.choice((-1, 1)) * rng.uniform(1e-45, 1e-39)) for _ in range(256)])
        add("huge", gauss_block(rng, 256, 1e37))
        add("range", [f32(rng.choice((1e30, -1e30, 1e-30, 3.0))) for _ in range(256)])
        b = gauss_block(rng, 256, 1.0)
        b[17] = math.inf
        add("inf", b)
        b = gauss_block(rng, 256, 1.0)
        b[17] = math.nan
        add("nan", b)

        values = [v for b in blocks for v in b]
        want = c_quant("q8_K", values)
        got = quantize_row_q8_K(values)
        self.assertEqual(len(got), len(want))
        ties = 0
        for i, tag in enumerate(tags):
            w, g = want[292 * i : 292 * i + 292], got[292 * i : 292 * i + 292]
            if tag == "zero":
                self.assertEqual(g[:260], w[:260], f"block {i} ({tag}): d or qs")
                self.assertEqual(w[260:], b"\xa5" * 32, "C leaves bsums unwritten")
            else:
                self.assertEqual(g, w, f"block {i} ({tag})")
            if tag == "ties":
                (d,) = struct.unpack_from("<f", w, 0)
                iscale = div(1.0, d)
                ties += sum(1 for v in blocks[i] if abs(mul(iscale, v) % 1.0) == 0.5)
        self.assertGreater(ties, 200, "exact .5 ties must occur")


class QuantQ80(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access(HARNESS, os.X_OK):
            raise unittest.SkipTest(f"no C harness at {HARNESS}; run harness/build.sh")

    def test_q8_0(self):
        rng = random.Random(SEED)
        blocks, tags = [], []

        def add(tag, b):
            assert len(b) == 32
            blocks.append(b)
            tags.append(tag)

        for e in range(-6, 7):
            for _ in range(40):
                add("random", gauss_block(rng, 32, 10.0**e))
        # amax = 127 gives d = 1, id = 1: roundf ties go away from zero.
        add("ties", [127.0] + [k + 0.5 for k in range(-16, 15)])
        add("ties", [-127.0] + [-(k + 0.5) for k in range(-16, 15)])
        add("fp16_overflow", gauss_block(rng, 32, 1e7))  # d > 65504
        add("fp16_subnormal", gauss_block(rng, 32, 1e-4))
        add("fp16_zero", gauss_block(rng, 32, 1e-12))
        add("zero", [0.0] * 32)
        add("zero", [-0.0] * 32)
        b = gauss_block(rng, 32, 1.0)
        b[10] = math.nan  # MAX(amax, NaN) is NaN; the next value replaces it
        add("nan_mid", b)
        b = gauss_block(rng, 32, 1.0)
        b[31] = math.nan  # NaN last: amax stays NaN
        add("nan_last", b)

        values = [v for b in blocks for v in b]
        want = c_quant("q8_0", values)
        got = quantize_row_q8_0(values)
        self.assertEqual(len(got), len(want))
        seen = set()
        for i, tag in enumerate(tags):
            w, g = want[34 * i : 34 * i + 34], got[34 * i : 34 * i + 34]
            self.assertEqual(g, w, f"block {i} ({tag})")
            (dh,) = struct.unpack_from("<H", w, 0)
            if dh & 0x7FFF == 0x7C00:
                seen.add("fp16_inf")
            elif 0 < dh & 0x7FFF < 0x0400:
                seen.add("fp16_subnormal")
            if tag == "ties":
                seen.add("ties")
                self.assertTrue(any(roundf(v) != round(v) for v in blocks[i][1:]),
                                "ties where roundf and round-to-even differ")
        self.assertEqual(seen, {"fp16_inf", "fp16_subnormal", "ties"})


if __name__ == "__main__":
    unittest.main()
