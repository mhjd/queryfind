# State

## Status

Bounded agent loop implemented and validated in heuristic mode.
Automatic heuristic fallback has been removed from LLM mode so benchmark and runtime behavior stay honest.

## Active Task

Stabilize and iterate on the first macOS-first QueryFind baseline:

- `python -m queryfind`
- read-only allowlisted search commands
- path and content search
- iterative `LLM -> tool -> observe -> revise` search flow
- streaming-friendly local Ollama integration
- richer ranked results
- synthetic filesystem smoke evaluation
- fuller benchmark corpus and runner

## Assumptions

- Current priority is the user's macOS setup, not broad platform support.
- Homebrew-installed `fd`, `rg`, `tree`, and `ollama` are acceptable.
- Runtime must stay local-only.
- The default Ollama model is `qwen3.5:27b`.

## Next Steps

1. Tune the Qwen prompts and payload sizes so the model can complete agent turns within the current timeout budget.
2. Run the full benchmark against installed local models and compare actual LLM turn usage, success, and timing.
3. Review the benchmark design with read-only Codex feedback and harden weak cases that are too noisy or too lexical.
4. Add stronger file-type handling for formats like PDF and Office documents.
