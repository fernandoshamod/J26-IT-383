"""Explicitly gated, dimensionless diagnostic pipeline; never an LKR fallback."""
from copy import deepcopy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import numpy as np
from .engine import fingerprint, FORMULA_IDS
from .unitless_experiment import validate_unitless_config, _calculate_unitless
from .dataset_design import assign_groups, audit_split_leakage, split_components
from .diagnostic_design import validate_diagnostic_design

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'unitless-pilot.0.2'
DIAGNOSTIC_VERSION = 'unitless-pilot.0.3'
CODE_FILES = ('component4/unitless_pilot.py', 'component4/unitless_experiment.py',
              'component4/scenario_generator.py', 'component4/dataset_design.py',
              'component4/engine.py', 'component4/diagnostic_design.py',
              'work/minimal_pilot_authoring/export_unitless.mjs')


def code_hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in CODE_FILES}


def validate(config):
    validate_unitless_config(config)
    if config.get('version') not in (VERSION, DIAGNOSTIC_VERSION):
        raise ValueError('unsupported_unitless_version')
    for key in ('maximum_stage_area_m2', 'av_breakpoint_m2'):
        v = config.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError('missing_or_invalid:' + key)
    if config['av_breakpoint_m2'] > config['maximum_stage_area_m2'] or not config.get('accounting_policy'):
        raise ValueError('accounting_or_threshold_policy_missing')
    expected_units = {'catering': 'persons', 'chairs': 'chairs', 'tables': 'tables', 'stage': 'm2', 'av': 'kits', 'labour': 'weighted_person_hours', 'venue_fixed': 'bookings'}
    if config.get('quantity_units') != expected_units:
        raise ValueError('explicit_quantity_units_required')
    p = config['proposed_pilot']
    if p['planning_states_per_root'] != 3 or p['outcome_replications_per_state'] != 2:
        raise ValueError('three_states_two_replications_required')
    if config['version'] == VERSION and config.get('planning_states') != ['baseline', 'guest_minus_one', 'guest_plus_one']:
        raise ValueError('explicit_intervention_policy_required')
    if config['version'] == DIAGNOSTIC_VERSION:
        validate_diagnostic_design(config)
    if config.get('split_policy') != {'protocol': 'conditional_in_simulator', 'fractions': [0.6, 0.2, 0.2], 'tolerance': 0.0}:
        raise ValueError('reviewed_split_policy_required')
    for key in ('venue_template_id', 'vendor_template_id'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('ancestry_required:' + key)
    if not isinstance(config.get('source_dependency_ids'), list) or not config['source_dependency_ids'] or any(not isinstance(x, str) or not x.strip() for x in config['source_dependency_ids']):
        raise ValueError('source_ancestry_required')
    if any(p['guest_max'] - p['guest_min'] < 2 for p in config['profiles'].values()):
        raise ValueError('guest_intervention_support_missing')
    if config.get('outcome_proposal', {}).get('distribution') != 'bounded_uniform':
        raise ValueError('explicit_uniform_shock_design_required')
    if config.get('source_snapshot_sha256') != fingerprint(config.get('experimental_source_snapshot')):
        raise ValueError('experimental_source_snapshot_mismatch')
    return True


def execution_blockers(config, authorization=None):
    try:
        validate(config)
    except (ValueError, TypeError, KeyError) as exc:
        return ['configuration_invalid:' + str(exc)]
    reasons = []
    a = authorization if isinstance(authorization, dict) else {}
    if config['record_kind'] != 'hypothetical_unitless_proposal':
        reasons.append('test_mock_forbidden_in_authorized_execution')
    if a.get('explicit_authorization') is not True:
        reasons.append('separate_explicit_authorization_missing')
    if a.get('configuration_sha256') != fingerprint(config):
        reasons.append('exact_configuration_hash_not_authorized')
    if a.get('code_sha256') != code_hashes():
        reasons.append('code_snapshot_not_authorized')
    if a.get('runtime') != {'python': platform.python_version(), 'numpy': np.__version__}:
        reasons.append('runtime_snapshot_not_authorized')
    if type(a.get('scenario_count')) is not int or a.get('scenario_count') != config['proposed_pilot']['rows'] or a.get('event_types') != ['Wedding', 'Corporate']:
        reasons.append('authorized_count_or_scope_mismatch')
    for name in (*FORMULA_IDS, 'numerical_parameters', 'methodology', 'sampling_split', 'acceptance_criteria', 'tests_passed'):
        records = a.get('approvals', {})
        r = records.get(name, {}) if isinstance(records, dict) else {}
        if not isinstance(r, dict) or r.get('status') != 'approved' or any(not isinstance(r.get(k), str) or not r[k].strip() for k in ('reviewer', 'role', 'date', 'rationale', 'evidence_ref')) or r.get('configuration_sha256') != fingerprint(config):
            reasons.append('approval_missing_or_mismatched:' + name)
    if any(not isinstance(a.get(k), str) or not a[k].strip() for k in ('authorizer', 'date', 'evidence_ref')):
        reasons.append('authorization_identity_and_evidence_missing')
    return sorted(set(reasons))


def _generate(config, mock=False):
    validate(config)
    c = deepcopy(config)
    p = c['proposed_pilot']
    origin = 'MOCK_UNITLESS_TEST_NOT_MARKET_DATA' if mock else 'SYNTHETIC_HYPOTHETICAL_UNITLESS_NOT_MARKET_DATA'
    planning, outcomes, ledger, provenance, latent, rejected = [], [], [], [], [], []
    # Canonical JSON ignores dictionary insertion order. Root assignment must too.
    events = [e for e in ('Wedding', 'Corporate')
              for _ in range(p['archetype_root_quotas'][e])]
    for index, event in enumerate(events):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(p['seed'], spawn_key=(index, 0))))
        profile = c['profiles'][event]
        family = 'UF-' + fingerprint({'config': fingerprint(c), 'index': index})[:20]
        design = c.get('diagnostic_families', [])[index] if c['version'] == DIAGNOSTIC_VERSION else None
        for attempt in range(1 if design else 100):
            if design:
                variants = [deepcopy(x['inputs']) for x in design['states']]
            else:
                base = {k: profile[k][int(rng.integers(len(profile[k])))] for k in ('event_hours', 'stage_width_m', 'stage_length_m', 'budget_score', 'retained_receipts_score')}
                base['guests'] = int(rng.integers(profile['guest_min'] + 1, profile['guest_max']))
                variants = [{**base, 'guests': base['guests'] + offset} for offset in (0, -1, 1)]
            try:
                results = [_calculate_unitless(c, event, x, origin) for x in variants]
                break
            except ValueError as exc:
                rejected.append({'family_id': family, 'attempt': attempt, 'reason': str(exc)})
        else:
            raise ValueError('no_feasible_root_after_100_attempts')
        for state, (inputs, result) in enumerate(zip(variants, results)):
            for rep in range(2):
                # Common random numbers for paired interventions; planning never reads shocks.
                shock = np.random.Generator(np.random.PCG64(np.random.SeedSequence(p['seed'], spawn_key=(index, 1, rep))))
                op = c['outcome_proposal']
                cost_factor = float(shock.uniform(*op['ordinary_common_cost_multiplier']))
                receipt_factor = float(shock.uniform(*op['independent_receipt_multiplier']))
                injected = bool(shock.random() < op['injection_prevalence'])
                target = op['eligible_services'][int(shock.integers(len(op['eligible_services'])))] if injected else None
                injection = float(shock.uniform(*op['injection_multiplier'])) if injected else 1.0
                sid = 'US-' + fingerprint({'family': family, 'state': state, 'replication': rep})[:20]
                state_name = design['states'][state]['name'] if design else c['planning_states'][state]
                planning.append({'scenario_id': sid, 'family_id': family, 'event_type': event, 'planning_state': state_name, 'outcome_replication': rep, **inputs,
                                 'planned_cost_score': result['planned_cost_score'], 'reserve_score': result['reserve_score'], 'planned_profit_score': result['planned_profit_score'],
                                 'planned_margin_points': result['margin_points'], 'used_area_m2': result['used_area_m2'], 'usable_area_m2': result['usable_area_m2'], 'staff': result['staff'], 'tables': result['tables'],
                                 'paid_hours_per_staff': result['paid_hours_per_staff'], 'seats': inputs['guests'], 'planned_budget_breach': result['planned_budget_breach'],
                                 'operating_allowance_score': inputs['budget_score'] - result['reserve_score'],
                                 'planned_operating_allowance_breach': result['planned_cost_score'] > inputs['budget_score'] - result['reserve_score']})
                actual = {k: v * cost_factor * (injection if k == target else 1) for k, v in result['line_items_score'].items()}
                total = math.fsum(actual.values())
                receipts = inputs['retained_receipts_score'] * receipt_factor
                profit = receipts - total
                margin = 100 * profit / receipts if receipts else None
                outcomes.append({'scenario_id': sid, 'simulated_cost_score': total, 'simulated_receipts_score': receipts, 'simulated_profit_score': profit, 'simulated_margin_points': margin,
                                 'simulated_budget_overrun': total > inputs['budget_score'], 'simulated_profit_margin_risk': margin < c['minimum_margin_points'] if margin is not None else None,
                                 'simulated_vendor_cost_anomaly': injected, 'label_origin': 'SIMULATOR_OUTCOME_NOT_OBSERVED'})
                for service, amount in result['line_items_score'].items():
                    ledger.append({'scenario_id': sid, 'service': service, 'quantity': result['quantities'][service], 'quantity_unit': c['quantity_units'][service], 'reference_quantity': c['reference_quantities'][service], 'experimental_coefficient': c['coefficients'][service], 'planned_score': amount, 'simulated_realized_score': actual[service], 'cost_unit': 'dimensionless_score'})
                provenance.append({'scenario_id': sid, 'family_id': family, 'planning_fingerprint': fingerprint({'event': event, 'inputs': inputs}),
                                   'venue_template_id': c['venue_template_id'], 'vendor_template_id': c['vendor_template_id'], 'source_dependency_ids': c['source_dependency_ids'],
                                   'configuration_sha256': fingerprint(c), 'source_snapshot_sha256': c['source_snapshot_sha256'], 'assumption_ids': list(FORMULA_IDS), 'origin': origin,
                                   'geometry_origin': c['geometry_origin'], 'cost_unit': 'dimensionless_score', 'is_observed_event': False, 'is_trained_prediction': False})
                latent.append({'scenario_id': sid, 'cost_multiplier': cost_factor, 'receipt_multiplier': receipt_factor, 'injected_service': target, 'injection_multiplier': injection})
    policy = c['split_policy']
    splits = assign_groups(provenance, policy['protocol'], p['seed'], tuple(policy['fractions']), policy['tolerance'])
    groups = split_components(provenance, policy['protocol'])
    for row in provenance:
        row['split_group_id'] = groups[row['family_id']]
        row['split'] = splits[row['scenario_id']]
    bundle = {'planning': planning, 'outcomes': outcomes, 'line_items': ledger, 'provenance': provenance, 'latent_DO_NOT_USE_AS_FEATURES': latent, 'rejections': rejected, 'configuration': c,
              'manifest': {'rule_version': c['version'], 'configuration_sha256': fingerprint(c), 'code_sha256': code_hashes(), 'seed': p['seed'], 'python': platform.python_version(), 'numpy': np.__version__, 'origin': origin,
                           'split_audit': audit_split_leakage(provenance, splits, policy['protocol']), 'realism_validated': False}}
    validate_bundle(bundle)
    return bundle


