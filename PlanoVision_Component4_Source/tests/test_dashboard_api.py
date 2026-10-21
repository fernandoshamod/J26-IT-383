import copy,json,unittest
from pathlib import Path
from component4.api import dashboard_request
from component4.engine import evaluate

ROOT=Path(__file__).resolve().parents[1]
class DashboardTests(unittest.TestCase):
    def setUp(self):self.config=json.loads((ROOT/'config/simulator.v0.1.template.json').read_text())
    def test_live_missing_config_blocked(self):
        result=dashboard_request(self.config,{'event_type':'Wedding'})
        self.assertEqual(result['status'],'blocked');self.assertIsNone(result['costs'])
    def test_client_cannot_switch_mode(self):
        with self.assertRaises(ValueError):dashboard_request(self.config,{'event_type':'Wedding','mode':'mock_test_fixture'})
    def test_client_cannot_submit_outcomes(self):
        with self.assertRaises(ValueError):dashboard_request(self.config,{'event_type':'Wedding','outcome':{'cost_lkr':0}})
    def test_live_what_if_blocked_no_delta(self):
        result=dashboard_request(self.config,{'event_type':'Corporate','changes':{'guest_count':50}},operation='what-if')
        self.assertEqual(result['comparison_status'],'blocked');self.assertIsNone(result['delta'])
    def test_template_contains_no_numerical_values(self):
        def visit(value):
            if isinstance(value,dict):
                for v in value.values():visit(v)
            elif isinstance(value,list):
                for v in value:visit(v)
            else:self.assertFalse(isinstance(value,(int,float)) and not isinstance(value,bool))
        visit(self.config)
    def test_fixture_response_contracts(self):
        from component4.contracts import validate_contract
        schema=json.loads((ROOT/'api/contracts/financial_dashboard.response.schema.json').read_text())
        for filename in ['wedding.response.mock.json','corporate.response.mock.json','blocked.response.json']:
            response=json.loads((ROOT/'api/mock'/filename).read_text())
            validate_contract(response,schema)
            self.assertIs(response['provenance']['is_trained_model_prediction'],False)
        response['provenance']['is_trained_model_prediction']=True
        with self.assertRaises(ValueError):validate_contract(response,schema)
