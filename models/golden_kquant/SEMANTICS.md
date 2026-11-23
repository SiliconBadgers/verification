# Golden model semantics

This is what the golden model reproduces, bit for bit, with the source line for every rule. The
sources are llama.cpp at **`f46bc30cb6a7f68a67e34a00061e20a4ad1eff43`**.
`tools/fetch_reference.sh` checks them out sparsely (`ggml/include`, `ggml/src/*`,
`ggml/src/ggml-cpu/`), by default at `~/ref/llama.cpp-f46bc30`. Paths below are relative to
`ggml/src/`.

The model file is `unsloth/Qwen3.5-2B-GGUF` at revision `f6d5376`, `Qwen3.5-2B-Q4_K_M.gguf`,
1,280,835,840 bytes, sha256 `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`.
The same script fetches it and checks the hash.

## 1. What "the reference" is

**The reference is the generic (scalar C) CPU path, one row per dot product.**
- Activation rows are quantized with the `from_float` of the weight's `vec_dot_type`.
- Each output element is one `vec_dot` call over the whole row.
  - In `ggml_compute_forward_mul_mat_one_chunk` (`ggml-cpu/ggml-cpu.c:1165`), results go through
    a `tmp[32]` buffer and `memcpy` with no further arithmetic.
  - Threads split rows, not the arithmetic of an element.

**Excluded paths.** These produce different float rounding, so each is checked against the model
within a tolerance, never bit-exactly:

| Path | Where | Why it differs |
| --- | --- | --- |
| SIMD `vec_dot` (AVX2, AVX-512, NEON) | `ggml-cpu/arch/*/quants.c` | Different lane counts and summation order |
| Two rows per `vec_dot` | `nrows = 2` under `__ARM_FEATURE_MATMUL_INT8` (`ggml-cpu/ggml-cpu.c:276`, 315, 331) | Different kernel. The baseline Mac very likely has these instructions (likely, not verified). |
| llamafile `sgemm` | `GGML_USE_LLAMAFILE` (`ggml-cpu/CMakeLists.txt:82`) | Its own blocking and order |
| Repacked weights (interleaved Q4_K etc.), KleidiAI, AMX | `ggml-cpu/repack.cpp`, `kleidiai/`, `amx/` | Different kernels |

**The C harness used to prove bit-exactness** compiles `ggml-quants.c` and `ggml-cpu/quants.c`:
- with `-DGGML_CPU_GENERIC` (`ggml-cpu/arch-fallback.h:7` maps every `*_generic` to the public
  name);
- with `-O2 -ffp-contract=off`, no `-march`, no fast-math.

`-ffp-contract=off` matters: without it a compiler may turn `d1 * q - m1` or `sums[l] += d * aux32[l]`
into one fused multiply-add. That rounds once instead of twice and changes results.

## 2. Number formats and arithmetic

**fp16 → fp32** (`ggml_compute_fp16_to_fp32`, `ggml-impl.h:396`).
- Exact, including subnormals.
- `GGML_CPU_FP16_TO_FP32` (a NEON lookup table, F16C, or the same function) gives identical
  values.
- Python: `struct.unpack('<e', ...)`.

**fp32 → fp16** (`ggml_compute_fp32_to_fp16`, `ggml-impl.h:419`).
- Used only for the `q8_0` activation scale.
- Round-to-nearest-even, with overflow to infinity. Python's `struct.pack('e')` raises on overflow
  instead, so the model handles that case itself.
- Bit equality with C is a phase 2 test.

**fp32 arithmetic.**
- Every `float` operation in the reference is one IEEE binary32 operation with round-to-nearest-even.
- The model computes each one in double and rounds the result to binary32. That is exact for
  +, −, ×, ÷ (53 ≥ 2·24 + 2).
- No operation is ever fused.

**int → float conversions are all exact here.** Every integer converted to float is below 2²⁴ in
magnitude (bounds in section 5). So the only roundings are the float multiplies and adds listed
below.

**Python's own float errors.** Python raises where C returns IEEE values. The model handles
both cases:
- **Division by zero:** C gives ±∞ (the XOR of the operand signs), or NaN for `0/0`.
- **Overflow when rounding to binary32:** C gives ±∞.

**Integer types.** Quant codes are `int8`/`uint8`, products are `int16` (`aux16`), and accumulators
are `int32`. None overflows at the bounds in section 5.

**Dequantization rounds at most once per value.** All its products are exact in binary32:

| Product | Significant bits | Note |
| --- | ---: | --- |
| `d·sc`, `dmin·m` (fp16 × 6-bit) | ≤ 17 | Exact |
| `(d·sc)·q` for `q4_K`/`q5_K` | ≤ 22 | Exact |
| `(d·sc)·q` for `q6_K` | ≤ 24 | Exact |
| `q·d` for `q8_0` | ≤ 19 | Exact |
| The `− m1` in `q4_K`/`q5_K` | | The only rounding |

