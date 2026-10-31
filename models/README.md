# models

Independent reference models and documented numerical/timing semantics. Cite provenance and explain how the model differs from the implementation it checks.

See [the current assignment](../docs/START-HERE.md).

## Models

| Model | What it is a model of | Checked against |
| --- | --- | --- |
| [golden_kquant](golden_kquant/README.md) | llama.cpp's quantized matrix arithmetic for Qwen3.5-2B Q4_K_M (dequantization, activation quantization, the four dot products, matrix × vector), plus the matrix unit's arithmetic contract | llama.cpp `f46bc30`'s own reference functions, bit for bit (generic CPU path); the matrix unit RTL, bit for bit, on exported real-tensor vectors |
