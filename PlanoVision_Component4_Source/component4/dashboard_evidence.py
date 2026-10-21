"""Read-only, checksum-pinned presentation of existing frozen diagnostics. No fitting."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = 'reports/diagnostics/v3_1_steps1_2_20261016/'
ROBUSTNESS = 'reports/robustness/v3_1_frozen_robustness_20261016/'
FILES = {
    'errors': (DIAGNOSTICS+'error_audit.json', 'b5fb0cf8ef574c42c91b4a15f7edda39d89f5598dd0992bf6f62af3d3b0b4fb3'),
    'curves': (DIAGNOSTICS+'learning_curve_summary.json', 'c3f5df58bdf93dc8dbeaaedbb0345e6fdf2641503973ec1214337cb808a2d825'),
    'robustness': (ROBUSTNESS+'performance_summary.json', '00f4745339e790387602864b0158ad3bf2e65e696c796d2f327677cb4d27e055'),
    'learning-curves.png': (DIAGNOSTICS+'learning_curves.png', '0fd3d3c0a352a0198418552c98a98f2028568ba8857a9a9383ce765c47549868'),
    'error-concentration.png': (DIAGNOSTICS+'error_concentration.png', '902c971d1ad4875e944e83a0cd2585f4a42c275660e9f0685c50c3d4a7653f84'),
    'regime-performance.png': (ROBUSTNESS+'regime_performance.png', '3ba2a82c357f6d363b9a1a152ee49b0f59977ef7186823502f409c372133d2a9'),
}


def verified_bytes(key, root=ROOT):
    path, expected = FILES[key]
    content = (root/path).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError('frozen_evidence_checksum_mismatch')
    return content


def evidence_summary(root=ROOT):
    errors, curves, robustness = [json.loads(verified_bytes(k, root)) for k in ('errors', 'curves', 'robustness')]
    return {
        'version': 'v3.1-frozen-diagnostics',
        'model_run': 'expense_risk_v3_1_20261016',
        'sources': {k: {'path': v[0], 'sha256': v[1]} for k, v in FILES.items()},
        'errors': {target: {'counts': value['test']['counts'],
                            'near_boundary': value['test']['errors_near_boundary'],
                            'paired_conflicts': value['test']['paired_label_ambiguity']['conflicting_label_vectors']}
                   for target, value in errors['strata_and_counts'].items()},
        'curves': {target: [{'families': row['training_families'],
                            'train_accuracy': row['train_accuracy']['mean'],
                            'validation_accuracy': row['validation_accuracy']['mean'],
                            'validation_log_loss': row['validation_log_loss']['mean']}
                           for row in settings['current_selected']]
                   for target, settings in curves['curves'].items()},
        'robustness': {regime: {target: {'cases': v['matched_model_supported_cases']['cases'],
                                         'metrics': v['matched_model_supported_cases']['metrics']['frozen_xgboost']}
                               for target, v in targets.items()}
                       for regime, targets in robustness['pooled'].items()},
    }
