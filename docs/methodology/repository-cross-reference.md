# Repository cross-reference for the block UVM pilot

Source audit: 2026-10-05. This records the inputs to the proposed environment,
not a licensed simulator qualification result. Scope follows verification
[issue #2](https://github.com/SiliconBadgers/verification/issues/2),
[issue #3](https://github.com/SiliconBadgers/verification/issues/3) and
[issue #4](https://github.com/SiliconBadgers/verification/issues/4).

## Source snapshot

The following are the checked-out commits inspected for this work. Record the
actual source revisions again for each run; sibling repository heads and SoC
submodule pins are separate configurations.

| Repository | Full commit | Role |
|---|---|---|
| verification | `91a35e01f961195b1b635924d185dcfb17d6c79d` | Existing MAC smoke test, command-router test, current assignment |
| UVM_Library | `33e85d8ba594a478de41bbf38a72e037bfa8cbb3` | Accellera UVM 1.2 implementation and vendor examples |
| uvm-training | `a207f23d74d66e57ac1b074d2b6b78a8a6a7a8ba` | UART UVM teaching environment |
| uvm-training/UVM_Library | `33e85d8ba594a478de41bbf38a72e037bfa8cbb3` | Same UVM library revision as the sibling clone |
| uvm-training/CHIPKIT | `11c76bbb996a54ca93551cbdc9ba23f48c80918e` | UART RTL exercised by training |
| rtl | `c01e870e7ca2d22a6c02e0322aba9cfb64d378fc` | MAC and command-router RTL |
| soc | `e618739e05b7e3152c8842d3eda0cce9ee7469a4` | Engine stubs and routing test assembly |
| architecture | `81fdeae2d4d3facd3e88a0c06a7b577ed1a7d2e3` | Contracts and shared architectural direction |
| planning | `c033694ae8d95c4e49ce4b6a413c68c5991cb269` | Workload and team planning |
| software | `60ed9307a3e82e2fcb789fd8700a8fd3800a8599` | Independent MAC vectors and workload evidence |

Training's committed `.gitmodules` still names
`git@github.com:ihagedo/UVM_Library.git`. This checkout has a local Git-config
override to `https://github.com/SiliconBadgers/UVM_Library.git`; the source file
was not changed. A fresh recursive checkout can therefore encounter the old
URL. The proposed verification pilot reads an explicit `UVM_HOME` and does not
depend on training's submodule URL or compile both UVM copies.

## What each environment contributes

| Environment | Existing behavior | Reuse decision |
|---|---|---|
| verification MAC smoke | Icarus runner; independent software vectors plus integer checks for signed products, hold, clear, wraparound and asynchronous reset | Preserve as a fast independent baseline. A new VCS/UVM pilot must agree with the existing MAC contract; it does not establish the eventual accelerator numeric format. |
| verification command-router test | Eight command cases using RTL's command package/router and SoC engine stubs; identity, backpressure, quiesce/drain, bad opcode/ABI and reset | Port its source assembly to VCS as a directed integration pilot. The endpoints return errors and implement no tensor datapath or DMA. |
| UVM_Library | UVM class library, factory/phases/configuration/TLM/sequences and simulator examples | Consume as a versioned dependency; do not copy or modify the library to make a project environment. Preserve license/provenance. |
| uvm-training | Factory-created UART agent, config object, sequence/driver/monitor, environment and scoreboard; four fixed loopback bytes | Reuse component organization and learning references. The UART protocol, stimulus, checker and ModelSim scripts are not an accelerator base environment. |

The central design remains the
[Architecture diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md).
The block-level verification diagram describes stimulus and checking around
an RTL boundary; it does not revise that system architecture.

## UVM and simulator provenance

`UVM_Library/README.txt` identifies version 1.2 and the Apache-2.0 license.
`src/macros/uvm_version_defines.svh` defines major revision 1 and minor revision 2.
Both local library copies have the same Git revision. This is the historical
UVM 1.2 baseline, not a claim that it is the latest IEEE 1800.2 implementation;
Accellera lists these separately on its
[official download page](https://www.accellera.org/downloads/standards/uvm).

The vendor-supplied
[VCS example makefile](https://github.com/SiliconBadgers/UVM_Library/blob/33e85d8ba594a478de41bbf38a72e037bfa8cbb3/examples/Makefile.vcs)
provides this source-compilation pattern:

```sh
vcs -sverilog -timescale=1ns/1ns +acc +vpi \
  +incdir+"$UVM_HOME/src" "$UVM_HOME/src/uvm.sv" \
  "$UVM_HOME/src/dpi/uvm_dpi.cc" -CFLAGS -DVCS <project sources>
```

This is a reference pattern, not the complete project command or a verified
CAE invocation. In the library, `uvm_dpi.cc` includes its C/C++ helpers and
`uvm_hdl.c` selects `uvm_hdl_vcs.c` when `VCS` is defined. The example warns that
`+acc` and `+vpi` have a performance cost; enable visibility needed by the chosen
debug/backdoor flow rather than treating every historical flag as mandatory.
Compile the UVM package once, before project classes. A separately qualified
vendor-precompiled UVM mode must replace source-mode UVM compilation, not add a
second package or a mismatched DPI implementation.

Training's
[run/run.do](https://github.com/SiliconBadgers/uvm-training/blob/a207f23d74d66e57ac1b074d2b6b78a8a6a7a8ba/run/run.do)
creates ModelSim libraries using `vlib`/`vmap`/`vlog`, compiles `uvm_pkg.sv` with
`+define+UVM_NO_DPI`, then invokes `vsim`. It offers no VCS or Verdi qualification.
Its no-DPI choice disables UVM's DPI features; it is not evidence that a project
C++ predictor has been compiled or checked. The new predictor's DPI source is a
separate dependency from UVM's own DPI source.

[VCS](https://www.synopsys.com/verification/simulation/vcs.html) supplies the
simulation engine, SystemVerilog execution and DPI integration.
[Verdi](https://www.synopsys.com/verification/debug.html) supplies debug and
coverage analysis. Record the actual CAE tool/compiler versions and successful
license checkout from execution; public product descriptions and local source
inspection cannot establish availability or release-specific FSDB support.

## Training limitations that the base must address

These are static findings at the recorded training revision, not results from
running or modifying the training example.

| Training source and finding | Consequence for a reusable block environment |
|---|---|
| `test/tc_direct_urx_utx.svh` pushes four expected transactions directly into the scoreboard; `agent/uart_sequence.svh` independently hardcodes the same four bytes | Predict from observed accepted DUT inputs. Do not use the sequence's intended traffic as evidence of acceptance. |
| `environment/uart_scoreboard.svh` declares `expected` as `uvm_analysis_imp_observed`, and does not construct/connect it | Provide correctly typed and connected expected/actual channels. The unused `write_expected()` function is not a working predictor path. |
| Same scoreboard pops without checking queue emptiness, and `check_phase` does not reject leftover expected transactions | Detect unexpected/duplicate output, missing output, nonzero-count violations and undrained queues. Include bounded end-of-test drain. |
| `agent/uart_seqit.svh` stores monitored data in two-state `bit` values | Check four-state DUT samples for unknowns before conversion or DPI calls, so X/Z cannot silently become a passing numeric value. |
| `agent/uart_monitor.svh` always waits for a rising reset edge; the driver alone consults configurable reset polarity | Share reset semantics, invalidate in-flight expectations on reset, and verify reset during traffic. |
| `agent/uart_agent.svh` unconditionally builds driver and sequencer | Support active/passive reuse when block agents become monitors in integration environments. |
| The test waits a fixed `#100us` after its sequence | Complete on checked/retired transactions with a deadline, rather than assuming an elapsed delay proves completion. |
| No functional covergroups, bound SVA or C++ predictor in the training environment | Add requirement-driven coverage and protocol assertions around the actual block interface, with explicit numerical model semantics. |
| `top_tb/top_tb.sv` uses wildcard virtual-interface configuration and a loopback UART DUT | Scope configuration to the intended agent and replace the protocol adapter for each block. Retain UART only as a training reference. |

## Existing integration pilot: VCS assembly and checks

The directed router test can compile without UVM or a C++ predictor. Use one
consistent revision set, with an ordered file list such as:

```text
rtl/rtl/common/command_pkg.sv
rtl/rtl/control/command_router.sv
soc/sim/engine_stub.sv
soc/sim/command_router_test_top.sv
verification/tb/command_router_tb.sv
```

The top is `command_router_tb`. The baseline success marker is:

```text
PASS router: 8 commands, all routes, ABI error, backpressure, quiesce, reset
```

The baseline test has a 10,000 ns watchdog. Both router and engine-stub assertions
must be enabled and assertion failures must fail the runner. Require the pass
marker, a successful process exit, no fatal/error diagnostics and a wall-clock
deadline. The marker proves only the named directed fixture cases, not complete
command protocol coverage. In particular, this fixture does not test real DMA,
memory visibility, CPU execution or tensor arithmetic.

For runner qualification, demonstrate three independent failures: corrupt a
checked result to exercise mismatch handling; prevent retirement to exercise
simulation/wall-clock timeout; and supply an invalid tool/source setup to
exercise preflight/compile failure. A host-only fake-tool test can qualify
runner error handling, but cannot replace these checks on VCS and real RTL.

## Migration sequence

| Stage | Concrete change | Evidence needed before expanding scope |
|---|---|---|
| Base pilot | UVM 1.2 source mode, one block adapter, accepted-input/output monitors, independent DPI predictor, strict scoreboard and bound assertions | Unit compile/run in licensed VCS; deterministic seed; nonzero checks; coverage; deliberate mismatch and timeout failures |
| CAE debug | Qualified VCS/Verdi release, isolated build/run directories, waveform and coverage artifacts | Reopen the failing run in Verdi; observe assertions and source correspondence; record versions without secrets |
| Directed integration | Existing router plus explicit engine stubs under VCS | All directed checks and injected failure cases pass/fail as intended; no tensor/DMA claim |
| Real block integration | Replace each stub only after an interface contract and independent reference behavior exist | Accepted/completed/visible distinctions, latency/backpressure/reset, per-block coverage and replayable regressions |
| SoC reuse | Passive block monitors, shared transaction contracts, software-driven system tests | Pinned SoC component revisions, software/RTL agreement, real memory/interrupt/error/reset behavior |

UVM is justified where transaction stimulus, component reuse and coverage help.
Direct SV is sufficient for the current small routing pilot. C++ is justified
for independent numeric models and reuse of trustworthy software evidence;
calling a model through DPI alone does not establish its independence.
