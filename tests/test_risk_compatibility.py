"""Focused model, join, compatibility and ranking checks."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import pandas as pd

from backend.engine import risk_signals
from backend.engine.bounded_package_generator import (
    _ranking, generate_bounded_packages,
)
from backend.engine.service_compatibility import (
    load_compatibility_rules, service_compatibility,
)

ROOT = Path(__file__).resolve().parents[1]


def option(service, vendor, option_id, cost):
    return {
        "service_category": service,
        "business_id": vendor,
        "service_option_id": option_id,
        "option_tier": "Test",
        "pricing_basis": "fixed_package",
        "unit_price_lkr": cost,
        "min_billable_guests": None,
        "min_billable_hours": None,
        "guest_capacity_applicability": "not_applicable",
        "max_guests": None,
        "data_origin": "synthetic",
    }


def event():
    return {
        "event_id": "USER-RISK-TEST",
        "guest_count": 50,
        "duration_hours": 6,
        "budget_lkr": 1000,
    }


def signal(vendor, score, label="Low"):
    return {
        "vendor_id": vendor,
        "vendor_name": vendor,
        "predicted_risk_level": label,
        "rule_risk_level": label,
        "rule_risk_score": score,
        "risk_status": "available",
        "risk_provenance": "random_forest_prediction_of_rule_generated_label",
    }


class RiskCompatibilityTests(unittest.TestCase):
    def test_verified_model_inference_and_old_artifact_agreement(self):
        profiles = pd.read_csv(
            ROOT / "hybrid_simulation_v1/real_vendor_profiles.csv", nrows=5
        )
        new_model = risk_signals.verified_model()
        features = list(risk_signals.FEATURES)
        first = new_model.predict(profiles[features]).tolist()
        second = new_model.predict(profiles[features]).tolist()
        old_model = joblib.load(ROOT / "vendor_risk_model.pkl")
        old_labels = [
            ("High", "Low", "Medium")[index]
            for index in old_model.predict(profiles[features])
        ]
        self.assertEqual(first, second)
        self.assertEqual(first, profiles["risk_level"].tolist())
        self.assertEqual(first, old_labels)
        self.assertEqual(features, list(new_model.feature_names_in_))

    def test_verified_business_id_join_and_unmatched_id(self):
        options = pd.read_csv(
            ROOT / "hybrid_simulation_v1/synthetic_service_options.csv",
            usecols=["business_id"],
        )
        profiles = pd.read_csv(
            ROOT / "hybrid_simulation_v1/real_vendor_profiles.csv",
            usecols=["business_id"],
        )
        self.assertFalse(profiles.business_id.duplicated().any())
        self.assertEqual(
            len(set(options.business_id) - set(profiles.business_id)), 0
        )
        business_id = options.business_id.iloc[0]
        lookup, audit = risk_signals.load_risk_signals(
            {business_id, "nonexistent-vendor"}
        )
        self.assertEqual(lookup[business_id]["risk_status"], "available")
        self.assertEqual(
            lookup["nonexistent-vendor"]["risk_status"], "profile_not_found"
        )
        self.assertIsNone(
            lookup["nonexistent-vendor"]["rule_risk_score"]
        )
        self.assertEqual(audit["status_counts"]["profile_not_found"], 1)
        risk_dataset = pd.read_csv(
            ROOT / "vendor_risk_dataset.csv", usecols=["business_id"]
        )
        self.assertEqual(
            len(set(options.business_id) - set(risk_dataset.business_id)), 235
        )
        self.assertEqual(
            set(risk_dataset.business_id) - set(profiles.business_id),
            {"#NAME?"},
        )

    def test_missing_model_feature_stays_unknown(self):
        row = {
            "business_id": "missing-feature",
            "name": "Test",
            "stars": 4.0,
            "review_count": 10,
            "collected_review_count": 10,
            "mean_review_rating": 4.0,
            "rating_std": None,
            "risk_level": "Low",
            "risk_score": 100,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.csv"
            pd.DataFrame([row]).to_csv(path, index=False)
            with patch.object(risk_signals, "PROFILE_FILE", path):
                lookup, audit = risk_signals.load_risk_signals(
                    {"missing-feature"}
                )
        self.assertEqual(
            lookup["missing-feature"]["risk_status"], "missing_model_features"
        )
        self.assertIsNone(
            lookup["missing-feature"]["predicted_risk_level"]
        )
        self.assertIsNone(
            lookup["missing-feature"]["rule_risk_score"]
        )
        self.assertEqual(audit["status_counts"]["missing_model_features"], 1)

    def test_model_hash_change_is_rejected(self):
        with patch.object(risk_signals, "MODEL_SHA256", "0" * 64):
            with self.assertRaises(risk_signals.RiskModelUnavailable):
                risk_signals.verified_model()

    def test_known_and_unknown_compatibility_pairs(self):
        rules = load_compatibility_rules()
        known = service_compatibility(
            ["Photography", "Decoration"], rules
        )
        unknown = service_compatibility(
            ["Photography", "Event Planning"], rules
        )
        self.assertEqual(known["score"], 85)
        self.assertEqual(known["status"], "complete")
        self.assertFalse(known["is_vendor_collaboration_evidence"])
        self.assertIsNone(unknown["score"])
        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(
            unknown["unknown_pairs"], [["Photography", "Event Planning"]]
        )

    def test_partial_compatibility_remains_unknown_at_package_level(self):
        rules = load_compatibility_rules()
        partial = service_compatibility(
            ["Photography", "Decoration", "Event Planning"], rules
        )
        self.assertEqual(partial["status"], "partial")
        self.assertIsNone(partial["score"])
        self.assertEqual(len(partial["unknown_pairs"]), 2)
    def test_score_uses_explicit_weights(self):
        risk = {"mean_rule_risk_score": 100}
        compatibility = {"score": 85}
        score, factors = _ranking(
            200, 1000, risk, compatibility,
            {"cost": 0.4, "risk": 0.4, "compatibility": 0.2},
        )
        self.assertAlmostEqual(score, 89)
        self.assertEqual(factors["risk_score"], 100)
        self.assertEqual(factors["compatibility_score"], 85)
        self.assertEqual(
            factors["effective_weights"],
            {"cost": 0.4, "risk": 0.4, "compatibility": 0.2},
        )

    def test_unknown_risk_and_compatibility_are_not_fabricated(self):
        groups = {
            "Photography": pd.DataFrame([
                option("Photography", "unknown", "photo", 200)
            ])
        }
        result = generate_bounded_packages(
            event(), ["Photography"], groups, 10
        )
        package = result["packages"][0]
        self.assertEqual(package["risk"]["status"], "unknown")
        self.assertIsNone(package["risk"]["mean_rule_risk_score"])
        self.assertIsNone(package["compatibility"]["score"])
        self.assertEqual(
            package["ranking_factors"]["effective_weights"], {"cost": 1.0}
        )
        self.assertIn("missing_vendor_risk_data", package["warnings"])

    def test_risk_changes_deterministic_ordering(self):
        groups = {
            "Photography": pd.DataFrame([
                option("Photography", "high-risk", "cheap", 100),
                option("Photography", "low-risk", "dearer", 200),
            ]),
            "Decoration": pd.DataFrame([
                option("Decoration", "middle-risk", "decor", 100),
            ]),
        }
        lookup = {
            "high-risk": signal("high-risk", 20, "High"),
            "low-risk": signal("low-risk", 100),
            "middle-risk": signal("middle-risk", 60, "Medium"),
        }
        compatibility = service_compatibility(
            ["Photography", "Decoration"], load_compatibility_rules()
        )
        first = generate_bounded_packages(
            event(), ["Photography", "Decoration"], groups, 10,
            risk_lookup=lookup, compatibility=compatibility,
        )
        second = generate_bounded_packages(
            event(), ["Photography", "Decoration"], groups, 10,
            risk_lookup=lookup, compatibility=compatibility,
        )
        self.assertEqual(
            [(p["option_ids"], p["ranking_score"]) for p in first["packages"]],
            [(p["option_ids"], p["ranking_score"]) for p in second["packages"]],
        )
        self.assertEqual(
            first["packages"][0]["option_ids"], ["dearer", "decor"]
        )

    def test_candidate_cap_reserves_quality_slots(self):
        rows = [
            option("Photography", f"high-{index}", f"cheap-{index}", index + 10)
            for index in range(15)
        ]
        rows.append(option("Photography", "low-risk", "quality", 200))
        lookup = {
            f"high-{index}": signal(f"high-{index}", 20, "High")
            for index in range(15)
        }
        lookup["low-risk"] = signal("low-risk", 100)
        with patch.dict(
            "os.environ",
            {"PLANOVISION_MAX_CANDIDATES_PER_SERVICE": "4"},
        ):
            result = generate_bounded_packages(
                event(), ["Photography"],
                {"Photography": pd.DataFrame(rows)}, 10,
                risk_lookup=lookup,
            )
        selected = {
            option_id for package in result["packages"]
            for option_id in package["option_ids"]
        }
        self.assertIn("quality", selected)
        self.assertEqual(result["search"]["max_candidates_per_service"], 4)

    def test_search_cap_still_applies_with_risk_signals(self):
        services = ["Photography", "Decoration", "Catering"]
        groups = {
            service: pd.DataFrame([
                option(service, f"{service}-{index}",
                       f"{service}-option-{index}", 10)
                for index in range(20)
            ])
            for service in services
        }
        lookup = {
            f"{service}-{index}": signal(f"{service}-{index}", 100)
            for service in services for index in range(20)
        }
        with patch.dict(
            "os.environ",
            {
                "PLANOVISION_MAX_CANDIDATES_PER_SERVICE": "4",
                "PLANOVISION_MAX_SEARCH_NODES": "5",
            },
        ):
            result = generate_bounded_packages(
                event(), services, groups, 3, risk_lookup=lookup
            )
        self.assertLessEqual(result["search"]["nodes_visited"], 5)
        self.assertTrue(result["search"]["node_limit_reached"])
        self.assertLessEqual(len(result["packages"]), 3)


if __name__ == "__main__":
    unittest.main()
