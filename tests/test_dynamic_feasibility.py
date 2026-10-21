"""USER-event feasibility and bounded recommendation checks."""

import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.engine.dynamic_feasibility import validate_dynamic_package
from backend.engine.bounded_package_generator import generate_bounded_packages


def event(**overrides):
    value = {
        "event_id": "USER-TEST", "event_type": "Wedding",
        "event_date": "2099-03-20", "start_time": "10:00",
        "end_time": "16:00", "duration_hours": 6, "city": "Philadelphia",
        "state": "PA", "guest_count": 50, "budget_lkr": 1000,
        "required_services": "Photography;Decoration",
    }
    value.update(overrides)
    return value


def option(service, vendor, cost=100, **overrides):
    value = {
        "service_category": service, "business_id": vendor,
        "service_option_id": f"{service}-{vendor}",
        "pricing_basis": "fixed_package", "unit_price_lkr": cost,
        "min_billable_guests": None, "min_billable_hours": None,
        "guest_capacity_applicability": "not_applicable",
        "max_guests": None, "supported_event_types": "Wedding",
        "simulated_service_city": "Philadelphia",
        "simulated_service_state": "PA", "data_origin": "synthetic",
    }
    value.update(overrides)
    return value


class DynamicFeasibilityTests(unittest.TestCase):
    def test_user_event_is_pending_and_uses_current_options(self):
        result = validate_dynamic_package(event(), [
            option("Photography", "a"), option("Decoration", "b", 200)])
        self.assertEqual(result["final_status"], "VERIFICATION_REQUIRED")
        self.assertEqual(result["total_cost_lkr"], 300)
        self.assertFalse(result["is_real_world_feasible"])
        codes = {item["code"] for item in result["pending_checks"]}
        self.assertIn("availability:a:Photography", codes)
        self.assertIn("vendor_collaboration:a:b", codes)
        self.assertIn("venue_suitability", codes)
        self.assertIn("scheduling:a:Photography", codes)

    def test_budget_failure(self):
        result = validate_dynamic_package(event(budget_lkr=100), [
            option("Photography", "a"), option("Decoration", "b", 200)])
        self.assertEqual(result["final_status"], "FAIL")
        self.assertIn("budget", {item["code"] for item in result["failed_checks"]})

    def test_capacity_failure(self):
        result = validate_dynamic_package(event(), [
            option("Photography", "a"),
            option("Decoration", "b", guest_capacity_applicability="simulated_catering_limit",
                   max_guests=20)])
        self.assertEqual(result["final_status"], "FAIL")
        self.assertIn("capacity:b:Decoration", {item["code"] for item in result["failed_checks"]})

    def test_duplicate_vendor_and_service_failure(self):
        result = validate_dynamic_package(event(), [
            option("Photography", "a"), option("Photography", "a")])
        self.assertEqual(result["final_status"], "FAIL")
        self.assertEqual({item["code"] for item in result["failed_checks"]},
                         {"service_coverage", "unique_vendors"})

    def test_failed_complete_package_excluded_and_explanation_faithful(self):
        groups = {
            "Photography": pd.DataFrame([option("Photography", "a", 100)]),
            "Decoration": pd.DataFrame([
                option("Decoration", "b", 200),
                option("Decoration", "c", 300, supported_event_types="Birthday"),
            ]),
        }
        result = generate_bounded_packages(event(), ["Photography", "Decoration"], groups, 10)
        self.assertEqual(result["feasibility_counts"]["FAIL"], 1)
        self.assertEqual(len(result["packages"]), 1)
        pkg = result["packages"][0]
        self.assertEqual(pkg["feasibility"]["final_status"], "VERIFICATION_REQUIRED")
        self.assertIn("300.00", " ".join(pkg["explanation"]["reasons"]))
        self.assertEqual(pkg["explanation"]["verification_steps"],
                         pkg["feasibility"]["verification_requirements"])

    def test_search_limit_still_bounds_validation(self):
        groups = {
            service: pd.DataFrame([option(service, f"{service}-{n}") for n in range(30)])
            for service in ("Photography", "Decoration")
        }
        with patch.dict("os.environ", {
            "PLANOVISION_MAX_CANDIDATES_PER_SERVICE": "3",
            "PLANOVISION_MAX_SEARCH_NODES": "4",
        }):
            result = generate_bounded_packages(event(), ["Photography", "Decoration"], groups, 2)
        self.assertLessEqual(result["search"]["nodes_visited"], 4)
        self.assertLessEqual(result["total_generated"], 4)
        self.assertTrue(result["search"]["all_examined_combinations_validated"])
        self.assertEqual(sum(result["feasibility_counts"].values()), result["total_generated"])

    def test_feasibility_status_precedes_score(self):
        groups = {
            "Photography": pd.DataFrame([
                option("Photography", "cheap", 100),
                option("Photography", "validated", 400),
            ]),
            "Decoration": pd.DataFrame([option("Decoration", "decor", 100)]),
        }
        real_validator = validate_dynamic_package

        def status_fixture(selected_event, selected_options, required):
            result = real_validator(selected_event, selected_options, required)
            if selected_options[0]["business_id"] == "validated":
                result["final_status"] = "PASS_IN_SIMULATION"
                result["pending_checks"] = []
                result["verification_requirements"] = []
            return result

        with patch("backend.engine.bounded_package_generator.validate_dynamic_package",
                   side_effect=status_fixture):
            result = generate_bounded_packages(
                event(), ["Photography", "Decoration"], groups, 2)
        self.assertEqual(result["packages"][0]["vendor_ids"][0], "validated")
        self.assertLess(result["packages"][0]["ranking_score"],
                        result["packages"][1]["ranking_score"])

    def test_dynamic_api_uses_in_memory_event_and_preserves_legacy(self):
        client = TestClient(app)
        generated = client.post("/api/packages/generate-dynamic", json={
            "event_type": "Wedding", "event_date": "2099-03-20",
            "start_time": "10:00", "end_time": "16:00",
            "city": "Philadelphia", "state": "PA", "guest_count": 50,
            "budget_lkr": 10000000,
            "required_services": ["Photography", "Decoration"],
            "top_k": 1,
        })
        self.assertEqual(generated.status_code, 200)
        data = generated.json()
        payload = {
            "event": data["event"],
            "package_options": data["generation"]["packages"][0]["package_options"],
        }
        response = client.post("/api/feasibility/validate-dynamic", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["final_status"], "VERIFICATION_REQUIRED")
        self.assertEqual(response.json()["event_id"], data["event_id"])
        rejected = client.post("/api/feasibility/validate-dynamic",
                               json={"event": {**data["event"], "event_id": "SIMEVT-0000"},
                                     "package_options": payload["package_options"]})
        self.assertEqual(rejected.status_code, 422)
        self.assertIn("/api/feasibility/validate", client.app.openapi()["paths"])


if __name__ == "__main__":
    unittest.main()
