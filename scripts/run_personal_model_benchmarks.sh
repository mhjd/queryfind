#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

MANIFEST="benchmark_fs/handmade100_manifest.json"
CATEGORY="personal"
MODELS=(
  "qwen3.5:27b"
  "glm-4.7-flash:latest"
  "qwen3-coder:30b"
)

mkdir -p .queryfind/benchmarks

echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting personal-only benchmark batch"
echo "manifest=$MANIFEST"
echo "category=$CATEGORY"

for model in "${MODELS[@]}"; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] running model=$model"
  "$PYTHON_BIN" -m queryfind.benchmark \
    --manifest "$MANIFEST" \
    --category "$CATEGORY" \
    --model "$model" \
    --quiet
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] personal-only benchmark batch complete"
