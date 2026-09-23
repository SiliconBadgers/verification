# Verification

Develop the architecture-based test plan, justify a methodology at every layer, and build/harden a runnable Synopsys verification environment.

## Start here

1. Read [the current assignment and artifact locations](docs/START-HERE.md).
2. Complete [AI setup and the capture check](docs/git-ai.md) before AI edits or
   your first commit. Every clone needs its local hook activated.
3. Work on a branch and open a PR for `@abhinavnandwani` using
   [CONTRIBUTING.md](CONTRIBUTING.md). Main requires a code-owner approval;
   admins can bypass.

## Current issues

- [Architecture-based test plan](https://github.com/SiliconBadgers/verification/issues/2)
- [Per-layer methodology using Synopsys](https://github.com/SiliconBadgers/verification/issues/3)
- [Runnable and hardened verification scaffold](https://github.com/SiliconBadgers/verification/issues/4)

## Repository structure

| Location | Purpose |
|---|---|
| [plans/](plans/README.md) | Versioned test plan and requirements-to-tests/coverage mapping for issue #2. Use stable requirement/test IDs; identify assumptions and proposed completion criteria. |
| [docs/methodology/](docs/methodology/README.md) | Per-layer methodology matrix, environment diagram, alternatives and feasibility evidence for issue #3. Identify the Synopsys role at each layer. |
| [models/](models/README.md) | Independent reference models and documented numerical/timing semantics. Cite provenance and explain how the model differs from the implementation it checks. |
| [tb/unit/](tb/unit/README.md) | Unit pilot testbenches, stimulus, checking and coverage. The existing tb/pe_mac_smoke_tb.sv remains an Icarus example, not completion of the Synopsys requirement. |
| [tb/integration/](tb/integration/README.md) | Integration/SoC pilot and its connection to RTL. Label every stub and the scope of behavior actually checked. |
| [scripts/regression/](scripts/regression/README.md) | Team-owned VCS compile/run, Verdi debug/coverage and deterministic regression entry points for issue #4. These are deliverables to implement, not working commands supplied by this folder. |

## Current material and scope

An independent Icarus MAC smoke test exists. Synopsys setup, unit/integration pilots and the test/methodology proposals remain open team deliverables; this refresh does not claim they have run.

[Shared diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md) · [Software evidence](https://github.com/SiliconBadgers/software/tree/main/experiments/llama-cpp/2026-09-22)

[CHARTER.md](CHARTER.md) and [OBJECTIVES.md](OBJECTIVES.md) describe the
longer-term purpose. Current issues and the starting guide specify the work
assigned now. [SETUP.md](SETUP.md) describes existing example commands and scope.
