from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

from queryfind.config import ALLOWED_COMMANDS, REQUIRED_COMMANDS, TRUSTED_COMMAND_DIRS
from queryfind.logging_utils import RunLogger
from queryfind.models import AgentAction, AgentObservation, SearchCandidate, SearchIntent


@dataclass(slots=True)
class DependencyReport:
    required_missing: list[str]
    optional_missing: list[str]


SAFE_ENV_KEYS = ("HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE")


class SearchBackend:
    def __init__(self, *, root: Path, logger: RunLogger, max_candidates: int) -> None:
        self.root = root.resolve()
        self.logger = logger
        self.max_candidates = max_candidates
        self._recent_warnings: list[str] = []
        self._trusted_search_path = os.pathsep.join(TRUSTED_COMMAND_DIRS)
        self._command_paths = {
            name: self._resolve_command_path(name)
            for name in ALLOWED_COMMANDS
        }

    def dependency_report(self) -> DependencyReport:
        required_missing = [name for name in REQUIRED_COMMANDS if self._command_paths.get(name) is None]
        optional_missing = [
            name for name in ALLOWED_COMMANDS if name not in REQUIRED_COMMANDS and self._command_paths.get(name) is None
        ]
        return DependencyReport(required_missing=required_missing, optional_missing=optional_missing)

    def inspect_root(self) -> str:
        if self._command_paths.get("tree") is not None:
            result = self._try_run(
                ["tree", "-a", "-L", "2", "--noreport", "-I", ".git", str(self.root)],
                allowed_returncodes={0},
                context="root inspection via tree",
            )
            if result is not None:
                text = result.stdout.strip()
                if text:
                    return _truncate(text, 1500)
        result = self._try_run(
            ["ls", "-la", str(self.root)],
            allowed_returncodes={0},
            context="root inspection via ls",
        )
        if result is None:
            self.logger.warn("Root inspection failed; continuing without a root overview")
            return ""
        return _truncate(result.stdout.strip(), 1500)

    def search(self, intent: SearchIntent) -> list[SearchCandidate]:
        by_path: dict[Path, SearchCandidate] = {}
        self._search_paths(intent, by_path)
        self._search_contents(intent, by_path)
        if not by_path and intent.extensions:
            fallback_intent = SearchIntent(
                query_summary=intent.query_summary,
                path_terms=intent.path_terms[:],
                content_terms=intent.content_terms[:],
                filename_hints=intent.filename_hints[:],
                extensions=[],
                sort_hint=intent.sort_hint,
                notes=intent.notes[:] + ["Retried without model-suggested extensions."],
                planning_source=intent.planning_source,
            )
            self.logger.warn("No candidates found with extension filter; retrying without extensions")
            self._search_paths(fallback_intent, by_path)
            self._search_contents(fallback_intent, by_path)
        candidates = [candidate for candidate in by_path.values() if self._is_within_root(candidate.path)]
        self._enrich_metadata(candidates[: self.max_candidates])
        self._sort_candidates(candidates, intent.sort_hint)
        return candidates[: self.max_candidates]

    def execute_action(self, action: AgentAction, by_path: dict[Path, SearchCandidate]) -> AgentObservation:
        self._recent_warnings = []
        before_paths = set(by_path)
        if action.action == "search_paths":
            self._search_paths(
                SearchIntent(
                    query_summary=action.reasoning or "Agent path search",
                    path_terms=action.terms[:],
                    filename_hints=action.terms[:],
                    extensions=action.extensions[:],
                    planning_source=action.source,
                ),
                by_path,
            )
        elif action.action == "search_contents":
            self._search_contents(
                SearchIntent(
                    query_summary=action.reasoning or "Agent content search",
                    content_terms=action.terms[:],
                    path_terms=action.terms[:],
                    extensions=action.extensions[:],
                    planning_source=action.source,
                ),
                by_path,
            )
        candidates = self.finalize_candidates(by_path, sort_hint="relevance")
        new_paths = [
            self._display_path(candidate.path)
            for candidate in candidates
            if candidate.path not in before_paths
        ]
        if action.action == "finish":
            summary = action.final_summary or "Agent finished without another tool action."
        elif new_paths:
            summary = (
                f"{action.action} added {len(new_paths)} candidate(s); "
                f"top now: {', '.join(self._display_path(item.path) for item in candidates[:3])}"
            )
        elif candidates:
            summary = (
                f"{action.action} added no new candidates; "
                f"current top: {', '.join(self._display_path(item.path) for item in candidates[:3])}"
            )
        else:
            summary = f"{action.action} found no candidates."
        return AgentObservation(
            action=action.action,
            summary=summary,
            executed_terms=action.terms[:],
            total_candidates=len(candidates),
            new_candidates=new_paths[:5],
            top_paths=[self._display_path(item.path) for item in candidates[:5]],
            warnings=self._recent_warnings[:],
        )

    def finalize_candidates(self, by_path: dict[Path, SearchCandidate], *, sort_hint: str) -> list[SearchCandidate]:
        candidates = [candidate for candidate in by_path.values() if self._is_within_root(candidate.path)]
        self._enrich_metadata(candidates[: self.max_candidates])
        self._sort_candidates(candidates, sort_hint)
        return candidates[: self.max_candidates]

    def _search_paths(self, intent: SearchIntent, by_path: dict[Path, SearchCandidate]) -> None:
        terms = _dedupe(intent.filename_hints + intent.path_terms)
        for term in terms[:6]:
            safe_term = self._validated_search_term(term, context="path search")
            if safe_term is None:
                continue
            argv = [
                "fd",
                "-0",
                "-i",
                "-t",
                "f",
                "--hidden",
                "--exclude",
                ".git",
            ]
            for extension in intent.extensions[:4]:
                argv.extend(["-e", extension])
            argv.extend(["--", safe_term, str(self.root)])
            result = self._try_run(argv, allowed_returncodes={0}, context=f"path search for '{safe_term}'")
            if result is None:
                continue
            for raw_path in [item for item in result.stdout.split("\0") if item]:
                path = Path(raw_path).resolve()
                if not path.is_file() or not self._is_within_root(path):
                    continue
                candidate = by_path.setdefault(path, SearchCandidate(path=path))
                weight = 8.0 if safe_term in path.name.lower() else 4.0
                candidate.score += weight
                _append_unique(candidate.reasons, f"path matches '{safe_term}'")

    def _search_contents(self, intent: SearchIntent, by_path: dict[Path, SearchCandidate]) -> None:
        terms = _dedupe(intent.content_terms or intent.path_terms)
        for term in terms[:6]:
            safe_term = self._validated_search_term(term, context="content search")
            if safe_term is None:
                continue
            argv = ["rg", "--no-config", "--json", "-n", "-i", "--hidden", "--glob", "!.git", "-m", "2"]
            for extension in intent.extensions[:4]:
                argv.extend(["-g", f"*.{extension}"])
            argv.extend(["--", safe_term, str(self.root)])
            result = self._try_run(argv, allowed_returncodes={0, 1}, context=f"content search for '{safe_term}'")
            if result is None:
                continue
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
                if not path.is_file() or not self._is_within_root(path):
                    continue
                candidate = by_path.setdefault(path, SearchCandidate(path=path))
                candidate.score += 12.0
                _append_unique(candidate.reasons, f"content matches '{safe_term}'")
                line_number = int(data.get("line_number") or 0)
                text = (((data.get("lines") or {}).get("text")) or "").strip()
                if text:
                    snippet = f"L{line_number}: {text[:180]}"
                    _append_unique(candidate.snippets, snippet)
                if line_number:
                    _append_unique_int(candidate.line_numbers, line_number)

    def _enrich_metadata(self, candidates: list[SearchCandidate]) -> None:
        for candidate in candidates:
            if self._command_paths.get("stat") is not None:
                result = self._try_run(
                    ["stat", "-f", "%m|%z|%N", str(candidate.path)],
                    allowed_returncodes={0},
                    context=f"metadata lookup via stat for {candidate.path.name}",
                )
                if result is not None:
                    parts = result.stdout.strip().split("|", maxsplit=2)
                    if len(parts) >= 2:
                        candidate.mtime_epoch = int(parts[0])
                        candidate.size_bytes = int(parts[1])
            if self._command_paths.get("mdls") is not None:
                result = self._try_run(
                    ["mdls", "-raw", "-name", "kMDItemKind", str(candidate.path)],
                    allowed_returncodes={0, 1},
                    context=f"metadata lookup via mdls for {candidate.path.name}",
                )
                if result is not None:
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
        if not argv:
            raise ValueError("Command not allowed: <empty>")
        executable = argv[0]
        if executable not in ALLOWED_COMMANDS:
            raise ValueError(f"Command not allowed: {executable}")
        self._validate_argv(argv)
        command_path = self._command_paths.get(executable)
        if command_path is None:
            raise RuntimeError(f"Command not available in trusted macOS paths: {executable}")
        self.logger.command(argv)
        result = subprocess.run(
            [str(command_path), *argv[1:]],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=self._command_env(),
            check=False,
        )
        if result.returncode not in allowed_returncodes:
            stderr = result.stderr.strip() or "unknown command error"
            raise RuntimeError(f"{executable} failed with code {result.returncode}: {stderr}")
        return result

    def _try_run(
        self,
        argv: list[str],
        *,
        allowed_returncodes: set[int],
        context: str,
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            return self._run(argv, allowed_returncodes=allowed_returncodes)
        except (RuntimeError, ValueError) as exc:
            message = f"{context} failed; continuing with fallback behavior: {exc}"
            self._recent_warnings.append(message)
            self.logger.warn(message)
            return None

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def _resolve_command_path(self, executable: str) -> Path | None:
        path = shutil.which(executable, path=self._trusted_search_path)
        return Path(path).resolve() if path else None

    def _command_env(self) -> dict[str, str]:
        env = {"NO_COLOR": "1", "PATH": self._trusted_search_path}
        for key in SAFE_ENV_KEYS:
            value = os.environ.get(key)
            if value:
                env[key] = value
        return env

    def _validate_argv(self, argv: list[str]) -> None:
        executable = argv[0]
        if executable == "fd":
            self._validate_fd_argv(argv)
            return
        if executable == "rg":
            self._validate_rg_argv(argv)
            return
        if executable == "ls":
            if argv != ["ls", "-la", str(self.root)]:
                raise ValueError("Invalid ls invocation")
            return
        if executable == "tree":
            if argv != ["tree", "-a", "-L", "2", "--noreport", "-I", ".git", str(self.root)]:
                raise ValueError("Invalid tree invocation")
            return
        if executable == "stat":
            if len(argv) != 4 or argv[:3] != ["stat", "-f", "%m|%z|%N"] or not self._is_within_root(Path(argv[3])):
                raise ValueError("Invalid stat invocation")
            return
        if executable == "mdls":
            if (
                len(argv) != 5
                or argv[:4] != ["mdls", "-raw", "-name", "kMDItemKind"]
                or not self._is_within_root(Path(argv[4]))
            ):
                raise ValueError("Invalid mdls invocation")
            return
        raise ValueError(f"Command not allowed: {executable}")

    def _validate_fd_argv(self, argv: list[str]) -> None:
        prefix = ["fd", "-0", "-i", "-t", "f", "--hidden", "--exclude", ".git"]
        if argv[: len(prefix)] != prefix:
            raise ValueError("Invalid fd invocation")
        index = len(prefix)
        while index + 1 < len(argv) and argv[index] == "-e":
            extension = argv[index + 1]
            if not extension or extension.startswith("-"):
                raise ValueError("Invalid fd extension filter")
            index += 2
        if len(argv) != index + 3 or argv[index] != "--" or argv[index + 2] != str(self.root):
            raise ValueError("Invalid fd search arguments")

    def _validate_rg_argv(self, argv: list[str]) -> None:
        prefix = ["rg", "--no-config", "--json", "-n", "-i", "--hidden", "--glob", "!.git", "-m", "2"]
        if argv[: len(prefix)] != prefix:
            raise ValueError("Invalid rg invocation")
        index = len(prefix)
        while index + 1 < len(argv) and argv[index] == "-g":
            glob = argv[index + 1]
            if not glob or glob.startswith("-"):
                raise ValueError("Invalid rg glob filter")
            index += 2
        if len(argv) != index + 3 or argv[index] != "--" or argv[index + 2] != str(self.root):
            raise ValueError("Invalid rg search arguments")

    def _validated_search_term(self, term: str, *, context: str) -> str | None:
        cleaned = term.strip()
        if not cleaned:
            return None
        if cleaned.startswith("-") or any(char in cleaned for char in ("\0", "\n", "\r")):
            message = f"{context} skipped suspicious term: {cleaned!r}"
            self._recent_warnings.append(message)
            self.logger.warn(message)
            return None
        return cleaned

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root)
            return True
        except ValueError:
            return False


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
