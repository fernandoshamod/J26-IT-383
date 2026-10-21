from copy import deepcopy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from component4.component2_adapter import import_bundle,strict_json
from component4.forecast_bridge import catalog,preview,artifacts,FILES,BASE,ROOT
from component4.planner_dashboard_api import PlannerDashboard
from component4.planner_dashboard_http import create_server


def bundle():
    # All numeric rates/percentages are unit-test assumptions, not market evidence.
    return {'contract_version':'component2.quotation_bundle.v1','bundle_id':'TEST-BUNDLE',
            'supplier_id':'TEST-NOT-REAL-SUPPLIER','issued_on':'2026-10-18','event_type':'Wedding','event_date':'2026-10-22',
            'quotations':[{'id':'p2_test_photo','label':'TEST photography','mode':'add','service':'photography',
                'quantity_basis':'booking','unit_rate_lkr':10000,'currency':'LKR','tax_scope':'exclusive_declared',
                'service_pct':10,'tax_pct':18,'pricing_policy':'documented_escalation','increase_pct':10,
                'evidence_ref':'TEST ONLY; not a published quotation','valid_from':'2026-10-18','valid_until':'2026-11-01',
                'covers':['photography'],'committed':False,'cancellation_fee_lkr':0}]}


class Component2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=PlannerDashboard()
    def state(self):return self.api.config()['default_state']
    def test_import_is_preview_only_unverified_and_reconciles(self):
        s=self.state();before=deepcopy(s);r=import_bundle(bundle(),s)
        self.assertEqual(s,before);self.assertFalse(r['independently_verified']);self.assertFalse(r['transport_authenticated'])
        c=self.api.calculate({'baseline':s,'alternative':r['proposed_state']})
        self.assertEqual(c['delta']['cost_lkr'],14278)
        self.assertFalse(c['alternative']['model_trace']['prediction_executed'])
        self.assertIn('Component 2 bundle TEST-BUNDLE',c['report_text'])
    def test_unknown_terms_remain_blocking(self):
        b=bundle();b['quotations'][0].update(unit_rate_lkr=None,tax_scope='unknown',tax_pct=None,service_pct=None,pricing_policy='unknown',increase_pct=None)
        r=import_bundle(b,self.state());c=self.api.calculate({'baseline':self.state(),'alternative':r['proposed_state']})
        self.assertEqual(c['alternative']['status'],'quotation_required');self.assertIsNone(c['alternative']['plan'])
    def test_scope_currency_approval_and_outcome_injection_rejected(self):
        for field,value in [('event_type','Corporate'),('event_date','2026-10-23'),('approved',True),('model_predictions',{})]:
            b=bundle();b[field]=value
            with self.assertRaises(ValueError):import_bundle(b,self.state())
        for update in ({'currency':'USD'},{'unit_rate_lkr':True},{'evidence_ref':None},{'source_kind':'verified'},{'actual_total_cost':1}):
            b=bundle();b['quotations'][0].update(update)
            with self.assertRaises(ValueError):import_bundle(b,self.state())
    def test_no_duplicate_or_overwritten_quote_ids(self):
        s=import_bundle(bundle(),self.state())['proposed_state']
        with self.assertRaises(ValueError):import_bundle(bundle(),s)
        b=bundle();b['quotations'].append(deepcopy(b['quotations'][0]))
        with self.assertRaises(ValueError):import_bundle(b,self.state())
    def test_strict_bundle_parsing(self):
        for raw in ('{"a":1,"a":2}','{"a":NaN}','x'*60001):
            with self.assertRaises(ValueError):strict_json(raw)
        self.assertEqual(strict_json(json.dumps(bundle())),bundle())
    def test_published_contract_example_is_test_only_and_importable(self):
        fixture=ROOT/'fixtures/component2_quotation_bundle.mock_test_only.json'
        b=json.loads(fixture.read_text(encoding='utf-8'))
        self.assertIn('MOCK',b['supplier_id'])
        self.assertEqual(len(import_bundle(b,self.state())['proposed_state']['quotes']),1)
        schema=json.loads((ROOT/'api/contracts/component2_quotation_bundle.schema.json').read_text())
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['properties']['quotations']['items']['required']),set(b['quotations'][0]))


