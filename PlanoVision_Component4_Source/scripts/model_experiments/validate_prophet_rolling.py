"""Fixed, training-only expanding-origin robustness check; never uses test labels."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import logging
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['MPLCONFIGDIR'] = str(ROOT / 'work/prophet_matplotlib_cache')
import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json
from component4.historical_forecasting import audit_series, expanding_validation_windows, baseline_predictions, forecast_metrics
from component4.release_input import verified_release, sha256, assert_experiment_output


def run(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    archive, release = verified_release()
    original = ROOT / release['original_archive']['project_relative_path']
    protected = [original] + [p for p in archive.parent.iterdir() if p.is_file()]
    before = {str(p.relative_to(ROOT)): sha256(p) for p in protected}
    policy = ROOT / 'config/experiments/prophet_historical.v0.1.json'
    plan = json.loads(policy.read_text())
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('package_manifest.json'))
        names = ['prepared/prophet/prophet_cost_timeseries.csv', 'prepared/prophet/chronological_split_manifest.csv']
        payloads = {name: z.read(name) for name in names}
    for name, data in payloads.items():
        if hashlib.sha256(data).hexdigest() != manifest['files'][name]:
            raise ValueError('historical_input_checksum_mismatch')
    tables = [list(csv.DictReader(io.StringIO(payloads[name].decode('utf-8-sig')))) for name in names]
    groups, audit = audit_series(*tables)
    windows = {sid: expanding_validation_windows(data) for sid, data in groups.items()}
    output = assert_experiment_output(ROOT / 'outputs/experiments/v1.1' / run_id)
    report = assert_experiment_output(ROOT / 'reports/experiments/v1.1' / run_id)
    if output.exists() or report.exists():
        raise ValueError('refuse_existing_run')
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    protocol = {'recorded_before_fit_utc': datetime.now(timezone.utc).isoformat(), 'input_checksums': before,
        'policy_sha256': sha256(policy), 'historical_member_checksums': {n: manifest['files'][n] for n in names},
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in (Path(__file__), ROOT / 'component4/historical_forecasting.py')},
        'folds_per_series': 3, 'horizon_months': 3, 'minimum_training_months': 24,
        'window_origins': {sid: [t[-1]['ds'] for t, e in w] for sid, w in windows.items()},
        'methods': ['prophet', 'last_value', 'seasonal_naive_12'], 'parameters': plan['prophet_parameters'],
        'selection': 'none; prior fixed-origin selection remains unchanged; robustness only',
        'test_records_used': 0, 'publication_time_validation': False,
        'runtime': {name: importlib.metadata.version(name) for name in ('prophet','cmdstanpy','numpy','pandas')}}
    (output / 'protocol.json').write_text(json.dumps(protocol, indent=2))
    logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
    metrics, predictions = [], []
    replay_checks = 0
    for sid, folds in sorted(windows.items()):
        for fold, (training, evaluation) in enumerate(folds, 1):
            frame = pd.DataFrame({'ds': pd.to_datetime([r['ds'] for r in training]), 'y': [float(r['y']) for r in training]})
            dates = pd.DataFrame({'ds': pd.to_datetime([r['ds'] for r in evaluation])})
            model = Prophet(**plan['prophet_parameters'])
            model.fit(frame, seed=plan['random_seed'])
            predicted = model.predict(dates)['yhat'].to_numpy()
            serialized = model_to_json(model)
            stem = hashlib.sha256(sid.encode()).hexdigest()[:12] + '_fold' + str(fold)
            (output / (stem + '.prophet.json')).write_text(serialized, encoding='utf-8')
            if not np.allclose(model_from_json(serialized).predict(dates)['yhat'], predicted, rtol=1e-10, atol=1e-10):
                raise ValueError('serialization_replay_failed')
            replay_checks += 1
            methods = {'prophet': predicted.tolist(), **{name: baseline_predictions(training, [r['ds'] for r in evaluation], name)
                       for name in ('last_value', 'seasonal_naive_12')}}
            for method, values in methods.items():
                scores = forecast_metrics([r['y'] for r in evaluation], values, [r['y'] for r in training])
                metrics.append({'series_id': sid, 'unit': training[0]['unit'], 'fold': fold,
                    'training_count': len(training), 'forecast_origin': training[-1]['ds'], 'method': method,
                    'evaluation_start': evaluation[0]['ds'], 'evaluation_end': evaluation[-1]['ds'],
                    'flagged_evaluation_rows': sum(r['source_quality_review'] == '1' for r in evaluation), **scores})
                predictions.extend({'series_id': sid, 'fold': fold, 'method': method, 'observation_id': r['observation_id'],
                    'ds': r['ds'], 'unit': r['unit'], 'original_partition': r['partition'], 'forecast_origin': training[-1]['ds'],
                    'observed_y': float(r['y']), 'forecast_yhat': float(value), 'quality_flag': r['quality_flag']}
                    for r, value in zip(evaluation, values))
            print('Validated', sid, 'fold', fold, flush=True)
    summary_rows = []
    for sid in sorted(groups):
        for method in protocol['methods']:
            scores = [r for r in metrics if r['series_id'] == sid and r['method'] == method]
            summary_rows.append({'series_id': sid, 'unit': groups[sid][0]['unit'], 'method': method,
                                 'mean_fold_mae': sum(r['mae'] for r in scores)/len(scores),
                                 'nonpositive_predictions': sum(r['nonpositive_prediction_count'] for r in scores)})
    if len(metrics) != 108 or len(predictions) != 324 or any(r['original_partition'] == 'test' for r in predictions):
        raise ValueError('rolling_scope_or_leakage_failure')
    (report / 'fold_metrics.json').write_text(json.dumps(metrics, indent=2, allow_nan=False))
    (report / 'per_series_summary.json').write_text(json.dumps(summary_rows, indent=2, allow_nan=False))
    (output / 'rolling_forecasts.json').write_text(json.dumps(predictions, indent=2, allow_nan=False))
    saved = json.loads((output / 'rolling_forecasts.json').read_text())
    if saved != predictions or len({(r['observation_id'],r['fold'],r['method'],r['series_id']) for r in saved}) != 324:
        raise ValueError('saved_export_reconciliation_failed')
    original_values = {r['observation_id']: float(r['y']) for r in tables[0]}
    if any(original_values[r['observation_id']] != r['observed_y'] for r in saved):
        raise ValueError('historical_values_changed')
    if before != {str(p.relative_to(ROOT)): sha256(p) for p in protected}:
        raise ValueError('frozen_release_changed')
    result = {'status': 'PASS_RETROSPECTIVE_ROLLING_ROBUSTNESS', 'series': len(groups), 'fitted_models': replay_checks,
              'forecasts': len(predictions), 'fold_metrics': len(metrics), 'test_records_used': 0,
              'frozen_inputs_unchanged': True, 'serialization_replay': 'PASS',
              'parameter_tuning': False, 'previous_model_selection_changed': False,
              'empirical_event_cost_validity': False}
    (report / 'verification.json').write_text(json.dumps(result, indent=2))
    (report / 'README.md').write_text('''# Prophet chronological robustness completion

Twelve separate observed price/index series were tested at three expanding origins with three-month horizons. Each fit uses only original training records available before its origin. Evaluation uses later original training or validation observations, never original test rows. The 36 Prophet fits reuse unchanged fixed parameters; last-value and seasonal-naive baselines use the same cutoffs. No tuning, new method selection or rewriting of prior fixed-origin test results occurred.

Per-series errors retain original units. Do not average raw errors across incompatible series. Dates are month-period keys, not verified publication availability dates. All source quality flags are retained, not certified or silently removed. This is retrospective robustness, not live-vintage forecasting or observed complete event-budget prediction. The old fixed-origin selection and deployment limitations remain. Flags and negative forecasts are reported rather than artificially improved.

protocol.json records cutoffs and runtime before fitting; fold_metrics.json and per_series_summary.json document outcomes; rolling_forecasts.json preserves IDs and units. All 36 serialization replays and saved-export checks passed; frozen inputs remain unchanged. Use a new run ID:

```powershell
./work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/validate_prophet_rolling.py --run-id prophet_rolling_replay_NEW
```
''', encoding='utf-8')
    (report / 'checksums.sha256').write_text(''.join(sha256(p)+'  '+p.relative_to(ROOT).as_posix()+'\n'
        for p in sorted(list(output.iterdir()) + list(report.iterdir())) if p.is_file()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='prophet_rolling_v1_1_20261012')
    run(parser.parse_args().run_id)
