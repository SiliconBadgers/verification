#!/usr/bin/env python3
"""Isolated VCS pilots. A planned command or missing license is never a test pass."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAC_TESTS = ("sb_mac_smoke_test", "sb_mac_random_test", "sb_mac_overflow_test")
BLOCK_TESTS = ("tc_block_smoke", "tc_block_random")
TOPS = {"block": "top_tb", "mac": "sb_mac_top", "router": "command_router_tb"}
UNITS = {"block": ROOT / "tb/block", "mac": ROOT / "tb/unit/mac"}
METRICS = "line+cond+tgl+branch+assert"
FAILURE = re.compile(
    r"^\s*(?:Error(?:-|:)|Fatal(?:-|:)|UVM_(?:ERROR|FATAL)\s+(?![\s:]))"
    r"|assertion[^\n]*(?:fail|error)|\$fatal",
    re.MULTILINE | re.IGNORECASE,
)
LICENSE_FAILURE = re.compile(
    r"license.*(?:fail|denied|unavailable|cannot|unable)|"
    r"(?:cannot|unable|failed).*license|no valid license",
    re.IGNORECASE,
)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", choices=("block", "mac", "router"), default="block")
    p.add_argument("--test", choices=BLOCK_TESTS + MAC_TESTS)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--rtl-root", type=Path, default=ROOT.parent / "rtl")
    p.add_argument("--soc-root", type=Path, default=ROOT.parent / "soc")
    p.add_argument("--uvm-root", type=Path, default=ROOT.parent / "UVM_Library")
    p.add_argument("--uvm-mode", choices=("source", "vcs"), default="vcs")
    p.add_argument(
        "--contract", type=Path, default=ROOT.parent / "architecture/contracts/mac-v0.json"
    )
    p.add_argument("--output-root", type=Path, default=ROOT / "build" / "vcs")
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--compile-timeout", type=float, default=300)
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--waves", action="store_true")
    p.add_argument("--inject", choices=("mismatch", "timeout"))
    p.add_argument("--vcs", default="vcs")
    p.add_argument("--urg", default="urg")
    p.add_argument("--vcs-arg", action="append", default=[])
    p.add_argument("--plusarg", action="append", default=[])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--doctor", action="store_true")
    return p


def source_files(args):
    rtl = args.rtl_root.resolve()
    if args.pilot == "router":
        soc = args.soc_root.resolve()
        return [
            rtl / "rtl/common/command_pkg.sv",
            rtl / "rtl/control/command_router.sv",
            soc / "sim/engine_stub.sv",
            soc / "sim/command_router_test_top.sv",
            ROOT / "tb/command_router_tb.sv",
        ]
    if args.pilot == "block":
        unit = UNITS["block"]
        return [
            ROOT / "tb/common/sb_uvm_base_pkg.sv",
            unit / "agent/block_if.sv",
            unit / "agent/block_pkg.sv",
            unit / "test/verif_pkg.sv",
            unit / "dut/block_stub.sv",
            unit / "block_assertions.sv",
            unit / "top_tb/top_tb.sv",
            ROOT / "models/block_stub_reference.cpp",
        ]
    unit = UNITS["mac"]
    return [
        rtl / "rtl/compute/pe_mac.sv",
        ROOT / "tb/common/sb_uvm_base_pkg.sv",
        unit / "agent/sb_mac_if.sv",
        unit / "sb_mac_pkg.sv",
        unit / "sb_mac_assertions.sv",
        unit / "top_tb/sb_mac_top.sv",
        ROOT / "models/mac_reference.cpp",
    ]


def commands(args, run_dir):
    sources = source_files(args)
    top = TOPS[args.pilot]
    compile_cmd = [
        args.vcs,
        "-full64",
        "-sverilog",
        "-timescale=1ns/1ps",
        "-top",
        top,
        "-o",
        str(run_dir / "simv"),
    ]
    if args.pilot != "router":
        compile_cmd += [f"+incdir+{UNITS[args.pilot]}"]
        if args.uvm_mode == "source":
            uvm = args.uvm_root.resolve() / "src"
            compile_cmd += [
                f"+incdir+{uvm}",
                str(uvm / "uvm.sv"),
                str(uvm / "dpi/uvm_dpi.cc"),
                "-CFLAGS",
                "-DVCS -std=c++11",
            ]
        else:
            compile_cmd += ["-ntb_opts", "uvm-1.2", "-CFLAGS", "-std=c++11"]
    if args.waves:
        compile_cmd += ["-kdb", "-debug_access+all", "+define+SB_FSDB"]
    if args.coverage:
        compile_cmd += ["-cm", METRICS, "-cm_dir", str(run_dir / "coverage.vdb")]
    compile_cmd += args.vcs_arg + [str(p) for p in sources]
    run_cmd = [str(run_dir / "simv"), f"+ntb_random_seed={args.seed}"]
    if args.pilot != "router":
        test = args.test or (BLOCK_TESTS[0] if args.pilot == "block" else MAC_TESTS[0])
        run_cmd += [f"+UVM_TESTNAME={test}", "+UVM_VERBOSITY=UVM_LOW"]
    if args.inject:
        run_cmd += [f"+SB_INJECT_{args.inject.upper()}"]
    run_cmd += args.plusarg
    if args.waves:
        run_cmd += ["+SB_FSDB"]
    if args.coverage:
        run_cmd += [
            "-cm",
            METRICS,
            "-cm_dir",
            str(run_dir / "coverage.vdb"),
            "-cm_name",
            f"{args.pilot}_{args.test}_{args.seed}",
        ]
    return compile_cmd, run_cmd


def run_stage(command, cwd, log, timeout):
    """Bound the whole process group on Linux, including simulator/compiler children."""
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as out:
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=(os.name == "posix"),
            )
        except OSError as exc:
            out.write(f"Cannot execute {command[0]}: {exc}\n")
            return {
                "returncode": None,
                "timeout": False,
                "launch_error": True,
                "seconds": time.monotonic() - start,
            }
        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            timed_out = True
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            proc.wait()
            if isinstance(exc, KeyboardInterrupt):
                raise
        return {
            "returncode": proc.returncode,
            "timeout": timed_out,
            "launch_error": False,
            "seconds": time.monotonic() - start,
        }


def verdict(log_text, result, pilot):
    if result["timeout"]:
        return "TIMEOUT", 124
    if result["launch_error"] or LICENSE_FAILURE.search(log_text):
        return "TOOL_FAILURE", 4
    if result["returncode"] != 0 or FAILURE.search(log_text):
        return "FAIL", 1
    if pilot != "router":
        for severity in ("ERROR", "FATAL"):
            counts = re.findall(rf"^\s*UVM_{severity}\s*:\s*(\d+)\s*$", log_text, re.M)
            if len(counts) != 1 or counts[0] != "0":
                return "FAIL", 1
        marker = re.search(r"UVM_INFO[^\n]*\[SB_TEST_PASS\]\s+compared=(\d+)", log_text)
        passed = bool(marker and int(marker[1]) > 0)
    else:
        passed = "PASS router: 8 commands" in log_text
    return ("PASS", 0) if passed else ("FAIL", 1)


def revision(path):
    result = {"path": str(path.resolve())}
    for key, options in (("commit", ["rev-parse", "HEAD"]), ("changes", ["status", "--porcelain"])):
        try:
            p = subprocess.run(
                ["git", "-C", str(path), *options],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            result[key] = p.stdout.strip() if p.returncode == 0 else "unavailable"
        except (OSError, subprocess.TimeoutExpired):
            result[key] = "unavailable"
    return result


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    args = parser().parse_args(argv)
    allowed = BLOCK_TESTS if args.pilot == "block" else MAC_TESTS
    if args.pilot == "router":
        if args.test:
            parser().error("router is a procedural pilot and has no UVM test selection")
        args.test = "command_router_tb"
    else:
        args.test = args.test or allowed[0]
        if args.test not in allowed:
            parser().error(f"{args.test} does not belong to --pilot {args.pilot}")
    if not 1 <= args.seed <= 2**31 - 1 or not all(
        math.isfinite(t) and t > 0 for t in (args.timeout, args.compile_timeout)
    ):
        parser().error("seed must be 1..2147483647 and timeouts must be positive")
    if args.pilot == "router" and args.inject:
        parser().error("failure injection is implemented by the block and onboarding MAC pilots")
    if any(
        not value.startswith("+SB_") or any(c.isspace() for c in value) for value in args.plusarg
    ):
        parser().error("--plusarg accepts only +SB_* pilot controls without whitespace")
    if args.doctor:
        report = {
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "vcs": shutil.which(args.vcs),
            "verdi": shutil.which("verdi"),
            "urg": shutil.which(args.urg),
            "cxx": shutil.which("g++"),
            "license_status": "UNTESTED: only a real compile/run establishes access",
        }
        print(json.dumps(report, indent=2))
        return (
            0
            if all(report[k] for k in ("vcs", "verdi", "urg", "cxx")) and os.name == "posix"
            else 2
        )
    # Resolve relative executable paths before changing to an isolated run folder.
    args.vcs = shutil.which(args.vcs) or args.vcs
    args.urg = shutil.which(args.urg) or args.urg
    name = f"{args.pilot}-{args.seed}-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    run_dir = args.output_root.resolve() / name
    run_dir.mkdir(parents=True, exist_ok=False)
    compile_cmd, run_cmd = commands(args, run_dir)
    sources = source_files(args)
    required = list(sources)
    if args.pilot == "mac":
        required += sorted((ROOT / "tb/unit/mac").rglob("*.svh")) + [args.contract.resolve()]
    if args.pilot != "router" and args.uvm_mode == "source":
        required += [
            args.uvm_root.resolve() / "src/uvm.sv",
            args.uvm_root.resolve() / "src/dpi/uvm_dpi.cc",
        ]
    if args.pilot == "block":
        required += sorted(UNITS["block"].rglob("*.svh")) + [UNITS["block"] / "contract.json"]
    hash_inputs = list(required)
    if args.pilot != "router" and args.uvm_mode == "source":
        hash_inputs += sorted(
            p
            for p in (args.uvm_root / "src").rglob("*")
            if p.suffix in (".sv", ".svh", ".c", ".cc", ".h")
        )
    manifest = {
        "schema": 1,
        "pilot": args.pilot,
        "test": args.test,
        "seed": args.seed,
        "injection": args.inject,
        "uvm_mode": args.uvm_mode if args.pilot != "router" else None,
        "coverage_requested": args.coverage,
        "waves_requested": args.waves,
        "timeouts_s": {"compile": args.compile_timeout, "run": args.timeout},
        "commands": {"compile": compile_cmd, "run": run_cmd},
        "environment": {
            "platform": sys.platform,
            "python": sys.version,
            "verdi_home": os.environ.get("VERDI_HOME"),
            "verdi": shutil.which("verdi"),
            "urg": shutil.which(args.urg),
        },
        "sources": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in hash_inputs if p.is_file()
        },
        "repositories": {"verification": revision(ROOT)},
        "requirements": (
            ["MAC-001", "MAC-002", "MAC-003", "ENV-004"]
            if args.pilot == "mac"
            else (
                ["STUB-001", "STUB-002", "STUB-003", "ENV-004"]
                if args.pilot == "block"
                else ["INT-001", "INT-002", "ENV-004"]
            )
        ),
        "scope": {
            "mac": "ONBOARDING INT8 MAC; not accelerator verification",
            "block": "PROVISIONAL BLOCK STUB; not an accelerator interface or DUT",
            "router": "router with error-only stubs",
        }[args.pilot],
    }
    if args.pilot != "block":
        manifest["repositories"]["rtl"] = revision(args.rtl_root)
    if args.pilot != "router":
        if args.uvm_mode == "source":
            manifest["repositories"]["uvm"] = revision(args.uvm_root)
        if args.inject:
            manifest["requirements"].append("ENV-001" if args.inject == "mismatch" else "ENV-002")
        if args.test == "sb_mac_overflow_test":
            manifest["requirements"].append("MAC-004")
    else:
        manifest["repositories"]["soc"] = revision(args.soc_root)
    write_json(run_dir / "manifest.json", manifest)

    def finish(status, code, **details):
        summary = {
            "status": status,
            "exit_code": code,
            "run_dir": str(run_dir),
            "test": manifest["test"],
            "seed": args.seed,
            "requirements": manifest["requirements"],
            **details,
        }
        write_json(run_dir / "summary.json", summary)
        print(json.dumps(summary, indent=2))
        return code

    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        return finish("SETUP_FAILURE", 2, missing_files=missing)
    if args.pilot == "mac":
        expected = {
            "id": "siliconbadgers.mac.v0",
            "operand_bits": 8,
            "accumulator_bits": 32,
            "signed": True,
            "overflow": "wrap",
            "clear_priority": "before_enable",
            "reset": "asynchronous_active_low",
        }
        try:
            contract = json.loads(args.contract.read_text(encoding="utf-8"))
            if any(contract.get(k) != v for k, v in expected.items()):
                return finish(
                    "SETUP_FAILURE", 2, reason="MAC contract differs from the pilot model"
                )
        except (ValueError, AttributeError) as exc:
            return finish("SETUP_FAILURE", 2, reason=f"Invalid MAC contract: {exc}")
    if args.dry_run:
        return finish("PLANNED", 0, note="No tools executed; no simulation or coverage evidence")
    if os.name != "posix" or not shutil.which(args.vcs):
        return finish("SETUP_FAILURE", 2, reason="Run on CAE Linux with VCS on PATH")
    if args.coverage and not shutil.which(args.urg):
        return finish("SETUP_FAILURE", 2, reason="--coverage requires URG on PATH")
    if args.waves and not os.environ.get("VERDI_HOME"):
        return finish(
            "SETUP_FAILURE", 2, reason="--waves requires the CAE VERDI_HOME setup; see SETUP.md"
        )
    run_stage([args.vcs, "-ID"], run_dir, run_dir / "vcs-version.log", 15)
    compile_result = run_stage(compile_cmd, run_dir, run_dir / "compile.log", args.compile_timeout)
    compile_text = (run_dir / "compile.log").read_text(encoding="utf-8", errors="replace")
    if compile_result["timeout"]:
        return finish("COMPILE_TIMEOUT", 124, compile=compile_result)
    if compile_result["launch_error"] or LICENSE_FAILURE.search(compile_text):
        return finish("TOOL_FAILURE", 4, compile=compile_result)
    if (
        compile_result["returncode"] != 0
        or FAILURE.search(compile_text)
        or not (run_dir / "simv").is_file()
    ):
        return finish("COMPILE_FAILURE", 3, compile=compile_result)
    run_result = run_stage(run_cmd, run_dir, run_dir / "run.log", args.timeout)
    log_text = (run_dir / "run.log").read_text(encoding="utf-8", errors="replace")
    status, code = verdict(log_text, run_result, args.pilot)
    artifacts = {
        "coverage_database_present": (run_dir / "coverage.vdb").is_dir(),
        "waveform_present": (run_dir / "waves.fsdb").is_file(),
    }
    if status == "PASS" and (
        (args.coverage and not artifacts["coverage_database_present"])
        or (args.waves and not artifacts["waveform_present"])
    ):
        status, code = "ARTIFACT_FAILURE", 1
    if status == "PASS" and args.coverage:
        coverage_cmd = [
            args.urg,
            "-full64",
            "-dir",
            str(run_dir / "coverage.vdb"),
            "-report",
            str(run_dir / "coverage_report"),
        ]
        manifest["commands"]["coverage"] = coverage_cmd
        write_json(run_dir / "manifest.json", manifest)
        coverage_result = run_stage(
            coverage_cmd, run_dir, run_dir / "coverage.log", args.compile_timeout
        )
        coverage_log = (run_dir / "coverage.log").read_text(encoding="utf-8", errors="replace")
        artifacts["coverage_report"] = coverage_result
        artifacts["coverage_dashboard_present"] = (
            run_dir / "coverage_report/dashboard.html"
        ).is_file()
        if (
            coverage_result["returncode"] != 0
            or coverage_result["timeout"]
            or coverage_result["launch_error"]
            or FAILURE.search(coverage_log)
            or LICENSE_FAILURE.search(coverage_log)
            or not artifacts["coverage_dashboard_present"]
        ):
            status, code = "COVERAGE_FAILURE", 1
    return finish(status, code, compile=compile_result, run=run_result, **artifacts)


if __name__ == "__main__":
    raise SystemExit(main())
