"""Focused evidence and cause-classification tests for empty dynamic results."""

import unittest

import pandas as pd
from fastapi.testclient import TestClient

from backend.engine.coverage_diagnostics import diagnose_generation
from backend.main import app


def option(service, vendor, location="Example", price=100, basis="fixed_package"):
    return {
        "service_option_id": service + "-" + vendor,
        "business_id": vendor,
        "service_category": service,
        "simulated_service_city": location,
        "simulated_service_state": "PA",
        "supported_event_types": "Corporate",
        "max_guests": 100,
        "unit_price": price,
        "unit_price_lkr": price,
        "pricing_basis": basis,
        "min_billable_guests": None,
        "min_billable_hours": None,
        "guest_capacity_applicability": "not_applicable",
        "data_origin": "synthetic_simulation",
        "is_vendor_confirmed": False,
    }


EVENT = {
    "city": "Example", "state": "PA", "event_type": "Corporate",
    "guest_count": 50, "duration_hours": 8, "budget_lkr": 1000,
}


def generation(*, visited=0, candidate_cap=False, node_cap=False, missing=None):
    return {
        "packages": [],
        "missing_services": missing or [],
        "search": {
            "nodes_visited": visited,
            "candidate_limit_reached": candidate_cap,
            "node_limit_reached": node_cap,
        },
    }


class NoMatchDiagnosticsTests(unittest.TestCase):
    def diagnose(self, rows, services, **kwargs):
        return diagnose_generation(
            {**EVENT, **kwargs.pop("event", {})},
            services,
            pd.DataFrame(rows),
            generation(**kwargs),
        )

    def test_missing_service_and_budget_causes_are_both_preserved(self):
        result = self.diagnose(
            [option("Catering", "a", price=2000),
             option("Entertainment", "b", location="Elsewhere")],
            ["Entertainment", "Catering"],
            missing=["Entertainment"],
        )
        codes = {reason["code"] for reason in result["reasons"]}
        self.assertEqual(codes, {"NO_SERVICE_COVERAGE", "BUDGET_INSUFFICIENT"})
        self.assertFalse(result["search_attempted"])
        self.assertIsNone(result["minimum_observed_package_lower_bound_lkr"])

    def test_location_without_any_rows_has_location_and_service_causes(self):
        result = self.diagnose(
            [option("Catering", "a", location="Elsewhere")],
            ["Catering"], missing=["Catering"],
        )
        self.assertEqual(
            {reason["code"] for reason in result["reasons"]},
            {"NO_LOCATION_COVERAGE", "NO_SERVICE_COVERAGE"},
        )
        self.assertEqual(result["location_matching_rows"], 0)

    def test_unpriceable_is_distinct_from_no_service(self):
        result = self.diagnose(
            [option("Catering", "a", basis="unknown")],
            ["Catering"], missing=["Catering"],
        )
        self.assertEqual([reason["code"] for reason in result["reasons"]],
                         ["UNPRICEABLE_OPTIONS"])
        self.assertEqual(result["service_stages"]["Catering"]["priceable_rows"], 0)

    def test_candidate_cap_without_search_is_not_search_limit_cause(self):
        result = self.diagnose(
            [option("Catering", "a")], ["Entertainment"],
            candidate_cap=True, missing=["Entertainment"],
        )
        self.assertNotIn(
            "SEARCH_LIMIT_REACHED",
            [reason["code"] for reason in result["reasons"]],
        )

    def test_truncated_search_does_not_claim_no_valid_combination(self):
        result = self.diagnose(
            [option("Catering", "a"), option("Entertainment", "b")],
            ["Catering", "Entertainment"], visited=2, node_cap=True,
        )
        codes = [reason["code"] for reason in result["reasons"]]
        self.assertIn("SEARCH_LIMIT_REACHED", codes)
        self.assertNotIn("NO_COMPATIBLE_COMBINATION", codes)

    def test_complete_search_can_report_no_valid_combination(self):
        result = self.diagnose(
            [option("Catering", "same"), option("Entertainment", "same")],
            ["Catering", "Entertainment"], visited=2,
        )
        self.assertIn(
            "NO_COMPATIBLE_COMBINATION",
            [reason["code"] for reason in result["reasons"]],
        )
        self.assertEqual(result["category_compatibility_candidates_removed"], 0)

    def test_location_suggestions_have_source_backed_priceable_categories(self):
        result = self.diagnose(
            [option("Catering", "a"),
             option("Entertainment", "b", location="Elsewhere"),
             option("Catering", "c", location="Elsewhere")],
            ["Catering", "Entertainment"], missing=["Entertainment"],
        )
        self.assertEqual(result["suggested_locations"],
                         [{"city": "Elsewhere", "state": "PA"}])
        self.assertEqual(result["available_priceable_services_here"], ["Catering"])
        self.assertFalse(result["is_vendor_confirmed"])
        self.assertEqual(result["availability_status"], "unverified")

    def test_live_belle_chasse_source_counts(self):
        request = {
            "event_type": "Corporate", "event_date": "2026-11-26",
            "start_time": "10:00", "end_time": "18:00",
            "city": "Belle Chasse", "state": "LA", "guest_count": 50,
            "budget_lkr": 1000000,
            "required_services": ["Entertainment", "Catering"], "top_k": 3,
        }
        response = TestClient(app).post("/api/packages/generate-dynamic", json=request)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["generation"]["packages"], [])
        diagnostic = payload["diagnostics"]
        self.assertEqual(diagnostic["source_service_option_rows"], 57549)
        self.assertEqual(diagnostic["location_matching_rows"], 27)
        self.assertEqual(diagnostic["service_stages"]["Entertainment"]["location_rows"], 0)
        self.assertEqual(diagnostic["service_stages"]["Catering"]["priceable_rows"], 27)
        self.assertFalse(diagnostic["search_attempted"])
        self.assertEqual([item["code"] for item in diagnostic["reasons"]],
                         ["NO_SERVICE_COVERAGE"])


if __name__ == "__main__":
    unittest.main()