def validate_bundle(bundle):
    plans = {x['scenario_id']: x for x in bundle['planning']}
    outcomes = {x['scenario_id']: x for x in bundle['outcomes']}
    provenance = {x['scenario_id']: x for x in bundle['provenance']}
    latent = {x['scenario_id']: x for x in bundle['latent_DO_NOT_USE_AS_FEATURES']}
    if len(plans) != len(bundle['planning']) or len(outcomes) != len(bundle['outcomes']) or len(provenance) != len(bundle['provenance']) or len(latent) != len(bundle['latent_DO_NOT_USE_AS_FEATURES']) or not set(plans) == set(outcomes) == set(provenance) == set(latent):
        raise ValueError('duplicate_or_mismatched_ids')
    if len(plans) != bundle['configuration']['proposed_pilot']['rows']:
        raise ValueError('row_count_mismatch')
    if set(x['scenario_id'] for x in bundle['line_items']) != set(plans):
        raise ValueError('line_item_scope_mismatch')
    def close(a, b):
        return isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    for sid, plan in plans.items():
        lines = [x for x in bundle['line_items'] if x['scenario_id'] == sid]
        expected = _calculate_unitless(bundle['configuration'], plan['event_type'], {k: plan[k] for k in ('guests', 'event_hours', 'stage_width_m', 'stage_length_m', 'budget_score', 'retained_receipts_score')})
        if len(lines) != 7 or {x['service'] for x in lines} != set(expected['line_items_score']):
            raise ValueError('double_charging_or_missing_service')
        outcome = outcomes[sid]
        shock = latent[sid]
        for line in lines:
            factor = shock['cost_multiplier'] * (shock['injection_multiplier'] if line['service'] == shock['injected_service'] else 1)
            if line['quantity_unit'] != bundle['configuration']['quantity_units'][line['service']] or line['quantity'] != expected['quantities'][line['service']] or not close(line['planned_score'], expected['line_items_score'][line['service']]) or not close(line['simulated_realized_score'], line['planned_score'] * factor):
                raise ValueError('line_item_dependency_mismatch')
        if not close(plan['planned_cost_score'], math.fsum(x['planned_score'] for x in lines)) or not close(outcome['simulated_cost_score'], math.fsum(x['simulated_realized_score'] for x in lines)) or not close(outcome['simulated_profit_score'], outcome['simulated_receipts_score'] - outcome['simulated_cost_score']):
            raise ValueError('financial_reconciliation_failed')
        if not close(outcome['simulated_receipts_score'], plan['retained_receipts_score'] * shock['receipt_multiplier']) or not close(plan['reserve_score'], expected['reserve_score']) or plan['used_area_m2'] != expected['used_area_m2']:
            raise ValueError('reserve_receipts_or_geometry_mismatch')
        if not close(plan['planned_profit_score'], expected['planned_profit_score']) or plan['staff'] != expected['staff'] or plan['tables'] != expected['tables'] or plan['seats'] != plan['guests'] or not close(plan['operating_allowance_score'], plan['budget_score'] - expected['reserve_score']):
            raise ValueError('planning_financial_or_quantity_mismatch')
        if plan['planned_budget_breach'] != expected['planned_budget_breach'] or plan['planned_operating_allowance_breach'] != (plan['planned_cost_score'] > plan['operating_allowance_score']):
            raise ValueError('planned_flag_mismatch')
        margin = 100 * outcome['simulated_profit_score'] / outcome['simulated_receipts_score'] if outcome['simulated_receipts_score'] else None
        if (margin is None and outcome['simulated_margin_points'] is not None) or (margin is not None and not close(outcome['simulated_margin_points'], margin)):
            raise ValueError('margin_mismatch')
        if outcome['simulated_budget_overrun'] != (outcome['simulated_cost_score'] > plan['budget_score']) or outcome['simulated_profit_margin_risk'] != (margin < bundle['configuration']['minimum_margin_points'] if margin is not None else None) or outcome['simulated_vendor_cost_anomaly'] != (shock['injected_service'] is not None):
            raise ValueError('label_inconsistent')
    audit = audit_split_leakage(bundle['provenance'], {r['scenario_id']: r['split'] for r in bundle['provenance']}, 'conditional_in_simulator')
    if audit['status'] != 'PASS':
        raise ValueError('split_leakage')
    return True