class ForecastBridgeTests(unittest.TestCase):
    def request(self,**changes):
        return dict({'series_id':'S003:Anamalu:1 Kg.','target_month':'2025-08-01','unit':'LKR/1 Kg.',
                     'quantity':10,'expense_scope':'ingredient_component'},**changes)
    def test_actual_saved_prophet_forecast_replayed_without_fitting(self):
        r=preview(self.request());self.assertEqual(r['model'],'prophet')
        self.assertEqual(r['status'],'available_historical_replay');self.assertAlmostEqual(r['forecast_yhat'],320.6111238665773)
        self.assertEqual(r['ingredient_subtotal_lkr'],3206.11);self.assertFalse(r['applied_to_event_budget'])
        self.assertFalse(r['calibrated_current_event_forecast'])
    def test_current_october_event_is_not_extrapolated(self):
        r=preview(self.request(target_month='2026-10-01'))
        self.assertEqual(r['status'],'blocked');self.assertIsNone(r['forecast_yhat']);self.assertIsNone(r['ingredient_subtotal_lkr'])
        self.assertEqual(r['last_supported_month'],'2026-09-01')
    def test_unit_scope_quantity_and_date_gates(self):
        for update in ({'unit':'LKR/plate'},{'expense_scope':'whole_catering_package'},{'quantity':True},
                       {'quantity':0},{'target_month':'2025-08-22'},{'series_id':'vendor_price'}):
            with self.assertRaises(ValueError):preview(self.request(**update))
    def test_indices_are_context_not_currency(self):
        p=dict(series_id='S001:CCPI:base2021',target_month='2025-04-01',unit='index (base 2021)',quantity=None,expense_scope='market_context_only')
        r=preview(p);self.assertEqual(r['model'],'last_value');self.assertIsNone(r['ingredient_subtotal_lkr'])
        with self.assertRaises(ValueError):preview(dict(p,quantity=10))
    def test_source_review_and_negative_values_block_cost_conversion(self):
        selected,rows=artifacts();row=next(r for r in rows if r['series_id']=='S003:Anamalu:1 Kg.' and r['model']=='prophet' and r['ds']=='2025-08-01')
        row['source_quality_review']='1'
        with patch('component4.forecast_bridge.artifacts',return_value=(selected,rows)):
            self.assertEqual(preview(self.request())['status'],'blocked')
            self.assertIsNone(preview(self.request())['ingredient_subtotal_lkr'])
        row['source_quality_review']='0';row['forecast_yhat']='-1'
        with patch('component4.forecast_bridge.artifacts',return_value=(selected,rows)):
            self.assertEqual(preview(self.request())['reason'],'nonpositive_or_invalid_saved_forecast')
    def test_catalog_and_hash_tampering(self):
        c=catalog();self.assertEqual(len(c['series']),12)
        self.assertEqual(sum(s['selected_model']=='prophet' for s in c['series']),3)
        (ROOT/'work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as folder:
            root=Path(folder);p=root/(BASE+'selected_models.json');p.parent.mkdir(parents=True);p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'hash_mismatch'):catalog(root)


class Component2ForecastHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=PlannerDashboard();cls.server=create_server(0,dashboard=cls.api)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,payload=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        c.request('GET' if payload is None else 'POST',path,body=None if payload is None else json.dumps(payload),headers={'Content-Type':'application/json'})
        r=c.getresponse();result=json.loads(r.read());c.close();return r.status,result
    def test_import_and_forecast_endpoints(self):
        status,r=self.request('/api/planner/component2/import',{'bundle_json':json.dumps(bundle()),'state':self.api.config()['default_state']})
        self.assertEqual(status,200);self.assertEqual(len(r['proposed_state']['quotes']),1)
        self.assertEqual(self.request('/api/planner/forecast-catalog')[1]['mode'],'archived_retrospective_replay_only')
        p=ForecastBridgeTests().request(target_month='2026-10-01')
        self.assertEqual(self.request('/api/planner/forecast-preview',p)[1]['status'],'blocked')
    def test_duplicate_bundle_keys_rejected(self):
        status,_=self.request('/api/planner/component2/import',{'bundle_json':'{"x":1,"x":2}','state':self.api.config()['default_state']})
        self.assertEqual(status,400)
