"""Execute fresh USER requests and write shadow-only research results."""
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend.engine.dynamic_package_service import generate_dynamic_packages
from backend.schemas.dynamic_package_request import DynamicPackageRequest
from research_data_v2.pp1_task3_shadow_integration.shadow_adapter import (
    assess_package, load_current_options,
)

SCENARIOS = [
    {"event_type": "Wedding", "event_date": "2026-10-21", "start_time": "10:00",
     "end_time": "18:00", "city": "Philadelphia", "state": "PA",
     "guest_count": 50, "budget_lkr": 1000000,
     "required_services": ["Photography", "Decoration"], "top_k": 3},
    {"event_type": "Corporate", "event_date": "2026-10-22", "start_time": "09:00",
     "end_time": "17:00", "city": "Philadelphia", "state": "PA",
     "guest_count": 40, "budget_lkr": 1000000,
     "required_services": ["Photography", "Audio Visual"], "top_k": 3},
]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_hashes():
    path = ROOT / "research_data_v2/audit_2026-10-17_01/dataset_inventory.csv"
    results = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            target = ROOT / row["path"]
            if target.is_file():
                results.append({"path": row["path"], "matches_task1": sha256(target) == row["sha256"]})
            else:
                results.append({"path": row["path"], "matches_task1": None})
    return results


def main():
    monitored = [
        ROOT / "backend/engine/dynamic_package_service.py",
        ROOT / "backend/engine/bounded_package_generator.py",
        ROOT / "backend/engine/dynamic_feasibility.py",
        ROOT / "research_data_v2/pp1_task2_conflict_engine/conflict_engine.py",
    ]
    before = {str(path.relative_to(ROOT)): sha256(path) for path in monitored}
    options = load_current_options()
    rows, events = [], []
    start_all = perf_counter()
    for scenario_number, scenario in enumerate(SCENARIOS, 1):
        start = perf_counter()
        response = generate_dynamic_packages(DynamicPackageRequest.model_validate(scenario))
        generation_ms = (perf_counter() - start) * 1000
        packages = response["generation"]["packages"]
        event = response["event"]
        events.append({
            "scenario": scenario_number, "event_id": response["event_id"],
            "required_services": scenario["required_services"],
            "generation_status": response["generation"]["status"],
            "generated_packages_examined": len(packages),
            "generation_ms": round(generation_ms, 3),
            "search": response["generation"]["search"],
        })
        for package in packages:
            start = perf_counter()
            assessment = assess_package(event, package, options)
            adapter_ms = (perf_counter() - start) * 1000
            rows.append({
                "scenario": scenario_number, "event_id": response["event_id"],
                "package_id": package["package_id"],
                "vendor_ids": ";".join(package["vendor_ids"]),
                "option_ids": ";".join(package["option_ids"]),
                "existing_feasibility_status": package["feasibility"]["final_status"],
                "existing_ranking_score": package["ranking_score"],
                "shadow_status": assessment["status"],
                "supported_conflicts": len(assessment["confirmed_conflicts"]),
                "pending_checks": len(assessment["pending_checks"]),
                "missing_evidence_categories": ";".join(assessment["missing_evidence_categories"]),
                "mapping_failures": len(assessment["mapping_failures"]),
                "adapter_ms": round(adapter_ms, 3),
            })
    elapsed = perf_counter() - start_all
    after = {str(path.relative_to(ROOT)): sha256(path) for path in monitored}
    category_counts = Counter()
    for row in rows:
        category_counts.update(row["missing_evidence_categories"].split(";"))
    summary = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_class": "SYNTHETIC_TEST", "scenario_count": len(SCENARIOS),
        "fresh_user_event_count": len(events), "packages_examined": len(rows),
        "packages_with_supported_conflicts": sum(row["supported_conflicts"] > 0 for row in rows),
        "packages_requiring_verification": sum(row["shadow_status"] == "VERIFICATION_REQUIRED" for row in rows),
        "missing_evidence_frequency_by_package": dict(sorted(category_counts.items())),
        "mapping_failure_count": sum(row["mapping_failures"] for row in rows),
        "assessment_disagreement_count": sum(
            row["existing_feasibility_status"] != row["shadow_status"] for row in rows
        ),
        "adapter_total_ms": round(sum(row["adapter_ms"] for row in rows), 3),
        "adapter_mean_ms": round(sum(row["adapter_ms"] for row in rows) / len(rows), 3) if rows else None,
        "evaluation_wall_seconds": round(elapsed, 3),
        "production_and_task2_hashes_unchanged_during_run": before == after,
        "task1_inventory_hashes": inventory_hashes(),
        "events": events,
        "packages": rows,
    }
    with (HERE / "evaluation_results.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    with (HERE / "shadow_comparison.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    example = rows[0] if rows else {"message": "No packages generated"}
    with (HERE / "example_output.txt").open("x", encoding="utf-8") as stream:
        stream.write("Shadow assessment of a freshly generated USER event; synthetic source options.\n")
        stream.write(json.dumps(example, indent=2) + "\n")
        stream.write("Pending means missing evidence, not confirmed vendor conflict or availability.\n")
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in ("events", "packages", "task1_inventory_hashes")}, indent=2))


if __name__ == "__main__":
    main()