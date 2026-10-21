from copy import deepcopy
import unittest
from component4.planner_dashboard_api import PlannerDashboard


class PricingDisclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=PlannerDashboard()
    def payload(self):
        base=self.api.config()['default_state']
        return {'baseline':deepcopy(base),'alternative':deepcopy(base)}
    def quote(self):
        # Explicit test-only coefficients; not a published quotation or tax claim.
        return {'id':'test_quote','label':'Test photography','mode':'add','service':'photography',
                'quantity_basis':'booking','unit_rate_lkr':10000,'tax_scope':'exclusive_declared',
                'service_pct':10,'tax_pct':18,'pricing_policy':'documented_escalation','increase_pct':10,
                'source_kind':'user_supplied_unverified_quote','evidence_ref':'TEST ONLY declared terms',
                'valid_from':'2026-10-01','valid_until':'2026-12-31','covers':['photography'],
                'committed':False,'cancellation_fee_lkr':0}
    def test_reference_date_changes_do_not_claim_forecast(self):
        p=self.payload();p['alternative']['event_date']='2027-01-01';r=self.api.calculate(p)
        self.assertEqual(r['delta']['cost_lkr'],0)
        self.assertFalse(r['pricing_scope']['alternative']['calibrated_future_forecast_applied'])
        self.assertIn('Event date alone does not forecast',r['report_text'])
        self.assertTrue(all(v['price_terms']=='no_calibrated_date_forecast' for v in r['pricing_scope']['alternative']['lines']))
    def test_declared_tax_and_escalation_reach_calculation_and_report(self):
        p=self.payload();p['alternative']['quotes']=[self.quote()];r=self.api.calculate(p)
        self.assertEqual(r['delta']['cost_lkr'],14278)
        line=r['pricing_scope']['alternative']['lines'][-1]
        self.assertEqual(line['documented_increase_pct'],10)
        self.assertFalse(line['independently_verified'])
        self.assertFalse(r['alternative']['model_trace']['prediction_executed'])
        self.assertIn('documented_escalation',r['report_text'])
    def test_missing_or_expired_terms_block_without_fake_values(self):
        for update in ({'unit_rate_lkr':None},{'tax_scope':'unknown','service_pct':None,'tax_pct':None},
                       {'pricing_policy':'unknown','increase_pct':None},{'valid_until':'2026-10-20'}):
            p=self.payload();q=self.quote();q.update(update);p['alternative']['quotes']=[q]
            r=self.api.calculate(p)
            self.assertEqual(r['alternative']['status'],'quotation_required')
            self.assertIsNone(r['alternative']['plan']);self.assertIsNone(r['delta'])
            self.assertEqual(r['pricing_scope']['alternative']['lines'],[])
    def test_all_in_no_double_tax_and_locked_quote(self):
        p=self.payload();q=self.quote();q.update(tax_scope='all_in',service_pct=0,tax_pct=0,pricing_policy='locked',increase_pct=0)
        p['alternative']['quotes']=[q];r=self.api.calculate(p)
        self.assertEqual(r['delta']['cost_lkr'],10000)
        self.assertEqual(r['pricing_scope']['alternative']['lines'][-1]['price_terms'],'locked')
        q['tax_pct']=18
        with self.assertRaises(ValueError):self.api.calculate(p)
    def test_wedding_core_replacement_not_double_charged(self):
        p=self.payload();q=self.quote();q.update(mode='replace',service='catering',quantity_basis='guests',covers=['catering'],unit_rate_lkr=5000,tax_scope='all_in',service_pct=0,tax_pct=0,pricing_policy='locked',increase_pct=0)
        p['alternative']['quotes']=[q];r=self.api.calculate(p)
        self.assertEqual(r['alternative']['plan']['line_items_lkr']['catering'],750000)
        self.assertEqual(sum(k.startswith('extra:') for k in r['alternative']['plan']['line_items_lkr']),0)
        p['alternative']['event_type']='Corporate'
        self.assertEqual(self.api.calculate(p)['alternative']['status'],'quotation_required')
    def test_committed_removal_keeps_declared_cancellation(self):
        p=self.payload();q=self.quote();q.update(committed=True,cancellation_fee_lkr=3000)
        p['alternative']['quotes']=[q];p['alternative']['removed_quote_ids']=[q['id']]
        r=self.api.calculate(p)
        self.assertEqual(r['delta']['cost_lkr'],3000)
        self.assertEqual(r['pricing_scope']['alternative']['lines'][-1]['basis'],'declared_cancellation_charge')
