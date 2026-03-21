# Progress

## 2026-03-21

- Clarified V1 scope around macOS-first delivery, local-only runtime, path and content search, richer ranked output, and streamed reasoning/progress.
- Decided the LLM will not emit arbitrary shell. QueryFind will compile model intent into a fixed read-only command allowlist.
- Chose the initial allowlisted command set: `fd`, `rg`, `ls`, `tree`, `stat`, `mdls`.
- Implemented the first `python -m queryfind` baseline and the required repo control files.
- Added a deterministic heuristic fallback so the CLI still works when the local Ollama server is not running.
- Added timestamped logging, root inspection, allowlisted command execution, heuristic planning, candidate scoring, and ranked result rendering.
- Added smoke tests for the heuristic planner, command allowlist enforcement, and the CLI search path.
- Validated the baseline locally with `python3 -m unittest discover -s tests -v` and `python3 -m queryfind --doctor`.
