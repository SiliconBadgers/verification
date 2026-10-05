# Shared UVM components

[Home](../../README.md) | [Onboarding example](../unit/mac/README.md) |
[New-block guide](../../docs/ADDING-A-BLOCK.md)

`sb_uvm_base_pkg.sv` is compiled once after `uvm_pkg` and before block packages.

- `sb_agent_config`: common active/passive choice. A block can extend it with
  a typed virtual interface and contract-specific parameters.
- `sb_in_order_scoreboard#(ITEM)`: typed expected/actual analysis endpoints,
  callback-order-independent queues, comparison/mismatch counts, rejection of
  null observations, empty-test detection and a pending-work check at test end.

Subclass `items_match(expected, actual)` and `mismatch_description(...)`.
Optionally override `sample_actual(item)` for observed-output coverage. The
default comparison fails deliberately until a block supplies its identity and
payload policy. Publish a new immutable object on every analysis write; this
scoreboard stores handles, not snapshots of reused objects.

This checker pairs streams **in order**. It does not model arbitrary completion
reordering, accepted-work ledgers, tolerance, reset epochs or cancellation.
Provide a reviewed keyed scoreboard for such blocks. Never silently drop pending
work on reset while external transfers remain live. See the
[MAC specialization](../unit/mac/environment/sb_mac_scoreboard.svh) for a small
example and the [plan](../../plans/block-verification-v0.1.md) for wider obligations.
