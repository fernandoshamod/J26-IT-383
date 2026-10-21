"""Read-only independent Stage 2 checks; only existing software fixtures are evaluated."""
import hashlib
import json
import math
from pathlib import Path
import unittest

import openpyxl
from component4.engine import FORMULA_IDS, PARAMS, RATE_UNITS, evaluate, money, risk_labels, step_units
from component4.gates import pilot_blockers

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def path_value(obj, path):
    for key in path.split('.'):
        obj = obj[key]
    return obj


def verify():
    data = load('work/approval_review_tables.json')
    config = load('config/simulator.candidate.json')
    base = load('config/simulator_parameters.proposed.json')
    prep = config['approval_preparation']
    for path, digest in data['input_hashes'].items():
        assert sha(path) == digest, ('input changed', path)
    assert config['archetypes'] == base['archetypes'], 'Runtime profiles must remain unchanged'
    assert config['pilot'] == base['pilot'] and config['seed'] is None
    assert prep['status'] == 'proposed_unresolved'
    assert prep['candidate_frozen'] is False and prep['values_and_units_fully_specified'] is False
    assert prep['frozen_at'] is None and prep['approved_configuration_sha256'] is None
    aids = {f'A{i:03}' for i in range(1, 35)}
    assert {x['assumption_id'] for x in config['assumption_decisions']} == aids
    formulas = prep['formula_review_records']
    assert len(formulas) == 21
    assert {x['formula_id'] for x in formulas if x['engine_gate_required']} == set(FORMULA_IDS)
    assert {x['formula_id'] for x in formulas if not x['engine_gate_required']} == {'U030', 'WHAT_IF'}
    records = formulas + prep['numeric_review_records'] + prep['control_review_records']
    for r in records:
        assert r['status'] == 'pending' and set(r['assumption_ids']) <= aids
        assert r['assumption_version'] == data['assumption_version']
        for k in ['reviewer', 'reviewer_role', 'review_date', 'rationale', 'decision_evidence_ref']:
            assert r[k] is None
    expected_paths = set()
    for event in ['Wedding', 'Corporate']:
        for k in PARAMS:
            expected_paths.add(f'archetypes.{event}.parameters.{k}')
        for k, unit in RATE_UNITS.items():
            for field in ['rate', 'tax_rate_points']:
                expected_paths.add(f'archetypes.{event}.rates.{k}.{field}')
            assert config['archetypes'][event]['rates'][k]['unit'] == unit
    assert len(expected_paths) == 108
    assert set(data['active_numeric_paths']) == expected_paths
    assert {r['path'] for r in prep['numeric_review_records']} == expected_paths
    for r in prep['numeric_review_records']:
        assert path_value(config, r['path']) is None and r['value'] is None
        if r['parameter'] == 'guest_count':
            assert r['assumption_ids'] == ['A003', 'A005', 'A012']
        if r['parameter'] == 'seated_share':
            assert r['assumption_ids'] == ['A008']
    refs = {r[0] for r in data['tables']['References']['rows']}
    for r in records:
        assert set(r['supporting_refs'].split(';')) <= refs, r['supporting_refs']
    for r in config['experimental_policy_proposals']:
        assert r['selected_value'] is None and r['status'] == 'pending'
        assert r['evidence_kind'] == 'hypothetical_experimental_choices'
        assert set(r['assumption_ids']) <= aids
        for k in ['reviewer', 'reviewer_role', 'review_date', 'decision_rationale', 'decision_evidence_ref']:
            assert r[k] is None
    assert len(config['experimental_policy_proposals']) == 15
    for r in config['assumption_decisions']:
        assert r['status'] == 'pending'
        assert all(r[k] is None for k in ['reviewer', 'reviewer_role', 'review_date', 'rationale', 'decision_evidence_ref'])
    live = {}
    for event in ['Wedding', 'Corporate']:
        result = evaluate(config, event, mode='live')
        assert result['status'] == 'blocked' and result['costs'] is None
        assert result['provenance']['is_trained_model_prediction'] is False
        live[event] = result['blockers']
    blockers = pilot_blockers(config)
    assert 'explicit_pilot_authorization_missing' in blockers
    assert 'scenario_generator_not_implemented_or_verified' in blockers

    # Read exported values and cached formula results, never author via openpyxl.
    path = ROOT / 'reports/assumption_decision_matrix.xlsx'
    wb = openpyxl.load_workbook(path, read_only=False, data_only=True)
    wf = openpyxl.load_workbook(path, read_only=False, data_only=False)
    expected = {'Wedding':127, 'Corporate':127, 'Formulas':21, 'Assumptions':34,
                'Policies':15, 'Shared_Controls':28}
    assert wb.sheetnames == ['Review', *expected, 'References']
    for name, count in expected.items():
        s = wb[name]
        assert s.max_row == count + 1 and s.max_column == 16
        assert s.freeze_panes == 'C2' and len(s.tables) == 1
        assert wf[name].data_validations.count >= 1
        for row in range(2, count + 2):
            assert s.cell(row, 10).value == 'Pending review'
            assert all(s.cell(row, c).value is None for c in range(11, 16))
            assert s.cell(row, 16).value is False
            assert wf[name].cell(row, 16).data_type == 'f'
            if name in ['Wedding', 'Corporate', 'Shared_Controls']:
                assert s.cell(row, 8).value is None
            if name == 'Policies':
                assert s.cell(row, 9).value is None
    for row, count in zip(range(6, 12), expected.values()):
        assert [wb['Review'].cell(row, col).value for col in range(2, 5)] == [count, count, 0]
    assert wb['Review']['B13'].value == wb['Review']['B14'].value == 54
    assert wb['References'].max_row - 1 == len(refs)
    for s in wb:
        for row in s:
            for c in row:
                assert c.data_type != 'e', (s.title, c.coordinate, c.value)
    wb.close()
    wf.close()

    # Existing mock fixture only: no event records or market rates are produced.
    fixture = load('fixtures/config.mock_test_only.json')
    diagnostics = []
    for event in ['Wedding', 'Corporate']:
        p = fixture['archetypes'][event]['parameters']
        baseline = evaluate(fixture, event, mode='mock_test_fixture')
        assert baseline['status'] == 'calculated'
        rows = {r['item_id']: r for r in baseline['costs']['line_items']}
        assert rows['catering']['quantity'] == p['guest_count']
        seats = math.ceil(p['guest_count'] * p['seated_share'])
        assert baseline['spatial']['planned_seats'] == seats
        tables = math.ceil((seats - p['vip_seats']) / p['seats_per_table']) + p['vip_tables']
        assert baseline['operations']['furniture_tables'] == tables
        assert money(sum(money(r['gross_lkr']) for r in rows.values())) == money(baseline['costs']['estimate_lkr'])
        reserve = money(baseline['costs']['estimate_lkr'] * p['reserve_ratio'])
        assert money(baseline['budget_constraints']['contingency_reserve_lkr']) == reserve
        assert money(baseline['risk_indicators']['expected_profit_lkr']) == money(p['expected_receipts_lkr']) - money(baseline['costs']['estimate_lkr'])
        diagnostics.append(event + ':catering_seating_accounting_reserve_profit')
        hours = p['event_hours'] + p['setup_hours'] + p['clearance_hours']
        for limit in [hours - 1, hours, hours + 1]:
            result = evaluate(fixture, event, {'regular_paid_hours_limit':limit}, mode='mock_test_fixture')
            assert result['status'] == 'calculated'
            staff = result['operations']['general_staff_count']
            regular, overtime = min(hours, limit), max(0, hours - limit)
            labour = next(r for r in result['costs']['line_items'] if r['item_id'] == 'labour')
            assert result['operations']['person_hours'] == staff * hours
            assert result['operations']['overtime_person_hours'] == staff * overtime
            assert labour['quantity'] == staff * (regular + overtime * p['overtime_multiplier'])
            diagnostics.append(event + ':paid_hour_boundary:' + str(limit))
        for key in ['av_steps', 'lighting_steps']:
            steps = fixture['archetypes'][event][key]
            for i, step in enumerate(steps):
                assert step_units(step['max_stage_area_m2'], steps) == step['units']
                if i + 1 < len(steps):
                    assert step_units(step['max_stage_area_m2'] + 0.000001, steps) == steps[i + 1]['units']
            try:
                step_units(steps[-1]['max_stage_area_m2'] + 1, steps)
                raise AssertionError('Exceedance must block')
            except ValueError as e:
                assert str(e) == 'stage_exceeds_reviewed_package_scope'
            diagnostics.append(event + ':' + key + ':boundary_and_exceedance')
    assert risk_labels(100, 125, 100, 20)['Budget_Overrun'] == 0
    assert risk_labels(100, 125, 100, 20)['Profit_Margin_Risk'] == 0
    assert risk_labels(100.01, 0, 100, 20)['Budget_Overrun'] == 1
    assert risk_labels(100, 0, 100, 20)['Profit_Margin_Risk'] is None
    assert risk_labels(None, None, None, None)['Vendor_Cost_Anomaly'] is None
    diagnostics.append('risk_label_equality_zero_receipts_and_missing_origin')
    suite = unittest.TestLoader().discover(str(ROOT / 'tests'))
    existing_count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    assert existing_count == 45 and result.wasSuccessful()
    report = {'status':'passed', 'audit_date':'2026-10-11', 'input_snapshots_preserved':len(data['input_hashes']),
              'original_assumptions':34, 'active_numeric_nulls':108, 'formula_and_utility_reviews':21,
              'workbook_review_counts':expected, 'pending_policy_menus':15, 'reference_count':len(refs),
              'existing_python_tests_passed':existing_count, 'fixture_only_diagnostic_groups':diagnostics,
              'candidate_frozen':False, 'formal_approvals_recorded':0,
              'live_blockers':live, 'pilot_blockers':blockers,
              'limitations':'Software fixture checks only; not empirical validation, scenario generation, or pilot approval.'}
    (ROOT / 'work/approval_review_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['live_blockers','pilot_blockers','fixture_only_diagnostic_groups']}, indent=2))


if __name__ == '__main__':
    verify()