def generate(config, authorization):
    blockers = execution_blockers(config, authorization)
    if blockers:
        raise ValueError('execution_blocked:' + '|'.join(blockers))
    return _generate(config)


def generate_test(config):
    if config.get('record_kind') != 'mock_unitless_test':
        raise ValueError('explicit_test_only_marker_required')
    return _generate(config, mock=True)


def _write_atomic(bundle, destination, node, exporter=None):
    validate_bundle(bundle)
    destination = Path(destination).resolve()
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('new_destination_in_existing_parent_required')
    with tempfile.TemporaryDirectory(prefix='.unitless-staging-', dir=destination.parent) as temp:
        stage = Path(temp) / 'output'
        stage.mkdir()
        for name in ('planning', 'outcomes', 'line_items', 'provenance', 'latent_DO_NOT_USE_AS_FEATURES', 'rejections'):
            rows = bundle[name]
            with (stage / (name + '.csv')).open('w', newline='', encoding='utf-8') as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)
                else:
                    f.write('family_id,attempt,reason\n')
        payload = stage / 'export_payload.json'
        payload.write_text(json.dumps(bundle, allow_nan=False, sort_keys=True), encoding='utf-8')
        if exporter:
            exporter(payload, stage / 'unitless_dataset.xlsx')
        else:
            subprocess.run([str(node), str(ROOT / 'work/minimal_pilot_authoring/export_unitless.mjs'), str(payload), str(stage / 'unitless_dataset.xlsx')], check=True)
        if not (stage / 'unitless_dataset.xlsx').is_file():
            raise ValueError('xlsx_export_missing')
        (stage / 'configuration.json').write_text(json.dumps(bundle['configuration'], indent=2, allow_nan=False), encoding='utf-8')
        (stage / 'validation_report.json').write_text(json.dumps({'arithmetic': 'PASS', 'spatial': 'PASS', 'split': bundle['manifest']['split_audit'], 'realism': 'NOT_VALIDATED', 'origin': bundle['manifest']['origin']}, indent=2), encoding='utf-8')
        manifest = {**bundle['manifest'], 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir() if p.is_file()}}
        if 'authorization_record' in bundle:
            manifest['authorization_record'] = bundle['authorization_record']
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        os.rename(stage, destination)
    return destination


def write(config, authorization, destination, node):
    bundle = generate(config, authorization)
    bundle['authorization_record'] = deepcopy(authorization)
    if execution_blockers(config, authorization):
        raise ValueError('authorization_changed_before_commit')
    return _write_atomic(bundle, destination, node)
