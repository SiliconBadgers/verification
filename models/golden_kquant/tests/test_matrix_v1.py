"""The proposed-spec additions (golden/matrix_v1.py): chained state, partial scaled K, M/N
masks, output encodings 0-4 and the version-1 record. Directed cases for ties, subnormals,
saturation and flags, plus cross-checks against hwmode.py and the host's own IEEE rounding.
"""

import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.fp import f32, f32_bits, f32_to_f16  # noqa: E402
from golden.hwmode import BLOCK_K, FX_MAX, FX_MIN, scaled_element, unscaled_element  # noqa: E402
from golden.matrix_v1 import (ELEMENT_BYTES, F16_NAN, F32_NAN, FMT_FP16, FMT_FP32,  # noqa: E402
                              FMT_INT8, FMT_INT32, FMT_LEGACY, Native, command, convert,
                              decode_record, encode_record, integer_step, output_bytes,
                              round_float, scaled_step)

ONE = 0x3F80  # bf16 1.0
NAN_BF16 = 0x7FC0


def fx(value, ovf=False, nan=False):
    return Native(True, value, ovf, nan)


def i(value):
    return Native(False, value)


def rand_scale(rng):
    return rng.choice([ONE, 0x3F00, 0x4000, 0x3E80, 0xBF80, 0x0000, 0x3C00, 0x4280])


