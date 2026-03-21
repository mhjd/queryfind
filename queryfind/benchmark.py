from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from statistics import mean, median
import time

from queryfind.app import execute_search, resolve_search_client
from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.search_backend import SearchBackend


@dataclass(slots=True)
class BenchmarkCase:
    name: str
    category: str
    difficulty: str
    capability_tags: list[str]
    query: str
    expected_path: str | None
    acceptable_paths: list[str]
    expected_snippet: str | None = None
    top_k: int = 3


@dataclass(slots=True)
class BenchmarkManifest:
    suite_name: str
    description: str
    corpus_root: Path
    mtimes: dict[str, str]
    cases: list[BenchmarkCase]


@dataclass(slots=True)
class CaseRunResult:
    target: str
    repeat_index: int
    case_name: str
    category: str
    difficulty: str
    capability_tags: list[str]
    query: str
    expected_path: str | None
    expected_snippet: str | None
    success: bool
    matched_rank: int | None
    matched_path: str | None
    snippet_matched: bool
    top_paths: list[str]
    planning_source: str
    ranking_source: str
    agent_step_count: int
    llm_agent_turn_count: int
    candidate_count: int
    command_count: int
    total_ms: float
    planning_ms: float
    search_ms: float
    ranking_ms: float


@dataclass(slots=True)
class TargetSummary:
    target: str
    repeat_count: int
    case_count: int
    success_count: int
    top1_count: int
    top3_count: int
    snippet_case_count: int
    snippet_success_count: int
    no_answer_case_count: int
    no_answer_success_count: int
    mrr: float
    success_rate: float
    top1_rate: float
    top3_rate: float
    snippet_success_rate: float | None
    no_answer_success_rate: float | None
    median_total_ms: float
    mean_total_ms: float
    p95_total_ms: float
    median_planning_ms: float
    median_search_ms: float
    median_ranking_ms: float
    median_agent_step_count: float
    median_llm_agent_turn_count: float
    median_candidate_count: float
    median_command_count: float
    llm_agent_case_rate: float
    llm_planner_rate: float
    llm_ranker_rate: float


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_MANIFEST_PATH = REPO_ROOT / "benchmark_fs" / "full_manifest.json"
DEFAULT_REPORT_DIR = REPO_ROOT / ".queryfind" / "benchmarks"


def load_manifest(path: Path = BENCHMARK_MANIFEST_PATH) -> BenchmarkManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        BenchmarkCase(
            name=item["name"],
            category=item["category"],
            difficulty=item["difficulty"],
            capability_tags=[str(tag) for tag in item.get("capability_tags", [])],
            query=item["query"],
            expected_path=item.get("expected_path"),
            acceptable_paths=[str(path) for path in item.get("acceptable_paths", [])]
            or ([str(item["expected_path"])] if item.get("expected_path") else []),
            expected_snippet=item.get("expected_snippet"),
            top_k=int(item.get("top_k", 3)),
        )
        for item in payload["cases"]
    ]
    return BenchmarkManifest(
        suite_name=str(payload["suite_name"]),
        description=str(payload["description"]),
        corpus_root=(path.parent / payload["corpus_root"]).resolve(),
        mtimes={str(key): str(value) for key, value in payload["mtimes"].items()},
        cases=cases,
    )


def normalize_corpus_metadata(manifest: BenchmarkManifest) -> None:
    for relative_path, iso_value in manifest.mtimes.items():
        path = manifest.corpus_root / relative_path
        timestamp = datetime.fromisoformat(iso_value).astimezone(timezone.utc).timestamp()
        os.utime(path, (timestamp, timestamp))


