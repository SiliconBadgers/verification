# Reusable block environment: training-style tour

[Home](../../README.md) | [CAE setup](../../SETUP.md) | [Diagram](../../docs/methodology/block-environment.md) | [Test plan](../../plans/block-verification-v0.1.md)

This is the primary example. The signal names and stub behavior are temporary
verification plumbing, explicitly authorized while real block interfaces evolve.
The [contract](contract.json) is not a production accelerator ABI.

## Familiar UART structure

| UART training file | New block file | Purpose |
|---|---|---|
| agent/uart_if.svh | [agent/block_if.sv](agent/block_if.sv) | Temporary pins |
| uart_seqit/config/sequence/sequencer | Corresponding block_*.svh in [agent](agent/) | Transaction, configuration and sequences |
| uart_driver.svh | [block_driver.svh](agent/block_driver.svh) | Timed request drive and response backpressure |
| uart_monitor.svh | [block_monitor.svh](agent/block_monitor.svh) | Separate input/output instances; observe actual handshakes |
| uart_agent.svh and uart_pkg.svh | [block_agent.svh](agent/block_agent.svh), [block_pkg.sv](agent/block_pkg.sv) | Active/passive composition and ordered includes |
| environment/env_top.svh | [environment/env_top.svh](environment/env_top.svh) | Build/configure/connect components |
| uart_scoreboard.svh | [block_scoreboard.svh](environment/block_scoreboard.svh), [predictor](environment/block_predictor.svh) | Independent expected versus observed streams |
| test/test_top.svh and test case | [test/test_top.svh](test/test_top.svh), tc_block_smoke/random | Objections, bounded drain, nonempty pass criteria |
| test/verif_pkg.svh | [test/verif_pkg.sv](test/verif_pkg.sv) | Environment/test includes and C++ DPI import |
| top_tb/top_tb.sv | [top_tb/top_tb.sv](top_tb/top_tb.sv) | DUT stub, clock/reset, vif config-db and FSDB |
| run/run.do | [run/run.py](run/run.py) | VCS entry point, replacing ModelSim commands |

Unlike the training test's manually preloaded expected queue, the predictor
consumes only independently observed accepted requests. The output monitor
supplies actual responses. Both streams publish fresh immutable objects into
the [shared scoreboard](../common/README.md).

## Placeholder signals and semantics

| Signals | Temporary meaning |
|---|---|
| clk, rst_n | 10 ns clock, asynchronous active-low stub reset |
| req_valid, req_ready | Request accepted on rising-edge valid && ready |
| req_id[15:0] | Request identity, copied into response |
| req_op[1:0], req_a/b[31:0] | 0: unsigned wrapping add; 1: XOR; 2/3: unsupported error |
| rsp_valid, rsp_ready | Response retires on rising-edge valid && ready |
| rsp_id[15:0], rsp_data[31:0], rsp_error | Matching ID, result (zero for unsupported), status |

The stub owns one request at a time, holds a blocked response stable and has no
DMA, persistent context or external side effects. The driver changes pins at
falling edges. Monitors sample accepted pins before rising-edge NBA updates.
The test applies deterministic output stalls and checks exact submitted,
accepted, observed and compared counts. Initial reset and reset/reuse **after
drain** are exercised; midflight reset/cancellation is not qualified here.

`tc_block_smoke` sends all opcodes and boundary data (16 total including reuse).
`tc_block_random` sends 100 seeded requests plus four directed post-reset items.
The common checker rejects empty, missing, extra or mismatched results. Bound
assertions check stable stalled payloads, known handshake controls, one-outstanding
ownership and reset clearing. Input opcode/operand bins and actual result/status
coverage are independent of the predictor.

## Replacing the placeholder for actual blocks

Copy this layout under a named block environment and replace its interface,
stub adapter, transaction/model/checks from a reviewed contract. Provisional
extensions could include compute shape/format fields, memory address/mask/write
fields or control descriptor/context fields. These are suggestions, not signals
implemented or accepted by other teams. Keep the shared topology and runner.
Use passive agents when a parent environment supplies stimulus; the supplied
`test_top` expects an active agent. Use a keyed scoreboard for reordered work.
See [ADDING-A-BLOCK.md](../../docs/ADDING-A-BLOCK.md).
