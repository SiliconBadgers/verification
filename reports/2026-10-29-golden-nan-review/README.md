# Golden-model NaN review correction — 2026-10-29

Addresses [PR #13's review](https://github.com/SiliconBadgers/verification/pull/13#pullrequestreview-5690053387).
Tested source: `ad634a4960363f552e5bd5d898f894dcfcdd2f86`, a clean LF clone of
`adam/golden-model`. This report and its logs were added afterward; no tested code changed.
The run started October 29 in America/Chicago, `2026-10-30T02:41:21Z` in UTC.

## Correction

The whole-tensor checker previously ignored every Python NaN, even against a finite C
reference, and accepted NaNs as nonzero stimulus. It now compares identical binary32 words
or NaN on both sides, checks output lengths before pairing rows, and requires a finite
nonzero result for the existing whole-tensor sanity check. Signed zeros remain distinct.
No model arithmetic or RTL changed.

Four new harness-independent test methods exercise matching outputs/two-sided NaNs,
one-sided NaNs in both directions, finite mismatches, signed zeros, unequal lengths,
and missing finite nonzero output. The original `[NaN, NaN]` versus `[1.0, 2.0]`
example must raise the mismatch assertion, not merely fail the sanity check.

## Results

| Check | Tests run | Passed | Failed | Skipped | Test elapsed | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Normal numerical suite](normal.log) | 29 | 28 | 0 | 1 | 7.644 s | 0 |
| [Full numerical suite, `GM_FULL=1`](full.log) | 29 | 29 | 0 | 0 | 108.701 s | 0 |
| [Repository Python tooling tests](tooling.log) | 9 | 9 | 0 | 0 | 0.019 s | 0 |

Counts are unittest test methods; subtest cases are not added to these totals. The two
numerical runs overlap. The normal skip is only the opt-in full output head. Full mode
executed all five whole-tensor cases, including all 248,320 output-head rows, with the
corrected comparison. There were no missing-harness or missing-model skips.

The C harness was rebuilt from the clean pinned local llama.cpp sources before testing;
[build log](harness-build.log), [commands](harness-build.command.txt), and
[process exit codes/wall times](status.txt) are retained. The build took 4 seconds.
Every suite used a bounded timeout (600 seconds numerical, 60 seconds tooling).

## Reproduction and provenance

- Python 3.14.4, GCC 15.2.0, Ubuntu under WSL.
- llama.cpp `f46bc30cb6a7f68a67e34a00061e20a4ad1eff43`, tracked worktree clean.
- Existing `Qwen3.5-2B-Q4_K_M.gguf`, SHA256 verified against
  `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`.
- `GM_SEED=1`; freshly rebuilt C harness with `-O2 -std=gnu11 -ffp-contract=off
  -fno-fast-math -DGGML_CPU_GENERIC -DNDEBUG`, using the checked-in build script.
- [Metadata and binary hashes](metadata.txt), [normal command](normal.command.txt),
  [full command](full.command.txt), [tooling command](tooling.command.txt).

With the pinned source/model prerequisites already installed, from the tested checkout:

```bash
cd models/golden_kquant
export GM_GGUF="$HOME/ref/models/qwen35-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf"
export GM_SEED=1
unset GM_FULL
harness_dir=$(mktemp -d)
bash harness/build.sh "$HOME/ref/llama.cpp-f46bc30" "$harness_dir"
export GM_HARNESS="$harness_dir/gm_harness"
timeout 600 python3 -m unittest discover -s tests -v
timeout 600 env GM_FULL=1 python3 -m unittest discover -s tests -v
cd ../..
timeout 60 python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

## Limits

These are direct Python invocations, not executions of uv-backed Make targets. The
repository tooling tests check Make routing with dry runs and stubs; they do not establish
that uv, Ruff, or VCS is available. `make style` and Ruff were not run: those tools were
unavailable in the local environment, and no new tools were downloaded. The existing
`style.json` only selects `scripts/*.py`; it does not include the changed model tests.

No VCS simulation, vector regeneration, coverage collection, model-accuracy study, or
earlier arithmetic mutation campaigns were rerun. The four new checker controls are
included in each numerical suite. These results validate the scalar llama.cpp reference
comparison and existing contract tests; they do not establish full-model numerical
quality or real-arbiter integration.

Review correction and report assisted by OpenAI Codex; exact runtime model ID unavailable.
