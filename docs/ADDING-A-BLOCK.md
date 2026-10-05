# Bring up the next block

[Home](../README.md) | [Block diagram](methodology/block-environment.md) |
[Test plan](../plans/block-verification-v0.1.md) | [Training-style example](../tb/unit/mac/README.md)

The onboarding MAC qualifies the infrastructure. Adding an accelerator block is
a separate verification increment with its own interface, reference and evidence.
Keep the MAC as a fast regression for the infrastructure while adding the new
environment under `tb/unit/<block>/` with the same familiar training layout.

## 1. Agree on observable behavior

Record a reviewed contract link/revision and answer these questions before
calling the new environment a DUT test:

| Boundary | Define |
|---|---|
| Input | Fields/units, valid encodings, accepted event, ownership and payload stability under stalls |
| Output | Result identity, ordering, expected count, error outcomes, latency bounds if guaranteed |
| Numerical | Signedness, packing/scales, rounding, wrap/saturation, intermediate precision, exact/tolerant comparisons |
| State | Context/token identity, initialization, persistence, sequence isolation and invalidation |
| Memory | Accepted/outstanding/retired traffic, output visibility and resource-release rule |
| Reset/fault | Stop/drain/cancel policy, pending work, terminal status and conditions for safe reuse |

If RTL is not ready, use a behavioral stub **with its own named provisional
contract**, and label every run as stub-only. A request/response stub can validate
agent plumbing and checker sensitivity; it cannot settle a production ABI or
close compute/memory coverage. Replace the stub using the same adapter boundary
once real RTL arrives. Keep a meaningful independent oracle when replacing it.

## 2. Instantiate the training-style structure

```text
tb/unit/<block>/
  agent/          interface, transaction, config, sequence, driver, monitors, agent
  environment/    predictor/model adapter, scoreboard, coverage, env
  test/           base test and named scenario classes
  top_tb/         DUT or explicitly labeled stub, clock/reset and vif binding
  run/            thin entry point into the maintained runner
  <block>_pkg.sv  ordered class includes
  <block>_assertions.sv
  README.md       contract, sampling, cases, commands, status and limitations
```

Use the MAC example to understand the composition; change its protocol-specific
code deliberately. Reuse `sb_uvm_base_pkg` instead of duplicating common
scoreboard accounting. Define a block-specific configuration type where needed,
and retain passive monitors when the parent environment owns stimulus.

The driver translates sequence items to timed pins. The input monitor reports
**observed acceptance**, not successful `finish_item()`. For ready/valid, observe
`valid && ready` and assert payload stability while stalled. Define clocking-block
or equivalent sampling skews so the testbench cannot race the DUT. The MAC's
negedge/posedge+1ps convention is specific to that example.

## 3. Connect independent checking

Use the documented topology: input monitor -> predictor and coverage; output
monitor -> actual scoreboard stream and coverage; predictor -> expected stream;
bound SVA -> local protocol/reset invariants. Keep expected state independent
of DUT outputs and driver intentions. Preserve X/Z information through monitors;
reject or explicitly model unknown values before converting to two-state C++.

For in-order traffic, specialize the common scoreboard's identity/payload check.
For reordered traffic, maintain an ID/context/epoch-keyed ledger, and check
duplicate, missing and unexpected completions. Record arithmetic completion
separately from externally visible output. An elapsed timeout cannot cancel DMA.
Stateful models must persist across commands until the contract says otherwise.

Define completion explicitly: expected work count, all accepted work retired,
no pending comparisons, zero unexpected results and no errors. Bound drain time;
do not copy training's fixed delay as a proof of completion.

## 4. Add the first executable tests and runner profile

Start with reset/idle, one legal transaction, boundary values, stalled input/output,
invalid input, reset/fault with work outstanding and safe reuse as applicable.
Give each scenario a stable plan ID. Add named functional bins and bound
assertions whose scope matches the contract; document unimplemented cases.

In `scripts/regression/run_vcs.py`, extend the pilot choices, explicit ordered
`source_files`, top/test selection, required contracts and pass-marker policy.
Keep C++/UVM selection in one place. Record stub-versus-RTL scope, model/contract
hashes and precise requirement IDs in the manifest. Update the runner tests for
the new profile; don't mark the broader plan executed simply because it builds.

The `run/` wrapper should delegate to this shared runner, as the onboarding
example does. Do not create a second shell flow with different failure rules.
Never mix built-in UVM with a source library in one compile.

## 5. Establish trust and retain evidence

Run local model checks and style/semantic checks first, then on CAE establish:

1. A passing, nonempty VCS test with the intended DUT/stub and source revisions.
2. A deliberate wrong result rejected by the intended checker; a compiler error
   is not a qualifying negative result.
3. A timeout and a missing-tool/setup failure, separately classified.
4. A reproducible seeded case with separate logs/FSDB/VDB and a Verdi review of
   the first divergence; review DUT functional/code/assertion coverage scope.
5. A small [run record](CAE-RUN-RECORD.md), updated requirement status and a PR
   listing remaining assumptions. Preserve generated databases outside Git.

Only then grow random scenarios, traffic overlap and integration. The
[plan's gates](../plans/block-verification-v0.1.md#regression-and-evidence-gates)
separate infrastructure qualification from verification of an actual accelerator
block and from system-level confidence.