def run_benchmark(
    *,
    models: list[str] | None = None,
    include_heuristic: bool = False,
    case_names: set[str] | None = None,
    categories: set[str] | None = None,
    difficulties: set[str] | None = None,
    repeats: int = 1,
    report_dir: Path = DEFAULT_REPORT_DIR,
    quiet: bool = False,
) -> tuple[BenchmarkManifest, list[CaseRunResult], list[TargetSummary], Path]:
    manifest = load_manifest()
    normalize_corpus_metadata(manifest)

    targets: list[tuple[str, bool, str | None]] = []
    if include_heuristic:
        targets.append(("heuristic", False, None))
    selected_models = ["qwen3.5:27b"] if models is None and not include_heuristic else (models or [])
    for model in selected_models:
        targets.append((model, True, model))

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir.mkdir(parents=True, exist_ok=True)
    logger = RunLogger(report_dir / f"benchmark-{timestamp}.log", echo=not quiet)
    all_results: list[CaseRunResult] = []
    summaries: list[TargetSummary] = []
    try:
        selected_cases = [
            case
            for case in manifest.cases
            if (case_names is None or case.name in case_names)
            and (categories is None or case.category in categories)
            and (difficulties is None or case.difficulty in difficulties)
        ]
        if not selected_cases:
            raise ValueError("No benchmark cases selected.")
        logger.info(f"benchmark suite: {manifest.suite_name}")
        logger.info(f"benchmark cases selected: {len(selected_cases)}")
        for target_name, use_llm, model in targets:
            logger.info(f"starting target: {target_name}")
            results = _run_target(
                target_name=target_name,
                model=model,
                use_llm=use_llm,
                manifest=manifest,
                cases=selected_cases,
                repeats=max(1, repeats),
                logger=logger,
                timestamp=timestamp,
            )
            all_results.extend(results)
            summary = _summarize_target(target_name, results)
            summaries.append(summary)
            logger.info(
                f"target summary {target_name}: success_rate={summary.success_rate:.3f} "
                f"top1_rate={summary.top1_rate:.3f} top3_rate={summary.top3_rate:.3f} "
                f"mean_total_ms={summary.mean_total_ms:.1f}"
            )
        report_path = report_dir / f"benchmark-report-{timestamp}.json"
        payload = {
            "suite_name": manifest.suite_name,
            "description": manifest.description,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "corpus_root": str(manifest.corpus_root),
            "summaries": [asdict(item) for item in summaries],
            "results": [asdict(item) for item in all_results],
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return manifest, all_results, summaries, report_path
    finally:
        logger.close()


def _run_target(
    *,
    target_name: str,
    model: str | None,
    use_llm: bool,
    manifest: BenchmarkManifest,
    cases: list[BenchmarkCase],
    repeats: int,
    logger: RunLogger,
    timestamp: str,
) -> list[CaseRunResult]:
    config = AppConfig(
        query="",
        root=manifest.corpus_root,
        model=model or "heuristic",
        ollama_request_timeout=12.0,
        no_llm=not use_llm,
        show_thinking=False,
        max_agent_steps=4,
        max_candidates=18,
        max_results=5,
        log_dir=logger.log_path.parent,
    )
    backend = SearchBackend(root=config.resolved_root, logger=logger, max_candidates=config.max_candidates)
    report = backend.dependency_report()
    if report.required_missing:
        raise RuntimeError(f"missing required commands: {', '.join(report.required_missing)}")
    root_overview = backend.inspect_root()
    client = resolve_search_client(config, logger, timestamp=f"{timestamp}-{target_name.replace(':', '_')}")
    if use_llm and client is None:
        raise RuntimeError(f"Requested model '{target_name}' is not available for benchmark execution.")

    results: list[CaseRunResult] = []
    for repeat_index in range(1, repeats + 1):
        logger.info(f"target={target_name} repeat={repeat_index}/{repeats}")
        for case in cases:
            config.query = case.query
            logger.info(f"target={target_name} case={case.name} start")
            case_start = time.perf_counter()

            search_start = time.perf_counter()
            commands_before = logger.command_count
            execution = execute_search(
                config,
                logger,
                backend=backend,
                client=client,
                root_overview=root_overview,
            )
            command_count = logger.command_count - commands_before
            search_ms = (time.perf_counter() - search_start) * 1000.0
            candidates = execution.candidates
            outcome = execution.outcome
            llm_agent_turn_count = sum(1 for step in execution.agent_steps if step.action.source == "ollama")
            planning_ms = 0.0
            search_ms = execution.agent_ms
            ranking_ms = execution.ranking_ms
            total_ms = (time.perf_counter() - case_start) * 1000.0

            matched_rank = None
            matched_path = None
            snippet_matched = case.expected_snippet is None
            acceptable_paths = {(manifest.corpus_root / path).resolve() for path in case.acceptable_paths}
            for index, candidate in enumerate(outcome.results[: case.top_k], start=1):
                if candidate.path not in acceptable_paths:
                    continue
                matched_rank = index
                matched_path = str(candidate.path.relative_to(manifest.corpus_root))
                if case.expected_snippet is not None:
                    snippet_matched = any(
                        case.expected_snippet.lower() in snippet.lower() for snippet in candidate.snippets
                    )
                break
            if not case.acceptable_paths:
                snippet_matched = True
                if not outcome.results:
                    matched_rank = 0
                    matched_path = None

            results.append(
                CaseRunResult(
                    target=target_name,
                    repeat_index=repeat_index,
                    case_name=case.name,
                    category=case.category,
                    difficulty=case.difficulty,
                    capability_tags=case.capability_tags,
                    query=case.query,
                    expected_path=case.expected_path,
                    expected_snippet=case.expected_snippet,
                    success=matched_rank is not None and snippet_matched,
                    matched_rank=matched_rank,
                    matched_path=matched_path,
                    snippet_matched=snippet_matched,
                    top_paths=[
                        str(candidate.path.relative_to(manifest.corpus_root)) for candidate in outcome.results[: case.top_k]
                    ],
                    planning_source="ollama" if llm_agent_turn_count else "heuristic",
                    ranking_source=outcome.ranking_source,
                    agent_step_count=len(execution.agent_steps),
                    llm_agent_turn_count=llm_agent_turn_count,
                    candidate_count=len(candidates),
                    command_count=command_count,
                    total_ms=round(total_ms, 3),
                    planning_ms=round(planning_ms, 3),
                    search_ms=round(search_ms, 3),
                    ranking_ms=round(ranking_ms, 3),
                )
            )
            logger.info(
                f"target={target_name} case={case.name} success={results[-1].success} "
                f"total_ms={results[-1].total_ms:.1f}"
            )
    return results


def _summarize_target(target_name: str, results: list[CaseRunResult]) -> TargetSummary:
    case_count = len(results)
    success_count = sum(1 for item in results if item.success)
    top1_count = sum(1 for item in results if item.matched_rank == 1 and item.success)
    top3_count = sum(
        1 for item in results if item.matched_rank is not None and item.matched_rank > 0 and item.matched_rank <= 3 and item.success
    )
    snippet_case_count = sum(1 for item in results if item.expected_snippet is not None)
    snippet_success_count = sum(
        1 for item in results if item.expected_snippet is not None and item.success and item.snippet_matched
    )
    no_answer_case_count = sum(1 for item in results if item.expected_path is None)
    no_answer_success_count = sum(1 for item in results if item.expected_path is None and item.success)
    mrr = sum(1.0 / item.matched_rank for item in results if item.matched_rank and item.matched_rank > 0) / case_count
    total_values = [item.total_ms for item in results]
    planning_values = [item.planning_ms for item in results]
    search_values = [item.search_ms for item in results]
    ranking_values = [item.ranking_ms for item in results]
    agent_step_values = [item.agent_step_count for item in results]
    llm_agent_turn_values = [item.llm_agent_turn_count for item in results]
    candidate_values = [item.candidate_count for item in results]
    command_values = [item.command_count for item in results]
    llm_agent_case_rate = sum(1 for item in results if item.llm_agent_turn_count > 0) / case_count
    llm_planner_rate = sum(1 for item in results if item.planning_source == "ollama") / case_count
    llm_ranker_rate = sum(1 for item in results if item.ranking_source == "ollama") / case_count
    return TargetSummary(
        target=target_name,
        repeat_count=max(item.repeat_index for item in results),
        case_count=case_count,
        success_count=success_count,
        top1_count=top1_count,
        top3_count=top3_count,
        snippet_case_count=snippet_case_count,
        snippet_success_count=snippet_success_count,
        no_answer_case_count=no_answer_case_count,
        no_answer_success_count=no_answer_success_count,
        mrr=round(mrr, 4),
        success_rate=round(success_count / case_count, 4),
        top1_rate=round(top1_count / case_count, 4),
        top3_rate=round(top3_count / case_count, 4),
        snippet_success_rate=round(snippet_success_count / snippet_case_count, 4) if snippet_case_count else None,
        no_answer_success_rate=round(no_answer_success_count / no_answer_case_count, 4) if no_answer_case_count else None,
        median_total_ms=round(median(total_values), 3),
        mean_total_ms=round(mean(total_values), 3),
        p95_total_ms=round(_percentile(total_values, 0.95), 3),
        median_planning_ms=round(median(planning_values), 3),
        median_search_ms=round(median(search_values), 3),
        median_ranking_ms=round(median(ranking_values), 3),
        median_agent_step_count=round(median(agent_step_values), 3),
        median_llm_agent_turn_count=round(median(llm_agent_turn_values), 3),
        median_candidate_count=round(median(candidate_values), 3),
        median_command_count=round(median(command_values), 3),
        llm_agent_case_rate=round(llm_agent_case_rate, 4),
        llm_planner_rate=round(llm_planner_rate, 4),
        llm_ranker_rate=round(llm_ranker_rate, 4),
    )


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the full QueryFind benchmark suite.")
    parser.add_argument(
        "--model",
        action="append",
        default=None,
        help="Ollama model to benchmark. May be repeated. Defaults to qwen3.5:27b unless heuristic-only is requested.",
    )
    parser.add_argument(
        "--heuristic-baseline",
        action="store_true",
        help="Include the heuristic baseline alongside any model runs.",
    )
    parser.add_argument("--case", action="append", default=[], help="Run only the named case. May be repeated.")
    parser.add_argument("--category", action="append", default=[], help="Run only cases in the named category.")
    parser.add_argument("--difficulty", action="append", default=[], help="Run only cases with the named difficulty.")
    parser.add_argument("--repeats", type=int, default=1, help="Repeat every case this many times.")
    parser.add_argument("--quiet", action="store_true", help="Reduce benchmark progress logging to stdout.")
    parser.add_argument("--list-cases", action="store_true", help="List available benchmark cases and exit.")
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="Directory for benchmark logs and JSON reports.",
    )
    args = parser.parse_args(argv)

    if args.list_cases:
        manifest = load_manifest()
        for case in manifest.cases:
            print(f"{case.name} [{case.category}/{case.difficulty}] {case.query}")
        return 0

    selected_models = list(args.model) if args.model is not None else None
    if selected_models is None and args.heuristic_baseline:
        selected_models = []

    manifest, results, summaries, report_path = run_benchmark(
        models=selected_models,
        include_heuristic=bool(args.heuristic_baseline),
        case_names=set(args.case) if args.case else None,
        categories=set(args.category) if args.category else None,
        difficulties=set(args.difficulty) if args.difficulty else None,
        repeats=max(1, args.repeats),
        report_dir=Path(args.report_dir).expanduser().resolve(),
        quiet=bool(args.quiet),
    )

    print(f"Benchmark suite: {manifest.suite_name}")
    print(f"Corpus root: {manifest.corpus_root}")
    for summary in summaries:
        print(f"\nTarget: {summary.target}")
        print(
            "  success: "
            f"{summary.success_count}/{summary.case_count} ({summary.success_rate:.1%})"
        )
        print(f"  top1: {summary.top1_count}/{summary.case_count} ({summary.top1_rate:.1%})")
        print(f"  mrr: {summary.mrr:.4f}")
        if summary.snippet_success_rate is not None:
            print(
                "  snippet success: "
                f"{summary.snippet_success_count}/{summary.snippet_case_count} "
                f"({summary.snippet_success_rate:.1%})"
            )
        print(
            "  median ms: "
            f"total={summary.median_total_ms:.1f} "
            f"agent={summary.median_search_ms:.1f} "
            f"rank={summary.median_ranking_ms:.1f}"
        )
        print(f"  p95 total ms: {summary.p95_total_ms:.1f}")
        print(
            "  medians: "
            f"agent_steps={summary.median_agent_step_count:.1f} "
            f"llm_turns={summary.median_llm_agent_turn_count:.1f} "
            f"candidates={summary.median_candidate_count:.1f} "
            f"commands={summary.median_command_count:.1f}"
        )
        print(
            "  llm usage: "
            f"agent_cases={summary.llm_agent_case_rate:.1%} "
            f"planner={summary.llm_planner_rate:.1%} "
            f"ranker={summary.llm_ranker_rate:.1%}"
        )
        if summary.no_answer_success_rate is not None:
            print(
                "  no-answer: "
                f"{summary.no_answer_success_count}/{summary.no_answer_case_count} "
                f"({summary.no_answer_success_rate:.1%})"
            )

        failures = [item for item in results if item.target == summary.target and not item.success]
        if failures:
            print("  failures:")
            for item in failures[:8]:
                print(f"    - {item.case_name}: top paths={', '.join(item.top_paths) or '(none)'}")
    print(f"\nJSON report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
