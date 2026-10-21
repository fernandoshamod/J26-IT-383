import unittest
import numpy as np
from component4.graph_experiment import fit_scaler, transform, adjacency, overlap_masks, make_model


class GraphExperimentTests(unittest.TestCase):
    def test_masked_values_not_observed_zero(self):
        x = np.array([[[2., np.nan]], [[4., np.nan]]])
        mask = np.isfinite(x)
        mean, scale = fit_scaler(x, mask)
        self.assertEqual(mean[0, 0], 3)
        result = transform(x, mask, mean, scale)
        self.assertTrue(np.isfinite(result).all())
        self.assertEqual(result[0, 0, 1], 0)
        self.assertEqual(result[0, 0, 3], 0)

    def test_scaler_training_only(self):
        train = np.array([[[2.]], [[4.]]])
        mean, scale = fit_scaler(train, np.isfinite(train))
        future = transform(np.array([[[100.]]]), np.ones((1, 1, 1), bool), mean, scale)
        self.assertEqual(future[0, 0, 0], 97)

    def test_direction_and_self_edges(self):
        edge = np.array([[0, 1], [1, 2]])
        mask = adjacency(edge, 3, 'gat_dependencies', 1)
        self.assertTrue(mask[1, 0])
        self.assertFalse(mask[0, 1])
        self.assertTrue(mask.diagonal().all())
        self.assertTrue(np.array_equal(adjacency(edge, 3, 'gat_self_only', 1), np.eye(3, dtype=bool)))

    def test_shuffle_reproducible(self):
        edge = np.array([[0, 1], [1, 2]])
        self.assertTrue(np.array_equal(adjacency(edge, 3, 'gat_shuffled_dependencies', 2), adjacency(edge, 3, 'gat_shuffled_dependencies', 2)))
        with self.assertRaises(ValueError):
            adjacency(np.array([[0], [9]]), 3, 'gat_dependencies', 1)

    def test_overlap_no_labels_used(self):
        a = {'x': np.array([[[1.]], [[1.]], [[2.]], [[2.]], [[3.]]]),
             'feature_mask': np.ones((5, 1, 1), bool), 'split': np.array(['train','validation','validation','test','test'])}
        masks = overlap_masks(a)
        self.assertEqual(masks['validation'].tolist(), [False, False, True, False, False])
        self.assertEqual(masks['test'].tolist(), [False, False, False, False, True])

    def test_attention_gradients_and_state_replay(self):
        import torch
        torch.manual_seed(123)
        model = make_model(4, 6, np.eye(3, dtype=bool))
        x = torch.randn(5, 3, 4)
        result = model(x)
        self.assertEqual(tuple(result.shape), (5, 3))
        result.square().mean().backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        replay = make_model(4, 6, np.eye(3, dtype=bool))
        replay.load_state_dict(model.state_dict())
        self.assertTrue(torch.equal(result, replay(x)))

    def test_disallowed_node_cannot_message_in_self_only(self):
        import torch
        torch.manual_seed(123)
        model = make_model(4, 6, np.eye(3, dtype=bool))
        x = torch.randn(1, 3, 4)
        before = model.first(x).detach()
        changed = x.clone()
        changed[:, 1] += 100
        after = model.first(changed).detach()
        self.assertTrue(torch.equal(before[:, 0], after[:, 0]))
        self.assertFalse(torch.equal(before[:, 1], after[:, 1]))


if __name__ == '__main__':
    unittest.main()
