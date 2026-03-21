# QueryFind

## Overview

QueryFind is a local CLI tool that helps users find files with natural language on macOS.

Instead of manually navigating a file system or crafting complex shell commands, the user describes what they want. QueryFind uses a local LLM agent to translate that request into a constrained search plan, execute a small set of read-only file-system commands, and return ranked results with evidence.

The current focus is still a reliable macOS-first product path, but the project now also includes a real benchmark path for comparing model quality and speed.

## V1 Goals

- Run as `python -m queryfind`.
- Search both file paths and file contents.
- Keep the runtime local-only.
- Stream the model's reasoning trace and progress while the search is running.
- Avoid requiring users to manually start Ollama. QueryFind should auto-start the local server when possible.
- Return richer results than plain paths:
  - ranked matches
  - short explanations for each result
  - evidence snippets
  - visible executed search steps for reproducibility
- Work even when the local model is unavailable by falling back to deterministic heuristics.

## V1 Technical Stack

- Language: Python
- CLI: native `argparse`
- Terminal UX: Rich when installed, with a plain-text fallback
- File search backend: `fd`, `rg`, `ls`, `tree`, `stat`, `mdls`
- LLM backend: Ollama
- Default model: `qwen3.5:27b` (configurable)
- Packaging target: `python -m queryfind`

## Read-Only Command Policy

The LLM must not emit arbitrary shell commands.

Instead, QueryFind will expose only a constrained internal tool surface and compile the model's search intent into an allowlisted set of read-only commands:

- `fd`
- `rg`
- `ls`
- `tree`
- `stat`
- `mdls`

Why this set:

- `fd` is the primary path search tool.
- `rg` is the primary content search tool and can also provide snippet evidence.
- `ls` is useful for quick directory inspection when `tree` is unavailable or too broad.
- `tree` is useful for shallow structure discovery.
- `stat` is useful for reliable file metadata such as modification time and size.
- `mdls` is useful on macOS for Finder metadata and file kind hints.

Commands intentionally excluded from the agent surface for now:

- write-capable shell commands
- arbitrary shell execution
- destructive file operations
- external network tools

## Interface

Typical usage:

```bash
python -m queryfind "find the latest signed contract for client beta"
```

Synthetic evaluation usage:

```bash
python -m queryfind.synthetic_eval
```

Benchmark usage:

```bash
python -m queryfind.benchmark --heuristic-baseline
python -m queryfind.benchmark --model qwen3.5:27b
```

Expected runtime flow:

1. Show root inspection progress.
2. Auto-start Ollama when needed and available locally.
3. Stream planner thinking.
4. Execute visible read-only search commands.
5. Stream ranking thinking.
6. Print a ranked result set with evidence.

## Notes

- Homebrew-installed dependencies are acceptable for now.
- Initial support is for the current macOS environment first.
- Broader macOS compatibility will be handled later.
- A small synthetic filesystem is included for early end-to-end validation before the later benchmark work exists.
- A fuller benchmark corpus is included to compare model correctness and latency once local models are installed.
- The synthetic eval remains the pass/fail gate; the benchmark is a measurement tool and should not be treated as a binary test.
