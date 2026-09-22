# Verification starting material

September 22, 2026. Initial investigations for team discussion; no personal assignments or deadlines.

## Shared starting points

- [Editable architecture diagram](https://github.com/SiliconBadgers/architecture/blob/main/docs/accelerator-diagram.md) and [candidate boundaries](https://github.com/SiliconBadgers/architecture/blob/main/contracts/accelerator-boundaries.md).
- [Workload cases and source shapes](https://github.com/SiliconBadgers/architecture/blob/main/docs/workload-cases.md).
- [Measured llama.cpp report](https://github.com/SiliconBadgers/software/blob/main/experiments/llama-cpp/2026-09-22/REPORT.md) and [reproduction procedure](https://github.com/SiliconBadgers/software/blob/main/experiments/llama-cpp/2026-09-22/README.md).
- [Parallel team investigations](https://github.com/SiliconBadgers/planning/blob/main/docs/team-start.md).

The diagram and engine split are proposals. Start from available shapes and
reference cases now; use explicit parameters or stubs where decisions remain
open. Software's broader profiling study is not a prerequisite. Preserve the
source revision, assumptions, commands and limits of each result. Members and
leads can choose a different investigation that resolves a relevant uncertainty.


## First useful output

A small reusable reference-case set and comparison runner covering arithmetic
and state evolution, plus a protocol-case table usable with models/stubs. Start
before engine RTL or final interfaces exist.

## Existing evidence to reuse

The Software experiment includes saved prefill/final-decode logits at four
lengths, exact prompts/tokens and compressed CPU traces. Its validation script
can regenerate eight CPU-profiler equivalence checks and eight CPU/Metal
comparisons without running the model. Follow its reproduction guide to create
an isolated Python environment and write outputs outside recorded `results/`.

Those checks establish saved checkpoint relationships only. They do not verify
all intermediate tensors, custom INT4 quality or a hardware engine. Extend with
intermediate/state fixtures rather than treating final-logit agreement as a
complete verification plan.

## Procedure

1. Agree exact versus tolerance-based comparisons per format/operation. Record the tolerance rationale; do not pick a universal epsilon.
2. Extract small cases for matrix tails, accumulation/conversion, attention normalization, recurrent updates and convolution history. Include scale/sign/extreme-value cases.
3. Cover prefill followed by multiple decode steps, sequence isolation and state reset/reuse. State ownership must be observable in fixtures.
4. With Control and Memory, exercise valid/invalid commands, backpressure, delayed responses, faults with outstanding work and completion visibility.
5. Pair local numerical tests with Software's later task-quality checks; kernel agreement alone is not whole-model quality.

Store cases with provenance, expected output/state and a runner command in
`experiments/<study>/` or the appropriate existing test directory. A useful
submission includes an intentionally corrupted case that the comparator rejects.

## Existing MAC example

With sibling `software`, `architecture` and `rtl-compute` checkouts:

```sh
python3 ../software/generate_vectors.py --contract ../architecture/contracts/mac-v0.json --output build/mac-vectors.txt
python3 run.py --rtl-root ../rtl-compute --vectors build/mac-vectors.txt
```

Requires Python 3.11+ and Icarus Verilog. This is a separate INT8/INT32 learning
example; its numerical policy does not define the accelerator.
