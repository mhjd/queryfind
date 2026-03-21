# Progress

## 2026-03-21

- Clarified V1 scope around macOS-first delivery, local-only runtime, path and content search, richer ranked output, and streamed reasoning/progress.
- Decided the LLM will not emit arbitrary shell. QueryFind will compile model intent into a fixed read-only command allowlist.
- Chose the initial allowlisted command set: `fd`, `rg`, `ls`, `tree`, `stat`, `mdls`.
- Implemented the first `python -m queryfind` baseline and the required repo control files.
- Added a deterministic heuristic fallback so the CLI still works when the local Ollama server is not running.
- Added automatic `ollama serve` startup so the CLI no longer depends on manual server launch.
- Added early fallback when Ollama is reachable but no local model is installed.
- Switched the project default Ollama model from `gpt-oss:20b` to `qwen3.5:27b`.
- Added a small synthetic filesystem under `synthetic_fs/basic/` for early end-to-end validation.
- Added `python -m queryfind.synthetic_eval` and a `make synthetic-eval` target to verify basic search and light reasoning cases.
- Validated the synthetic corpus locally with `python3 -m queryfind.synthetic_eval`, passing 6 out of 6 heuristic cases.
- Added a fuller benchmark corpus under `benchmark_fs/full/` plus a machine-readable manifest in `benchmark_fs/full_manifest.json`.
- Added `python -m queryfind.benchmark` to measure both correctness and timing across benchmark cases and models.
- Fixed the benchmark runner so heuristic-only runs no longer try to execute an unavailable default model.
- Changed the benchmark CLI to behave like a measurement tool rather than a pass/fail test command.
- Added timestamped logging, root inspection, allowlisted command execution, heuristic planning, candidate scoring, and ranked result rendering.
- Added smoke tests for the heuristic planner, command allowlist enforcement, and the CLI search path.
- Validated the baseline locally with `python3 -m unittest discover -s tests -v`, `python3 -m queryfind --doctor`, and one end-to-end auto-start run outside the sandbox.
