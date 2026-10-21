"""Independent read-only reconciliation of saved risk-experiment exports."""
import argparse
import csv
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.release_input import verified_release, sha256
from component4.split_derivative import apply_overlay, validate_overlay


def verify(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    report = ROOT / 'reports/experiments/v1.1' / run_id
    summary = json.loads((report / 'experiment_summary.json').read_text())
    model_dir = ROOT / 'outputs/experiments/v1.1' / run_id
    archive, release = verified_release()
    protocol = json.loads((model_dir / 'experiment_protocol.json').read_text())
    overlay_path = Path(summary['split_overlay']['path'])
    if sha256(overlay_path) != summary['split_overlay']['sha256']:
        raise ValueError('overlay_changed')
    for line in (report / 'checksums.sha256').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT) or sha256(target) != checksum:
            raise ValueError('output_checksum_mismatch:' + name)
    if sha256(archive) != protocol['archive_sha256']:
        raise ValueError('archive_changed')
    with zipfile.ZipFile(archive) as source:
        rows = list(csv.DictReader(io.StringIO(source.read('prepared/xgboost/xgboost_risk_dataset.csv').decode('utf-8-sig'))))
    overlay = json.loads(overlay_path.read_text())
    validate_overlay(rows, overlay)
    rows = apply_overlay(rows, overlay)
    by_id = {r['Scenario_ID']: r for r in rows}
    targets = set(summary['selected_models'])
    expected = {(r['Scenario_ID'], t) for r in rows if r['split'] in ('validation', 'test') for t in targets}
    with (model_dir / 'selected_predictions.csv').open(newline='', encoding='utf-8') as stream:
        predictions = list(csv.DictReader(stream))
    observed = {(r['Scenario_ID'], r['target']) for r in predictions}
    if len(observed) != len(predictions) or observed != expected:
        raise ValueError('prediction_ids_missing_or_duplicate')
    for prediction in predictions:
        r, target = by_id[prediction['Scenario_ID']], prediction['target']
        if any(prediction[k] != r[k] for k in ('Base_Event_ID', 'split_group_id', 'split')) or prediction['simulated_target'] != r[target]:
            raise ValueError('prediction_label_or_assignment_mismatch')
        p = float(prediction['model_score_uncalibrated'])
        if not 0 <= p <= 1 or int(prediction['predicted_label_threshold_0_5']) != int(p >= .5):
            raise ValueError('invalid_prediction_score_or_threshold')
    for metric in summary['selected_test_metrics']:
        selected = [r for r in predictions if r['target'] == metric['target'] and r['split'] == 'test']
        accuracy = sum(r['simulated_target'] == r['predicted_label_threshold_0_5'] for r in selected) / len(selected)
        if abs(accuracy - metric['accuracy']) > 1e-12:
            raise ValueError('accuracy_export_mismatch')
    original = ROOT / release['original_archive']['project_relative_path']
    if sha256(original) != release['original_archive']['sha256']:
        raise ValueError('original_archive_changed')
    print(json.dumps({'status': 'PASS', 'saved_output_checksums': 'PASS',
                      'prediction_identity_labels_and_overlay': 'PASS',
                      'prediction_rows': len(predictions), 'test_accuracy_reconciliation': 'PASS',
                      'original_and_release_checksums': 'PASS', 'real_world_validity_established': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    verify(parser.parse_args().run_id)
