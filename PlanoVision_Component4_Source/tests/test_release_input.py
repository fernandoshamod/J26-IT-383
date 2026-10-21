from pathlib import Path
import tempfile
import unittest

from component4.release_input import assert_experiment_output


class ReleaseInputTests(unittest.TestCase):
    def test_output_inside_release_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work') as directory:
            root = Path(directory) / 'dataset_releases'
            with self.assertRaises(ValueError):
                assert_experiment_output(root / 'v1.0/model.bin', root)
            with self.assertRaises(ValueError):
                assert_experiment_output(root, root)

    def test_ancestor_output_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work') as directory:
            with self.assertRaises(ValueError):
                assert_experiment_output(directory, Path(directory) / 'dataset_releases')

    def test_external_experiment_output_allowed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work') as directory:
            path = Path(directory) / 'outputs/experiment/model.bin'
            self.assertEqual(assert_experiment_output(path, Path(directory) / 'dataset_releases'), path.resolve())

    def test_normalized_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work') as directory:
            root = Path(directory) / 'dataset_releases'
            with self.assertRaises(ValueError):
                assert_experiment_output(root / 'v1.0/../v1.0/changed.csv', root)
