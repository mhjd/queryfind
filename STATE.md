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
There is now a dedicated batch helper for the 25-case handmade personal slice in `scripts/run_personal_model_benchmarks.sh`.
The prompt-tuning loop under `permanent_tasks_loop/` is now pinned to `glm-4.7-flash:latest`, requires general wording rather than benchmark-shaped examples, and keeps an append-only revision log in `permanent_tasks_loop/improving_system_prompt_history.md`.
Latest benchmark results with the current prompt:

- `qwen3-coder:30b`: 14/19 on the original suite and 28/40 on the extended suite
- `glm-4.7-flash:latest`: 15/19 on the original suite and 32/40 on the extended suite
- `gpt-oss:20b`: 2/19 on the original suite and 6/40 on the extended suite
- Handcrafted 125-case benchmark full run: `glm-4.7-flash:latest` scored 90/125 and `qwen3-coder:30b` scored 75/125.
- Two prompt-tuning iterations were screened and rejected on 2026-03-22; the stronger screened revision reached `3/9` on a hard GLM subset but regressed to `88/125` on the full 125-case GLM run, so `queryfind/planner.py` was reverted to the last validated prompt.

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
- Future prompt-tuning and evaluation work should move benchmark execution off the local GPU.
- Benchmarking changes must not change the real app runtime path; the real app should remain separate from benchmark-only experimentation.

## Next Steps

1. Change benchmark-only execution to use the OpenRouter API instead of the local GPU.
2. Keep that OpenRouter change benchmark-only; do not route the real app through OpenRouter as part of this work.
3. Add a second hidden 125-case witness benchmark whose contents are not visible during prompt-tuning iterations, and use it as an overfitting check.
4. Continue prompt iteration only after the visible benchmark and witness benchmark strategy are both defined.
5. After that, resume work on the remaining GLM-like failure clusters: contract lookups that stop at customer indexes, alias-to-target status hops, and personal-shell snippet queries.
