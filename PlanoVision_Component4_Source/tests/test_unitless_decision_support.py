from copy import deepcopy
import json
from pathlib import Path
import unittest
import numpy as np

from component4.unitless_decision_support import UnitlessDecisionSupport, draw_shocks, monte_carlo, model_features
from component4.unitless_experiment import _calculate_unitless
from component4.contracts import validate_contract

ROOT = Path(__file__).resolve().parents[1]


class UnitlessDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = UnitlessDecisionSupport()
        cls.schema = json.loads((ROOT/'api/contracts/unitless_decision.response.schema.json').read_text())

    def inputs(self):
        return {'guests':100,'event_hours':4,'stage_width_m':3,'stage_length_m':4,'budget_score':3,'retained_receipts_score':4}

    def calculate(self,**changes):
        return self.service.request({'event_type':'Wedding','inputs':{**self.inputs(),**changes},'draws':100})

    def compare(self,changes):
        return self.service.request({'event_type':'Wedding','baseline':self.inputs(),'alternative_changes':changes,'draws':100},'what-if')

    def test_end_to_end_actual_models_and_contract(self):
        response = self.calculate()
        validate_contract(response,self.schema)
        r = response['result']
        self.assertEqual(r['status'],'calculated')
        self.assertAlmostEqual(r['planned']['total_cost_score'],2.7)
        self.assertAlmostEqual(sum(r['planned']['line_items_score'].values()),2.7)
        self.assertAlmostEqual(r['planned']['expected_profit_score'],1.3)
        self.assertEqual(response['provenance']['currency'],None)
        self.assertEqual(response['provenance']['configuration_sha256'],'2a94673fa623cae6aff278f44d103061129718697dbded14ef1e8fe42404b9bb')
        self.assertGreaterEqual(r['model_risk_scores']['Budget_Overrun'],0)
        self.assertFalse(r['model_risk_scores']['calibrated'])
        self.assertIsNone(r['model_risk_scores']['Vendor_Cost_Anomaly'])
        self.assertIsNone(r['financial_health_score'])

    def test_corporate_supported(self):
        r = self.service.request({'event_type':'Corporate','inputs':self.inputs(),'draws':100})
        self.assertEqual(r['result']['status'],'calculated')

    def test_reproducibility(self):
        self.assertEqual(self.calculate(),self.calculate())

    def test_inputs_and_config_unchanged(self):
        inputs = self.inputs()
        before = deepcopy(self.service.config)
        self.service.request({'event_type':'Wedding','inputs':inputs,'draws':100})
        self.assertEqual(inputs,self.inputs())
        self.assertEqual(self.service.config,before)

    def test_identity_what_if_paired_zero(self):
        response = self.compare({})
        validate_contract(response,self.schema)
        self.assertEqual(response['baseline'],response['alternative'])
        self.assertEqual(response['delta']['paired_simulated_cost_difference_score'],{'mean':0.,'p05':0.,'p50':0.,'p95':0.})

    def test_guest_dependency(self):
        r = self.compare({'guests':120})
        self.assertGreater(r['delta']['planned_cost_score'],0)
        self.assertEqual(r['delta']['seats'],20)
        self.assertGreater(r['delta']['space_utilization'],0)

    def test_av_threshold_dependency(self):
        r = self.compare({'stage_length_m':6})
        self.assertEqual(r['baseline']['planned']['quantities']['av'],1)
        self.assertEqual(r['alternative']['planned']['quantities']['av'],2)

    def test_duration_and_overtime(self):
        r = self.compare({'event_hours':7})
        self.assertEqual(r['alternative']['planned']['paid_hours_per_staff'],9)
        self.assertGreater(r['alternative']['planned']['quantities']['labour'],r['baseline']['planned']['quantities']['labour'])

    def test_budget_changes_not_expenses(self):
        r = self.compare({'budget_score':2})
        self.assertEqual(r['delta']['planned_cost_score'],0)
        self.assertEqual(r['baseline']['monte_carlo']['cost_score'],r['alternative']['monte_carlo']['cost_score'])
        self.assertFalse(r['alternative']['planned']['budget_feasible'])
        self.assertTrue(r['alternative']['warnings'])
        self.assertGreaterEqual(r['alternative']['monte_carlo']['budget_overrun_frequency'],r['baseline']['monte_carlo']['budget_overrun_frequency'])

    def test_reserve_not_double_charged(self):
        r = self.calculate()['result']
        self.assertAlmostEqual(r['planned']['reserve_score'],.27)
        self.assertAlmostEqual(r['planned']['operating_allowance_score'],2.73)
        self.assertEqual(len(r['planned']['line_items_score']),7)

    def test_invalid_capacity_and_no_misleading_delta(self):
        r = self.compare({'guests':181})
        self.assertEqual(r['comparison_status'],'blocked')
        self.assertIsNone(r['delta'])
        self.assertIsNone(r['alternative']['model_risk_scores'])
        self.assertIsNone(r['alternative']['monte_carlo'])

    def test_invalid_stage_and_domain_blocked(self):
        for changes in ({'stage_width_m':100},{'event_hours':999},{'budget_score':100}):
            self.assertEqual(self.calculate(**changes)['result']['status'],'blocked')

    def test_invalid_finite_values(self):
        for value in (True,float('nan'),float('inf'),'100'):
            with self.assertRaises(ValueError): self.calculate(guests=value)

    def test_missing_inputs_and_client_rate_cards_rejected(self):
        with self.assertRaises(ValueError): self.service.request({'event_type':'Wedding','inputs':{}})
        for field in ('rates','config','approvals','realized_cost','model_predictions','mode'):
            with self.assertRaises(ValueError): self.service.request({'event_type':'Wedding','inputs':self.inputs(),field:{}})

    def test_invalid_draws_and_seed(self):
        for draws in (99,10001,True,100.5):
            with self.assertRaises(ValueError): self.service.request({'event_type':'Wedding','inputs':self.inputs(),'draws':draws})
        for seed in (-1,True,2**32):
            with self.assertRaises(ValueError): draw_shocks(self.service.config,100,seed)

    def test_no_outcome_inputs_in_feature_projection(self):
        plan = _calculate_unitless(self.service.config,'Wedding',self.inputs())
        features = model_features(self.service.config,'Wedding',self.inputs(),plan,self.service.spec['predictors'])
        self.assertEqual(len(features),21)
        self.assertFalse(set(features)&set(self.service.spec['forbidden_inputs']))

    def test_monte_carlo_identity_with_no_shocks(self):
        inputs = self.inputs()
        plan = _calculate_unitless(self.service.config,'Wedding',inputs)
        shocks = {'cost':np.ones(100),'receipts':np.ones(100),'injected':np.zeros(100,dtype=bool),
                  'service_index':np.zeros(100,dtype=int),'injection':np.ones(100)}
        simulation = monte_carlo(self.service.config,inputs,plan,shocks)
        np.testing.assert_allclose(simulation['cost'],2.7)
        np.testing.assert_allclose(simulation['profit'],1.3)
        self.assertFalse(simulation['overrun'].any())

    def test_out_of_model_support_no_score_fallback(self):
        support = self.service.support['Wedding']['Guest_Count']
        try:
            self.service.support['Wedding']['Guest_Count']=(110,120)
            r = self.calculate()['result']
            self.assertEqual(r['status'],'calculated')
            self.assertIsNone(r['model_risk_scores']['Budget_Overrun'])
            self.assertIsNotNone(r['monte_carlo'])
            self.assertTrue(r['warnings'])
        finally:
            self.service.support['Wedding']['Guest_Count']=support
