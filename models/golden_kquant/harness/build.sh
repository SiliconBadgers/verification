#!/usr/bin/env bash
# Build the C harness against the pinned llama.cpp sources (generic CPU path, no FMA
# contraction). Usage: harness/build.sh [LLAMA_DIR] [OUT_DIR]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
L="${1:-$HOME/ref/llama.cpp-f46bc30}"
OUT="${2:-$HOME/gm_build}"
want=f46bc30cb6a7f68a67e34a00061e20a4ad1eff43
have="$(git -C "$L" rev-parse HEAD)"
[ "$have" = "$want" ] || { echo "llama.cpp at $have, need $want" >&2; exit 1; }
mkdir -p "$OUT"
CFLAGS=(-O2 -std=gnu11 -ffp-contract=off -fno-fast-math -DGGML_CPU_GENERIC -DNDEBUG
        -I"$L/ggml/include" -I"$L/ggml/src" -I"$L/ggml/src/ggml-cpu")
gcc "${CFLAGS[@]}" -c "$L/ggml/src/ggml-quants.c" -o "$OUT/ggml-quants.o"
gcc "${CFLAGS[@]}" -c "$L/ggml/src/ggml-cpu/quants.c" -o "$OUT/cpu-quants.o"
gcc "${CFLAGS[@]}" -c "$here/stubs.c" -o "$OUT/stubs.o"
gcc "${CFLAGS[@]}" "$here/gm_harness.c" "$OUT/ggml-quants.o" "$OUT/cpu-quants.o" "$OUT/stubs.o" \
    -lm -o "$OUT/gm_harness"
echo "built $OUT/gm_harness (llama.cpp $have)"
