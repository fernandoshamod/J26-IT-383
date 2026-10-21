"""Alternating-order, unprofiled comparison of full dynamic requests."""
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend.engine.risk_signals import verified_model
from research_data_v2.pp1_task4_performance.baseline_profile import SCENARIOS, run_one
from research_data_v2.pp1_task4_performance.optimized_prototype import select_candidates_once


def main():
    verified_model()  # Warm the unchanged model loader for both approaches.
    rows = []
    for scenario in SCENARIOS:
        for repeat in range(2):
            order = ["original", "prototype"] if repeat == 0 else ["prototype", "original"]
            pair = {}
            for approach in order:
                result, _ = run_one(
                    scenario,
                    optimized_selector=select_candidates_once if approach == "prototype" else None,
                    profile=False,
                )
                pair[approach] = result
                print(scenario, repeat + 1, approach, result["elapsed_ms"], flush=True)
            original, prototype = pair["original"], pair["prototype"]
            rows.append({
                "scenario": scenario, "repeat": repeat + 1,
                "original_full_ms": original["elapsed_ms"],
                "prototype_full_ms": prototype["elapsed_ms"],
                "improvement_percent": round(
                    100 * (original["elapsed_ms"] - prototype["elapsed_ms"])
                    / original["elapsed_ms"], 3),
                "original_selection_ms": original["stage_ms"]["candidate_selection"],
                "prototype_selection_ms": prototype["stage_ms"]["candidate_selection"],
                "original_risk_ms": original["stage_ms"]["risk_inference_including_model_verification"],
                "prototype_risk_ms": prototype["stage_ms"]["risk_inference_including_model_verification"],
                "original_status": original["status"],
                "prototype_status": prototype["status"],
                "original_combinations_evaluated": original["combinations_evaluated"],
                "prototype_combinations_evaluated": prototype["combinations_evaluated"],
                "original_candidate_truncated": original["search"]["candidate_limit_reached"],
                "prototype_candidate_truncated": prototype["search"]["candidate_limit_reached"],
                "original_node_truncated": original["search"]["node_limit_reached"],
                "prototype_node_truncated": prototype["search"]["node_limit_reached"],
            })
    with (HERE / "benchmark_comparison.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for scenario in SCENARIOS:
        subset = [r for r in rows if r["scenario"] == scenario]
        print(scenario, {
            "original_median_ms": median(r["original_full_ms"] for r in subset),
            "prototype_median_ms": median(r["prototype_full_ms"] for r in subset),
            "original_range_ms": [min(r["original_full_ms"] for r in subset),
                                  max(r["original_full_ms"] for r in subset)],
            "prototype_range_ms": [min(r["prototype_full_ms"] for r in subset),
                                   max(r["prototype_full_ms"] for r in subset)],
        })


if __name__ == "__main__":
    main()