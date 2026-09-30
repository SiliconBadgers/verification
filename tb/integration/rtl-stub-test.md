# RTL routing integration test

`command_router_tb.sv` checks eight command cases: the four unimplemented routes,
invalid opcode and ABI, completion identity under changed inputs, backpressure,
quiesce/drain and reset of stub state. It has a bounded simulation timeout.

Run `./scripts/workspace.sh test` in the pinned SoC workspace. It compiles
Architecture's types, Control's routing experiment and SoC's fixture.
This Verilator pilot does not complete the Synopsys verification assignment,
exercise a CPU, test tensor arithmetic or validate reset with real DMA traffic.
