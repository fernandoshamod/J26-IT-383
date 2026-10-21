from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import numpy as np
from component4.expense_risk import ROOT
from component4.frozen_robustness import draw_regime,outcomes,make_cases,safety_checks,summarize
from component4.planner_dashboard_api import PlannerDashboard


class FrozenRobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=PlannerDashboard();cls.p=json.loads((ROOT/'config/robustness.v0.1.json').read_text())
    def test_regime_reproducibility_bounds_and_coupled_adversity(self):
        for regime in self.p['outcome_regimes']:
            x,y=draw_regime(regime,512,55);xx,yy=draw_regime(regime,512,55)
            self.assertTrue(np.array_equal(x,xx) and np.array_equal(y,yy))
            self.assertTrue(np.all((x>=regime['cost'][0])&(x<=regime['cost'][1])))
            if regime['dependence']=='inverse_common_uniform':self.assertAlmostEqual(float(np.corrcoef(x,y)[0,1]),-1)
        with self.assertRaises(ValueError):draw_regime({**regime,'dependence':'invented'},512,55)
    def test_generated_diagnostic_scope_and_no_fitting(self):
        with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('robustness_must_not_fit')):
            cases=make_cases(self.api,self.p)
        self.assertEqual(len(cases),180);self.assertEqual(len({c['root_family_id'] for c in cases}),12)
        self.assertEqual(len({c['test_case_id'] for c in cases}),180)
        self.assertTrue(all(c['origin'].startswith('hypothetical') for c in cases))
    def test_labels_reconcile_and_budget_changes_do_not_change_costs(self):
        state=self.api.config()['default_state'];plan=self.api.calculate({'baseline':state,'alternative':state})['alternative']['plan']
        p=self.api.state(state)['planning_inputs'];multipliers=(np.array([.9,1,1.1]),np.array([1,1,1]))
        y,cost,receipts=outcomes(plan,p,multipliers)
        self.assertTrue(np.array_equal(y['Budget_Overrun'],(cost>p['target_budget_lkr']).astype(int)))
        self.assertTrue(np.array_equal(y['Profit_Margin_Risk'],(100*(receipts-cost)/receipts<p['min_profit_margin_pct']).astype(int)))
        changed=deepcopy(p);changed['target_budget_lkr']=100
        self.assertTrue(np.array_equal(cost,outcomes(plan,changed,multipliers)[1]))
    def test_gate_and_add_remove_checks(self):
        with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_fit')):
            records=safety_checks(self.api,self.p)
        self.assertEqual(len(records),40)
        self.assertFalse(any(r.get('pass') is False for r in records))
    def test_matched_coverage_denominators_and_rule_not_probability_claim(self):
        records=[]
        for target in ('Budget_Overrun','Profit_Margin_Risk'):
            records.extend([{'regime':'test','target':target,'root_family_id':'A','positive_outcomes':2,'xgb_score':.8,'mc_score':.75,'rule_class':1},
                            {'regime':'test','target':target,'root_family_id':'B','positive_outcomes':0,'xgb_score':None,'mc_score':.1,'rule_class':0}])
        s=summarize(records,4)['test']['Budget_Overrun']
        self.assertEqual(s['matched_model_supported_cases']['simulated_outcome_draws'],4)
        self.assertEqual(s['all_calculable_cases']['simulated_outcome_draws'],8)
        self.assertNotIn('log_loss',s['matched_model_supported_cases']['metrics']['financial_rule_classes'])


if __name__=='__main__':unittest.main()
