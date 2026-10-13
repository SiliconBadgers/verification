# RTL routing integration test

`command_router_tb.sv` checks eight command cases: the four unimplemented routes,
invalid opcode and ABI, completion identity under changed inputs, backpressure,
quiesce/drain and reset of stub state. It has a bounded simulation timeout.

Run `./scripts/workspace.sh test` in the pinned SoC workspace. It compiles
RTL's shared command package and routing experiment with SoC's fixtures under
VCS `Y-2026.03_Full64`. The runner retains compilation and simulation logs in
`build/router/vcs/` and requires all eight cases to pass with a zero exit status.
This routing pilot does not complete block verification, exercise a CPU, test
tensor arithmetic or validate reset with real DMA traffic.
