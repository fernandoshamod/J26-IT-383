from copy import deepcopy
import unittest
from component4.split_derivative import create_overlay, apply_overlay, validate_overlay, digest


class SplitDerivativeTests(unittest.TestCase):
    def fixture(self):
        rows = [{'Scenario_ID': str(i), 'Base_Event_ID': str(i), 'split_group_id': str(i),
                 'split': part, 'configuration_sha256': 'frozen', 'planned': str(i), 'risk': str(i % 2)}
                for i, part in enumerate(('train', 'train', 'validation', 'validation', 'test', 'test'))]
        ancestry = [dict(r, planning_fingerprint='fp' + r['Scenario_ID']) for r in rows]
        spec = {'predictors': ['planned'], 'targets': ['risk'], 'metadata_not_predictors': ['Scenario_ID'], 'forbidden_inputs': ['actual']}
        return rows, spec, ancestry

    def test_overlap_repaired_without_mutation(self):
        rows, spec, ancestry = self.fixture()
        rows[2]['planned'] = rows[0]['planned']
        original = deepcopy(rows)
        overlay = create_overlay(rows, spec, ancestry)
        result = apply_overlay(rows, overlay)
        self.assertEqual(result[0]['split'], result[2]['split'])
        self.assertEqual(rows, original)
        for a, b in zip(rows, result):
            self.assertEqual({k: v for k, v in a.items() if k not in ('split', 'split_group_id')},
                             {k: v for k, v in b.items() if k not in ('split', 'split_group_id')})

    def test_reproducible_under_row_order(self):
        rows, spec, ancestry = self.fixture()
        self.assertEqual(create_overlay(rows, spec, ancestry), create_overlay(list(reversed(rows)), spec, list(reversed(ancestry))))

    def test_labels_not_used_for_assignment(self):
        rows, spec, ancestry = self.fixture()
        baseline = create_overlay(rows, spec, ancestry)
        for r in rows:
            r['risk'] = '1' if r['risk'] == '0' else '0'
        self.assertEqual(baseline, create_overlay(rows, spec, ancestry))

    def test_numeric_equivalence(self):
        rows, spec, ancestry = self.fixture()
        rows[2]['planned'] = '0.0'
        overlay = create_overlay(rows, spec, ancestry)
        groups = {r['Scenario_ID']: r['split_group_id'] for r in overlay['assignments']}
        self.assertEqual(groups['0'], groups['2'])

    def test_signed_zero_hash_equivalence(self):
        rows, spec, ancestry = self.fixture()
        rows[2]['planned'] = '-0.0'
        overlay = create_overlay(rows, spec, ancestry)
        records = {r['Scenario_ID']: r for r in overlay['assignments']}
        self.assertEqual(records['0']['feature_signature_sha256'], records['2']['feature_signature_sha256'])

    def test_ancestry_transitive_union(self):
        rows, spec, ancestry = self.fixture()
        rows[1]['Base_Event_ID'] = ancestry[1]['Base_Event_ID'] = '0'
        ancestry[2]['planning_fingerprint'] = ancestry[1]['planning_fingerprint']
        rows[4]['planned'] = rows[2]['planned']
        overlay = create_overlay(rows, spec, ancestry)
        groups = {r['Scenario_ID']: r['split_group_id'] for r in overlay['assignments']}
        self.assertEqual(len({groups[i] for i in ('0', '1', '2', '4')}), 1)

    def test_invalid_predictors(self):
        for value in ('', 'nan', 'inf'):
            rows, spec, ancestry = self.fixture()
            rows[0]['planned'] = value
            with self.assertRaises(ValueError): create_overlay(rows, spec, ancestry)
        rows, spec, ancestry = self.fixture()
        spec['predictors'] = ['risk']
        with self.assertRaises(ValueError): create_overlay(rows, spec, ancestry)

    def test_missing_and_duplicate_ids(self):
        rows, spec, ancestry = self.fixture()
        with self.assertRaises(ValueError): create_overlay(rows, spec, ancestry[:-1])
        with self.assertRaises(ValueError): create_overlay(rows + [rows[0]], spec, ancestry + [ancestry[0]])

    def test_tampered_overlay_rejected(self):
        rows, spec, ancestry = self.fixture()
        overlay = create_overlay(rows, spec, ancestry)
        overlay['assignments'][0]['split'] = 'test'
        with self.assertRaises(ValueError): validate_overlay(rows, overlay)
        overlay['assignment_sha256'] = digest(overlay['assignments'])
        overlay['assignments'][0]['feature_signature_sha256'] = 'wrong'
        overlay['assignment_sha256'] = digest(overlay['assignments'])
        with self.assertRaises(ValueError): validate_overlay(rows, overlay)

    def test_source_mismatch_rejected(self):
        rows, spec, ancestry = self.fixture()
        overlay = create_overlay(rows, spec, ancestry)
        rows[0]['configuration_sha256'] = 'changed'
        with self.assertRaises(ValueError): apply_overlay(rows, overlay)
