from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "handmade100"
MANIFEST_PATH = ROOT / "handmade100_manifest.json"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _write_file(path: str, content: str, mtime: datetime, mtimes: dict[str, str]) -> None:
    target = CORPUS_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + "\n", encoding="utf-8")
    mtimes[path] = mtime.isoformat()


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

    _write_file(
        "README.md",
        """
        # Handmade 100-Case Benchmark

        This corpus is a hand-curated benchmark for QueryFind. It favors realistic filesystem structure, indirect clues, aliases, and cross-file reasoning over simple keyword lookup.
        """,
        _dt("2025-01-01T09:00:00+00:00"),
        mtimes,
    )

    customers = [
        {
            "slug": "blueharbor",
            "name": "BlueHarbor Marine",
            "nickname": "bay aquarium account",
            "pilot": "reef-tag scanner pilot at Pier West",
            "owner": "Nadia Brooks",
            "scope": "cold-chain check-in for reef specimen freight",
            "msa_date": "2025-03-12",
            "security_date": "2025-03-10",
            "security_clause": "Guest credentials expire after 24 hours.",
            "queries": [
                (
                    "blueharbor_signed_msa",
                    "find the signed MSA for the bay aquarium account",
                    "records/signed/blueharbor-2025-03-12-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "blueharbor_security_schedule",
                    "find the executed security schedule that limits guest credentials to one day",
                    "records/risk/blueharbor-2025-03-10-schedule.txt",
                    "Guest credentials expire after 24 hours.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "blueharbor_account_brief",
                    "find the account note about the reef-tag scanner pilot at Pier West",
                    "workspace/client-briefs/blueharbor-q1.md",
                    "reef-tag scanner pilot at Pier West",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
        {
            "slug": "faraday",
            "name": "Faraday Recycling",
            "nickname": "battery recycler account",
            "pilot": "hazmat battery cage relocation at Switchback",
            "owner": "Owen Hart",
            "scope": "battery containment workflow for late inbound returns",
            "msa_date": "2025-02-27",
            "security_date": "2025-02-24",
            "security_clause": "Courier chain-of-custody photos stay available for 90 days.",
            "queries": [
                (
                    "faraday_signed_msa",
                    "find the signed agreement for the battery recycler account",
                    "records/signed/faraday-2025-02-27-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "faraday_security_schedule",
                    "find the security attachment that keeps courier chain-of-custody photos for ninety days",
                    "records/risk/faraday-2025-02-24-schedule.txt",
                    "Courier chain-of-custody photos stay available for 90 days.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "faraday_account_brief",
                    "find the account brief about the hazmat battery cage relocation at Switchback",
                    "workspace/client-briefs/faraday-q1.md",
                    "hazmat battery cage relocation at Switchback",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
        {
            "slug": "summitfoods",
            "name": "Summit Fresh Foods",
            "nickname": "midwest produce consolidator",
            "pilot": "overnight produce swing at Yard 4",
            "owner": "Camille Price",
            "scope": "overnight produce cross-dock consolidation",
            "msa_date": "2025-03-06",
            "security_date": "2025-03-02",
            "security_clause": "Visitor badges must be surrendered before shift close.",
            "queries": [
                (
                    "summitfoods_signed_msa",
                    "find the signed MSA for the midwest produce consolidator",
                    "records/signed/summitfoods-2025-03-06-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "summitfoods_security_schedule",
                    "find the security schedule that says visitor badges have to be surrendered before shift close",
                    "records/risk/summitfoods-2025-03-02-schedule.txt",
                    "Visitor badges must be surrendered before shift close.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "summitfoods_account_brief",
                    "find the account brief for the overnight produce swing at Yard 4",
                    "workspace/client-briefs/summitfoods-q1.md",
                    "overnight produce swing at Yard 4",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
        {
            "slug": "verdant",
            "name": "Verdant Sensors",
            "nickname": "greenhouse sensor client",
            "pilot": "humidity logger rollout in cold aisle B",
            "owner": "Mika Donnelly",
            "scope": "humidity telemetry validation for greenhouse produce",
            "msa_date": "2025-02-21",
            "security_date": "2025-02-18",
            "security_clause": "USB export on handhelds stays disabled by default.",
            "queries": [
                (
                    "verdant_signed_msa",
                    "find the signed contract for the greenhouse sensor client",
                    "records/signed/verdant-2025-02-21-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "verdant_security_schedule",
                    "find the executed security schedule that keeps handheld USB export turned off by default",
                    "records/risk/verdant-2025-02-18-schedule.txt",
                    "USB export on handhelds stays disabled by default.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "verdant_account_brief",
                    "find the account brief for the humidity logger rollout in cold aisle B",
                    "workspace/client-briefs/verdant-q1.md",
                    "humidity logger rollout in cold aisle B",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
        {
            "slug": "orchid",
            "name": "Orchid Labs",
            "nickname": "lab freezer account",
            "pilot": "sample freezer rack relabeling on the mezzanine",
            "owner": "Jonah Pike",
            "scope": "sample freezer rack relabeling and audit cleanup",
            "msa_date": "2025-02-11",
            "security_date": "2025-02-08",
            "security_clause": "Shared handheld PINs rotate every 30 days.",
            "queries": [
                (
                    "orchid_signed_msa",
                    "find the signed agreement for the lab freezer account",
                    "records/signed/orchid-2025-02-11-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "orchid_security_schedule",
                    "find the executed security schedule that rotates shared handheld PINs every thirty days",
                    "records/risk/orchid-2025-02-08-schedule.txt",
                    "Shared handheld PINs rotate every 30 days.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "orchid_account_brief",
                    "find the account note about sample freezer rack relabeling on the mezzanine",
                    "workspace/client-briefs/orchid-q1.md",
                    "sample freezer rack relabeling on the mezzanine",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
        {
            "slug": "redwood",
            "name": "Redwood Industrial",
            "nickname": "dock label modernization client",
            "pilot": "dock label modernization at North Quay",
            "owner": "Mara Chen",
            "scope": "dock label printer modernization and compliance traceability",
            "msa_date": "2025-03-11",
            "security_date": "2025-03-07",
            "security_clause": "Telemetry history is retained for 180 days.",
            "queries": [
                (
                    "redwood_signed_msa",
                    "find the signed MSA for the dock label modernization client",
                    "records/signed/redwood-2025-03-11-msa.txt",
                    None,
                    ["hidden", "multi_file", "contracts", "path"],
                ),
                (
                    "redwood_security_schedule",
                    "find the security schedule that keeps telemetry history for one hundred eighty days",
                    "records/risk/redwood-2025-03-07-schedule.txt",
                    "Telemetry history is retained for 180 days.",
                    ["content", "snippet", "contracts"],
                ),
                (
                    "redwood_account_brief",
                    "find the account brief for dock label modernization at North Quay",
                    "workspace/client-briefs/redwood-q1.md",
                    "dock label modernization at North Quay",
                    ["content", "snippet", "multi_file"],
                ),
            ],
        },
    ]

    for index, customer in enumerate(customers):
        _write_file(
            f"workspace/client-briefs/{customer['slug']}-q1.md",
            f"""
            Account: {customer['name']}
            Internal nickname: {customer['nickname']}
            Account lead: {customer['owner']}
            Current pilot: {customer['pilot']}
            Scope summary: {customer['scope']}
            """,
            _dt(f"2025-02-{10 + index:02d}T09:30:00+00:00"),
            mtimes,
        )
        _write_file(
            f"records/signed/{customer['slug']}-{customer['msa_date']}-msa.txt",
            f"""
            Client: {customer['name']}
            Document: Master Services Agreement
            Status: signed
            Signed date: {customer['msa_date']}
            Scope: {customer['scope']}
            """,
            _dt(f"{customer['msa_date']}T16:00:00+00:00"),
            mtimes,
        )
        _write_file(
            f"records/risk/{customer['slug']}-{customer['security_date']}-schedule.txt",
            f"""
            Client: {customer['name']}
            Document: Security Schedule
            Status: executed
            Signed date: {customer['security_date']}
            Control note: {customer['security_clause']}
            """,
            _dt(f"{customer['security_date']}T13:00:00+00:00"),
            mtimes,
        )
        for case_name, query, expected_path, snippet, tags in customer["queries"]:
            _add_case(
                cases,
                name=case_name,
                category="contracts",
                difficulty="medium",
                capability_tags=tags,
                query=query,
                expected_path=expected_path,
                expected_snippet=snippet,
                top_k=1 if "path" in tags else 3,
            )

    sites = [
        {
            "slug": "harbor-7",
            "name": "Harbor 7",
            "alias": "Pier West",
            "ssid": "HarborMesh-Guest",
            "wifi": "oak-tide-4117",
            "reset": "Hold the side button for 12 seconds",
            "inventory": "Zebra cradle kit",
            "queries": [
                ("harbor7_wifi", "find the file with the Wi-Fi password for Pier West", "ops/site-books/harbor-7-network.md", "oak-tide-4117"),
                ("harbor7_scanner", "find the reset procedure for the dock 3 scanner at Pier West", "ops/device-playbooks/harbor-7-dock-3.md", "Hold the side button for 12 seconds"),
                ("harbor7_inventory", "find the file listing the Zebra cradle kit at Pier West", "ops/spares/harbor-7-inventory.md", "Zebra cradle kit"),
            ],
        },
        {
            "slug": "north-quay",
            "name": "North Quay",
            "alias": "Yard 4",
            "ssid": "NorthQuay-Guest",
            "wifi": "quay-fog-9311",
            "reset": "Hold the side button for 11 seconds",
            "inventory": "thermal label spindle",
            "queries": [
                ("northquay_wifi", "find the Wi-Fi password file for Yard 4", "ops/site-books/north-quay-network.md", "quay-fog-9311"),
                ("northquay_scanner", "find the dock 3 scanner reset instructions for Yard 4", "ops/device-playbooks/north-quay-dock-3.md", "Hold the side button for 11 seconds"),
                ("northquay_inventory", "find the inventory note that lists the thermal label spindle at Yard 4", "ops/spares/north-quay-inventory.md", "thermal label spindle"),
            ],
        },
        {
            "slug": "raven-terminal",
            "name": "Raven Terminal",
            "alias": "Switchback",
            "ssid": "RavenTerm-Guest",
            "wifi": "raven-shift-6612",
            "reset": "Hold the side button for 9 seconds",
            "inventory": "alarm relay cartridge",
            "queries": [
                ("raven_wifi", "find the network runbook for Switchback that includes the guest password", "ops/site-books/raven-terminal-network.md", "raven-shift-6612"),
                ("raven_scanner", "find the scanner reset steps for the dock 3 device at Switchback", "ops/device-playbooks/raven-terminal-dock-3.md", "Hold the side button for 9 seconds"),
                ("raven_inventory", "find the file listing the alarm relay cartridge at Switchback", "ops/spares/raven-terminal-inventory.md", "alarm relay cartridge"),
            ],
        },
        {
            "slug": "orchard-dock",
            "name": "Orchard Dock",
            "alias": "Produce Wing",
            "ssid": "OrchardDock-Guest",
            "wifi": "orchard-wave-7425",
            "reset": "Hold the side button for 8 seconds",
            "inventory": "printer platen roller",
            "queries": [
                ("orchard_wifi", "find the file with the guest Wi-Fi password for Produce Wing", "ops/site-books/orchard-dock-network.md", "orchard-wave-7425"),
                ("orchard_scanner", "find the dock 3 scanner recovery steps for Produce Wing", "ops/device-playbooks/orchard-dock-dock-3.md", "Hold the side button for 8 seconds"),
                ("orchard_inventory", "find the inventory note that mentions the printer platen roller at Produce Wing", "ops/spares/orchard-dock-inventory.md", "printer platen roller"),
            ],
        },
        {
            "slug": "sunset-depot",
            "name": "Sunset Depot",
            "alias": "South Ramp",
            "ssid": "SunsetDepot-Guest",
            "wifi": "sunset-lane-4920",
            "reset": "Hold the side button for 13 seconds",
            "inventory": "gate camera injector",
            "queries": [
                ("sunset_wifi", "find the guest network password for South Ramp", "ops/site-books/sunset-depot-network.md", "sunset-lane-4920"),
                ("sunset_scanner", "find the scanner reset instructions for South Ramp", "ops/device-playbooks/sunset-depot-dock-3.md", "Hold the side button for 13 seconds"),
                ("sunset_inventory", "find the file that lists the gate camera injector at South Ramp", "ops/spares/sunset-depot-inventory.md", "gate camera injector"),
            ],
        },
        {
            "slug": "granite-wharf",
            "name": "Granite Wharf",
            "alias": "Stone Pier",
            "ssid": "GraniteWharf-Guest",
            "wifi": "granite-wake-5814",
            "reset": "Hold the side button for 15 seconds",
            "inventory": "forklift tablet dock",
            "queries": [
                ("granite_wifi", "find the Wi-Fi password file for Stone Pier", "ops/site-books/granite-wharf-network.md", "granite-wake-5814"),
                ("granite_scanner", "find the dock 3 scanner reset note for Stone Pier", "ops/device-playbooks/granite-wharf-dock-3.md", "Hold the side button for 15 seconds"),
                ("granite_inventory", "find the inventory list with the forklift tablet dock at Stone Pier", "ops/spares/granite-wharf-inventory.md", "forklift tablet dock"),
            ],
        },
    ]

    for index, site in enumerate(sites):
        _write_file(
            f"ops/site-books/{site['slug']}-network.md",
            f"""
            Site: {site['name']}
            Local alias: {site['alias']}
            Guest SSID: {site['ssid']}
            Wi-Fi password: {site['wifi']}
            """,
            _dt(f"2025-03-{1 + index:02d}T07:30:00+00:00"),
            mtimes,
        )
        _write_file(
            f"ops/device-playbooks/{site['slug']}-dock-3.md",
            f"""
            Site: {site['name']}
            Alias: {site['alias']}
            Device: Dock 3 scanner
            Reset procedure: {site['reset']}, then tap the trigger twice.
            """,
            _dt(f"2025-03-{1 + index:02d}T10:10:00+00:00"),
            mtimes,
        )
        _write_file(
            f"ops/spares/{site['slug']}-inventory.md",
            f"""
            Site: {site['name']}
            Alias: {site['alias']}
            Spare parts:
            - {site['inventory']}
            - badge printer spare roll
            - charging dock brick
            """,
            _dt(f"2025-03-{1 + index:02d}T11:40:00+00:00"),
            mtimes,
        )
        for case_name, query, expected_path, snippet in site["queries"]:
            _add_case(
                cases,
                name=case_name,
                category="operations",
                difficulty="medium",
                capability_tags=["hidden", "content", "snippet", "disambiguation"],
                query=query,
                expected_path=expected_path,
                expected_snippet=snippet,
            )

    shipments = [
        {
            "shipment_id": 7718,
            "cause": "customs inspection on reefer seal",
            "status": "pending customs inspection",
            "vendor": "Caspian Exports",
            "fix": "replace reefer seal photos",
        },
        {
            "shipment_id": 7724,
            "cause": "carrier missed the bonded window",
            "status": "awaiting bonded trailer swap",
            "vendor": "Faraday Recycling",
            "fix": "rebook bonded trailer",
        },
        {
            "shipment_id": 8842,
            "cause": "reefer unit battery failed during transfer",
            "status": "awaiting reefer battery replacement",
            "vendor": "Northwind Foods",
            "fix": "swap trailer battery cassette",
        },
        {
            "shipment_id": 8861,
            "cause": "manifest mismatch with supplier labels",
            "status": "waiting on corrected supplier manifest",
            "vendor": "Summit Fresh Foods",
            "fix": "supplier must resend corrected pallet labels",
        },
        {
            "shipment_id": 8921,
            "cause": "export paperwork missing pallet counts",
            "status": "blocked on pallet count correction",
            "vendor": "BlueHarbor Marine",
            "fix": "broker must add pallet counts to export packet",
        },
    ]

    for index, shipment in enumerate(shipments):
        incident_path = f"ops/incident-deck/load-{shipment['shipment_id']}-review.md"
        status_path = f"ops/live-loads/{shipment['shipment_id']}.txt"
        _write_file(
            incident_path,
            f"""
            Shipment: {shipment['shipment_id']}
            Counterparty: {shipment['vendor']}
            Delay reason: {shipment['cause']}
            Corrective action: {shipment['fix']}
            """,
            _dt(f"2025-03-{10 + index:02d}T15:15:00+00:00"),
            mtimes,
        )
        _write_file(
            status_path,
            f"""
            Shipment: {shipment['shipment_id']}
            Current status: {shipment['status']}
            Last action: {shipment['fix']}
            """,
            _dt(f"2025-03-{10 + index:02d}T13:25:00+00:00"),
            mtimes,
        )
        _add_case(
            cases,
            name=f"shipment_{shipment['shipment_id']}_incident",
            category="operations",
            difficulty="medium",
            capability_tags=["content", "disambiguation"],
            query=f"find the incident note for the load delayed because {shipment['cause']}",
            expected_path=incident_path,
            expected_snippet=shipment["cause"],
        )
        _add_case(
            cases,
            name=f"shipment_{shipment['shipment_id']}_status_from_cause",
            category="operations",
            difficulty="hard",
            capability_tags=["multi_file", "content", "snippet"],
            query=f"find the status log for the load whose incident says {shipment['cause']}",
            expected_path=status_path,
            expected_snippet=shipment["status"],
        )
        _add_case(
            cases,
            name=f"shipment_{shipment['shipment_id']}_fix",
            category="operations",
            difficulty="medium",
            capability_tags=["content", "snippet", "disambiguation"],
            query=f"find the file that says to {shipment['fix']}",
            expected_path=incident_path,
            expected_snippet=shipment["fix"],
        )

    programs = [
        {
            "slug": "atlas",
            "name": "Atlas",
            "alias": "Beacon",
            "owner": "Mara Chen",
            "scope": "dock label printer refresh",
            "blocker": "dock label printer calibration",
            "rollback_owner": "Quinn Mercer",
            "latest_date": "2025-03-14",
        },
        {
            "slug": "lantern",
            "name": "Lantern",
            "alias": "Bridgebook",
            "owner": "Priya Solanki",
            "scope": "warehouse migration playbook",
            "blocker": "rollback checkpoint signoff",
            "rollback_owner": "Priya Solanki",
            "latest_date": "2025-03-13",
        },
        {
            "slug": "northstar",
            "name": "Northstar",
            "alias": "Dispatch Glass",
            "owner": "Elena Park",
            "scope": "yard dispatch dashboard",
            "blocker": "dispatch screen latency in yard office",
            "rollback_owner": "Dev Patel",
            "latest_date": "2025-03-11",
        },
        {
            "slug": "quartz",
            "name": "Quartz",
            "alias": "Ledger Cleanup",
            "owner": "Tessa Nwosu",
            "scope": "accounts receivable exception review",
            "blocker": "duplicate invoice match tuning",
            "rollback_owner": "Jonah Pike",
            "latest_date": "2025-03-15",
        },
        {
            "slug": "tidewatch",
            "name": "Tidewatch",
            "alias": "Camera Retention",
            "owner": "Lina Gomez",
            "scope": "dock camera retention refresh",
            "blocker": "camera retention policy approval",
            "rollback_owner": "Lina Gomez",
            "latest_date": "2025-03-09",
        },
    ]

    for index, program in enumerate(programs):
        brief_path = f"workstreams/briefs/{program['slug']}.md"
        status_path = f"workstreams/checkpoints/{program['slug']}-{program['latest_date']}.md"
        rollback_path = f"workstreams/fallbacks/{program['slug']}.md"
        _write_file(
            brief_path,
            f"""
            Program: {program['name']}
            Internal codename: {program['alias']}
            Owner: {program['owner']}
            Scope: {program['scope']}
            """,
            _dt(f"2025-03-{4 + index:02d}T09:00:00+00:00"),
            mtimes,
        )
        _write_file(
            status_path,
            f"""
            Program: {program['name']}
            Codename: {program['alias']}
            Weekly update date: {program['latest_date']}
            Primary blocker: {program['blocker']}
            """,
            _dt(f"{program['latest_date']}T18:00:00+00:00"),
            mtimes,
        )
        _write_file(
            rollback_path,
            f"""
            Program: {program['name']}
            Codename: {program['alias']}
            Rollback owner: {program['rollback_owner']}
            Rollback checklist follows the {program['scope']} cutover.
            """,
            _dt(f"2025-03-{4 + index:02d}T14:20:00+00:00"),
            mtimes,
        )
        _add_case(
            cases,
            name=f"{program['slug']}_owner",
            category="projects",
            difficulty="hard",
            capability_tags=["hidden", "multi_file", "content", "snippet"],
            query=f"find the file that names the owner of the {program['alias']} program",
            expected_path=brief_path,
            expected_snippet=f"Owner: {program['owner']}",
        )
        _add_case(
            cases,
            name=f"{program['slug']}_latest_update",
            category="projects",
            difficulty="hard",
            capability_tags=["hidden", "multi_file", "path", "mtime"],
            query=f"find the latest weekly update for the {program['alias']} program",
            expected_path=status_path,
            top_k=1,
        )
        _add_case(
            cases,
            name=f"{program['slug']}_blocker",
            category="projects",
            difficulty="hard",
            capability_tags=["hidden", "multi_file", "content", "snippet"],
            query=f"find the file describing the blocker for the {program['alias']} program",
            expected_path=status_path,
            expected_snippet=program["blocker"],
        )
        _add_case(
            cases,
            name=f"{program['slug']}_rollback_owner",
            category="projects",
            difficulty="hard",
            capability_tags=["hidden", "multi_file", "content", "snippet"],
            query=f"find the rollback plan naming the owner for the {program['alias']} program",
            expected_path=rollback_path,
            expected_snippet=f"Rollback owner: {program['rollback_owner']}",
        )

    vendors = [
        {
            "slug": "meridian",
            "name": "Meridian Cold Storage",
            "alias": "overflow crew",
            "contact": "Elena Park",
            "specialty": "refrigerated overflow",
            "line_item": "outbound pallet transfer",
        },
        {
            "slug": "bluepeak",
            "name": "BluePeak Controls",
            "alias": "spare kit shop",
            "contact": "Dev Patel",
            "specialty": "dock scanner spare kits",
            "line_item": "firmware refresh labor",
        },
        {
            "slug": "coldtrail",
            "name": "ColdTrail Services",
            "alias": "coldfix crew",
            "contact": "Priya Solanki",
            "specialty": "reefer maintenance dispatch",
            "line_item": "compressor field inspection",
        },
        {
            "slug": "summit-packaging",
            "name": "Summit Packaging",
            "alias": "ribbon house",
            "contact": "Mara Chen",
            "specialty": "thermal label stock",
            "line_item": "industrial ribbon replenishment",
        },
        {
            "slug": "ironline",
            "name": "Ironline Freight",
            "alias": "night swap line",
            "contact": "Lina Gomez",
            "specialty": "linehaul trailer swaps",
            "line_item": "expedited trailer reposition",
        },
    ]

    for index, vendor in enumerate(vendors):
        profile_path = f"procurement/vendor-cards/{vendor['slug']}.md"
        invoice_path = f"procurement/payables/{vendor['slug']}-2025-02.txt"
        _write_file(
            profile_path,
            f"""
            Vendor: {vendor['name']}
            Internal shorthand: {vendor['alias']}
            Primary contact: {vendor['contact']}
            Specialty: {vendor['specialty']}
            """,
            _dt(f"2025-02-{21 + index:02d}T11:20:00+00:00"),
            mtimes,
        )
        _write_file(
            invoice_path,
            f"""
            Vendor: {vendor['name']}
            Invoice month: 2025-02
            Line item: {vendor['line_item']}
            """,
            _dt(f"2025-02-{21 + index:02d}T13:40:00+00:00"),
            mtimes,
        )
        _add_case(
            cases,
            name=f"{vendor['slug']}_profile_by_alias",
            category="finance",
            difficulty="hard",
            capability_tags=["hidden", "multi_file", "content", "snippet"],
            query=f"find the vendor profile for the {vendor['alias']}",
            expected_path=profile_path,
            expected_snippet=f"Vendor: {vendor['name']}",
        )
        _add_case(
            cases,
            name=f"{vendor['slug']}_profile_by_specialty",
            category="finance",
            difficulty="medium",
            capability_tags=["content", "snippet", "disambiguation"],
            query=f"find the vendor profile for the company that handles {vendor['specialty']}",
            expected_path=profile_path,
            expected_snippet=f"Specialty: {vendor['specialty']}",
        )
        _add_case(
            cases,
            name=f"{vendor['slug']}_invoice",
            category="finance",
            difficulty="medium",
            capability_tags=["content", "snippet"],
            query=f"find the invoice mentioning {vendor['line_item']}",
            expected_path=invoice_path,
            expected_snippet=vendor["line_item"],
        )

    _write_file(
        "ops/desk-guides/team-index.md",
        """
        Team directory
        Mara Chen: program director
        Dev Patel: director of operations systems
        Lina Gomez: platform delivery manager
        Jules Duran: logistics coordinator
        Elena Park: vendor operations lead
        Priya Solanki: migration lead
        Quinn Mercer: release manager
        Tessa Nwosu: finance systems owner
        """,
        _dt("2025-01-15T09:20:00+00:00"),
        mtimes,
    )
    _write_file(
        "ops/desk-guides/rotations.md",
        """
        Operations systems weekday rotation
        Monday: Dev Patel
        Tuesday: Mara Chen
        Wednesday: Quinn Mercer
        Platform weekend backup
        Saturday: Lina Gomez
        Sunday: Priya Solanki
        """,
        _dt("2025-02-12T10:00:00+00:00"),
        mtimes,
    )
    _write_file(
        "people/reviews/data-platform-analyst-panel.md",
        """
        Role: data platform analyst
        Candidate: Imani Holt
        Recommend hire: Imani Holt
        Notes: strongest evidence synthesis in the panel.
        """,
        _dt("2025-03-08T15:30:00+00:00"),
        mtimes,
    )
    _write_file(
        "people/reviews/site-reliability-manager-panel.md",
        """
        Role: site reliability manager
        Candidate: Devika Shah
        Recommend hire: Devika Shah
        Notes: best operator calibration in the loop.
        """,
        _dt("2025-03-09T15:30:00+00:00"),
        mtimes,
    )
    _write_file(
        "house-rules/archive-room-entry.md",
        """
        Area: archive room
        Door code: 4825#
        Keep the latch closed after badge entry.
        """,
        _dt("2025-02-20T08:45:00+00:00"),
        mtimes,
    )
    _write_file(
        "house-rules/south-loading-bay.md",
        """
        Area: south loading bay
        Keypad code: 7714#
        Use only during scheduled trailer arrivals.
        """,
        _dt("2025-02-21T08:45:00+00:00"),
        mtimes,
    )
    _write_file(
        "house-rules/guest-network-window.md",
        """
        Guest network policy
        Visitor credentials may remain active for 24 hours maximum.
        Escort approval is required for any extension.
        """,
        _dt("2025-02-23T09:15:00+00:00"),
        mtimes,
    )
    _write_file(
        "incident-followups/badge-printer-temp-location.md",
        """
        Incident: badge cloning follow-up
        Temporary badge printer location: cabinet C-19.
        Replace the ribbon after any visitor batch over 20 cards.
        """,
        _dt("2025-03-02T17:20:00+00:00"),
        mtimes,
    )

    _write_file(
        ".maps/customer-index.txt",
        """
        bay aquarium account = BlueHarbor Marine
        battery recycler account = Faraday Recycling
        midwest produce consolidator = Summit Fresh Foods
        greenhouse sensor client = Verdant Sensors
        lab freezer account = Orchid Labs
        dock label modernization client = Redwood Industrial
        """,
        _dt("2025-03-03T07:00:00+00:00"),
        mtimes,
    )
    _write_file(
        ".maps/site-callouts.txt",
        """
        Pier West = Harbor 7
        Yard 4 = North Quay
        Switchback = Raven Terminal
        Produce Wing = Orchard Dock
        South Ramp = Sunset Depot
        Stone Pier = Granite Wharf
        """,
        _dt("2025-03-03T07:05:00+00:00"),
        mtimes,
    )
    _write_file(
        ".maps/program-codes.txt",
        """
        Beacon = Atlas
        Bridgebook = Lantern
        Dispatch Glass = Northstar
        Ledger Cleanup = Quartz
        Camera Retention = Tidewatch
        """,
        _dt("2025-03-03T07:10:00+00:00"),
        mtimes,
    )
    _write_file(
        ".maps/vendor-shorthand.txt",
        """
        overflow crew = Meridian Cold Storage
        spare kit shop = BluePeak Controls
        coldfix crew = ColdTrail Services
        ribbon house = Summit Packaging
        night swap line = Ironline Freight
        """,
        _dt("2025-03-03T07:15:00+00:00"),
        mtimes,
    )

    for path, content, when in [
        (
            "notes/leadership-offsite.md",
            "Leadership offsite notes mention staffing, not operations controls.",
            _dt("2025-01-22T12:00:00+00:00"),
        ),
        (
            "notes/q1-planning-draft.md",
            "Draft planning memo with no approved customer commitments.",
            _dt("2025-01-25T12:00:00+00:00"),
        ),
        (
            "finance/archive/2024-close-checklist.md",
            "Archived checklist for the 2024 close package.",
            _dt("2025-01-30T08:00:00+00:00"),
        ),
        (
            "procurement/rfp/thermal-label-rfp.md",
            "RFP draft for future thermal label vendors.",
            _dt("2025-02-02T09:00:00+00:00"),
        ),
        (
            "operations/logistics/parking-lot-rules.md",
            "Parking lot rules for employee vehicles.",
            _dt("2025-02-04T09:00:00+00:00"),
        ),
        (
            "workstreams/misc/atlas-parking-lot.md",
            "Parking lot feature requests unrelated to current blocker.",
            _dt("2025-03-05T12:00:00+00:00"),
        ),
        (
            "procurement/payables/meridian-2025-01.txt",
            "Older Meridian invoice for freezer overflow staging.",
            _dt("2025-01-31T11:00:00+00:00"),
        ),
        (
            "house-rules/printer-ribbon-disposal.md",
            "Printer ribbon disposal note for general office equipment.",
            _dt("2025-02-28T11:00:00+00:00"),
        ),
    ]:
        _write_file(path, content, when, mtimes)

    extra_cases = [
        ("customer_alias_note", "aliases", "medium", ["hidden", "content", "snippet"], "find the hidden note that maps the bay aquarium account to a customer", ".maps/customer-index.txt", "bay aquarium account = BlueHarbor Marine"),
        ("site_alias_note", "aliases", "medium", ["hidden", "content", "snippet"], "find the hidden note that maps Yard 4 to a site", ".maps/site-callouts.txt", "Yard 4 = North Quay"),
        ("program_alias_note", "aliases", "medium", ["hidden", "content", "snippet"], "find the hidden note that says Beacon means Atlas", ".maps/program-codes.txt", "Beacon = Atlas"),
        ("vendor_alias_note", "aliases", "medium", ["hidden", "content", "snippet"], "find the hidden note that says ribbon house means Summit Packaging", ".maps/vendor-shorthand.txt", "ribbon house = Summit Packaging"),
        ("directory_for_beacon_owner", "people", "hard", ["hidden", "multi_file", "content", "snippet"], "find the directory file listing the role of the owner of the Beacon program", "ops/desk-guides/team-index.md", "Mara Chen: program director"),
        ("oncall_dev_patel", "people", "medium", ["content", "snippet"], "find the on-call note that includes Dev Patel on the operations systems weekday rotation", "ops/desk-guides/rotations.md", "Monday: Dev Patel"),
        ("analyst_scorecard", "hr", "medium", ["content", "snippet"], "find the scorecard recommending Imani Holt for the analyst role", "people/reviews/data-platform-analyst-panel.md", "Recommend hire: Imani Holt"),
        ("sre_scorecard", "hr", "medium", ["content", "snippet"], "find the scorecard for the site reliability candidate Devika Shah", "people/reviews/site-reliability-manager-panel.md", "Recommend hire: Devika Shah"),
        ("archive_room_code", "facilities", "medium", ["content", "snippet"], "find the document with the archive room door code", "house-rules/archive-room-entry.md", "Door code: 4825#"),
        ("south_loading_bay_code", "facilities", "medium", ["content", "snippet"], "find the note with the keypad code for the south loading bay", "house-rules/south-loading-bay.md", "Keypad code: 7714#"),
        ("guest_network_policy", "security", "medium", ["content", "snippet"], "find the advisory that says visitor credentials last one day maximum", "house-rules/guest-network-window.md", "Visitor credentials may remain active for 24 hours maximum."),
        ("badge_printer_cabinet", "security", "medium", ["content", "snippet"], "find the incident follow-up mentioning the temporary badge printer cabinet", "incident-followups/badge-printer-temp-location.md", "Temporary badge printer location: cabinet C-19."),
        ("no_mercury_contract", "negative", "medium", ["no_answer"], "find the signed contract for Mercury Bio", None, None),
        ("no_q2_bonus_sheet", "negative", "medium", ["no_answer"], "find the spreadsheet with Q2 retention bonuses", None, None),
    ]
    for name, category, difficulty, tags, query, expected_path, snippet in extra_cases:
        _add_case(
            cases,
            name=name,
            category=category,
            difficulty=difficulty,
            capability_tags=tags,
            query=query,
            expected_path=expected_path,
            expected_snippet=snippet,
            top_k=1 if expected_path is None else 3,
        )

    personal_files = [
        (
            "personal/inbox/cli-bootstraps.md",
            """
            Shell safety notes
            Preferred preamble:
            set -euo pipefail
            I use this when I want scripts to fail loudly instead of limping onward.
            """,
            "2025-01-12T18:10:00+00:00",
        ),
        (
            "personal/reference/parameter-expansion-cheats.md",
            """
            Parameter expansion drills
            Strip a suffix without invoking sed:
            ${file%.csv}
            Also useful for trimming one directory level with ${path%/*}.
            """,
            "2025-01-14T18:10:00+00:00",
        ),
        (
            "personal/scratch/reliability-loop.txt",
            """
            Reliability drills
            Retry an occasionally flaky command:
            until make test; do sleep 5; done
            Good enough for noisy local integration tests.
            """,
            "2025-01-16T18:10:00+00:00",
        ),
        (
            "personal/reference/null-delimited-filenames.md",
            """
            Filename safety
            Prefer:
            find . -type f -print0 | xargs -0 ls -l
            and when reading lines:
            while IFS= read -r line; do
              printf '%s\n' "$line"
            done
            """,
            "2025-01-18T18:10:00+00:00",
        ),
        (
            "personal/cards/process-substitution.txt",
            """
            Comparing command output
            diff <(sort old.txt) <(sort new.txt)
            Nice when I want to compare transformed output without temp files.
            """,
            "2025-01-20T18:10:00+00:00",
        ),
        (
            "personal/lab/throwaway-workdirs.md",
            """
            Temporary files
            tmpdir=$(mktemp -d)
            trap 'rm -rf "$tmpdir"' EXIT
            This keeps scratch directories from piling up.
            """,
            "2025-01-22T18:10:00+00:00",
        ),
        (
            "personal/desk/pipeline-postmortem.md",
            """
            Pipeline debugging
            After a pipeline, inspect ${PIPESTATUS[@]} to see which command failed.
            Helpful when tee hides the real failure point.
            """,
            "2025-01-24T18:10:00+00:00",
        ),
        (
            "personal/clippings/search-hygiene.md",
            """
            Ripgrep notes
            Example:
            rg --glob '!node_modules/**' --glob '!dist/**' TODO
            Exclude noisy build folders aggressively.
            """,
            "2025-01-26T18:10:00+00:00",
        ),
        (
            "personal/archive/terminal-cleanup.txt",
            """
            Shell history cleanup
            Remove the last command before sharing a terminal screenshot:
            history -d $(history 1 | awk '{print $1}')
            Then run history -w if I want it flushed.
            """,
            "2025-01-28T18:10:00+00:00",
        ),
        (
            "personal/desk/fzf-jump-list.md",
            """
            Navigation notes
            fzf plus fd is still the fastest way for me to jump into a project tree.
            Keep path previews shallow so I do not drown in noise.
            """,
            "2025-01-30T18:10:00+00:00",
        ),
        (
            "personal/reference/awk-reminders.md",
            """
            Awk reminders
            awk -F, '{sum += $3} END {print sum}'
            Still easier than spinning up Python for tiny column work.
            """,
            "2025-02-01T18:10:00+00:00",
        ),
        (
            "personal/inbox/git-rebase-traps.md",
            """
            Git course notes
            During a rebase, use git rebase --edit-todo when I need to reorder or squash after starting.
            Keep ORIG_HEAD in mind if I need to recover.
            """,
            "2025-02-02T18:10:00+00:00",
        ),
        (
            "personal/scratch/tmux-copy-mode.txt",
            """
            Tmux notes
            Copy mode is still easiest with prefix + [ then vi motions.
            I always forget the search bindings if I do not write them down.
            """,
            "2025-02-03T18:10:00+00:00",
        ),
        (
            "personal/lab/sqlite-joins.md",
            """
            SQLite practice
            Left joins plus coalesce are enough for half of the household tracking scripts.
            Need another pass on grouped window functions.
            """,
            "2025-02-04T18:10:00+00:00",
        ),
        (
            "personal/archive/http-cache-things.md",
            """
            HTTP caching note dump
            Cache-Control and ETag interact in ways I still only half remember.
            Review stale-while-revalidate examples later.
            """,
            "2025-02-05T18:10:00+00:00",
        ),
        (
            "personal/archive/regex-exercises.md",
            """
            Regex exercises
            Need more practice with reluctant quantifiers and multiline captures.
            """,
            "2025-02-06T18:10:00+00:00",
        ),
        (
            "personal/projects/js-build-lecture.md",
            """
            JS build lecture
            I finally understand why source maps get weird after double transforms.
            """,
            "2025-02-07T18:10:00+00:00",
        ),
        (
            "personal/cards/ssh-config-cheats.txt",
            """
            SSH config reminders
            Match exec is useful but can get unreadable fast.
            Keep prod aliases obvious.
            """,
            "2025-02-08T18:10:00+00:00",
        ),
        (
            "personal/desk/makefile-notes.md",
            """
            Makefile notes
            Phony targets should stay explicit.
            Avoid hiding side effects behind vague names.
            """,
            "2025-02-09T18:10:00+00:00",
        ),
        (
            "personal/lab/docker-layering.md",
            """
            Docker layering
            Keep frequently changing files low in the Dockerfile so cache reuse survives longer.
            """,
            "2025-02-10T18:10:00+00:00",
        ),
        (
            "personal/archive/2025/01-14-storm-day.md",
            """
            Wind picked up all afternoon.
            Lent the spare folding chair to Camille before the storm because her balcony one snapped.
            Need to remember that I am down to a single chair now.
            """,
            "2025-01-14T21:10:00+00:00",
        ),
        (
            "personal/archive/2025/02-06-flooded-tram.md",
            """
            Huge puddles by the tram line after work.
            Leo borrowed the tall rain boots so he could get home without soaking his socks.
            I should dry the insoles near the heater tomorrow.
            """,
            "2025-02-06T21:10:00+00:00",
        ),
        (
            "personal/archive/2025/02-19-river-stop.md",
            """
            Wrote down that the orange-awning cafe by the river tram stop was better than I remembered.
            The black sesame cream bun was the thing to go back for.
            """,
            "2025-02-19T21:10:00+00:00",
        ),
        (
            "personal/archive/2025/03-03-keyboard-day.md",
            """
            Keyboard practice felt stiff.
            The wrist nerve glide before scales actually helped and I should stop skipping it.
            """,
            "2025-03-03T21:10:00+00:00",
        ),
        (
            "personal/archive/2025/03-11-basil.md",
            """
            Afternoon sun hit the basil too hard again.
            Need to move the planter so it gets morning light and shade after lunch.
            """,
            "2025-03-11T21:10:00+00:00",
        ),
        (
            "personal/trips/kyoto-return-list.md",
            """
            Kyoto second pass
            Go back to Kissa Sora near the river tram stop.
            Orange awning, tiny standing counter, best black sesame cream bun of the trip.
            """,
            "2025-02-20T10:00:00+00:00",
        ),
        (
            "personal/trips/tokyo-loose-ends.md",
            """
            Tokyo loose ends
            Return to the basement bookstore in Jimbocho with the blue stair rail.
            I still want the essay collection on cities and maintenance work.
            """,
            "2025-02-22T10:00:00+00:00",
        ),
        (
            "personal/inbox/overnight-train-pack.txt",
            """
            Overnight train packing
            Keep the slim eye mask, charger brick, and one extra pair of socks in the top pocket.
            """,
            "2025-02-24T10:00:00+00:00",
        ),
        (
            "personal/lab/bun-notes.md",
            """
            Black sesame buns
            Tangzhong helped the crumb.
            Toast the seeds longer next time and make the filling less sugary.
            """,
            "2025-02-21T19:00:00+00:00",
        ),
        (
            "personal/misc/focaccia-v3.md",
            """
            No-knead focaccia
            The olive brine drizzle made the crust better than plain oil.
            Try shallots next time.
            """,
            "2025-02-23T19:00:00+00:00",
        ),
        (
            "personal/archive/mushroom-rice.txt",
            """
            Mushroom rice
            Toast rice a little longer and finish with lemon at the end.
            """,
            "2025-02-25T19:00:00+00:00",
        ),
        (
            "personal/lab/ssh-safety.md",
            """
            Remote shell safety
            Production hosts get a red PS1 so I stop confusing them with my local shell.
            Also disable shell completion that autocompletes dangerous paths too eagerly.
            """,
            "2025-02-10T20:20:00+00:00",
        ),
        (
            "personal/projects/homelab-backups.md",
            """
            Backup plan
            After successful backups, run restic forget --prune on the old snapshots.
            Keep one daily for a week, then weekly copies.
            """,
            "2025-02-12T20:20:00+00:00",
        ),
        (
            "personal/inbox/network-rename-note.md",
            """
            Home network notes
            Need to rename the living-room access point after I stabilize the mesh.
            """,
            "2025-02-14T20:20:00+00:00",
        ),
        (
            "personal/clippings/slow-productivity.md",
            """
            Slow Productivity notes
            Best phrase in the book: work in seasons instead of pretending intensity can stay flat forever.
            Protect long arcs, not just daily streaks.
            """,
            "2025-02-15T17:40:00+00:00",
        ),
        (
            "personal/archive/maintenance-reading.txt",
            """
            Maintenance reading
            The image that stayed with me was 'windowless errands' as a metaphor for invisible upkeep.
            Might reuse that in an essay.
            """,
            "2025-02-17T17:40:00+00:00",
        ),
        (
            "personal/desk/piano-loop.md",
            """
            Piano practice
            Five-minute Hanon warmup before jazz voicing drills.
            If wrists feel stiff, slow down and reset posture first.
            """,
            "2025-02-18T18:30:00+00:00",
        ),
        (
            "personal/notes/wrist-reset.txt",
            """
            Desk recovery
            Do the wrist nerve glide before keyboard practice.
            Shoulder rolls are nice, but the nerve glide changes the feeling immediately.
            """,
            "2025-02-19T18:30:00+00:00",
        ),
        (
            "personal/misc/balcony-planter.md",
            """
            Balcony garden
            Afternoon sun scorched the basil again.
            Move the planter so it gets gentler morning light.
            """,
            "2025-03-11T07:50:00+00:00",
        ),
        (
            "personal/drafts/windowless-errands-fragment.md",
            """
            Essay ideas
            Maintenance work feels like windowless errands: necessary, repetitive, hard to narrate, easy to undervalue.
            Maybe pair this with notes from the city essay collection.
            """,
            "2025-02-16T16:00:00+00:00",
        ),
        (
            "personal/admin/feb-checkin.txt",
            """
            February money check-in
            Delay the camera lens repair until after the tax refund lands.
            Replace the bike light first if one thing has to happen now.
            """,
            "2025-02-27T18:00:00+00:00",
        ),
        (
            "personal/notes/gifts-and-birthdays.md",
            """
            Gift ideas
            Aya: enamel camping mug
            Leo: repair kit for his old headphones
            Camille: heavy glass tea tumbler
            """,
            "2025-02-05T19:10:00+00:00",
        ),
        (
            "personal/inbox/weekend-brain-dump.md",
            """
            Weekend brain dump
            Buy filters, fix drawer, call landlord, return library books, remember mug idea.
            """,
            "2025-02-09T20:00:00+00:00",
        ),
        (
            "personal/desk/cleanup-reset.md",
            """
            Desk reset
            Clear receipts, wipe keyboard, move sticky notes into actual files.
            """,
            "2025-02-11T20:00:00+00:00",
        ),
        (
            "personal/archive/reading-queue.txt",
            """
            Reading queue
            Finish the essay collection on cities before buying anything else in Jimbocho.
            """,
            "2025-02-13T20:00:00+00:00",
        ),
        (
            "personal/inbox/course-admin.md",
            """
            Course admin
            Need to revisit the shell exercises on quoting because I still hesitate around arrays.
            """,
            "2025-01-29T20:00:00+00:00",
        ),
    ]
    for path, content, when in personal_files:
        _write_file(path, content, _dt(when), mtimes)

    personal_cases = [
        ("personal_bash_retry", "find my shell-course note about retrying a flaky command until it finally works", "personal/scratch/reliability-loop.txt", "until make test; do sleep 5; done", ["personal", "content", "snippet"]),
        ("personal_strict_mode", "find the shell note where I wrote the strict-mode preamble I put at the top of scripts", "personal/inbox/cli-bootstraps.md", "set -euo pipefail", ["personal", "content", "snippet"]),
        ("personal_xargs_spaces", "find the lesson note about handling filenames with spaces safely when piping into xargs", "personal/reference/null-delimited-filenames.md", "find . -type f -print0 | xargs -0", ["personal", "content", "snippet"]),
        ("personal_compare_outputs", "find the note about comparing two command outputs without temporary files", "personal/cards/process-substitution.txt", "diff <(sort old.txt) <(sort new.txt)", ["personal", "content", "snippet"]),
        ("personal_temp_cleanup", "find the note about cleaning a temporary directory automatically on exit", "personal/lab/throwaway-workdirs.md", "trap 'rm -rf \"$tmpdir\"' EXIT", ["personal", "content", "snippet"]),
        ("personal_strip_suffix", "find the shell note where I remove a csv suffix without using sed", "personal/reference/parameter-expansion-cheats.md", "${file%.csv}", ["personal", "content", "snippet"]),
        ("personal_read_backslashes", "find the shell note about reading lines without mangling backslashes", "personal/reference/null-delimited-filenames.md", "while IFS= read -r line", ["personal", "content", "snippet"]),
        ("personal_pipeline_failure", "find the note about checking which command failed in a pipeline", "personal/desk/pipeline-postmortem.md", "${PIPESTATUS[@]}", ["personal", "content", "snippet"]),
        ("personal_rg_excludes", "find the note about excluding noisy folders while searching with ripgrep", "personal/clippings/search-hygiene.md", "rg --glob '!node_modules/**' --glob '!dist/**' TODO", ["personal", "content", "snippet"]),
        ("personal_history_redact", "find the shell note about removing the last command from history before sharing a screenshot", "personal/archive/terminal-cleanup.txt", "history -d $(history 1 | awk '{print $1}')", ["personal", "content", "snippet"]),
        ("personal_folding_chair", "find the journal entry where I wrote about lending the folding chair to Camille before the storm", "personal/archive/2025/01-14-storm-day.md", "Lent the spare folding chair to Camille before the storm", ["personal", "content", "snippet"]),
        ("personal_rain_boots", "find the journal entry where Leo borrowed my tall rain boots after the flooded tram stop", "personal/archive/2025/02-06-flooded-tram.md", "Leo borrowed the tall rain boots", ["personal", "content", "snippet"]),
        ("personal_orange_awning_cafe", "find the travel note about the cafe with the orange awning near the river tram stop", "personal/trips/kyoto-return-list.md", "Orange awning, tiny standing counter", ["personal", "content", "snippet"]),
        ("personal_basement_bookstore", "find the note where I wrote about going back to the basement bookstore with the blue stair rail", "personal/trips/tokyo-loose-ends.md", "basement bookstore in Jimbocho with the blue stair rail", ["personal", "content", "snippet"]),
        ("personal_black_sesame_buns", "find the recipe note I wrote after the bakery experiment with the black sesame buns", "personal/lab/bun-notes.md", "Tangzhong helped the crumb.", ["personal", "content", "snippet"]),
        ("personal_focaccia_brine", "find the recipe note where I said the olive brine made the crust better", "personal/misc/focaccia-v3.md", "olive brine drizzle made the crust better", ["personal", "content", "snippet"]),
        ("personal_remote_red_prompt", "find my note about making the prompt red on remote machines so I do not type on the wrong host", "personal/lab/ssh-safety.md", "Production hosts get a red PS1", ["personal", "content", "snippet"]),
        ("personal_backup_prune", "find the home lab note about pruning old snapshots after backups", "personal/projects/homelab-backups.md", "restic forget --prune", ["personal", "content", "snippet"]),
        ("personal_work_in_seasons", "find the reading note where I underlined the idea of working in seasons instead of constant intensity", "personal/clippings/slow-productivity.md", "work in seasons instead of pretending intensity can stay flat forever", ["personal", "content", "snippet"]),
        ("personal_hanon_warmup", "find the practice note about doing Hanon before voicing drills", "personal/desk/piano-loop.md", "Five-minute Hanon warmup before jazz voicing drills", ["personal", "content", "snippet"]),
        ("personal_wrist_nerve_glide", "find the note where I reminded myself to do the wrist nerve glide before playing", "personal/notes/wrist-reset.txt", "Do the wrist nerve glide before keyboard practice.", ["personal", "content", "snippet"]),
        ("personal_basil_sun", "find the garden note where I realized the basil was getting too much afternoon sun", "personal/archive/2025/03-11-basil.md", "Afternoon sun hit the basil too hard again.", ["personal", "content", "snippet"]),
        ("personal_windowless_errands", "find the writing note where I compared maintenance work to windowless errands", "personal/drafts/windowless-errands-fragment.md", "Maintenance work feels like windowless errands", ["personal", "content", "snippet"]),
        ("personal_delay_lens_repair", "find the personal finance note where I said to postpone the camera lens repair", "personal/admin/feb-checkin.txt", "Delay the camera lens repair until after the tax refund lands.", ["personal", "content", "snippet"]),
        ("personal_aya_gift", "find the note where I wrote the camping mug gift idea for Aya", "personal/notes/gifts-and-birthdays.md", "Aya: enamel camping mug", ["personal", "content", "snippet"]),
    ]
    for name, query, expected_path, snippet, tags in personal_cases:
        _add_case(
            cases,
            name=name,
            category="personal",
            difficulty="medium",
            capability_tags=tags,
            query=query,
            expected_path=expected_path,
            expected_snippet=snippet,
        )

    payload = {
        "suite_name": "queryfind_handmade125_v1",
        "description": "A hand-curated benchmark with a realistic synthetic filesystem, alias files, indirect clues, multi-file search hops, and a dense personal-notes subtree.",
        "corpus_root": "handmade100",
        "mtimes": dict(sorted(mtimes.items())),
        "cases": cases,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"generated {len(cases)} cases in {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
