from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import numpy as np
from xgboost import DMatrix
from component4.expense_risk import ROOT,FEATURES,make_estimate
from component4.risk_enhancement import group_folds,fit,family_intervals
from component4.planner_dashboard_api import PlannerDashboard


class EnhancedRiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=PlannerDashboard();cls.risk=cls.api.risk
        cls.protocol=json.loads((cls.risk.folder/'protocol.json').read_text())['design']
    def payload(self):
        p=self.api.config()['default_state'];return {'baseline':deepcopy(p),'alternative':deepcopy(p)}
    def test_real_saved_model_projection_and_native_explanations(self):
        with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_serving_fit')):
            r=self.api.calculate(self.payload())['alternative']
        self.assertTrue(r['model_trace']['prediction_executed'])
        self.assertEqual(r['model_trace']['run_id'],'expense_risk_v3_1_20261016')
        for target,model in self.risk.models.items():
            fs=self.risk.metadata['model_features'][target]
            x=DMatrix(np.asarray([[r['model_trace']['input_features'][f] for f in fs]]))
            self.assertAlmostEqual(float(model.predict(x)[0]),r['model_scores'][target]['uncalibrated_score'])
            self.assertEqual(len(r['shap_drivers'][target]),min(5,len(fs)))
            self.assertTrue(set(d['feature'] for d in r['shap_drivers'][target])<=set(fs))
    def test_preview_remove_and_monotonic_expense_effects(self):
        prior={t:0 for t in self.risk.models}
        for amount in (0,100000,300000,500000,800000):
            p=self.payload()
            if amount:p['alternative']['quotes']=[make_estimate('photo',amount,0)]
            r=self.api.calculate(p)['alternative']
            self.assertTrue(r['model_trace']['prediction_executed'])
            for t,x in r['model_scores'].items():self.assertGreaterEqual(x['uncalibrated_score']+1e-8,prior[t]);prior[t]=x['uncalibrated_score']
        p['alternative']['removed_quote_ids']=['assumed_0']
        r=self.api.calculate(p)
        self.assertEqual(r['baseline']['model_scores'],r['alternative']['model_scores'])
    def test_group_cv_rejects_nontraining_and_projection_contamination(self):
        rows=[{'Scenario_ID':str(i),'Base_Event_ID':str(i//2),'split':'train',**{f:i//2 for f in FEATURES}} for i in range(12)]
        folds=group_folds(rows)
        self.assertEqual(sorted(i for _,v in folds for i in v),list(range(12)))
        rows[0]['split']='test'
        with self.assertRaisesRegex(ValueError,'training_rows'):group_folds(rows)
        with self.assertRaisesRegex(ValueError,'training_rows'):fit(self.protocol,self.protocol['candidates'][0],'Budget_Overrun',rows,{})
        rows[0]['split']='train'
        for row in rows:
            for f in FEATURES:row[f]=0
        with self.assertRaisesRegex(ValueError,'predictor_overlap'):group_folds(rows)
    def test_cluster_bootstrap_and_reproducibility(self):
        rows=[{'Base_Event_ID':str(i//2),'label':i%2} for i in range(12)]
        a=family_intervals(rows,'label',[.1,.9]*6,[.1,.9]*6,100,5)
        self.assertEqual(a,family_intervals(rows,'label',[.1,.9]*6,[.1,.9]*6,100,5))
        self.assertEqual(a['families'],6);self.assertEqual(a['accuracy_difference_vs_v3_95_interval'],[0,0])
    def test_honest_evaluation_and_unsupported_inputs(self):
        self.assertTrue(self.risk.evaluation['previously_inspected_test'])
        self.assertFalse(self.risk.evaluation['test_used_for_selection'])
        self.assertFalse(self.risk.evaluation['data_or_labels_or_splits_changed'])
        report=self.api.calculate(self.payload())['report_text']
        self.assertIn('MODEL EVALUATION — SYNTHETIC ENGINEERING EXPERIMENT',report)
        self.assertIn('Retrospective synthetic test',report)
        self.assertLess(self.risk.evaluation['targets']['Profit_Margin_Risk']['test']['xgboost']['accuracy'],self.risk.evaluation['targets']['Profit_Margin_Risk']['test']['original_v3']['accuracy'])
        p=self.payload();p['alternative']['venue_width_m']=1
        r=self.api.calculate(p)['alternative']
        self.assertFalse(r['model_trace']['prediction_executed']);self.assertIsNone(r['plan'])


if __name__=='__main__':unittest.main()
