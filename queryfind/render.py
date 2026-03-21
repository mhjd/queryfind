from __future__ import annotations

from queryfind.models import SearchIntent, SearchOutcome
from queryfind.search_backend import format_candidate_metadata

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:  # pragma: no cover
    Console = None
    Panel = None
    Table = None


def render_intent(intent: SearchIntent) -> None:
    if Console and Table:
        console = Console()
        table = Table(title="Search Plan", show_lines=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        table.add_row("Planner", intent.planning_source)
        table.add_row("Path terms", ", ".join(intent.path_terms) or "-")
        table.add_row("Content terms", ", ".join(intent.content_terms) or "-")
        table.add_row("Extensions", ", ".join(intent.extensions) or "-")
        table.add_row("Sort", intent.sort_hint)
        table.add_row("Notes", "; ".join(intent.notes) or "-")
        console.print(table)
        return
    print("Search Plan")
    print(f"  planner: {intent.planning_source}")
    print(f"  path terms: {', '.join(intent.path_terms) or '-'}")
    print(f"  content terms: {', '.join(intent.content_terms) or '-'}")
    print(f"  extensions: {', '.join(intent.extensions) or '-'}")
    print(f"  sort: {intent.sort_hint}")


def render_outcome(outcome: SearchOutcome) -> None:
    if Console and Table and Panel:
        console = Console()
        console.print(Panel(outcome.summary, title=f"Results via {outcome.ranking_source}"))
        table = Table(show_lines=True)
        table.add_column("#", width=3)
        table.add_column("Path", overflow="fold")
        table.add_column("Why", overflow="fold")
        table.add_column("Evidence", overflow="fold")
        for index, candidate in enumerate(outcome.results, start=1):
            reasons = "\n".join(candidate.reasons[:3]) or "-"
            evidence_parts = []
            metadata = format_candidate_metadata(candidate)
            if metadata:
                evidence_parts.append(metadata)
            evidence_parts.extend(candidate.snippets[:2])
            table.add_row(str(index), str(candidate.path), reasons, "\n".join(evidence_parts) or "-")
        console.print(table)
        return
    print(outcome.summary)
    for index, candidate in enumerate(outcome.results, start=1):
        print(f"{index}. {candidate.path}")
        for reason in candidate.reasons[:3]:
            print(f"   why: {reason}")
        metadata = format_candidate_metadata(candidate)
        if metadata:
            print(f"   meta: {metadata}")
        for snippet in candidate.snippets[:2]:
            print(f"   snippet: {snippet}")
