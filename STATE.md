# State

## Status

Baseline implemented and validated in heuristic mode.

## Active Task

Stabilize and iterate on the first macOS-first QueryFind baseline:

- `python -m queryfind`
- read-only allowlisted search commands
- path and content search
- streaming-friendly local Ollama integration
- richer ranked results

## Assumptions

- Current priority is the user's macOS setup, not broad platform support.
- Homebrew-installed `fd`, `rg`, `tree`, and `ollama` are acceptable.
- Runtime must stay local-only.

## Next Steps

1. Install and validate a real local model so streamed planning and ranking can run end to end after auto-start.
2. Improve ranking quality on real-world directories with prompt and scoring refinements.
3. Add stronger file-type handling for formats like PDF and Office documents.
4. Expand tests around metadata handling, planner parsing, and auto-start edge cases.
