"""Boundary design tests, explicitly mock-only; no persistent pilot outputs."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
from component4.engine import fingerprint
from component4.unitless_experiment import _calculate_unitless
from component4.unitless_pilot import validate, generate, generate_test, execution_blockers

ROOT = Path(__file__).resolve().parents[1]


def proposal(mock=False):
    c = json.loads((ROOT / 'config/unitless_pilot_candidate.v0.3.proposed.json').read_text())
    if mock:
        c['record_kind'] = 'mock_unitless_test'
        c['origin'] = 'ISOLATED_DIAGNOSTIC_TEST_NOT_APPROVED_PILOT'
    return c


class DiagnosticRevisionTests(unittest.TestCase):
    def test_complete_unapproved(self):
        self.assertTrue(validate(proposal()))
        self.assertIn('separate_explicit_authorization_missing', execution_blockers(proposal()))
        with self.assertRaisesRegex(ValueError, 'execution_blocked'):
            generate(proposal(), {})

    def test_original_candidate_preserved(self):
        c = json.loads((ROOT / 'config/unitless_pilot_candidate.json').read_text())
        self.assertEqual(fingerprint(c), 'f22c1c52bfb3ce2a1d0889ff38f73bc1d340f51e907e3979c71e0969506e3be9')

    def test_mock_reproducibility_and_scope(self):
        a = generate_test(proposal(True))
        self.assertEqual(a, generate_test(proposal(True)))
        self.assertEqual(len(a['planning']), 30)
        self.assertEqual(len(a['line_items']), 210)
        self.assertEqual(len({x['family_id'] for x in a['planning']}), 5)
        self.assertEqual(sum(x['event_type'] == 'Wedding' for x in a['planning']), 18)
        self.assertTrue(all(x['origin'].startswith('MOCK_') for x in a['provenance']))

    def test_order_independence(self):
        c = proposal(True)
        reordered = json.loads(json.dumps(c, sort_keys=True))
        self.assertEqual(generate_test(c), generate_test(reordered))

    def test_every_intervention_is_one_factor(self):
        for family in proposal()['diagnostic_families']:
            base = family['states'][0]['inputs']
            for state in family['states'][1:]:
                self.assertEqual(sum(v != base[k] for k, v in state['inputs'].items()), 1)

    def test_thresholds_and_budget_reserve_coverage(self):
        c = proposal()
        results = [[_calculate_unitless(c, f['event_type'], s['inputs']) for s in f['states']] for f in c['diagnostic_families']]
        for i in (0, 3):
            self.assertEqual(results[i][2]['tables'], results[i][0]['tables'] + 1)
            self.assertEqual(results[i][2]['staff'], results[i][0]['staff'] + 1)
        self.assertEqual([x['quantities']['av'] for x in results[1]], [1, 1, 2])
        self.assertEqual([x['paid_hours_per_staff'] for x in results[2]], [8, 7, 9])
        self.assertGreater(results[2][2]['quantities']['labour'] - results[2][0]['quantities']['labour'],
                           results[2][0]['quantities']['labour'] - results[2][1]['quantities']['labour'])
        self.assertEqual([x['planned_budget_breach'] for x in results[4]], [False, True, False])
        self.assertLess(results[4][0]['planned_cost_score'], 3.8)
        self.assertGreater(results[4][0]['planned_cost_score'] + results[4][0]['reserve_score'], 3.8)
        self.assertLess(results[4][2]['planned_cost_score'] + results[4][2]['reserve_score'], 5)

    def test_tampered_coverage_rejected(self):
        c = proposal()
        c['diagnostic_families'][0]['states'][2]['inputs']['guests'] = 122
        with self.assertRaisesRegex(ValueError, 'boundary_required'): validate(c)

    def test_confounding_rejected(self):
        c = proposal()
        c['diagnostic_families'][0]['states'][2]['inputs']['event_hours'] = 6
        with self.assertRaisesRegex(ValueError, 'one_factor'): validate(c)

    def test_capacity_boundary_separate_from_rows(self):
        c = proposal()
        x = dict(guests=180, event_hours=6, stage_width_m=5, stage_length_m=6,
                 budget_score=4, retained_receipts_score=4)
        self.assertEqual(_calculate_unitless(c, 'Wedding', x)['used_area_m2'], 384)
        # Explicit boundary probe changes capacity only, not a pilot configuration.
        probe = deepcopy(c)
        probe['capacity_persons'] = 179
        with self.assertRaisesRegex(ValueError, 'capacity_or_area_invalid'):
            _calculate_unitless(probe, 'Wedding', x)

    def test_area_boundary_separate_from_rows(self):
        c = proposal()
        x = dict(guests=180, event_hours=6, stage_width_m=5, stage_length_m=6,
                 budget_score=4, retained_receipts_score=4)
        c['excluded_area_m2'] = 48  # 432 - 48 = 384, equality permitted.
        self.assertEqual(_calculate_unitless(c, 'Wedding', x)['usable_area_m2'], 384)
        c['excluded_area_m2'] = 48.001
        with self.assertRaisesRegex(ValueError, 'capacity_or_area_invalid'):
            _calculate_unitless(c, 'Wedding', x)

    def test_old_hash_does_not_authorize_revision(self):
        self.assertIn('exact_configuration_hash_not_authorized', execution_blockers(proposal(), {
            'configuration_sha256': proposal()['revision_of_configuration_sha256']}))

    def test_outcome_features_remain_separate(self):
        b = generate_test(proposal(True))
        forbidden = {'cost_multiplier', 'receipt_multiplier', 'injection_multiplier',
                     'simulated_cost_score', 'simulated_vendor_cost_anomaly'}
        self.assertFalse(any(forbidden & set(x) for x in b['planning']))
        self.assertTrue(all(x['label_origin'] == 'SIMULATOR_OUTCOME_NOT_OBSERVED' for x in b['outcomes']))


if __name__ == '__main__':
    unittest.main()
