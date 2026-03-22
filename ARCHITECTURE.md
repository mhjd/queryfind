# Architecture

## Current Shape

- `queryfind/`
  - `__main__.py`: `python -m queryfind` entrypoint.
  - `cli.py`: argument parsing and command dispatch.
  - `app.py`: top-level search and doctor workflows plus the bounded agent loop orchestration.
  - `config.py`: runtime defaults and configuration dataclass.
  - `models.py`: shared dataclasses for intents, agent actions and observations, candidates, and outcomes.
  - `logging_utils.py`: timestamped stdout and file logging with streamed sections.
  - `ollama_client.py`: local Ollama HTTP streaming client.
  - `planner.py`: heuristic fallback, iterative LLM action selection, and final candidate ranking.
  - `search_backend.py`: allowlisted command runner and file-system search pipeline, including per-action observations and warnings.
  - `render.py`: terminal result rendering with Rich when available.
  - `benchmark.py`: full benchmark runner with correctness, timing, and agent-turn usage summaries.
  - `synthetic_eval.py`: small first-filter evaluation runner for the synthetic corpus.
- `tests/test_queryfind.py`: smoke tests for the heuristic baseline and CLI path.
- `benchmark_fs/`: benchmark corpora and manifests, including the original 19-case suite, the 40-case extended suite, the generated 100-case mega suite, and the handcrafted 100-case suite.
- `synthetic_fs/`: small static synthetic filesystem for early search validation.
- `pyproject.toml`: package metadata and pinned runtime dependency declaration.
- `Makefile`: project commands.
- `README.md`: quick user-facing overview, install steps, and primary commands.
- `PROJECT.md`: product scope and command policy.
- `STATE.md`: current work state and next steps.
- `PROGRESS.md`: append-only progress log.

## Runtime Flow

1. Parse CLI arguments.
2. Validate required search tools.
3. Auto-start `ollama serve` when the configured local endpoint is down and auto-start is enabled.
4. Inspect the root directory with `tree` or `ls`.
5. Ask the local model for the next bounded search action when available.
6. Compile that action into allowlisted `fd`, `rg`, `stat`, and `mdls` calls.
7. Convert command results and warnings into an observation summary and feed it back into the next step.
8. Repeat until the agent finishes or the step budget is exhausted.
9. Ask the local model to rank and summarize candidates when available.
10. Render ranked results and keep a timestamped log file.

## Synthetic Validation

- `synthetic_fs/basic/` provides a small local directory tree with contracts, runbooks, project notes, onboarding files, and hidden notes.
- `queryfind.synthetic_eval` resets corpus mtimes, runs representative search cases, and verifies the expected file appears in the top results.
- The synthetic evaluation is a first filter for concrete environment checks before a later benchmark is added.

## Benchmarking

- `benchmark_fs/full/` provides a larger static corpus with stronger ambiguity and more varied domains.
- `benchmark_fs/full_manifest.json` keeps the original 19-case suite.
- `benchmark_fs/extended_manifest.json` defines the 40-case extended suite that reuses the same corpus root with more cases, aliases, negatives, and distractors.
- `benchmark_fs/mega/` plus `benchmark_fs/mega_manifest.json` provide a generated 100-case scale suite.
- `benchmark_fs/handmade100/` plus `benchmark_fs/handmade100_manifest.json` provide a handcrafted 125-case suite with realistic aliases, indirect clues, multi-file hops, and deliberately messy company plus personal subtrees.
- `benchmark_fs/generate_large_benchmark.py` rebuilds the generated mega suite.
- `benchmark_fs/build_handmade100.py` rebuilds the handcrafted suite from curated scenario data.
- `queryfind.benchmark` runs the real agent/search/ranker pipeline, measures correctness and latency, records step counts and actual LLM turn usage, supports case/category/difficulty filtering, accepts a `--manifest` selector, and writes a JSON report.

## Safety Model

- The LLM never runs shell directly.
- The backend enforces an explicit executable allowlist.
- Search is read-only.
- Network use is limited to the local Ollama API.
- Heuristic search remains available only as an explicit mode for tests and baselines; LLM mode no longer silently falls back to heuristic execution.
