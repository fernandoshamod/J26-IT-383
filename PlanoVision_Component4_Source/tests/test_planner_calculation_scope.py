from copy import deepcopy
from pathlib import Path
import unittest
from component4.planner_dashboard_api import PlannerDashboard
from component4.lkr_research import load_config
from component4.release_input import sha256

ROOT = Path(__file__).resolve().parents[1]


class PlannerCalculationScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = PlannerDashboard(extended_calculator_scope=True)

    def run_case(self, **changes):
        state = deepcopy(self.api.config()['default_state'])
        state.update(changes)
        return self.api.calculate({'baseline': state, 'alternative': deepcopy(state)})

    def test_small_venue_and_100000_budget_calculate_without_forcing_affordability(self):
        for event in ('Wedding', 'Corporate'):
            response = self.run_case(event_type=event, guests=10, venue_width_m=10, venue_length_m=12,
                                     target_budget_lkr=100000, retained_receipts_lkr=150000)
            result = response['alternative']; plan = result['plan']
            self.assertEqual(result['status'], 'calculated')
            self.assertEqual(plan['used_area_m2'], 99)
            self.assertAlmostEqual(sum(plan['line_items_lkr'].values()), plan['total_cost_lkr'], places=2)
            self.assertEqual(plan['budget_feasible'], plan['total_cost_lkr'] <= 100000)
            self.assertAlmostEqual(plan['expected_profit_lkr'], 150000 - plan['total_cost_lkr'], places=2)
            self.assertEqual(set(result['calculator_scope']['extended_input_fields']), {'guests', 'venue_area_m2'})
            self.assertFalse(result['model_trace']['prediction_executed'])
            self.assertTrue(all(v is None for v in result['model_scores'].values()))
            self.assertEqual(result['graph_risk']['status'], 'withheld')
            self.assertIn('Extended-scope', response['report_text'])

    def test_screenshot_sized_event_under_400_m2_no_longer_has_artificial_area_block(self):
        r = self.run_case(guests=50, venue_width_m=12, venue_length_m=15,
                          target_budget_lkr=500000, retained_receipts_lkr=700000)['alternative']
        self.assertEqual(r['status'], 'calculated')
        self.assertEqual(r['plan']['used_area_m2'], 159)
        self.assertFalse(r['model_trace']['prediction_executed'])

    def test_large_event_calculates_but_does_not_claim_model_coverage(self):
        r = self.run_case(guests=1000, venue_width_m=40, venue_length_m=50)['alternative']
        self.assertEqual(r['status'], 'calculated')
        self.assertEqual(r['plan']['seats'], 1000)
        self.assertFalse(r['model_trace']['prediction_executed'])
        self.assertEqual(r['graph_risk']['status'], 'withheld')

    def test_physical_constraints_and_input_safety_remain(self):
        for changes in ({'guests':50,'venue_width_m':5,'venue_length_m':5}, {'guests':5001}):
            r = self.run_case(**changes)['alternative']
            self.assertEqual(r['status'], 'blocked')
            self.assertIsNone(r['plan'])
        for changes in ({'guests':0}, {'target_budget_lkr':0}):
            self.assertEqual(self.run_case(**changes)['alternative']['status'], 'blocked')

    def test_normal_demo_unchanged_and_frozen_configuration_preserved(self):
        r = self.run_case(); p = r['alternative']['plan']
        self.assertEqual(p['total_cost_lkr'], 1570450.2)
        self.assertEqual(r['insights']['score']['value'], 100)
        self.assertTrue(r['alternative']['model_trace']['prediction_executed'])
        self.assertEqual(r['alternative']['calculator_scope']['extended_input_fields'], [])
        self.assertEqual(load_config()[0]['domains']['guest_count'], [50,500])
        self.assertEqual(load_config()[0]['domains']['venue_area_m2'], [400,1600])
        self.assertEqual(sha256(ROOT/'config/lkr_research.v2.0.json'), '4165b1f251ea12183fd6a6981cbb16df8387693a3664401dba19682f7eacaa40')
        self.assertNotEqual(r['provenance']['configuration_sha256'], r['provenance']['base_configuration_sha256'])


if __name__ == '__main__':
    unittest.main()
