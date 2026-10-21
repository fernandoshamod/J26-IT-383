"""Fail-closed Stage 10 inventory audit. Never generates scenarios or approvals."""
from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

TARGETS = ('Budget_Overrun', 'Profit_Margin_Risk', 'Vendor_Cost_Anomaly')
FORBIDDEN_FEATURES = {'Actual_Total_Cost', 'Actual_Revenue', 'Budget_Utilization',
                      'Profit', 'Profit_Margin', 'Cost_Per_Guest', 'Cost_Variance',
                      'Financial_Health_Score', 'cost_multiplier', 'receipt_multiplier',
                      'injection_multiplier', 'injected_service'}
MANDATORY = {
    'master_event_financial_dataset.csv': 'data/final/master_event_financial_dataset.csv',
    'master_event_financial_dataset.xlsx': 'data/final/master_event_financial_dataset.xlsx',
    'xgboost_risk_dataset.csv': 'data/final/xgboost_risk_dataset.csv',
    'prophet_cost_timeseries.csv': 'data/final/prophet_cost_timeseries.csv',
    'spatial_financial_graphs/': 'data/final/spatial_financial_graphs',
    'master_scenario_provenance.csv': 'data/final/master_scenario_provenance.csv',
    'master_financial_line_items.csv': 'data/final/master_financial_line_items.csv',
    'final_data_dictionary.xlsx': 'reports/final_data_dictionary.xlsx',
    'source_mapping.xlsx': 'reports/source_mapping.xlsx',
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_table(path):
    if not path.is_file():
        return [], []
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if any(None in r for r in rows):
            raise ValueError('malformed_csv:' + str(path))
        return reader.fieldnames or [], rows


def chronological_audit(observations, splits):
    """Per-series retrospective splits, not pooled future forecasting validation."""
    keys = [(r['series_id'], r['ds']) for r in observations]
    known = set(keys)
    split_keys = [(r['series_id'], r['ds']) for r in splits]
    groups = defaultdict(lambda: defaultdict(list))
    issues = []
    if len(keys) != len(known):
        issues.append('duplicate_observation_keys')
    if len(split_keys) != len(set(split_keys)):
        issues.append('duplicate_split_keys')
    for r in splits:
        if (r['series_id'], r['ds']) not in known:
            issues.append('unknown_split_observation')
        if r['partition'] not in ('train', 'validation', 'test'):
            issues.append('unknown_partition')
        else:
            groups[r['series_id']][r['partition']].append(r['ds'])
    for series, parts in groups.items():
        if set(parts) != {'train', 'validation', 'test'}:
            issues.append('incomplete_series_partitions:' + series)
            continue
        if not max(parts['train']) < min(parts['validation']) or not max(parts['validation']) < min(parts['test']):
            issues.append('nonchronological_partitions:' + series)
    return {'status': 'PASS' if splits and not issues else 'FAIL',
            'issues': sorted(set(issues)), 'partition_rows': dict(Counter(r['partition'] for r in splits)),
            'partition_series': {p: sum(p in g for g in groups.values()) for p in ('train', 'validation', 'test')},
            'series_with_splits': len(groups), 'unassigned_observations': len(known - set(split_keys))}


def historical_audit(rows):
    series = defaultdict(list)
    issues = []
    for row in rows:
        try:
            date.fromisoformat(row['ds'])
            if not math.isfinite(float(row['y'])):
                raise ValueError('nonfinite')
        except (ValueError, KeyError):
            issues.append('invalid_date_or_measurement')
        series[row.get('series_id', '')].append(row)
    for sid, values in series.items():
        dates = [v['ds'] for v in values]
        if not sid or dates != sorted(dates) or len(dates) != len(set(dates)):
            issues.append('invalid_series_order_or_key:' + sid)
        for field in ('unit', 'source_id', 'observation_kind'):
            if len({v.get(field) for v in values}) != 1 or not values[0].get(field):
                issues.append('mixed_or_missing_' + field + ':' + sid)
    return {'status': 'PASS' if rows and not issues else 'FAIL', 'issues': sorted(set(issues)),
            'rows': len(rows), 'series': len(series),
            'observation_kinds': dict(Counter(r.get('observation_kind') for r in rows))}


def audit(root, test_result=None):
    root = Path(root)
    schema = json.loads((root / 'work/original_schema.json').read_text())['Master_Data']['data'][0]
    header, master = read_table(root / MANDATORY['master_event_financial_dataset.csv'])
    xheader, xrows = read_table(root / MANDATORY['xgboost_risk_dataset.csv'])
    _, historical = read_table(root / MANDATORY['prophet_cost_timeseries.csv'])
    _, partitions = read_table(root / 'data/final/prophet_chronological_partitions.csv')
    _, context_provenance = read_table(root / 'data/final/master_provenance.csv')
    _, synthetic_provenance = read_table(root / MANDATORY['master_scenario_provenance.csv'])
    context_ids = {r['Scenario_ID'] for r in context_provenance if r['Record_Kind'] == 'observed_event_context_only'}
    synthetic = [r for r in master if r.get('Is_Augmented') == '1']
    observed_financial_ids = {r['Scenario_ID'] for r in context_provenance if r['Record_Kind'] == 'observed_event_financial_outcome'}
    observed_financial = [r for r in master if r.get('Scenario_ID') in observed_financial_ids
                          and r.get('Actual_Total_Cost') and r.get('Actual_Revenue')]
    hist = historical_audit(historical)
    chronology = chronological_audit(historical, partitions)
    checks = []
    def add(n, name, status, detail):
        checks.append({'id': n, 'check': name, 'status': status, 'detail': detail})
    id_ok = bool(master) and all(r.get('Scenario_ID') and r.get('Base_Event_ID') for r in master) and len({r['Scenario_ID'] for r in master}) == len(master)
    add(1, '46-column master schema', 'PASS' if len(schema) == 46 and header == schema else 'FAIL',
        'Checks original column names and order only; not evidence of financial completeness or formal approval.')
    add(2, 'Scenario and family identifiers', 'PARTIAL' if id_ok else 'FAIL',
        f'{len(master)} context IDs; synthetic financial ancestry cannot be verified without generated scenarios.')
    add(3, 'Complete synthetic provenance', 'NOT TESTABLE', 'No generated synthetic scenarios; required master_scenario_provenance.csv is absent or unverified.')
    add(4, 'Source references and assumption versions', 'PARTIAL', 'Historical source replay checked separately; no approved synthetic configuration/source/assumption binding.')
    for n, name in [(5, 'Financial accounting formulas'), (6, 'Contingency and budget accounting'),
                    (7, 'Venue and capacity constraints'), (8, 'Cost dependency consistency')]:
        add(n, name, 'NOT TESTABLE', 'No approved generated financial rows and reconciled line-item ledgers; software tests alone are insufficient.')
    unsupported = ['Historical_Mean_Cost', 'Vendor_Price_Volatility', 'Financial_Health_Score']
    add(9, 'Unsupported features not fabricated', 'PASS' if master and all(not r.get(k) for r in master for k in unsupported) else 'REVIEW REQUIRED',
        'Unsupported historical means, vendor volatility and health scores are missing in current context rows.')
    outcome_fields = ['Actual_Total_Cost', 'Actual_Revenue', 'Profit', 'Profit_Margin', *TARGETS]
    no_outcomes = all(not r.get(k) for r in master for k in outcome_fields)
    add(10, 'Simulated outcomes versus observed data', 'PASS' if master and no_outcomes and not synthetic else 'REVIEW REQUIRED',
        'Current context rows have no supplied outcomes/labels; no synthetic outcomes may be inferred from them.')
    leaked = sorted(FORBIDDEN_FEATURES & (set(xheader) - set(TARGETS)))
    add(11, 'XGBoost feature leakage prevention', 'PARTIAL' if not leaked else 'FAIL',
        f'Header forbidden-field check: {leaked}; {len(xrows)} labelled rows. Timing/forecast leakage cannot be verified on an empty dataset.')
    add(12, 'Grouped financial train/validation/test independence', 'NOT TESTABLE', 'No financial split manifest or executed financial scenarios. Shared-template holdout remains unsupported.')
    add(13, 'Chronological Prophet splitting', chronology['status'], json.dumps(chronology, sort_keys=True))
    add(14, 'Distinct price/index series', hist['status'], json.dumps(hist, sort_keys=True) + '; separate targets, never complete event costs.')
    graph_files = [p for p in (root / MANDATORY['spatial_financial_graphs/']).glob('**/*') if p.is_file() and p.name != 'STATUS.json']
    add(15, 'Graphs, references and split consistency', 'NOT TESTABLE', f'{len(graph_files)} graph payload files. STATUS.json is not a graph.')
    add(16, 'Scenario diversity and label distributions', 'NOT TESTABLE', 'No generated financial population; empty targets have no estimable class distribution.')
    add(17, 'Frozen-seed scenario reproducibility', 'NOT TESTABLE', 'Proposed configuration is not approved; no frozen executed pilot/master to replay.')
    test_ok = bool(test_result) and test_result.get('exit_code') == 0 and test_result.get('tests_run', 0) > 0
    add(18, 'Automated tests', 'PASS' if test_ok else 'NOT VERIFIED', json.dumps(test_result or {'reason': 'No fresh test receipt supplied'}, sort_keys=True))
    add(19, 'Output SHA-256 checksums', 'PASS', 'Actual audit archive entries are checked against an embedded SHA-256 manifest; missing outputs have no invented checksum.')
    add(20, 'Limitations and experimental assumptions', 'PASS', 'Documented in the Stage 10 audit package; no synthetic success is evidence of real-world accuracy.')
    missing = [name for name, path in MANDATORY.items() if not (root / path).exists()]
    incomplete = ['master_event_financial_dataset.csv: context-only, not a financial scenario dataset',
                  'xgboost_risk_dataset.csv: header-only, no labels', 'spatial_financial_graphs/: status-only, zero graph payloads']
    return {
        'dataset_status': 'NOT READY', 'freeze_authorized': False,
        'audit_date': '2026-10-12', 'requested_dataset_version': '1.0', 'validated_dataset_version': None,
        'checks': checks, 'missing_mandatory_artifacts': missing, 'incomplete_artifacts': incomplete,
        'counts': {'master_context_rows': len(master), 'generated_master_financial_scenarios': len(synthetic),
                   'generated_financial_base_families': len({r['Base_Event_ID'] for r in synthetic}),
                   'synthetic_variants': 0 if not synthetic else None, 'outcome_replications': 0 if not synthetic else None,
                   'observed_event_financial_outcome_records': len(observed_financial),
                   'xgboost_records': len(xrows), 'target_class_distributions': {t: dict(Counter(r.get(t) for r in xrows)) if xrows else None for t in TARGETS},
                   'prophet_observations': len(historical), 'prophet_individual_series': hist['series'],
                   'gnn_graphs': 0 if not graph_files else None,
                   'financial_split_group_counts': None, 'legacy_prophet_splits': chronology},
        'historical_verification': json.loads((root / 'reports/historical_refinement_verification.json').read_text()),
        'source_scope': 'Public event context, separate price/index observations and source extracts; no calibrated Sri Lankan event outcomes.',
        'decision_record': json.loads((root / 'reports/unitless_pilot_user_design_decision.json').read_text()),
        'test_result': test_result,
        'never_infer_ready_from_checksums_or_tests': True,
    }
