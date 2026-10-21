"""Execute paired, request-time PlanoVision evaluation without editing production code.

Run from the project root: venv/Scripts/python.exe -m research_evaluation.run_evaluation
"""

import csv
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fastapi
import joblib
import numpy
import pandas as pd
import pydantic
import sklearn
import starlette
from fastapi.testclient import TestClient

from backend.main import app
from backend.engine import bounded_package_generator as generator
from backend.engine.package_data_loader import USD_TO_LKR
from research_evaluation.metrics import (
    aggregate, identity, mean, mean_rank_shift, overlap, rank_pool,
    recommendation_metrics,
)
from research_evaluation.model_audit import evaluate_model
from research_evaluation.render_reports import write_reports

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "research_evaluation"
TOP_K = 10
WEIGHTS = {
    "production": {"cost": 0.4, "risk": 0.4, "compatibility": 0.2},
    "cost_focused": {"cost": 0.7, "risk": 0.2, "compatibility": 0.1},
    "risk_focused": {"cost": 0.2, "risk": 0.7, "compatibility": 0.1},
    "compatibility_focused": {"cost": 0.2, "risk": 0.1, "compatibility": 0.7},
    "balanced": {"cost": 1 / 3, "risk": 1 / 3, "compatibility": 1 / 3},
}
INPUTS = [
    "hybrid_simulation_v1/synthetic_event_requirements.csv",
    "hybrid_simulation_v1/synthetic_service_options.csv",
    "hybrid_simulation_v1/real_vendor_profiles.csv",
    "data/cleaned/vendor_profiles_missingness_checked.csv",
    "vendor_risk_dataset.csv",
    "vendor_compatibility_matrix.csv",
    "models/vendor_risk_random_forest.pkl",
    "vendor_risk_model.pkl",
]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def input_manifest():
    manifest = {}
    for name in INPUTS:
        path = ROOT / name
        manifest[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        if path.suffix == ".csv":
            manifest[name]["rows"] = len(pd.read_csv(path, usecols=[0]))
    return manifest


def scenarios():
    source = pd.read_csv(ROOT / INPUTS[0])
    result = []
    for row in source.itertuples(index=False):
        required = [part.strip() for part in row.required_services.split(";")]
        result.append({
            "scenario_id": str(row.event_id),
            "origin": "existing_synthetic_event_template_redated_2099",
            "source_event_date": str(row.event_date),
            "payload": {
                "event_type": row.event_type,
                "event_date": pd.Timestamp(row.event_date).replace(year=2099).date().isoformat(),
                "start_time": str(row.start_time), "end_time": str(row.end_time),
                "city": row.city, "state": row.state,
                "guest_count": int(row.guest_count),
                "budget_lkr": round(float(row.budget) * USD_TO_LKR, 2),
                "required_services": required, "top_k": TOP_K,
            },
        })
    extras = [
        ("EVAL-PHILLY-MULTI", "Philadelphia", "PA", "Wedding",
         ["Catering", "Photography", "Decoration"], 10000000),
        ("EVAL-PHILLY-CORPORATE", "Philadelphia", "PA", "Corporate",
         ["Photography", "Decoration", "Event Planning"], 12000000),
        ("EVAL-PHILLY-UNKNOWN-PAIR", "Philadelphia", "PA", "Wedding",
         ["Event Planning", "Equipment Rental"], 10000000),
        ("EVAL-PHILLY-LOW-BUDGET", "Philadelphia", "PA", "Wedding",
         ["Photography", "Decoration"], 1),
        ("EVAL-UNSUPPORTED-LOCATION", "Nowhere", "ZZ", "Wedding",
         ["Photography"], 1000000),
    ]
    for scenario_id, city, state, event_type, services, budget in extras:
        result.append({
            "scenario_id": scenario_id,
            "origin": "additional_explicit_synthetic_test_scenario",
            "source_event_date": None,
            "payload": {
                "event_type": event_type, "event_date": "2027-06-20",
                "start_time": "10:00", "end_time": "16:00",
                "city": city, "state": state, "guest_count": 50,
                "budget_lkr": budget, "required_services": services, "top_k": TOP_K,
            },
        })
    return result


def snapshot(package, budget):
    return {
        "option_ids": list(package["option_ids"]),
        "vendor_ids": list(package["vendor_ids"]),
        "total_cost_lkr": package["total_cost_lkr"],
        "budget_lkr": budget,
        "risk": package["risk"],
        "compatibility": package["compatibility"],
        "feasibility_status": package["feasibility"]["final_status"],
        "production_score": package["ranking_score"],
        "service_coverage": list(package["service_coverage"]),
    }


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run():
    actual = {
        "max_candidates_per_service": generator._positive_limit(
            "PLANOVISION_MAX_CANDIDATES_PER_SERVICE", 12),
        "max_search_nodes": generator._positive_limit(
            "PLANOVISION_MAX_SEARCH_NODES", 5000),
        "production_weights": generator._ranking_weights(),
    }
    expected = {
        "max_candidates_per_service": 12,
        "max_search_nodes": 5000,
        "production_weights": WEIGHTS["production"],
    }
    if actual != expected:
        raise ValueError(f"Evaluation requires production defaults; observed {actual}")
    begun = time.perf_counter()
    before = input_manifest()
    all_scenarios = scenarios()
    model_result = evaluate_model()
    client = TestClient(app)
    # Warm the model and route before measured requests; same input is measured again.
    client.post("/api/packages/generate-dynamic", json=all_scenarios[0]["payload"])
    event_rows, package_rows, comparison_rows, sensitivity_rows = [], [], [], []
    for index, scenario in enumerate(all_scenarios, 1):
        payload = scenario["payload"]
        started = time.perf_counter()
        response = client.post("/api/packages/generate-dynamic", json=payload)
        elapsed_ms = (time.perf_counter() - started) * 1000
        body = response.json()
        generation = body.get("generation", {})
        packages = generation.get("packages", [])
        search = generation.get("search", {})
        pool = []
        if response.status_code == 200:
            original = generator.explain_package

            def capture(package):
                pool.append(snapshot(package, payload["budget_lkr"]))
                return original(package)

            with patch.object(generator, "explain_package", side_effect=capture):
                replay = client.post("/api/packages/generate-dynamic", json=payload)
            if replay.status_code != 200:
                raise AssertionError(f"Replay failed for {scenario['scenario_id']}: {replay.status_code}")
            replay_generation = replay.json()["generation"]
            if (generation["total_generated"] != replay_generation["total_generated"]
                    or generation["search"]["nodes_visited"] != replay_generation["search"]["nodes_visited"]
                    or len(pool) != generation["feasible_combinations_seen"]):
                raise AssertionError(f"Search pool changed on replay: {scenario['scenario_id']}")
            proposed = rank_pool(pool, "multi_factor", TOP_K, WEIGHTS["production"])
            api_ids = [tuple(pkg["option_ids"]) for pkg in packages]
            if [identity(pkg) for pkg in proposed] != api_ids:
                raise AssertionError(f"Captured pool does not reproduce API ranking: {scenario['scenario_id']}")
            baseline = rank_pool(pool, "cost_only", TOP_K)
            base_stats, proposed_stats = recommendation_metrics(baseline), recommendation_metrics(proposed)
            overlap_value = overlap(baseline, proposed)
            comparison_rows.append({
                "scenario_id": scenario["scenario_id"], "candidate_pool_size": len(pool),
                "baseline_top_k_option_ids": json.dumps([p["option_ids"] for p in baseline]),
                "proposed_top_k_option_ids": json.dumps([p["option_ids"] for p in proposed]),
                "baseline_mean_cost_lkr": base_stats["mean_cost_lkr"],
                "proposed_mean_cost_lkr": proposed_stats["mean_cost_lkr"],
                "cost_difference_lkr": (
                    proposed_stats["mean_cost_lkr"] - base_stats["mean_cost_lkr"]
                    if baseline and proposed else None),
                "baseline_mean_risk_score_known": base_stats["mean_risk_score_known"],
                "proposed_mean_risk_score_known": proposed_stats["mean_risk_score_known"],
                "baseline_mean_compatibility_score_known": base_stats["mean_compatibility_score_known"],
                "proposed_mean_compatibility_score_known": proposed_stats["mean_compatibility_score_known"],
                "baseline_vendor_diversity": base_stats["vendor_diversity"],
                "proposed_vendor_diversity": proposed_stats["vendor_diversity"],
                "top_k_overlap": overlap_value,
                "mean_absolute_rank_shift": mean_rank_shift(baseline, proposed),
            })
            for name, weights in WEIGHTS.items():
                ranked = rank_pool(pool, "multi_factor", TOP_K, weights)
                stats = recommendation_metrics(ranked)
                sensitivity_rows.append({
                    "scenario_id": scenario["scenario_id"], "configuration": name,
                    "weights": json.dumps(weights, sort_keys=True),
                    "candidate_pool_size": len(pool),
                    "top_k_option_ids": json.dumps([p["option_ids"] for p in ranked]),
                    "top_k_overlap_vs_production": overlap(proposed, ranked),
                    "mean_absolute_rank_shift_vs_production": mean_rank_shift(proposed, ranked),
                    **stats,
                })
        else:
            comparison_rows.append({
                "scenario_id": scenario["scenario_id"], "candidate_pool_size": 0,
                "baseline_top_k_option_ids": "[]", "proposed_top_k_option_ids": "[]",
                "baseline_mean_cost_lkr": None, "proposed_mean_cost_lkr": None,
                "cost_difference_lkr": None, "baseline_mean_risk_score_known": None,
                "proposed_mean_risk_score_known": None,
                "baseline_mean_compatibility_score_known": None,
                "proposed_mean_compatibility_score_known": None,
                "baseline_vendor_diversity": None, "proposed_vendor_diversity": None,
                "top_k_overlap": None, "mean_absolute_rank_shift": None,
            })
            for name, weights in WEIGHTS.items():
                sensitivity_rows.append({
                    "scenario_id": scenario["scenario_id"], "configuration": name,
                    "weights": json.dumps(weights, sort_keys=True),
                    "candidate_pool_size": 0, "top_k_option_ids": "[]",
                    "top_k_overlap_vs_production": None,
                    "mean_absolute_rank_shift_vs_production": None,
                    **recommendation_metrics([]),
                })
        event_row = {
            "scenario_id": scenario["scenario_id"], "scenario_origin": scenario["origin"],
            "source_event_date": scenario["source_event_date"],
            "event_date": payload["event_date"],
            "event_type": payload["event_type"], "city": payload["city"], "state": payload["state"],
            "required_services": payload["required_services"],
            "service_count": len(payload["required_services"]), "budget_lkr": payload["budget_lkr"],
            "http_status": response.status_code, "generation_status": generation.get("status"),
            "recommended_count": len(packages), "execution_ms": elapsed_ms,
            "candidate_counts": generation.get("candidate_counts", {}),
            "selected_candidate_counts": generation.get("selected_candidate_counts", {}),
            "combinations_evaluated": generation.get("total_generated", 0),
            "nodes_visited": search.get("nodes_visited", 0),
            "candidate_limit_reached": search.get("candidate_limit_reached", False),
            "node_limit_reached": search.get("node_limit_reached", False),
            "feasibility_counts": generation.get("feasibility_counts", {}),
            "error": body.get("detail") if response.status_code != 200 else None,
        }
        event_rows.append(event_row)
        if not packages:
            package_rows.append({**event_row, "package_rank": None,
                                 "option_ids": [], "vendor_ids": [], "vendor_count": 0,
                                 "known_risk_vendor_count": 0, "coverage_exact": None,
                                 "budget_feasible": None, "total_cost_lkr": None,
                                 "risk_score": None, "compatibility_score": None,
                                 "compatibility_status": None, "feasibility_status": None})
        for package in packages:
            risk = package["risk"]
            package_rows.append({
                **event_row, "package_rank": package["rank"],
                "option_ids": package["option_ids"], "vendor_ids": package["vendor_ids"],
                "vendor_count": risk["total_vendor_count"],
                "known_risk_vendor_count": risk["known_vendor_count"],
                "coverage_exact": set(package["service_coverage"]) == set(payload["required_services"])
                                  and len(package["service_coverage"]) == len(payload["required_services"]),
                "budget_feasible": package["total_cost_lkr"] <= payload["budget_lkr"],
                "total_cost_lkr": package["total_cost_lkr"],
                "risk_score": risk["mean_rule_risk_score"],
                "compatibility_score": package["compatibility"]["score"],
                "compatibility_status": package["compatibility"]["status"],
                "feasibility_status": package["feasibility"]["final_status"],
            })
        print(f"{index}/{len(all_scenarios)} {scenario['scenario_id']} HTTP {response.status_code} "
              f"{len(packages)} recommendations {elapsed_ms:.1f} ms", flush=True)

    after = input_manifest()
    if before != after:
        raise AssertionError("Source dataset or model artifact hashes changed during evaluation")
    aggregate_results = aggregate(event_rows, package_rows, comparison_rows)
    summary = {
        "evaluation_date_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_execution_seconds": time.perf_counter() - begun,
        "method": "Measured FastAPI TestClient requests; identical feasible package pool captured by evaluation-only explanation hook and reranked.",
        "production_code_modified": False,
        "scenario_counts": {
            "existing_synthetic_event_templates": 30,
            "additional_explicit_synthetic_scenarios": len(all_scenarios) - 30,
            "total": len(all_scenarios),
        },
        "input_manifest": before,
        "runtime": {
            "python": platform.python_version(), "pandas": pd.__version__,
            "numpy": numpy.__version__, "scikit_learn": sklearn.__version__,
            "fastapi": fastapi.__version__, "pydantic": pydantic.__version__,
            "starlette": starlette.__version__, "joblib": joblib.__version__,
        },
        "configuration": {
            "top_k": TOP_K, "max_candidates_per_service": 12,
            "max_search_nodes": 5000, "production_weights": WEIGHTS["production"],
            "sensitivity_weights": WEIGHTS, "simulation_seed": 42,
            "model_split_seed": 42,
            "currency": "LKR", "synthetic_usd_to_lkr": USD_TO_LKR,
            "measured_request_warmups": 1,
        },
        "metrics": aggregate_results,
        "model_evaluation": model_result,
    }
    # Tables are written before reports, which quote only calculated values.
    package_fields = list(package_rows[0])
    package_csv_rows = []
    for row in package_rows:
        encoded = dict(row)
        for key in ("required_services", "candidate_counts", "selected_candidate_counts",
                    "feasibility_counts", "option_ids", "vendor_ids"):
            encoded[key] = json.dumps(encoded[key], sort_keys=True)
        package_csv_rows.append(encoded)
    write_csv(OUTPUT / "evaluation_results.csv", package_csv_rows, package_fields)
    write_csv(OUTPUT / "baseline_comparison.csv", comparison_rows, list(comparison_rows[0]))
    write_csv(OUTPUT / "ranking_sensitivity.csv", sensitivity_rows, list(sensitivity_rows[0]))
    (OUTPUT / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_reports(summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run()["metrics"], indent=2))
