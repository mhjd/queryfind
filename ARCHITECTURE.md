# Architecture

## Current Shape

- `queryfind/`
  - `__main__.py`: `python -m queryfind` entrypoint.
  - `cli.py`: argument parsing and command dispatch.
  - `app.py`: top-level search and doctor workflows.
  - `config.py`: runtime defaults and configuration dataclass.
  - `models.py`: shared dataclasses for intents, candidates, and outcomes.
  - `logging_utils.py`: timestamped stdout and file logging with streamed sections.
  - `ollama_client.py`: local Ollama HTTP streaming client.
  - `planner.py`: heuristic planning plus optional LLM planning and ranking.
  - `search_backend.py`: allowlisted command runner and file-system search pipeline.
  - `render.py`: terminal result rendering with Rich when available.
  - `benchmark.py`: full benchmark runner with correctness and timing summaries.
  - `synthetic_eval.py`: small first-filter evaluation runner for the synthetic corpus.
- `tests/test_queryfind.py`: smoke tests for the heuristic baseline and CLI path.
- `benchmark_fs/`: fuller benchmark corpus plus manifest for model comparison.
- `synthetic_fs/`: small static synthetic filesystem for early search validation.
- `pyproject.toml`: package metadata and pinned runtime dependency declaration.
- `Makefile`: project commands.
- `PROJECT.md`: product scope and command policy.
- `STATE.md`: current work state and next steps.
- `PROGRESS.md`: append-only progress log.

## Runtime Flow

1. Parse CLI arguments.
2. Validate required search tools.
3. Auto-start `ollama serve` when the configured local endpoint is down and auto-start is enabled.
4. Inspect the root directory with `tree` or `ls`.
5. Ask the local model for a structured search intent when available.
6. Compile that intent into allowlisted `fd`, `rg`, `stat`, and `mdls` calls.
7. Merge and score candidate files from path and content evidence.
8. Ask the local model to rank and summarize candidates when available.
9. Render ranked results and keep a timestamped log file.

## Synthetic Validation

- `synthetic_fs/basic/` provides a small local directory tree with contracts, runbooks, project notes, onboarding files, and hidden notes.
- `queryfind.synthetic_eval` resets corpus mtimes, runs representative search cases, and verifies the expected file appears in the top results.
- The synthetic evaluation is a first filter for concrete environment checks before a later benchmark is added.

## Benchmarking

- `benchmark_fs/full/` provides a larger static corpus with stronger ambiguity and more varied domains.
- `benchmark_fs/full_manifest.json` defines benchmark cases and normalized file mtimes.
- `queryfind.benchmark` runs the real planner/search/ranker pipeline, measures correctness and latency, supports case/category/difficulty filtering, and writes a JSON report.

## Safety Model

- The LLM never runs shell directly.
- The backend enforces an explicit executable allowlist.
- Search is read-only.
- Network use is limited to the local Ollama API.
