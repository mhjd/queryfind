# State

## Status

Bounded agent loop implemented and validated in heuristic mode.
Automatic heuristic fallback has been removed from LLM mode so benchmark and runtime behavior stay honest.
Agent steps now stream even in hidden-thinking mode so timeout diagnosis can distinguish "no output at all" from "partial progress".
Benchmark runs now prewarm the selected Ollama model and request a long keep-alive so cold-start and model eviction are less misleading.
The current accepted general agent prompt is the concise content-vs-path guidance variant in `queryfind/planner.py`.
The command sandbox has been hardened so execution now uses trusted macOS command paths, validated argv shapes, root containment checks, and a repo-local `.venv` workflow for Python commands and tests.
Ollama access is now loopback-only by default, with explicit remote opt-in and no autostart for non-local endpoints.
The original 19-case suite remains available in `benchmark_fs/full_manifest.json`, and a new 40-case suite now exists in `benchmark_fs/extended_manifest.json`.
Two larger suites now exist as well: the generated `benchmark_fs/mega_manifest.json` and the handcrafted `benchmark_fs/handmade100_manifest.json`, which now contains 125 cases over a deliberately messy mixed company/personal filesystem.
Latest benchmark results with the current prompt:

- `qwen3-coder:30b`: 14/19 on the original suite and 28/40 on the extended suite
- `glm-4.7-flash:latest`: 15/19 on the original suite and 32/40 on the extended suite
- `gpt-oss:20b`: 2/19 on the original suite and 6/40 on the extended suite
- Handcrafted 125-case benchmark full run: `glm-4.7-flash:latest` scored 90/125 and `qwen3-coder:30b` scored 75/125.

## Active Task

Stabilize and iterate on the first macOS-first QueryFind baseline:

- `python -m queryfind`
- read-only allowlisted search commands
- path and content search
- iterative `LLM -> tool -> observe -> revise` search flow
- streaming-friendly local Ollama integration
- richer ranked results
- stricter command sandboxing for read-only search execution
- synthetic filesystem smoke evaluation
- fuller benchmark corpus and runner
- handcrafted 125-case benchmark corpus with indirect clues, alias-driven hops, and a deliberately messy mixed company/personal layout

## Assumptions

- Current priority is the user's macOS setup, not broad platform support.
- Homebrew-installed `fd`, `rg`, `tree`, and `ollama` are acceptable.
- Runtime must stay local-only.
- The default Ollama model is `qwen3.5:27b`.

## Next Steps

1. Analyze the handcrafted 125-case failures by category to understand where the current agent loop breaks on messy personal notes versus alias-driven company cases.
2. Improve the action prompts so models do not over-constrain themselves with bad extension filters or miss obvious content-first cases.
3. Add stronger file-type handling for formats like PDF and Office documents.
4. Tune the agent loop against the handcrafted benchmark so models continue past alias files and complete the second hop to the real answer file.
5. Consider whether self-generated log files under the search root should remain searchable or move outside the root by default.
