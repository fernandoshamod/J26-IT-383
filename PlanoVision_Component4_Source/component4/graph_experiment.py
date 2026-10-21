"""Immutable synthetic graph experiment helpers; no dataset mutation."""
from collections import Counter
import csv
import hashlib
import io
import json
import zipfile
import numpy as np
from .release_input import verified_release


def validate_graphs(a, schema, rows):
    n = len(a['graph_id'])
    nodes, features = len(schema['node_types']), len(schema['feature_names'])
    if a['x'].shape != (n, nodes, features) or a['feature_mask'].shape != a['x'].shape:
        raise ValueError('invalid_feature_shape')
    if len(set(a['graph_id'])) != n or len(rows) != n:
        raise ValueError('duplicate_or_missing_graph_id')
    if a['y'].shape != (n, 3) or a['label_mask'].shape != (n, 3) or not a['label_mask'].all() or not np.isin(a['y'], [0, 1]).all():
        raise ValueError('invalid_labels')
    if not np.isfinite(a['x'][a['feature_mask']]).all() or not np.isnan(a['x'][~a['feature_mask']]).all():
        raise ValueError('invalid_feature_mask')
    edge = a['edge_index']
    expected = np.array([[r[0], r[1]] for r in schema['edge_rules']]).T
    if edge.shape != expected.shape or not np.array_equal(edge, expected):
        raise ValueError('edge_rule_mismatch')
    if not np.array_equal(a['node_type_index'], np.arange(nodes)):
        raise ValueError('node_type_mismatch')
    registries = [{}, {}]
    for i, row in enumerate(rows):
        if row['graph_id'] != a['graph_id'][i] or row['split'] != a['split'][i] or row['split_group_id'] != a['split_group_id'][i]:
            raise ValueError('graph_index_alignment')
        if row['Record_Kind'] != 'synthetic_event_financial' or row['layout_origin'] != 'synthetic_assumption':
            raise ValueError('synthetic_origin_required')
        if row['split'] not in ('train', 'validation', 'test'):
            raise ValueError('invalid_split')
        for field, registry in zip(('Base_Event_ID', 'split_group_id'), registries):
            key = row[field]
            if not key or (key in registry and registry[key] != row['split']):
                raise ValueError('ancestry_crosses_split')
            registry[key] = row['split']
    return {'rows': dict(Counter(a['split'])), 'families': dict(Counter(registries[0].values())),
            'groups': dict(Counter(registries[1].values())), 'topologies': 1}


def load_graphs():
    archive, release = verified_release()
    prefix = 'prepared/spatial_financial_graphs/'
    names = [prefix + p for p in ('graphs.npz', 'schema.json', 'graph_index.csv')]
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('package_manifest.json'))
        payloads = {k: z.read(k) for k in names}
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in payloads.items()}
    if any(manifest['files'][k] != v for k, v in hashes.items()):
        raise ValueError('input_member_checksum')
    with np.load(io.BytesIO(payloads[names[0]]), allow_pickle=False) as data:
        a = {k: data[k].copy() for k in data.files}
    schema = json.loads(payloads[names[1]])
    rows = list(csv.DictReader(io.StringIO(payloads[names[2]].decode('utf-8-sig'))))
    audit = validate_graphs(a, schema, rows)
    if audit['rows'] != release['record_counts']['split_rows']:
        raise ValueError('release_scope_changed')
    return archive, release, a, schema, audit, hashes


def fit_scaler(x, mask):
    counts = mask.sum(axis=0)
    mean = np.divide(np.where(mask, x, 0).sum(axis=0), counts, out=np.zeros(counts.shape), where=counts > 0)
    variance = np.divide(np.where(mask, (x - mean) ** 2, 0).sum(axis=0), counts,
                         out=np.zeros(counts.shape), where=counts > 0)
    scale = np.sqrt(variance)
    scale[scale < 1e-12] = 1
    return mean, scale


def transform(x, mask, mean, scale):
    numeric = np.where(mask, (x - mean) / scale, 0)
    if not np.isfinite(numeric).all():
        raise ValueError('nonfinite_transformed_input')
    types = np.broadcast_to(np.eye(x.shape[1]), (len(x), x.shape[1], x.shape[1]))
    return np.concatenate([numeric, mask.astype(float), types], axis=2).astype(np.float32)


def overlap_masks(a):
    keys = [hashlib.sha256(np.where(m, x, 0).astype('<f8').tobytes() + m.tobytes()).hexdigest()
            for x, m in zip(a['x'], a['feature_mask'])]
    train = {k for k, s in zip(keys, a['split']) if s == 'train'}
    validation = {k for k, s in zip(keys, a['split']) if s == 'validation'}
    return {s: np.array([split == s and k not in excluded for k, split in zip(keys, a['split'])])
            for s, excluded in [('train', set()), ('validation', train), ('test', train | validation)]}


def adjacency(edge, nodes, mode, seed):
    if edge.ndim != 2 or edge.shape[0] != 2 or not np.isin(edge, np.arange(nodes)).all():
        raise ValueError('invalid_edge_index')
    result = np.eye(nodes, dtype=bool)
    if mode not in ('gat_dependencies', 'gat_self_only', 'gat_shuffled_dependencies'):
        raise ValueError('invalid_model')
    if mode == 'gat_shuffled_dependencies':
        edge = np.random.default_rng(seed).permutation(nodes)[edge]
    if mode != 'gat_self_only':
        result[edge[1], edge[0]] = True  # rows are receivers; columns are senders
    return result


def make_model(input_features, hidden, adjacency_mask):
    import torch
    from torch import nn

    class Attention(nn.Module):
        def __init__(self, size):
            super().__init__()
            self.projection = nn.Linear(size, hidden, bias=False)
            self.sender = nn.Parameter(torch.randn(hidden) * 0.1)
            self.receiver = nn.Parameter(torch.randn(hidden) * 0.1)
            self.register_buffer('allowed', torch.tensor(adjacency_mask, dtype=torch.bool))

        def forward(self, x):
            h = self.projection(x)
            e = torch.nn.functional.leaky_relu((h @ self.receiver).unsqueeze(2) + (h @ self.sender).unsqueeze(1), 0.2)
            weights = torch.softmax(e.masked_fill(~self.allowed, float('-inf')), dim=2)
            return torch.nn.functional.elu(weights @ h)

    class GraphClassifier(nn.Module):
        def __init__(self):
            super().__init__()
            self.first = Attention(input_features)
            self.second = Attention(hidden)
            self.readout = nn.Linear(hidden, 3)

        def forward(self, x):
            return self.readout(self.second(self.first(x)).mean(dim=1))

    return GraphClassifier()
