"""Focused tests for the standalone read-only shadow adapter."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.engine.dynamic_package_service import generate_dynamic_packages
from backend.schemas.dynamic_package_request import DynamicPackageRequest
from research_data_v2.pp1_task3_shadow_integration.shadow_adapter import (
    assess_package, load_current_options,
)

REQUEST = {
    "event_type": "Wedding", "event_date": "2026-10-21",
    "start_time": "10:00", "end_time": "18:00",
    "city": "Philadelphia", "state": "PA", "guest_count": 50,
    "budget_lkr": 1000000, "required_services": ["Photography", "Decoration"],
    "top_k": 3,
}


class ShadowAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.options = load_current_options()
        cls.response = generate_dynamic_packages(DynamicPackageRequest.model_validate(REQUEST))
        cls.event = cls.response["event"]
        cls.packages = cls.response["generation"]["packages"]
        assert cls.packages, "Controlled request returned no packages"
        cls.package = cls.packages[0]

    def test_current_source_mapping(self):
        result = assess_package(self.event, self.package, self.options)
        self.assertEqual([], result["mapping_failures"])
        self.assertEqual(self.package["option_ids"], [x["option_id"] for x in result["resolved_options"]])
        self.assertEqual(self.package["vendor_ids"], [x["vendor_id"] for x in result["resolved_options"]])

    def test_unknown_pair_and_operational_evidence_stay_pending(self):
        result = assess_package(self.event, self.package, self.options)
        self.assertEqual("VERIFICATION_REQUIRED", result["status"])
        self.assertEqual([], result["confirmed_conflicts"])
        self.assertTrue(all(x["status"] == "VERIFICATION_REQUIRED" for x in result["pair_results"]))
        self.assertIn("resource_capacity", result["missing_evidence_categories"])
        self.assertIn("availability", result["missing_evidence_categories"])
        self.assertEqual("NOT_RUN_MISSING_INPUTS", result["operational_engine_status"])
        self.assertEqual("EXTERNAL_VERIFICATION_REQUIRED", result["venue_suitability"])

    def test_no_fixture_evidence_leaks(self):
        with patch("research_data_v2.pp1_task3_shadow_integration.shadow_adapter.lookup_pair",
                   wraps=__import__("research_data_v2.pp1_task2_conflict_engine.conflict_engine",
                                    fromlist=["lookup_pair"]).lookup_pair) as lookup:
            result = assess_package(self.event, self.package, self.options)
        self.assertTrue(lookup.call_args_list)
        self.assertTrue(all(call.args[3] == [] for call in lookup.call_args_list))
        self.assertTrue(all(not x["evidence_ids"] for x in result["pair_results"]))

    def test_deterministic_and_no_mutation(self):
        original = copy.deepcopy(self.package)
        first = assess_package(self.event, self.package, self.options)
        second = assess_package(self.event, self.package, self.options)
        self.assertEqual(first, second)
        self.assertEqual(original, self.package)

    def test_mapping_failure_does_not_invent_evidence(self):
        tampered = copy.deepcopy(self.package)
        tampered["vendor_ids"][0] = "UNMATCHED"
        result = assess_package(self.event, tampered, self.options)
        self.assertTrue(result["mapping_failures"])
        self.assertFalse(result["pair_results"])
        self.assertEqual("VERIFICATION_REQUIRED", result["status"])

    def test_fresh_requests_read_current_source_and_keep_ranking(self):
        from backend.engine import dynamic_package_service as service
        with patch.object(service, "load_service_options", wraps=service.load_service_options) as loader:
            a = service.generate_dynamic_packages(DynamicPackageRequest.model_validate(REQUEST))
            b = service.generate_dynamic_packages(DynamicPackageRequest.model_validate(REQUEST))
        self.assertEqual(2, loader.call_count)
        self.assertNotEqual(a["event_id"], b["event_id"])
        self.assertTrue(a["event_id"].startswith("USER-"))
        self.assertEqual("dynamic_user_request", a["generation_mode"])
        self.assertEqual(
            [(p["option_ids"], p["ranking_score"]) for p in a["generation"]["packages"]],
            [(p["option_ids"], p["ranking_score"]) for p in b["generation"]["packages"]],
        )
        before = copy.deepcopy(a["generation"]["packages"])
        for package in a["generation"]["packages"]:
            assess_package(a["event"], package, self.options)
        self.assertEqual(before, a["generation"]["packages"])

    def test_non_user_event_rejected(self):
        event = dict(self.event, event_id="SIMEVT-0000")
        with self.assertRaises(ValueError):
            assess_package(event, self.package, self.options)


if __name__ == "__main__":
    unittest.main()