# State

## Status

Benchmark runner implemented and being tightened for fair comparison behavior.

## Active Task

Stabilize and iterate on the first macOS-first QueryFind baseline:

- `python -m queryfind`
- read-only allowlisted search commands
- path and content search
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

1. Run the full benchmark against installed local models and compare success and timing.
2. Review the benchmark design with read-only Codex feedback and harden weak cases.
3. Improve ranking quality on the synthetic corpus and benchmark corpus with prompt and scoring refinements.
4. Add stronger file-type handling for formats like PDF and Office documents.
