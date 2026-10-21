"""Fixed-protocol CPU GAT experiment. Input ZIP and inherited splits are immutable."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from component4.graph_experiment import load_graphs, fit_scaler, transform, overlap_masks, adjacency, make_model
from component4.release_input import assert_experiment_output, sha256
from component4.risk_experiment import metrics
from component4.risk_experiment import archive_inputs
from component4.split_derivative import validate_overlay, apply_overlay
from component4.graph_experiment import validate_graphs
import csv, io, zipfile


def write_json(path, value):
    assert_experiment_output(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def weights(groups):
    counts = Counter(groups)
    return np.array([len(groups) / (len(counts) * counts[k]) for k in groups])


def run(run_id, split_overlay=None):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    policy = ROOT / 'config/experiments/graph_risk.v0.1.json'
    plan = json.loads(policy.read_text())
    archive, release, a, schema, audit, hashes = load_graphs()
    overlay_receipt = None
    version = 'v1.0'
    if split_overlay:
        overlay_path = Path(split_overlay).resolve()
        overlay = json.loads(overlay_path.read_text())
        receipt = json.loads((ROOT / 'reports/dataset_quality_audit_20261012/split_derivative_validation.json').read_text())
        if sha256(overlay_path) != receipt['overlay_sha256'] or overlay['source_archive_sha256'] != sha256(archive):
            raise ValueError('overlay_checksum_mismatch')
        _, _, financial, spec, _, _ = archive_inputs()
        validate_overlay(financial, overlay)
        revised = {r['Scenario_ID']: r for r in apply_overlay(financial, overlay)}
        with zipfile.ZipFile(archive) as source:
            index = list(csv.DictReader(io.StringIO(source.read('prepared/spatial_financial_graphs/graph_index.csv').decode('utf-8-sig'))))
        for row in index:
            assignment = revised[row['graph_id']]
            if row['Base_Event_ID'] != assignment['Base_Event_ID']:
                raise ValueError('graph_family_mismatch')
            row['split'], row['split_group_id'] = assignment['split'], assignment['split_group_id']
        # New arrays prevent silent truncation of longer derivative group IDs.
        a['split'] = np.array([revised[s]['split'] for s in a['graph_id']], dtype=str)
        a['split_group_id'] = np.array([revised[s]['split_group_id'] for s in a['graph_id']], dtype=str)
        audit = validate_graphs(a, schema, index)
        overlay_receipt = {'path':str(overlay_path), 'sha256':sha256(overlay_path),
                           'assignment_sha256':overlay['assignment_sha256'],
                           'prior_test_exposure':'exploratory reanalysis of previously inspected scenarios'}
        version = 'v1.1'
    before = sha256(archive)
    original = ROOT / release['original_archive']['project_relative_path']
    if before != plan['release_sha256'] or sha256(original) != before:
        raise ValueError('release_mismatch')
    protected = {p: sha256(p) for p in archive.parent.iterdir() if p.is_file()}
    output = assert_experiment_output(ROOT / 'outputs/experiments' / version / run_id)
    report = assert_experiment_output(ROOT / 'reports/experiments' / version / run_id)
    if output.exists() or report.exists():
        raise ValueError('refuse_existing_experiment')
    clean = overlap_masks(a)
    split = {s: np.flatnonzero(a['split'] == s) for s in ('train', 'validation', 'test')}
    if any(not clean[s].any() for s in clean):
        raise ValueError('empty_nonoverlap_split')
    mean, scale = fit_scaler(a['x'][split['train']], a['feature_mask'][split['train']])
    x = torch.tensor(transform(a['x'], a['feature_mask'], mean, scale))
    y = torch.tensor(a['y'], dtype=torch.float32)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    write_json(output / 'experiment_protocol.json', {
        'plan': plan, 'policy_sha256': sha256(policy), 'release_sha256': before,
        'split_overlay': overlay_receipt,
        'input_sha256': hashes, 'audit': audit,
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in (Path(__file__), ROOT / 'component4/graph_experiment.py', ROOT / 'component4/risk_experiment.py')},
        'runtime': {'python': platform.python_version(), **{k: importlib.metadata.version(k) for k in ('torch', 'numpy', 'scikit-learn')}},
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'state': 'RECORDED_BEFORE_FIT',
        'nonoverlap_rows': {s: int(clean[s].sum()) for s in clean},
        'excluded_ids': {s: a['graph_id'][(a['split'] == s) & ~clean[s]].tolist() for s in clean}})
    np.savez_compressed(output / 'training_scaler.npz', mean=mean, scale=scale)
    training_weights = torch.tensor(weights(a['split_group_id'][split['train']]), dtype=torch.float32)
    val_ids = np.flatnonzero(clean['validation'])
    val_weights = weights(a['split_group_id'][val_ids])
    train_ids = split['train']
    fitted, validation, history, best_epochs = {}, {}, {}, {}
    for name in plan['candidate_models']:
        torch.manual_seed(plan['seed'])
        rng = np.random.default_rng(plan['seed'])
        mask = adjacency(a['edge_index'], x.shape[1], name, plan['seed'])
        model = make_model(x.shape[2], plan['hidden_features'], mask)
        optimizer = torch.optim.Adam(model.parameters(), lr=plan['learning_rate'])
        best, checkpoint, best_epoch = float('inf'), None, None
        log = []
        for epoch in range(1, plan['epochs'] + 1):
            model.train()
            order = rng.permutation(len(train_ids))
            for start in range(0, len(order), plan['batch_size']):
                local = order[start:start + plan['batch_size']]
                ids = train_ids[local]
                optimizer.zero_grad()
                loss_each = torch.nn.functional.binary_cross_entropy_with_logits(model(x[ids]), y[ids], reduction='none').mean(dim=1)
                loss = (loss_each * training_weights[local]).mean()
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                p = torch.sigmoid(model(x[val_ids])).numpy()
            score = float(np.mean([metrics(a['y'][val_ids, j], p[:, j], val_weights)['log_loss'] for j in (0, 1)]))
            log.append({'epoch': epoch, 'validation_group_equal_log_loss_first_two_targets': score})
            if score < best:
                best, checkpoint, best_epoch = score, copy.deepcopy(model.state_dict()), epoch
        model.load_state_dict(checkpoint)
        model.eval()
        torch.save(checkpoint, output / (name + '.pt'))
        restored = make_model(x.shape[2], plan['hidden_features'], mask)
        restored.load_state_dict(torch.load(output / (name + '.pt'), weights_only=True))
        restored.eval()
        with torch.no_grad():
            if not torch.equal(model(x[val_ids]), restored(x[val_ids])):
                raise ValueError('model_serialization_replay')
        fitted[name], validation[name], history[name], best_epochs[name] = model, best, log, best_epoch
        print('Fitted', name, 'best_epoch', best_epoch, 'validation_loss', best, flush=True)
    prior = np.average(a['y'][train_ids], axis=0, weights=training_weights.numpy())
    prior_val = np.tile(prior, (len(val_ids), 1))
    validation['dummy_prior'] = float(np.mean([metrics(a['y'][val_ids, j], prior_val[:, j], val_weights)['log_loss'] for j in (0, 1)]))
    chosen = min(validation, key=lambda k: (validation[k], k))
    selection = {'Budget_Overrun': chosen, 'Profit_Margin_Risk': chosen, 'Vendor_Cost_Anomaly': 'dummy_prior'}
    all_metrics, predictions = [], {}
    for name in [*fitted, 'dummy_prior']:
        ids = split['test']
        with torch.no_grad():
            p = torch.sigmoid(fitted[name](x[ids])).numpy() if name in fitted else np.tile(prior, (len(ids), 1))
        predictions[name] = p
        for population, keep in [('full_test', np.ones(len(ids), dtype=bool)), ('nonoverlap_test', clean['test'][ids])]:
            chosen_ids = ids[keep]
            for j, target in enumerate(plan['targets']):
                for weighting, w in [('row', None), ('group_equal', weights(a['split_group_id'][chosen_ids]))]:
                    all_metrics.append({'model': name, 'target': target, 'population': population, 'weighting': weighting,
                                        'rows': int(keep.sum()), **metrics(a['y'][chosen_ids, j], p[keep, j], w)})
    np.savez_compressed(output / 'heldout_predictions.npz', graph_id=a['graph_id'][split['test']],
                        split_group_id=a['split_group_id'][split['test']], targets=a['y'][split['test']],
                        nonoverlap_mask=clean['test'][split['test']], **predictions)
    write_json(output / 'model_metadata.json', {'selected': selection, 'prior': prior.tolist(), 'schema': schema,
               'best_epochs': best_epochs, 'parameters': plan, 'feature_encoding': '26 standardized values + 26 masks + 9 type indicators'})
    write_json(report / 'test_metrics.json', all_metrics)
    write_json(report / 'training_history.json', history)
    write_json(report / 'validation_selection.json', {'scores': validation, 'selected': selection})
    summary = {'status': 'PASS_EXPLORATORY_SYNTHETIC_GRAPH_EXPERIMENT', 'audit': audit,
               'split_overlay': overlay_receipt,
               'selected': selection, 'nonoverlap_rows': {s: int(clean[s].sum()) for s in clean},
               'serialization_replay': 'PASS', 'release_unchanged': True,
               'single_seed': True, 'unseen_template_evaluation': 'UNSUPPORTED',
               'attention_is_not_validated_causal_explanation': True}
    if any(sha256(p) != v for p, v in protected.items()) or sha256(original) != before:
        raise ValueError('immutable_input_changed')
    if overlay_receipt and sha256(overlay_path) != overlay_receipt['sha256']:
        raise ValueError('overlay_changed')
    write_json(report / 'experiment_summary.json', summary)
    requirements = '\n'.join(sorted(d.metadata['Name'] + '==' + d.version for d in importlib.metadata.distributions())) + '\n'
    (output / 'requirements.txt').write_text(requirements)
    lines = ['# Synthetic dependency graph experiment', '',
             'Single-seed exploratory classification of simulated outcomes, NOT real venue layouts, LKR budgets or real-world performance.', '',
             f'Inherited split counts: {audit["rows"]}. Group counts: {audit["groups"]}. Family counts: {audit["families"]}.',
             f'Validation choices: {selection}. Checkpoints selected on first-two-target group-equal validation log loss only.', '',
             '## Selected full-test results (row weighted)', '']
    for target, name in selection.items():
        result = next(r for r in all_metrics if r['target'] == target and r['model'] == name and r['population'] == 'full_test' and r['weighting'] == 'row')
        lines.append(f'- {target}: {name}; accuracy {result["accuracy"]:.4f}, balanced accuracy {result["balanced_accuracy"]:.4f}, ROC-AUC {result["roc_auc"]:.4f}, log loss {result["log_loss"]:.4f}.')
    lines += ['', '## Limitations', '',
              'One fixed assumed topology. Node quantities and planned charges already encode simulator arithmetic; results cannot establish spatial intelligence or graph benefit by themselves.',
              'Compare all dependency, self-only, shuffled-edge and prior results in test_metrics.json; no test tuning. Two GAT layers, one head, no dimensional edge coefficients consumed. Self-loops are computational only.',
              ('Frozen original splits remain unchanged; this run uses the checksum-bound v1.1 overlay in memory, identical to the financial-model grouping. Previously inspected test data mean exploratory reanalysis, not a pristine holdout.' if overlay_receipt else 'Original splits are unchanged. Exact input overlaps are excluded from validation selection and separately reported test sensitivity, not deleted from the dataset.'),
              'Vendor anomaly is random injection, with training prior selected as a negative control. No deployment calibration, confidence intervals, seed stability or unseen-template performance is established.',
              '19 formulas lack independent domain validation. Engineering waiver does not imply institutional approval. Attention weights are not SHAP or causal coefficients.', '',
              '## Reproduction (Windows PowerShell)', '', '```powershell',
              './work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/train_graph_risk.py --run-id graph_risk_replay_NEW' + (' --split-overlay data/experiments/v1.1/split_integrity_derivative/split_manifest.v1.1.json' if overlay_receipt else ''),
              '```', '', 'Use a new run ID; existing outputs cannot be overwritten. Same recorded CPU/runtime and seed required; cross-version bitwise reproducibility is not guaranteed.', '',
              'Methods: [GAT paper](https://arxiv.org/abs/1710.10903), [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html).']
    (report / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    files = sorted([p for folder in (output, report) for p in folder.iterdir() if p.is_file()])
    (report / 'checksums.sha256').write_text('\n'.join(sha256(p) + '  ' + p.relative_to(ROOT).as_posix() for p in files) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--split-overlay')
    args = parser.parse_args()
    run(args.run_id, args.split_overlay)
