# SiliconBadgers verification

## Quick start: CAE instructions

Use your CAE Linux terminal (Guacamole for Verdi GUI). On the **host**, run:

```sh
module load synopsys/suite
synopsys-run
```

Inside the **Synopsys container**, from your checkout of `verification`:

```sh
export VERDI_HOME="$(dirname "$(dirname "$(command -v verdi)")")"
python3 scripts/regression/run_vcs.py --doctor
python3 scripts/regression/run_vcs.py --dry-run
python3 scripts/regression/run_vcs.py --test tc_block_smoke --seed 1 --waves --coverage
```

The default is the **temporary block stub**, not the onboarding MAC. Python
3.11+, VCS, Verdi, URG and the site's supported C++ compiler are needed. Select
this branch in your CAE checkout once it is published or transferred; a local
Windows branch is not automatically available on CAE.

The runner prints a new directory under `build/vcs/`. Open that exact directory:

```sh
cd /absolute/path/printed/by/the/runner
cat summary.json
cat manifest.json
tail -n 40 run.log
verdi -ssf waves.fsdb
```

In Verdi choose `top_tb.dut`, add request/response signals, and Zoom All.
Open `coverage_report/dashboard.html` in the CAE desktop browser. A dry-run is
`PLANNED`, never a simulation pass. The full [setup guide](SETUP.md) explains
access, modes, failures and the optional onboarding/router examples.

For the familiar training workflow:

```sh
cd tb/block/run
python3 run.py --test tc_block_random --seed 17 --waves --coverage
```

Run this from the repository root to verify checker sensitivity; these commands
must fail for the intended reason, after successful compilation:

```sh
python3 scripts/regression/run_vcs.py --inject mismatch
python3 scripts/regression/run_vcs.py --inject timeout --plusarg=+SB_TIMEOUT_NS=10000
```

## Overview

This springboard strongly follows `uvm-training`: `agent/`, `environment/`,
`test/`, `top_tb/`, and `run/`, with `env_top`, `test_top`, `verif_pkg`, config-db
wiring, a sequencer/driver, monitors and a scoreboard. Synopsys VCS replaces
ModelSim; Verdi/FSDB and URG provide debug and coverage outputs.

The main example uses an explicitly **made-up request/response protocol and
behavioral DUT stub**. It exercises accepted-input prediction through C++ DPI-C,
independent output observation, backpressure, reset/reuse, checking and coverage.
Its add/XOR/error operations qualify infrastructure only. They are not proposed
accelerator instructions. The PE MAC remains an optional **onboarding project**.

## Navigation

| Task | Read |
|---|---|
| First CAE run, dependencies, troubleshooting | [SETUP.md](SETUP.md) |
| UART-to-block map and placeholder signal definitions | [Block environment tour](tb/block/README.md) |
| Environment block diagram and per-layer method | [Methodology](docs/methodology/block-environment.md) |
| What to verify and why | [Test plan](plans/block-verification-v0.1.md), [35 requirements](plans/requirements-v0.1.csv) |
| Add or replace a block | [Bring-up guide](docs/ADDING-A-BLOCK.md) |
| Runner flags, outputs and failure statuses | [Runner reference](scripts/regression/README.md) |
| Original repositories and reuse decisions | [Cross-reference](docs/methodology/repository-cross-reference.md) |
| What has actually been checked | [Validation record](docs/VALIDATION.md) |
| Record a real CAE run | [Evidence template](docs/CAE-RUN-RECORD.md) |
| Optional onboarding MAC | [MAC tour](tb/unit/mac/README.md) |

```text
tb/block/          primary UART-style example with temporary DUT/protocol
  agent/           interface, config, item, sequence, sequencer, driver, monitors
  environment/     env_top, predictor, scoreboard, coverage
  test/            verif_pkg, test_top, directed/random tests
  top_tb/          DUT, clock/reset, virtual interface and FSDB
  dut/             explicitly labeled behavioral stub
  run/             thin entry point to the common VCS runner
tb/common/         reusable in-order scoreboard and active/passive config
tb/unit/mac/       optional onboarding MAC environment
models/            independent C++ reference functions and local tests
scripts/regression/ runners and local checks
plans/             architecture-aligned scenarios and stable requirement IDs
docs/              methodology, extension and evidence guides
build/             ignored logs, compiled outputs, FSDB/VDB and local tools
```

## Status and next use

See [VALIDATION.md](docs/VALIDATION.md) for the exact checks and limitations.
**Licensed VCS/DPI execution and Verdi review remain unrun on this branch.**
Neither a stub nor an onboarding MAC pass closes accelerator requirements.
Replace provisional signals and the stub using each block's reviewed contract;
keep accepted input, completion, output visibility and state/reset ownership
explicit. The [central architecture diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md)
remains the shared system reference.

This work advances verification issues #2, #3 and #4. Follow
[CONTRIBUTING.md](CONTRIBUTING.md) for review. AI assistance: OpenAI Codex;
exact runtime model ID unavailable.
