"""Runner failure-sensitivity tests. Fake process output is not VCS evidence."""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("run_vcs", Path(__file__).with_name("run_vcs.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

GOOD = "UVM_INFO test.svh(1) @ 35: uvm_test_top [SB_TEST_PASS] compared=3\nUVM_ERROR : 0\nUVM_FATAL : 0\n"
NORMAL = {"returncode": 0, "timeout": False, "launch_error": False}


class VerdictTests(unittest.TestCase):
    def test_checked_positive(self):
        self.assertEqual(runner.verdict(GOOD, NORMAL, "mac"), ("PASS", 0))

    def test_zero_exit_fatal_is_failure(self):
        self.assertEqual(runner.verdict(GOOD + "Fatal: data failed\n", NORMAL, "mac"), ("FAIL", 1))

    def test_uvm_error_even_when_summary_is_zero(self):
        text = "UVM_ERROR test.svh(1) @ 25: reporter [SB_MISMATCH] bad data\n" + GOOD
        self.assertEqual(runner.verdict(text, NORMAL, "mac"), ("FAIL", 1))

    def test_nonzero_or_missing_uvm_summary(self):
        for text in (
            GOOD.replace("ERROR : 0", "ERROR : 1"),
            GOOD.split("UVM_ERROR")[0],
            GOOD + "UVM_ERROR : 0\n",
        ):
            with self.subTest(text=text):
                self.assertNotEqual(runner.verdict(text, NORMAL, "mac")[0], "PASS")

    def test_empty_or_banner_only_test_cannot_pass(self):
        for text in (
            "",
            "SB_TEST_PASS\nUVM_ERROR : 0\nUVM_FATAL : 0\n",
            GOOD.replace("compared=3", "compared=0"),
        ):
            self.assertEqual(runner.verdict(text, NORMAL, "mac"), ("FAIL", 1))

    def test_assertion_and_license_diagnostics(self):
        self.assertEqual(
            runner.verdict(GOOD + "Assertion a_hold failed", NORMAL, "mac"), ("FAIL", 1)
        )
        self.assertEqual(
            runner.verdict("Unable to checkout license", NORMAL, "mac"), ("TOOL_FAILURE", 4)
        )

    def test_raw_nonzero_and_timeout_override_pass(self):
        self.assertEqual(runner.verdict(GOOD, dict(NORMAL, returncode=1), "mac"), ("FAIL", 1))
        self.assertEqual(runner.verdict(GOOD, dict(NORMAL, timeout=True), "mac"), ("TIMEOUT", 124))

    def test_router_needs_its_own_marker(self):
        self.assertEqual(runner.verdict("PASS router: 8 commands", NORMAL, "router"), ("PASS", 0))
        self.assertEqual(runner.verdict(GOOD, NORMAL, "router"), ("FAIL", 1))


class ProcessTests(unittest.TestCase):
    def test_real_process_exit_and_log(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = runner.run_stage(
                [sys.executable, "-c", "print('Fatal: data failed')"], path, path / "run.log", 5
            )
            self.assertEqual(result["returncode"], 0)
            self.assertEqual(
                runner.verdict((path / "run.log").read_text(), result, "mac"), ("FAIL", 1)
            )

    def test_wall_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = runner.run_stage(
                [sys.executable, "-c", "import time; time.sleep(30)"], path, path / "run.log", 0.1
            )
            self.assertTrue(result["timeout"])
            self.assertLess(result["seconds"], 5)

    def test_missing_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = runner.run_stage([str(path / "missing-vcs")], path, path / "run.log", 1)
            self.assertTrue(result["launch_error"])


class FlowTests(unittest.TestCase):
    def invoke(self, directory, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            code = runner.main(["--pilot", "mac", "--output-root", directory, *args])
        summaries = list(Path(directory).glob("*/summary.json"))
        self.assertEqual(len(summaries), 1)
        summary = json.loads(summaries[0].read_text())
        manifest = json.loads(summaries[0].with_name("manifest.json").read_text())
        return code, summary, manifest

    def test_dry_run_is_planned_with_training_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            code, summary, manifest = self.invoke(directory, "--dry-run")
            self.assertEqual((code, summary["status"]), (0, "PLANNED"))
            self.assertIn("-ntb_opts", manifest["commands"]["compile"])
            self.assertTrue(
                any("agent/sb_mac_if.sv" in p.replace("\\", "/") for p in manifest["sources"])
            )
            self.assertTrue(any(p.endswith("sb_mac_driver.svh") for p in manifest["sources"]))

    def test_source_uvm_selected_once(self):
        args = runner.parser().parse_args(["--pilot", "mac", "--uvm-mode", "source"])
        command, _ = runner.commands(args, Path("build"))
        self.assertNotIn("-ntb_opts", command)
        self.assertEqual(sum(p.endswith("uvm.sv") for p in command), 1)
        self.assertIn("-DVCS -std=c++11", command)

    def test_missing_sources_are_setup_failure_even_in_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            code, summary, _ = self.invoke(
                directory, "--dry-run", "--rtl-root", str(Path(directory) / "absent")
            )
            self.assertEqual((code, summary["status"]), (2, "SETUP_FAILURE"))

    def test_contract_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "contract.json"
            contract.write_text('{"operand_bits": 4}')
            code, summary, _ = self.invoke(directory, "--dry-run", "--contract", str(contract))
            self.assertEqual((code, summary["status"]), (2, "SETUP_FAILURE"))

    def test_missing_vcs_never_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            code, summary, _ = self.invoke(directory, "--vcs", "sb-definitely-missing-vcs")
            self.assertEqual((code, summary["status"]), (2, "SETUP_FAILURE"))

    @unittest.skipUnless(os.name == "posix", "VCS execution flow targets Linux")
    def test_compile_and_simulation_failure_statuses(self):
        # Stage mocks test orchestration, not actual simulator behavior.
        for outcome in ("compile_error", "fatal_zero", "missing_marker", "pass"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:

                def stage(command, cwd, log, timeout):
                    if log.name == "compile.log":
                        (cwd / "simv").write_text("fake executable")
                        log.write_text(
                            "Error-[SYNTAX] invalid source"
                            if outcome == "compile_error"
                            else "compiled"
                        )
                    elif log.name == "run.log":
                        log.write_text(
                            {
                                "fatal_zero": GOOD + "Fatal: wrong value",
                                "missing_marker": "finished",
                                "pass": GOOD,
                            }[outcome]
                        )
                    else:
                        log.write_text("fake tool version")
                    return dict(NORMAL)

                with mock.patch.object(runner, "run_stage", side_effect=stage):
                    code, summary, _ = self.invoke(directory, "--vcs", sys.executable)
                expected = {
                    "compile_error": "COMPILE_FAILURE",
                    "fatal_zero": "FAIL",
                    "missing_marker": "FAIL",
                    "pass": "PASS",
                }[outcome]
                self.assertEqual(summary["status"], expected)
                self.assertEqual(code == 0, outcome == "pass")


if __name__ == "__main__":
    unittest.main()
