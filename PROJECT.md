# QueryFind

## Overview

QueryFind is a local CLI tool that helps users find files with natural language on macOS.

Instead of manually navigating a file system or crafting complex shell commands, the user describes what they want. QueryFind uses a local LLM agent to translate that request into a constrained search plan, execute a small set of read-only file-system commands, and return ranked results with evidence.

The benchmark side of the project exists, but it is intentionally out of scope for now. The current focus is a reliable macOS-first product path.

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
- Default model: `gpt-oss:20b` (configurable)
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
- Broader macOS compatibility and benchmark work will be handled later.
