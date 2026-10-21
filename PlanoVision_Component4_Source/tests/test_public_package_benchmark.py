import copy
import unittest
from pathlib import Path

from component4.public_package_benchmark import estimate_package, load_evidence


class PublicPackageBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.evidence = load_evidence(Path(__file__).resolve().parents[1] / 'config/public_hotel_benchmark.v0.1.json')

    def test_radisson_component_reconciliation(self):
        r = estimate_package(self.evidence, 'HOTEL-PUB-R001', 100, 'Wedding')
        self.assertEqual(r['advertised_package_amount_lkr'], 980000)
        self.assertEqual(r['published_charge_amount_lkr'], 98000)
        self.assertEqual(r['known_components_subtotal_lkr'], 1078000)
        self.assertIsNone(r['complete_event_total_lkr'])
        self.assertIsNone(r['confirmed_all_in_package_total_lkr'])

    def test_starting_nett_is_not_tax_calibration(self):
        r = estimate_package(self.evidence, 'HOTEL-PUB-R004', 100, 'Corporate')
        self.assertEqual(r['advertised_package_amount_lkr'], 650000)
        self.assertEqual(r['published_price_kind'], 'Starting price')
        self.assertIsNone(r['published_charge_amount_lkr'])

    def test_silver_surcharge_not_misclassified(self):
        r = estimate_package(self.evidence, 'HOTEL-PUB-R010', 100, 'Wedding')
        self.assertEqual(r['published_charge_kind'], 'unspecified_surcharge')
        self.assertEqual(r['known_components_subtotal_lkr'], 704000)

    def test_no_created_outcomes_or_labels(self):
        r = estimate_package(self.evidence, 'HOTEL-PUB-R006', 100, 'Wedding')
        for key in ('actual_cost_lkr', 'profit_lkr', 'risk_labels'):
            self.assertIsNone(r[key])
        self.assertFalse(r['eligible_as_financial_risk_training_record'])
        self.assertFalse(r['is_observed_event_outcome'])

    def test_guests_validation(self):
        for n in [0, -1, True, 2.5, '100']:
            with self.subTest(n=n), self.assertRaises(ValueError):
                estimate_package(self.evidence, 'HOTEL-PUB-R001', n, 'Wedding')

    def test_wrong_archetype_rejected(self):
        with self.assertRaisesRegex(ValueError, 'scope_mismatch'):
            estimate_package(self.evidence, 'HOTEL-PUB-R004', 100, 'Wedding')

    def test_expired_rate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'expiry'):
            estimate_package(self.evidence, 'HOTEL-PUB-R001', 100, 'Wedding', '2028-01-01')

    def test_special_day_scope(self):
        with self.assertRaisesRegex(ValueError, 'poya_confirmation'):
            estimate_package(self.evidence, 'HOTEL-PUB-R005', 100, 'Wedding', '2026-10-12')
        r = estimate_package(self.evidence, 'HOTEL-PUB-R005', 100, 'Wedding', '2026-10-18')
        self.assertEqual(r['advertised_package_amount_lkr'], 600000)

    def test_source_is_not_mutated(self):
        before = copy.deepcopy(self.evidence)
        estimate_package(self.evidence, 'HOTEL-PUB-R001', 100, 'Wedding')
        self.assertEqual(self.evidence, before)

    def test_unknown_and_duplicate_ids_rejected(self):
        for e in [self.evidence, {'rates': self.evidence['rates'] * 2}]:
            with self.assertRaises(ValueError):
                estimate_package(e, 'missing' if e is self.evidence else 'HOTEL-PUB-R001', 100, 'Wedding')

    def test_invalid_rate_rejected(self):
        e = copy.deepcopy(self.evidence)
        e['rates'][0]['Rate_LKR'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'invalid_published_rate'):
            estimate_package(e, 'HOTEL-PUB-R001', 100, 'Wedding')

    def test_double_charge_rejected(self):
        e = copy.deepcopy(self.evidence)
        e['rates'][0]['Unspecified_Surcharge_Points'] = 10
        with self.assertRaisesRegex(ValueError, 'overlapping_charge'):
            estimate_package(e, 'HOTEL-PUB-R001', 100, 'Wedding')
