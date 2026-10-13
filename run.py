#!/usr/bin/env python3
"""Run the independent MAC testbench with VCS and record its actual check counts."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-root", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "build/mac/vcs")
    args = parser.parse_args()
    rtl_root = args.rtl_root.resolve()
    vcs_runner = rtl_root / "scripts/vcs.py"
    if not vcs_runner.is_file():
        parser.error("RTL checkout lacks scripts/vcs.py; use the coordinated VCS-enabled revision")
    sources = [rtl_root / "rtl/compute/pe_mac.sv", ROOT / "tb/pe_mac_smoke_tb.sv"]
    vectors = args.vectors.resolve()
    if any(not path.is_file() for path in [*sources, vectors]):
        parser.error("Missing RTL, independent verification testbench, or reference vectors")
    build = args.out.resolve()
    build.mkdir(parents=True, exist_ok=True)
    summary = {
        "inputs": [
            {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in [*sources, vectors]
        ],
        "steps": [],
        "passed": False,
    }
    for name, command in [
        (
            "compile",
            [
                "compile",
                "-top",
                "pe_mac_smoke_tb",
                *map(str, sources),
                "-Mdir=" + str(build / "csrc"),
                "-o",
                str(build / "simv"),
            ],
        ),
        ("run", ["run", str(build / "simv"), f"+VECTORS={vectors}"]),
    ]:
        log = build / f"{name}.log"
        elapsed = build / f"{name}.elapsed"
        with log.open("w") as stream:
            result = subprocess.run(
                [
                    sys.executable,
                    str(vcs_runner),
                    "--timeout",
                    "900",
                    "--elapsed-file",
                    str(elapsed),
                    *command,
                ],
                cwd=build,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        text = log.read_text()
        print(text, end="")
        summary["steps"].append(
            {
                "name": name,
                "exit_code": result.returncode,
                "log": str(log),
                "elapsed_seconds": float(elapsed.read_text()) if elapsed.exists() else None,
            }
        )
        if result.returncode:
            (build / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            return result.returncode
    golden = re.findall(r"^PASS golden vectors checked=(\d+)$", text, re.MULTILINE)
    checks = re.findall(r"^PASS pe_mac_smoke checks=(\d+) ", text, re.MULTILINE)
    summary["passed"] = (
        len(golden) == len(checks) == 1 and int(golden[0]) > 0 and int(checks[0]) > 0
    )
    summary["golden_vectors_checked"] = int(golden[0]) if len(golden) == 1 else None
    summary["rtl_checks"] = int(checks[0]) if len(checks) == 1 else None
    (build / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
