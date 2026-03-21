# State

## Status

Bounded agent loop implemented and validated in heuristic mode.
Automatic heuristic fallback has been removed from LLM mode so benchmark and runtime behavior stay honest.
Agent steps now stream even in hidden-thinking mode so timeout diagnosis can distinguish "no output at all" from "partial progress".
Benchmark runs now prewarm the selected Ollama model and request a long keep-alive so cold-start and model eviction are less misleading.
The current accepted general agent prompt is the concise content-vs-path guidance variant in `queryfind/planner.py`; the latest verification run on `qwen3-coder:30b` scored 14/19.

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

1. Evaluate `glm-4.7-flash` with the current general prompt and compare it against `qwen3-coder:30b`.
2. Improve the action prompts so models do not over-constrain themselves with bad extension filters or miss obvious content-first cases.
3. Add stronger file-type handling for formats like PDF and Office documents.
4. Consider separate cold-start and warm-run benchmark modes for clearer latency reporting.
