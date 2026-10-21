import json
from copy import deepcopy
from pathlib import Path
import unittest

from component4.dataset_design import (assign_groups, audit_split_leakage, split_components,
                                       validate_expansion_plan, bulk_validation_blockers)
from component4.unitless_experiment import (validate_unitless_config, evaluate_unitless_test, unitless_pilot_blockers)

ROOT = Path(__file__).resolve().parents[1]


def metadata(n=20):
    return [{'scenario_id': f'S-{i}', 'family_id': f'F-{i}', 'planning_fingerprint': f'P-{i}',
             'venue_template_id': 'shared-real-identity', 'vendor_template_id': 'shared-card',
             'source_dependency_ids': ['same-quote']} for i in range(n)]


class GroupTests(unittest.TestCase):
    def test_conditional_shared_sources_are_disclosed_not_unseen(self):
        rows = metadata()
        assignment = assign_groups(rows, 'conditional_in_simulator', 42)
        report = audit_split_leakage(rows, assignment, 'conditional_in_simulator')
        self.assertEqual(report['status'], 'PASS')
        self.assertFalse(report['unseen_venue_claim_supported_by_protocol'])
        self.assertEqual(report['shared_source_overlap']['venue_template'], ['shared-real-identity'])

    def test_shared_venue_blocks_unseen(self):
        with self.assertRaisesRegex(ValueError, 'insufficient_indivisible'):
            assign_groups(metadata(), 'unseen_templates', 42)

    def test_family_replications_stay_together(self):
        rows = metadata()
        replica = {**rows[0], 'scenario_id': 'replica'}
        rows.append(replica)
        assignment = assign_groups(rows, 'conditional_in_simulator', 42)
        self.assertEqual(assignment['S-0'], assignment['replica'])

    def test_independent_audit_catches_broken_family(self):
        rows = metadata()
        rows.append({**rows[0], 'scenario_id': 'replica'})
        assignment = assign_groups(rows, 'conditional_in_simulator', 42)
        assignment['replica'] = 'test' if assignment['S-0'] != 'test' else 'train'
        self.assertIn('family', audit_split_leakage(rows, assignment, 'conditional_in_simulator')['violations'])

    def test_identical_planning_states_merge_different_families(self):
        rows = metadata()
        rows[1]['planning_fingerprint'] = rows[0]['planning_fingerprint']
        groups = split_components(rows, 'conditional_in_simulator')
        self.assertEqual(groups['F-0'], groups['F-1'])

    def test_transitive_partial_ancestry_overlap(self):
        rows = metadata(3)
        for i, row in enumerate(rows):
            row['venue_template_id'] = f'V{i}'
            row['vendor_template_id'] = f'B{i}'
            row['source_dependency_ids'] = [f'Q{i}']
        rows[1]['venue_template_id'] = rows[0]['venue_template_id']
        rows[2]['vendor_template_id'] = rows[1]['vendor_template_id']
        self.assertEqual(len(set(split_components(rows, 'unseen_templates').values())), 1)

    def test_reproducible_and_input_order_invariant(self):
        rows = metadata()
        self.assertEqual(assign_groups(rows, 'conditional_in_simulator', 42),
                         assign_groups(list(reversed(rows)), 'conditional_in_simulator', 42))

    def test_invalid_metadata_and_map_rejected(self):
        for key in ('family_id', 'planning_fingerprint', 'venue_template_id', 'vendor_template_id', 'source_dependency_ids'):
            rows = metadata()
            del rows[0][key]
            with self.assertRaises(ValueError):
                split_components(rows, 'conditional_in_simulator')
        with self.assertRaises(ValueError):
            audit_split_leakage(metadata(), {}, 'conditional_in_simulator')

    def test_duplicate_ids_rejected(self):
        rows = metadata()
        rows.append(rows[0])
        with self.assertRaisesRegex(ValueError, 'duplicate_scenario_id'):
            split_components(rows, 'conditional_in_simulator')

    def test_invalid_seeds_fractions_and_tolerance(self):
        for seed in (True, -1, 1.5, None):
            with self.assertRaises(ValueError):
                assign_groups(metadata(), 'conditional_in_simulator', seed)
        for fractions in ((.7, .2, .2), (True, .1, .1), (.7, float('nan'), .15)):
            with self.assertRaises(ValueError):
                assign_groups(metadata(), 'conditional_in_simulator', 42, fractions)
        with self.assertRaises(ValueError):
            assign_groups(metadata(), 'conditional_in_simulator', 42, tolerance=float('nan'))

    def test_unknown_protocol_and_empty_splits(self):
        with self.assertRaises(ValueError):
            split_components(metadata(), 'row_random')
        self.assertEqual(audit_split_leakage(metadata(), {r['scenario_id']: 'train' for r in metadata()}, 'conditional_in_simulator')['status'], 'FAIL')


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'root_count': 1250, 'planning_states_per_root': 3, 'outcome_replications_per_state': 2,
                     'target_rows': 7500, 'archetype_root_quotas': {'Wedding': 625, 'Corporate': 625},
                     'split_protocol': 'conditional_in_simulator'}

    def test_exact_counts(self):
        self.assertTrue(validate_expansion_plan(self.plan))

    def test_missing_bool_fractional_and_mismatched_counts(self):
        for v in (None, True, 1250.0, -1):
            p = {**self.plan, 'root_count': v}
            with self.assertRaises(ValueError):
                validate_expansion_plan(p)
        with self.assertRaises(ValueError):
            validate_expansion_plan({**self.plan, 'target_rows': 7501})

    def test_quota_scope_and_sum(self):
        for q in ({'Wedding': 1250}, {'Wedding': 624, 'Corporate': 625}, {'Wedding': True, 'Corporate': 1249}):
            with self.assertRaises(ValueError):
                validate_expansion_plan({**self.plan, 'archetype_root_quotas': q})

    def test_fail_closed_without_bulk_authority(self):
        reasons = bulk_validation_blockers(self.plan, {})
        self.assertIn('missing:pilot_validated_pass', reasons)
        self.assertIn('missing:explicit_bulk_authorization', reasons)
        self.assertIn('authorization_hash_mismatch', reasons)

    def test_invalid_plan_fails_closed_without_crash(self):
        self.assertIn('plan_object_required', bulk_validation_blockers(None, {}))

    def test_fractional_authorized_count_rejected(self):
        self.assertIn('authorized_count_mismatch', bulk_validation_blockers(self.plan, {'authorized_rows': 7500.0}))


class UnitlessTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((ROOT / 'config/unitless_pilot.proposed.json').read_text())
        self.inputs = {'guests': 100, 'event_hours': 4, 'stage_width_m': 4, 'stage_length_m': 3,
                       'budget_score': 3, 'retained_receipts_score': 3}

    def mock(self):
        c = deepcopy(self.c)
        c['record_kind'] = 'mock_unitless_test'
        return c

    def test_complete_dimensionless_config(self):
        self.assertTrue(validate_unitless_config(self.c))

    def test_no_live_or_lkr_activation(self):
        with self.assertRaisesRegex(ValueError, 'test_only'):
            evaluate_unitless_test(self.c, 'Wedding', self.inputs)
        c = self.mock()
        c['currency'] = 'LKR'
        with self.assertRaises(ValueError):
            evaluate_unitless_test(c, 'Wedding', self.inputs)

    def test_accounting_reserve_and_profit(self):
        r = evaluate_unitless_test(self.mock(), 'Wedding', self.inputs)
        self.assertAlmostEqual(sum(r['line_items_score'].values()), r['planned_cost_score'])
        self.assertAlmostEqual(r['planned_cost_score'], 2.7)
        self.assertAlmostEqual(r['reserve_score'], .27)
        self.assertAlmostEqual(r['planned_profit_score'], .3)
        self.assertAlmostEqual(r['margin_points'], 10)
        self.assertFalse(any('lkr' in k.lower() for k in r))

    def test_guests_propagate_and_financial_failure_retained(self):
        c = self.mock()
        a = evaluate_unitless_test(c, 'Wedding', self.inputs)
        b = evaluate_unitless_test(c, 'Wedding', {**self.inputs, 'guests': 101, 'budget_score': 2})
        self.assertGreater(b['planned_cost_score'], a['planned_cost_score'])
        self.assertTrue(b['planned_budget_breach'])

    def test_missing_coefficient_and_invalid_value_blocked(self):
        for value in (None, True, -1, float('inf')):
            c = self.mock()
            c['coefficients']['catering'] = value
            with self.assertRaises(ValueError):
                validate_unitless_config(c)

    def test_area_and_guest_capacity(self):
        c = self.mock()
        c['seat_zone_m2'] = 100
        with self.assertRaisesRegex(ValueError, 'area_invalid'):
            evaluate_unitless_test(c, 'Wedding', self.inputs)
        with self.assertRaises(ValueError):
            evaluate_unitless_test(self.mock(), 'Wedding', {**self.inputs, 'guests': 181})

    def test_zero_receipts_margin_unavailable(self):
        c = self.mock()
        c['profiles']['Wedding']['retained_receipts_score'].append(0)
        r = evaluate_unitless_test(c, 'Wedding', {**self.inputs, 'retained_receipts_score': 0})
        self.assertIsNone(r['margin_points'])

    def test_pending_approval_and_no_writer_remain_blockers(self):
        reasons = unitless_pilot_blockers(self.c)
        self.assertIn('unitless_methodology_approval_missing', reasons)
        self.assertIn('explicit_unitless_pilot_authorization_missing', reasons)
        self.assertIn('unitless_stochastic_generator_and_authorized_writer_not_implemented', reasons)

    def test_shock_and_pilot_parameters_validated(self):
        for path, value in (('injection_prevalence', None), ('injection_prevalence', 1.1), ('injection_multiplier', [1, 1.5])):
            c = self.mock()
            c['outcome_proposal'][path] = value
            with self.assertRaises(ValueError):
                validate_unitless_config(c)
        c = self.mock()
        c['proposed_pilot']['rows'] = 25
        with self.assertRaises(ValueError):
            validate_unitless_config(c)

    def test_missing_configuration_fails_closed(self):
        self.assertIn('unitless_configuration_object_required', unitless_pilot_blockers(None))

    def test_unitless_market_conversion_forbidden(self):
        c = self.mock()
        c['market_conversion_factor'] = 1000
        with self.assertRaises(ValueError):
            validate_unitless_config(c)


if __name__ == '__main__':
    unittest.main()
