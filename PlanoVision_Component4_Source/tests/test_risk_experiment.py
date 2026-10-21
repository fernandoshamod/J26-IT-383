from copy import deepcopy
import unittest

from component4.risk_experiment import validate_rows, group_weights, select_model, nonoverlap_rows


class RiskExperimentTests(unittest.TestCase):
    def fixture(self):
        spec = {'predictors':['planned'], 'targets':['risk'], 'metadata_not_predictors':['Scenario_ID'], 'forbidden_inputs':['actual']}
        rows = [{'Scenario_ID':str(i), 'split':s, 'split_group_id':str(i), 'Base_Event_ID':str(i), 'planned':str(i), 'risk':str(i%2)} for i,s in enumerate(('train','validation','test'))]
        return rows,spec

    def test_valid_partitions(self):
        rows,spec = self.fixture()
        self.assertEqual(validate_rows(rows,spec)['status'],'PASS')

    def test_forbidden_predictor_rejected(self):
        rows,spec = self.fixture()
        spec['predictors'].append('actual')
        with self.assertRaises(ValueError): validate_rows(rows,spec)

    def test_shared_group_and_family_rejected(self):
        for key in ('split_group_id','Base_Event_ID'):
            rows,spec = self.fixture()
            rows[1][key] = rows[0][key]
            with self.assertRaises(ValueError): validate_rows(rows,spec)

    def test_projection_overlap_disclosed_and_masked(self):
        rows,spec = self.fixture()
        rows[1]['planned'] = rows[0]['planned']
        audit = validate_rows(rows,spec)
        self.assertEqual(audit['cross_split_feature_projection_keys'],1)
        clean = nonoverlap_rows({s:[r for r in rows if r['split']==s] for s in ('train','validation','test')},spec['predictors'])
        self.assertEqual(clean['validation'],[])
        self.assertEqual(len(clean['test']),1)

    def test_invalid_values_and_ids_rejected(self):
        for key,value in (('planned','nan'),('risk','2'),('Scenario_ID','0')):
            rows,spec = self.fixture()
            rows[1][key] = value
            with self.assertRaises(ValueError): validate_rows(rows,spec)

    def test_group_weights_equal_group_totals(self):
        rows = [{'split_group_id':'a'}]*2 + [{'split_group_id':'b'}]*4
        weights = group_weights(rows)
        self.assertAlmostEqual(sum(weights[:2]),sum(weights[2:]))
        self.assertAlmostEqual(sum(weights),6)

    def test_selection_has_negative_control_exception(self):
        scores = {'dummy_prior':1.0, 'xgboost':0.1}
        self.assertEqual(select_model(scores,'Budget_Overrun'),'xgboost')
        self.assertEqual(select_model(scores,'Vendor_Cost_Anomaly'),'dummy_prior')
