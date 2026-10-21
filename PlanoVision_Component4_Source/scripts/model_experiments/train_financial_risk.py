"""Run a predeclared, small baseline comparison from the frozen ZIP only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from component4.risk_experiment import archive_inputs, group_weights, metrics, select_model, write_table, nonoverlap_rows
from component4.release_input import assert_experiment_output, verified_release, sha256
from component4.split_derivative import create_overlay, validate_overlay, apply_overlay
from component4.risk_experiment import validate_rows


def run(run_id, split_overlay=None):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    policy = ROOT / 'config/experiments/financial_risk_baseline.v0.1.json'
    plan = json.loads(policy.read_text())
    archive, release, rows, spec, audit, input_hashes = archive_inputs()
    overlay_receipt = None
    experiment_version = 'v1.0'
    if split_overlay is not None:
        overlay_path = Path(split_overlay).resolve()
        overlay = json.loads(overlay_path.read_text(encoding='utf-8'))
        if overlay['source_archive_sha256'] != sha256(archive) or overlay['predictors'] != spec['predictors']:
            raise ValueError('overlay_frozen_input_mismatch')
        if any(overlay['source_payload_checksums'].get(name) != checksum for name, checksum in input_hashes.items()):
            raise ValueError('overlay_payload_mismatch')
        import csv, io
        with zipfile.ZipFile(archive) as source:
            ancestry = list(csv.DictReader(io.StringIO(source.read('prepared/xgboost/grouped_split_manifest.csv').decode('utf-8-sig'))))
        expected = create_overlay(rows, spec, ancestry)
        if overlay['assignments'] != expected['assignments'] or overlay['assignment_sha256'] != expected['assignment_sha256']:
            raise ValueError('overlay_not_reproducible_from_frozen_ancestry')
        overlay_audit = validate_overlay(rows, overlay)
        rows = apply_overlay(rows, overlay)
        audit = validate_rows(rows, spec)
        if audit['cross_split_feature_projection_keys'] != 0:
            raise ValueError('overlay_projection_leakage')
        overlay_receipt = {'path':str(overlay_path), 'sha256':sha256(overlay_path),
                           'assignment_sha256':overlay['assignment_sha256'], 'validation':overlay_audit,
                           'prior_test_exposure':'v1.0 results already inspected; exploratory reanalysis, not pristine unseen validation'}
        experiment_version = 'v1.1'
    archive_before = sha256(archive)
    if archive_before != plan['release_sha256']:
        raise ValueError('experiment_release_mismatch')
    original = ROOT / release['original_archive']['project_relative_path']
    if sha256(original) != archive_before:
        raise ValueError('original_zip_changed')
    release_files = {p.name: sha256(p) for p in archive.parent.iterdir() if p.is_file()}
    output = assert_experiment_output(ROOT / 'outputs/experiments' / experiment_version / run_id)
    report = assert_experiment_output(ROOT / 'reports/experiments' / experiment_version / run_id)
    if output.exists() or report.exists():
        raise ValueError('refuse_to_overwrite_existing_experiment')
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    protocol = {'plan': plan, 'policy_sha256': sha256(policy), 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'split_overlay':overlay_receipt,
                'archive_sha256': archive_before, 'input_member_sha256': input_hashes, 'split_audit': audit,
                'source_sha256': {'trainer': sha256(Path(__file__)), 'experiment_helpers': sha256(ROOT / 'component4/risk_experiment.py')},
                'runtime': {'python': platform.python_version(), **{k: importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','xgboost','joblib','threadpoolctl','cloudpickle')}},
                'state': 'PROTOCOL_RECORDED_BEFORE_FITTING'}
    if overlay_receipt:
        protocol['source_sha256']['split_derivative_helpers'] = sha256(ROOT / 'component4/split_derivative.py')
    (output / 'experiment_protocol.json').write_text(json.dumps(protocol, indent=2))
    partitions = {s: [r for r in rows if r['split'] == s] for s in ('train','validation','test')}
    nonoverlap = nonoverlap_rows(partitions, spec['predictors'])
    clean_ids = {s: {r['Scenario_ID'] for r in data} for s,data in nonoverlap.items()}
    clean_masks = {s: np.array([r['Scenario_ID'] in clean_ids[s] for r in partitions[s]]) for s in nonoverlap}
    clean_weights = {s: np.array(group_weights(data)) for s,data in nonoverlap.items()}
    (output / 'feature_overlap_audit.json').write_text(json.dumps({'audit':audit,
        'nonoverlap_rows':{s:len(v) for s,v in nonoverlap.items()},
        'excluded_from_selection_or_sensitivity':{s:[r['Scenario_ID'] for r in partitions[s] if r['Scenario_ID'] not in clean_ids[s]] for s in nonoverlap},
        'mask_origin':'planning_feature_values_only_no_target_labels', 'original_rows_or_splits_modified':False},indent=2))
    x = {s: np.array([[float(r[k]) for k in spec['predictors']] for r in data], dtype=np.float64) for s, data in partitions.items()}
    weights = {s: np.array(group_weights(data)) for s, data in partitions.items()}
    candidates, prediction_rows, test_rows, class_rows, importance_rows, subgroup_rows, sensitivity_rows = [], [], [], [], [], [], []
    selected = {}
    constructors = {'dummy_prior': DummyClassifier, 'decision_tree': DecisionTreeClassifier,
                    'random_forest': RandomForestClassifier, 'xgboost': XGBClassifier}
    for target in spec['targets']:
        y = {s: np.array([int(r[target]) for r in data]) for s, data in partitions.items()}
        for split in partitions:
            if len(np.unique(y[split])) != 2:
                raise ValueError('both_classes_required:' + target + ':' + split)
            counts = Counter(y[split].tolist())
            class_rows.append({'target': target, 'split': split, 'rows': len(y[split]), 'negative': counts[0], 'positive': counts[1], 'positive_rate': counts[1]/len(y[split])})
        fitted, scores = {}, {}
        for name, parameters in plan['candidate_models'].items():
            model = constructors[name](**parameters, random_state=plan['random_seed'])
            model.fit(x['train'], y['train'], sample_weight=weights['train'])
            fitted[name] = model
            p = model.predict_proba(x['validation'])[:, list(model.classes_).index(1)]
            mask = clean_masks['validation']
            for weighting, w in (('row', None), ('group_equal', clean_weights['validation'])):
                score = metrics(y['validation'][mask], p[mask], w)
                candidates.append({'target': target, 'model': name, 'split': 'validation_nonoverlap', 'rows':int(mask.sum()), 'weighting': weighting, **score})
                if weighting == 'group_equal':
                    scores[name] = score['log_loss']
            print('Fitted:', target, name, flush=True)
        chosen = select_model(scores, target)
        selected[target] = {'model': chosen, 'validation_nonoverlap_group_equal_log_loss': scores[chosen],
                            'reason': 'negative_control_prior_predeclared' if target == 'Vendor_Cost_Anomaly' else 'lowest_validation_nonoverlap_group_equal_log_loss'}
        model = fitted[chosen]
        joblib.dump(model, output / (target + '.joblib'))
        if chosen == 'xgboost':
            model.save_model(output / (target + '.xgboost.json'))
        # Test only the locked choice and fixed baseline; no comparison-driven retuning.
        for evaluated in dict.fromkeys((chosen, 'dummy_prior')):
            evaluated_model = fitted[evaluated]
            p = evaluated_model.predict_proba(x['test'])[:, list(evaluated_model.classes_).index(1)]
            for weighting, w in (('row',None), ('group_equal',weights['test'])):
                test_rows.append({'target': target, 'model': evaluated, 'selected': evaluated == chosen, 'split': 'test', 'weighting': weighting, **metrics(y['test'],p,w)})
            mask = clean_masks['test']
            for weighting, w in (('row',None), ('group_equal',clean_weights['test'])):
                sensitivity_rows.append({'target':target, 'model':evaluated, 'selected':evaluated==chosen, 'split':'test_nonoverlap', 'rows':int(mask.sum()), 'weighting':weighting, **metrics(y['test'][mask],p[mask],w)})
        for split in ('validation','test'):
            p = model.predict_proba(x[split])[:, list(model.classes_).index(1)]
            for r, value, truth in zip(partitions[split], p, y[split]):
                prediction_rows.append({'Scenario_ID': r['Scenario_ID'], 'Base_Event_ID': r['Base_Event_ID'], 'split_group_id': r['split_group_id'], 'split': split,
                    'target': target, 'model': chosen, 'simulated_target': int(truth), 'model_score_uncalibrated': float(value), 'predicted_label_threshold_0_5': int(value >= 0.5),
                    'planning_features_unseen_in_prior_partitions':r['Scenario_ID'] in clean_ids[split],
                    'scope': 'synthetic_conditional_experiment_not_real_world_probability'})
            if split == 'test':
                for archetype in ('Wedding','Corporate'):
                    mask = np.array([r['Event_Type_' + archetype] == '1' for r in partitions[split]])
                    subgroup_rows.append({'target': target, 'model': chosen, 'archetype': archetype, 'rows': int(mask.sum()), **metrics(y[split][mask], p[mask])})
        if hasattr(model, 'feature_importances_'):
            for name, value in zip(spec['predictors'], model.feature_importances_):
                importance_rows.append({'target': target, 'model': chosen, 'feature': name, 'importance': float(value), 'method': 'model_internal_importance_not_SHAP_or_causal_effect'})
        reloaded = joblib.load(output / (target + '.joblib'))
        if not np.array_equal(model.predict_proba(x['validation']), reloaded.predict_proba(x['validation'])):
            raise ValueError('model_reload_prediction_mismatch')
    write_table(report / 'validation_candidates.csv', candidates)
    write_table(report / 'selected_test_metrics.csv', test_rows)
    write_table(output / 'selected_predictions.csv', prediction_rows)
    write_table(report / 'class_distributions.csv', class_rows)
    write_table(report / 'feature_importance.csv', importance_rows, ['target','model','feature','importance','method'])
    write_table(report / 'test_archetype_metrics.csv', subgroup_rows)
    write_table(report / 'test_nonoverlap_sensitivity.csv', sensitivity_rows)
    # Reconcile written prediction IDs/counts and unchanged release, not just model scores.
    expected_predictions = (len(partitions['validation']) + len(partitions['test'])) * len(spec['targets'])
    if len(prediction_rows) != expected_predictions or len({(r['Scenario_ID'],r['target']) for r in prediction_rows}) != expected_predictions:
        raise ValueError('prediction_scope_failed')
    import csv
    for path, expected in ((report/'validation_candidates.csv',len(candidates)), (report/'selected_test_metrics.csv',len(test_rows)),
                           (output/'selected_predictions.csv',expected_predictions), (report/'class_distributions.csv',9),
                           (report/'feature_importance.csv',len(importance_rows)), (report/'test_archetype_metrics.csv',6),
                           (report/'test_nonoverlap_sensitivity.csv',len(sensitivity_rows))):
        with path.open(encoding='utf-8', newline='') as stream:
            if sum(1 for _ in csv.DictReader(stream)) != expected:
                raise ValueError('export_count:' + path.name)
    verified_release()
    if sha256(original) != archive_before or any(sha256(archive.parent / name) != digest for name,digest in release_files.items()):
        raise ValueError('release_changed_during_training')
    if overlay_receipt and sha256(overlay_path) != overlay_receipt['sha256']:
        raise ValueError('overlay_changed_during_training')
    selected_rows = [r for r in test_rows if r['selected'] and r['weighting'] == 'row']
    summary = {'status': 'PASS_INTERNAL_SYNTHETIC_EXPERIMENT', 'selected_models': selected, 'selected_test_metrics': selected_rows,
               'split_audit': audit, 'threshold': 0.5, 'release_before_sha256': archive_before, 'release_after_sha256': sha256(archive),
               'nonoverlap_partition_rows':{s:len(v) for s,v in nonoverlap.items()},
               'selected_test_nonoverlap_metrics':[r for r in sensitivity_rows if r['selected'] and r['weighting']=='row'],
               'release_unchanged': True, 'model_reload_checks': 'PASS', 'prediction_export_rows': expected_predictions,
               'split_overlay': overlay_receipt,
               'validation_selection_only': True, 'test_retuning_performed': False, 'real_world_validity_established': False,
               'runtime': protocol['runtime'], 'model_directory': str(output), 'report_directory': str(report)}
    (report / 'experiment_summary.json').write_text(json.dumps(summary, indent=2))
    lines = ['# Financial-risk experiment ' + experiment_version, '', 'Synthetic-only, conditional in-simulator evaluation. These are NOT actual Sri Lankan financial forecasts or calibrated real-world risk probabilities.', '',
             '| Target | Selected classifier | Test accuracy | Balanced accuracy | ROC-AUC | Log loss |', '|---|---|---:|---:|---:|---:|']
    for r in selected_rows:
        lines.append(f"| {r['target']} | {r['model']} | {r['accuracy']:.4f} | {r['balanced_accuracy']:.4f} | {r['roc_auc']:.4f} | {r['log_loss']:.4f} |")
    lines += ['', '## Protocol and interpretation', '',
        'Frozen release is unchanged. Train/validation/test rows are 4500/1500/1500, connected groups 711/248/248. Only the fixed 21 archived planning predictors are used; metadata, realized outcomes and injected shocks are excluded. No historical LKR prices are silently joined to score scenarios.',
        'Models fit training only with equal total weight per connected group. Fixed small parameter settings were recorded before fitting; no search, SMOTE, scaling, calibration, threshold tuning or validation refit. Select positive-risk models using group-equal validation log loss on feature vectors absent from training, with deterministic tie breaking. Test only the chosen classifier and prior baseline. Report row metrics plus group-equal sensitivity metrics. No IID confidence intervals are claimed for related rows.',
        f"Feature projection audit found {audit['cross_split_feature_projection_keys']} shared feature vectors involving {audit['cross_split_feature_projection_rows']} rows across original splits. These are aliases of distinct original planning contexts (for example swapped stage dimensions) under the archived 21-field projection. Groups/families remain disjoint, but strict model-input uniqueness did not hold. No release rows or splits were changed. Model selection uses {len(nonoverlap['validation'])} nonoverlap validation rows; the additional test sensitivity view uses {len(nonoverlap['test'])} rows unseen in train or validation. Masks were defined before fitting using inputs only. Full-test results retain all 1500 original test rows and must be interpreted alongside that sensitivity view.",
        'Vendor_Cost_Anomaly is a random-injection negative control; its final classifier is the prior baseline by predeclared policy, even if a candidate scores better by chance. A constant baseline can have high accuracy for rare positives while having zero recall; do not present it as successful anomaly detection.',
        'Scores are uncalibrated. Internal feature importance is not SHAP, causal attribution or evidence that a correlated feature uniquely drives risk. Expected receipts and costs are pre-event synthetic values; rule-related predictors can predict simulator labels without validating the accounting assumptions.',
        'There are zero observed complete event-financial outcomes, 19 independently unvalidated formulas, shared hypothetical venue/vendor/source templates and random realization noise. Unseen-template or real-world predictive performance is unsupported. Synthetic test success is not market validity. This one held-out run is exploratory and not external validation.',
        '', '## Reproduce in Windows', '', 'Run from the existing project root using the isolated environment:', '```powershell',
        './work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/train_financial_risk.py --run-id financial_risk_v0_1_replay', '```',
        'Use a new run ID; existing experiments are never overwritten. requirements.txt in the model directory records exact library versions. Load only trusted local joblib artifacts; pickle/joblib loading can execute code.',
        '', '## Methods references', '', '[scikit-learn metric definitions](https://scikit-learn.org/stable/modules/model_evaluation.html)', '[XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)']
    if overlay_receipt:
        # Replace legacy v1.0-specific prose, not the empirical results or methods.
        start = lines.index('## Protocol and interpretation')
        lines = lines[:start] + ['## Protocol and interpretation', '',
            f"Frozen v1.0 archive and scenario values are unchanged. Corrected overlay row counts: {audit['row_counts']}; connected group counts: {audit['group_counts']}. The overlay is recorded in experiment_protocol.json and bound by SHA-256.",
            'Only the fixed 21 pre-event predictors are used. No realized outcomes, hidden shocks, metadata or historical LKR rates enter the model inputs. Overlay assignments were independently reproduced from frozen ancestry and feature signatures before fitting.',
            'Zero identical feature vectors cross splits. Root families, old groups, full planning fingerprints and feature signatures are grouped together. The repaired assignment minimizes changes to original splits rather than introducing a new randomized sample.',
            'Training-only fitting with equal total weight per connected group. Reuse fixed v0.1 candidate settings, seed and 0.5 threshold. No tuning, calibration, resampling or train-plus-validation refit. Select using validation group-equal log loss; evaluate only the locked choice and prior baseline on test.',
            'Vendor_Cost_Anomaly remains a random-injection negative control with the prior classifier predeclared as the final choice. High majority-class accuracy is not evidence of useful anomaly prediction.',
            'This is exploratory reanalysis: v1.0 test outcomes were previously inspected. Repaired splits do not create a pristine holdout or independent external validation. Shared templates do not support unseen-venue/vendor evaluation.',
            'Zero observed completed event-financial outcomes; hypothetical dimensionless financial values; 19 formulas without independent domain validation. Scores are uncalibrated, feature importance is not SHAP or causal explanation, and synthetic accuracy does not establish Sri Lankan market prediction accuracy.',
            '', '## Reproduce on Windows', '', 'Use a new run ID; previous experiment directories are never overwritten.', '```powershell',
            './work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/train_financial_risk.py --run-id financial_risk_v1_1_replay --split-overlay data/experiments/v1.1/split_integrity_derivative/split_manifest.v1.1.json',
            '```', 'Exact runtime versions are in requirements.txt and experiment_protocol.json. Load only trusted local joblib artifacts. The pre-fit protocol and output checksum file bind this run to its inputs.']
    (report / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (output / 'requirements.txt').write_text('\n'.join(f'{k}=={v}' for k,v in protocol['runtime'].items() if k != 'python') + '\n')
    # File checksums bind predictions, saved models and interpretation to this run.
    all_outputs = list(output.iterdir()) + list(report.iterdir())
    (report / 'checksums.sha256').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(ROOT)).replace('\\','/') + '\n' for p in sorted(all_outputs) if p.is_file()))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='financial_risk_v0_1_20261012')
    parser.add_argument('--split-overlay', help='Explicit checksum-bound v1.1 split overlay; original release remains unchanged')
    args = parser.parse_args()
    run(args.run_id, args.split_overlay)
