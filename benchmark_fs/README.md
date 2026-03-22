# QueryFind Benchmark

This folder contains the fuller local benchmark corpus and manifest used to compare QueryFind performance across models.

- `full/`: benchmark corpus searched by the product pipeline
- `full_manifest.json`: benchmark case definitions and normalized file mtimes
- `mega/`: larger synthetic filesystem used by the 100-case comparison suite
- `mega_manifest.json`: 100-case manifest for the larger suite
- `generate_large_benchmark.py`: reproducible generator for the `mega/` corpus and manifest
- `handmade100/`: handcrafted mixed corpus with intentionally messy company and personal layouts, indirect clues, alias files, and cross-file hops
- `handmade100_manifest.json`: handcrafted 125-case manifest
- `build_handmade100.py`: curated builder for the handcrafted suite

Run it with:

```bash
python -m queryfind.benchmark --heuristic-baseline
```

Run the 100-case suite with:

```bash
python -m queryfind.benchmark --manifest benchmark_fs/mega_manifest.json --model glm-4.7-flash:latest
```

Run the handcrafted suite with:

```bash
python -m queryfind.benchmark --manifest benchmark_fs/handmade100_manifest.json --model glm-4.7-flash:latest
```