So fused multiply-add can't change a dequantized value. Phase 1's planted-FMA bug went
undetected for exactly this reason: it is an equivalent mutant, not a test gap.

The dot products are different. There `d = fp16(x.d) · y.d` already carries the activation
scale's full 24 bits, and `aux32[l]` has up to 24 more, so `d · aux32[l]` rounds. Fusing it into
the following add **does** change results, and phase 3's tests must catch a planted FMA.

## 3. Block layouts

All little-endian, `QK_K = 256` (`ggml-common.h:89`). Offsets are in bytes.

| Type | Bytes | Fields | Source |
| --- | ---: | --- | --- |
| `q4_K` | 144 | `d` fp16 @0, `dmin` fp16 @2, `scales[12]` @4, `qs[128]` @16 | `ggml-common.h:337` |
| `q5_K` | 176 | `d` @0, `dmin` @2, `scales[12]` @4, `qh[32]` @16, `qs[128]` @48 | `ggml-common.h:355` |
| `q6_K` | 210 | `ql[128]` @0, `qh[64]` @128, `scales[16]` int8 @192, `d` fp16 @208 | `ggml-common.h:367` |
| `q8_0` | 34 | `d` fp16 @0, `qs[32]` int8 @2 | `ggml-common.h:255` |
| `q8_K` | 292 | `d` **fp32** @0, `qs[256]` int8 @4, `bsums[16]` int16 @260 | `ggml-common.h:375` |

**The 6-bit scales and mins of `q4_K`/`q5_K`** come from `get_scale_min_k4(j)`
(`ggml-quants.c:880`), for sub-block `j` = 0…7:
- `j < 4`: `sc = s[j] & 63`, `m = s[j+4] & 63`.
- `j ≥ 4`: `sc = (s[j+4] & 0xF) | ((s[j-4] >> 6) << 4)`, `m = (s[j+4] >> 4) | ((s[j] >> 6) << 4)`.

The dot products unpack the same 12 bytes with `kmask1..3` on 32-bit words (`ggml-cpu/quants.c:736`).
The harness checks that the two unpacks agree.

**Element order within a super-block.** Element `e` = 0…255 lies in sub-block `e / 32`
(`q4_K`, `q5_K`) or `e / 16` (`q6_K`).
- **`q4_K`.** For chunk `c` = 0…3 and `l` = 0…31:
  - element `64c + l` is the low nibble of `qs[32c + l]`;
  - element `64c + 32 + l` is the high nibble of the same byte.
- **`q5_K`.** Same nibbles, plus 16 when bit `e / 32` of `qh[l]` is set (`ggml-quants.c:1750`).
- **`q6_K`.** For half `h` = 0…1 and `l` = 0…31, with `L = ql[64h + …]` and `H = qh[32h + l]`:

  | Element | Value (minus 32) |
  | --- | --- |
  | `128h + l` | `(L[l] & 0xF) \| ((H & 3) << 4)` |
  | `128h + 32 + l` | `(L[l+32] & 0xF) \| ((H >> 2 & 3) << 4)` |
  | `128h + 64 + l` | `(L[l] >> 4) \| ((H >> 4 & 3) << 4)` |
  | `128h + 96 + l` | `(L[l+32] >> 4) \| ((H >> 6 & 3) << 4)` |

  The scale index is `e / 16` (`ggml-quants.c:1939`).

## 4. Activation quantization

**`q8_K`**, for `q4_K`/`q5_K`/`q6_K` weights (`quantize_row_q8_K_ref`, `ggml-quants.c:2768`, called
through `quantize_row_q8_K_generic`, `ggml-cpu/quants.c:121`). For each block of 256:
1. `amax` = max |x|, and `max` = the signed `x` at the **first** index reaching it (strict `>`).
2. If `amax == 0`: `d = 0`, all `qs = 0`, and `continue`.
   - **`bsums` is left unwritten** in C.
   - It never affects the result, because `dmin · d = 0`.
   - The model sets it to 0 and the harness compares only `d` and `qs` for such blocks.
3. `iscale = fp32(-127.f / max)`. The negative sign is real: codes come out negated, and so does `d`.
4. `q[j] = min(127, nearest_int(fp32(iscale · x[j])))`. `nearest_int` (`ggml-quants.c:621`) adds
   `12582912.f` (1.5·2²³) in fp32 and reads the low mantissa bits. That rounds to nearest even for
   |v| ≤ 4,194,303, and here |v| ≤ ~127.
5. `bsums[g] = Σ q[16g … 16g+15]` (int16).
6. `d = fp32(1 / iscale)`.

So codes lie in −127…127, never −128, for any finite block that doesn't overflow.

