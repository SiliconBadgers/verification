#!/usr/bin/env bash
# Fetch the two pinned references the golden model checks against, outside the repository:
#   llama.cpp f46bc30 (a sparse checkout of ggml/: about 6 MB), for the C harness;
#   Qwen3.5-2B-Q4_K_M.gguf (1.28 GB, sha256-checked), for the real-tensor tests and tools.
# Pins: SiliconBadgers/software experiments/llama-cpp/2026-09-22/manifest.json.
# Usage: tools/fetch_reference.sh [DEST]   (default ~/ref)
set -euo pipefail
DEST="${1:-$HOME/ref}"
COMMIT=f46bc30cb6a7f68a67e34a00061e20a4ad1eff43
REV=f6d5376be1edb4d416d56da11e5397a961aca8ae
FILE=Qwen3.5-2B-Q4_K_M.gguf
SHA=aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223

L="$DEST/llama.cpp-f46bc30"
mkdir -p "$L"
if [ "$(git -C "$L" rev-parse HEAD 2>/dev/null)" != "$COMMIT" ]; then
  git -C "$L" init -q
  git -C "$L" remote get-url origin >/dev/null 2>&1 \
    || git -C "$L" remote add origin https://github.com/ggml-org/llama.cpp.git
  git -C "$L" sparse-checkout set --no-cone '/ggml/include/' '/ggml/src/*.h' '/ggml/src/*.c' \
    '/ggml/src/*.cpp' '/ggml/src/ggml-cpu/' '/LICENSE'
  git -C "$L" fetch -q --depth 1 --filter=blob:none origin "$COMMIT"
  git -C "$L" checkout -q FETCH_HEAD
fi
echo "llama.cpp $(git -C "$L" rev-parse HEAD) in $L"

M="$DEST/models/qwen35-2b-q4km"
mkdir -p "$M"
if [ ! -f "$M/$FILE" ]; then
  curl -fL --retry 3 -C - -o "$M/$FILE.part" \
    "https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/$REV/$FILE"
  echo "$SHA  $M/$FILE.part" | sha256sum -c -
  mv "$M/$FILE.part" "$M/$FILE"
fi
echo "$SHA  $M/$FILE" | sha256sum -c -
