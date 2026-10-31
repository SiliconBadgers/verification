# Golden model: llama.cpp's quantized matrix arithmetic (Qwen3.5-2B Q4_K_M)

A bit-exact Python model of what llama.cpp computes for every matrix weight of the team's
target model, plus a model of the matrix unit's own arithmetic contract. Standard library only.

| It reproduces | Bit-exact against |
| --- | --- |
| Dequantization of `q4_K`, `q5_K`, `q6_K`, `q8_0` | llama.cpp's reference functions, compiled from the pinned sources |
| Activation quantization to `q8_K` and `q8_0` | the same |
| The four dot products, and matrix × vector for one token | the same, on whole real tensors, the 248,320-row output head included |
| The matrix unit's arithmetic contract (INT8/INT4, bf16 scales per 16, Q23.24, binary32) | the RTL: `bpu_sa_sram_wrapper_golden_tb` in SiliconBadgers/rtl reproduces its real-tensor vectors bit for bit |

[SEMANTICS.md](SEMANTICS.md) is the specification, with a source line for every rule.
[ACCURACY.md](ACCURACY.md) compares the arithmetic of llama.cpp and the matrix unit on real
tensors.

## What it is a model of, and how it differs

- **The reference is llama.cpp `f46bc30`'s generic (scalar C) CPU path,** one row per dot
  product. The pin is the software team's baseline
  (`software/experiments/llama-cpp/2026-09-22/manifest.json`).
  - **Not bit-exact against SIMD or repacked kernels.** llama.cpp's SIMD kernels (AVX2, NEON,
    int8 matmul) and its repacked or llamafile paths add floats in other orders, so they agree
    with this model only within a tolerance. The recorded Mac baseline ran such kernels.
  - **Exact float arithmetic.** Every binary32 operation is computed in double and rounded once.
    That is exact for + − × ÷, with no fused multiply-add, matching a C build with
    `-ffp-contract=off`.
- **The contract mode (`golden/hwmode.py`) models the matrix unit as built,** not llama.cpp. It
  is our own spec implemented twice (here and in the RTL). Agreement catches implementation
  bugs, not a misunderstanding of the spec shared by both. The rule that requantizes model
  tensors into the unit's format is an **assumption**, not a team decision.
- **Scope.** Only matrix weights. Attention over the KV cache, the DeltaNet state update, norms
  and activations are not modeled.

## Layout

| Path | What |
| --- | --- |
| `golden/fp.py` | Exact binary32 and binary16 operations, IEEE where Python would raise |
| `golden/blocks.py` | Block layouts, decoders, dequantization |
| `golden/quant.py` | Activation quantization: `q8_K` (`nearest_int`) and `q8_0` (`roundf`) |
| `golden/dot.py` | The four dot products: 8 interleaved lanes, the min term, C's order |
| `golden/matvec.py` | Matrix × vector for one token |
| `golden/hwmode.py` | The matrix unit's contract, and the requantization rule (an assumption) |
| `golden/gguf.py` | Minimal GGUF reader |
| `harness/` | C harness that runs llama.cpp's own reference functions |
| `tests/` | Bit-exact tests against the harness, plus directed tests of the contract |
| `tools/fetch_reference.sh` | Fetches the pinned llama.cpp sources and model file (sha256-checked), outside the repo |
| `tools/export_rtl_vectors.py` | Writes the RTL's `tb/compute/Matrix_Unit/bpu_sa_golden_vectors_pkg.sv` |
| `tools/accuracy_study.py` | Writes `ACCURACY.md` |
| `tools/inspect_gguf.py` | Summarizes a model file |

## Running

Linux or WSL, with Python 3.11+, gcc, git and curl. From this directory:

```sh
bash tools/fetch_reference.sh        # once: ~/ref/llama.cpp-f46bc30 (6 MB), ~/ref/models/... (1.28 GB)
bash harness/build.sh                # builds ~/gm_build/gm_harness from the pinned sources
python3 -m unittest discover -s tests -v
```

**From the repository root,** `make test-models` runs the same tests.

**When pieces are missing:**
- Without the harness, the bit-exact tests skip.
- Without the model file, the real-tensor tests skip.
- The contract tests always run.

**Environment variables:**
- `GM_HARNESS`, `GM_GGUF`: override the default paths.
- `GM_SEED`: changes the random stimulus.
- `GM_FULL=1`: adds the full output head (about 2 minutes).

**Regenerating the RTL vectors** (`RTL` is a checkout of SiliconBadgers/rtl):

```sh
python3 tools/export_rtl_vectors.py ~/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf \
  "$RTL/tb/compute/Matrix_Unit/bpu_sa_golden_vectors_pkg.sv"
```

The output is deterministic and already Verible-formatted. The RTL runs it as `wrap_8x8_golden`
in `tb/compute/Matrix_Unit/run_tests.sh`.

## Evidence (2026-10-22/23)

All of this is local: Python 3.14, gcc 15.2, llama.cpp `f46bc30` built with `-DGGML_CPU_GENERIC
-ffp-contract=off`. Each phase also had bugs planted in the model; every one was caught, except
one that is provably equivalent (noted below).

| Phase | Result |
| --- | --- |
| 1 Dequantization | Bit-exact on 1,500 random blocks per format (salted with subnormal, ±0, infinite and NaN scales), edge-case blocks, and real rows. Bugs planted: 2/2 caught. A planted FMA is provably equivalent: every dequantization product is exact (SEMANTICS §2). |
| 2 Activation quantization | Byte-exact on 207 `q8_K` and 529 `q8_0` blocks, aimed at each trap: ties, first-index max, fp16 overflow and subnormals, NaN inside `MAX`, overflowing scales. Bugs planted: 6/6 caught. |
| 3 Dot products | Bit-exact for every format on random, raw-random, special-scale, directed and real rows. Bugs planted: 7/7 caught, including the FMA, which does change results here. |
| 4 Matrix × vector | Whole real tensors (q4_K 2048 × 2048, q5_K 6144 rows, q6_K with K = 6144, q8_0) and the whole output head (248,320 rows): bit-exact. |
| 5 Contract mode | The RTL reproduces all 256 C elements of the exported real-tensor vectors bit for bit: INT4 and INT8 tiles with K = 2048, a chained split, an unscaled tile, 3 seeds under arbiter stalls. Directed tests cover special scales, saturation to ±∞ and ties. |
| 6 Accuracy | `ACCURACY.md`. INT8 costs nothing; symmetric INT4 has about 12× llama.cpp's error on Q4_K weights. |

## Provenance

- **llama.cpp** `f46bc30cb6a7f68a67e34a00061e20a4ad1eff43`.
- **Model:** `unsloth/Qwen3.5-2B-GGUF` revision `f6d5376`, `Qwen3.5-2B-Q4_K_M.gguf`, 1,280,835,840
  bytes, sha256 `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`.
- **What is never committed:** the model weights and llama.cpp's sources stay outside the
  repository (CONTRIBUTING).
