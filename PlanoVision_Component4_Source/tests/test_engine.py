import unittest,json,copy
from pathlib import Path
from decimal import Decimal
from component4.engine import evaluate,what_if,risk_labels,step_units,money,parameter_payload,fingerprint
from component4.gates import pilot_blockers

ROOT=Path(__file__).resolve().parents[1]
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.fixture=json.loads((ROOT/'fixtures/config.mock_test_only.json').read_text())
        self.template=json.loads((ROOT/'config/simulator.v0.1.template.json').read_text())
    def calc(self,changes=None):return evaluate(self.fixture,'Wedding',changes,mode='mock_test_fixture')
    def test_reconciliation(self):
        r=self.calc();self.assertEqual(r['status'],'calculated')
        total=sum((money(x['gross_lkr']) for x in r['costs']['line_items']),Decimal(0))
        self.assertEqual(total,money(r['costs']['estimate_lkr']))
        for line in r['costs']['line_items']:self.assertEqual(money(line['net_lkr'])+money(line['tax_lkr']),money(line['gross_lkr']))
    def test_inclusive_tax_is_not_added_twice(self):
        rate=self.fixture['archetypes']['Wedding']['rates']['catering'];rate.update(tax_scope='inclusive',tax_rate_points=10)
        l=next(x for x in self.calc()['costs']['line_items'] if x['item_id']=='catering')
        self.assertEqual(l['gross_lkr'],100000);self.assertAlmostEqual(l['net_lkr'],90909.09)
    def test_exclusive_tax(self):
        self.fixture['archetypes']['Wedding']['rates']['catering'].update(tax_scope='exclusive',tax_rate_points=10)
        l=next(x for x in self.calc()['costs']['line_items'] if x['item_id']=='catering')
        self.assertEqual(l['gross_lkr'],110000);self.assertEqual(l['tax_lkr'],10000)
    def test_capacity_boundary(self):
        self.assertEqual(self.calc({'capacity_persons':100})['status'],'calculated')
        self.assertIn('guest_count_exceeds_arrangement_capacity',self.calc({'capacity_persons':99})['blockers'])
    def test_area_boundary(self):
        used=self.calc()['spatial']['used_area_m2']
        self.assertEqual(self.calc({'venue_area_m2':used,'excluded_area_m2':0})['status'],'calculated')
        self.assertIn('used_area_exceeds_usable_area',self.calc({'venue_area_m2':used-1,'excluded_area_m2':0})['blockers'])
    def test_vip_invalid(self):self.assertIn('invalid_seating_or_vip_counts',self.calc({'vip_seats':101})['blockers'])
    def test_seating_integer_and_table_ceiling(self):
        r=self.calc({'guest_count':101});self.assertEqual(r['spatial']['planned_seats'],101);self.assertEqual(r['operations']['furniture_tables'],11)
    def test_contingency_not_an_expense(self):
        a=self.calc({'reserve_ratio':0});b=self.calc({'reserve_ratio':.2})
        self.assertEqual(a['costs']['estimate_lkr'],b['costs']['estimate_lkr'])
        self.assertEqual(b['budget_constraints']['contingency_reserve_lkr'],float(money(.2*b['costs']['estimate_lkr'])))
        self.assertFalse(b['budget_constraints']['reserve_is_expense'])
    def test_budget_below_reserve_blocks(self):self.assertIn('budget_below_contingency_reserve',self.calc({'initial_budget_lkr':1})['blockers'])
    def test_financial_failure_retained(self):
        r=self.calc({'initial_budget_lkr':100000,'reserve_ratio':0,'expected_receipts_lkr':1})
        self.assertEqual(r['status'],'calculated');self.assertTrue(r['risk_indicators']['planned_budget_breach']);self.assertLess(r['risk_indicators']['expected_profit_lkr'],0)
    def test_profit_labels(self):
        r=risk_labels(120,150,100,25);self.assertEqual(r['Profit'],30);self.assertEqual(r['Profit_Margin'],20);self.assertEqual(r['Budget_Overrun'],1);self.assertEqual(r['Profit_Margin_Risk'],1)
    def test_equality_is_not_risk(self):
        r=risk_labels(80,100,80,20);self.assertEqual(r['Budget_Overrun'],0);self.assertEqual(r['Profit_Margin_Risk'],0)
    def test_zero_missing_negative_receipts(self):
        for revenue in [None,0,-1]:self.assertIsNone(risk_labels(10,revenue,100,20)['Profit_Margin_Risk'])
        self.assertIsNone(risk_labels(None,100,100,20)['Budget_Overrun'])
    def test_vendor_regime_not_guessed(self):
        self.assertIsNone(risk_labels(10,20,15,20)['Vendor_Cost_Anomaly']);self.assertEqual(risk_labels(10,20,15,20,True)['Vendor_Cost_Anomaly'],1)
    def test_bundle_not_double_charged(self):
        self.fixture['archetypes']['Wedding']['billing']['included_items']={'chairs':'venue_fixed'}
        r=self.calc();l=next(x for x in r['costs']['line_items'] if x['item_id']=='chairs');self.assertEqual(l['gross_lkr'],0);self.assertEqual(l['included_in'],'venue_fixed')
    def test_invalid_bundle_cycle(self):
        self.fixture['archetypes']['Wedding']['billing']['included_items']={'chairs':'tables','tables':'chairs'}
        self.assertEqual(self.calc()['status'],'blocked')
    def test_stepwise_independent_thresholds(self):
        p=self.fixture['archetypes']['Wedding']
        self.assertEqual(step_units(20,p['av_steps']),1);self.assertEqual(step_units(20.01,p['av_steps']),2)
        self.assertEqual(step_units(20.01,p['lighting_steps']),1)
        with self.assertRaises(ValueError):step_units(51,p['av_steps'])
    def test_null_template_blocks(self):
        r=evaluate(self.template,'Wedding');self.assertEqual(r['status'],'blocked');self.assertIsNone(r['costs']);self.assertTrue(any('missing_or_invalid_rate:' in x for x in r['blockers']))
    def test_no_default_missing_rate(self):
        self.fixture['archetypes']['Wedding']['rates']['catering']['rate']=None
        self.assertIn('missing_or_invalid_rate:catering',self.calc()['blockers'])
    def test_negative_nonfinite_and_boolean_parameter(self):
        for x in [-1,float('nan'),True]:self.assertEqual(self.calc({'guest_count':x})['status'],'blocked')
    def test_tax_unit_and_date_blocking(self):
        r=self.fixture['archetypes']['Wedding']['rates']['catering'];r.update(unit='GBP/contract',tax_scope=None,quote_date='not-date')
        reasons=self.calc()['blockers'];self.assertIn('rate_unit_mismatch:catering',reasons);self.assertIn('tax_scope_unresolved:catering',reasons);self.assertIn('invalid_quote_date:catering',reasons)
    def test_fixture_cannot_be_live_prediction(self):
        r=evaluate(self.fixture,'Wedding');self.assertIn('mock_config_forbidden_in_live_mode',r['blockers']);self.assertFalse(r['provenance']['is_trained_model_prediction'])
    def test_deterministic_replay(self):self.assertEqual(self.calc(),self.calc())
    def test_what_if_and_baseline_immutable(self):
        before=copy.deepcopy(self.fixture);r=what_if(self.fixture,'Wedding',{'guest_count':150},mode='mock_test_fixture')
        self.assertEqual(r['comparison_status'],'comparable');self.assertGreater(r['delta']['estimated_cost_lkr'],0);self.assertEqual(self.fixture,before)
    def test_invalid_alternative_no_misleading_delta(self):
        r=what_if(self.fixture,'Wedding',{'guest_count':1000},mode='mock_test_fixture');self.assertEqual(r['comparison_status'],'blocked');self.assertIsNone(r['delta'])
    def test_outcome_firewall(self):
        r=self.calc();self.assertIsNone(r['outcome_labels']['Budget_Overrun']);self.assertIsNone(r['risk_indicators']['predicted_probabilities']);self.assertIsNone(r['financial_health_score'])
        self.assertEqual(evaluate(self.fixture,'Wedding',mode='mock_test_fixture',outcome={'cost_lkr':120,'receipts_lkr':150})['outcome_labels']['label_origin'],'mock_test_fixture')
    def test_pilot_is_blocked(self):
        reasons=pilot_blockers(self.template);self.assertIn('explicit_pilot_authorization_missing',reasons);self.assertIn('scenario_generator_not_implemented_or_verified',reasons)
    def test_only_two_event_types(self):self.assertIn('unsupported_event_type',evaluate(self.fixture,'Conference',mode='mock_test_fixture')['blockers'])
    def test_hash_binds_override_bounds(self):
        p=self.fixture['archetypes']['Wedding'];old=fingerprint(parameter_payload(p));p['approved_override_bounds']['guest_count']['max']=999
        self.assertNotEqual(old,fingerprint(parameter_payload(p)))
    def test_vip_tables_insufficient(self):
        self.assertIn('vip_tables_insufficient_for_seats',self.calc({'vip_seats':5,'vip_tables':0})['blockers'])
    def test_nonboolean_vendor_injection_not_labelled(self):
        self.assertIsNone(risk_labels(10,20,15,20,'false')['Vendor_Cost_Anomaly'])
    def approved_test_config(self):
        # In-memory branch test only. NOT a genuine review or approved market record.
        c=copy.deepcopy(self.fixture);c['record_kind']='unit_test_live_branch'
        approval={'status':'approved','reviewer':'UNIT TEST','reviewer_role':'TEST ONLY','reviewed_at':'2026-10-09','rationale':'branch coverage only','evidence_ref':'TEST-NOT-APPROVAL'}
        for aid in c['formula_approvals']:c['formula_approvals'][aid]=copy.deepcopy(approval)
        for p in c['archetypes'].values():
            for r in p['rates'].values():r['approval_status']='approved'
            for k,v in p['parameters'].items():p['approved_override_bounds'][k]={'min':v,'max':v}
            p['parameter_approval']={**approval,'parameter_hash':fingerprint(parameter_payload(p))}
        return c
    def test_live_branch_and_hash_invalidation_unit_only(self):
        c=self.approved_test_config();self.assertEqual(evaluate(c,'Wedding')['status'],'calculated')
        c['archetypes']['Wedding']['rates']['catering']['rate']+=1
        self.assertIn('parameter_approval_hash_mismatch',evaluate(c,'Wedding')['blockers'])
    def test_live_override_bounds_unit_only(self):
        c=self.approved_test_config()
        self.assertEqual(evaluate(c,'Wedding',{'guest_count':100})['status'],'calculated')
        self.assertIn('override_outside_approved_scope:guest_count',evaluate(c,'Wedding',{'guest_count':101})['blockers'])
if __name__=='__main__':unittest.main()
