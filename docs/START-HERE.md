# Verification: current work

Develop the architecture-based test plan, justify a methodology at every layer, and build/harden a runnable Synopsys verification environment.

## Assignment

- [Architecture-based test plan](https://github.com/SiliconBadgers/verification/issues/2)
- [Per-layer methodology using Synopsys](https://github.com/SiliconBadgers/verification/issues/3)
- [Runnable and hardened verification scaffold](https://github.com/SiliconBadgers/verification/issues/4)

1. Map primitives/units, controllers, memory/control integration and accelerator/SoC boundaries to requirements, tests, reference checks, coverage and pass criteria. Include numerical, state, protocol, error and reset behavior.
2. Evaluate C++ models/harnesses and SystemVerilog/UVM per layer; language/framework choices are not predetermined. Explain model independence and connections to RTL.
3. Verify actual Synopsys VCS and Verdi versions, execution environment and license access. Keep site paths and licenses outside Git.
4. Build a unit pilot and an integration pilot, with explicit stubs where needed. Include repeatable commands, seeds, timeouts, logs and coverage; demonstrate wrong-result, timeout and setup/tool failures are detected.
5. Progress the plan, methodology and pilots together using current interfaces and assumptions. Do not wait for final RTL or claim stub-only coverage as finished accelerator verification.

## Starting evidence

- [Central diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md)
- [Recorded Software profiling package](https://github.com/SiliconBadgers/software/tree/main/experiments/llama-cpp/2026-09-22)

## Artifact locations

| Location | What belongs here |
|---|---|
| [plans/](../plans/README.md) | Versioned test plan and requirements-to-tests/coverage mapping for issue #2. Use stable requirement/test IDs; identify assumptions and proposed completion criteria. |
| [docs/methodology/](../docs/methodology/README.md) | Per-layer methodology matrix, environment diagram, alternatives and feasibility evidence for issue #3. Identify the Synopsys role at each layer. |
| [models/](../models/README.md) | Independent reference models and documented numerical/timing semantics. Cite provenance and explain how the model differs from the implementation it checks. |
| [tb/unit/](../tb/unit/README.md) | Unit pilot testbenches, stimulus, checking and coverage. The existing tb/pe_mac_smoke_tb.sv remains an Icarus example, not completion of the Synopsys requirement. |
| [tb/integration/](../tb/integration/README.md) | Integration/SoC pilot and its connection to RTL. Label every stub and the scope of behavior actually checked. |
| [scripts/regression/](../scripts/regression/README.md) | Team-owned VCS compile/run, Verdi debug/coverage and deterministic regression entry points for issue #4. These are deliverables to implement, not working commands supplied by this folder. |

## What runs today

An independent Icarus MAC smoke test exists. Synopsys setup, unit/integration pilots and the test/methodology proposals remain open team deliverables; this refresh does not claim they have run.

These folders organize the work; they do not complete the issues. Use the
existing evidence now and publish useful intermediate results. Arrange a team
meeting this week to divide the work and agree on next steps.

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) before editing or committing.
