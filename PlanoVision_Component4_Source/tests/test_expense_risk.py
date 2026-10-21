from copy import deepcopy
import unittest
from component4.expense_risk import CalculationOnlyService,PlannerServices,load_design,generate,audit,project,FEATURES,make_estimate,support_reasons
from component4.lkr_research import defaults


class ExpenseFeatureTests(unittest.TestCase):
    def setUp(self):
        self.service=CalculationOnlyService();self.planner=PlannerServices(self.service)
        p=defaults(self.service.config);p['venue_area_m2']=500
        self.state={'planning_inputs':p,'event_date':'2026-10-22','quotes':[],'removed_quote_ids':[]}
    def test_current_500_m2_and_optional_expense_projection(self):
        state=deepcopy(self.state);state['quotes']=[make_estimate('fireworks',50000,0)]
        r=self.planner.request({'baseline':self.state,'alternative':state})
        f=project(state,r['alternative'])
        self.assertEqual(f['Optional_Expense_Total_LKR'],50000);self.assertEqual(f['Optional_Expense_Count'],1)
        self.assertEqual(r['delta']['cost_lkr'],50000)
        self.assertEqual(support_reasons(load_design(),state,r['alternative']),[])
    def test_removed_expense_is_not_an_input_exposure(self):
        state=deepcopy(self.state);state['quotes']=[make_estimate('photo',50000,0)];state['removed_quote_ids']=['assumed_0']
        r=self.planner.request({'baseline':state,'alternative':state})['alternative']
        self.assertEqual(project(state,r)['Optional_Expense_Total_LKR'],0)
    def test_no_target_or_shock_features(self):
        self.assertFalse(set(FEATURES)&{'Budget_Overrun','Profit_Margin_Risk','simulated_final_cost_lkr','outcome_seed','split','Base_Event_ID'})
    def test_generator_replay_grouping_ledger_and_labels(self):
        d=load_design();d['root_families']=12;d['split_roots']={'train':8,'validation':2,'test':2}
        first=generate(d);self.assertEqual(first,generate(d));result=audit(*first)
        self.assertEqual(result['rows'],72);self.assertEqual(result['families'],12)
    def test_invalid_scenario_and_leakage_rejected(self):
        d=load_design();d['root_families']=4;d['split_roots']={'train':2,'validation':2,'test':0}
        rows,ledger,prov=generate(d);rows[1]['split']='test'
        with self.assertRaisesRegex(ValueError,'leakage'):audit(rows,ledger,prov)


if __name__=='__main__':unittest.main()
