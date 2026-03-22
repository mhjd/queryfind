# QueryFind

QueryFind is a local macOS-first CLI for finding files with natural-language queries.

It is useful when:
- you know the information you want, but not the exact file name
- the answer is likely inside file contents, not just in paths
- you want a constrained local search agent instead of arbitrary shell execution

QueryFind uses a local Ollama model plus a read-only command allowlist (`fd`, `rg`, `ls`, `tree`, `stat`, `mdls`) to plan searches, inspect results, and return ranked matches with evidence.

## Install

Requirements:
- macOS
- Python 3.12+
- `fd`
- `rg`
- `tree` recommended
- `ollama`
- a local Ollama model, for example `qwen3.5:27b` or `qwen3-coder:30b`

Typical setup with Homebrew:

```bash
brew install fd ripgrep tree ollama
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ollama pull qwen3-coder:30b
```

Check the environment:

```bash
python -m queryfind --doctor
make test
```

## Use

Run a search:

```bash
python -m queryfind "find the latest signed contract for Redwood"
```

Search a specific folder:

```bash
python -m queryfind "find the Wi-Fi password for Harbor 7" --root ~/Documents
```

Run without the LLM:

```bash
python -m queryfind "find project files about Atlas" --no-llm
```

Useful commands:

```bash
make doctor
make synthetic-eval
python -m queryfind.benchmark --model qwen3-coder:30b
python -m queryfind.benchmark --manifest benchmark_fs/extended_manifest.json --model qwen3-coder:30b
python -m queryfind.benchmark --manifest benchmark_fs/handmade100_manifest.json --model qwen3-coder:30b
```

## Notes

- QueryFind auto-starts Ollama when possible.
- LLM mode is local-only and read-only by default. Non-local Ollama URLs are rejected unless `--allow-remote-ollama` is passed explicitly.
- Backend command execution is constrained to trusted macOS binaries plus validated read-only argv shapes.
- Heuristic mode is available explicitly with `--no-llm`.
- Logs are written under `.queryfind/`.
