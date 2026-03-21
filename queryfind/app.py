from __future__ import annotations

from datetime import datetime

from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.ollama_client import OllamaClient
from queryfind.planner import plan_search, rank_results
from queryfind.render import render_intent, render_outcome
from queryfind.search_backend import SearchBackend


def resolve_search_client(config: AppConfig, logger: RunLogger, *, timestamp: str) -> OllamaClient | None:
    client = None if config.no_llm else OllamaClient(config.ollama_url)
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
                logger.warn("automatic Ollama startup failed; using heuristic fallback")
        else:
            logger.warn("local Ollama server unavailable; using heuristic fallback")
        if llm_available:
            try:
                tags = client.tags()
            except Exception:
                tags = []
            if not tags:
                logger.warn("Ollama is running but no models are installed; using heuristic fallback")
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

        logger.info("collecting root overview")
        root_overview = backend.inspect_root()
        intent = plan_search(
            config.query or "",
            root_overview=root_overview,
            config=config,
            logger=logger,
            client=client,
        )
        render_intent(intent)

        logger.info("executing local search pipeline")
        candidates = backend.search(intent)
        if not candidates:
            logger.warn("no files matched the current query")
        outcome = rank_results(
            config.query or "",
            candidates=candidates,
            config=config,
            logger=logger,
            client=client,
        )
        render_outcome(outcome)
        logger.info(f"log file: {logger.log_path}")
        return 0 if outcome.results else 1
    finally:
        logger.close()


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

        client = OllamaClient(config.ollama_url)
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
