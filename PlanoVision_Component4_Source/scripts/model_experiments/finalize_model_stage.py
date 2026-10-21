"""Verify completed experiment artifacts and write an honest scope-bound summary."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.release_input import verified_release, sha256, assert_experiment_output
from component4.risk_experiment import archive_inputs
from component4.split_derivative import apply_overlay, validate_overlay
from scripts.model_experiments.verify_financial_risk_run import verify


def main():
    runs = {
        'financial': ('v1.1', 'financial_risk_v1_1_20261012'),
        'shap': ('v1.1', 'financial_shap_v1_1_memory_20261012'),
        'graph': ('v1.1', 'graph_risk_v1_1_20261012'),
        'prophet_fixed': ('v1.0', 'prophet_historical_v0_1_native_20261012'),
        'prophet_rolling': ('v1.1', 'prophet_rolling_v1_1_20261012'),
    }
    receipts = {}
    for name, (version, run) in runs.items():
        folder = ROOT / 'reports/experiments' / version / run
        for line in (folder / 'checksums.sha256').read_text().splitlines():
            expected, relative = line.split('  ', 1)
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or sha256(path) != expected:
                raise ValueError('artifact_checksum_mismatch:' + relative)
        receipt_path = folder / ('verification.json' if name in ('shap', 'prophet_rolling') else 'experiment_summary.json')
        receipts[name] = json.loads(receipt_path.read_text())
        if not receipts[name]['status'].startswith('PASS'):
            raise ValueError('experiment_not_pass:' + name)
    verify(runs['financial'][1])
    archive, release, rows, spec, _, _ = archive_inputs()
    overlay = json.loads((ROOT / 'data/experiments/v1.1/split_integrity_derivative/split_manifest.v1.1.json').read_text())
    validate_overlay(rows, overlay)
    revised = {r['Scenario_ID']: r for r in apply_overlay(rows, overlay)}
    graph_output = ROOT / 'outputs/experiments' / runs['graph'][0] / runs['graph'][1]
    graph_report = ROOT / 'reports/experiments' / runs['graph'][0] / runs['graph'][1]
    if receipts['financial']['split_overlay']['assignment_sha256'] != receipts['graph']['split_overlay']['assignment_sha256']:
        raise ValueError('financial_graph_split_disagreement')
    graph_metrics = json.loads((graph_report / 'test_metrics.json').read_text())
    selected_graph = []
    with np.load(graph_output / 'heldout_predictions.npz', allow_pickle=False) as saved:
        ids = saved['graph_id'].tolist()
        if len(ids) != 1500 or len(set(ids)) != 1500 or set(ids) != {s for s, r in revised.items() if r['split'] == 'test'}:
            raise ValueError('graph_prediction_scope_mismatch')
        for i, sid in enumerate(ids):
            r = revised[sid]
            if saved['split_group_id'][i] != r['split_group_id'] or not np.array_equal(saved['targets'][i], [int(r[t]) for t in spec['targets']]):
                raise ValueError('graph_prediction_group_or_label_mismatch')
        for j, target in enumerate(spec['targets']):
            model = receipts['graph']['selected'][target]
            metric = next(m for m in graph_metrics if m['target'] == target and m['model'] == model and m['population'] == 'full_test' and m['weighting'] == 'row')
            p = saved[model][:, j]
            if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any() or abs(float(np.mean((p >= .5) == saved['targets'][:, j])) - metric['accuracy']) > 1e-12:
                raise ValueError('graph_metric_reconciliation_failed')
            selected_graph.append(metric)
    rolling_report = ROOT / 'reports/experiments' / runs['prophet_rolling'][0] / runs['prophet_rolling'][1]
    rolling = json.loads((rolling_report / 'per_series_summary.json').read_text())
    tests_path = ROOT / 'reports/public_hotel_benchmark_test_results.json'
    tests = json.loads(tests_path.read_text())
    if tests['full_suite_status'] != 'PASS' or tests['errors'] or tests['failures'] or not tests['release_zip_files_unchanged']:
        raise ValueError('full_test_suite_not_pass')
    verified_release()
    original = ROOT / release['original_archive']['project_relative_path']
    if sha256(original) != release['original_archive']['sha256']:
        raise ValueError('original_archive_changed')
    destination = assert_experiment_output(ROOT / 'reports/model_stage_final_20261012')
    if destination.exists():
        raise ValueError('refuse_existing_consolidated_report')
    destination.mkdir(parents=True)
    result = {'status': 'COMPLETE_INTERNAL_RESEARCH_MODEL_PROTOCOL_NOT_PRODUCTION_OR_REAL_WORLD_VALIDATION',
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'runs': {name: {'version': version, 'run_id': run} for name, (version, run) in runs.items()},
        'financial_selected_test': receipts['financial']['selected_test_metrics'],
        'graph_selected_test': selected_graph, 'prophet_fixed_selection': receipts['prophet_fixed']['selected_model_counts'],
        'rolling_verification': receipts['prophet_rolling'], 'tests': {'count': tests['tests_run'], 'failures':0, 'errors':0, 'skips':tests['skipped']},
        'tests_receipt_sha256': sha256(tests_path), 'release_zip_sha256': sha256(archive), 'original_zip_sha256':sha256(original),
        'dataset_records_changed': False, 'synthetic_rows':7500, 'independent_synthetic_roots':1250,
        'observed_completed_event_outcomes':0, 'unseen_template_evaluation':'UNSUPPORTED',
        'vendor_anomaly_detector':'NOT_ESTABLISHED; dummy prior negative control only',
        'graph_dependency_advantage':'NOT_ESTABLISHED; shuffled dependency model selected by validation',
        'calibrated_probabilities': False, 'real_world_prediction_validity':False,
        'next_stage':'Monte Carlo and consistent What-If decision support; frontend remains deferred'}
    (destination / 'MODEL_STAGE_COMPLETION.json').write_text(json.dumps(result, indent=2))
    (destination / 'automated_test_receipt.json').write_text(json.dumps(tests, indent=2))
    lines = ['# Component 4 — model stage completion', '',
        'Status: **COMPLETE for the declared internal research experiment protocol.** This is not 100% prediction accuracy, production readiness, institutional approval or real-world validation. Unsupported claims below are explicitly excluded rather than represented as completed scientific findings.', '',
        '## Completed work', '',
        '- Financial risk: prior, Decision Tree, Random Forest and XGBoost validation comparison; locked test evaluation; saved selected models and reload verification. Corrected v1.1 overlay uses 4,506/1,494/1,500 rows with disjoint connected ancestry and identical feature signatures.',
        '- Graph prototype: directed dependencies, self-only and shuffled-dependency GAT variants; training-only standardization; validation checkpoint/model selection; all fixed ablation results; saved checkpoints and exact serialization replay. Same overlay as financial models. All 1,500 exported test IDs, groups and synthetic targets were independently reconciled.',
        '- Historical forecasting: 12 separate observed price/index Prophet models with naive baselines and chronological fixed-origin test evaluation, plus 36 additional fits at three predeclared expanding origins per series and three-month horizons. Rolling checks never use original test records or change prior model selection. Each series retains its unit; no event-total-cost target is claimed.',
        '- SHAP: all 1,500 test scenarios for each selected financial XGBoost target; raw-margin additivity, score reconciliation, group-equal global summaries and fixed-ID local examples. No retraining and no causal claim.', '',
        '## Financial and graph results', '', '| Model | Target | Test accuracy | Balanced accuracy | ROC-AUC |', '|---|---|---:|---:|---:|']
    for name, records in (('Financial', result['financial_selected_test']), ('Graph', selected_graph)):
        for r in records:
            lines.append(f"| {name}: {r['model']} | {r['target']} | {r['accuracy']:.4f} | {r['balanced_accuracy']:.4f} | {r['roc_auc']:.4f} |")
    lines += ['', 'Vendor anomaly accuracy of 90% comes from predicting the majority class: recall is zero and balanced accuracy is 50%. It is not a useful trained detector.',
        'The selected graph variant has shuffled dependencies. This experiment does not establish added value of the designed spatial-financial edges. Small score differences versus XGBoost do not establish statistical superiority or robust seed stability.', '',
        '## Prophet robustness results', '',
        'The original fixed-origin validation choice remains last-value for 9 series and Prophet for 3. The following mean three-fold MAEs are descriptive robustness results, not a new model-selection policy. Never pool errors across different units.', '',
        '| Series | Unit | Prophet mean fold MAE | Last-value mean fold MAE | Seasonal-naive mean fold MAE |', '|---|---|---:|---:|---:|']
    for sid in sorted({r['series_id'] for r in rolling}):
        by_method = {r['method']: r for r in rolling if r['series_id'] == sid}
        lines.append(f"| {sid} | {by_method['prophet']['unit']} | {by_method['prophet']['mean_fold_mae']:.3f} | {by_method['last_value']['mean_fold_mae']:.3f} | {by_method['seasonal_naive_12']['mean_fold_mae']:.3f} |")
    lines += ['', '## Verification and scientific limits', '',
        f"Full suite: {tests['tests_run']} tests passed, zero failures/errors. Checksum inventories for all five successful experiment runs verified. Both ZIP hashes remain `{sha256(archive)}`. All original 7,500 synthetic records and 1,900 selected public measurements remain unchanged.",
        'There are zero observed complete event-financial outcomes and 19 independently unvalidated formulas. Financial fields are hypothetical dimensionless scores, not Sri Lankan quotations. Shared venue/vendor assumptions and one fixed graph topology rule out unseen-template validation. Previously inspected test results make the corrected-split analysis exploratory. Model scores are uncalibrated. Independent-seed stability and formal statistical superiority were not demonstrated.',
        'Historical source flags remain unresolved review candidates, not automatically erroneous measurements. Month keys are not verified publisher release dates; this is retrospective analysis, not live-vintage forecasting. Negative forecasts, long horizons and weaker-than-baseline Prophet performance remain reported. No calibrated prediction intervals are claimed.',
        'No further dataset rebuild or XGBoost retraining is required to complete this scoped stage. Real-world validation, deployment calibration or broader claims would require a separately defined experiment and suitable evidence.', '',
        '## Artifacts and reproduction', '']
    for name, (version, run) in runs.items():
        lines.append(f'- {name}: `reports/experiments/{version}/{run}/README.md`; saved models or explanations: `outputs/experiments/{version}/{run}/`. Exact run commands and runtime/protocol hashes are retained there. Use new run IDs; do not overwrite previous runs.')
    lines += ['', 'Read-only consolidated integrity command:', '```powershell',
        './work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/verify_financial_risk_run.py --run-id financial_risk_v1_1_20261012',
        '```', 'Frozen data remains an immutable input. New work belongs outside dataset_releases. Next planned stage is Monte Carlo and consistent What-If decision support, not another repeat of dataset engineering.']
    (destination / 'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (destination / 'checksums.sha256').write_text(''.join(sha256(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in sorted(destination.iterdir()) if p.is_file()))
    print(json.dumps({'status':result['status'], 'tests':result['tests'], 'report':str(destination / 'README.md'),
                      'graph_prediction_reconciliation':'PASS', 'all_five_experiment_checksums':'PASS',
                      'original_and_release_zip_sha256':sha256(archive)}, indent=2))


if __name__ == '__main__':
    main()
