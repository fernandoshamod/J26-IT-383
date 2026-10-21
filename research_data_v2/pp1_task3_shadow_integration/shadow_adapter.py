"""Read-only shadow assessment of fresh USER packages from current option IDs."""
import csv
from itertools import combinations
from pathlib import Path

from research_data_v2.pp1_task2_conflict_engine.conflict_engine import (
    CONFLICT, PENDING, lookup_pair,
)

ROOT = Path(__file__).resolve().parents[2]
OPTION_FILE = ROOT / "hybrid_simulation_v1" / "synthetic_service_options.csv"


def load_current_options(path=OPTION_FILE):
    """Load source option records without using package catalogs or fixtures."""
    options = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            option_id = row.get("service_option_id", "").strip()
            if not option_id or option_id in options:
                raise ValueError(f"Missing or duplicate source option ID: {option_id!r}")
            options[option_id] = row
    return options


def assess_package(event, package, source_options=None):
    """Return a separate assessment without mutating event or package."""
    if not str(event.get("event_id", "")).startswith("USER-"):
        raise ValueError("Shadow assessment requires a USER event")
    options = source_options if source_options is not None else load_current_options()
    option_ids = list(package.get("option_ids", []))
    vendor_ids = list(package.get("vendor_ids", []))
    breakdown = list(package.get("service_breakdown", []))
    selected = list(package.get("package_options", []))
    required = [s.strip() for s in str(event.get("required_services", "")).split(";") if s.strip()]
    failures, resolved = [], []
    if not option_ids or not (len(option_ids) == len(vendor_ids) == len(breakdown) == len(selected)):
        failures.append("Package ID, vendor, breakdown and option counts differ or are empty.")
    if len(set(option_ids)) != len(option_ids):
        failures.append("Package repeats an option ID.")
    if len(set(vendor_ids)) != len(vendor_ids):
        failures.append("Package repeats a vendor ID.")
    if len(required) != len(set(required)) or len(option_ids) != len(required):
        failures.append("Required-service cardinality differs from package options.")
    for i, option_id in enumerate(option_ids):
        source = options.get(str(option_id))
        if source is None:
            failures.append(f"{option_id}: absent from current source records.")
            continue
        resolved.append({
            "option_id": option_id, "vendor_id": source["business_id"],
            "service": source["service_category"],
            "data_origin": source.get("data_origin") or "UNKNOWN",
            "is_vendor_confirmed": source.get("is_vendor_confirmed") == "True",
        })
        if i >= min(len(vendor_ids), len(breakdown), len(selected)):
            continue
        comparisons = (
            (vendor_ids[i], source["business_id"], "package vendor"),
            (breakdown[i].get("vendor_id"), source["business_id"], "breakdown vendor"),
            (breakdown[i].get("option_id"), option_id, "breakdown option"),
            (breakdown[i].get("service"), source["service_category"], "breakdown service"),
            (selected[i].get("business_id"), source["business_id"], "embedded vendor"),
            (selected[i].get("service_option_id"), option_id, "embedded option"),
            (selected[i].get("service_category"), source["service_category"], "embedded service"),
        )
        for actual, expected, label in comparisons:
            if str(actual) != str(expected):
                failures.append(f"{option_id}: {label} differs from current source.")
        supported = {x.strip().casefold() for x in source["supported_event_types"].split(";")}
        if str(event.get("event_type", "")).casefold() not in supported:
            failures.append(f"{option_id}: event type not supported by source.")
        location = (source["simulated_service_city"].casefold(), source["simulated_service_state"].casefold())
        if (str(event.get("city", "")).casefold(), str(event.get("state", "")).casefold()) != location:
            failures.append(f"{option_id}: simulated location differs from event.")
    if sorted(row["service"] for row in resolved) != sorted(required):
        failures.append("Source options do not cover each required service exactly once.")

    pair_results = []
    if not failures:
        for first, second in combinations(sorted(row["vendor_id"] for row in resolved), 2):
            # Current records contain no event-specific pair evidence.
            # Deliberately do not load Task 2 synthetic fixtures.
            pair_results.append(lookup_pair(first, second, event["event_id"], []))
    checks = [
        {"category": category, "status": PENDING, "reason": reason}
        for category, reason in (
            ("availability", "No vendor-confirmed availability for this USER event."),
            ("option_schedule", "No option-specific service interval or timezone."),
            ("teardown_duration", "No option-specific teardown duration."),
            ("resource_requirements", "No documented vendor equipment or crew assignment."),
            ("resource_capacity", "No documented shared equipment or crew limits."),
        )
    ]
    if pair_results:
        checks.extend({
            "category": "vendor_pair_evidence", "status": pair["status"],
            "vendor_ids": pair["vendor_ids"], "reason": pair["reason"],
        } for pair in pair_results)
    else:
        checks.append({"category": "vendor_pair_evidence", "status": PENDING,
                       "reason": "No assessable pair or source mapping is incomplete."})
    if failures:
        checks.append({"category": "source_mapping", "status": PENDING,
                       "reason": "Source mapping requires correction before assessment."})
    conflicts = [check for check in checks if check["status"] == CONFLICT]
    return {
        "event_id": event["event_id"], "package_id": package.get("package_id"),
        "option_ids": option_ids, "vendor_ids": vendor_ids,
        "resolved_options": resolved,
        "source_option_file": str(OPTION_FILE.relative_to(ROOT)).replace("\\", "/"),
        "source_data_class": "SYNTHETIC_TEST",
        "existing_feasibility_status": package.get("feasibility", {}).get("final_status"),
        "existing_ranking_score": package.get("ranking_score"),
        "status": CONFLICT if conflicts else PENDING,
        "confirmed_conflicts": conflicts,
        "pending_checks": [check for check in checks if check["status"] == PENDING],
        "missing_evidence_categories": sorted({check["category"] for check in checks
                                               if check["status"] == PENDING}),
        "pair_results": pair_results, "mapping_failures": failures,
        "operational_engine_status": "NOT_RUN_MISSING_INPUTS",
        "venue_suitability": "EXTERNAL_VERIFICATION_REQUIRED",
        "is_real_world_feasible": False,
    }