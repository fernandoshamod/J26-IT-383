from copy import deepcopy
import unittest
from component4.lkr_research import load_config,defaults,calculate,features,generate,validate_dataset,FEATURES,shocks,realized


class LKRResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.config,cls.evidence=load_config()

    def inputs(self,**changes):return {**defaults(self.config),**changes}

    def small(self):
        c=deepcopy(self.config);c['generation']['root_families']=10
        c['generation']['split_root_counts']={'train':6,'validation':2,'test':2}
        return c

    def test_monetary_not_score_conversion(self):
        p=calculate(self.config,self.evidence,self.inputs())
        self.assertGreater(p['total_cost_lkr'],100000)
        self.assertEqual(p['reference_rate_lkr_per_person'],5950)
        self.assertFalse(p['confirmed_all_in_market_quote'])

    def test_continuous_inputs_and_ledger(self):
        p=calculate(self.config,self.evidence,self.inputs(event_hours=5.25,stage_width_m=4.15,stage_length_m=6.35))
        self.assertAlmostEqual(sum(p['line_items_lkr'].values()),p['total_cost_lkr'])

    def test_guest_cost_dependency(self):
        a=calculate(self.config,self.evidence,self.inputs());b=calculate(self.config,self.evidence,self.inputs(guests=180))
        self.assertGreater(b['line_items_lkr']['catering'],a['line_items_lkr']['catering'])
        self.assertGreater(b['total_cost_lkr'],a['total_cost_lkr'])

    def test_stage_and_duration_dependencies(self):
        a=calculate(self.config,self.evidence,self.inputs());b=calculate(self.config,self.evidence,self.inputs(stage_width_m=6,event_hours=9))
        for service in ('stage','av','labour','venue'):self.assertGreater(b['line_items_lkr'][service],a['line_items_lkr'][service])

    def test_budget_changes_do_not_change_cost(self):
        a=calculate(self.config,self.evidence,self.inputs());b=calculate(self.config,self.evidence,self.inputs(target_budget_lkr=100))
        self.assertEqual(a['total_cost_lkr'],b['total_cost_lkr']);self.assertFalse(b['budget_feasible'])

    def test_reserve_not_expense_and_client_price(self):
        p=calculate(self.config,self.evidence,self.inputs())
        self.assertEqual(p['expected_profit_lkr'],round(2500000-p['total_cost_lkr'],2))
        self.assertEqual(p['recommended_client_price_excluding_output_tax_lkr'],round((p['total_cost_lkr']+p['reserve_lkr'])/.85,2))

    def test_corporate_bundle_not_double_charged(self):
        inputs=defaults(self.config,'Corporate');inputs.update(stage_width_m=3,stage_length_m=4)
        p=calculate(self.config,self.evidence,inputs)
        self.assertEqual(p['total_cost_lkr'],inputs['guests']*6500)
        self.assertEqual(sum(p['assumed_incremental_extras_before_charges_lkr'].values()),0)

    def test_negative_margin_retained(self):
        p=calculate(self.config,self.evidence,self.inputs(retained_receipts_lkr=100))
        self.assertLess(p['expected_margin_pct'],0);self.assertFalse(p['margin_feasible'])

    def test_unsupported_and_invalid(self):
        for changes in ({'event_type':'Concert'},{'guests':150.5},{'guests':True},{'event_hours':float('nan')},
                        {'target_budget_lkr':0},{'retained_receipts_lkr':0},{'min_profit_margin_pct':100},
                        {'stage_width_m':0},{'venue_area_m2':400,'guests':500}):
            with self.assertRaises(ValueError):calculate(self.config,self.evidence,self.inputs(**changes))

    def test_stage_removal(self):
        p=calculate(self.config,self.evidence,self.inputs(stage_width_m=0,stage_length_m=0))
        self.assertEqual(p['line_items_lkr']['stage'],0);self.assertEqual(p['line_items_lkr']['av'],0)

    def test_only_planning_features(self):
        f=features(self.inputs(),calculate(self.config,self.evidence,self.inputs()))
        self.assertEqual(list(f),FEATURES)
        self.assertFalse(any('simulated' in k or 'actual' in k.lower() for k in f))

    def test_generator_reproducibility_and_groups(self):
        c=self.small();a=generate(c,self.evidence);self.assertEqual(a,generate(c,self.evidence))
        audit=validate_dataset(*a);self.assertEqual(audit['rows'],60)
        self.assertEqual(audit['split_rows'],{'train':36,'validation':12,'test':12})

    def test_label_and_arithmetic_tampering(self):
        for mutate in ('label','cost','ledger','group'):
            rows,ledger,prov=generate(self.small(),self.evidence)
            if mutate=='label':rows[0]['Budget_Overrun']=1-rows[0]['Budget_Overrun']
            elif mutate=='cost':rows[0]['simulated_final_cost_lkr']+=10000
            elif mutate=='ledger':ledger[0]['planned_lkr']+=100
            else:rows[1]['split']='test' if rows[0]['split']!='test' else 'train'
            with self.assertRaises(ValueError):validate_dataset(rows,ledger,prov)

    def test_shock_controls_and_identity_outcome(self):
        for args in ((True,1),(100,-1),(0,1),(100,2**32)):
            with self.assertRaises(ValueError):shocks(self.config,*args)
        p=calculate(self.config,self.evidence,self.inputs());r=realized(self.inputs(),p,(1.,1.))
        self.assertEqual(r['simulated_final_cost_lkr'],p['total_cost_lkr'])
        self.assertEqual(r['simulated_profit_lkr'],p['expected_profit_lkr'])
