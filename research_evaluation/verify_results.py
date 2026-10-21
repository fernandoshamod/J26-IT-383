"""Verify saved evaluation claims against CSV rows and unchanged source hashes."""

import csv
import json
import math
from pathlib import Path

from research_evaluation.metrics import aggregate
from research_evaluation.run_evaluation import input_manifest

OUTPUT = Path(__file__).resolve().parent


def read_csv(name):
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def optional_float(value):
    return None if value == "" else float(value)


def assert_same(expected, actual, location="metrics"):
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            raise AssertionError(f"{location}: key mismatch")
        for key in expected:
            assert_same(expected[key], actual[key], f"{location}.{key}")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-9):
            raise AssertionError(f"{location}: expected {expected}, got {actual}")
    elif expected != actual:
        raise AssertionError(f"{location}: expected {expected}, got {actual}")


def verify():
    summary = json.loads((OUTPUT / "evaluation_summary.json").read_text(encoding="utf-8"))
    rows = read_csv("evaluation_results.csv")
    baseline = read_csv("baseline_comparison.csv")
    sensitivity = read_csv("ranking_sensitivity.csv")
    event_rows = []
    package_rows = []
    seen = set()
    for row in rows:
        scenario = row["scenario_id"]
        if scenario not in seen:
            event_rows.append({
                "http_status": int(row["http_status"]),
                "recommended_count": int(row["recommended_count"]),
                "execution_ms": float(row["execution_ms"]),
                "candidate_counts": json.loads(row["candidate_counts"]),
                "candidate_limit_reached": row["candidate_limit_reached"] == "True",
                "node_limit_reached": row["node_limit_reached"] == "True",
                "combinations_evaluated": int(row["combinations_evaluated"]),
            })
            seen.add(scenario)
        if row["package_rank"]:
            package_rows.append({
                "package_rank": int(row["package_rank"]),
                "risk_score": optional_float(row["risk_score"]),
                "compatibility_score": optional_float(row["compatibility_score"]),
                "vendor_count": int(row["vendor_count"]),
                "known_risk_vendor_count": int(row["known_risk_vendor_count"]),
                "service_count": int(row["service_count"]),
                "compatibility_status": row["compatibility_status"],
                "feasibility_status": row["feasibility_status"],
                "coverage_exact": row["coverage_exact"] == "True",
                "budget_feasible": row["budget_feasible"] == "True",
                "vendor_ids": json.loads(row["vendor_ids"]),
            })
    baseline_rows = [{
        "top_k_overlap": optional_float(row["top_k_overlap"]),
        "cost_difference_lkr": optional_float(row["cost_difference_lkr"]),
        "mean_absolute_rank_shift": optional_float(row["mean_absolute_rank_shift"]),
    } for row in baseline]
    expected = aggregate(event_rows, package_rows, baseline_rows)
    assert_same(expected, summary["metrics"])
    if len(event_rows) != summary["scenario_counts"]["total"]:
        raise AssertionError("Event count mismatch")
    if len(baseline) != len(event_rows):
        raise AssertionError("Baseline row count mismatch")
    if len(sensitivity) != len(event_rows) * len(summary["configuration"]["sensitivity_weights"]):
        raise AssertionError("Sensitivity row count mismatch")
    if input_manifest() != summary["input_manifest"]:
        raise AssertionError("Source/model file changed since evaluation")
    return {"events": len(event_rows), "recommendations": len(package_rows),
            "baseline_rows": len(baseline), "sensitivity_rows": len(sensitivity),
            "source_and_model_hashes_match": True, "metrics_match": True}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
