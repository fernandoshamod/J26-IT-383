"""Stage 10 must fail closed rather than turn structural passes into readiness."""
import unittest
from pathlib import Path
from component4.final_dataset_audit import audit, chronological_audit, historical_audit

ROOT = Path(__file__).resolve().parents[1]


class FinalAuditTests(unittest.TestCase):
    def test_current_data_not_ready(self):
        r = audit(ROOT)
        self.assertEqual(r['dataset_status'], 'NOT READY')
        self.assertFalse(r['freeze_authorized'])
        self.assertEqual(r['counts']['generated_master_financial_scenarios'], 0)
        self.assertEqual(r['counts']['observed_event_financial_outcome_records'], 0)
        self.assertEqual(r['counts']['xgboost_records'], 0)
        self.assertEqual(r['counts']['gnn_graphs'], 0)

    def test_all_twenty_requirements_present(self):
        checks = audit(ROOT)['checks']
        self.assertEqual([r['id'] for r in checks], list(range(1, 21)))
        self.assertEqual(checks[4]['status'], 'NOT TESTABLE')
        self.assertEqual(checks[14]['status'], 'NOT TESTABLE')

    def test_software_pass_cannot_authorize_freeze(self):
        r = audit(ROOT, {'exit_code': 0, 'tests_run': 178})
        self.assertEqual(r['checks'][17]['status'], 'PASS')
        self.assertFalse(r['freeze_authorized'])
        self.assertEqual(r['dataset_status'], 'NOT READY')

    def test_test_failure_visible(self):
        r = audit(ROOT, {'exit_code': 1, 'tests_run': 178})
        self.assertEqual(r['checks'][17]['status'], 'NOT VERIFIED')

    def test_empty_time_series_not_pass(self):
        self.assertEqual(historical_audit([])['status'], 'FAIL')
        self.assertEqual(chronological_audit([], [])['status'], 'FAIL')

    def test_series_cannot_mix_units(self):
        rows = [dict(series_id='a', ds='2026-01-01', y='1', unit='LKR/kg', source_id='s', observation_kind='price'),
                dict(series_id='a', ds='2026-02-01', y='2', unit='index', source_id='s', observation_kind='price')]
        self.assertEqual(historical_audit(rows)['status'], 'FAIL')

    def test_unknown_or_duplicate_split_keys_rejected(self):
        obs = [dict(series_id='a', ds='2026-01-01')]
        split = [dict(series_id='a', ds='2026-02-01', partition='train')]
        self.assertIn('unknown_split_observation', chronological_audit(obs, split)['issues'])
        self.assertIn('duplicate_split_keys', chronological_audit(obs, split + split)['issues'])

    def test_future_training_leakage_rejected(self):
        obs = [dict(series_id='a', ds=x) for x in ['2026-01-01', '2026-02-01', '2026-03-01']]
        split = [dict(series_id='a', ds=x, partition=p) for x, p in zip(
            ['2026-03-01', '2026-02-01', '2026-01-01'], ['train', 'validation', 'test'])]
        self.assertEqual(chronological_audit(obs, split)['status'], 'FAIL')

    def test_empty_target_distribution_unavailable_not_zero_risk(self):
        r = audit(ROOT)
        self.assertTrue(all(v is None for v in r['counts']['target_class_distributions'].values()))
        self.assertIsNone(r['counts']['financial_split_group_counts'])


if __name__ == '__main__':
    unittest.main()