**The pathological case.** In a block of only subnormals, `−127/max` overflows to −∞, and
`nearest_int(−∞)` is −4,194,304. The stored `int8_t` keeps its low byte (0), and `bsums` sums the
stored bytes. The model does the same; this was found by testing.

**`q8_0`**, for `q8_0` weights (`quantize_row_q8_0_ref`, `ggml-quants.c:276`). For each block of 32:
1. `amax` = max |x|.
2. `d = fp32(amax / 127)`, `id = d ? fp32(1/d) : 0`.
3. Store `fp16(d)`.
4. `q[j] = roundf(fp32(x[j] · id))`.

Three traps:
- **This is `roundf`, half away from zero, not `nearest_int`.**
- **`id` uses the fp32 `d`**, while the dot product uses the stored fp16 `d`.
- **`MAX` is `a > b ? a : b`.**
  - A NaN element makes `amax` NaN, and the next element then replaces it.
  - A NaN in the last element leaves `d` NaN.
  - A float that doesn't fit `int8` (or NaN) stores 0 on x86, the low byte of `INT32_MIN`.

## 5. Dot products

`n` is a multiple of the block size. Each formula lists every rounding step in order.

**`q8_0 · q8_0`** (`ggml-cpu/quants.c:451`). `sumf = 0`, then for each block `b`:
1. `sumi = Σ₃₂ x.qs · y.qs` (int, |sumi| ≤ 516,128).
2. `t = fp32(dx · dy)`.
3. `sumf = fp32(sumf + fp32(sumi · t))`.

**`q4_K · q8_K`** (`ggml-cpu/quants.c:696`).
1. `sums[0..7] = 0` once, before all super-blocks. `sumf = 0`.
2. For each super-block `i`:
   1. `aux32[l]`, for `l` = 0…7: the integer sum of `sc[j] · (q8[e] · a[e])` over all `e` with
      `e mod 8 = l`, where `j = e / 32`. These are 8 interleaved lanes, not sub-blocks.
   2. `sumi = Σ_{g<16} bsums[g] · mins[g/2]` (int).
   3. `d = fp32(fp16(x.d) · y.d)`.
   4. For `l` = 0…7: `sums[l] = fp32(sums[l] + fp32(d · aux32[l]))`.
   5. `dmin = fp32(fp16(x.dmin) · y.d)`.
   6. `sumf = fp32(sumf − fp32(dmin · sumi))`.
3. Finally, for `l` = 0…7 in order: `sumf = fp32(sumf + sums[l])`.

**`q5_K · q8_K`** (`ggml-cpu/quants.c:771`). Identical, with `a[e]` = 0…31.

**`q6_K · q8_K`** (`ggml-cpu/quants.c:851`). The same lane structure, with:
- `a[e]` = −32…31;
- an int8 scale per 16 elements;
- no min term, so `sumf = 0 + sums[0] + … + sums[7]`.

**Why the int → float conversions are exact.** Every bound is below 2²⁴ = 16,777,216, and the
`aux16` products fit int16.

| Quantity | Bound |
| --- | --- |
| `q4_K` `aux32` | 8 groups × 4 × 63 × 127 × 15 = 3,840,480 |
| `q5_K` `aux32` | … × 31 = 7,936,992 |
| `q6_K` `aux32` | 16 groups × 2 × 128 × 127 × 32 = 16,646,144 |
| min term `sumi` | 16 × 2,032 × 63 = 2,048,256 |

## 6. What this means for the hardware

- **The arithmetic is integer until one float step per super-block.**
  - Integer sub-block sums times small integer scales, then `d`, `dmin` and the activation scale
    once per 256 elements (once per 32 for `q8_0`).
  - That maps to integer MAC lanes plus a small fp32 unit, far cheaper than today's bf16 scale on
    every 16 elements.
- **To be bit-exact with the generic C, hardware must keep the same eight fp32 lane accumulators**
  (`sums[l]`, lane = element index mod 8). It must carry them across super-blocks and combine them
  in the same order at the end.
  - A different order is fine numerically, but then the match with llama.cpp is within tolerance,
    not exact.
  - **This is a decision to write down before designing the next engine.**
- **The activation side is shared.** The hardware (or the host) has to produce `q8_K` exactly as in
  section 4, including the first-index tie rule and the bsums.

## 7. Status

- [x] Sources checked out at `f46bc30`; model downloaded and sha256 verified.
- [x] Every function the model needs located and specified above.
- [x] Phase 1: block decoders, dequantization, the C harness. Bit-exact (README).
- [x] Phase 2: `q8_K` and `q8_0` activation quantization. Bit-exact (README).
- [x] Phase 3: the four dot products. Bit-exact, with 7/7 planted bugs caught, the FMA included (README).
- [x] Phases 4–7: matrix × vector, the contract mode with its RTL vectors, the accuracy study, and the K-quant-native mode (README, ACCURACY.md).
