# VCS regression runner

[Home](../../README.md) | [CAE setup](../../SETUP.md) | [Block tour](../../tb/block/README.md) | [Validation](../../docs/VALIDATION.md)

From `verification`, run `python3 scripts/regression/run_vcs.py --help` for all
options. Python 3.11+ standard library is sufficient for this runner.

## Profiles and commands

| Profile | Test selection | Scope |
|---|---|---|
| `--pilot block` (default) | tc_block_smoke (default), tc_block_random | Temporary behavioral block/protocol |
| `--pilot mac` | sb_mac_smoke_test, sb_mac_random_test, sb_mac_overflow_test | Onboarding PE MAC |
| `--pilot router` | Procedural command_router_tb; no --test | Existing router with error-only engine stubs |

```sh
python3 scripts/regression/run_vcs.py --test tc_block_random --seed 17 --waves --coverage
python3 scripts/regression/run_vcs.py --uvm-mode source --uvm-root ../UVM_Library --dry-run
python3 scripts/regression/run_vcs.py --pilot mac --test sb_mac_overflow_test
python3 scripts/regression/run_vcs.py --pilot router
```

`--uvm-mode vcs` is default and selects the installed UVM 1.2. Source mode
compiles one pinned source library and its DPI backend. `--seed` is deterministic;
`--timeout` bounds simulation wall time (120 s default), `--compile-timeout`
bounds compile/URG (300 s). `--plusarg=+SB_TIMEOUT_NS=10000` changes the simulation
watchdog, separately from wall time. The MAC random test also accepts
`--plusarg=+SB_RANDOM_CYCLES=1000`.

`--waves` requires VERDI_HOME, adds KDB/debug/FSDB compilation and demands a
waveform. `--coverage` adds code/assertion instrumentation, demands a VDB and
runs URG to create a dashboard. Functional covergroups live in UVM sources;
inspect their measured database scope rather than inferring closure from flags.
Use `--vcs-arg=...` for site-documented extra compile flags only. `--vcs`, `--urg`,
component roots and `--output-root` are overridable. No shell evaluates commands.

## Results and exit statuses

Every invocation creates a fresh directory; no previous executable/log can make
a new run pass. `manifest.json` records exact argument arrays, source/header/model
hashes, selected repositories/dirty state, UVM mode, seed, scope and requirement
IDs. `summary.json` records verdict, raw stage outcomes and artifacts. Logs are
`vcs-version.log`, `compile.log`, `run.log`, and optional `coverage.log`.

| Result | Exit | Meaning |
|---|---|---|
| PASS | 0 | Checks/marker, summaries and requested artifacts passed |
| PLANNED | 0 | Dry-run only; no tool or license evidence |
| FAIL | 1 | Wrong/missing result, diagnostic, nonzero simulator status or missing marker |
| ARTIFACT_FAILURE / COVERAGE_FAILURE | 1 | Requested waveform/database/report missing or report tool failed |
| SETUP_FAILURE | 2 | Missing input/tool/platform or mismatched MAC contract |
| COMPILE_FAILURE | 3 | Build failed or produced no executable |
| TOOL_FAILURE | 4 | Launch or recognized license failure |
| TIMEOUT / COMPILE_TIMEOUT | 124 | Wall-time deadline; Linux process group is terminated |

An in-simulation watchdog is a UVM fatal (`FAIL`), while the process watchdog
reports `TIMEOUT`. Both are failures; preserve the log to identify which fired.
Raw exit zero is insufficient: class tests require `SB_TEST_PASS` with nonzero
comparisons and zero UVM error/fatal summaries; all flows reject error/fatal and
assertion diagnostics. Router requires its own eight-command marker.

## Negative checks and debug

`--inject mismatch` corrupts one expected transaction; require `SB_MISMATCH`
following successful compile. `--inject timeout` intentionally retains the test
objection; require `SB_TIMEOUT` or the process timeout. Both should have no pass
marker. Missing VCS or a syntax error cannot qualify a behavioral negative test.
Open `verdi -ssf waves.fsdb` from that exact run directory. Keep each build's KDB,
FSDB and logs together. URG's report is `coverage_report/dashboard.html`.

## Local checking

`python3 -m unittest discover -s scripts/regression -p test_run_vcs.py -v` checks
runner failure sensitivity with controlled processes/mocks. It is not simulator
evidence. Optional `check_sv.py --pilot block|mac|router` uses pyslang plus UVM
source for semantic analysis; it does not run simulation or DPI.
