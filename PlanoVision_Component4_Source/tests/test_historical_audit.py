from copy import deepcopy
import unittest
from component4.historical_audit import reconcile, month_number


class HistoricalAuditTests(unittest.TestCase):
    def setUp(self):
        self.source = {'source_record_id': 'index-1', 'month': '2026-09-01',
                       'source_id': 'S001', 'index_type': 'CCPI', 'base_year': '2021',
                       'index_value': '124.3', 'quality_flag': ''}
        self.row = {'ds': '2026-09-01', 'y': '124.3', 'series_id': 'S001:CCPI:base2021',
                    'source_id': 'S001', 'unit': 'index (base 2021)',
                    'cost_category': 'inflation_index', 'observation_kind': 'observed_monthly_index',
                    'provenance': 'index-1'}

    def audit(self, rows=None, sources=None):
        return reconcile(rows or [self.row], sources or [self.source], [], '2026-10-12')

    def test_valid_index_reconciles(self):
        self.assertEqual(self.audit()['reconciled_rows'], 1)

    def test_value_tampering_rejected(self):
        self.row['y'] = '125'
        self.assertEqual(self.audit()['reconciled_rows'], 0)

    def test_wrong_unit_rejected(self):
        self.row['unit'] = 'LKR'
        self.assertEqual(self.audit()['reconciled_rows'], 0)

    def test_unknown_lineage_rejected(self):
        self.row['provenance'] = 'missing'
        self.assertEqual(self.audit()['reconciled_rows'], 0)

    def test_duplicate_key_flagged(self):
        self.assertIn('duplicate_series_date', self.audit([self.row, deepcopy(self.row)])['issue_rows'][0]['reasons'])

    def test_open_month_not_a_closed_month_experiment(self):
        self.row['ds'] = self.source['month'] = '2026-10-01'
        result = self.audit()
        self.assertEqual(result['reconciled_rows'], 1)
        self.assertEqual(result['open_or_future_month_rows'], 1)
        self.assertEqual(result['series'][0]['closed_reconciled_rows'], 0)

    def test_nonfinite_rejected(self):
        self.row['y'] = 'NaN'
        self.assertEqual(self.audit()['reconciled_rows'], 0)

    def test_date_must_be_month_start(self):
        with self.assertRaises(ValueError):
            month_number('2026-09-02')

    def test_quality_flags_not_silently_dropped(self):
        self.source['quality_flag'] = 'review'
        self.assertEqual(self.audit()['source_quality_review_rows'], 1)

    def test_retail_mean_and_week_counts(self):
        records = [{'source_record_id': f'r{i}', 'year': '2026', 'month': '9',
                    'item_raw': 'Rice', 'unit_raw': '1 kg', 'source_id': 'S003',
                    'reported_week': f'2026-09-W{i}', 'current_price_lkr': str(i*100),
                    'parse_status': 'Parsed', 'quality_flag': ''} for i in (1, 2)]
        row = {'ds': '2026-09-01', 'y': '150', 'series_id': 'S003:Rice:1 kg',
               'source_id': 'S003', 'unit': 'LKR/1 kg', 'cost_category': 'ingredient_price_proxy',
               'observation_kind': 'monthly mean of published weekly prices',
               'reported_weeks': '2', 'provenance': 'r1;r2'}
        self.assertEqual(reconcile([row], [], records, '2026-10-12')['reconciled_rows'], 1)
        records[1]['reported_week'] = records[0]['reported_week']
        self.assertEqual(reconcile([row], [], records, '2026-10-12')['reconciled_rows'], 0)


if __name__ == '__main__':
    unittest.main()
