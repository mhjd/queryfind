from __future__ import annotations

import argparse
from pathlib import Path

from queryfind.app import run_doctor, run_search
from queryfind.config import AppConfig, DEFAULT_MODEL, DEFAULT_OLLAMA_URL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="queryfind",
        description="Natural-language local file search with a read-only command allowlist.",
    )
    parser.add_argument("query", nargs="?", help="Natural-language file search request.")
    parser.add_argument("--root", default=".", help="Directory to search. Defaults to the current directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Local Ollama model to use.")
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help="Base URL for the local Ollama server.",
    )
    parser.add_argument(
        "--think-level",
        default="medium",
        choices=("low", "medium", "high"),
        help="Thinking level for GPT-OSS models.",
    )
    parser.add_argument(
        "--max-agent-steps",
        type=int,
        default=4,
        help="Maximum tool-observation iterations before final ranking.",
    )
    parser.add_argument("--max-candidates", type=int, default=20, help="Maximum candidates to keep before ranking.")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum ranked results to display.")
    parser.add_argument("--no-llm", action="store_true", help="Disable Ollama and use heuristics only.")
    parser.add_argument(
        "--no-ollama-autostart",
        action="store_true",
        help="Do not auto-start Ollama when it is not already running.",
    )
    parser.add_argument(
        "--ollama-start-timeout",
        type=float,
        default=12.0,
        help="Seconds to wait for an auto-started Ollama server to become reachable.",
    )
    parser.add_argument(
        "--hide-thinking",
        action="store_true",
        help="Hide streamed model reasoning while still using the local model.",
    )
    parser.add_argument("--doctor", action="store_true", help="Check tool and Ollama availability.")
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory for QueryFind log files. Defaults to ./.queryfind/logs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.doctor and not args.query:
        parser.error("a query is required unless --doctor is used")
    max_results = max(1, args.max_results)
    max_candidates = max(max_results, args.max_candidates)
    config = AppConfig(
        query=args.query,
        root=Path(args.root),
        model=args.model,
        ollama_url=args.ollama_url,
        think_level=args.think_level,
        max_agent_steps=max(1, args.max_agent_steps),
        max_candidates=max_candidates,
        max_results=max_results,
        no_llm=bool(args.no_llm),
        show_thinking=not bool(args.hide_thinking),
        ollama_autostart=not bool(args.no_ollama_autostart),
        ollama_start_timeout=max(1.0, args.ollama_start_timeout),
        log_dir=Path(args.log_dir) if args.log_dir else None,
    )
    if args.doctor:
        return run_doctor(config)
    return run_search(config)
