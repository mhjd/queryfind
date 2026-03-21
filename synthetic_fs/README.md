# Synthetic File System

This folder contains a small, inspectable local corpus for early QueryFind validation.

Goals:

- provide a concrete directory tree to search
- exercise path search, content search, hidden files, and file metadata
- provide a light reasoning filter before the later benchmark work exists

The primary corpus lives in `synthetic_fs/basic/`.

Use:

```bash
python -m queryfind.synthetic_eval
```

The evaluation runner normalizes file mtimes before each run so queries involving `latest` or `recent` remain reproducible.
