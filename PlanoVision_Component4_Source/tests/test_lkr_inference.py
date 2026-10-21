from copy import deepcopy
import unittest
import numpy as np
from component4.lkr_research import defaults,shocks
from component4.lkr_inference import LKRResearchInference
from scripts.research_pipeline.run_planner_cli_lkr import collect


class LKRInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.service=LKRResearchInference()

    def baseline(self):return defaults(self.service.config)

    def test_actual_new_models_and_shap(self):
        response=self.service.request({'inputs':self.baseline(),'draws':100})
        r=response['result'];self.assertEqual(r['status'],'calculated')
        self.assertEqual(response['provenance']['currency'],'LKR')
        self.assertFalse(response['provenance']['real_world_validated'])
        self.assertAlmostEqual(r['plan']['total_cost_lkr'],1570450.2)
        for target in ('Budget_Overrun','Profit_Margin_Risk'):
            self.assertIsNotNone(r['model_scores'][target])
            self.assertEqual(len(r['shap_drivers'][target]),3)

    def test_seed_reproducibility(self):
        p={'inputs':self.baseline(),'draws':100,'seed':123}
        self.assertEqual(self.service.request(p),self.service.request(p))

    def test_identical_paired_comparison(self):
        response=self.service.request({'baseline':self.baseline(),'alternative_changes':{},'draws':100},'what-if')
        self.assertEqual(response['baseline'],response['alternative'])
        self.assertEqual(response['delta']['estimated_cost_lkr'],0)
        self.assertEqual(response['delta']['paired_simulated_cost_difference_lkr']['p95'],0)

    def test_continuous_what_if(self):
        response=self.service.request({'baseline':self.baseline(),'alternative_changes':{'event_hours':7.25,'stage_width_m':5.5,'guests':180},'draws':100},'what-if')
        self.assertAlmostEqual(response['delta']['estimated_cost_lkr'],348837.5)
        self.assertLess(response['delta']['expected_profit_lkr'],0)
        self.assertFalse(response['alternative']['plan']['affordable_after_reserve'])

    def test_spatial_block_no_scores_or_delta(self):
        response=self.service.request({'baseline':self.baseline(),'alternative_changes':{'guests':500,'venue_area_m2':400},'draws':100},'what-if')
        self.assertEqual(response['alternative']['status'],'blocked')
        self.assertIsNone(response['alternative']['model_scores'])
        self.assertIsNone(response['delta'])

    def test_out_of_support_not_clamped(self):
        inputs={**self.baseline(),'target_budget_lkr':1e12}
        r=self.service.request({'inputs':inputs,'draws':100})['result']
        self.assertEqual(r['status'],'calculated');self.assertEqual(r['inputs']['target_budget_lkr'],1e12)
        self.assertIsNone(r['model_scores']['Budget_Overrun'])
        self.assertIsNone(r['shap_drivers']['Budget_Overrun'])

    def test_no_client_outcomes_rates_or_approvals(self):
        for name in ('actual_cost','shocks','rates','approvals','model_predictions','mode'):
            with self.assertRaises(ValueError):self.service.request({'inputs':self.baseline(),name:{}})

    def test_invalid_random_controls(self):
        for value in (-1,0,10001,True):
            with self.assertRaises(ValueError):self.service.request({'inputs':self.baseline(),'draws':value})

    def test_inputs_and_configuration_unchanged(self):
        inputs=self.baseline();original=deepcopy(inputs);config=deepcopy(self.service.config)
        self.service.request({'inputs':inputs,'draws':100})
        self.assertEqual(inputs,original);self.assertEqual(self.service.config,config)

    def test_cli_continuous_values_and_lkr(self):
        values=iter(['150','5.25','4.15','6.35','1000','2,000,000','2,500,000','15'])
        inputs=collect(self.service.config,'Wedding',reader=lambda _:next(values),writer=lambda _:None)
        self.assertEqual(inputs['stage_width_m'],4.15)
        self.assertEqual(inputs['target_budget_lkr'],2000000)
        self.assertEqual(self.service.request({'inputs':inputs,'draws':100})['result']['status'],'calculated')
