# QueryFind Benchmark

This folder contains the fuller local benchmark corpus and manifest used to compare QueryFind performance across models.

- `full/`: benchmark corpus searched by the product pipeline
- `full_manifest.json`: benchmark case definitions and normalized file mtimes

Run it with:

```bash
python -m queryfind.benchmark --heuristic-baseline
```
