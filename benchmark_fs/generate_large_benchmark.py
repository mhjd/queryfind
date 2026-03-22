from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import shutil
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "mega"
MANIFEST_PATH = ROOT / "mega_manifest.json"


@dataclass(frozen=True, slots=True)
class ClientRecord:
    slug: str
    name: str
    msa_signed: str
    security_signed: str
    scope: str
    security_snippet: str


@dataclass(frozen=True, slots=True)
class SiteRecord:
    slug: str
    name: str
    wifi_password: str
    scanner_hold_seconds: int
    guest_ssid: str


@dataclass(frozen=True, slots=True)
class ShipmentRecord:
    shipment_id: int
    delay_reason: str
    status_phrase: str


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    slug: str
    name: str
    owner: str
    scope: str
    blocker: str
    update_latest: str
    update_previous: str


@dataclass(frozen=True, slots=True)
class VendorRecord:
    slug: str
    name: str
    contact: str
    specialty: str
    invoice_item: str


@dataclass(frozen=True, slots=True)
class ScorecardRecord:
    slug: str
    role: str
    recommendation: str
    candidate: str


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _write_file(relative_path: str, content: str, mtime: datetime, mtimes: dict[str, str]) -> None:
    path = CORPUS_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    mtimes[relative_path] = mtime.isoformat()


def _add_case(
    cases: list[dict[str, object]],
    *,
    name: str,
    category: str,
    difficulty: str,
    capability_tags: list[str],
    query: str,
    expected_path: str | None,
    expected_snippet: str | None = None,
    top_k: int = 3,
) -> None:
    payload: dict[str, object] = {
        "name": name,
        "category": category,
        "difficulty": difficulty,
        "capability_tags": capability_tags,
        "query": query,
        "expected_path": expected_path,
        "acceptable_paths": [] if expected_path is None else [expected_path],
        "top_k": top_k,
    }
    if expected_snippet is not None:
        payload["expected_snippet"] = expected_snippet
    cases.append(payload)


