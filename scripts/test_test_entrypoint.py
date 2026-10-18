"""Test current-design delegation without running a simulator."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestEntrypointTests(unittest.TestCase):
    def invoke(self, rtl, *args):
        return subprocess.run(
            ["make", "--no-print-directory", "test", f"RTL_ROOT={rtl}", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_current_suite_and_arguments_are_forwarded(self):
        with tempfile.TemporaryDirectory(prefix="rtl checkout ") as folder:
            rtl = Path(folder)
            (rtl / "Makefile").write_text(
                "test-matrix-unit:\n\t@echo CURRENT_MATRIX $(MATRIX_UNIT_ARGS)\n"
            )
            result = self.invoke(rtl, "MATRIX_UNIT_ARGS=--only array_8x8_acc32 --seeds 7")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CURRENT_MATRIX --only array_8x8_acc32 --seeds 7", result.stdout)

    def test_current_suite_failure_is_propagated(self):
        with tempfile.TemporaryDirectory() as folder:
            rtl = Path(folder)
            (rtl / "Makefile").write_text("test-matrix-unit:\n\t@exit 7\n")
            self.assertNotEqual(self.invoke(rtl).returncode, 0)

    def test_missing_current_suite_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Makefile").write_text("unrelated:\n\t@true\n")
            self.assertNotEqual(self.invoke(folder).returncode, 0)

    def test_missing_rtl_checkout_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertNotEqual(self.invoke(Path(folder) / "missing").returncode, 0)

    def test_retired_runner_and_testbench_are_absent(self):
        self.assertFalse((ROOT / "run.py").exists())
        self.assertFalse((ROOT / "tb/pe_mac_smoke_tb.sv").exists())
        makefile = (ROOT / "Makefile").read_text()
        for obsolete in ("MODELS_ROOT", "CONTRACT", "mac-vectors", "run.py"):
            self.assertNotIn(obsolete, makefile)


if __name__ == "__main__":
    unittest.main()
