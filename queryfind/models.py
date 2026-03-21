from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SearchIntent:
    query_summary: str
    path_terms: list[str] = field(default_factory=list)
    content_terms: list[str] = field(default_factory=list)
    filename_hints: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    sort_hint: str = "relevance"
    notes: list[str] = field(default_factory=list)
    planning_source: str = "heuristic"


@dataclass(slots=True)
class SearchCandidate:
    path: Path
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    snippets: list[str] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)
    size_bytes: int | None = None
    mtime_epoch: int | None = None
    kind: str | None = None


@dataclass(slots=True)
class SearchOutcome:
    summary: str
    results: list[SearchCandidate]
    ranking_source: str
