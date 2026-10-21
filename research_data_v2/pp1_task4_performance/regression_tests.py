"""Regression tests: identical source candidates and full dynamic outputs."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas.testing as pdt
from backend.engine import dynamic_package_service as service
from backend.engine.candidate_selection import select_candidates_for_event
from backend.engine.package_data_loader import OPTION_FILE, load_service_options
from backend.schemas.dynamic_package_request import DynamicPackageRequest
from research_data_v2.pp1_task4_performance.baseline_profile import SCENARIOS
from research_data_v2.pp1_task4_performance.optimized_prototype import select_candidates_once


def normalized(response):
    value = copy.deepcopy(response)
    identifier = value["event_id"]
    return json.loads(json.dumps(value).replace(identifier, "USER-NORMALIZED"))


class PrototypeTests(unittest.TestCase):
    def test_candidate_groups_equal_for_all_scenarios(self):
        options = load_service_options()
        for name, raw in SCENARIOS.items():
            with self.subTest(name=name):
                request = DynamicPackageRequest.model_validate(raw)
                event = {"event_type": request.event_type, "city": request.city,
                         "state": request.state, "guest_count": request.guest_count}
                original = select_candidates_for_event(event, request.required_services, options)
                proposed = select_candidates_once(event, request.required_services, options)
                self.assertEqual(list(original), list(proposed))
                for service_name in original:
                    pdt.assert_frame_equal(original[service_name], proposed[service_name],
                                           check_exact=True)

    def test_full_response_equal_and_source_unchanged(self):
        before = hashlib.sha256(OPTION_FILE.read_bytes()).hexdigest()
        for name, raw in SCENARIOS.items():
            with self.subTest(name=name):
                request = DynamicPackageRequest.model_validate(raw)
                original = service.generate_dynamic_packages(request)
                with patch.object(service, "select_candidates_for_event", select_candidates_once):
                    proposed = service.generate_dynamic_packages(request)
                self.assertNotEqual(original["event_id"], proposed["event_id"])
                self.assertEqual(normalized(original), normalized(proposed))
                self.assertEqual(
                    [p["option_ids"] for p in original["generation"]["packages"]],
                    [p["option_ids"] for p in proposed["generation"]["packages"]],
                )
        self.assertEqual(before, hashlib.sha256(OPTION_FILE.read_bytes()).hexdigest())

    def test_no_cross_request_state_or_input_mutation(self):
        options = load_service_options()
        before = options.copy(deep=True)
        raw = SCENARIOS["wedding"]
        event = {"event_type": raw["event_type"], "city": raw["city"],
                 "state": raw["state"], "guest_count": raw["guest_count"]}
        first = select_candidates_once(event, raw["required_services"], options)
        event["city"] = "Unlisted"
        second = select_candidates_once(event, raw["required_services"], options)
        self.assertTrue(all(group.empty for group in second.values()))
        self.assertTrue(any(not group.empty for group in first.values()))
        pdt.assert_frame_equal(before, options, check_exact=True)


if __name__ == "__main__":
    unittest.main()