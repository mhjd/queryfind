from __future__ import annotations

from datetime import datetime
import time

from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.models import AgentStep, SearchExecution
from queryfind.ollama_client import OllamaClient
from queryfind.planner import heuristic_intent, next_agent_action, rank_results
from queryfind.render import render_outcome
from queryfind.search_backend import SearchBackend


def resolve_search_client(config: AppConfig, logger: RunLogger, *, timestamp: str) -> OllamaClient | None:
    client = None if config.no_llm else OllamaClient(
        config.ollama_url,
        request_timeout=config.ollama_request_timeout,
    )
    llm_available = False
    if client is not None:
        llm_available = client.available()
        if llm_available:
            logger.info("local Ollama server available")
        elif config.ollama_autostart:
            server_log_path = logger.log_path.parent / f"ollama-serve-{timestamp}.log"
            logger.info("local Ollama server unavailable; attempting automatic startup")
            llm_available = client.ensure_running(
                timeout=config.ollama_start_timeout,
                server_log_path=server_log_path,
            )
            if llm_available:
                logger.info("local Ollama server started automatically")
            else:
                logger.warn("automatic Ollama startup failed")
        else:
            logger.warn("local Ollama server unavailable")
        if llm_available:
            try:
                tags = client.tags()
            except Exception:
                tags = []
            if not tags:
                logger.warn("Ollama is running but no models are installed")
                llm_available = False
            elif config.model not in tags:
                logger.warn(f"configured model not installed locally: {config.model}")
                llm_available = False
        else:
            client = None
        if not llm_available:
            client = None
    else:
        logger.info("LLM disabled by flag; using heuristic fallback")
    return client


def run_search(config: AppConfig) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger = RunLogger(config.resolved_log_dir / f"queryfind-{timestamp}.log")
    try:
        logger.info(f"search root: {config.resolved_root}")
        logger.info(f"model: {config.model}")
        backend = SearchBackend(root=config.resolved_root, logger=logger, max_candidates=config.max_candidates)
        report = backend.dependency_report()
        if report.required_missing:
            logger.error(f"missing required commands: {', '.join(report.required_missing)}")
            return 2
        if report.optional_missing:
            logger.warn(f"missing optional commands: {', '.join(report.optional_missing)}")

        client = resolve_search_client(config, logger, timestamp=timestamp)
        if not config.no_llm and client is None:
            logger.error("LLM mode requested but the configured local model is unavailable")
            logger.info(f"log file: {logger.log_path}")
            return 2
        execution = execute_search(config, logger, backend=backend, client=client)
        if not execution.outcome.results:
            logger.warn("no files matched the current query")
        render_outcome(execution.outcome)
        logger.info(f"log file: {logger.log_path}")
        return 0 if execution.outcome.results else 1
    finally:
        logger.close()


def execute_search(
    config: AppConfig,
    logger: RunLogger,
    *,
    backend: SearchBackend | None = None,
    client: OllamaClient | None = None,
    root_overview: str | None = None,
) -> SearchExecution:
    backend = backend or SearchBackend(root=config.resolved_root, logger=logger, max_candidates=config.max_candidates)
    logger.info("collecting root overview")
    root_overview = root_overview if root_overview is not None else backend.inspect_root()

    sort_hint = heuristic_intent(config.query or "").sort_hint
    by_path = {}
    steps: list[AgentStep] = []
    final_summary_hint = ""
    agent_start = time.perf_counter()

    for index in range(1, config.max_agent_steps + 1):
        candidates = backend.finalize_candidates(by_path, sort_hint=sort_hint)
        action = next_agent_action(
            config.query or "",
            root_overview=root_overview,
            candidates=candidates,
            steps=steps,
            config=config,
            logger=logger,
            client=client,
        )
        logger.info(
            f"agent step {index}/{config.max_agent_steps}: action={action.action} "
            f"terms={action.terms or ['-']} source={action.source}"
        )
        step = AgentStep(index=index, action=action)
        observation = backend.execute_action(action, by_path)
        step.observation = observation
        steps.append(step)
        if action.final_summary:
            final_summary_hint = action.final_summary
        logger.info(f"agent observation {index}: {observation.summary}")
        if observation.warnings:
            logger.info(f"agent warnings {index}: {'; '.join(observation.warnings[:2])}")
        if action.action == "finish":
            break
    else:
        logger.warn("agent loop reached the step limit; ranking current candidates")

    candidates = backend.finalize_candidates(by_path, sort_hint=sort_hint)
    agent_ms = (time.perf_counter() - agent_start) * 1000.0

    ranking_start = time.perf_counter()
    outcome = rank_results(
        config.query or "",
        candidates=candidates,
        agent_steps=steps,
        final_summary_hint=final_summary_hint,
        config=config,
        logger=logger,
        client=client,
    )
    ranking_ms = (time.perf_counter() - ranking_start) * 1000.0
    return SearchExecution(
        outcome=outcome,
        candidates=candidates,
        agent_steps=steps,
        agent_ms=round(agent_ms, 3),
        ranking_ms=round(ranking_ms, 3),
    )


def run_doctor(config: AppConfig) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger = RunLogger(config.resolved_log_dir / f"queryfind-doctor-{timestamp}.log")
    try:
        logger.info(f"doctor root: {config.resolved_root}")
        backend = SearchBackend(root=config.resolved_root, logger=logger, max_candidates=config.max_candidates)
        report = backend.dependency_report()
        if report.required_missing:
            logger.error(f"missing required commands: {', '.join(report.required_missing)}")
        else:
            logger.info("required commands available: fd, rg")
        if report.optional_missing:
            logger.warn(f"missing optional commands: {', '.join(report.optional_missing)}")
        else:
            logger.info("optional commands available: ls, tree, stat, mdls")

        client = OllamaClient(config.ollama_url, request_timeout=config.ollama_request_timeout)
        if client.available():
            tags = client.tags()
            logger.info(f"Ollama reachable at {config.ollama_url}")
            if tags:
                logger.info(f"installed models: {', '.join(tags)}")
            else:
                logger.warn("Ollama reachable but no models are installed")
        else:
            logger.warn(f"Ollama not reachable at {config.ollama_url}")
        logger.info(f"log file: {logger.log_path}")
        return 0
    finally:
        logger.close()
