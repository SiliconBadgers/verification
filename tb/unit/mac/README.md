# Onboarding MAC UVM environment

[Home](../../../README.md) | [CAE setup](../../../SETUP.md) |
[Block diagram](../../../docs/methodology/block-environment.md) |
[Add a block](../../../docs/ADDING-A-BLOCK.md)

This example exercises the verification infrastructure with the **onboarding PE
MAC**. It is not an accelerator DUT or evidence of accelerator numerical support.
The layout deliberately resembles `uvm-training`, so the path from the UART
exercise to a future accelerator block is easy to follow.

## From training to this environment

| Training location | Here | Responsibility |
|---|---|---|
| `agent/uart_if.svh` | [agent/sb_mac_if.sv](agent/sb_mac_if.sv) | Physical DUT signals and virtual-interface type |
| `agent/uart_seqit.svh` | [agent/sb_mac_item.svh](agent/sb_mac_item.svh) | Stimulus and observed transaction fields |
| `agent/uart_sequence.svh` | [agent/sb_mac_sequence.svh](agent/sb_mac_sequence.svh) | Directed/random operations; no expected-result injection |
| `agent/uart_sequencer.svh` | `uvm_sequencer#(sb_mac_item)` in the agent | Standard sequencer needs no empty custom subclass |
| `agent/uart_config.svh` | [common sb_agent_config](../../common/sb_uvm_base_pkg.sv) and `vif` config-db entry | Active/passive selection and interface binding |
| Driver and monitor | [driver](agent/sb_mac_driver.svh), [input monitor](agent/sb_mac_input_monitor.svh), [output monitor](agent/sb_mac_output_monitor.svh) | Drive pins; independently observe sampled controls and actual results |
| `agent/uart_agent.svh` | [agent/sb_mac_agent.svh](agent/sb_mac_agent.svh) | Compose driver/sequencer in active mode; retain both monitors in passive mode |
| `environment/env_top.svh` | [environment/sb_mac_env.svh](environment/sb_mac_env.svh) | Build components and connect analysis streams |
| `environment/uart_scoreboard.svh` | [scoreboard](environment/sb_mac_scoreboard.svh) and [predictor](environment/sb_mac_predictor.svh) | Compare independently predicted results with observed output |
| `test/test_top.svh` and test case | [test/sb_mac_base_test.svh](test/sb_mac_base_test.svh) and derived tests | Objections, completion, pass criteria and scenario selection |
| `test/verif_pkg.svh` | [sb_mac_pkg.sv](sb_mac_pkg.sv) | Ordered includes, UVM imports and DPI declaration |
| `top_tb/top_tb.sv` | [top_tb/sb_mac_top.sv](top_tb/sb_mac_top.sv) | Onboarding DUT, clock, config-db binding, watchdog and FSDB |
| `run/run.do` | [run/run.py](run/run.py) | Entry point into the maintained VCS flow; no ModelSim commands |

Headers are included by `sb_mac_pkg.sv`; do not compile them independently or
compile the package twice. The [runner](../../../scripts/regression/run_vcs.py)
owns package/interface/top ordering and C++ compilation.

## Read the example in this order

1. `top_tb/sb_mac_top.sv`: see the actual pins and virtual-interface binding.
2. `agent/sb_mac_item.svh`, interface and driver: understand the transaction and
   timed stimulus. Driver pin changes occur at falling edges; reset pulses occur
   strictly between clock edges.
3. Both monitors: input/control events are sampled at rising clock or falling
   reset; actual output is sampled 1 ps later, after NBA updates. Event IDs
   correlate observations. MAC has no valid/ready handshake.
4. `environment/sb_mac_env.svh`: input monitor -> predictor and input coverage;
   output monitor -> scoreboard and observed-result coverage; predictor -> expected.
5. Predictor/model and scoreboard: only observed input drives the independent
   expected accumulator. Output never feeds the predictor. Every stream publishes
   a fresh immutable item. Four-state observations detect X/Z before DPI conversion.
6. Tests and [bound assertions](sb_mac_assertions.sv): inspect what creates
   stimulus, what checks it and what allows the test to finish.

## Tests and checking

| Runnable test | Intent | Plan IDs |
|---|---|---|
| `sb_mac_smoke_test` | 25 corner operand pairs, signed products, hold, clear priority, short asynchronous reset and restart | MAC-001..003 |
| `sb_mac_random_test` | Smoke plus 1,000 seeded random cycles by default | MAC-001..003 |
| `sb_mac_overflow_test` | Smoke plus long legal accumulations crossing both signed 32-bit bounds | MAC-001..004 |

Pass requires nonzero comparisons, identical event IDs and exact bit patterns,
empty pending queues, zero mismatch count and zero UVM errors/fatals. Overflow
additionally requires both wrap directions. The final idle item and bounded
drain prevent stimulus completion from racing the final output observation.
The simulation watchdog and runner's wall timeout serve different purposes.

Input coverage includes operand categories/crosses and clear/enable combinations.
Observed output signs and predictor wrap events have separate coverage.
Assertions check clear, hold, known signals and asynchronous reset. Reaching a
bin does not replace independent output checking. No coverage is claimed until
a real VCS run produces reviewed evidence.

The passive agent can be embedded in a larger harness through
`uvm_config_db#(sb_agent_config)` at the agent's `config` key with
`is_active = UVM_PASSIVE`. The supplied base test intentionally expects an active
agent; a parent integration test must own stimulus and completion in passive mode.

## Reuse boundary

Reuse the [common in-order scoreboard](../../common/sb_uvm_base_pkg.sv),
configuration pattern, environment topology, runner and evidence conventions.
For another protocol, specialize its interface, transaction, monitors, model,
comparison and assertions. The MAC's fixed sampling delays and event counters
are not a generic accelerator handshake or reset policy. Follow the
[new-block guide](../../../docs/ADDING-A-BLOCK.md).
