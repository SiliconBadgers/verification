# Validation and remaining work

[Home](../README.md) | [Setup](../SETUP.md) | [CAE record](CAE-RUN-RECORD.md)

Local work on October 5, 2026, branch `feat/block-uvm-vcs-verdi`:

| Check | Observed result | Limit |
|---|---|---|
| Final source style: Verible v0.0-3946-g851d3ff4 and Ruff 0.16.6 | Passed for 41 SV/header sources and six Python files; format then check | Not simulation |
| Primary block UVM semantic compilation, pyslang 12.0.0 with source UVM 1.2 | 0 errors; two pre-existing vendor empty-loop warnings | No runtime/DPI/VCS execution |
| Onboarding MAC semantic compilation | 0 errors; same two vendor warnings | Onboarding source only |
| Router semantic compilation | 0 errors, 0 warnings | Error-only integration fixtures |
| Stub C++ oracle, g++ 15.2, undefined-behavior sanitizer | 100 opcode/boundary cases passed | Temporary add/XOR/error semantics only |
| MAC C++ oracle, same compiler/sanitizer | 327,680 arithmetic vectors plus priority/overflow cases passed | Onboarding model only |
| Final Python runner suite, Windows Python 3.12.6 | 17 tests: 16 passed, one Linux-specific test skipped | Controlled processes/mocks are not VCS |
| Earlier Linux runner suite | All 17 tests passed before block-profile expansion | Final Linux rerun still useful on CAE |
| Default block and training-style run wrapper | Smoke/random dry-runs generated PLANNED manifests with STUB IDs | No simulation claim |
| Documentation | Local navigation links resolve; 35 unique traceable requirement rows | Architecture proposals remain open |

The final style, block semantic and model checks completed successfully after
an earlier automatic-review usage interruption. Commands are documented in
[SETUP.md](../SETUP.md) and the [runner guide](../scripts/regression/README.md).

## Required CAE evidence

VCS compilation/linking of class-based UVM and C++ DPI, positive and intentional
negative simulations, FSDB generation, URG reporting and interactive Verdi review
are **UNRUN**. The September 23 handout's reported versions/setup are incorporated
in SETUP.md; its register example does not validate this branch. Complete the
[CAE record](CAE-RUN-RECORD.md) with exact versions and run artifacts.

The primary DUT/protocol is a temporary stub. The PE MAC is an onboarding project.
Neither provides accelerator arithmetic, real memory/DMA, state continuity or
production-interface signoff. Those tests remain proposed in the plan.

AI assistance: OpenAI Codex; exact runtime model ID unavailable.
