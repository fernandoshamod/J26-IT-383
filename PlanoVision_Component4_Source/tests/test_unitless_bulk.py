from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from component4.engine import fingerprint
from component4.unitless_bulk import blockers, generate, generate_test, master_rows, validate, validate_bulk_bundle, write

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    model = json.loads((ROOT / 'config/unitless_pilot_candidate.v0.3.proposed.json').read_text())
    columns = json.loads((ROOT / 'work/original_schema.json').read_text())['Master_Data']['data'][0]
    return {'version': 'unitless-bulk.0.1', 'record_kind': 'mock_unitless_bulk_test',
            'cost_unit': 'dimensionless_score', 'currency': None,
            'master_columns': columns, 'master_schema_sha256': fingerprint(columns),
            'field_semantics_version': 'unitless-master-mapping.0.1',
            'financial_model': model, 'financial_model_sha256': fingerprint(model),
            'sampling': {'roots': 10, 'states_per_root': 3, 'replications_per_state': 2, 'rows': 60,
                         'seed': 20261022, 'attempt_cap_per_root': 100,
                         'event_root_quotas': {'Wedding': 5, 'Corporate': 5},
                         'states': ['baseline', 'guest_minus_one', 'guest_plus_one'],
                         'root_policy': 'unique_baselines_uniform_discrete_rejection_sampling',
                         'event_date_start': '2027-01-01', 'event_date_end': '2027-12-31'},
            'split_policy': {'protocol': 'conditional_in_simulator', 'fractions': [.6, .2, .2], 'tolerance': .05},
            'acceptance_criteria': {'invalid_financial_rows': 0, 'invalid_spatial_rows': 0, 'missing_provenance_rows': 0,
                                    'duplicate_ids': 0, 'distinct_baselines': 10, 'unseen_template_evaluation': False,
                                    'economic_realism_claim': False, 'class_balancing': False}}


class UnitlessBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = generate_test(fixture())

    def test_counts_and_disjoint_ledger(self):
        self.assertEqual(len(self.bundle['planning']), 60)
        self.assertEqual(len(self.bundle['line_items']), 420)
        self.assertTrue(validate_bulk_bundle(self.bundle))

    def test_reproducibility_and_key_order(self):
        self.assertEqual(self.bundle, generate_test(dict(reversed(list(fixture().items())))))

    def test_changed_seed_changes_ids(self):
        c = fixture()
        c['sampling']['seed'] += 1
        self.assertNotEqual(self.bundle['planning'][0]['scenario_id'], generate_test(c)['planning'][0]['scenario_id'])

    def test_missing_authorization_blocks(self):
        c = fixture()
        c['record_kind'] = 'hypothetical_unitless_bulk_proposal'
        self.assertIn('missing_or_mismatched:explicit_bulk_authorization', blockers(c))
        with self.assertRaisesRegex(ValueError, 'bulk_execution_blocked'):
            generate(c, {})

    def test_pilot_approval_cannot_authorize_bulk(self):
        c = fixture()
        c['record_kind'] = 'hypothetical_unitless_bulk_proposal'
        a = json.loads((ROOT / 'config/unitless_pilot_authorization.v0.3.user.json').read_text())
        self.assertIn('missing_or_mismatched:configuration_sha256', blockers(c, a))
        self.assertIn('missing_or_mismatched:scenario_count', blockers(c, a))

    def test_no_file_creation_without_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'bulk'
            with self.assertRaises(ValueError):
                write(fixture(), {}, dest, None, [])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_bad_count_and_changed_model(self):
        c = fixture()
        c['sampling']['rows'] = True
        with self.assertRaises(ValueError):
            validate(c)
        c = fixture()
        c['financial_model']['coefficients']['catering'] += 1
        with self.assertRaisesRegex(ValueError, 'financial_model_hash'):
            validate(c)

    def test_corrupt_arithmetic_rejected(self):
        b = deepcopy(self.bundle)
        b['outcomes'][0]['simulated_profit_score'] += 1
        with self.assertRaises(ValueError):
            validate_bulk_bundle(b)

    def test_no_family_or_identical_planning_split_leakage(self):
        self.assertEqual(self.bundle['manifest']['split_audit']['status'], 'PASS')
        self.assertFalse(self.bundle['manifest']['split_audit']['unseen_venue_claim_supported_by_protocol'])
        self.assertTrue(self.bundle['manifest']['split_audit']['shared_source_overlap']['venue_template'])

    def test_same_shocks_across_family_interventions(self):
        latents = self.bundle['latent_DO_NOT_USE_AS_FEATURES']
        first = {k: v for k, v in latents[0].items() if k != 'scenario_id'}
        self.assertEqual(first, {k: v for k, v in latents[2].items() if k != 'scenario_id'})
        self.assertEqual(first, {k: v for k, v in latents[4].items() if k != 'scenario_id'})

    def test_mock_cannot_use_public_generator(self):
        with self.assertRaises(ValueError):
            generate(fixture(), {})

    def test_schema_nulls_and_unitless_mapping(self):
        rows = master_rows(self.bundle, fixture()['master_columns'])
        self.assertEqual(len(rows[0]), 46)
        for row in rows:
            for name in ('Historical_Mean_Cost', 'Vendor_Price_Volatility', 'Financial_Health_Score',
                         'VIP_Area_m2', 'Quoted_Decoration_Cost', 'Quoted_Lighting_Cost', 'Quoted_Security_Cost', 'Transport_Cost', 'Misc_Cost'):
                self.assertIsNone(row[name])
            self.assertEqual(row['Data_Source'], 'MOCK_UNITLESS_TEST_NOT_MARKET_DATA')
            total = sum(row[k] for k in ('Quoted_Catering_Cost', 'Quoted_AV_Cost', 'Quoted_Venue_Rental_Cost',
                                         'Quoted_Equipment_Rental_Cost', 'Quoted_Labor_Cost'))
            self.assertAlmostEqual(total, row['Forecasted_Total_Cost'])

    def test_invalid_labels_and_shocks(self):
        for section, key, value in [('outcomes', 'simulated_vendor_cost_anomaly', True),
                                    ('latent_DO_NOT_USE_AS_FEATURES', 'cost_multiplier', 100),
                                    ('planning', 'reserve_score', 100), ('provenance', 'venue_template_id', 'fake-new-venue')]:
            b = deepcopy(self.bundle)
            b[section][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_bulk_bundle(b)

    def test_atomic_export_failure_leaves_no_dataset(self):
        from unittest.mock import patch
        def fail(*args):
            raise RuntimeError('intentional_test_export_failure')
        with tempfile.TemporaryDirectory() as tmp, patch('component4.unitless_bulk.generate', return_value=deepcopy(self.bundle)):
            with self.assertRaisesRegex(RuntimeError, 'intentional_test_export_failure'):
                write(fixture(), {}, Path(tmp) / 'test', None, fixture()['master_columns'], exporter=fail)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
