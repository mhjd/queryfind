from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path

from queryfind.app import resolve_search_client
from queryfind.config import AppConfig
from queryfind.logging_utils import RunLogger
from queryfind.planner import plan_search, rank_results
from queryfind.search_backend import SearchBackend


@dataclass(slots=True)
class EvalCase:
    name: str
    query: str
    expected_path: str
    expected_snippet: str | None = None
    top_k: int = 3


@dataclass(slots=True)
class EvalResult:
    case: EvalCase
    success: bool
    matched_rank: int | None
    top_paths: list[str]
    matched_snippet: str | None


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ROOT = REPO_ROOT / "synthetic_fs" / "basic"

MTIMES = {
    "README.md": "2024-01-01T00:00:00+00:00",
    "clients/maple/contracts/2024-11-02-maple-msa-draft.txt": "2024-11-02T10:00:00+00:00",
    "clients/maple/contracts/2025-02-14-maple-master-services-agreement-signed.txt": "2025-02-14T09:30:00+00:00",
    "clients/maple/contracts/2025-02-10-maple-security-addendum-signed.txt": "2025-02-10T09:00:00+00:00",
    "clients/maple/notes/account-summary.md": "2025-01-15T08:00:00+00:00",
    "operations/sites/lakeside-cabin/network-access.md": "2025-01-20T15:00:00+00:00",
    "operations/sites/lakeside-cabin/supply-closet.txt": "2025-01-18T12:00:00+00:00",
    "operations/logistics/incidents/shipment-8842-delay-postmortem.md": "2025-02-18T11:45:00+00:00",
    "operations/logistics/shipments/8842-status-log.txt": "2025-02-17T16:20:00+00:00",
    "projects/northstar/project-brief.md": "2025-02-12T13:10:00+00:00",
    "projects/northstar/status/2025-02-21-weekly-update.md": "2025-02-21T17:00:00+00:00",
    "hr/onboarding/analyst-onboarding-checklist.md": "2025-01-07T10:10:00+00:00",
    "people/team-directory.md": "2025-01-03T09:40:00+00:00",
    ".hidden/alias-notes.txt": "2025-02-05T07:25:00+00:00",
}

CASES = [
    EvalCase(
        name="latest_maple_contract",
        query="find the latest signed contract for client maple",
        expected_path="clients/maple/contracts/2025-02-14-maple-master-services-agreement-signed.txt",
        top_k=1,
    ),
    EvalCase(
        name="lakeside_wifi",
        query="find the file with the Wi-Fi password for the lakeside cabin",
        expected_path="operations/sites/lakeside-cabin/network-access.md",
        expected_snippet="lantern-ember-4821",
    ),
    EvalCase(
        name="shipment_delay_reason",
        query="find the document that explains why shipment 8842 was delayed",
        expected_path="operations/logistics/incidents/shipment-8842-delay-postmortem.md",
    ),
    EvalCase(
        name="northstar_codename",
        query="find the file that says Northstar is the codename for the warehouse migration",
        expected_path="projects/northstar/project-brief.md",
        expected_snippet="codename for the warehouse migration",
    ),
    EvalCase(
        name="analyst_onboarding",
        query="find the onboarding checklist for the new analyst",
        expected_path="hr/onboarding/analyst-onboarding-checklist.md",
    ),
    EvalCase(
        name="northstar_owner",
        query="find the file that names the owner of project northstar",
        expected_path="projects/northstar/project-brief.md",
        expected_snippet="Owner: Nina Solis",
    ),
]


def normalize_corpus_metadata(root: Path = SYNTHETIC_ROOT) -> None:
    for relative_path, iso_value in MTIMES.items():
        path = root / relative_path
        timestamp = datetime.fromisoformat(iso_value).astimezone(timezone.utc).timestamp()
        os.utime(path, (timestamp, timestamp))


def run_eval(*, use_llm: bool = False, case_names: set[str] | None = None) -> list[EvalResult]:
    normalize_corpus_metadata()
    log_root = REPO_ROOT / ".queryfind" / "logs"
    config = AppConfig(
        query="",
        root=SYNTHETIC_ROOT,
        no_llm=not use_llm,
        show_thinking=False,
        max_candidates=12,
        max_results=5,
        log_dir=log_root,
    )
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger = RunLogger(log_root / f"synthetic-eval-{timestamp}.log", echo=False)
    try:
        backend = SearchBackend(root=config.resolved_root, logger=logger, max_candidates=config.max_candidates)
        report = backend.dependency_report()
        if report.required_missing:
            raise RuntimeError(f"missing required commands: {', '.join(report.required_missing)}")
        root_overview = backend.inspect_root()
        client = resolve_search_client(config, logger, timestamp=timestamp)

        selected_cases = [case for case in CASES if case_names is None or case.name in case_names]
        results: list[EvalResult] = []
        for case in selected_cases:
            config.query = case.query
            intent = plan_search(
                case.query,
                root_overview=root_overview,
                config=config,
                logger=logger,
                client=client,
            )
            candidates = backend.search(intent)
            outcome = rank_results(
                case.query,
                candidates=candidates,
                config=config,
                logger=logger,
                client=client,
            )
            matched_rank = None
            matched_snippet = None
            target = (SYNTHETIC_ROOT / case.expected_path).resolve()
            for index, candidate in enumerate(outcome.results[: case.top_k], start=1):
                if candidate.path == target:
                    matched_rank = index
                    if case.expected_snippet:
                        for snippet in candidate.snippets:
                            if case.expected_snippet.lower() in snippet.lower():
                                matched_snippet = snippet
                                break
                    break
            success = matched_rank is not None and (
                case.expected_snippet is None or matched_snippet is not None
            )
            results.append(
                EvalResult(
                    case=case,
                    success=success,
                    matched_rank=matched_rank,
                    top_paths=[str(candidate.path.relative_to(SYNTHETIC_ROOT)) for candidate in outcome.results[: case.top_k]],
                    matched_snippet=matched_snippet,
                )
            )
        return results
    finally:
        logger.close()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run QueryFind against a synthetic local filesystem.")
    parser.add_argument("--use-llm", action="store_true", help="Use the configured Ollama model instead of heuristics.")
    parser.add_argument("--case", action="append", default=[], help="Run only the named case. May be repeated.")
    args = parser.parse_args(argv)

    names = set(args.case) if args.case else None
    results = run_eval(use_llm=bool(args.use_llm), case_names=names)
    failures = 0
    print(f"Synthetic root: {SYNTHETIC_ROOT}")
    for result in results:
        status = "PASS" if result.success else "FAIL"
        print(f"[{status}] {result.case.name}")
        print(f"  query: {result.case.query}")
        print(f"  expected: {result.case.expected_path}")
        print(f"  top paths: {', '.join(result.top_paths) or '(none)'}")
        if result.matched_rank is not None:
            print(f"  matched rank: {result.matched_rank}")
        if result.matched_snippet:
            print(f"  snippet: {result.matched_snippet}")
        if not result.success:
            failures += 1
    print(f"Summary: {len(results) - failures}/{len(results)} cases passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
