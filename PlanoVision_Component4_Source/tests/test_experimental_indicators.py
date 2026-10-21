from copy import deepcopy
import json
from pathlib import Path
import unittest
from component4.experimental_indicators import planning_indicator, invoice_request
from component4.contracts import validate_contract


def fixture():
    line = {'line_id':'catering','service':'catering','unit':'person','currency':'LKR',
            'quantity':100,'unit_rate':1000,'date':'2026-10-01','tax_scope':'tax_inclusive',
            'included_services':['food'],'bundle_id':None,'evidence_reference':'MOCK TEST ONLY'}
    invoice = {**line,'date':'2026-10-02'}
    return {'quote':[line],'invoice':[invoice],'relative_rate_tolerance':.05,'evidence_kind':'mock_test_only'}


class ExperimentalIndicatorTests(unittest.TestCase):
    def plan(self,**changes):
        return {'status':'calculated','inputs':{'budget_score':3},'planned':{
            'total_cost_score':2.7,'reserve_score':.27,'required_min_margin_points':10,
            'expected_margin_points':32.5,**changes}}

    def compare(self,**changes):
        p=fixture();p['invoice'][0].update(changes)
        return invoice_request(p)['line_comparisons'][0]

    def test_budget_reserve_bottleneck_and_no_double_expense(self):
        self.assertEqual(planning_indicator(self.plan())['score'],100)
        r=planning_indicator(self.plan(total_cost_score=3,reserve_score=.3))
        self.assertAlmostEqual(r['score'],100*3/3.3)
        self.assertFalse(r['policy']['empirically_validated'])

    def test_margin_score_and_negative_profit(self):
        self.assertEqual(planning_indicator(self.plan(expected_margin_points=5))['score'],50)
        self.assertEqual(planning_indicator(self.plan(expected_margin_points=-20))['score'],0)

    def test_unavailable_block_and_undefined_margin(self):
        self.assertIsNone(planning_indicator({'status':'blocked'})['score'])
        self.assertIsNone(planning_indicator(self.plan(expected_margin_points=None))['score'])

    def test_invalid_minimum(self):
        with self.assertRaises(ValueError):planning_indicator(self.plan(required_min_margin_points=0))

    def test_identity_and_no_mutation(self):
        p=fixture();before=deepcopy(p);r=invoice_request(p)
        self.assertEqual(p,before)
        self.assertEqual(r['line_comparisons'][0]['total_difference_amount'],0)
        self.assertFalse(r['line_comparisons'][0]['rate_increase_flag'])

    def test_quantity_is_not_price_anomaly(self):
        r=self.compare(quantity=120)
        self.assertFalse(r['rate_increase_flag'])
        self.assertEqual(r['quantity_effect_amount'],20000)

    def test_rate_and_quantity_decomposition(self):
        r=self.compare(quantity=120,unit_rate=1100)
        self.assertTrue(r['rate_increase_flag'])
        self.assertEqual(r['total_difference_amount'],32000)
        self.assertEqual(r['rate_effect_amount']+r['quantity_effect_amount'],32000)

    def test_tolerance_boundary_and_discount(self):
        self.assertFalse(self.compare(unit_rate=1050)['rate_increase_flag'])
        self.assertFalse(self.compare(unit_rate=900)['rate_increase_flag'])

    def test_scope_and_date_mismatches(self):
        for changes in ({'unit':'hour'},{'currency':'USD'},{'tax_scope':'unknown'},
                        {'included_services':['food','chairs']},{'date':'2026-09-30'},{'bundle_id':'a'}):
            r=self.compare(**changes)
            self.assertEqual(r['status'],'manual_review');self.assertIsNone(r['rate_increase_flag'])

    def test_zero_quote_rate(self):
        p=fixture();p['quote'][0]['unit_rate']=0
        self.assertIsNone(invoice_request(p)['line_comparisons'][0]['relative_rate_change'])

    def test_unmatched_line(self):
        self.assertEqual(self.compare(line_id='new')['status'],'manual_review')

    def test_invalid_numbers_dates_and_input_fields(self):
        for changes in ({'unit_rate':True},{'quantity':0},{'quantity':float('nan')},{'date':'yesterday'}):
            with self.assertRaises(ValueError):self.compare(**changes)
        for value in (-1,2,True,float('inf')):
            p=fixture();p['relative_rate_tolerance']=value
            with self.assertRaises(ValueError):invoice_request(p)
        p=fixture();p['approvals']={}
        with self.assertRaises(ValueError):invoice_request(p)

    def test_duplicate_and_overlapping_bundles(self):
        p=fixture();p['quote'].append(deepcopy(p['quote'][0]))
        with self.assertRaises(ValueError):invoice_request(p)
        p['quote'][1]['line_id']='other'
        with self.assertRaises(ValueError):invoice_request(p)

    def test_finite_overflow_blocked(self):
        with self.assertRaises(ValueError):self.compare(quantity=1e308,unit_rate=1e308)

    def test_response_schema_and_synthetic_marker(self):
        schema=json.loads((Path(__file__).resolve().parents[1]/'api/contracts/experimental_indicators.response.schema.json').read_text())
        r=invoice_request(fixture());validate_contract(r,schema)
        self.assertFalse(r['source_verified']);self.assertIsNone(r['Vendor_Cost_Anomaly_prediction'])
        health={'api_version':'experimental-indicators.0.1','operation':'planning-health','decision':{},'indicator':planning_indicator(self.plan())}
        validate_contract(health,schema)
