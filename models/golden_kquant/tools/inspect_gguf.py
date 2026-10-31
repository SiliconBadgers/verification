#!/usr/bin/env python3
"""Summarize a GGUF file: version, tensor counts by type, and the matrix weights' shapes.

Usage: python3 tools/inspect_gguf.py MODEL.gguf
"""

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.gguf import GGUF  # noqa: E402


def main():
    g = GGUF(sys.argv[1])
    print(f"GGUF v{g.version}, {len(g.tensors)} tensors, {len(g.metadata)} metadata keys, "
          f"data at {g.data_start}")
    print("arch:", g.metadata.get("general.architecture"), " alignment:",
          g.metadata.get("general.alignment", 32))
    by_type = collections.Counter(t.type_name for t in g.tensors.values())
    print("tensors by type:", dict(sorted(by_type.items())))
    matrices = [t for t in g.tensors.values() if t.type_name in ("q4_K", "q5_K", "q6_K", "q8_0")]
    print("matrix weights:", len(matrices),
          dict(collections.Counter(t.type_name for t in matrices)))
    for t in sorted(matrices, key=lambda t: t.name)[:6]:
        print(f"  {t.name:32s} {t.type_name:5s} dims={t.dims} rows={t.rows} row_bytes={t.row_bytes}")


if __name__ == "__main__":
    main()
