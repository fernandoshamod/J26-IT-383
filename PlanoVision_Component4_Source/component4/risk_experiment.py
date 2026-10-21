"""First immutable-input risk-classification experiment; no scenario generation."""
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

from .release_input import verified_release, assert_experiment_output


def validate_rows(rows, spec):
    predictors, targets = spec['predictors'], spec['targets']
    if len(set(predictors)) != len(predictors) or set(predictors) & (set(targets) | set(spec['metadata_not_predictors']) | set(spec['forbidden_inputs'])):
        raise ValueError('forbidden_or_duplicate_predictor')
    identities, groups, families, fingerprints = set(), {}, {}, {}
    for row in rows:
        sid, split = row['Scenario_ID'], row['split']
        if sid in identities or split not in ('train', 'validation', 'test'):
            raise ValueError('duplicate_id_or_invalid_split')
        identities.add(sid)
        for column, registry in (('split_group_id', groups), ('Base_Event_ID', families)):
            key = row[column]
            if not key or (key in registry and registry[key] != split):
                raise ValueError('ancestry_crosses_split')
            registry[key] = split
        values = tuple(float(row[k]) for k in predictors)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('missing_or_nonfinite_predictor')
        fingerprints.setdefault(values, set()).add(split)
        if any(row[k] not in ('0', '1') for k in targets):
            raise ValueError('invalid_binary_target')
    if set(groups.values()) != {'train', 'validation', 'test'}:
        raise ValueError('missing_partition')
    return {'row_counts': dict(Counter(r['split'] for r in rows)),
            'group_counts': dict(Counter(groups.values())), 'family_counts': dict(Counter(families.values())),
            'feature_vector_count': len(fingerprints),
            'cross_split_feature_projection_keys': sum(len(v) > 1 for v in fingerprints.values()),
            'cross_split_feature_projection_rows': sum(len(fingerprints[tuple(float(r[k]) for k in predictors)]) > 1 for r in rows),
            'status': 'PASS_WITH_FEATURE_PROJECTION_OVERLAP' if any(len(v) > 1 for v in fingerprints.values()) else 'PASS'}


def nonoverlap_rows(partitions, predictors):
    def key(row):
        return tuple(float(row[k]) for k in predictors)
    train = {key(r) for r in partitions['train']}
    validation = {key(r) for r in partitions['validation']}
    return {
        'validation': [r for r in partitions['validation'] if key(r) not in train],
        'test': [r for r in partitions['test'] if key(r) not in train | validation],
    }


def group_weights(rows):
    counts = Counter(r['split_group_id'] for r in rows)
    return [len(rows) / (len(counts) * counts[r['split_group_id']]) for r in rows]


def select_model(scores, target):
    if target == 'Vendor_Cost_Anomaly':
        return 'dummy_prior'
    return min(scores, key=lambda name: (scores[name], name))


def metrics(y, probability, weights=None):
    import numpy as np
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
        recall_score, f1_score, roc_auc_score, average_precision_score, log_loss,
        brier_score_loss, confusion_matrix)
    p = np.asarray(probability, dtype=float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('invalid_probability')
    predicted = (p >= 0.5).astype(int)
    result = {
        'accuracy': accuracy_score(y, predicted, sample_weight=weights),
        'balanced_accuracy': balanced_accuracy_score(y, predicted, sample_weight=weights),
        'precision': precision_score(y, predicted, sample_weight=weights, zero_division=0),
        'recall': recall_score(y, predicted, sample_weight=weights, zero_division=0),
        'f1': f1_score(y, predicted, sample_weight=weights, zero_division=0),
        'roc_auc': roc_auc_score(y, p, sample_weight=weights) if len(set(y)) == 2 else None,
        'average_precision': average_precision_score(y, p, sample_weight=weights) if len(set(y)) == 2 else None,
        'log_loss': log_loss(y, p, labels=[0, 1], sample_weight=weights),
        'brier_score': brier_score_loss(y, p, sample_weight=weights),
    }
    for key, value in zip(('tn', 'fp', 'fn', 'tp'), confusion_matrix(y, predicted, labels=[0, 1], sample_weight=weights).ravel()):
        result[key] = float(value)
    return {k: float(v) if v is not None else None for k, v in result.items()}


def archive_inputs():
    archive, release = verified_release()
    with zipfile.ZipFile(archive, 'r') as package:
        manifest = json.loads(package.read('package_manifest.json'))
        names = ('prepared/xgboost/xgboost_risk_dataset.csv', 'prepared/xgboost/feature_specification.json', 'prepared/xgboost/grouped_split_manifest.csv')
        payloads = {name: package.read(name) for name in names}
        for name, payload in payloads.items():
            if hashlib.sha256(payload).hexdigest() != manifest['files'][name]:
                raise ValueError('archived_input_checksum:' + name)
        rows = list(csv.DictReader(io.StringIO(payloads[names[0]].decode('utf-8-sig'))))
        spec = json.loads(payloads[names[1]])
        assignments = {r['Scenario_ID']: r for r in csv.DictReader(io.StringIO(payloads[names[2]].decode('utf-8-sig')))}
    audit = validate_rows(rows, spec)
    for row in rows:
        assignment = assignments[row['Scenario_ID']]
        if any(row[k] != assignment[k] for k in ('Base_Event_ID', 'split', 'split_group_id', 'configuration_sha256')):
            raise ValueError('split_assignment_changed')
    if audit['row_counts'] != release['record_counts']['split_rows'] or len(rows) != 7500:
        raise ValueError('frozen_scope_changed')
    return archive, release, rows, spec, audit, {name: manifest['files'][name] for name in names}


def write_table(path, rows, fields=None):
    path = assert_experiment_output(path)
    with path.open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
