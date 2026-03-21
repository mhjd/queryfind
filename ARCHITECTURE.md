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
- `tests/test_queryfind.py`: smoke tests for the heuristic baseline and CLI path.
- `pyproject.toml`: package metadata and pinned runtime dependency declaration.
- `Makefile`: project commands.
- `PROJECT.md`: product scope and command policy.
- `STATE.md`: current work state and next steps.
- `PROGRESS.md`: append-only progress log.

## Runtime Flow

1. Parse CLI arguments.
2. Validate required search tools.
3. Inspect the root directory with `tree` or `ls`.
4. Ask the local model for a structured search intent when available.
5. Compile that intent into allowlisted `fd`, `rg`, `stat`, and `mdls` calls.
6. Merge and score candidate files from path and content evidence.
7. Ask the local model to rank and summarize candidates when available.
8. Render ranked results and keep a timestamped log file.

## Safety Model

- The LLM never runs shell directly.
- The backend enforces an explicit executable allowlist.
- Search is read-only.
- Network use is limited to the local Ollama API.
