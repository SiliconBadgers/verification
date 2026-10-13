# Verification setup

The MAC example uses Synopsys VCS `Y-2026.03_Full64`, Make and Python 3.11+.
Keep Architecture, Software, RTL and Verification checkouts as siblings.
The RTL checkout must include the VCS launcher at `scripts/vcs.py`, introduced
by [RTL PR #14](https://github.com/SiliconBadgers/rtl/pull/14). Use the RTL
revision recorded in the validation report or the updated SoC workspace pin.

On UW–Madison CAE Linux:

```sh
module load synopsys/vcs-mx/2026.03
make doctor
make test
```

Run Python and Make on the host. The shared helper invokes tools through
`synopsys-run` on CAE, or directly on another licensed Linux installation.
It checks the exact version, enables assertions, supplies a default
`1ns/1ps` timescale and runs `simv -exitstatus`. Compilation and simulation
have 900-second limits. There is no Icarus or Verilator simulation fallback.
Verilator may be used for lint only.

The reference-vector generator remains in Software, the RTL in RTL, and the
independent testbench and result checks in Verification. Override `RTL_ROOT`,
`MODELS_ROOT` and `CONTRACT` for a different checkout layout. Record all component
revisions with results; the coordinated VCS runner and RTL helper must both be
present.

```sh
python3 run.py --rtl-root ../rtl --vectors build/mac-vectors.txt
```

Logs, actual counts, input hashes, elapsed times and exit codes are saved under
`build/mac/vcs/`. Use `--out` to preserve separate runs. Success requires both
MAC PASS markers, positive check counts and a zero simulator exit status.
This example checks signed arithmetic, hold, clear, reset and overflow. It does
not establish full-accelerator correctness or coverage closure.

The earlier SoC routing experiment is documented in
[tb/integration/rtl-stub-test.md](tb/integration/rtl-stub-test.md); its historical
simulator results do not replace a current VCS run. See the
[workspace guide](https://github.com/SiliconBadgers/soc/blob/main/docs/GETTING_STARTED.md)
for the combined repository layout.
