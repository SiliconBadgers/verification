# Accuracy study (phase 6)

This is the relative RMS error of each arithmetic against the ideal, on real Qwen3.5-2B Q4_K_M tensors with real activations (the dequantized embeddings of four tokens: 151644, 872, 9707, 1879).

- **Ideal:** the stored weights (dequantized, exact) times the float activations, computed in double.
- **llama.cpp:** the bit-exact golden model. Its error comes from quantizing the activation (q8_K, or q8_0 for q8_0 weights).
- **Matrix unit:** the unit as built. Weights are requantized to INT4 (q4_K) or INT8, and activations to INT8, with bf16 scales per 16 (an assumed rule, `golden/hwmode.py`), then run through the unit's arithmetic contract.

`tools/accuracy_study.py`, up to 256 output rows per tensor, spread over the matrix.

| Tensor | Rows | K | llama.cpp error (mean / worst) | Matrix unit error (mean / worst) | Matrix unit ÷ llama.cpp |
| --- | ---: | ---: | ---: | ---: | ---: |
| FFN gate, q4_K as INT4 (`blk.0.ffn_gate.weight`) | 256 | 2048 | 7.25e-03 / 7.70e-03 | 8.80e-02 / 9.16e-02 | 12.1× |
| FFN gate, q4_K as INT8 (`blk.0.ffn_gate.weight`) | 256 | 2048 | 7.25e-03 / 7.70e-03 | 6.83e-03 / 7.43e-03 | 0.9× |
| attention QKV, q5_K (`blk.0.attn_qkv.weight`) | 256 | 2048 | 3.90e-03 / 4.49e-03 | 3.94e-03 / 4.51e-03 | 1.0× |
| FFN down, q6_K (`blk.0.ffn_down.weight`) | 256 | 6144 | 7.47e-03 / 8.29e-03 | 6.74e-03 / 7.19e-03 | 0.9× |
| DeltaNet alpha, q8_0 (`blk.0.ssm_alpha.weight`) | 16 | 2048 | 4.14e-03 / 7.70e-03 | 4.13e-03 / 5.34e-03 | 1.0× |
| output head, q6_K (`token_embd.weight`) | 256 | 2048 | 2.33e-03 / 6.10e-03 | 2.69e-03 / 7.53e-03 | 1.2× |

## What it shows

- **INT8 costs nothing.** Every tensor run through the unit as INT8 (Q5_K, Q6_K, Q8_0, and Q4_K too) lands within 0.9–1.2× of llama.cpp's own error.
- **INT4 costs a lot.** Q4_K requantized to symmetric INT4 with bf16 scales per 16 has 12× llama.cpp's error (8.8% against 0.72%).
  - The control row is the same tensor as INT8 (0.9×), so the INT4 grid is the cause.
  - Q4_K's asymmetric grid (6-bit scale and min per 32, fp16 per 256) cannot be expressed in symmetric INT4.
  - Requantizing therefore adds a full 4-bit step of quantization noise: about step/√12 ≈ 8% for Gaussian-like weights in groups of 16.
- **What it means for D2 (the weight format).** 98 of the model's 187 matrix weights (49% of the weights) are Q4_K. Three options:
  1. **Support Q4_K natively** (integer sub-block scales and the min term, as in llama.cpp). It's exact and keeps INT4 throughput.
  2. **Run Q4_K tensors as INT8 on today's unit.** It's accurate, but runs at half the INT4 rate and moves twice the weight bytes.
  3. **Keep symmetric INT4** and accept about 12× the error on half the weights. That needs an end-to-end check (perplexity) before anyone signs off on it.

## Caveats

- **Not a real forward pass.** These are layer-0 tensors (and the output head) against raw token embeddings, not RMS-normed hidden states.
- **A sample.** At most 256 output rows per tensor.
- **Not model quality.** The metric is relative RMS error over the output vector, not perplexity.
- **The requantization rule is an assumption.** A smarter rule (for example, MSE-optimal scales) can reduce the INT4 gap but not remove it, because the two grids differ.

