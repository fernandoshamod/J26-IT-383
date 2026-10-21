"""Focused provenance and status checks for the isolated PP1 research snapshot."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from research_data_v2.pp1_vendor_conflict_demo.build_demo_data import OUTPUT, build_snapshot


class VendorConflictDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = build_snapshot()
        cls.saved = json.loads(Path(OUTPUT).read_text(encoding="utf-8"))

    def test_snapshot_matches_existing_engine_fixtures_and_matrix(self):
        self.assertEqual(self.saved, self.expected)
        self.assertEqual(len(self.saved["examples"]), 3)

    def test_three_distinct_scoped_outcomes(self):
        self.assertEqual([row["operational_status"] for row in self.saved["examples"]], [
            "COMPATIBLE_WITH_EVIDENCE", "CONFLICT_WITH_EVIDENCE", "VERIFICATION_REQUIRED"])
        self.assertIn("peak demand", self.saved["examples"][1]["reason"][0])
        self.assertEqual(self.saved["examples"][2]["pair_evidence_ids"], [])
        self.assertEqual(self.saved["examples"][2]["pair_evidence_status"], "VERIFICATION_REQUIRED")

    def test_category_score_is_not_vendor_status(self):
        self.assertEqual({row["category_score"] for row in self.saved["examples"]}, {85.0})
        self.assertEqual({row["category_score_source"] for row in self.saved["examples"]},
                         {"vendor_compatibility_matrix.csv"})
        self.assertEqual(self.saved["examples"][1]["pair_evidence_status"],
                         "COMPATIBLE_WITH_EVIDENCE")
        self.assertEqual(self.saved["examples"][1]["operational_status"],
                         "CONFLICT_WITH_EVIDENCE")

    def test_real_world_limits_are_never_promoted(self):
        for row in self.saved["examples"]:
            with self.subTest(fixture=row["fixture_id"]):
                self.assertEqual(row["evidence_source"], "SYNTHETIC TEST DATA")
                self.assertEqual(row["real_world_availability"], "NOT VERIFIED")
                self.assertEqual(row["real_world_collaboration_history"], "UNKNOWN")
                self.assertEqual(row["venue_suitability"], "VERIFICATION_REQUIRED")
                self.assertFalse(row["is_real_world_feasible"])
                self.assertEqual(len(row["vendors"]), 2)
                self.assertTrue(all(vendor["vendor_id"] and vendor["option_id"]
                                    for vendor in row["vendors"]))


if __name__ == "__main__":
    unittest.main()
