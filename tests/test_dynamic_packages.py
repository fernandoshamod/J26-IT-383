"""Focused checks for request-time dynamic package generation."""

import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.engine.bounded_package_generator import generate_bounded_packages


def option(service, vendor, option_id, price):
    return {
        "service_category": service,
        "business_id": vendor,
        "service_option_id": option_id,
        "option_tier": "Test",
        "pricing_basis": "fixed_package",
        "unit_price_lkr": price,
        "min_billable_guests": None,
        "min_billable_hours": None,
        "guest_capacity_applicability": "not_applicable",
        "max_guests": None,
        "data_origin": "synthetic",
    }


def event():
    return {
        "event_id": "USER-TEST",
        "guest_count": 50,
        "duration_hours": 6.0,
        "budget_lkr": 1000.0,
    }


class DynamicPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def request_body(self, **overrides):
        body = {
            "event_type": "Wedding",
            "event_date": "2099-03-20",
            "start_time": "10:00",
            "end_time": "16:00",
            "city": "Philadelphia",
            "state": "PA",
            "guest_count": 50,
            "budget_lkr": 10000000,
            "required_services": ["Photography", "Decoration"],
        }
        body.update(overrides)
        return body

    def test_philadelphia_multiservice_request(self):
        response = self.client.post(
            "/api/packages/generate-dynamic", json=self.request_body()
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["event_id"].startswith("USER-"))
        self.assertEqual(data["generation_mode"], "dynamic_user_request")
        self.assertEqual(data["data_origin"], "synthetic_simulation")
        packages = data["generation"]["packages"]
        self.assertGreater(len(packages), 0)
        self.assertLessEqual(len(packages), 10)
        for package in packages:
            self.assertEqual(
                set(package["service_coverage"]), {"Photography", "Decoration"}
            )
            self.assertEqual(len(set(package["vendor_ids"])), 2)
            self.assertLessEqual(package["total_cost_lkr"], 10000000)
            self.assertEqual(package["availability_status"], "unverified")
            self.assertEqual(
                len(package["service_breakdown"]), 2
            )

    def test_unsupported_location_is_actionable(self):
        response = self.client.post(
            "/api/packages/generate-dynamic",
            json=self.request_body(city="Nowhere", state="ZZ"),
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("GET /api/locations", response.json()["detail"])

    def test_supported_location_with_no_service_candidates(self):
        response = self.client.post(
            "/api/packages/generate-dynamic",
            json=self.request_body(
                city="Affton", state="MO",
                required_services=["Photography"],
            ),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["generation"]
        self.assertEqual(result["status"], "no_matching_candidates")
        self.assertEqual(result["missing_services"], ["Photography"])
        self.assertEqual(result["packages"], [])
    def test_insufficient_budget_is_distinct(self):
        response = self.client.post(
            "/api/packages/generate-dynamic",
            json=self.request_body(budget_lkr=1),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["generation"]
        self.assertEqual(result["status"], "no_budget_feasible_combinations")
        self.assertEqual(result["packages"], [])
        self.assertTrue(result["search"]["complete"])

    def test_duplicate_vendor_is_rejected(self):
        groups = {
            "Photography": pd.DataFrame([
                option("Photography", "vendor-a", "photo-a", 100),
            ]),
            "Decoration": pd.DataFrame([
                option("Decoration", "vendor-a", "decor-a", 100),
                option("Decoration", "vendor-b", "decor-b", 200),
            ]),
        }
        result = generate_bounded_packages(
            event(), ["Photography", "Decoration"], groups, 10
        )
        self.assertEqual(len(result["packages"]), 1)
        self.assertEqual(result["packages"][0]["vendor_ids"],
                         ["vendor-a", "vendor-b"])
        self.assertGreater(result["duplicate_vendor_rejected"], 0)

    def test_ranking_is_deterministic(self):
        groups = {
            "Photography": pd.DataFrame([
                option("Photography", "vendor-a", "photo-a", 100),
                option("Photography", "vendor-b", "photo-b", 200),
            ]),
            "Decoration": pd.DataFrame([
                option("Decoration", "vendor-c", "decor-c", 100),
            ]),
        }
        first = generate_bounded_packages(
            event(), ["Photography", "Decoration"], groups, 10
        )
        second = generate_bounded_packages(
            event(), ["Photography", "Decoration"], groups, 10
        )
        first_ranked = [
            (package["option_ids"], package["ranking_score"])
            for package in first["packages"]
        ]
        second_ranked = [
            (package["option_ids"], package["ranking_score"])
            for package in second["packages"]
        ]
        self.assertEqual(first_ranked, second_ranked)
        self.assertEqual(first_ranked[0][0], ["photo-a", "decor-c"])
        self.assertGreater(first_ranked[0][1], first_ranked[1][1])

    def test_search_is_bounded_before_product_enumeration(self):
        services = ["Photography", "Decoration", "Catering"]
        groups = {
            service: pd.DataFrame([
                option(service, f"{service}-{index}",
                       f"{service}-option-{index}", 10)
                for index in range(50)
            ])
            for service in services
        }
        with patch.dict(
            "os.environ",
            {
                "PLANOVISION_MAX_CANDIDATES_PER_SERVICE": "4",
                "PLANOVISION_MAX_SEARCH_NODES": "5",
            },
        ):
            result = generate_bounded_packages(event(), services, groups, 3)
        search = result["search"]
        self.assertEqual(result["status"], "search_limit_reached")
        self.assertLessEqual(search["nodes_visited"], 5)
        self.assertEqual(search["selected_search_space_upper_bound"], 64)
        self.assertTrue(search["candidate_limit_reached"])
        self.assertTrue(search["node_limit_reached"])
        self.assertLessEqual(len(result["packages"]), 3)

    def test_invalid_service_and_event_type(self):
        service = self.client.post(
            "/api/packages/generate-dynamic",
            json=self.request_body(required_services=["Unsupported"]),
        )
        event_type = self.client.post(
            "/api/packages/generate-dynamic",
            json=self.request_body(event_type="Unsupported"),
        )
        self.assertEqual(service.status_code, 422)
        self.assertIn("Unsupported services", str(service.json()))
        self.assertEqual(event_type.status_code, 422)
        self.assertIn("Unsupported event type", str(event_type.json()))


if __name__ == "__main__":
    unittest.main()
