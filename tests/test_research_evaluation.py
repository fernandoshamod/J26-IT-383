"""Focused tests for evaluation arithmetic, fairness and production boundaries."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.engine.bounded_package_generator import _ranking_weights
from research_evaluation.metrics import (
    aggregate, mean_rank_shift, overlap, rank_pool, recommendation_metrics,
)
from research_evaluation.run_evaluation import scenarios, WEIGHTS, run


def package(option_id, vendor, cost, score=None, compatibility=None):
    return {
        "option_ids": [option_id], "vendor_ids": [vendor],
        "total_cost_lkr": cost, "budget_lkr": 1000,
        "risk": {"mean_rule_risk_score": score,
                 "known_vendor_count": int(score is not None), "total_vendor_count": 1},
        "compatibility": {"score": compatibility,
                          "status": "complete" if compatibility is not None else "not_applicable"},
        "feasibility_status": "VERIFICATION_REQUIRED",
    }


class ResearchEvaluationTests(unittest.TestCase):
    def test_empty_results_are_undefined_not_zero(self):
        result = aggregate([], [], [])
        self.assertIsNone(result["request_success_rate"])
        self.assertIsNone(result["budget_feasible_package_rate"])
        self.assertIsNone(result["mean_vendor_risk_score_known"])
        self.assertIsNone(result["baseline_proposed_top_k_overlap_mean"])
        self.assertIsNone(recommendation_metrics([])["vendor_diversity"])

    def test_metric_denominators_and_missing_signals(self):
        events = [{"http_status": 200, "recommended_count": 2, "execution_ms": 10,
                   "candidate_counts": {"Photography": 3},
                   "candidate_limit_reached": False, "node_limit_reached": False,
                   "combinations_evaluated": 4},
                  {"http_status": 422, "recommended_count": 0, "execution_ms": 20,
                   "candidate_counts": {}, "candidate_limit_reached": False,
                   "node_limit_reached": False, "combinations_evaluated": 0}]
        packages = [
            {"package_rank": 1, "risk_score": 80, "compatibility_score": 85,
             "vendor_count": 2, "known_risk_vendor_count": 2, "service_count": 2,
             "compatibility_status": "complete", "feasibility_status": "VERIFICATION_REQUIRED",
             "coverage_exact": True, "budget_feasible": True, "vendor_ids": ["a", "b"]},
            {"package_rank": 2, "risk_score": None, "compatibility_score": None,
             "vendor_count": 2, "known_risk_vendor_count": 1, "service_count": 2,
             "compatibility_status": "unknown", "feasibility_status": "VERIFICATION_REQUIRED",
             "coverage_exact": True, "budget_feasible": True, "vendor_ids": ["a", "c"]},
        ]
        result = aggregate(events, packages, [])
        self.assertEqual(result["request_success_rate"], 0.5)
        self.assertEqual(result["average_recommended_packages_per_event"], 1)
        self.assertEqual(result["missing_risk_fraction"], 0.25)
        self.assertEqual(result["mean_vendor_risk_score_known"], 80)
        self.assertEqual(result["unknown_compatibility_fraction"], 0.5)
        self.assertEqual(result["vendor_diversity_top_k"], 0.75)
        self.assertEqual(result["evaluated_package_combinations"], 4)
        self.assertEqual(result["median_execution_ms"], 15)

    def test_cost_baseline_and_proposed_share_pool(self):
        pool = [package("cheap", "a", 100, 10),
                package("quality", "b", 200, 100)]
        baseline = rank_pool(pool, "cost_only", 2)
        proposed = rank_pool(pool, "multi_factor", 2, WEIGHTS["production"])
        self.assertEqual(len(baseline), len(proposed))
        self.assertEqual({id(item) for item in baseline}, {id(item) for item in proposed})
        self.assertEqual(baseline[0]["option_ids"], ["cheap"])
        self.assertEqual(proposed[0]["option_ids"], ["quality"])
        self.assertEqual(overlap(baseline[:1], proposed[:1]), 0)
        self.assertEqual(mean_rank_shift(baseline, proposed), 1)

    def test_missing_risk_and_compatibility_do_not_become_zero(self):
        pool = [package("cheap", "a", 100),
                package("expensive", "b", 200)]
        ranked = rank_pool(pool, "multi_factor", 2, WEIGHTS["production"])
        self.assertEqual(ranked[0]["option_ids"], ["cheap"])
        metrics = recommendation_metrics(pool)
        self.assertIsNone(metrics["mean_risk_score_known"])
        self.assertIsNone(metrics["mean_compatibility_score_known"])
        self.assertEqual(metrics["missing_risk_fraction"], 1)

    def test_repeatable_scenarios_and_caps(self):
        first, second = scenarios(), scenarios()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 35)
        self.assertEqual(first[0]["payload"]["event_date"], "2099-01-01")
        self.assertEqual(first[0]["source_event_date"], "2027-01-01")
        self.assertEqual(first[-1]["payload"]["city"], "Nowhere")
        self.assertEqual(_ranking_weights(), WEIGHTS["production"])

    def test_rejects_unrecorded_search_limit_override(self):
        with patch.dict("os.environ", {"PLANOVISION_MAX_SEARCH_NODES": "1"}):
            with self.assertRaisesRegex(ValueError, "production defaults"):
                run()

    def test_unsupported_and_insufficient_requests_preserve_api(self):
        client = TestClient(app)
        unsupported = next(item for item in scenarios()
                           if item["scenario_id"] == "EVAL-UNSUPPORTED-LOCATION")
        budget = next(item for item in scenarios()
                      if item["scenario_id"] == "EVAL-PHILLY-LOW-BUDGET")
        bad = client.post("/api/packages/generate-dynamic", json=unsupported["payload"])
        low = client.post("/api/packages/generate-dynamic", json=budget["payload"])
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(low.status_code, 200)
        self.assertEqual(low.json()["generation"]["status"], "no_budget_feasible_combinations")
        self.assertIn("/api/packages/generate", client.app.openapi()["paths"])
        self.assertIn("/api/feasibility/validate", client.app.openapi()["paths"])


if __name__ == "__main__":
    unittest.main()
