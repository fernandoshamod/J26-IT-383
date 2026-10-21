import copy
import json
from pathlib import Path
import unittest

from component4.pilot_review import review

ROOT = Path(__file__).resolve().parents[1]


class PilotReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads((ROOT / 'data/pilot/unitless-v0.3-user-authorized-20261012/export_payload.json').read_text())

    def test_real_pilot_diagnostics(self):
        result = review(self.bundle)
        self.assertEqual(result['planning_configurations'], 15)
        self.assertEqual(result['outcome_random_streams'], 10)
        self.assertTrue(all(r['passed'] for r in result['dependencies']))
        self.assertFalse(result['real_world_validated'])
        self.assertFalse(result['bulk_generation_authorized'])

    def test_corrupt_cost_fails_closed(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['outcomes'][0]['simulated_cost_score'] += 1
        with self.assertRaises(ValueError):
            review(bundle)

    def test_reproducible_nonmutating_review(self):
        before = copy.deepcopy(self.bundle)
        self.assertEqual(review(self.bundle), review(self.bundle))
        self.assertEqual(before, self.bundle)


if __name__ == '__main__':
    unittest.main()
