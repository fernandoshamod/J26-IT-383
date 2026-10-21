"""Verify benchmark consistency and Task 1 source/model hashes."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    inventory = []
    with (ROOT / "research_data_v2/audit_2026-10-17_01/dataset_inventory.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        for row in csv.DictReader(stream):
            path = ROOT / row["path"]
            inventory.append({"path": row["path"], "exists": path.is_file(),
                              "matches_task1": path.is_file() and sha(path) == row["sha256"]})
    with (HERE / "benchmark_comparison.csv").open(newline="", encoding="utf-8") as stream:
        benchmark = list(csv.DictReader(stream))
    comparison_consistent = all(
        row["original_status"] == row["prototype_status"]
        and row["original_combinations_evaluated"] == row["prototype_combinations_evaluated"]
        and row["original_candidate_truncated"] == row["prototype_candidate_truncated"]
        and row["original_node_truncated"] == row["prototype_node_truncated"]
        for row in benchmark
    )
    monitored = [
        "backend/engine/dynamic_package_service.py",
        "backend/engine/candidate_selection.py",
        "backend/engine/bounded_package_generator.py",
        "backend/engine/dynamic_feasibility.py",
        "backend/engine/risk_signals.py",
        "backend/engine/service_compatibility.py",
        "backend/engine/package_explanations.py",
        "research_data_v2/pp1_task2_conflict_engine/conflict_engine.py",
        "research_data_v2/pp1_task3_shadow_integration/shadow_adapter.py",
    ]
    output = {
        "inventory_files_checked": len(inventory),
        "inventory_matches": sum(row["matches_task1"] for row in inventory),
        "inventory": inventory,
        "benchmark_pairs": len(benchmark),
        "benchmark_search_metadata_consistent": comparison_consistent,
        "monitored_existing_code_sha256": {name: sha(ROOT / name) for name in monitored},
        "note": "Code hashes are a post-run record; no pre-task code-hash baseline was available.",
    }
    with (HERE / "validation_results.json").open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2)
    if not all(row["matches_task1"] for row in inventory) or not comparison_consistent:
        raise SystemExit("Validation failed")
    print(json.dumps({key: output[key] for key in (
        "inventory_files_checked", "inventory_matches", "benchmark_pairs",
        "benchmark_search_metadata_consistent")}, indent=2))


if __name__ == "__main__":
    main()