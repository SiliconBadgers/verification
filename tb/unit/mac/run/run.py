#!/usr/bin/env python3
"""Training-style entry point: delegate to the single maintained VCS runner."""

import runpy
import sys
from pathlib import Path

sys.argv[1:1] = ["--pilot", "mac"]
runpy.run_path(
    str(Path(__file__).resolve().parents[4] / "scripts/regression/run_vcs.py"), run_name="__main__"
)
