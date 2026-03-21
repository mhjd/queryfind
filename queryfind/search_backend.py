from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

from queryfind.config import ALLOWED_COMMANDS, REQUIRED_COMMANDS
from queryfind.logging_utils import RunLogger
from queryfind.models import SearchCandidate, SearchIntent


@dataclass(slots=True)
class DependencyReport:
    required_missing: list[str]
    optional_missing: list[str]


class SearchBackend:
    def __init__(self, *, root: Path, logger: RunLogger, max_candidates: int) -> None:
        self.root = root
        self.logger = logger
        self.max_candidates = max_candidates

    def dependency_report(self) -> DependencyReport:
        required_missing = [name for name in REQUIRED_COMMANDS if shutil.which(name) is None]
        optional_missing = [
            name for name in ALLOWED_COMMANDS if name not in REQUIRED_COMMANDS and shutil.which(name) is None
        ]
        return DependencyReport(required_missing=required_missing, optional_missing=optional_missing)

    def inspect_root(self) -> str:
        if shutil.which("tree"):
            result = self._run(
                ["tree", "-a", "-L", "2", "--noreport", "-I", ".git", str(self.root)],
                allowed_returncodes={0},
            )
            text = result.stdout.strip()
            if text:
                return _truncate(text, 1500)
        result = self._run(["ls", "-la", str(self.root)], allowed_returncodes={0})
        return _truncate(result.stdout.strip(), 1500)

    def search(self, intent: SearchIntent) -> list[SearchCandidate]:
        by_path: dict[Path, SearchCandidate] = {}
        self._search_paths(intent, by_path)
        self._search_contents(intent, by_path)
        candidates = list(by_path.values())
        self._enrich_metadata(candidates[: self.max_candidates])
        self._sort_candidates(candidates, intent.sort_hint)
        return candidates[: self.max_candidates]

    def _search_paths(self, intent: SearchIntent, by_path: dict[Path, SearchCandidate]) -> None:
        terms = _dedupe(intent.filename_hints + intent.path_terms)
        for term in terms[:6]:
            argv = [
                "fd",
                "-0",
                "-i",
                "-t",
                "f",
                "--hidden",
                "--follow",
                "--exclude",
                ".git",
            ]
            for extension in intent.extensions[:4]:
                argv.extend(["-e", extension])
            argv.extend([term, str(self.root)])
            result = self._run(argv, allowed_returncodes={0})
            for raw_path in [item for item in result.stdout.split("\0") if item]:
                path = Path(raw_path).resolve()
                if not path.is_file():
                    continue
                candidate = by_path.setdefault(path, SearchCandidate(path=path))
                weight = 8.0 if term in path.name.lower() else 4.0
                candidate.score += weight
                _append_unique(candidate.reasons, f"path matches '{term}'")

    def _search_contents(self, intent: SearchIntent, by_path: dict[Path, SearchCandidate]) -> None:
        terms = _dedupe(intent.content_terms or intent.path_terms)
        for term in terms[:6]:
            argv = ["rg", "--json", "-n", "-i", "--hidden", "--glob", "!.git", "-m", "2"]
            for extension in intent.extensions[:4]:
                argv.extend(["-g", f"*.{extension}"])
            argv.extend([term, str(self.root)])
            result = self._run(argv, allowed_returncodes={0, 1})
            if not result.stdout.strip():
                continue
            for line in result.stdout.splitlines():
                event = json.loads(line)
                if event.get("type") != "match":
                    continue
                data = event.get("data", {})
                raw_path = (((data.get("path") or {}).get("text")) or "").strip()
                if not raw_path:
                    continue
                path = Path(raw_path).resolve()
                if not path.is_file():
                    continue
                candidate = by_path.setdefault(path, SearchCandidate(path=path))
                candidate.score += 12.0
                _append_unique(candidate.reasons, f"content matches '{term}'")
                line_number = int(data.get("line_number") or 0)
                text = (((data.get("lines") or {}).get("text")) or "").strip()
                if text:
                    snippet = f"L{line_number}: {text[:180]}"
                    _append_unique(candidate.snippets, snippet)
                if line_number:
                    _append_unique_int(candidate.line_numbers, line_number)

    def _enrich_metadata(self, candidates: list[SearchCandidate]) -> None:
        for candidate in candidates:
            if shutil.which("stat"):
                result = self._run(
                    ["stat", "-f", "%m|%z|%N", str(candidate.path)],
                    allowed_returncodes={0},
                )
                parts = result.stdout.strip().split("|", maxsplit=2)
                if len(parts) >= 2:
                    candidate.mtime_epoch = int(parts[0])
                    candidate.size_bytes = int(parts[1])
            if shutil.which("mdls"):
                result = self._run(
                    ["mdls", "-raw", "-name", "kMDItemKind", str(candidate.path)],
                    allowed_returncodes={0, 1},
                )
                kind = result.stdout.strip()
                if result.returncode == 0 and kind and kind != "(null)" and "could not find" not in kind:
                    candidate.kind = kind.strip('"')

    def _sort_candidates(self, candidates: list[SearchCandidate], sort_hint: str) -> None:
        if sort_hint == "mtime_desc":
            candidates.sort(
                key=lambda candidate: (
                    candidate.mtime_epoch or 0,
                    candidate.score,
                    candidate.path.name.lower(),
                ),
                reverse=True,
            )
            return
        candidates.sort(
            key=lambda candidate: (
                candidate.score,
                candidate.mtime_epoch or 0,
                candidate.path.name.lower(),
            ),
            reverse=True,
        )

    def _run(self, argv: list[str], *, allowed_returncodes: set[int]) -> subprocess.CompletedProcess[str]:
        executable = Path(argv[0]).name
        if executable not in ALLOWED_COMMANDS:
            raise ValueError(f"Command not allowed: {executable}")
        self.logger.command(argv)
        result = subprocess.run(
            argv,
            cwd=self.root,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
            check=False,
        )
        if result.returncode not in allowed_returncodes:
            stderr = result.stderr.strip() or "unknown command error"
            raise RuntimeError(f"{executable} failed with code {result.returncode}: {stderr}")
        return result


def format_candidate_metadata(candidate: SearchCandidate) -> str:
    parts = []
    if candidate.kind:
        parts.append(candidate.kind)
    if candidate.size_bytes is not None:
        parts.append(f"{candidate.size_bytes} bytes")
    if candidate.mtime_epoch is not None:
        timestamp = datetime.fromtimestamp(candidate.mtime_epoch).isoformat(sep=" ", timespec="seconds")
        parts.append(f"modified {timestamp}")
    return " | ".join(parts)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        cleaned = item.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _append_unique_int(items: list[int], value: int) -> None:
    if value not in items:
        items.append(value)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n..."