class Accumulation(unittest.TestCase):
    def test_matches_hwmode_on_whole_blocks(self):
        rng = random.Random(1)
        for _ in range(50):
            g = rng.randrange(1, 4)
            k = g * BLOCK_K
            a = [rng.randrange(-128, 128) for _ in range(k)]
            b = [rng.randrange(-8, 8) for _ in range(k)]
            sa = [rand_scale(rng) for _ in range(g)]
            sb = [rand_scale(rng) for _ in range(g)]
            got = convert(scaled_step(None, a, b, sa, sb), FMT_LEGACY)
            self.assertEqual(got, scaled_element(a, b, sa, sb))
            self.assertEqual(convert(integer_step(None, a, b), FMT_LEGACY),
                             unscaled_element(a, b))

    def test_partial_block_is_zero_padding(self):
        rng = random.Random(2)
        for k in (1, 15, 17, 20, 31, 33):
            g = -(-k // BLOCK_K)
            a = [rng.randrange(-128, 128) for _ in range(k)]
            b = [rng.randrange(-128, 128) for _ in range(k)]
            sa = [rand_scale(rng) for _ in range(g)]
            sb = [rand_scale(rng) for _ in range(g)]
            pad = g * BLOCK_K - k
            self.assertEqual(scaled_step(None, a, b, sa, sb),
                             scaled_step(None, a + [0] * pad, b + [0] * pad, sa, sb))

    def test_scale_count_must_be_ceiling(self):
        with self.assertRaises(ValueError):
            scaled_step(None, [1] * 17, [1] * 17, [ONE], [ONE])

    def test_chain_split_at_block_boundary_equals_one_command(self):
        rng = random.Random(3)
        k = 3 * BLOCK_K
        a = [rng.randrange(-128, 128) for _ in range(k)]
        b = [rng.randrange(-128, 128) for _ in range(k)]
        sa = [rand_scale(rng) for _ in range(3)]
        sb = [rand_scale(rng) for _ in range(3)]
        first = scaled_step(None, a[:BLOCK_K], b[:BLOCK_K], sa[:1], sb[:1])
        both = scaled_step(first, a[BLOCK_K:], b[BLOCK_K:], sa[1:], sb[1:])
        self.assertEqual(both, scaled_step(None, a, b, sa, sb))
        first = integer_step(None, a[:5], b[:5])
        self.assertEqual(integer_step(first, a[5:], b[5:]), integer_step(None, a, b))

    def test_chain_split_inside_a_block_rounds_twice(self):
        # Splitting a block between commands adds a rounding point (spec): 3 * 2^-25 and
        # 3 * 2^-25 round to 2 and 2 separately but 6 * 2^-25 is exactly 3 in one block.
        sa, sb = [0x3380], [0x3F00]  # 2^-24, 0.5
        one = scaled_step(None, [3, 3], [1, 1], sa, sb)
        split = scaled_step(scaled_step(None, [3], [1], sa, sb), [3], [1], sa, sb)
        self.assertEqual(one.value, 3)
        self.assertEqual(split.value, 4)

    def test_nan_and_overflow_are_sticky_across_commands(self):
        x = scaled_step(None, [1], [1], [NAN_BF16], [ONE])
        x = scaled_step(x, [1], [1], [ONE], [ONE])
        self.assertTrue(x.nan)
        y = scaled_step(None, [-128] * 16, [-128] * 16, [0x7F00], [0x7F00])
        y = scaled_step(y, [1], [1], [ONE], [ONE])
        self.assertTrue(y.ovf)
        self.assertEqual(y.value, FX_MAX)


class Masks(unittest.TestCase):
    def test_inactive_lanes_are_zero_whatever_they_hold(self):
        rng = random.Random(4)
        rows = cols = 8
        k = 20
        m, n = 3, 5
        a = [[rng.randrange(-128, 128) for _ in range(k)] for _ in range(rows)]
        b = [[rng.randrange(-8, 8) for _ in range(cols)] for _ in range(k)]
        g = 2
        sa = [[ONE if r < m else NAN_BF16 for _ in range(g)] for r in range(rows)]
        sb = [[ONE if c < n else NAN_BF16 for c in range(cols)] for _ in range(g)]
        st = command(None, a, b, sa, sb, m, n, scaled=True)
        for r in range(rows):
            for c in range(cols):
                x = st[r][c]
                if r < m and c < n:
                    self.assertFalse(x.nan)
                    self.assertEqual(x.value, sum(a[r][kk] * b[kk][c] for kk in range(k)) << 24)
                else:
                    self.assertEqual(x, Native(True))
        for fmt in range(5):
            data = output_bytes(st, fmt, m, n, frac=3, mul=7, shift=30)
            self.assertEqual(len(data), ELEMENT_BYTES[fmt] * rows * cols)
            eb = ELEMENT_BYTES[fmt]
            for r in range(rows):
                for c in range(cols):
                    if not (r < m and c < n):
                        off = eb * (r * cols + c)
                        self.assertEqual(data[off : off + eb], bytes(eb))

    def test_packing_is_little_endian_row_major(self):
        st = [[i(r * 4 + c) for c in range(4)] for r in range(2)]
        self.assertEqual(output_bytes(st, FMT_INT8, mul=1)[:8], bytes(range(8)))
        self.assertEqual(output_bytes(st, FMT_LEGACY)[4:8], b"\x01\x00\x00\x00")


class FloatFormats(unittest.TestCase):
    def test_round_float_matches_host_ieee(self):
        rng = random.Random(5)
        for _ in range(4000):
            a = rng.randrange(-(1 << 47), 1 << 47) >> rng.randrange(0, 48)
            if a == 0:
                continue
            v = a / (1 << 24)  # exact in double
            self.assertEqual(round_float(Fraction(a, 1 << 24), 8, 23), f32_bits(f32(v)))
            self.assertEqual(round_float(Fraction(a, 1 << 24), 5, 10), f32_to_f16(v))

    def test_fp16_subnormals_ties_and_overflow(self):
        self.assertEqual(convert(fx(1), FMT_FP16), 0x0001)  # 2^-24, smallest subnormal
        self.assertEqual(convert(fx(-3), FMT_FP16), 0x8003)
        self.assertEqual(convert(fx(1 << 10), FMT_FP16), 0x0400)  # 2^-14, smallest normal
        # 2^-13 + 2^-24: the ULP at 2^-13 is 2^-23, so a tie, kept even
        self.assertEqual(convert(fx((1 << 11) + 1), FMT_FP16), 0x0800)
        self.assertEqual(convert(fx((1 << 11) + 3), FMT_FP16), 0x0802)  # tie, rounds up to even
        self.assertEqual(convert(i(65504), FMT_FP16), 0x7BFF)
        self.assertEqual(convert(i(65519), FMT_FP16), 0x7BFF)
        self.assertEqual(convert(i(65520), FMT_FP16), 0x7C00)  # rounds to infinity
        self.assertEqual(convert(i(-70000), FMT_FP16), 0xFC00)
        self.assertEqual(convert(i(2049), FMT_FP16), 0x6800)  # 2049: tie -> 2048
        self.assertEqual(convert(i(2051), FMT_FP16), 0x6802)  # 2051: tie -> 2052

    def test_fp16_is_direct_not_through_fp32(self):
        # 1 + 2^-11 is an FP16 tie (half its ULP at 1.0), kept at 1.0.
        acc = (1 << 24) + (1 << 13)
        self.assertEqual(convert(fx(acc), FMT_FP16), 0x3C00)
        # 1 + 2^-11 + 2^-24 is just above that tie, so it rounds up directly. Through FP32
        # it would first round to 1 + 2^-11 (2^-24 is half an FP32 ULP, a tie to even) and
        # then down to 1.0: the double rounding the spec rules out.
        acc_up = acc + 1
        self.assertEqual(convert(fx(acc_up), FMT_FP16), 0x3C01)
        self.assertEqual(f32_to_f16(f32(acc_up / (1 << 24))), 0x3C00)

    def test_float_flags(self):
        for fmt, nan, inf in ((FMT_FP32, F32_NAN, 0x7F800000), (FMT_FP16, F16_NAN, 0x7C00),
                              (FMT_LEGACY, F32_NAN, 0x7F800000)):
            self.assertEqual(convert(fx(5, nan=True), fmt), nan)
            self.assertEqual(convert(fx(5, ovf=True, nan=True), fmt), nan)
            self.assertEqual(convert(fx(FX_MAX, ovf=True), fmt), inf)
            sign = 0x80000000 if inf == 0x7F800000 else 0x8000
            self.assertEqual(convert(fx(FX_MIN, ovf=True), fmt), sign | inf)
            self.assertEqual(convert(fx(0), fmt), 0)

    def test_fp32_of_integer_commands_rounds(self):
        self.assertEqual(convert(i((1 << 24) + 1), FMT_FP32), 0x4B800000)  # tie -> even
        self.assertEqual(convert(i((1 << 24) + 3), FMT_FP32), 0x4B800002)
        self.assertEqual(convert(i(-(1 << 31)), FMT_FP32), 0xCF000000)
        self.assertEqual(convert(i(-1), FMT_LEGACY), 0xFFFFFFFF)  # legacy integer is int32


class IntegerFormats(unittest.TestCase):
    def test_int32_fixed(self):
        half = 1 << 23
        self.assertEqual(convert(fx(3 * half), FMT_INT32, frac=0), 2)  # 1.5 -> 2
        self.assertEqual(convert(fx(5 * half), FMT_INT32, frac=0), 2)  # 2.5 -> 2
        self.assertEqual(convert(fx(-5 * half), FMT_INT32, frac=0), (-2) & 0xFFFFFFFF)
        self.assertEqual(convert(fx(1), FMT_INT32, frac=24), 1)
        self.assertEqual(convert(fx(1), FMT_INT32, frac=31), 128)
        self.assertEqual(convert(fx(FX_MAX), FMT_INT32, frac=31), 0x7FFFFFFF)
        self.assertEqual(convert(i(1), FMT_INT32, frac=31), 0x7FFFFFFF)
        self.assertEqual(convert(i(-1), FMT_INT32, frac=31), 0x80000000)
        self.assertEqual(convert(i(-2), FMT_INT32, frac=31), 0x80000000)
        self.assertEqual(convert(i(-123), FMT_INT32, frac=0), (-123) & 0xFFFFFFFF)
        self.assertEqual(convert(fx(5, nan=True), FMT_INT32, frac=4), 0)
        self.assertEqual(convert(fx(FX_MIN, ovf=True), FMT_INT32), 0x80000000)
        self.assertEqual(convert(fx(FX_MAX, ovf=True), FMT_INT32), 0x7FFFFFFF)

    def test_int8_requant(self):
        self.assertEqual(convert(i(127), FMT_INT8, mul=1), 127)
        self.assertEqual(convert(i(128), FMT_INT8, mul=1), 127)
        self.assertEqual(convert(i(-128), FMT_INT8, mul=1), (-127) & 0xFF)
        self.assertEqual(convert(i(3), FMT_INT8, mul=1, shift=1), 2)  # 1.5 -> 2
        self.assertEqual(convert(i(5), FMT_INT8, mul=1, shift=1), 2)  # 2.5 -> 2
        self.assertEqual(convert(i(-5), FMT_INT8, mul=1, shift=1), (-2) & 0xFF)
        self.assertEqual(convert(i(1000), FMT_INT8, mul=0), 0)
        # The full 80-bit product: (2^47 - 1)(2^32 - 1) / 2^79 is just below 1 -> 1
        self.assertEqual(convert(fx(FX_MAX), FMT_INT8, mul=0xFFFFFFFF, shift=79), 1)
        self.assertEqual(convert(fx(FX_MIN), FMT_INT8, mul=0xFFFFFFFF, shift=79), (-1) & 0xFF)
        self.assertEqual(convert(fx(FX_MIN), FMT_INT8, mul=0xFFFFFFFF, shift=80), 0)  # < 1/2
        self.assertEqual(convert(fx(FX_MIN), FMT_INT8, mul=0xFFFFFFFF, shift=127), 0)
        # Scaled code with the 24 fractional bits folded into the shift: 2.5 -> 2
        self.assertEqual(convert(fx(5 << 23), FMT_INT8, mul=1, shift=24), 2)
        self.assertEqual(convert(fx(5, nan=True), FMT_INT8, mul=1), 0)
        self.assertEqual(convert(fx(FX_MIN, ovf=True), FMT_INT8, mul=1), (-127) & 0xFF)
        self.assertEqual(convert(fx(FX_MAX, ovf=True), FMT_INT8, mul=0), 127)

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            convert(i(1), 5)


class Record(unittest.TestCase):
    def test_round_trip(self):
        rng = random.Random(6)
        for _ in range(200):
            f = dict(a_addr=rng.getrandbits(32), b_addr=rng.getrandbits(32),
                     c_addr=rng.getrandbits(32), sa_addr=rng.getrandbits(32),
                     sb_addr=rng.getrandbits(32), m=rng.getrandbits(16), n=rng.getrandbits(16),
                     k=rng.getrandbits(16), clear=rng.getrandbits(1),
                     write=rng.getrandbits(1), int4=rng.getrandbits(1),
                     scaled=rng.getrandbits(1), fmt=rng.randrange(5), frac=rng.randrange(32),
                     mul=rng.getrandbits(32), shift=rng.getrandbits(7),
                     mem_wait=rng.getrandbits(32), vec_wait=rng.getrandbits(32))
            got, bad = decode_record(encode_record(**f))
            self.assertFalse(bad)
            for key, val in f.items():
                self.assertEqual(got[key], val, key)

    def test_word_layout(self):
        rec = encode_record(m=3, n=5, k=0x1234, clear=1, write=0, fmt=FMT_FP16, frac=7)
        w9 = (rec >> (32 * 9)) & 0xFFFFFFFF
        self.assertEqual(rec & 0xFFFFFFFF, 0x0101)
        self.assertEqual((rec >> (32 * 8)) & 0xFFFFFFFF, 0x00050003)
        self.assertEqual(w9, 0x1234 | 1 << 18 | 3 << 22 | 7 << 25)

    def test_malformed(self):
        good = encode_record()
        self.assertFalse(decode_record(good)[1])
        self.assertEqual(decode_record(encode_record(trans_b=1))[0]["trans_b"], 1)
        cases = [encode_record(kind=2), encode_record(version=2), encode_record(fmt=5),
                 encode_record(frac=32), encode_record(trans_a=1), encode_record(trans_b=1),
                 good | 1 << 4, good | 1 << 16, good | 1 << (32 * 9 + 31),
                 good | 1 << (32 * 11 + 7), good | 1 << (32 * 12), good | 1 << 511]
        for rec in cases:
            self.assertTrue(decode_record(rec)[1], hex(rec))


if __name__ == "__main__":
    unittest.main()
