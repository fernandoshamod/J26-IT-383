import json
from pathlib import Path
import unittest
from component4.planner_input import collect_planner_inputs

ROOT = Path(__file__).resolve().parents[1]


class PlannerInputTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'config/lkr_research.v2.0.json').read_text())

    def collect(self, answers):
        prompts, messages = [], []
        entries = iter(answers)
        def reader(prompt):
            prompts.append(prompt)
            return next(entries)
        result = collect_planner_inputs(self.config, 'Wedding', reader=reader, writer=messages.append)
        return result, prompts, messages

    def test_defaults_and_no_stage_prompts(self):
        (inputs, dims), prompts, messages = self.collect(['']*7)
        self.assertEqual(inputs['venue_area_m2'], dims['venue_width_m']*dims['venue_length_m'])
        self.assertFalse(any('stage' in p.lower() for p in prompts))
        self.assertEqual(dims, {'venue_width_m':20.0,'venue_length_m':25.0})
        self.assertEqual(inputs['venue_area_m2'],500)
        self.assertEqual(inputs['stage_length_m'],6)
        self.assertEqual(inputs['stage_width_m'], 4)
        self.assertEqual(inputs['retained_receipts_lkr'], 2500000)

    def test_dimension_product(self):
        (inputs, _), _, _ = self.collect(['150','5','20','30','2,000,000','2,500,000','15'])
        self.assertEqual(inputs['venue_area_m2'], 600)

    def test_invalid_dimension_reprompts(self):
        (inputs, _), _, _ = self.collect(['','','nan','0','25','40','','',''])
        self.assertEqual(inputs['venue_area_m2'],1000)

    def test_outside_engine_area_blocks(self):
        with self.assertRaisesRegex(ValueError, 'venue usable area'):
            self.collect(['','','2','3','','',''])

    def test_continuous_dimensions(self):
        (inputs, _), _, _ = self.collect(['','','20.5','25.25','','',''])
        self.assertEqual(inputs['venue_area_m2'],517.625)

    def test_capacity_boundary(self):
        from component4.lkr_research import calculate, load_config
        config, evidence = load_config()
        (inputs, _), _, _ = self.collect(['277','','','','','',''])
        self.assertLessEqual(calculate(config,evidence,inputs)['space_utilization'],1)
        inputs['guests']=278
        with self.assertRaisesRegex(ValueError,'spatially_infeasible'):
            calculate(config,evidence,inputs)


if __name__ == '__main__':
    unittest.main()
