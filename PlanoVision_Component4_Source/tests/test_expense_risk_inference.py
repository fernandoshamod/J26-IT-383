from copy import deepcopy
import unittest
from unittest.mock import patch
from component4.planner_dashboard_api import PlannerDashboard
from component4.expense_risk import make_estimate,FEATURES


class ExpenseInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=PlannerDashboard(use_enhanced_model=False)
    def payload(self):
        p=self.api.config()['default_state']
        return {'baseline':deepcopy(p),'alternative':deepcopy(p)}
    def test_native_model_default_500_m2_and_shap(self):
        with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('serving_must_not_fit')):
            r=self.api.calculate(self.payload())['alternative']
        self.assertTrue(r['model_trace']['prediction_executed'])
        self.assertTrue(r['model_trace']['shap_additivity_verified'])
        self.assertEqual(r['model_trace']['input_features']['Venue_Area_m2'],500)
        self.assertEqual(set(r['model_trace']['input_features']),set(FEATURES))
        for target in r['model_scores']:
            self.assertIsNotNone(r['model_scores'][target]);self.assertEqual(len(r['shap_drivers'][target]),5)
            self.assertEqual(len(r['model_trace']['model_sha256'][target]),64)
    def test_optional_addition_changes_actual_features_and_native_risk(self):
        p=self.payload();p['alternative']['quotes']=[make_estimate('fireworks',500000,0)]
        r=self.api.calculate(p)
        self.assertAlmostEqual(r['delta']['cost_lkr'],500000)
        self.assertEqual(r['alternative']['model_trace']['input_features']['Optional_Expense_Total_LKR'],500000)
        for target in r['alternative']['model_scores']:
            self.assertGreaterEqual(r['alternative']['model_scores'][target]['uncalibrated_score'],r['baseline']['model_scores'][target]['uncalibrated_score'])
        self.assertTrue(r['alternative']['model_trace']['prediction_executed'])
        self.assertFalse(any('classifier/SHAP outputs withheld' in w for w in r['alternative']['plan']['warnings']))
        self.assertTrue(any('hypothetical all-in allowances' in w for w in r['alternative']['plan']['warnings']))
        self.assertIn('NATIVE TREESHAP',r['report_text'])
    def test_removal_restores_features_and_native_prediction(self):
        p=self.payload();original=self.api.calculate(p)['baseline']
        for state in p.values():state['quotes']=[make_estimate('photo',50000,0)]
        p['alternative']['removed_quote_ids']=['assumed_0']
        r=self.api.calculate(p)
        self.assertEqual(r['alternative']['model_scores'],original['model_scores'])
        self.assertEqual(r['alternative']['model_trace']['input_features'],original['model_trace']['input_features'])
    def test_regime_count_exposure_and_geometry_withhold(self):
        changes=[{'quotes':[make_estimate('extra_'+str(i),10000,i) for i in range(5)]},
                 {'quotes':[make_estimate('photo',2000000,0)]},{'venue_width_m':1}]
        quoted=make_estimate('photo',50000,0);quoted['committed']=True
        changes.append({'quotes':[quoted]})
        for update in changes:
            p=self.payload();p['alternative'].update(update);r=self.api.calculate(p)['alternative']
            self.assertFalse(r['model_trace']['prediction_executed'])
            self.assertTrue(r['model_trace']['support_reasons'])
            self.assertTrue(all(x is None for x in r['model_scores'].values()))
    def test_repeat_and_no_post_event_features(self):
        p=self.payload();r=self.api.calculate(p)
        self.assertEqual(r,self.api.calculate(p))
        forbidden={'simulated_final_cost_lkr','simulated_receipts_lkr','outcome_seed','Base_Event_ID','Budget_Overrun','Profit_Margin_Risk','split'}
        self.assertFalse(forbidden&set(r['alternative']['model_trace']['input_features']))


if __name__=='__main__':unittest.main()