def main() -> None:
    if CORPUS_ROOT.exists():
        shutil.rmtree(CORPUS_ROOT)
    CORPUS_ROOT.mkdir(parents=True)

    mtimes: dict[str, str] = {}
    cases: list[dict[str, object]] = []

    base = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)

    clients = [
        ClientRecord("redwood", "Redwood Industrial", "2025-03-11", "2025-03-07", "dock labeling modernization", "retains 180 days of telemetry logs"),
        ClientRecord("orchid", "Orchid Labs", "2025-02-01", "2025-01-28", "laboratory cold-chain onboarding", "rotates shared access tokens every 30 days"),
        ClientRecord("ember", "Ember Freight", "2025-03-05", "2025-03-01", "cross-dock intake cleanup", "stores badge audit events for 365 days"),
        ClientRecord("northwind", "Northwind Foods", "2025-02-19", "2025-02-15", "frozen overflow routing", "exports access logs to the customer vault weekly"),
        ClientRecord("kestrel", "Kestrel Retail", "2025-03-09", "2025-03-04", "returns consolidation program", "disables inactive vendor accounts after 14 days"),
        ClientRecord("sablecrest", "Sablecrest Health", "2025-02-25", "2025-02-22", "clinical sample lane rollout", "encrypts handheld backups before upload"),
        ClientRecord("blueharbor", "BlueHarbor Marine", "2025-03-12", "2025-03-10", "reef cargo intake tracking", "limits guest network credentials to 24 hours"),
        ClientRecord("willow", "Willow Foods", "2025-02-27", "2025-02-24", "temperature exception triage", "keeps freezer alarm history for 400 days"),
    ]

    sites = [
        SiteRecord("cinder-harbor", "Cinder Harbor", "oak-tide-4117", 12, "HarborMesh-Guest"),
        SiteRecord("delta-yard", "Delta Yard", "delta-knot-7721", 10, "DeltaMesh-Guest"),
        SiteRecord("marlin-port", "Marlin Port", "marlin-sail-2284", 14, "MarlinPort-Guest"),
        SiteRecord("north-quay", "North Quay", "quay-fog-9311", 11, "NorthQuay-Guest"),
        SiteRecord("raven-terminal", "Raven Terminal", "raven-shift-6612", 9, "RavenTerm-Guest"),
        SiteRecord("sunset-depot", "Sunset Depot", "sunset-lane-4920", 13, "SunsetDepot-Guest"),
        SiteRecord("granite-wharf", "Granite Wharf", "granite-wake-5814", 15, "GraniteWharf-Guest"),
        SiteRecord("orchard-dock", "Orchard Dock", "orchard-wave-7425", 8, "OrchardDock-Guest"),
    ]

    shipments = [
        ShipmentRecord(7718, "customs inspection on reefer seal", "pending customs inspection"),
        ShipmentRecord(7724, "carrier missed the bonded window", "awaiting bonded trailer swap"),
        ShipmentRecord(7731, "temperature variance review", "held for temperature variance review"),
        ShipmentRecord(8842, "reef unit battery failed during transfer", "awaiting reefer battery replacement"),
        ShipmentRecord(8850, "staging lane congestion", "queued in overflow staging lane"),
        ShipmentRecord(8861, "manifest mismatch with supplier labels", "waiting on corrected supplier manifest"),
        ShipmentRecord(8873, "gate appointment was rescheduled", "assigned to revised gate appointment"),
        ShipmentRecord(8890, "export paperwork missing pallet counts", "blocked on pallet count correction"),
    ]

    projects = [
        ProjectRecord("atlas", "Atlas", "Mara Chen", "dock label printer refresh", "dock label printer calibration", "2025-03-14", "2025-03-07"),
        ProjectRecord("lantern", "Lantern", "Priya Solanki", "warehouse migration playbook", "rollback checkpoint signoff", "2025-03-13", "2025-03-06"),
        ProjectRecord("frostline", "Frostline", "Jonas Reed", "freezer sensor rollout", "cold aisle repeater placement", "2025-03-12", "2025-03-05"),
        ProjectRecord("northstar", "Northstar", "Elena Park", "yard dispatch dashboard", "dispatch screen latency in yard office", "2025-03-11", "2025-03-04"),
        ProjectRecord("keel", "Keel", "Owen Hart", "slotting optimization for inbound pallets", "slotting map export is stale", "2025-03-10", "2025-03-03"),
        ProjectRecord("tidewatch", "Tidewatch", "Lina Gomez", "dock camera retention refresh", "camera retention policy approval", "2025-03-09", "2025-03-02"),
        ProjectRecord("embergrid", "EmberGrid", "Noah Bishop", "cross-site exception routing", "handoff queue backpressure", "2025-03-08", "2025-03-01"),
        ProjectRecord("quartz", "Quartz", "Tessa Nwosu", "accounts receivable exception review", "duplicate invoice match tuning", "2025-03-15", "2025-03-08"),
    ]

    vendors = [
        VendorRecord("meridian", "Meridian Cold Storage", "Elena Park", "refrigerated overflow", "outbound pallet transfer"),
        VendorRecord("northcoast", "NorthCoast Logistics", "Jules Duran", "after-hours shuttle recovery", "weekend lane recovery"),
        VendorRecord("bluepeak", "BluePeak Controls", "Dev Patel", "dock scanner spare kits", "firmware refresh labor"),
        VendorRecord("ironline", "Ironline Freight", "Lina Gomez", "linehaul trailer swaps", "expedited trailer reposition"),
        VendorRecord("summit", "Summit Packaging", "Mara Chen", "thermal label stock", "industrial ribbon replenishment"),
        VendorRecord("coldtrail", "ColdTrail Services", "Priya Solanki", "reef maintenance dispatch", "compressor field inspection"),
    ]

    scorecards = [
        ScorecardRecord("data-platform-analyst", "data platform analyst", "Recommend hire: Imani Holt", "Imani Holt"),
        ScorecardRecord("analytics-engineer", "analytics engineer", "Recommend hire: no", "Sofia Lane"),
        ScorecardRecord("warehouse-supervisor", "warehouse supervisor", "Recommend hire: Mateo Ruiz", "Mateo Ruiz"),
        ScorecardRecord("fleet-analyst", "fleet analyst", "Recommend hire: Simone Vega", "Simone Vega"),
        ScorecardRecord("site-reliability-manager", "site reliability manager", "Recommend hire: Devika Shah", "Devika Shah"),
        ScorecardRecord("operations-program-manager", "operations program manager", "Recommend hire: Graham Lee", "Graham Lee"),
        ScorecardRecord("security-analyst", "security analyst", "Recommend hire: Amara Cole", "Amara Cole"),
        ScorecardRecord("inventory-planner", "inventory planner", "Recommend hire: Keenan Fox", "Keenan Fox"),
    ]

    team_directory = {
        "Jules Duran": "logistics coordinator",
        "Dev Patel": "director of operations systems",
        "Mara Chen": "program director",
        "Elena Park": "vendor operations lead",
        "Priya Solanki": "migration lead",
        "Lina Gomez": "platform delivery manager",
    }

    _write_file(
        "README.md",
        """
        # QueryFind Mega Benchmark

        This synthetic corpus is larger than the default suites and is intended to compare model quality across a broader set of retrieval and reasoning tasks.
        """,
        base,
        mtimes,
    )

    # Clients corpus and cases.
    for index, client in enumerate(clients):
        offset = timedelta(days=index * 3)
        _write_file(
            f"clients/{client.slug}/contracts/2024-08-{10 + index:02d}-{client.slug}-msa-draft.txt",
            f"""
            Client: {client.name}
            Document: Master Services Agreement
            Status: draft
            Scope: legacy draft for {client.scope}.
            """,
            base + offset,
            mtimes,
        )
        signed_msa_path = f"clients/{client.slug}/contracts/{client.msa_signed}-{client.slug}-master-services-agreement-signed.txt"
        _write_file(
            signed_msa_path,
            f"""
            Client: {client.name}
            Document: Master Services Agreement
            Status: signed
            Signed date: {client.msa_signed}
            Scope: {client.scope}
            """,
            datetime.fromisoformat(f"{client.msa_signed}T14:00:00+00:00"),
            mtimes,
        )
        security_path = f"clients/{client.slug}/contracts/{client.security_signed}-{client.slug}-security-addendum-signed.txt"
        _write_file(
            security_path,
            f"""
            Client: {client.name}
            Document: Security Addendum
            Status: signed
            Signed date: {client.security_signed}
            Control note: {client.security_snippet}.
            """,
            datetime.fromisoformat(f"{client.security_signed}T11:00:00+00:00"),
            mtimes,
        )
        _write_file(
            f"clients/{client.slug}/notes/account-brief.md",
            f"""
            Account: {client.name}
            Active program: {client.scope}
            Contract trail: use the latest signed MSA and signed security addendum in this folder.
            """,
            base + offset + timedelta(days=1),
            mtimes,
        )
        _add_case(
            cases,
            name=f"latest_{client.slug}_contract",
            category="contracts",
            difficulty="easy",
            capability_tags=["path", "content", "mtime"],
            query=f"find the latest signed contract for {client.name}",
            expected_path=signed_msa_path,
            top_k=1,
        )
        _add_case(
            cases,
            name=f"{client.slug}_security_addendum",
            category="contracts",
            difficulty="easy",
            capability_tags=["path", "content", "snippet"],
            query=f"find the signed security addendum for {client.name}",
            expected_path=security_path,
            expected_snippet=client.security_snippet,
            top_k=1,
        )

    # Site corpus and cases.
    for index, site in enumerate(sites):
        when = base + timedelta(days=40 + index)
        network_path = f"operations/sites/{site.slug}/network-runbook.md"
        scanner_path = f"operations/sites/{site.slug}/dock-3-scanner-maintenance.md"
        _write_file(
            network_path,
            f"""
            Site: {site.name}
            Guest SSID: {site.guest_ssid}
            Wi-Fi password: {site.wifi_password}
            Use this runbook for badge readers and dock handheld onboarding.
            """,
            when,
            mtimes,
        )
        _write_file(
            scanner_path,
            f"""
            Site: {site.name}
            Device: Dock 3 scanner firmware
            Reset procedure: Hold the side button for {site.scanner_hold_seconds} seconds, then tap the trigger twice.
            """,
            when + timedelta(hours=2),
            mtimes,
        )
        _write_file(
            f"operations/sites/{site.slug}/device-inventory.md",
            f"""
            Site: {site.name}
            Assets:
            - Dock 3 scanner
            - Badge encoder
            - Yard tablet
            """,
            when + timedelta(hours=4),
            mtimes,
        )
        _add_case(
            cases,
            name=f"{site.slug}_wifi_password",
            category="operations",
            difficulty="easy",
            capability_tags=["content", "snippet"],
            query=f"find the file with the Wi-Fi password for {site.name}",
            expected_path=network_path,
            expected_snippet=site.wifi_password,
        )
        _add_case(
            cases,
            name=f"{site.slug}_scanner_reset",
            category="operations",
            difficulty="medium",
            capability_tags=["content", "snippet", "disambiguation"],
            query=f"find the procedure for resetting the dock 3 scanner firmware at {site.name}",
            expected_path=scanner_path,
            expected_snippet=f"Hold the side button for {site.scanner_hold_seconds} seconds",
        )

    # Shipments corpus and cases.
    for index, shipment in enumerate(shipments):
        when = base + timedelta(days=70 + index)
        incident_path = f"operations/logistics/incidents/shipment-{shipment.shipment_id}-root-cause.md"
        status_path = f"operations/logistics/shipments/{shipment.shipment_id}-status-log.txt"
        _write_file(
            incident_path,
            f"""
            Shipment: {shipment.shipment_id}
            Root cause: {shipment.delay_reason}
            Resolution owner: exception desk
            """,
            when + timedelta(hours=1),
            mtimes,
        )
        _write_file(
            status_path,
            f"""
            Shipment: {shipment.shipment_id}
            Current status: {shipment.status_phrase}
            Last note: escalation remains open.
            """,
            when,
            mtimes,
        )
        _add_case(
            cases,
            name=f"shipment_{shipment.shipment_id}_delay_reason",
            category="operations",
            difficulty="medium",
            capability_tags=["content", "disambiguation"],
            query=f"find the document that explains why shipment {shipment.shipment_id} was delayed",
            expected_path=incident_path,
            expected_snippet=shipment.delay_reason,
        )
        _add_case(
            cases,
            name=f"shipment_{shipment.shipment_id}_status_log",
            category="operations",
            difficulty="medium",
            capability_tags=["content", "snippet", "disambiguation"],
            query=f"find the shipment log showing {shipment.shipment_id} {shipment.status_phrase}",
            expected_path=status_path,
            expected_snippet=shipment.status_phrase,
        )

    # Projects corpus and cases.
    for index, project in enumerate(projects):
        when = base + timedelta(days=110 + index)
        brief_path = f"projects/{project.slug}/project-brief.md"
        latest_path = f"projects/{project.slug}/status/{project.update_latest}-weekly-update.md"
        previous_path = f"projects/{project.slug}/status/{project.update_previous}-weekly-update.md"
        _write_file(
            brief_path,
            f"""
            Project: {project.name}
            Owner: {project.owner}
            Scope: {project.scope}
            """,
            when,
            mtimes,
        )
        _write_file(
            latest_path,
            f"""
            Project: {project.name}
            Week ending: {project.update_latest}
            Primary blocker: {project.blocker}
            """,
            when + timedelta(days=1),
            mtimes,
        )
        _write_file(
            previous_path,
            f"""
            Project: {project.name}
            Week ending: {project.update_previous}
            Highlight: execution remains on plan.
            """,
            when,
            mtimes,
        )
        _write_file(
            f"projects/{project.slug}/notes/rollback-plan.md",
            f"""
            Project: {project.name}
            Rollback owner: {project.owner}
            Rollback checkpoints stay aligned with {project.scope}.
            """,
            when + timedelta(hours=6),
            mtimes,
        )
        _add_case(
            cases,
            name=f"{project.slug}_owner",
            category="projects",
            difficulty="easy",
            capability_tags=["content", "snippet"],
            query=f"find the file that names the owner of project {project.name}",
            expected_path=brief_path,
            expected_snippet=f"Owner: {project.owner}",
        )
        _add_case(
            cases,
            name=f"{project.slug}_latest_update",
            category="projects",
            difficulty="easy",
            capability_tags=["path", "mtime"],
            query=f"find the latest weekly update for {project.name}",
            expected_path=latest_path,
            top_k=1,
        )
        _add_case(
            cases,
            name=f"{project.slug}_blocker",
            category="projects",
            difficulty="medium",
            capability_tags=["content", "snippet"],
            query=f"find the file describing the blocker for project {project.name}",
            expected_path=latest_path,
            expected_snippet=project.blocker,
        )

    # Vendor corpus and cases.
    for index, vendor in enumerate(vendors):
        when = base + timedelta(days=160 + index)
        profile_path = f"finance/vendors/{vendor.slug}/profile.md"
        invoice_path = f"finance/vendors/{vendor.slug}/invoices/2025-02-invoice.txt"
        _write_file(
            profile_path,
            f"""
            Vendor: {vendor.name}
            Primary contact: {vendor.contact}
            Specialty: {vendor.specialty}
            """,
            when,
            mtimes,
        )
        _write_file(
            invoice_path,
            f"""
            Vendor: {vendor.name}
            Invoice month: 2025-02
            Line item: {vendor.invoice_item}
            """,
            when + timedelta(hours=1),
            mtimes,
        )
        _add_case(
            cases,
            name=f"{vendor.slug}_primary_contact",
            category="finance",
            difficulty="easy",
            capability_tags=["content", "snippet"],
            query=f"find the vendor profile that lists {vendor.contact} as the primary contact",
            expected_path=profile_path,
            expected_snippet=f"Primary contact: {vendor.contact}",
        )
        _add_case(
            cases,
            name=f"{vendor.slug}_invoice_line_item",
            category="finance",
            difficulty="medium",
            capability_tags=["content", "snippet"],
            query=f"find the invoice mentioning {vendor.invoice_item}",
            expected_path=invoice_path,
            expected_snippet=vendor.invoice_item,
        )

    # HR scorecards and cases.
    for index, scorecard in enumerate(scorecards):
        when = base + timedelta(days=190 + index)
        scorecard_path = f"hr/hiring/{scorecard.slug}-scorecard.md"
        _write_file(
            scorecard_path,
            f"""
            Role: {scorecard.role}
            Candidate: {scorecard.candidate}
            {scorecard.recommendation}
            """,
            when,
            mtimes,
        )
        _add_case(
            cases,
            name=f"{scorecard.slug}_recommendation",
            category="hr",
            difficulty="medium",
            capability_tags=["content", "snippet", "disambiguation"],
            query=f"find the scorecard for the {scorecard.role} role",
            expected_path=scorecard_path,
            expected_snippet=scorecard.recommendation,
        )

    # People and alias corpus.
    _write_file(
        "people/team-directory.md",
        "\n".join(["Team directory:"] + [f"{name}: {role}" for name, role in team_directory.items()]),
        base + timedelta(days=230),
        mtimes,
    )
    _write_file(
        "people/oncall-rotations.md",
        """
        Operations systems on-call rotation:
        - Mara Chen
        - Dev Patel
        - Lina Gomez
        """,
        base + timedelta(days=231),
        mtimes,
    )
    for name in ["Jules Duran", "Dev Patel", "Mara Chen", "Elena Park"]:
        _add_case(
            cases,
            name=f"{_slugify(name)}_role",
            category="people",
            difficulty="easy",
            capability_tags=["content", "snippet"],
            query=f"find the directory file that lists {name}'s role",
            expected_path="people/team-directory.md",
            expected_snippet=f"{name}: {team_directory[name]}",
        )

    _write_file(
        ".hidden/site-aliases.txt",
        """
        Harbor 7 = Cinder Harbor
        Yard 4 = Delta Yard
        """,
        base + timedelta(days=232),
        mtimes,
    )
    _write_file(
        ".hidden/project-aliases.txt",
        """
        Beacon program = Atlas
        Cold aisle program = Frostline
        """,
        base + timedelta(days=233),
        mtimes,
    )
    _add_case(
        cases,
        name="harbor7_wifi_password",
        category="aliases",
        difficulty="hard",
        capability_tags=["hidden", "multi_file", "snippet"],
        query="find the file with the Wi-Fi password for Harbor 7",
        expected_path="operations/sites/cinder-harbor/network-runbook.md",
        expected_snippet="oak-tide-4117",
    )
    _add_case(
        cases,
        name="beacon_program_owner",
        category="aliases",
        difficulty="hard",
        capability_tags=["hidden", "multi_file", "snippet"],
        query="find the file that names the owner of the Beacon program",
        expected_path="projects/atlas/project-brief.md",
        expected_snippet="Owner: Mara Chen",
    )

    # Negative cases.
    _add_case(
        cases,
        name="no_mistral_contract",
        category="negative",
        difficulty="medium",
        capability_tags=["no_answer"],
        query="find the signed contract for Mistral Bio",
        expected_path=None,
        top_k=1,
    )
    _add_case(
        cases,
        name="no_april_bonus_sheet",
        category="negative",
        difficulty="medium",
        capability_tags=["no_answer"],
        query="find the spreadsheet with April bonus payouts",
        expected_path=None,
        top_k=1,
    )

    payload = {
        "suite_name": "queryfind_mega_v1",
        "description": "A 100-case large local benchmark for model comparison across path search, content retrieval, disambiguation, aliases, and no-answer behavior.",
        "corpus_root": "mega",
        "mtimes": dict(sorted(mtimes.items())),
        "cases": cases,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"generated {len(cases)} cases in {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
