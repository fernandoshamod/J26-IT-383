from copy import deepcopy
import json
from pathlib import Path
import unittest
from component4.lkr_inference import LKRResearchInference
from scripts.research_pipeline.build_pp1_evidence import check_case,request_for

ROOT=Path(__file__).resolve().parents[1]


class PP1EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/'config/pp1_demo_cases.v1.0.json').read_text())
        cls.service=LKRResearchInference(cls.config['model_run'])

    def test_three_actual_cases_and_replay(self):
        for case in self.config['cases']:
            p=request_for(self.config,case)
            response=self.service.request(p,'what-if');check_case(case,response)
            self.assertEqual(response,self.service.request(p,'what-if'))

    def test_saved_case_files_match_actual_models(self):
        folder=ROOT/'reports/pp1_readiness_20261015'
        for case in self.config['cases']:
            saved=json.loads((folder/(case['id']+'.json')).read_text())
            self.assertEqual(saved['response'],self.service.request(request_for(self.config,case),'what-if'))
            self.assertEqual(saved['purpose'],'illustrative_synthetic_demo_not_training_or_observed_record')

    def test_valid_demo_tampering_detected(self):
        case=self.config['cases'][0];r=self.service.request(request_for(self.config,case),'what-if')
        modified=deepcopy(r);modified['alternative']['plan']['margin_feasible']=False
        with self.assertRaises(ValueError):check_case(case,modified)

    def test_spatial_nulls_are_mandatory(self):
        case=self.config['cases'][2];r=self.service.request(request_for(self.config,case),'what-if')
        modified=deepcopy(r);modified['alternative']['model_scores']={'Budget_Overrun':0.1}
        with self.assertRaises(ValueError):check_case(case,modified)

    def test_packet_documents_exist(self):
        folder=ROOT/'reports/pp1_readiness_20261015'
        for name in ('README.md','requirements_traceability.md','architecture_and_progress.md',
                     'research_gap_and_method_rationale.md','risk_and_remaining_actions.md',
                     'viva_walkthrough_and_qa.md','planner_feedback_protocol.md','demo_cost_margin.png'):
            self.assertTrue((folder/name).is_file())
            self.assertGreater((folder/name).stat().st_size,0)
