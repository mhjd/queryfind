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
- synthetic filesystem smoke evaluation

## Assumptions

- Current priority is the user's macOS setup, not broad platform support.
- Homebrew-installed `fd`, `rg`, `tree`, and `ollama` are acceptable.
- Runtime must stay local-only.
- The default Ollama model is `qwen3.5:27b`.

## Next Steps

1. Install and validate a real local model so streamed planning and ranking can run end to end after auto-start.
2. Improve ranking quality on the synthetic corpus and real-world directories with prompt and scoring refinements.
3. Add stronger file-type handling for formats like PDF and Office documents.
4. Expand the synthetic corpus with harder multi-file reasoning cases after the first benchmark-free filter is stable.
