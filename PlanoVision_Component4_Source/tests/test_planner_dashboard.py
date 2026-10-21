from copy import deepcopy
import http.client
import json
import threading
import unittest
from component4.planner_dashboard_api import PlannerDashboard
from component4.planner_dashboard_http import create_server


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=PlannerDashboard(use_expense_model=False)
    def payload(self):
        state=self.api.config()['default_state']
        return {'baseline':deepcopy(state),'alternative':deepcopy(state)}
    def test_real_engine_default(self):
        r=self.api.calculate(self.payload())
        self.assertEqual(r['alternative']['geometry']['venue_area_m2'],500)
        self.assertEqual(r['alternative']['geometry']['area_rule_capacity'],277)
        self.assertEqual(r['delta']['cost_lkr'],0)
        self.assertIn('LKR',r['report_text'])
        self.assertEqual(r['mode'],'research_only')
    def test_what_if(self):
        p=self.payload();p['alternative']['guests']=160
        r=self.api.calculate(p)
        self.assertEqual(r['delta']['cost_lkr'],91119.6)
        self.assertLess(r['delta']['profit_lkr'],0)
    def test_capacity_blocked(self):
        p=self.payload();p['alternative']['guests']=300
        r=self.api.calculate(p)
        self.assertEqual(r['alternative']['status'],'blocked')
        self.assertIsNone(r['alternative']['plan']);self.assertIsNone(r['delta'])
    def test_budget_margin_warnings(self):
        p=self.payload();p['alternative'].update(target_budget_lkr=900000,retained_receipts_lkr=1000000)
        r=self.api.calculate(p)['alternative']['plan']
        self.assertFalse(r['budget_feasible']);self.assertFalse(r['margin_feasible'])
    def test_no_client_models_rates_or_stage(self):
        for extra in ('stage_width_m','model_scores','rate_card','approvals','realized_cost'):
            p=self.payload();p['alternative'][extra]=10
            with self.assertRaises(ValueError):self.api.calculate(p)
    def test_invalid_dimensions_and_guest_types(self):
        for update in ({'guests':True},{'guests':150.1},{'venue_width_m':0},{'venue_length_m':float('nan')}):
            p=self.payload();p['alternative'].update(update)
            with self.assertRaises(ValueError):self.api.calculate(p)
    def test_missing_quote_blocks(self):
        p=self.payload()
        from pathlib import Path
        q=json.loads((Path(__file__).resolve().parents[1]/'fixtures/planner_services.mock_test_only.json').read_text())['alternative']['quotes'][0]
        q['unit_rate_lkr']=None;p['alternative']['quotes']=[q]
        # Align fixture validity with the displayed demo date.
        q['valid_from']='2026-10-01';q['valid_until']='2026-10-31'
        r=self.api.calculate(p)
        self.assertEqual(r['alternative']['status'],'quotation_required');self.assertIsNone(r['delta'])

    def test_score_matches_existing_rule_and_report(self):
        r=self.api.calculate(self.payload());score=r['insights']['score']
        self.assertEqual(score['value'],r['alternative']['draft_planning_health']['score_points'])
        self.assertEqual(score['value'],100)
        self.assertFalse(score['validated'])
        self.assertIn('RECOMMENDATIONS',r['report_text'])

    def test_actual_loss_never_scores_100(self):
        for event in ('Wedding','Corporate'):
            p=self.payload()
            for value in p.values():value['event_type']=event
            p['alternative']['retained_receipts_lkr']=100000
            r=self.api.calculate(p)
            self.assertLess(r['alternative']['plan']['expected_profit_lkr'],0)
            self.assertEqual(r['insights']['score']['value'],0)
            self.assertEqual(r['insights']['score']['status'],'action_required')

    def test_profit_reduction_does_not_mean_actual_loss(self):
        p=self.payload();p['baseline'].update(event_type='Corporate',guests=50,event_hours=8,target_budget_lkr=3000000)
        r=self.api.calculate(p)
        self.assertLess(r['delta']['profit_lkr'],0)
        self.assertGreater(r['alternative']['plan']['expected_profit_lkr'],0)
        self.assertEqual(r['insights']['score']['value'],100)

    def test_score_shortfall_and_cost_reduction(self):
        p=self.payload();p['alternative'].update(target_budget_lkr=1000000,retained_receipts_lkr=1500000)
        r=self.api.calculate(p);i=r['insights'];self.assertEqual(i['score']['value'],0)
        self.assertEqual(i['score']['status'],'action_required')
        rec={x['id']:x for x in i['recommendations']}
        plan=r['alternative']['plan']
        self.assertAlmostEqual(rec['budget_shortfall']['amount_lkr'],plan['total_cost_lkr']+plan['reserve_lkr']-1000000,places=2)
        self.assertGreater(rec['client_payment']['amount_lkr'],0)
        self.assertGreater(rec['cost_reduction']['amount_lkr'],0)

    def test_zero_margin_policy_and_blocked_score(self):
        p=self.payload();p['alternative']['min_profit_margin_pct']=0
        self.assertEqual(self.api.calculate(p)['insights']['score']['margin_coverage'],1)
        p['alternative']['retained_receipts_lkr']=1000000
        self.assertEqual(self.api.calculate(p)['insights']['score']['margin_coverage'],0)
        p['alternative']['guests']=300
        r=self.api.calculate(p)
        self.assertIsNone(r['insights']['score']);self.assertEqual(r['insights']['recommendations'],[])

    def test_ledger_explanation_is_not_shap(self):
        p=self.payload();p['alternative']['guests']=160
        r=self.api.calculate(p);explain=r['insights']['explainability']
        self.assertEqual(explain['method'],'ledger_delta_only')
        self.assertFalse(explain['model_explanation_available'])
        self.assertAlmostEqual(sum(x['change_lkr'] for x in explain['drivers']),r['delta']['cost_lkr'],places=2)

    def test_real_native_shap_is_in_report_when_supported(self):
        p=self.payload()
        for value in p.values():value.update(venue_width_m=25,venue_length_m=40)
        r=self.api.calculate(p)
        self.assertTrue(r['insights']['explainability']['model_explanation_available'])
        self.assertIn('NATIVE TREESHAP',r['report_text'])
        self.assertEqual(r['insights']['explainability']['method'],'native_TreeSHAP_plus_ledger_delta')


class DashboardHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server(0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,payload=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=20)
        actual={'Content-Type':'application/json',**(headers or {})}
        conn.request('POST' if payload is not None else 'GET',path,body=payload,headers=actual)
        r=conn.getresponse();data=r.read();conn.close()
        return r.status,json.loads(data)
    def test_health_and_config(self):
        status,r=self.request('/api/planner/config');self.assertEqual(status,200);self.assertFalse(r['live_enabled'])
    def test_http_real_calculation(self):
        _,c=self.request('/api/planner/config');s=c['default_state']
        status,r=self.request('/api/planner/compare',json.dumps({'baseline':s,'alternative':s}))
        self.assertEqual(status,200);self.assertEqual(r['delta']['cost_lkr'],0)
    def test_live_no_research_fallback(self):
        status,r=self.request('/api/live/calculate','{}')
        self.assertEqual(status,403);self.assertEqual(r['status'],'blocked')
    def test_origin_and_host_protection(self):
        self.assertEqual(self.request('/api/planner/compare','{}',{'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.request('/api/health',headers={'Host':'untrusted.example'})[0],403)
    def test_duplicate_and_invalid_request(self):
        self.assertEqual(self.request('/api/planner/compare','{"baseline":{},"baseline":{}}')[0],400)
        self.assertEqual(self.request('/api/planner/compare','{}')[0],400)
        self.assertEqual(self.request('/api/planner/compare','{}',{'Content-Type':'text/plain'})[0],415)


if __name__=='__main__':unittest.main()
