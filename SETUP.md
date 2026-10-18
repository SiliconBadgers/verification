# Verification setup

The obsolete standalone MAC DUT, runner and smoke test are retired. `make test`
now delegates to the current RTL-owned Matrix Unit suite; it is not independent
Verification-owned coverage or a claim that the retired accumulator interface
is still tested. Historical reports under `reports/` describe their recorded
revisions only and are not instructions for the current checkout.

## Current-design regression

Use Synopsys VCS `Y-2026.03_Full64`, Bash 3.2+, Make and Python 3.11+.
Keep RTL and Verification checkouts as siblings, or set `RTL_ROOT`.
On UW–Madison CAE Linux:

```sh
module load synopsys/vcs-mx/2026.03
make doctor
make test RTL_ROOT=../rtl
make test RTL_ROOT=../rtl MATRIX_UNIT_ARGS="--only array_8x8_acc32 --seeds 7"
```

The target calls `make -C "$RTL_ROOT" test-matrix-unit` and propagates failures.
It no longer uses the Software vector generator, the standalone MAC contract,
or a legacy MAC runner. The RTL checkout must contain the Matrix Unit runner
and its VCS helper, available in RTL revision
`7d78d3c9b326e218e8e26390ca523c5413c09751` and later compatible revisions.
See [the RTL test guide](https://github.com/SiliconBadgers/rtl/blob/main/tb/compute/Matrix_Unit/README.md)
for configurations, seeds, failure injection, result counts and logs under
`build/matrix_unit/vcs/` in the RTL checkout. Record both repository revisions.

The helper checks the exact VCS version, enables assertions, uses
`simv -exitstatus`, and bounds compilation and simulation time. Run Python and
Make on the CAE host; the helper uses `synopsys-run` there or a licensed native
installation elsewhere. There is no Icarus or Verilator simulation fallback;
Verilator is permitted for lint only. Missing tools are failed prerequisites.

## Tooling checks and remaining coverage

`make test-tooling` checks Make delegation, argument forwarding and failure
propagation with a fake Make target. These are Python tooling tests, not RTL
simulations. `make style` performs source formatting and lint checks.

Independent current-design unit/integration environments, coverage closure and
Verdi debug workflows remain open in issue #4. The routing pilot testbench is
retained; its [historical scope](tb/integration/rtl-stub-test.md) does not replace
a current VCS result or establish full-accelerator correctness.
