from __future__ import annotations

from collections.abc import Iterable
import json
import re

from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.models import SearchCandidate, SearchIntent, SearchOutcome
from queryfind.ollama_client import OllamaClient, OllamaUnavailableError, resolve_think_value

STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "for",
    "find",
    "from",
    "in",
    "is",
    "latest",
    "me",
    "of",
    "on",
    "recent",
    "show",
    "signed",
    "the",
    "to",
    "with",
}

EXTENSIONS = {
    "csv",
    "doc",
    "docx",
    "json",
    "md",
    "pdf",
    "py",
    "rst",
    "txt",
    "xlsx",
}


def plan_search(
    query: str,
    *,
    root_overview: str,
    config: AppConfig,
    logger: RunLogger,
    client: OllamaClient | None,
) -> SearchIntent:
    heuristic = heuristic_intent(query)
    if config.no_llm or client is None:
        logger.info("Using heuristic planner")
        return heuristic

    messages = [
        {
            "role": "system",
            "content": (
                "You are planning a local file search. "
                "Do not produce shell commands. "
                "Output only one JSON object with the keys "
                "query_summary, path_terms, content_terms, filename_hints, "
                "extensions, sort_hint, notes. "
                "Use concise arrays. "
                "Only mention extensions when they materially help."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query:\n{query}\n\n"
                f"Root overview:\n{root_overview or '(not available)'}\n\n"
                "Remember: execution is limited to fd, rg, ls, tree, stat, mdls."
            ),
        },
    ]
    try:
        response = _stream_completion(
            client=client,
            config=config,
            logger=logger,
            label="Streaming planner thinking",
            messages=messages,
        )
        payload = _extract_json_object(response)
        if payload is None:
            logger.warn("Planner JSON parse failed; falling back to heuristic planner")
            return heuristic
        return SearchIntent(
            query_summary=str(payload.get("query_summary") or heuristic.query_summary),
            path_terms=_list_of_strings(payload.get("path_terms")) or heuristic.path_terms,
            content_terms=_list_of_strings(payload.get("content_terms")) or heuristic.content_terms,
            filename_hints=_list_of_strings(payload.get("filename_hints")) or heuristic.filename_hints,
            extensions=_valid_extensions(_list_of_strings(payload.get("extensions")) or heuristic.extensions),
            sort_hint=str(payload.get("sort_hint") or heuristic.sort_hint),
            notes=_list_of_strings(payload.get("notes")),
            planning_source="ollama",
        )
    except OllamaUnavailableError as exc:
        logger.warn(f"Ollama planning unavailable: {exc}")
        return heuristic


def rank_results(
    query: str,
    *,
    candidates: list[SearchCandidate],
    config: AppConfig,
    logger: RunLogger,
    client: OllamaClient | None,
) -> SearchOutcome:
    if not candidates:
        return SearchOutcome(
            summary="No matching files were found.",
            results=[],
            ranking_source="heuristic",
        )
    if config.no_llm or client is None:
        return heuristic_ranking(query, candidates, limit=config.max_results)

    candidate_blob = json.dumps(
        [
            {
                "path": str(candidate.path),
                "score": round(candidate.score, 2),
                "reasons": candidate.reasons,
                "snippets": candidate.snippets,
                "mtime_epoch": candidate.mtime_epoch,
                "size_bytes": candidate.size_bytes,
                "kind": candidate.kind,
            }
            for candidate in candidates[:8]
        ],
        indent=2,
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are ranking local file search candidates. "
                "Output only one JSON object with keys summary and results. "
                "results must be an array of objects with keys path and why. "
                "Keep the summary short and grounded in the evidence."
            ),
        },
        {
            "role": "user",
            "content": f"Query:\n{query}\n\nCandidates:\n{candidate_blob}",
        },
    ]
    try:
        response = _stream_completion(
            client=client,
            config=config,
            logger=logger,
            label="Streaming ranking thinking",
            messages=messages,
        )
        payload = _extract_json_object(response)
        if payload is None:
            logger.warn("Ranking JSON parse failed; falling back to heuristic ranking")
            return heuristic_ranking(query, candidates, limit=config.max_results)
        path_map = {str(candidate.path): candidate for candidate in candidates}
        ranked: list[SearchCandidate] = []
        for item in payload.get("results", []):
            path = str(item.get("path") or "")
            candidate = path_map.get(path)
            if candidate is None:
                continue
            why = str(item.get("why") or "").strip()
            if why:
                candidate.reasons.insert(0, why)
            ranked.append(candidate)
        if not ranked:
            return heuristic_ranking(query, candidates, limit=config.max_results)
        return SearchOutcome(
            summary=str(payload.get("summary") or "Ranked candidates from local evidence."),
            results=ranked[: config.max_results],
            ranking_source="ollama",
        )
    except OllamaUnavailableError as exc:
        logger.warn(f"Ollama ranking unavailable: {exc}")
        return heuristic_ranking(query, candidates, limit=config.max_results)


def heuristic_intent(query: str) -> SearchIntent:
    lowered = query.lower()
    quoted_matches = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
    quoted_terms = [next(part for part in match if part).strip() for match in quoted_matches]
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,}", lowered)
    filtered = [token for token in tokens if token not in STOPWORDS]
    extensions = [token.lstrip(".") for token in filtered if token.lstrip(".") in EXTENSIONS]
    filename_hints = [token for token in filtered if token not in EXTENSIONS][:4]
    content_terms = quoted_terms or filtered[:4]
    sort_hint = "mtime_desc" if any(word in lowered for word in ("latest", "newest", "recent")) else "relevance"
    notes = []
    if "signed" in lowered:
        notes.append("Prefer files that look final or signed.")
    return SearchIntent(
        query_summary=query.strip(),
        path_terms=filtered[:6],
        content_terms=content_terms[:4],
        filename_hints=filename_hints[:4],
        extensions=extensions[:4],
        sort_hint=sort_hint,
        notes=notes,
        planning_source="heuristic",
    )


def heuristic_ranking(query: str, candidates: list[SearchCandidate], *, limit: int) -> SearchOutcome:
    top = candidates[:]
    summary = f"Ranked {min(len(top), limit)} candidates for: {query}"
    return SearchOutcome(summary=summary, results=top[:limit], ranking_source="heuristic")


def _stream_completion(
    *,
    client: OllamaClient,
    config: AppConfig,
    logger: RunLogger,
    label: str,
    messages: list[dict[str, str]],
) -> str:
    logger.start_stream(label)
    thinking_seen = False
    content_seen = False
    content_parts: list[str] = []
    try:
        for chunk in client.chat_stream(
            model=config.model,
            messages=messages,
            think=resolve_think_value(config.model, config.think_level),
        ):
            if config.show_thinking and chunk.thinking:
                thinking_seen = True
                logger.write_stream(chunk.thinking)
            if chunk.content:
                if config.show_thinking and thinking_seen and not content_seen:
                    logger.write_stream("\n\nFinal response:\n")
                content_seen = True
                logger.write_stream(chunk.content)
                content_parts.append(chunk.content)
    finally:
        logger.end_stream()
    return "".join(content_parts).strip()


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _valid_extensions(items: list[str]) -> list[str]:
    return [item.lstrip(".") for item in items if item.lstrip(".") in EXTENSIONS]
