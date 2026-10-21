"""Explain saved XGBoost classifiers only: no training, tuning or data mutation."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from xgboost import Booster, DMatrix
from component4.model_explanations import validate_additivity, summarize_features
from component4.risk_experiment import archive_inputs, group_weights
from component4.split_derivative import apply_overlay, validate_overlay
from component4.release_input import sha256, assert_experiment_output, verified_release
from scripts.model_experiments.verify_financial_risk_run import verify

SOURCE_RUN = 'financial_risk_v1_1_20261012'
TARGETS = ('Budget_Overrun', 'Profit_Margin_Risk')


def run(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    verify(SOURCE_RUN)
    model_dir = ROOT / 'outputs/experiments/v1.1' / SOURCE_RUN
    source_report = ROOT / 'reports/experiments/v1.1' / SOURCE_RUN
    summary = json.loads((source_report / 'experiment_summary.json').read_text())
    archive, release, rows, spec, _, _ = archive_inputs()
    overlay_path = Path(summary['split_overlay']['path'])
    overlay = json.loads(overlay_path.read_text())
    validate_overlay(rows, overlay)
    rows = sorted((r for r in apply_overlay(rows, overlay) if r['split'] == 'test'), key=lambda r: r['Scenario_ID'])
    with (model_dir / 'selected_predictions.csv').open(newline='', encoding='utf-8') as stream:
        scores = {(r['Scenario_ID'], r['target']): float(r['model_score_uncalibrated'])
                  for r in csv.DictReader(stream) if r['split'] == 'test'}
    original = ROOT / release['original_archive']['project_relative_path']
    protected = [archive, original, overlay_path, source_report / 'experiment_summary.json',
                 model_dir / 'experiment_protocol.json'] + [model_dir / (t + '.xgboost.json') for t in TARGETS]
    before = {str(p.relative_to(ROOT)): sha256(p) for p in protected}
    output = assert_experiment_output(ROOT / 'outputs/experiments/v1.1' / run_id)
    report = assert_experiment_output(ROOT / 'reports/experiments/v1.1' / run_id)
    if output.exists() or report.exists():
        raise ValueError('refuse_existing_explanation_run')
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    protocol = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'source_run': SOURCE_RUN,
        'input_checksums': before, 'explained_partition': 'test', 'selection': 'all test rows, no cherry-picking',
        'method': 'native XGBoost pred_contribs=True, approx_contribs=False; model tree-path cover reference',
        'scale': 'binary raw log-odds; bias plus contributions sum to raw margin, sigmoid gives uncalibrated model score',
        'scope': 'descriptive explanation only; already-inspected synthetic test set; no performance-based tuning',
        'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in (Path(__file__), ROOT / 'component4/model_explanations.py')},
        'runtime': {p: importlib.metadata.version(p) for p in ('numpy', 'xgboost', 'matplotlib')},
        'training_performed': False}
    (output / 'explanation_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    x = np.array([[float(r[f]) for f in spec['predictors']] for r in rows], dtype=np.float64)
    matrix = DMatrix(x)
    results, examples = {}, []
    for target in TARGETS:
        if summary['selected_models'][target]['model'] != 'xgboost':
            raise ValueError('unsupported_selected_classifier')
        booster = Booster()
        # Memory loading avoids native Windows path canonicalization restrictions.
        booster.load_model(bytearray((model_dir / (target + '.xgboost.json')).read_bytes()))
        if booster.num_features() != len(spec['predictors']):
            raise ValueError('model_feature_count_mismatch')
        contributions = booster.predict(matrix, pred_contribs=True, approx_contribs=False)
        margins = booster.predict(matrix, output_margin=True)
        probabilities = booster.predict(matrix)
        additive = validate_additivity(contributions, margins, probabilities, len(spec['predictors']))
        saved = np.array([scores[(r['Scenario_ID'], target)] for r in rows])
        if not np.allclose(saved, probabilities, rtol=1e-6, atol=1e-7):
            raise ValueError('saved_prediction_mismatch')
        features = summarize_features(contributions, spec['predictors'], group_weights(rows))
        results[target] = {'additivity': additive, 'saved_scores_match': True, 'features': features}
        np.savez_compressed(output / (target + '.shap.npz'),
            scenario_ids=np.array([r['Scenario_ID'] for r in rows]), predictors=np.array(spec['predictors']),
            planning_inputs=x, shap_values=contributions[:, :-1], bias=contributions[:, -1],
            raw_margin=margins, uncalibrated_score=probabilities)
        # Fixed ID ordering, one example per archetype: not chosen by outcomes or errors.
        for archetype in ('Wedding', 'Corporate'):
            index = next(i for i, r in enumerate(rows) if r['Event_Type_' + archetype] == '1')
            examples.append({'Scenario_ID': rows[index]['Scenario_ID'], 'event_type': archetype, 'target': target,
                'bias_log_odds': float(contributions[index, -1]), 'raw_margin': float(margins[index]),
                'uncalibrated_model_score': float(probabilities[index]),
                'contributions': [{'feature': f, 'planning_value': float(x[index, j]),
                    'shap_log_odds': float(contributions[index, j])} for j, f in enumerate(spec['predictors'])]})
    (report / 'global_shap_summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    (report / 'local_explanation_examples.json').write_text(json.dumps(examples, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    for axis, target in zip(axes, TARGETS):
        top = list(reversed(results[target]['features'][:10]))
        axis.barh([r['feature'].replace('_', ' ') for r in top],
                  [r['mean_absolute_shap_group_equal'] for r in top], color='#335c81')
        axis.set_title(target.replace('_', ' '))
        axis.set_xlabel('Group-equal mean |SHAP| (log-odds)')
        axis.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Synthetic XGBoost explanations — descriptive, not causal', fontsize=13)
    fig.savefig(report / 'shap_overview.png', dpi=150)
    plt.close(fig)
    verified_release()
    if before != {str(p.relative_to(ROOT)): sha256(p) for p in protected}:
        raise ValueError('protected_inputs_changed')
    receipt = {'status': 'PASS', 'source_run': SOURCE_RUN, 'explained_rows_per_target': len(rows),
        'targets_explained': list(TARGETS), 'feature_count': len(spec['predictors']),
        'models_retrained': False, 'dataset_or_model_files_changed': False,
        'margin_additivity_and_saved_score_checks': 'PASS', 'vendor_anomaly': 'not explained; prior-only negative control',
        'global_top_features': {t: results[t]['features'][:3] for t in TARGETS}}
    (report / 'verification.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    readme = '''# Financial-risk SHAP explanations

Existing saved v1.1 XGBoost models were explained without retraining. All 1,500 test scenarios were covered separately for Budget_Overrun and Profit_Margin_Risk, with the exact 21 planning predictors. No prediction-time outcome fields enter these explanations.

## Meaning and checks

Native XGBoost TreeSHAP uses the model's tree-path cover reference, not a newly sampled real-event background population. Contributions are in raw binary **log-odds**, not LKR, cost units, percentages or probability-point changes. The bias plus all 21 contributions reconstructs the raw model margin; applying the logistic function reconstructs the uncalibrated score. Both checks passed, and scores match the already-saved test predictions.

See global_shap_summary.json for row-weighted and connected-group-equal mean absolute contributions, local_explanation_examples.json for four fixed-ID Wedding/Corporate examples, and shap_overview.png for the top ten group-equal features per target. Compressed NPZ files contain every scenario's feature inputs, contributions, bias, raw margin and score. Load them with numpy.load(..., allow_pickle=False).

## Limitations

Explanations describe these fitted classifiers, not causal effects, verified financial rules or real market economics. Correlated simulator inputs (budget/reserve, guests/catering, quoted totals/components) can share or redistribute attribution. Changing one displayed feature alone may violate simulator accounting or geometry, so do not interpret SHAP as a feasible What-If intervention or optimizer. Zero real completed event-financial outcomes and 19 independently unvalidated formulas remain. The test set was previously inspected, so this is exploratory explanation, not a new unbiased performance experiment. Vendor_Cost_Anomaly remains a prior-only random-injection negative control; no SHAP-based anomaly-detection claim is made.

## Reproduce in Windows

From the project root, use a new run ID:

```powershell
./work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/explain_financial_risk.py --run-id financial_shap_v1_1_replay
```

Models and data are checksum-verified before use and unchanged afterward. explanation_protocol.json records method, runtime, source and code identity before calculation. checksums.sha256 binds saved explanation outputs. This script does not train, tune or calibrate models or modify the frozen dataset.

Method source: [XGBoost 3.0 Python API, Booster.predict](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html).
'''
    (report / 'README.md').write_text(readme, encoding='utf-8')
    files = list(output.iterdir()) + list(report.iterdir())
    (report / 'checksums.sha256').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(ROOT)).replace('\\', '/') + '\n'
                                          for p in sorted(files) if p.is_file()), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='financial_shap_v1_1_20261012')
    run(parser.parse_args().run_id)
