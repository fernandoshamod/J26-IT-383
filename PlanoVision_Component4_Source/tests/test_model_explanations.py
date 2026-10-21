import unittest
import numpy as np
from component4.model_explanations import validate_additivity, summarize_features


class ModelExplanationTests(unittest.TestCase):
    def test_additivity_and_probability(self):
        phi = np.array([[1., -.5, .2], [-1., .5, .2]])
        margin = phi.sum(axis=1)
        p = np.exp(-np.logaddexp(0., -margin))
        self.assertEqual(validate_additivity(phi, margin, p, 2)['status'], 'PASS')

    def test_corrupt_margin_rejected(self):
        with self.assertRaises(ValueError): validate_additivity([[1., 0.]], [2.], [.731], 1)

    def test_corrupt_score_rejected(self):
        with self.assertRaises(ValueError): validate_additivity([[0., 0.]], [0.], [.9], 1)

    def test_invalid_shapes_and_nonfinite(self):
        for phi in ([[0.]], [[float('nan'), 0.]], []):
            with self.assertRaises(ValueError): validate_additivity(phi, [0.], [.5], 1)

    def test_group_equal_summary_excludes_bias(self):
        summary = summarize_features([[1., 100.], [3., 100.], [9., 100.]], ['x'], [.5, .5, 1.])
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['mean_absolute_shap_group_equal'], 5.5)
        self.assertAlmostEqual(summary[0]['mean_absolute_shap_row_weighted'], 13/3)

    def test_invalid_summary_weights(self):
        with self.assertRaises(ValueError): summarize_features([[1., 0.]], ['x'], [0.])
