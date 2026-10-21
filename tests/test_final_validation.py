"""Final edge-case and source-integrity regression tests."""

import copy
import json
import unittest

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.engine.package_data_loader import load_service_options


class FinalValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.request = {
            "event_type": "Wedding", "event_date": "2099-06-20",
            "start_time": "10:00", "end_time": "16:00",
            "city": "Philadelphia", "state": "PA", "guest_count": 50,
            "budget_lkr": 10000000,
            "required_services": ["Photography", "Decoration"], "top_k": 2,
        }
        response = cls.client.post("/api/packages/generate-dynamic", json=cls.request)
        if response.status_code != 200 or not response.json()["generation"]["packages"]:
            raise AssertionError(f"Cannot prepare valid package: {response.status_code}")
        cls.generated = response.json()
        cls.feasibility_payload = {
            "event": cls.generated["event"],
            "package_options": cls.generated["generation"]["packages"][0]["package_options"],
        }

    def test_valid_options_match_current_record_prices(self):
        response = self.client.post("/api/feasibility/validate-dynamic",
                                    json=self.feasibility_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["final_status"], "VERIFICATION_REQUIRED")
        self.assertEqual(response.json()["total_cost_lkr"],
                         self.generated["generation"]["packages"][0]["total_cost_lkr"])

    def test_unknown_and_conflicting_options_rejected(self):
        for field, value in (
            ("service_option_id", "INVENTED"),
            ("unit_price_lkr", 1),
            ("business_id", "INVENTED-VENDOR"),
            ("simulated_service_city", "Nowhere"),
            ("supported_event_types", "Birthday"),
            ("max_guests", 999999),
            ("guest_capacity_applicability", "not_applicable"),
        ):
            with self.subTest(field=field):
                body = copy.deepcopy(self.feasibility_payload)
                body["package_options"][0][field] = value
                response = self.client.post("/api/feasibility/validate-dynamic", json=body)
                self.assertEqual(response.status_code, 422, response.text)

    def test_missing_option_id_and_event_requirements_rejected(self):
        no_id = copy.deepcopy(self.feasibility_payload)
        no_id["package_options"][0].pop("service_option_id")
        self.assertEqual(self.client.post("/api/feasibility/validate-dynamic",
                                          json=no_id).status_code, 422)
        no_services = copy.deepcopy(self.feasibility_payload)
        no_services["event"].pop("required_services")
        self.assertEqual(self.client.post("/api/feasibility/validate-dynamic",
                                          json=no_services).status_code, 422)
        bad_budget = copy.deepcopy(self.feasibility_payload)
        bad_budget["event"]["budget_lkr"] = 0
        self.assertEqual(self.client.post("/api/feasibility/validate-dynamic",
                                          json=bad_budget).status_code, 422)

    def test_duplicate_vendor_and_oversized_option_submission(self):
        duplicate = copy.deepcopy(self.feasibility_payload)
        duplicate["package_options"][1] = copy.deepcopy(duplicate["package_options"][0])
        response = self.client.post("/api/feasibility/validate-dynamic",
                                    json=duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["final_status"], "FAIL")
        self.assertIn("unique_vendors",
                      {check["code"] for check in response.json()["failed_checks"]})
        excessive = copy.deepcopy(self.feasibility_payload)
        excessive["package_options"] *= 100
        response = self.client.post("/api/feasibility/validate-dynamic",
                                    json=excessive)
        self.assertEqual(response.status_code, 422)

    def test_empty_duplicate_and_unsupported_services(self):
        empty = self.client.post("/api/packages/generate-dynamic",
                                 json={**self.request, "required_services": []})
        invalid = self.client.post("/api/packages/generate-dynamic",
                                   json={**self.request, "required_services": ["Fake"]})
        duplicate = self.client.post("/api/packages/generate-dynamic",
                                     json={**self.request,
                                           "required_services": ["Photography", "Photography"]})
        self.assertEqual(empty.status_code, 422)
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["required_services"], ["Photography"])

    def test_bad_type_location_dates_times_and_budgets(self):
        invalid = [
            {"event_type": "Invented"},
            {"city": "Nowhere", "state": "ZZ"},
            {"event_date": "2000-01-01"},
            {"event_date": "not-a-date"},
            {"start_time": "25:99"},
            {"end_time": "not-a-time"},
            {"budget_lkr": 0},
            {"budget_lkr": -1},
        ]
        for fields in invalid:
            with self.subTest(fields=fields):
                response = self.client.post("/api/packages/generate-dynamic",
                                            json={**self.request, **fields})
                self.assertEqual(response.status_code, 422, response.text)
        for token in ("NaN", "Infinity", "-Infinity"):
            body = json.dumps({**self.request, "budget_lkr": 1}).replace(
                '"budget_lkr": 1', f'"budget_lkr": {token}')
            with self.subTest(budget=token):
                response = self.client.post(
                    "/api/packages/generate-dynamic", content=body,
                    headers={"content-type": "application/json"})
                self.assertEqual(response.status_code, 422, response.text)

    def test_low_budget_high_guest_and_repeatability(self):
        low = self.client.post("/api/packages/generate-dynamic",
                               json={**self.request, "budget_lkr": 1})
        high_guests = self.client.post("/api/packages/generate-dynamic",
                                      json={**self.request, "guest_count": 100000,
                                            "required_services": ["Catering"]})
        second = self.client.post("/api/packages/generate-dynamic", json=self.request)
        self.assertEqual(low.status_code, 200)
        self.assertEqual(low.json()["generation"]["status"],
                         "no_budget_feasible_combinations")
        self.assertEqual(high_guests.status_code, 200)
        self.assertEqual(high_guests.json()["generation"]["status"],
                         "no_matching_candidates")
        self.assertNotEqual(second.json()["event_id"], self.generated["event_id"])
        first_ids = [p["option_ids"] for p in self.generated["generation"]["packages"]]
        second_ids = [p["option_ids"] for p in second.json()["generation"]["packages"]]
        self.assertEqual(first_ids, second_ids)

    def test_rule_risk_score_direction(self):
        profiles = pd.read_csv(
            "hybrid_simulation_v1/real_vendor_profiles.csv",
            usecols=["risk_level", "risk_score"])
        expected = {"Low": 100, "Medium": 60, "High": 20}
        self.assertTrue(profiles["risk_score"].eq(
            profiles["risk_level"].map(expected)).all())
        self.assertGreater(expected["Low"], expected["Medium"])
        self.assertGreater(expected["Medium"], expected["High"])

    def test_legacy_routes_remain_registered(self):
        paths = self.client.app.openapi()["paths"]
        self.assertIn("/api/packages/generate", paths)
        self.assertIn("/api/feasibility/validate", paths)
        self.assertIn("/api/events/{event_id}", paths)


if __name__ == "__main__":
    unittest.main()
