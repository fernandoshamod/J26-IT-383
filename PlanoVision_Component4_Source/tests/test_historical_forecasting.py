import unittest
from component4.historical_forecasting import baseline_predictions,forecast_metrics,audit_series,month_number


class HistoricalForecastTests(unittest.TestCase):
    def fixture(self):
        rows=[];assignments=[]
        for i in range(40):
            ds=f'{2020+i//12:04d}-{i%12+1:02d}-01'
            rows.append({'observation_id':str(i),'ds':ds,'y':str(i+1),'series_id':'s','source_id':'source','unit':'index','currency':'',
                'synthetic_origin':'0','event_total_cost_observation':'0','lineage_reconciled':'1','closed_calendar_month':'1','source_quality_review':'0'})
            assignments.append({'observation_id':str(i),'partition':'train' if i<28 else 'validation' if i<34 else 'test'})
        return rows,assignments

    def test_chronological_series_audit(self):
        rows,assignments=self.fixture()
        _,audit=audit_series(rows,assignments)
        self.assertEqual(audit[0]['train_records'],28)

    def test_duplicate_and_gaps_rejected(self):
        rows,assignments=self.fixture();rows[2]['ds']=rows[1]['ds']
        with self.assertRaises(ValueError):audit_series(rows,assignments)

    def test_mixed_units_and_synthetic_rejected(self):
        for key,value in (('unit','LKR'),('synthetic_origin','1'),('closed_calendar_month','0'),('y','nan')):
            rows,assignments=self.fixture();rows[2][key]=value
            with self.assertRaises(ValueError):audit_series(rows,assignments)

    def test_nonchronological_and_missing_assignments_rejected(self):
        rows,assignments=self.fixture();assignments[1]['partition']='test'
        with self.assertRaises(ValueError):audit_series(rows,assignments)
        with self.assertRaises(ValueError):audit_series(rows,assignments[:-1])

    def test_baseline_uses_training_only_for_long_horizon(self):
        rows,_=self.fixture();training=rows[:24]
        self.assertEqual(baseline_predictions(training,['2022-01-01','2023-01-01'],'seasonal_naive_12'),[13,13])
        self.assertEqual(baseline_predictions(training,['2022-01-01'],'last_value'),[24])

    def test_past_and_nonmonthly_dates_rejected(self):
        rows,_=self.fixture()
        with self.assertRaises(ValueError):baseline_predictions(rows[:24],['2021-12-01'],'last_value')
        with self.assertRaises(ValueError):month_number('2022-01-02')

    def test_metrics_training_denominator_and_undefined_scale(self):
        metrics=forecast_metrics([1,3],[2,2],list(range(24)))
        self.assertEqual(metrics['mae'],1)
        self.assertEqual(metrics['rmse'],1)
        self.assertAlmostEqual(metrics['mase_seasonal12'],1/12)
        self.assertIsNone(forecast_metrics([1],[2],[1]*24)['mase_seasonal12'])

    def test_nonfinite_and_empty_metrics_rejected(self):
        with self.assertRaises(ValueError):forecast_metrics([1],[float('nan')],list(range(24)))
        with self.assertRaises(ValueError):forecast_metrics([],[],list(range(24)))
