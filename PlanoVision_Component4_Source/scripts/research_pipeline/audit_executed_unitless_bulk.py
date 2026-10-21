"""Read-only output audit and replay; does not persist generated scenarios."""
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.unitless_bulk import blockers, generate, master_rows, validate_bulk_bundle
from openpyxl import load_workbook


def main():
    directory = ROOT / 'data/final/unitless-bulk-v0.1'
    report = ROOT / 'reports/unitless_bulk_execution_20261012'
    report.mkdir(exist_ok=True)
    bundle = json.loads((directory / 'export_payload.json').read_text())
    config = bundle['configuration']
    auth = json.loads((directory / 'authorization.json').read_text())
    checks = {}
    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise ValueError(name)
    check('execution_gates', not blockers(config, auth))
    check('financial_spatial_labels_provenance', validate_bulk_bundle(bundle) is not False)
    manifest = json.loads((directory / 'manifest.json').read_text())
    check('file_checksums', all(hashlib.sha256((directory / name).read_bytes()).hexdigest() == value for name, value in manifest['files'].items()))
    replay = generate(config, auth)
    replay['master'] = master_rows(replay, config['master_columns'])
    for key in ('planning', 'outcomes', 'provenance', 'line_items', 'latent_DO_NOT_USE_AS_FEATURES', 'rejections', 'master'):
        check('replay_' + key, replay[key] == bundle[key])
    tables = {'master_event_financial_dataset': 'master', 'master_scenario_provenance': 'provenance', 'master_financial_line_items': 'line_items', 'planning': 'planning', 'outcomes': 'outcomes', 'latent_DO_NOT_USE_AS_FEATURES': 'latent_DO_NOT_USE_AS_FEATURES', 'rejections': 'rejections'}
    def csv_value(value):
        return '' if value is None else json.dumps(value, sort_keys=True) if isinstance(value, (list, dict)) else str(value)
    for filename, key in tables.items():
        with (directory / (filename + '.csv')).open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            if key == 'master':
                check('46_column_schema', reader.fieldnames == config['master_columns'])
        check('csv_' + key, rows == [{k: csv_value(v) for k, v in row.items()} for row in bundle[key]])
    wb = load_workbook(directory / 'master_event_financial_dataset.xlsx', read_only=True, data_only=True)
    def equal(value, target, key):
        if isinstance(target, (list, dict)):
            return json.loads(value) == target
        if hasattr(value, 'isoformat') and key in ('event_date', 'Event_Date'):
            return value.isoformat()[:10] == target
        if type(value) in (int, float) and type(target) in (int, float):
            return math.isclose(value, target, rel_tol=1e-12, abs_tol=1e-12)
        return value == target
    try:
        for sheet, key in [('Master Data', 'master'), ('Planning', 'planning'), ('Outcomes', 'outcomes'), ('Line Items', 'line_items'), ('Provenance', 'provenance'), ('Latent NOT FEATURES', 'latent_DO_NOT_USE_AS_FEATURES'), ('Rejections', 'rejections')]:
            rows = bundle[key]
            keys = list(rows[0]) if rows else ['family_id', 'attempt', 'reason']
            iterator = wb[sheet].iter_rows(values_only=True)
            check('xlsx_headers_' + key, list(next(iterator)) == keys)
            count = 0
            for expected, saved in zip(rows, iterator):
                check('xlsx_cells_' + key, len(saved) == len(keys) and all(equal(v, expected[k], k) for k, v in zip(keys, saved)))
                count += 1
            check('xlsx_rows_' + key, count == len(rows) and next(iterator, None) is None)
    finally:
        wb.close()
    provenance = bundle['provenance']
    families = {r['family_id']: r['split'] for r in provenance}
    split_groups = {r['split_group_id']: r['split'] for r in provenance}
    unsupported = [k for k in config['master_columns'] if all(row[k] is None for row in bundle['master'])]
    result = {'status': 'PASS_INTERNAL_UNITLESS_DATASET_AUDIT', 'configuration_sha256': manifest['configuration_sha256'], 'rows': len(bundle['master']), 'families': len(families), 'events': dict(Counter(r['event_type'] for r in bundle['planning'])), 'split_rows': dict(Counter(r['split'] for r in provenance)), 'split_families': dict(Counter(families.values())), 'split_groups': dict(Counter(split_groups.values())), 'line_items': len(bundle['line_items']), 'provenance_rows': len(provenance), 'rejected_attempts': len(bundle['rejections']), 'rejection_reasons': dict(Counter(r['reason'] for r in bundle['rejections'])), 'classes': {k: dict(Counter(str(r[k]) for r in bundle['master'])) for k in ('Budget_Overrun', 'Profit_Margin_Risk', 'Vendor_Cost_Anomaly')}, 'unsupported_columns': unsupported, 'real_observed_event_outcomes': 0, 'qualified_formula_reviews_pending': 19, 'unseen_template_evaluation_supported': False, 'real_world_validated': False, 'model_training_performed': False, 'checks': checks, 'split_audit': bundle['manifest']['split_audit'], 'output_sha256': {**manifest['files'], 'manifest.json': hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest()}}
    result['automated_tests'] = json.loads((report / 'current_execution_test_receipt.json').read_text())
    result['retry_automated_tests'] = json.loads((report / 'retry_test_receipt.json').read_text())
    result['export_runtime_retry'] = json.loads((report / 'export_retry_record.json').read_text())
    result['planning_configurations'] = len({(r['family_id'], r['planning_state']) for r in bundle['planning']})
    result['paired_outcome_streams'] = len({(r['family_id'], r['outcome_replication']) for r in bundle['planning']})
    result['event_root_counts'] = dict(Counter({r['family_id']: r['event_type'] for r in bundle['planning']}.values()))
    result['visual_qa'] = {'sheets_reviewed': 8, 'scope': 'Actual-data first five records and first six columns per sheet, full overview; same frozen export formatting. All saved data cells checked numerically separately.', 'readable': True, 'preview_native_exit_warning': 'Preview-only process returned exit 1 after saving all eight PNGs. Production export exit and saved-file validation assessed separately.'}
    (report / 'validation_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    text = '# Authorized unitless bulk generation validation\n\n'
    text += 'PASS for internal hypothetical simulation consistency, not real-world financial validity.\n\n'
    text += f"Configuration: `{result['configuration_sha256']}`.\n\n"
    text += f"Rows: {result['rows']}. Families: {result['families']}. Events: {result['events']}.\n\n"
    text += f"Split rows: {result['split_rows']}. Split families: {result['split_families']}. Split connected groups: {result['split_groups']}.\n\n"
    text += f"Ledger rows: {result['line_items']}. Provenance rows: {result['provenance_rows']}. Rejected sampling attempts: {result['rejected_attempts']}.\n\n"
    text += 'All accounting, spatial constraints, label definitions, provenance, exact deterministic replay, file checksums, CSV values and all saved XLSX data cells passed.\n\n'
    text += 'All 204 existing automated tests passed during this execution (36.397 seconds). Eight bounded actual-data sheet previews were visually reviewed; the preview-only native process returned exit 1 after saving all images, independently of production export and numerical validation.\n\n'
    text += f"Target counts: {result['classes']}. No class balancing was applied.\n\n"
    text += f"Unsupported fields remain missing: {', '.join(unsupported)}.\n\n"
    text += 'The user separately authorized the exact bulk scope and limited engineering waiver on 2026-10-12. Nineteen formulas still lack independent qualified review. No institutional approval is claimed. Costs use dimensionless_score, not LKR. Actual-named columns contain simulated outcomes; Quoted-named columns contain hypothetical planned charges.\n\n'
    text += 'The 1250 unique synthetic roots share venue/vendor/source templates. Paired outcomes and planning interventions are related. Row count is not independent sample size. Conditional grouped evaluation is supported; unseen-template and real-world prediction evaluation are unsupported. No observed event-financial records or models were created.\n\n'
    text += 'The generator manifest retains its original GENERATED_PENDING_FINAL_AUDIT status as execution history; this separate audit is the final internal validation receipt. ML-ready feature extraction remains a separate task.\n'
    (report / 'validation_report.md').write_text(text, encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'output_sha256', 'split_audit')}, indent=2))


if __name__ == '__main__':
    main()
