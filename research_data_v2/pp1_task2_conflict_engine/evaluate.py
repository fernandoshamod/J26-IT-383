"""Run controlled synthetic evaluation; writes only to this directory on request."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns

from conflict_engine import COMPATIBLE, CONFLICT, PENDING, evaluate_case

HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "fixtures.json"


def evaluate() -> dict:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if fixture["evidence_class"] != "SYNTHETIC_TEST":
        raise ValueError("Only controlled synthetic fixtures are accepted")
    results = []
    for case in fixture["cases"]:
        start = perf_counter_ns()
        actual = evaluate_case(case)
        duration_ms = (perf_counter_ns() - start) / 1_000_000
        results.append({
            "case_id": case["case_id"], "expected": case["expected_status"],
            "actual": actual["status"], "correct": actual["status"] == case["expected_status"],
            "expected_conflict": case["expected_conflict"],
            "actual_conflict": actual["status"] == CONFLICT,
            "conflict_checks": actual["conflict_count"],
            "pending_checks": actual["pending_count"],
            "execution_ms": duration_ms,
        })
    known = [row for row in results if row["expected"] in {CONFLICT, COMPATIBLE}]
    tp = sum(row["expected"] == CONFLICT and row["actual"] == CONFLICT for row in known)
    fn = sum(row["expected"] == CONFLICT and row["actual"] != CONFLICT for row in known)
    fp = sum(row["expected"] == COMPATIBLE and row["actual"] == CONFLICT for row in known)
    tn = sum(row["expected"] == COMPATIBLE and row["actual"] != CONFLICT for row in known)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if (
        precision is not None and recall is not None and precision + recall
    ) else None
    times = [row["execution_ms"] for row in results]
    return {
        "evaluation_type": "SYNTHETIC_TEST",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "fixture_sha256": hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256((HERE / "conflict_engine.py").read_bytes()).hexdigest(),
        "case_count": len(results),
        "correct_three_way_statuses": sum(row["correct"] for row in results),
        "known_binary_cases": len(known),
        "unknown_expected_cases": sum(row["expected"] == PENDING for row in results),
        "pending_predicted_cases": sum(row["actual"] == PENDING for row in results),
        "correctly_identified_conflicts": tp,
        "missed_conflicts": fn,
        "false_conflict_warnings": fp,
        "correct_nonconflicts": tn,
        "conflict_precision": precision,
        "conflict_recall": recall,
        "conflict_f1": f1,
        "total_case_execution_ms": sum(times),
        "mean_case_execution_ms": statistics.mean(times) if times else None,
        "median_case_execution_ms": statistics.median(times) if times else None,
        "metric_policy": (
            "Conflict is positive. Compatible is known negative. Expected pending "
            "cases are excluded from binary precision/recall/F1; undefined ratios are null. "
            "Timing is local in-process fixture evaluation only."
        ),
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-results", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.write_results:
        target = HERE / "evaluation_results.json"
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(f"Saved {target}")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
