"""Focused tests for standalone synthetic vendor conflict evidence."""
from __future__ import annotations

import copy
import csv
import json
import unittest
from pathlib import Path

from conflict_engine import COMPATIBLE, CONFLICT, PENDING, evaluate_case, lookup_pair

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))


class ConflictEngineTests(unittest.TestCase):
    def case(self, name: str) -> dict:
        return copy.deepcopy(next(item for item in FIXTURE["cases"]
                                  if item["case_id"] == name))

    def test_all_independent_fixture_labels(self):
        self.assertEqual(len(FIXTURE["cases"]), 12)
        for case in FIXTURE["cases"]:
            with self.subTest(case=case["case_id"]):
                result = evaluate_case(case)
                self.assertEqual(result["status"], case["expected_status"])
                self.assertEqual(bool(result["conflict_count"]), case["expected_conflict"])
                self.assertEqual(result["venue_suitability"], PENDING)
                self.assertFalse(result["is_real_world_feasible"])

    def test_pair_lookup_is_symmetric(self):
        case = self.case("compatible_pair")
        first, second = (item["vendor_id"] for item in case["assignments"])
        forward = lookup_pair(first, second, case["event"]["event_id"],
                              case["pair_evidence"])
        reverse = lookup_pair(second, first, case["event"]["event_id"],
                              case["pair_evidence"])
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["status"], COMPATIBLE)
        self.assertFalse(forward["is_real_world_collaboration_confirmed"])

    def test_unrelated_sample_event_evidence_is_ignored(self):
        case = self.case("compatible_pair")
        case["pair_evidence"][0]["event_id"] = "SIMEVT-0002"
        self.assertEqual(evaluate_case(case)["status"], PENDING)

    def test_category_rule_is_not_vendor_pair_evidence(self):
        case = self.case("compatible_pair")
        case["pair_evidence"][0]["evidence_type"] = "category_rule"
        self.assertEqual(evaluate_case(case)["status"], PENDING)

    def test_contradiction_is_pending(self):
        result = evaluate_case(self.case("contradictory_pair"))
        self.assertEqual(result["status"], PENDING)
        self.assertIn("contradicts", result["pair_results"][0]["reason"])

    def test_shared_resource_peak_exceeds_limit(self):
        result = evaluate_case(self.case("equipment_insufficient"))
        checks = {item["code"]: item for item in result["checks"]}
        self.assertEqual(checks["resource:equipment:shared-camera"]["status"],
                         CONFLICT)
        self.assertIn("peak demand 2", checks["resource:equipment:shared-camera"]["message"])

    def test_missing_capacity_stays_pending(self):
        result = evaluate_case(self.case("missing_resource_capacity"))
        self.assertEqual(result["status"], PENDING)
        self.assertTrue(any(item["code"].startswith("resource:")
                            and item["status"] == PENDING for item in result["checks"]))

    def test_unknown_availability_stays_pending(self):
        result = evaluate_case(self.case("unknown_availability"))
        self.assertEqual(result["status"], PENDING)
        self.assertTrue(any(item["code"].startswith("availability:")
                            and item["status"] == PENDING for item in result["checks"]))

    def test_multiple_conflicts_are_retained(self):
        result = evaluate_case(self.case("multiple_conflicts"))
        self.assertGreaterEqual(result["conflict_count"], 2)
        self.assertEqual(result["status"], CONFLICT)

    def test_nonoverlap_does_not_conflict(self):
        self.assertEqual(evaluate_case(self.case("nonoverlap"))["status"], COMPATIBLE)

    def test_setup_and_teardown_overlap(self):
        for name in ("setup_overlap", "teardown_overlap"):
            with self.subTest(name=name):
                result = evaluate_case(self.case(name))
                self.assertTrue(any(item["code"].startswith("setup_teardown:")
                                    and item["status"] == CONFLICT
                                    for item in result["checks"]))

    def test_missing_same_vendor_duration_is_pending(self):
        case = self.case("nonoverlap")
        case["assignments"][0]["teardown_minutes"] = None
        self.assertEqual(evaluate_case(case)["status"], PENDING)

    def test_availability_interval_must_cover_service(self):
        case = self.case("compatible_pair")
        case["assignments"][0]["availability"]["end_at"] = "2026-10-21T13:00:00-04:00"
        self.assertEqual(evaluate_case(case)["status"], PENDING)

    def test_exclusive_setup_crew_conflicts_even_if_service_multitask_is_allowed(self):
        case = self.case("same_vendor_overlap")
        for item in case["assignments"]:
            item["can_multitask"] = True
        result = evaluate_case(case)
        self.assertEqual(result["status"], CONFLICT)
        self.assertTrue(any(check["code"].startswith("setup_teardown:")
                            and check["status"] == CONFLICT for check in result["checks"]))
    def test_unverified_public_pair_claim_is_pending(self):
        case = self.case("compatible_pair")
        record = case["pair_evidence"][0]
        record["evidence_class"] = "REAL_PUBLIC"
        record["evidence_type"] = "direct_pair_observation"
        record["verification_status"] = "unverified"
        record["source_uri"] = "https://example.invalid/unverified-claim"
        self.assertEqual(evaluate_case(case)["status"], PENDING)

    def test_evaluation_denominators_and_metrics(self):
        from evaluate import evaluate
        result = evaluate()
        self.assertEqual(result["case_count"], 12)
        self.assertEqual(result["known_binary_cases"], 8)
        self.assertEqual(result["unknown_expected_cases"], 4)
        self.assertEqual(result["correctly_identified_conflicts"], 6)
        self.assertEqual(result["missed_conflicts"], 0)
        self.assertEqual(result["false_conflict_warnings"], 0)
        self.assertEqual(result["conflict_precision"], 1.0)
        self.assertEqual(result["conflict_recall"], 1.0)
        self.assertEqual(result["conflict_f1"], 1.0)
    def test_deterministic_output(self):
        case = self.case("compatible_pair")
        self.assertEqual(evaluate_case(case), evaluate_case(copy.deepcopy(case)))

    def test_reject_invalid_assignment_and_resource(self):
        case = self.case("compatible_pair")
        case["assignments"][1]["option_id"] = case["assignments"][0]["option_id"]
        with self.assertRaises(ValueError):
            evaluate_case(case)
        case = self.case("equipment_insufficient")
        case["assignments"][0]["resources"][0]["resource_id"] = "venue:power"
        with self.assertRaises(ValueError):
            evaluate_case(case)

    def test_fixture_source_ids_match_current_options(self):
        wanted = {
            "SIMOPT-000057-B": ("yRO9jF-YqiMwq5ja96GdTg", "Photography"),
            "SIMOPT-000115-B": ("gziMakTc9EnZszDdTn9f8Q", "Decoration"),
        }
        found = {}
        with (ROOT / "hybrid_simulation_v1" / "synthetic_service_options.csv").open(
                newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                if row["service_option_id"] in wanted:
                    found[row["service_option_id"]] = (
                        row["business_id"], row["service_category"])
        self.assertEqual(found, wanted)


if __name__ == "__main__":
    unittest.main()
