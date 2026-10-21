import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from component4.benchmark_api import benchmark_request
from component4.contracts import validate_contract
from component4.local_dashboard_http import create_server
from component4.public_package_benchmark import load_evidence

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=3)

    def request(self, path, payload=None, *, raw=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else raw
        req = Request(self.base + path, data=body, headers=headers or {'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def payload(self):
        return {'evidence_id': 'HOTEL-PUB-R001', 'event_type': 'Wedding', 'guests': 100}

    def test_health_and_no_mock_activation(self):
        code, response = self.request('/api/health')
        self.assertEqual(code, 200)
        self.assertFalse(response['mock_fallback_enabled'])
        self.assertFalse(response['live_calculation_approved'])

    def test_package_catalog(self):
        code, response = self.request('/api/benchmark/packages')
        self.assertEqual(code, 200)
        self.assertEqual(len(response['packages']), 11)
        self.assertFalse(response['is_trained_model_prediction'])

    def test_estimate_response_schema(self):
        code, response = self.request('/api/benchmark/estimate', self.payload())
        self.assertEqual(code, 200)
        schema = json.loads((ROOT / 'api/contracts/public_package_benchmark.response.schema.json').read_text())
        validate_contract(response, schema)
        self.assertEqual(response['known_components_subtotal_lkr'], 1078000)
        self.assertIsNone(response['complete_event_total_lkr'])

    def test_what_if_delta(self):
        code, response = self.request('/api/benchmark/compare', {'evidence_id': 'HOTEL-PUB-R001', 'event_type': 'Wedding', 'baseline_guests': 100, 'alternative_guests': 120})
        self.assertEqual(code, 200)
        self.assertEqual(response['delta']['known_components_subtotal_lkr'], 215600)
        self.assertEqual(response['delta']['planned_guests'], 20)
        self.assertIsNone(response['delta']['profit_lkr'])
        self.assertEqual(response['full_budget_feasibility'], 'unavailable_incomplete_event_costs')

    def test_normal_live_stays_blocked(self):
        code, response = self.request('/api/live/calculate', {'event_type': 'Wedding'})
        self.assertEqual(code, 200)
        self.assertEqual(response['status'], 'blocked')
        self.assertIsNone(response['costs'])
        self.assertTrue(response['blockers'])

    def test_live_what_if_no_mock_fallback(self):
        code, response = self.request('/api/live/what-if', {'event_type': 'Corporate', 'changes': {'guest_count': 120}})
        self.assertEqual(code, 200)
        self.assertEqual(response['comparison_status'], 'blocked')
        self.assertIsNone(response['delta'])

    def test_cannot_submit_financial_or_mode_fields(self):
        for field in ('rates', 'approvals', 'outcomes', 'predictions', 'mode'):
            with self.subTest(field=field):
                code, response = self.request('/api/benchmark/estimate', {**self.payload(), field: {}})
                self.assertEqual(code, 422)

    def test_invalid_guest_count(self):
        for n in (0, -1, True, 1.5, None):
            with self.subTest(n=n):
                code, response = self.request('/api/benchmark/estimate', {**self.payload(), 'guests': n})
                self.assertEqual(code, 422)

    def test_invalid_json_and_nonfinite_rejected(self):
        for raw in (b'{broken', b'{"guests":NaN}'):
            code, response = self.request('/api/benchmark/estimate', raw=raw)
            self.assertEqual(code, 422)

    def test_wrong_content_type(self):
        code, response = self.request('/api/benchmark/estimate', self.payload(), headers={'Content-Type': 'text/plain'})
        self.assertEqual(code, 415)

    def test_body_size_limit(self):
        code, response = self.request('/api/benchmark/estimate', raw=b'x' * 8193)
        self.assertEqual(code, 413)

    def test_unknown_route(self):
        self.assertEqual(self.request('/api/demo/calculate', self.payload())[0], 404)

    def test_host_and_origin_firewall(self):
        self.assertEqual(self.request('/api/health', headers={'Host': 'evil.example'})[0], 403)
        headers = {'Content-Type': 'application/json', 'Origin': 'https://evil.example'}
        self.assertEqual(self.request('/api/benchmark/estimate', self.payload(), headers=headers)[0], 403)

    def test_early_post_rejections_deliver_status_without_dispatching_body(self):
        from unittest.mock import patch
        with patch('component4.local_dashboard_http.benchmark_request',side_effect=AssertionError('rejected_body_must_not_execute')):
            for _ in range(8):
                self.assertEqual(self.request('/api/benchmark/estimate',self.payload(),headers={'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
                self.assertEqual(self.request('/api/unknown',self.payload())[0],404)
                self.assertEqual(self.request('/api/benchmark/estimate',self.payload(),headers={'Content-Type':'text/plain'})[0],415)

    def test_scope_and_expiry_errors(self):
        self.assertEqual(self.request('/api/benchmark/estimate', {**self.payload(), 'event_type': 'Corporate'})[0], 422)
        self.assertEqual(self.request('/api/benchmark/estimate', {**self.payload(), 'event_date': '2028-01-01'})[0], 422)

    def test_response_cannot_claim_model_or_actual_outcome(self):
        _, response = self.request('/api/benchmark/estimate', self.payload())
        schema = json.loads((ROOT / 'api/contracts/public_package_benchmark.response.schema.json').read_text())
        for field in ('is_trained_model_prediction', 'is_observed_event_outcome'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_contract({**response, field: True}, schema)

    def test_transport_adapter_rejects_invalid_shapes(self):
        _, evidence = load_evidence(ROOT / 'config/public_hotel_benchmark.v0.1.json')
        for value in (None, [], {}, {**self.payload(), 'event_date': 1}, {**self.payload(), 'evidence_id': 1}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                benchmark_request(evidence, value)
