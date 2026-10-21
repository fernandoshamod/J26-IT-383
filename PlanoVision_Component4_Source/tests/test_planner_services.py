from copy import deepcopy
import json
from pathlib import Path
import unittest
from component4.planner_services import PlannerServices,report_text
from component4.lkr_research import defaults

ROOT=Path(__file__).resolve().parents[1]


class PlannerServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.planner=PlannerServices()

    def fixture(self):return json.loads((ROOT/'fixtures/planner_services.mock_test_only.json').read_text())

    def test_add_service_and_profit_margin_effect(self):
        r=self.planner.request(self.fixture())
        self.assertEqual(r['delta']['cost_lkr'],60000)
        self.assertEqual(r['delta']['profit_lkr'],-60000)
        self.assertAlmostEqual(r['delta']['margin_pct_points'],-2.4)

    def test_remove_uncommitted_service(self):
        p=self.fixture();p['baseline']=deepcopy(p['alternative'])
        p['alternative']['removed_quote_ids']=['photo_demo']
        r=self.planner.request(p);self.assertEqual(r['delta']['cost_lkr'],-60000)

    def test_cancellation_fee_and_missing_terms(self):
        p=self.fixture();p['baseline']=deepcopy(p['alternative'])
        p['alternative']['quotes'][0].update(committed=True,cancellation_fee_lkr=10000)
        p['alternative']['removed_quote_ids']=['photo_demo']
        r=self.planner.request(p);self.assertEqual(r['delta']['cost_lkr'],-50000)
        p['alternative']['quotes'][0]['cancellation_fee_lkr']=None
        r=self.planner.request(p);self.assertEqual(r['alternative']['status'],'quotation_required')
        self.assertIsNone(r['delta'])

    def test_unknown_price_tax_or_future_terms_not_zero(self):
        for update in ({'unit_rate_lkr':None},{'tax_scope':'unknown','tax_pct':None},
                       {'pricing_policy':'unknown','increase_pct':None}):
            p=self.fixture();p['alternative']['quotes'][0].update(update)
            r=self.planner.request(p);self.assertEqual(r['alternative']['status'],'quotation_required')
            self.assertIsNone(r['alternative']['plan']);self.assertIsNone(r['delta'])

    def test_expired_quote(self):
        p=self.fixture();p['alternative']['event_date']='2026-11-01'
        self.assertEqual(self.planner.request(p)['alternative']['status'],'quotation_required')

    def test_declared_tax_and_escalation(self):
        p=self.fixture();p['alternative']['quotes'][0].update(unit_rate_lkr=10000,tax_scope='exclusive_declared',
            service_pct=10,tax_pct=18,pricing_policy='documented_escalation',increase_pct=10)
        self.assertEqual(self.planner.request(p)['delta']['cost_lkr'],14278)

    def test_all_in_no_double_grossup(self):
        p=self.fixture();p['alternative']['quotes'][0]['tax_pct']=18
        with self.assertRaises(ValueError):self.planner.request(p)

    def test_duplicate_and_overlapping_inclusions(self):
        p=self.fixture();p['alternative']['quotes'].append(deepcopy(p['alternative']['quotes'][0]))
        with self.assertRaises(ValueError):self.planner.request(p)
        p['alternative']['quotes'][1]['id']='different_id'
        with self.assertRaises(ValueError):self.planner.request(p)

    def test_catering_replacement_reconciles_and_tracks_guests(self):
        p=self.fixture();q=p['alternative']['quotes'][0]
        q.update(mode='replace',service='catering',covers=['catering'],quantity_basis='guests',unit_rate_lkr=5000)
        r=self.planner.request(p);self.assertEqual(r['alternative']['plan']['line_items_lkr']['catering'],750000)
        p['alternative']['planning_inputs']['guests']=180
        r=self.planner.request(p);self.assertEqual(r['alternative']['plan']['line_items_lkr']['catering'],900000)
        self.assertAlmostEqual(sum(r['alternative']['plan']['line_items_lkr'].values()),r['alternative']['plan']['total_cost_lkr'])

    def test_corporate_package_cannot_be_arbitrarily_unbundled(self):
        p=self.fixture()
        for state in ('baseline','alternative'):p[state]['planning_inputs']=defaults(self.planner.service.config,'Corporate')
        p['alternative']['quotes'][0].update(mode='replace',service='catering',covers=['catering'],quantity_basis='guests')
        self.assertEqual(self.planner.request(p)['alternative']['status'],'quotation_required')

    def test_locked_quote_increment_constant_in_paired_shocks(self):
        r=self.planner.request(self.fixture())
        for key in ('mean','p05','p50','p95'):self.assertAlmostEqual(r['delta']['paired_simulated_cost_difference_lkr'][key],60000)

    def test_quote_changes_do_not_reuse_inapplicable_models(self):
        r=self.planner.request(self.fixture())
        self.assertIsNotNone(r['baseline']['model_scores']['Budget_Overrun'])
        self.assertIsNone(r['alternative']['model_scores']['Budget_Overrun'])
        self.assertIsNone(r['alternative']['shap_drivers'])

    def test_spatial_block_and_readable_report(self):
        p=self.fixture();p['alternative']['planning_inputs'].update(guests=500,venue_area_m2=400)
        r=self.planner.request(p);self.assertEqual(r['alternative']['status'],'blocked')
        self.assertIsNone(r['delta']);self.assertIn('spatially_infeasible',report_text(r))
        text=report_text(self.planner.request(self.fixture()))
        self.assertIn('60,000.00',text);self.assertIn('TEST FIXTURE',text)

    def test_preserves_requests_and_replay(self):
        p=self.fixture();before=deepcopy(p)
        self.assertEqual(self.planner.request(p),self.planner.request(p));self.assertEqual(p,before)

    def test_invalid_numbers_and_units(self):
        for value in (float('nan'),True,-1,1e308):
            p=self.fixture();p['alternative']['quotes'][0]['unit_rate_lkr']=value
            with self.assertRaises(ValueError):self.planner.request(p)
        p=self.fixture();p['alternative']['quotes'][0].update(mode='replace',service='chairs',covers=['chairs'],quantity_basis='booking')
        with self.assertRaises(ValueError):self.planner.request(p)

    def test_planner_estimate_not_quote_or_lock(self):
        p=self.fixture();q=p['alternative']['quotes'][0]
        q.update(source_kind='planner_entered_assumption',pricing_policy='planning_estimate',evidence_ref='Planner hypothetical allowance')
        before=deepcopy(p);r=self.planner.request(p)
        self.assertEqual(r['delta']['cost_lkr'],60000);self.assertEqual(p,before)
        self.assertIn('hypothetical all-in allowances',' '.join(r['alternative']['plan']['warnings']))
        self.assertIsNone(r['alternative']['model_scores']['Budget_Overrun'])
        self.assertNotEqual(r['delta']['paired_simulated_cost_difference_lkr']['p05'],60000)

    def test_estimate_removal_and_not_fake_expiry(self):
        p=self.fixture();q=p['alternative']['quotes'][0]
        q.update(source_kind='planner_entered_assumption',pricing_policy='planning_estimate')
        p['alternative']['event_date']='2028-10-22'
        self.assertEqual(self.planner.request(p)['alternative']['status'],'calculated')
        p['baseline']=deepcopy(p['alternative']);p['alternative']['removed_quote_ids']=[q['id']]
        self.assertEqual(self.planner.request(p)['delta']['cost_lkr'],-60000)

    def test_estimate_cannot_claim_supplier_lock(self):
        p=self.fixture();p['alternative']['quotes'][0]['source_kind']='planner_entered_assumption'
        with self.assertRaisesRegex(ValueError,'planning_estimate_requires'):self.planner.request(p)
