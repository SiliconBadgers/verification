#!/usr/bin/env python3
"""Optional slang semantic check; no simulation, DPI execution, or VCS license check."""

import argparse
from pathlib import Path

from pyslang.driver import Driver
from run_vcs import ROOT, TOPS, UNITS, parser, source_files


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--uvm-root", type=Path, default=ROOT.parent / "UVM_Library")
    cli.add_argument("--rtl-root", type=Path, default=ROOT.parent / "rtl")
    cli.add_argument("--soc-root", type=Path, default=ROOT.parent / "soc")
    cli.add_argument("--pilot", choices=("block", "mac", "router"), default="block")
    options = cli.parse_args()
    args = parser().parse_args([])
    args.rtl_root, args.soc_root, args.pilot = options.rtl_root, options.soc_root, options.pilot
    files = [p for p in source_files(args) if p.suffix == ".sv"]
    command = [
        "slang",
        "--single-unit",
        "--timescale",
        "1ns/1ps",
        "--top",
        TOPS[args.pilot],
    ]
    if args.pilot != "router":
        uvm = options.uvm_root.resolve() / "src"
        command += [f"+incdir+{uvm.as_posix()}", f"+incdir+{UNITS[args.pilot].as_posix()}"]
        files.insert(0, uvm / "uvm.sv")
    for path in files:
        if not path.is_file():
            raise SystemExit(f"Missing source: {path}")
    command += [p.resolve().as_posix() for p in files]
    driver = Driver()
    driver.addStandardArgs()
    # slang's own argument parser, not a shell. Quotes preserve paths with spaces.
    if not driver.parseCommandLine(" ".join(f'"{arg}"' for arg in command)):
        return 1
    if not driver.processOptions() or not driver.parseAllSources():
        return 1
    return 0 if driver.runFullCompilation() else 1


if __name__ == "__main__":
    raise SystemExit(main())
