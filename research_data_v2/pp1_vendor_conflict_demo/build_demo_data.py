"""Build a static research-only frontend snapshot from existing engine fixtures."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from research_data_v2.pp1_task2_conflict_engine.conflict_engine import evaluate_case

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "research_data_v2/pp1_task2_conflict_engine/fixtures.json"
MATRIX = ROOT / "vendor_compatibility_matrix.csv"
OUTPUT = ROOT / "frontend/src/data/vendor_conflict_research.json"
CASE_IDS = ("compatible_pair", "equipment_insufficient", "unknown_pair")
LABELS = {
    "compatible_pair": "No conflict detected within supplied simulated checks",
    "equipment_insufficient": "Conflict detected in supplied simulated evidence",
    "unknown_pair": "Verification required because evidence is missing",
}


def build_snapshot() -> dict:
    fixtures = {item["case_id"]: item for item in json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]}
    with MATRIX.open(newline="", encoding="utf-8-sig") as stream:
        rules = {tuple(sorted((row["service_1"], row["service_2"]))): float(row["base_score"])
                 for row in csv.DictReader(stream)}
    examples = []
    for case_id in CASE_IDS:
        case = fixtures[case_id]
        result = evaluate_case(case)
        assignments = case["assignments"]
        categories = [item["service_category"] for item in assignments]
        rule = rules.get(tuple(sorted(categories))) if len(categories) == 2 else None
        pair = result["pair_results"][0] if len(result["pair_results"]) == 1 else None
        examples.append({
            "fixture_id": case_id,
            "label": LABELS[case_id],
            "event_id": case["event"]["event_id"],
            "vendors": [{"vendor_id": item["vendor_id"], "option_id": item["option_id"],
                         "service_category": item["service_category"]} for item in assignments],
            "service_categories": categories,
            "category_score": rule,
            "category_score_source": "vendor_compatibility_matrix.csv" if rule is not None else None,
            "operational_status": result["status"],
            "reason": result["explanation"],
            "pair_evidence_status": pair["status"] if pair else "VERIFICATION_REQUIRED",
            "pair_evidence_ids": pair["evidence_ids"] if pair else [],
            "conflict_count": result["conflict_count"],
            "pending_count": result["pending_count"],
            "evidence_source": "SYNTHETIC TEST DATA",
            "real_world_availability": "NOT VERIFIED",
            "real_world_collaboration_history": "UNKNOWN",
            "venue_suitability": result["venue_suitability"],
            "is_real_world_feasible": result["is_real_world_feasible"],
        })
    return {"title": "Vendor-specific conflict research demonstration",
            "fixture_source": "research_data_v2/pp1_task2_conflict_engine/fixtures.json",
            "engine_source": "research_data_v2/pp1_task2_conflict_engine/conflict_engine.py",
            "matrix_source": "vendor_compatibility_matrix.csv",
            "examples": examples}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write only the isolated frontend snapshot")
    parser.add_argument("--check", action="store_true", help="Check the frontend snapshot matches current inputs")
    args = parser.parse_args()
    expected = json.dumps(build_snapshot(), indent=2, ensure_ascii=False) + "\n"
    if args.write:
        OUTPUT.write_text(expected, encoding="utf-8")
        print(f"Wrote {OUTPUT}")
    elif args.check:
        assert OUTPUT.read_text(encoding="utf-8") == expected, "Research snapshot differs from fixtures, engine, or matrix"
        print("Research snapshot matches conflict engine, fixtures, and matrix")
    else:
        print(expected, end="")


if __name__ == "__main__":
    main()
