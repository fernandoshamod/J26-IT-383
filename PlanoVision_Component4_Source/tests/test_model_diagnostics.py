from copy import deepcopy
import json
import unittest
import numpy as np
from component4.expense_risk import ROOT,FEATURES
from component4.model_diagnostics import simulator_reference,nested_family_subsets,paired_label_ambiguity,error_audit,bucket


class ModelDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.a={'ordinary_cost_multiplier':[.9,1.1],'receipt_multiplier':[.95,1.05]}
        self.p=json.loads((ROOT/'config/model_diagnostics.v0.1.json').read_text())
        self.row={f:1. for f in FEATURES};self.row.update(Planned_Total_Cost_LKR=100,Target_Budget_LKR=100,Retained_Receipts_LKR=125,Minimum_Margin_Pct=20)
    def test_assumption_reference_integral_and_endpoints(self):
        self.assertAlmostEqual(simulator_reference(self.row,'Budget_Overrun',self.a),.5)
        self.assertAlmostEqual(simulator_reference(self.row,'Profit_Margin_Risk',self.a),.5)
        self.row['Target_Budget_LKR']=120;self.assertEqual(simulator_reference(self.row,'Budget_Overrun',self.a),0)
        self.row['Target_Budget_LKR']=80;self.assertEqual(simulator_reference(self.row,'Budget_Overrun',self.a),1)
        for receipts in (90,110,150):
            self.row['Retained_Receipts_LKR']=receipts
            grid=np.linspace(.95,1.05,10001);threshold=.8*receipts/100
            expected=np.trapezoid(np.clip((1.1-threshold*grid)/.2,0,1),grid)/.1
            self.assertAlmostEqual(simulator_reference(self.row,'Profit_Margin_Risk',self.a),expected,places=7)
    def rows(self):
        rows=[]
        for event in ('Wedding','Corporate'):
            for family in range(4):
                for rep in range(2):
                    r=deepcopy(self.row);r.update(Scenario_ID=f'{event}{family}-{rep}',Base_Event_ID=f'{event}{family}',split='train',Event_Type_Wedding=int(event=='Wedding'),Event_Type_Corporate=int(event=='Corporate'),outcome_replication=rep,planning_state=0,Budget_Overrun=rep,Profit_Margin_Risk=rep,simulated_final_cost_lkr=110 if rep else 90,simulated_receipts_lkr=125,Planned_Budget_Utilization=1,Planned_Margin_Buffer_Pct=0)
                    rows.append(r)
        return rows
    def test_subsets_are_nested_balanced_complete_families_and_reproducible(self):
        rows=self.rows();first=nested_family_subsets(rows,[2,4,8],7)
        self.assertEqual(first,nested_family_subsets(rows,[2,4,8],7))
        prior=set()
        for count,part,ids in first:
            self.assertEqual(len(part),count*2);self.assertTrue(prior<=set(ids));prior=set(ids)
            self.assertEqual(sum(r['Event_Type_Wedding'] for r in part),len(part)//2)
    def test_heldout_rows_and_invalid_counts_blocked(self):
        rows=self.rows();rows[0]['split']='test'
        with self.assertRaisesRegex(ValueError,'training_split_only'):nested_family_subsets(rows,[2],1)
        rows[0]['split']='train'
        for counts in ([3],[4,2],[10]):
            with self.assertRaises(ValueError):nested_family_subsets(rows,counts,1)
    def test_error_categories_denominators_post_outcome_separation(self):
        rows=self.rows()
        for r in rows:r['split']='test'
        saved=[{'Scenario_ID':r['Scenario_ID'],'target':'Budget_Overrun','split':'test','label':r['Budget_Overrun'],'score':.8 if i%4<2 else .2} for i,r in enumerate(rows)]
        summary,cases=error_audit(rows,saved,self.a,self.p)
        self.assertEqual(summary['Budget_Overrun']['test']['counts'],{'TN':4,'FP':4,'FN':4,'TP':4})
        self.assertEqual(len(cases),8);self.assertEqual(summary['Budget_Overrun']['test']['errors_in_stochastic_overlap'],8)
        self.assertNotIn('simulated_final_cost_lkr',cases[0]['planning_context'])
        self.assertIn('simulated_final_cost_lkr',cases[0]['post_outcome_diagnostic_only'])
        with self.assertRaisesRegex(ValueError,'duplicate_prediction'):error_audit(rows,saved+[saved[0]],self.a,self.p)
    def test_paired_label_ambiguity_and_bucket_boundaries(self):
        result=paired_label_ambiguity(self.rows(),'Budget_Overrun')
        self.assertEqual(result['conflicting_label_vectors'],2)
        self.assertEqual(result['rows_in_conflicting_vectors'],16)
        self.assertEqual(bucket(0,[-1,0,1]),'0 to 1')


if __name__=='__main__':unittest.main()
