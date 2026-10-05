# Architecture-aligned block verification plan, v0.1

Draft dated October 5, 2026. Implements the first planning/environment increment
for [verification #2](https://github.com/SiliconBadgers/verification/issues/2),
[#3](https://github.com/SiliconBadgers/verification/issues/3) and
[#4](https://github.com/SiliconBadgers/verification/issues/4).

The immediate deliverable is a repeatable VCS block environment with independent
checking, bound assertions, functional coverage and Verdi debug support. The
primary DUT is a temporary request/response stub; `pe_mac` is an optional onboarding project; a separate routing integration test uses explicit
engine stubs. The broader plan is written now so Memory, Control and each
Compute team can use it while their interfaces are still proposals.

This is **not accelerator signoff**. The new Synopsys flows require execution on
a configured licensed host. A source file or planned test is not pass evidence.
See [requirements-v0.1.csv](requirements-v0.1.csv) for the stable requirement,
stimulus, test, checker, coverage and pass-criterion mapping, and
[block-environment.md](../docs/methodology/block-environment.md) for methodology
and the block verification diagram.

## Primary scaffold and onboarding scope

The main runnable profile is now `--pilot block`: a temporary request/response
stub with `tc_block_smoke` and `tc_block_random`, strongly following the UART
training structure. STUB-001..003 qualify plumbing, backpressure and drained
reset/reuse. These are invented scaffold semantics, not accelerator requirements.
The PE MAC is an onboarding project, retained as `--pilot mac`; MAC-* requirements
must never be counted as verification of an actual accelerator block.

## Source baseline and authority

The [central Architecture diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md)
is the authoritative shared view. Its candidate boxes are not a decision to
implement four independent engines. This plan links that diagram instead of
copying the accelerator into Verification.

| Repository | Inspected revision | Source authority / interpretation |
|---|---|---|
| Architecture | [`81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3`](https://github.com/SiliconBadgers/architecture/commit/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3) | MAC example contract is concrete; overall boundaries, numerical choices and ABI remain proposals |
| RTL | [`c01e870e7ca2d22a6c02e0322aba9cfb64d378fc`](https://github.com/SiliconBadgers/rtl/commit/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc) | Real MAC and routing experiment; Memory/Control controller deliverables and Compute1/Compute2 proposals remain open |
| Software | [`60ed9307a3e82e2fcb789fd8700a8fd3800a8599`](https://github.com/SiliconBadgers/software/commit/60ed9307a3e82e2fcb789fd8700a8fd3800a8599) | Profiling, graph/dependency evidence and numerical reference work; owns workload mapping and runtime/host integration |
| SoC | [`e618739e05b7e3152c8842d3eda0cce9ee7469a4`](https://github.com/SiliconBadgers/soc/commit/e618739e05b7e3152c8842d3eda0cce9ee7469a4) | Pinned composition and RISC-V integration harness; component gitlinks differ from sibling branch tips |
| Planning | [`c033694ae8d95c4e49ce4b6a413c68c5991cb269`](https://github.com/SiliconBadgers/planning/commit/c033694ae8d95c4e49ce4b6a413c68c5991cb269) | Current seven-team assignment map takes precedence over historical eleven-charter snapshots |
| Verification starting point | [`91a35e01f961195b1b635924d185dcfb17d6c79d`](https://github.com/SiliconBadgers/verification/commit/91a35e01f961195b1b635924d185dcfb17d6c79d) | Existing Icarus MAC and Verilator router checks, new work added on this branch |
| UVM library / training | `33e85d8ba594a478de41bbf38a72e037bfa8cbb3` / `a207f23d74d66e57ac1b074d2b6b78a8a6a7a8ba` | UVM 1.2 and UART training structure; neither establishes a validated VCS accelerator environment |

The `source_requirement` field in the CSV uses these source keys:

| Key | Requirement source |
|---|---|
| `SRC-MAC` | Architecture [contracts/mac-v0.json](https://github.com/SiliconBadgers/architecture/blob/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3/contracts/mac-v0.json) |
| `SRC-BOUNDARY` | Architecture [candidate boundaries](https://github.com/SiliconBadgers/architecture/blob/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3/contracts/accelerator-boundaries.md) and [system status](https://github.com/SiliconBadgers/architecture/blob/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3/contracts/system-boundaries-and-evidence.md) |
| `SRC-WORKLOAD` | Architecture [workload cases and matrix inventory](https://github.com/SiliconBadgers/architecture/blob/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3/docs/workload-cases.md) |
| `SRC-COMPUTE` | RTL [Compute assignment](https://github.com/SiliconBadgers/rtl/blob/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/docs/compute/START-HERE.md), [Compute1](https://github.com/SiliconBadgers/rtl/tree/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/research/compute1), [Compute2](https://github.com/SiliconBadgers/rtl/tree/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/research/compute2) |
| `SRC-CONTROL` | RTL [Control assignment](https://github.com/SiliconBadgers/rtl/blob/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/docs/control/START-HERE.md), [router experiment](https://github.com/SiliconBadgers/rtl/blob/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/docs/control/command-router.md); Architecture [slide map baseline](https://github.com/SiliconBadgers/architecture/blob/81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3/docs/register-maps.md) |
| `SRC-MEMORY` | RTL [Memory assignment](https://github.com/SiliconBadgers/rtl/blob/c01e870e7ca2d22a6c02e0322aba9cfb64d378fc/docs/memory/START-HERE.md) |
| `SRC-SOFTWARE` | Software [current assignment](https://github.com/SiliconBadgers/software/blob/60ed9307a3e82e2fcb789fd8700a8fd3800a8599/docs/START-HERE.md), [operation dependency map](https://github.com/SiliconBadgers/software/tree/60ed9307a3e82e2fcb789fd8700a8fd3800a8599/research/compute-mapping/2026-10-02-op-dependency-map) and [F32 recurrence study](https://github.com/SiliconBadgers/software/tree/60ed9307a3e82e2fcb789fd8700a8fd3800a8599/research/compute-mapping/2026-10-03-recurrence-multiplier-sensitivity) |
| `SRC-PLAN` | Planning [current teams](https://github.com/SiliconBadgers/planning/blob/c033694ae8d95c4e49ce4b6a413c68c5991cb269/docs/team-start.md) and [technical plan, numerical/state and evidence sections](https://github.com/SiliconBadgers/planning/blob/c033694ae8d95c4e49ce4b6a413c68c5991cb269/technical-plan.md) |
| `SRC-SOC` | SoC [integration scope](https://github.com/SiliconBadgers/soc/blob/e618739e05b7e3152c8842d3eda0cce9ee7469a4/docs/integration/README.md) and [pinned workflow](https://github.com/SiliconBadgers/soc/blob/e618739e05b7e3152c8842d3eda0cce9ee7469a4/docs/WORKSPACE.md) |
| `SRC-ENV` | Verification [current assignment](../docs/START-HERE.md), issues #3 and #4 |

The supplied September 23, 2026 CAE handout adds a reported tool baseline:
VCS `Y-2026.03_Full64`, Verdi `Y-2026.03` and URG `Y-2026.03`, using the
`synopsys/suite` module and `synopsys-run`. It supplies a starting setup procedure
in [SETUP.md](../SETUP.md), not current-branch execution evidence. Its procedural
UVM-import example does not exercise this class-based environment. Verify the
actual installed versions and successful license use in each recorded pilot run.

Do not update the SoC gitlinks as an incidental effect of running these tests.
The standalone new pilot may consume the explicitly selected sibling RTL/SoC
checkouts; its result must record those exact inputs. A SoC integration result
must use the recorded component combination or a separately reviewed proposed
combination. Neither silently tracks all repository `main` branches.

## Current direction and limits

- Compute1 and Compute2 **each** investigate the full operation set: matrix and
  vector arithmetic, projection/output head, attention, DeltaNet/recurrent state,
  convolution, norm/activation and layout. They do not split arithmetic and state
  responsibilities. Their research directories contain scaffolding at this
  baseline; this plan does not label either an accepted compute implementation.
- Memory specifies data movement, addressing, ports/arbitration, outstanding
  requests and buffer ownership. Control specifies acceptance, validation,
  dispatch, coordination and terminal status. Their interface proposals must be
  testable before widths and resource counts are final.
- Four-bit weight storage is a direction, not a selected arithmetic contract.
  INT4, a specifically defined FP4 format, activation precision, accumulator
  precision and persistent-state precision are separate decisions. The current
  INT8 MAC does not establish support for the proposed INT4/group-64 layout.
- The September 22 Q4_K_M profiling baseline mixes tensor formats. The September
  24 BF16 graph captures used by the October 2 dependency map have flash attention
  disabled; their structural counts cannot be substituted for the earlier
  CPU timing shares. The October 3 recurrence study identifies captured F32
  recurrence and explicitly uncalibrated shared-matrix penalties; it does not
  justify narrowing recurrence to the surrounding projection precision.
- SoC uses existing RISC-V cores in a simulation harness, C++ mailbox/RAM/MMIO
  adapters and RTL routing/stubs. It has no implemented tensor datapath/DMA in
  that harness. The Qwen callback observes host CPU execution and sends metadata;
  it is not accelerator offload. There is no new compiler team, custom CPU or ISA
  introduced by this verification work.

## Requirement and implementation status

Stable IDs survive renaming of tests or changes in implementation. Retire an ID
with a reason rather than reusing it for a different requirement. CSV status
values in v0.1 are:

| Status | Meaning |
|---|---|
| `pilot-authored-unvalidated` | New implementation exists on this branch; required VCS/Verdi execution is not established by the plan |
| `existing-pilot-vcs-unvalidated` | Existing test is used for the new VCS flow; historical Icarus/Verilator scope remains separate |
| `proposed` | Test intent, checker and coverage are specified; no runnable test or accepted final interface is claimed |

Record an execution outcome alongside a command, manifest and logs. Do not turn
a row into `passed` because a simulator executable returned zero, a different
backend ran, or a model-only test agreed with itself. A proposed `P-*` test ID in
the CSV is a work item, not a runnable UVM test name.

| Requirement group | First concrete evidence | Remaining boundary |
|---|---|---|
| `MAC-001` through `MAC-004` | `sb_mac_smoke_test`, `sb_mac_random_test`, `sb_mac_overflow_test`; independent model and bound local assertions | VCS run, functional/assertion coverage review and mutation sensitivity |
| `ENV-001` through `ENV-004` | Wrong-result and timeout injection, setup failure, bounded runner with recorded inputs and tool outcomes | Licensed host/version/compiler checks, Verdi inspection, reviewed coverage evidence |
| `INT-001`, `INT-002` | Existing `command_router_tb`: four unimplemented routes, invalid opcode/ABI, retained identity, backpressure, quiesce and stub reset | Real compute/memory integration, randomized outstanding traffic and visibility |
| `NUM`, `CMP`, `MEM`, `CTL`, `STATE`, `SYS` | Explicit scenarios, oracle and proposed exit criterion in the CSV | Accepted contracts, implementation and measured execution evidence |

## Layered test strategy

| Layer and requirement IDs | Stimulus and observations | Checking and completion criterion |
|---|---|---|
| Primitive / unit: `MAC-*`, `NUM-*` | Signed extrema/zero, enabled/held/cleared cycles, reset between clock edges, long positive and negative accumulations; later all encodings and numerical boundaries | Exact contract-defined bits for the MAC. Later format-specific decode/round/clip cases and independent kernel outputs; no tolerance invented before numerical policy |
| Compute block: `CMP-*` | Workload-derived shapes, single-token decode and actual prefill microbatches, tails, zero-sized/unsupported shapes according to contract, contention and output stalls | Observe accepted work, compare tensor and intermediate state results, detect missing/duplicate output, retire all owned work; exact or approved per-operation numerical rule |
| Controller: `INT-*`, `CTL-*` | Valid/invalid commands, changed pins after acceptance, busy/repeated doorbells, delayed engine/transfer completion, blocked completion, quiesce and error injection | Identity/ownership state model, stable backpressured payload, no unauthorized side effects, exactly one terminal result, and no premature visibility claim |
| Memory and integration: `MEM-*` | Load -> compute -> store with varied latency, arbitration, bank conflicts, masks/strides/tails; delayed and erroneous responses | Byte-addressed oracle plus accepted/outstanding/retired ledger; every response belongs to a live request; reuse only after the agreed visibility and release event |
| Stateful chains: `STATE-*`, `CMP-003/004` | Whole/chunked prefill, multiple decode steps, interleaved request IDs, reset/reuse, fault and optional checkpoint/replay | Compare KV/recurrent/convolution state at specified boundaries, preserve token order and context isolation; report invalidated partial state explicitly |
| Accelerator/SoC: `SYS-*` | Firmware submission ordering, capability query, rejected/unsupported work, software fallback and completion observation | Actual RTL path plus host reference, with stubs and adapters named; complete tensor comparison before claiming offload, end-to-end quality or speed |

### Numerical oracles and workload selection

Keep three references distinct, following `SRC-PLAN`: checkpoint/software
semantics, a deliberately quantized candidate, and a bit-defined hardware kernel.
Approximation error versus the checkpoint is different from a hardware mismatch
against its selected kernel contract. Define rounding, saturation/wrap,
conversion order, non-finite handling and comparison tolerance in the owning
contract before marking a numerical row executable.

Initial matrix cases use Architecture's selected weight inventory and Software's
trace shapes, including the tied embedding/output matrix. Respect `ggml` dimension
order, tensor type, source revision and physical graph microbatch size. Use
representative `M/N/K` plus dimensions immediately below/at/above a chosen tile
or packing boundary. Resource counts remain parameters. Exercise both prefill
and decode; arbitrary random dimensions do not replace recorded workload cases.

For packed weights, cover every encoding, group boundary, scale index, zero
block, extreme scale, ties, clipping, padding and unsupported format. Combining
group partials requires a common numerical domain. FP4 encodings and scaling
need their own oracle; an INT4 nibble decode is not an FP4 reference.

For attention, check Q/K normalization, RoPE, masking, cache write/read order,
QK -> softmax -> AV -> gate ordering and accumulation error against the selected
contract. For DeltaNet, check state decay, prediction, update and readout plus
convolution history. Record intermediate state to localize an error before it
propagates into final logits. The initial MAC pilot establishes none of those
larger numerical behaviors.

### Acceptance, completion, visibility and faults

For a handshaked block, the input monitor records work only at `valid && ready`;
the driver issuing an item is not acceptance. The MAC instead observes each
clock/reset event because it has no ready/valid protocol. The independent result
monitor supplies actual data to the scoreboard; no expected value is learned
from the DUT output.

Maintain separate events for command acceptance, compute completion, transfer
retirement and externally visible output/state. A key proposed integration test
finishes arithmetic while withholding the final write response. Terminal success
and buffer release must wait for the reviewed visibility rule (`CTL-003`,
`MEM-003`). Cover acceptance under backpressure and a held completion as distinct
states. A timeout detects lack of progress; it does not remove outstanding DMA.

For fault/reset, test idle, after acceptance, mid-compute, during a stalled write
and while completion is blocked. Stop new work, drain or invalidate according to
the agreed recovery contract, then verify safe reuse. Error status must retain
the correct sequence/context identity. The existing router reset only clears
fixture state with no external writes; it cannot discharge `CTL-004` or
`STATE-003`.

### State continuity

Mutable KV, recurrent and convolution state belongs to a request/sequence;
temporary GEMM partial sums have a different lifetime. Compare an uninterrupted
prompt/continuation with the same accepted chunking/token order; compare two
interleaved contexts with isolated execution. Probe repeated IDs, reset and reuse,
partially updated state, stale state after fault, and format/model revision
changes in a continuing context. Save/restore, rollback and cancellation are
proposed cases only when supported by an agreed contract; do not assert them as
implemented features. A KV pointer rollback alone does not restore recurrence.

## Regression and evidence gates

Exact commands live in the [runner guide](../scripts/regression/README.md).
Suggested initial seeds for review are `1`, `17` and `103`; these are a
reproduction starting set, not statistical coverage closure. Run directed smoke
before random cases; use the dedicated long overflow test for both wrap
directions. Keep a fixed reproducer for every discovered failure.

| Gate | Required evidence and proposed pass condition |
|---|---|
| G0: source/model/setup checks | Independent model boundary checks pass; source paths and UVM selection are explicit; absent tools/invalid inputs fail clearly; dry-run is labeled as such |
| G1: VCS unit pilot | VCS compiles/elaborates onboarding MAC + UVM + C++ DPI; all directed and selected random/overflow cases finish with nonzero comparisons, empty pending work and no UVM/assertion errors |
| G2: failure sensitivity | Mismatch injection fails from the intended numerical checker; timeout injection fails from the intended watchdog; missing-tool/setup failure is classified separately. A setup failure cannot satisfy a negative simulation test |
| G3: VCS integration pilot | The existing router's eight command cases pass, including unsupported-route status and quiesce; fixture limitations are stated in the report |
| G4: Verdi and coverage | Open an actual failing run in Verdi, correlate expected/actual/assertion evidence with waveform state, inspect functional/code/assertion coverage and explain every relevant missing case |
| G5: one real integrated compute path | Replace one agreed fixture with real RTL plus modeled/real memory traffic; check tensors, delayed visibility, state/reset/fault and backpressure before claiming block integration |

No fixed coverage percentage is an acceptance substitute. First enumerate the
required bins/properties per row, collect real coverage, review unreachable or
excluded behavior with the owner, then set a justified closure target. Record
which requirements remain untested even when code coverage appears high. A
code-coverage toggle, a reached functional bin and a passing assertion provide
different evidence and should remain distinguishable.

A run record needs date/host, simulator/debug/compiler versions, exact source and
contract revisions, dirty-worktree state or source hashes, source-file manifest,
UVM mode/version, command/seed/test/parameters, input hashes, compile/run exit
status, watchdog outcome, checker/assertion counts and coverage/database paths.
Keep generated databases and licensed files out of Git; check in small reports
with the reproduction command and limitations. Cross-repository published
evidence should use clean published component commits, with any local experiment
changes explicitly identified.

## Next work and unresolved contracts

These are proposed review handoffs, not assignments to named individuals.

| Priority | Handoff | Evidence needed to make the next tests concrete |
|---|---|---|
| Now | Verification with CAE/site support | Reproduce the supplied September 23 handout setup, record actual VCS/Verdi/compiler versions and license checkout; execute G0-G4 and retain results |
| Now | Verification with Top-Level Control / Architecture | Acceptance and busy behavior, descriptor validation, sequence identity, completion visibility, IRQ/ack and reset/quiescence proposal |
| Now | Verification with Memory Control | Address units/ranges, layout, masks/alignment, allowed ordering, outstanding count, response identity and buffer release condition; executable load/compute/store trace |
| In parallel | Verification with each of Compute1 and Compute2 | Full operation map, parameterized interface assumptions, numerical formats, shared-resource scheduling and state lifetime; run the same functional cases against both proposals |
| In parallel | Verification with Software | Reproducible shapes/formats and continuation cases, model/trace hashes, independent numerical kernels, quantization thresholds and fallback boundary |
| Next | Verification with SoC | Reviewed component pins and one real compute path; distinguish local-memory first-chip assumptions from HBM/platform studies |

The plan can progress before final lane counts or buffer depths are chosen.
Acceptance, ownership, numerical semantics, state lifetime and recovery must be
explicit enough to distinguish correct behavior from a plausible waveform.

AI assistance for this draft: OpenAI Codex; exact runtime model ID was not
available to the agent. No model ID is inferred.
