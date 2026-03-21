from __future__ import annotations

from collections.abc import Iterable
import json
import re

from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.models import AgentAction, AgentStep, SearchCandidate, SearchIntent, SearchOutcome
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

AGENT_ACTIONS = {"search_paths", "search_contents", "finish"}


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
    agent_steps: list[AgentStep] | None = None,
    final_summary_hint: str = "",
    config: AppConfig,
    logger: RunLogger,
    client: OllamaClient | None,
) -> SearchOutcome:
    if not candidates:
        return SearchOutcome(
            summary=final_summary_hint or "No matching files were found.",
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
            "content": (
                f"Query:\n{query}\n\n"
                f"Agent observations:\n{_trace_snapshot(agent_steps or [])}\n\n"
                f"Candidate shortlist:\n{candidate_blob}\n\n"
                f"Current best hypothesis:\n{final_summary_hint or '(none)'}"
            ),
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
            summary=str(payload.get("summary") or final_summary_hint or "Ranked candidates from local evidence."),
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


def next_agent_action(
    query: str,
    *,
    root_overview: str,
    candidates: list[SearchCandidate],
    steps: list[AgentStep],
    config: AppConfig,
    logger: RunLogger,
    client: OllamaClient | None,
) -> AgentAction:
    heuristic = heuristic_next_action(query, steps)
    if config.no_llm or client is None:
        logger.info("Using heuristic agent action")
        return heuristic

    messages = [
        {
            "role": "system",
            "content": (
                "You are driving a local file search agent. "
                "Do not produce shell commands. "
                "Choose exactly one next action and output only one JSON object with keys "
                "action, terms, extensions, reasoning, final_summary. "
                "action must be one of search_paths, search_contents, finish. "
                "Use short terms arrays. "
                "Use finish when the current evidence is sufficient or the answer is likely absent."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query:\n{query}\n\n"
                f"Root overview:\n{root_overview or '(not available)'}\n\n"
                f"Previous observations:\n{_trace_snapshot(steps)}\n\n"
                f"Current candidates:\n{_candidate_snapshot(candidates)}\n\n"
                "Remember: execution is limited to fd, rg, ls, tree, stat, mdls via the application."
            ),
        },
    ]
    try:
        response = _stream_completion(
            client=client,
            config=config,
            logger=logger,
            label="Streaming agent-step thinking",
            messages=messages,
        )
        payload = _extract_json_object(response)
        action = _parse_agent_action(payload)
        if action is None:
            logger.warn("Agent action JSON parse failed; falling back to heuristic action")
            return heuristic
        action.source = "ollama"
        return action
    except OllamaUnavailableError as exc:
        logger.warn(f"Ollama agent step unavailable: {exc}")
        return heuristic


def heuristic_next_action(query: str, steps: list[AgentStep]) -> AgentAction:
    intent = heuristic_intent(query)
    used_path_terms = {
        term for step in steps if step.action.action == "search_paths" for term in step.action.terms
    }
    used_content_terms = {
        term for step in steps if step.action.action == "search_contents" for term in step.action.terms
    }
    remaining_path_terms = [
        term for term in _dedupe_terms(intent.filename_hints + intent.path_terms) if term not in used_path_terms
    ]
    remaining_content_terms = [
        term for term in _dedupe_terms(intent.content_terms or intent.path_terms) if term not in used_content_terms
    ]
    if remaining_path_terms:
        return AgentAction(
            action="search_paths",
            terms=remaining_path_terms[:2],
            extensions=intent.extensions[:4],
            reasoning="Heuristic path-first exploration.",
            source="heuristic",
        )
    if remaining_content_terms:
        return AgentAction(
            action="search_contents",
            terms=remaining_content_terms[:2],
            extensions=intent.extensions[:4],
            reasoning="Heuristic content follow-up.",
            source="heuristic",
        )
    return AgentAction(
        action="finish",
        final_summary="The heuristic search loop exhausted its planned steps.",
        reasoning="No unused heuristic terms remain.",
        source="heuristic",
    )


def _stream_completion(
    *,
    client: OllamaClient,
    config: AppConfig,
    logger: RunLogger,
    label: str,
    messages: list[dict[str, str]],
) -> str:
    if not config.show_thinking:
        logger.info(f"{label} (non-streaming JSON mode)")
        return client.chat_json(
            model=config.model,
            messages=messages,
            think=resolve_think_value(config.model, config.think_level),
        )

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


def _parse_agent_action(payload: dict | None) -> AgentAction | None:
    if payload is None:
        return None
    action = str(payload.get("action") or "").strip()
    if action not in AGENT_ACTIONS:
        return None
    return AgentAction(
        action=action,
        terms=_list_of_strings(payload.get("terms"))[:3],
        extensions=_valid_extensions(_list_of_strings(payload.get("extensions")))[:4],
        reasoning=str(payload.get("reasoning") or "").strip(),
        final_summary=str(payload.get("final_summary") or "").strip(),
    )


def _trace_snapshot(steps: list[AgentStep]) -> str:
    if not steps:
        return "(none yet)"
    lines: list[str] = []
    for step in steps[-5:]:
        lines.append(
            f"step {step.index}: action={step.action.action} terms={step.action.terms or ['-']} "
            f"source={step.action.source}"
        )
        if step.observation is not None:
            lines.append(f"observation: {step.observation.summary}")
            if step.observation.warnings:
                lines.append(f"warnings: {'; '.join(step.observation.warnings[:2])}")
    return "\n".join(lines)


def _candidate_snapshot(candidates: list[SearchCandidate], *, limit: int = 5) -> str:
    if not candidates:
        return "(none yet)"
    rows = []
    for candidate in candidates[:limit]:
        rows.append(
            json.dumps(
                {
                    "path": str(candidate.path),
                    "score": round(candidate.score, 2),
                    "reasons": candidate.reasons[:2],
                    "snippets": candidate.snippets[:1],
                    "kind": candidate.kind,
                }
            )
        )
    return "\n".join(rows)


def _dedupe_terms(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        cleaned = item.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output
