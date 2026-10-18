# Contributing

Start with `README.md` and `docs/START-HERE.md`. The linked issues define the
current assignments. Divide the work within your team and record ownership in
the issue. Use existing evidence and explicit assumptions to work in parallel.

## Branch, validate, propose

1. Accept any pending organization invite and check repository write access.
2. Create a descriptive branch from current `main`, then make the issue's change.
3. Keep editable diagram sources and link the central architecture diagram.
   Distinguish proposed interfaces, stubs, measured results and estimates.
4. Record source revisions, commands, inputs, tool versions, assumptions and
   relevant pass/fail evidence. Use `SETUP.md` for existing example checks;
   those checks only validate the example. Mark unrun licensed-tool checks as
   unrun, not passed. Keep secrets, licenses, PDKs, model weights and generated
   build/simulation databases out of Git.
5. Commit your changes with a clear description.
6. Push the branch and open a PR linked to the issue for `@abhinavnandwani` to
   review. Main requires one code-owner approval; admins can bypass. Do not
   close research/scaffold issues just because folders or templates exist.

Preserve recorded experiments and slide baselines. Put new runs and proposals
in their own locations so reviewers can compare them. A change in architecture
or team scope needs an explicit proposal, not a silent documentation rewrite.

## Formatting and style checks

Follow the [SystemVerilog coding standards](https://app.notion.com/p/3eb38826be1b81129170e99b72affdca).
Run `make format` to apply Verible formatting and Ruff fixes, then `make style`
to check formatting and lint without changing files. CI runs the same check on
pull requests. Verible v0.0-3946-g851d3ff4 and Ruff 0.16.6 are pinned in CI.
Install the pinned Verible release separately and check its version. Ruff is
provided by the locked uv `dev` group; do not install a separate global copy.
Python 3.11+ and uv 0.12.23+ are required; see [SETUP.md](SETUP.md).

`style.json` selects RTL/testbench/simulation SystemVerilog and Python scripts
owned by this repository. New files in those directories are picked up
automatically. Ignored files, third-party dependencies, and submodule contents
are excluded. A scaffold with no SystemVerilog explicitly reports that there
are no SV inputs; it does not claim RTL validation. Run component checks in
each owning repository. Style checks do not replace elaboration or simulation.

## Simulation baseline

RTL simulation results must use Synopsys VCS Y-2026.03_Full64 with assertions
and `-exitstatus` enabled. Verilator may be used for lint only. Include exact
source/dependency revisions, commands, seeds, test/check counts and logs.
Follow [SETUP.md](SETUP.md) for the shared VCS launcher; missing access is a
failed prerequisite, not a reason to substitute another simulator. Preserve
earlier dated results as historical evidence.
