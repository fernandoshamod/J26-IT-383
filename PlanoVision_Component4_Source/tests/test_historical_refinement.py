from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from component4.historical_refinement import build, validate, write_new_package, read_csv, sha, expected_observations, verify_workbook

ROOT = Path(__file__).resolve().parents[1]


class HistoricalRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build(ROOT, '2026-10-12')

    def test_complete_observational_export(self):
        self.assertEqual(len(self.bundle['observations']), 5110)
        self.assertEqual(len(self.bundle['closed_month_observations']), 5003)
        self.assertTrue(validate(self.bundle))

    def test_reproducible_complete_build(self):
        self.assertEqual(self.bundle, build(ROOT, '2026-10-12'))

    def test_bad_arithmetic_rejected(self):
        b = deepcopy(self.bundle); b['observations'][0]['y'] = '1'
        with self.assertRaises(ValueError): validate(b)

    def test_missing_provenance_rejected(self):
        b = deepcopy(self.bundle); b['observation_provenance'].pop()
        with self.assertRaises(ValueError): validate(b)

    def test_synthetic_origin_rejected(self):
        b = deepcopy(self.bundle); b['observations'][0]['synthetic_origin'] = True
        with self.assertRaises(ValueError): validate(b)

    def test_invented_publication_date_rejected(self):
        b = deepcopy(self.bundle); b['observations'][0]['publication_date'] = '2026-09-01'
        with self.assertRaises(ValueError): validate(b)

    def test_split_duplicate_rejected(self):
        b = deepcopy(self.bundle); b['chronological_partitions_proposed'].append(b['chronological_partitions_proposed'][0])
        with self.assertRaises(ValueError): validate(b)

    def test_split_missing_row_rejected(self):
        b = deepcopy(self.bundle); b['chronological_partitions_proposed'].pop()
        with self.assertRaises(ValueError): validate(b)

    def test_not_a_training_authorization(self):
        b = deepcopy(self.bundle); b['model_training_authorized'] = True
        with self.assertRaises(ValueError): validate(b)

    def test_csv_atomic_preserves_sources_and_existing_export(self):
        before = {p: sha(ROOT/p) for p in self.bundle['source_hashes']}
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as td:
            target = Path(td)/'new_export'
            stats = write_new_package(self.bundle, target, ROOT)
            self.assertEqual(stats['observations'], len(read_csv(target/'historical_observations.csv')))
            initial = sha(target/'historical_observations.csv')
            with self.assertRaises(FileExistsError): write_new_package(self.bundle, target, ROOT)
            self.assertEqual(initial, sha(target/'historical_observations.csv'))
        self.assertEqual(before, {p: sha(ROOT/p) for p in before})

    def test_changed_source_hash_blocks_before_writing(self):
        b = deepcopy(self.bundle)
        b['source_hashes']['data/processed/inflation.csv'] = '0'*64
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as td:
            target = Path(td)/'blocked'
            with self.assertRaises(ValueError): write_new_package(b, target, ROOT)
            self.assertFalse(target.exists())

    def test_recipe_keeps_all_weekly_contributors(self):
        rows = [{'source_record_id': f'r{i}', 'year': '2026', 'month': '9', 'item_raw': 'Rice',
                 'unit_raw': 'kg', 'current_price_lkr': '100', 'reported_week': f'W{i}',
                 'parse_status': 'Parsed'} for i in [1, 2]]
        expected = expected_observations([], rows)
        self.assertEqual(expected[('S003:Rice:kg', '2026-09-01')], {'r1', 'r2'})
        rows[1]['reported_week'] = rows[0]['reported_week']
        self.assertEqual(expected_observations([], rows), {})

    def test_bundle_metadata_cannot_bypass_source_rebuild(self):
        b = deepcopy(self.bundle)
        b['observations'][0]['model_use_status'] = 'approved for training'
        # Pure arithmetic can still reconcile; persistent export must reject this claim.
        self.assertTrue(validate(b))
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as td:
            target = Path(td)/'blocked'
            with self.assertRaises(ValueError): write_new_package(b, target, ROOT)
            self.assertFalse(target.exists())

    def test_export_failure_without_saved_file_is_atomic(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as td:
            target = Path(td)/'failed_export'
            with patch('component4.historical_refinement.subprocess.run', return_value=SimpleNamespace(returncode=1)):
                with self.assertRaises(ValueError):
                    write_new_package(self.bundle, target, ROOT, 'test-node', 'test-exporter')
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_saved_workbook_all_cells_and_recovered_copy(self):
        path = ROOT/'data/refined/historical.v0.1-20261012/historical_observations.xlsx'
        if not path.exists():
            self.skipTest('Versioned historical workbook has not been exported in this checkout')
        self.assertTrue(verify_workbook(path, self.bundle))
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as td:
            target = Path(td)/'verified_export'
            stats = write_new_package(self.bundle, target, ROOT, workbook_source=path,
                                      source_renderer_returncode=3221226505)
            self.assertEqual(sha(path), sha(target/'historical_observations.xlsx'))
            self.assertEqual(stats['xlsx_saved_cell_validation'], 'PASS')
            self.assertIn('nonzero', stats['xlsx_renderer_warning'])


if __name__ == '__main__': unittest.main()
