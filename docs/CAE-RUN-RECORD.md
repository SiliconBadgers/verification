# CAE run record template

[Setup](../SETUP.md) | [Validation status](VALIDATION.md) | [Test plan](../plans/block-verification-v0.1.md)

Copy this template into a dated file under `experiments/` after a real run.
Leave unexecuted entries as **UNRUN**. Keep licenses, credentials and generated
databases out of the repository; retain their approved artifact locations.

- Date / operator / execution host:
- Scope: onboarding MAC / routing with error-only stubs / named accelerator DUT:
- Verification commit and dirty state:
- RTL / Architecture contract / SoC / UVM source revisions:
- VCS, Verdi, URG, Python and VCS C++ compiler versions:
- Site module/container setup and selected UVM mode:
- Exact command, test, seed, parameters and timeouts:
- Run directory / manifest / summary / logs / FSDB / VDB / URG report:

| Qualification | Observed result and evidence | Status |
|---|---|---|
| Directed smoke | Nonzero comparisons, no pending/error work | UNRUN |
| Selected random seeds | List exact seeds and reproduced outcomes | UNRUN |
| Both overflow directions (onboarding MAC only) | Exact bits plus wrap counts | UNRUN |
| Wrong-result detection | Intended mismatch diagnostic; no pass marker; compile succeeded | UNRUN |
| Timeout | Intended watchdog; no pass marker; bounded process cleanup | UNRUN |
| Setup/tool failure | Classified outcome and preserved diagnostic | UNRUN |
| Routing experiment | Eight cases; all endpoints still error-only stubs | UNRUN |
| Verdi debug | First divergence/time, expected versus observed, matching KDB/FSDB | UNRUN |
| Coverage review | DUT scope, functional bins, assertions, gaps/exclusions and rationale | UNRUN |

List requirement IDs exercised, open contract questions, discovered bugs,
proposed next tests, and reviewer. Record pass/fail at the tested scope; an
onboarding/stub pass does not close accelerator requirements.
