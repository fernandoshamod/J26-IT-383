import json
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from component4.local_dashboard_http import create_server


class UnitlessResearchHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server(0,enable_unitless_research=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)

    def request(self,path,payload=None):
        req=Request(self.base+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try: result=urlopen(req,timeout=10)
        except HTTPError as exc: result=exc
        with result:return result.status,json.loads(result.read())

    def inputs(self):
        return {'guests':100,'event_hours':4,'stage_width_m':3,'stage_length_m':4,'budget_score':3,'retained_receipts_score':4}

    def test_domains_explicitly_unitless(self):
        status,r=self.request('/api/research/unitless/domains')
        self.assertEqual(status,200)
        self.assertEqual(r['cost_unit'],'dimensionless_score')
        self.assertIsNone(r['financial_health_score'])

    def test_calculation_and_comparison(self):
        code,r=self.request('/api/research/unitless/calculate',{'event_type':'Wedding','inputs':self.inputs(),'draws':100})
        self.assertEqual(code,200)
        self.assertEqual(r['result']['status'],'calculated')
        code,r=self.request('/api/research/unitless/what-if',{'event_type':'Wedding','baseline':self.inputs(),'alternative_changes':{'guests':120},'draws':100})
        self.assertEqual(code,200)
        self.assertGreater(r['delta']['planned_cost_score'],0)

    def test_live_endpoint_cannot_activate_research(self):
        code,r=self.request('/api/live/calculate',{'event_type':'Wedding'})
        self.assertEqual(code,200)
        self.assertEqual(r['status'],'blocked')
        self.assertFalse(r['provenance']['is_trained_model_prediction'])

    def test_mode_override_rejected(self):
        code,r=self.request('/api/research/unitless/calculate',{'event_type':'Wedding','inputs':self.inputs(),'mode':'live','draws':100})
        self.assertEqual(code,422)

    def test_experimental_health_is_separate_and_draft(self):
        code,r=self.request('/api/research/experimental/planning-health',{'event_type':'Wedding','inputs':self.inputs(),'draws':100})
        self.assertEqual(code,200)
        self.assertEqual(r['indicator']['score'],100)
        self.assertFalse(r['indicator']['policy']['empirically_validated'])
        self.assertIsNone(r['decision']['result']['financial_health_score'])

    def test_health_spatial_block_has_no_score(self):
        code,r=self.request('/api/research/experimental/planning-health',{'event_type':'Wedding','inputs':{**self.inputs(),'guests':181},'draws':100})
        self.assertEqual(code,200);self.assertIsNone(r['indicator']['score'])

    def test_post_invoice_detector_not_prediction(self):
        from test_experimental_indicators import fixture
        p=fixture();p['invoice'][0]['unit_rate']=1100
        code,r=self.request('/api/research/experimental/quote-invoice',p)
        self.assertEqual(code,200);self.assertTrue(r['line_comparisons'][0]['rate_increase_flag'])
        self.assertIsNone(r['Vendor_Cost_Anomaly_prediction'])

    def test_experimental_bad_payload_rejected(self):
        code,_=self.request('/api/research/experimental/quote-invoice',{'mode':'live'})
        self.assertEqual(code,422)

    def test_disabled_by_default(self):
        server=create_server(0)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with self.assertRaises(HTTPError) as caught:
                urlopen(f'http://127.0.0.1:{server.server_port}/api/research/unitless/domains',timeout=5)
            self.assertEqual(caught.exception.code,404)
        finally:
            server.shutdown();server.server_close();worker.join(timeout=3)
