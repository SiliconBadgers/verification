# CAE setup and first run

[Home](README.md) | [Environment tour](tb/unit/mac/README.md) |
[Runner reference](scripts/regression/README.md) | [Test plan](plans/block-verification-v0.1.md)

The [README quick start](README.md#quick-start-cae-instructions) uses the primary
placeholder block. It requires no sibling RTL/SoC checkout when using installed
UVM. The onboarding MAC-specific walkthrough below remains an optional example;
use `--pilot mac` for its tests and `sb_mac_top.dut` for its waveforms. For the
primary block use `tc_block_smoke` / `tc_block_random` and `top_tb.dut`.

## 1. Enter the CAE environment

These steps adapt Abhinav Nandwani's **Verification on CAE**, September 23, 2026,
supplied with this task. It reports VCS `Y-2026.03_Full64`, Verdi `Y-2026.03` and
URG `Y-2026.03` for a procedural register example. These are handout-reported
baseline versions; record the tools actually used for this branch.

For GUI work, open [CAE Guacamole](https://guacamole.cae.wisc.edu), complete UW
NetID sign-in/MFA, then use your NetID again at the Linux desktop login.
Open **Apps > Favorites > Terminal**. This terminal is already on CAE;
see [CAE sign-in help](https://kb.wisc.edu/cae/163323).
For terminal-only work, connect from your laptop using
`ssh YOUR_NETID@best-tux.cae.wisc.edu`.

In each new **CAE host terminal**:

```sh
module load synopsys/suite
synopsys-run
```

Then in the **Synopsys container**:

```sh
command -v vcs verdi urg g++ python3
export VERDI_HOME="$(dirname "$(dirname "$(command -v verdi)")")"
vcs -ID
python3 --version
g++ --version
```

Python 3.11+ is required. Use the VCS-supported site C++ compiler. Passing the
standalone model test with another compiler does not prove VCS compatibility.
Record Verdi's version from its startup/About dialog and URG's version from its
report. Finding executables alone does not establish license access. Keep
credentials, license configuration and site installation paths out of Git.

## 2. Select the workspace

Use sibling checkouts with these **case-sensitive names**:

```text
siliconbadgers/
  verification/       feat/block-uvm-vcs-verdi
  rtl/                onboarding MAC and routing experiment
  architecture/       contracts/mac-v0.json
  soc/                router fixtures; only needed for the router pilot
  UVM_Library/        optional source UVM 1.2 build
  uvm-training/       reference; not compiled by this runner
```

A local branch does not automatically appear on CAE. Use the CAE copy of this
branch once it is published or transferred. To reproduce the documented baseline,
use the revisions in the [test plan](plans/block-verification-v0.1.md).
The runner records actual revisions, local changes and hashes; it never fetches
or edits other repositories. For another layout supply `--rtl-root`, `--soc-root`,
`--contract`, and, for source mode, `--uvm-root`. Explicit paths are relative to
your current shell directory; defaults resolve from this repository.

## 3. Run and inspect the onboarding pilot

From `verification` in the Synopsys container:

```sh
python3 scripts/regression/run_vcs.py --doctor
python3 scripts/regression/run_vcs.py --pilot mac --test sb_mac_smoke_test --seed 1 --dry-run
python3 scripts/regression/run_vcs.py --pilot mac --test sb_mac_smoke_test --seed 1 --waves --coverage
```

Doctor checks availability. Dry-run validates inputs and writes `PLANNED`
commands; it does not simulate. The third command compiles the onboarding MAC,
UVM environment and C++ model, runs the test, and invokes URG after a passing
simulation. It stops if compilation fails.

Use the **exact new run directory** printed by the runner:

```sh
cd /absolute/path/printed/by/the/runner
cat summary.json
cat manifest.json
tail -n 40 run.log
verdi -ssf waves.fsdb
```

In Verdi select `sb_mac_top.dut`. Add `clk`, `rst_n`, `clear`, `enable`, `a`, `b`
and `acc` to nWave, Zoom All, then inspect reset, clear/hold and signed arithmetic.
Inputs are driven on a falling edge; normal results are sampled 1 ps after the
rising edge's NBA update. The short reset pulse must clear `acc` without a rising
clock. Keep the matching build/KDB and FSDB together.

Open `coverage_report/dashboard.html` in the CAE desktop browser. Inspect DUT
coverage separately from testbench/imported UVM, then review the authored
functional bins and bound assertions. Record the scope and missing cases.
For supported installations, `verdi -cov -covdir coverage.vdb` opens the coverage
UI; confirm with the site's installed help if its wrapper differs.

## 4. Qualify the environment before using it for accelerator blocks

Run each command separately and inspect its own result:

```sh
python3 scripts/regression/run_vcs.py --pilot mac --test sb_mac_random_test --seed 17 --coverage --waves
python3 scripts/regression/run_vcs.py --pilot mac --test sb_mac_overflow_test --seed 1 --coverage
python3 scripts/regression/run_vcs.py --pilot router --coverage --waves
python3 scripts/regression/run_vcs.py --inject mismatch --waves
python3 scripts/regression/run_vcs.py --inject timeout --plusarg=+SB_TIMEOUT_NS=10000
python3 scripts/regression/run_vcs.py --vcs sb-intentionally-missing-vcs
```

The first three must pass. The last three **must fail for their intended reasons**:

- Mismatch: successful compilation followed by `SB_MISMATCH`, no `SB_TEST_PASS`,
  and a nonzero runner verdict. This corrupts one expected transaction, not RTL.
- Timeout: successful compilation followed by simulation `SB_TIMEOUT` or process
  `TIMEOUT`, with no success marker. A compile/license error does not qualify.
- Missing tool: `SETUP_FAILURE`, never a simulation pass.

The handout observed a VCS fatal diagnostic with raw exit zero. The runner also
requires a positive marker, nonzero comparisons, zero UVM error/fatal summaries,
and no error/fatal/assertion diagnostics. See the [runner reference](scripts/regression/README.md).
Use the [CAE record template](docs/CAE-RUN-RECORD.md) for measured results.

## Optional source-library comparison

```sh
python3 scripts/regression/run_vcs.py --pilot mac --uvm-mode source --uvm-root ../UVM_Library --test sb_mac_smoke_test
```

The CAE default uses `-ntb_opts uvm-1.2`. Source mode compiles `src/uvm.sv` and
`src/dpi/uvm_dpi.cc` with `-DVCS`. Never compile both UVM implementations together.
Do not copy the UART training flow's `UVM_NO_DPI` setting into this C++ build.
Both modes need their own licensed run evidence.

## Local checks without Synopsys

On Linux/WSL with Python 3.11+ and a C++ compiler, from `verification`:

```sh
python3 -m unittest discover -s scripts/regression -p test_run_vcs.py -v
mkdir -p build/model
g++ -std=c++11 -Wall -Wextra -Werror -fsanitize=undefined models/mac_reference.cpp models/mac_reference_test.cpp -o build/model/mac_reference_test
build/model/mac_reference_test
```

For optional semantic checking, install `requirements-dev.txt` in an isolated
Python environment. The MAC semantic check needs the sibling UVM source:

```sh
python3 scripts/regression/check_sv.py
python3 scripts/regression/check_sv.py --pilot router
make format
make style
```

The style targets also need Verible `v0.0-3946-g851d3ff4` on PATH; Ruff `0.16.6`
is pinned. These checks do not execute UVM, DPI or RTL. The original Icarus
onboarding example remains available through `make test` with Icarus plus the
sibling Software vector generator and Architecture contract.

## Troubleshooting

| Symptom | First check |
|---|---|
| CAE launcher warning/missing tools | Load the module before entering `synopsys-run`, in each terminal |
| Compile/DPI failure | First error in `compile.log`, UVM mode, package order and supported C++ compiler |
| License error | Preserve diagnostic/version; this is a tool failure, not a behavioral result |
| Missing source | Sibling roots/branch, including case-sensitive `UVM_Library` |
| No pass marker/mismatch | Earliest checker message and expected event/value versus observed pins |
| Missing FSDB | `VERDI_HOME`, matching VCS/Verdi versions, `--waves`; site-documented extra flags via `--vcs-arg=...` |
| Empty GUI | Matching run directory, FSDB, DUT scope, added signals, Zoom All |
| Coverage failure | `coverage.log`, actual VDB and URG dashboard; inspect scope before reporting percentages |

Close EDA applications, exit the container, and log out of the CAE desktop when
done. Closing only the Guacamole tab can leave the session running.
