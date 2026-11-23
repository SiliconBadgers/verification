"""Phase 5: the matrix unit's arithmetic contract (golden/hwmode.py), directed cases.

Real-tensor agreement with the RTL is checked by the RTL itself (bpu_sa_sram_wrapper_golden_tb
on the vectors tools/export_rtl_vectors.py writes). These cases cover what real data never
reaches: special scales, saturation to each infinity, rounding ties, the unscaled wrap and
the requantization rule. They mirror the special commands of bpu_sa_sram_wrapper_tb.
"""

import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.fp import f32, f32_bits  # noqa: E402
from golden.hwmode import (BLOCK_K, F32_NAN, FX_MAX, bf16_value, contribution,  # noqa: E402
                           f32_to_bf16, requantize, scaled_element, unscaled_element)

ONE = 0x3F80  # bf16 1.0
TWO16 = 0x4780  # bf16 2^16
K = 2 * BLOCK_K


class Contract(unittest.TestCase):
    def test_plain_block_is_exact(self):
        rng = random.Random(1)
        a = [rng.randrange(-128, 128) for _ in range(K)]
        b = [rng.randrange(-8, 8) for _ in range(K)]
        got = scaled_element(a, b, [ONE, ONE], [ONE, ONE])
        self.assertEqual(got, f32_bits(f32(sum(x * y for x, y in zip(a, b)))))

    def test_nan_scale(self):
        a, b = [1] * K, [1] * K
        self.assertEqual(scaled_element(a, b, [0x7FC0, ONE], [ONE, ONE]), F32_NAN)
        self.assertEqual(scaled_element(a, b, [ONE, ONE], [ONE, 0x7F80]), F32_NAN)  # inf scale

    def test_zero_and_subnormal_scales_count_as_zero(self):
        a, b = [3] * K, [5] * K
        self.assertEqual(scaled_element(a, b, [0x0000, 0x0001], [ONE, ONE]), 0)

    def test_saturation_to_each_infinity(self):
        # The wrapper TB's special command: every operand at its negative limit, 2^16 scales.
        a, b = [-128] * K, [-8] * K
        self.assertEqual(scaled_element(a, b, [TWO16] * 2, [TWO16] * 2), 0x7F800000)
        self.assertEqual(scaled_element(a, b, [TWO16] * 2, [0xC780] * 2), 0xFF800000)

    def test_contribution_overflow_sign(self):
        c, ovf, bad = contribution(-1, 0x7F00, 0x7F00)  # 2^127 * 2^127: far out of range
        self.assertTrue(ovf)
        self.assertFalse(bad)
        self.assertEqual(c, -(FX_MAX + 1))

    def test_round_half_even(self):
        # isum = 3, scales 2^-24 * 2^-1 -> 3 * 2^-25 * 2^24 = 1.5 -> 2; isum = 5 -> 2.5 -> 2
        s_a = f32_to_bf16(2.0 ** -24)
        s_b = f32_to_bf16(0.5)
        self.assertEqual(contribution(3, s_a, s_b)[0], 2)
        self.assertEqual(contribution(5, s_a, s_b)[0], 2)
        self.assertEqual(contribution(-5, s_a, s_b)[0], -2)
        self.assertEqual(contribution(-3, s_a, s_b)[0], -2)

    def test_unscaled_wraps_to_acc_width(self):
        a, b = [127] * 4, [127] * 4
        self.assertEqual(unscaled_element(a, b), 4 * 127 * 127)
        self.assertEqual(unscaled_element([-1], [1]), 0xFFFFFFFF)
        self.assertEqual(unscaled_element([1 << 15] * 2, [1 << 16] * 2, acc_w=32), 0)


class Requantize(unittest.TestCase):
    def test_ranges_and_scales(self):
        rng = random.Random(2)
        x = [f32(rng.gauss(0.0, 1.0)) for _ in range(4 * BLOCK_K)] + [0.0] * BLOCK_K
        for bits, q in ((4, 7), (8, 127)):
            codes, scales = requantize(x, bits)
            self.assertEqual(len(codes), len(x))
            self.assertEqual(len(scales), len(x) // BLOCK_K)
            self.assertTrue(all(-q <= c <= q for c in codes))
            self.assertEqual(scales[-1], 0)  # the all-zero block
            for g, s in enumerate(scales[:-1]):
                block = x[g * BLOCK_K : (g + 1) * BLOCK_K]
                self.assertIn(q, [abs(c) for c in codes[g * BLOCK_K : (g + 1) * BLOCK_K]])
                # every code is the nearest grid point to its value
                for v, c in zip(block, codes[g * BLOCK_K : (g + 1) * BLOCK_K]):
                    self.assertLessEqual(abs(Fraction(v) - c * bf16_value(s)), bf16_value(s) / 2)

    def test_bf16_rounding(self):
        self.assertEqual(f32_to_bf16(1.0), 0x3F80)
        self.assertEqual(f32_to_bf16(f32(1.0 + 2.0 ** -8)), 0x3F80)  # tie -> even
        self.assertEqual(f32_to_bf16(f32(1.0 + 3 * 2.0 ** -8)), 0x3F82)  # tie -> even, up
        self.assertEqual(f32_to_bf16(f32(-2.0)), 0xC000)


if __name__ == "__main__":
    unittest.main()
