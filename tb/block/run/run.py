#!/usr/bin/env python3
"""Training-style entry point, using the common Synopsys runner."""

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parents[3] / "scripts/regression/run_vcs.py"), run_name="__main__"
)
