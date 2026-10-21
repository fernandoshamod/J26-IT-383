import unittest
from component4.historical_forecasting import expanding_validation_windows


class RollingForecastValidationTests(unittest.TestCase):
    def fixture(self):
        return [{'ds': f'{2022 + i//12:04d}-{i%12+1:02d}-01',
                 'partition': 'train' if i < 31 else 'validation' if i < 38 else 'test'} for i in range(45)]

    def test_fixed_windows_no_future_inputs(self):
        windows = expanding_validation_windows(self.fixture())
        self.assertEqual([len(t) for t, e in windows], [25, 28, 31])
        self.assertEqual([len(e) for t, e in windows], [3, 3, 3])
        for training, evaluation in windows:
            self.assertTrue(all(r['partition'] == 'train' for r in training))
            self.assertTrue(all(r['partition'] != 'test' for r in evaluation))
            self.assertLess(training[-1]['ds'], evaluation[0]['ds'])

    def test_short_history_rejected(self):
        with self.assertRaises(ValueError): expanding_validation_windows(self.fixture(), minimum_training=30)

    def test_missing_month_rejected(self):
        data = self.fixture()
        del data[5]
        with self.assertRaises(ValueError): expanding_validation_windows(data)

    def test_invalid_horizon(self):
        for h in (0, -1, 1.5, True):
            with self.assertRaises(ValueError): expanding_validation_windows(self.fixture(), horizon=h)

    def test_test_only_evaluation_rejected(self):
        data = self.fixture()
        for r in data:
            if r['partition'] == 'validation': r['partition'] = 'test'
        with self.assertRaises(ValueError): expanding_validation_windows(data)
