"""Label-blind split overlay; preserves frozen scenario values and ancestry."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math

POLICY_VERSION = 'feature-projection-group-overlay.1.1'
SEED = 'component4-v1.1-overlap-repair-20261012'
PARTITIONS = ('train', 'validation', 'test')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def signature(row, predictors):
    try:
        values = tuple(float(row[k]) for k in predictors)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('missing_or_invalid_predictor') from exc
    if not all(math.isfinite(v) for v in values):
        raise ValueError('nonfinite_predictor')
    # Python considers -0.0 and 0.0 equal; hashes must use that same equivalence.
    return tuple(0.0 if v == 0 else v for v in values)


def create_overlay(rows, spec, ancestry):
    predictors = spec['predictors']
    forbidden = set(spec['targets']) | set(spec['metadata_not_predictors']) | set(spec['forbidden_inputs'])
    if not predictors or len(set(predictors)) != len(predictors) or set(predictors) & forbidden:
        raise ValueError('invalid_predictor_allowlist')
    ids = [r['Scenario_ID'] for r in rows]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('empty_or_duplicate_scenarios')
    if len(ancestry) != len(rows) or {r['Scenario_ID'] for r in ancestry} != set(ids):
        raise ValueError('ancestry_identity_mismatch')
    old = {r['Scenario_ID']: r for r in ancestry}
    parent = {sid: sid for sid in ids}

    def find(sid):
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    registries = [dict() for _ in range(4)]
    for r in sorted(rows, key=lambda r: r['Scenario_ID']):
        sid, prior = r['Scenario_ID'], old[r['Scenario_ID']]
        if r['split'] not in PARTITIONS or any(r[k] != prior[k] for k in ('Base_Event_ID', 'split', 'split_group_id', 'configuration_sha256')):
            raise ValueError('invalid_or_mismatched_source_assignment')
        keys = (r['Base_Event_ID'], r['split_group_id'], prior['planning_fingerprint'], signature(r, predictors))
        if any(not key for key in keys):
            raise ValueError('missing_ancestry')
        for registry, key in zip(registries, keys):
            if key in registry:
                union(sid, registry[key])
            else:
                registry[key] = sid
    components = defaultdict(list)
    for sid in ids:
        components[find(sid)].append(sid)
    by_id = {r['Scenario_ID']: r for r in rows}
    assignments = []
    for members in sorted(components.values(), key=lambda ms: min(ms)):
        members = sorted(members)
        group = 'V11-' + digest(members)
        votes = Counter(by_id[sid]['split'] for sid in members)
        # Minimal moved rows, never optimize using targets. Stable tie-break.
        partition = min(PARTITIONS, key=lambda p: (-votes[p], digest([SEED, group, p])))
        for sid in members:
            r, prior = by_id[sid], old[sid]
            assignments.append({'Scenario_ID': sid, 'Base_Event_ID': r['Base_Event_ID'],
                'planning_fingerprint': prior['planning_fingerprint'],
                'feature_signature_sha256': digest(signature(r, predictors)),
                'original_split_group_id': r['split_group_id'], 'original_split': r['split'],
                'split_group_id': group, 'split': partition,
                'configuration_sha256': r['configuration_sha256']})
    assignments.sort(key=lambda r: r['Scenario_ID'])
    overlay = {'version': POLICY_VERSION, 'deterministic_tie_break_seed': SEED,
               'predictors': list(predictors), 'policy': 'connected ancestry and feature projection; majority original split; target-blind',
               'evaluation_scope': 'in-simulator exploratory reanalysis, not unseen-template or external validation',
               'assignments': assignments}
    overlay['assignment_sha256'] = digest(assignments)
    validate_overlay(rows, overlay)
    return overlay


def apply_overlay(rows, overlay):
    assignments = overlay['assignments']
    lookup = {r['Scenario_ID']: r for r in assignments}
    if len(lookup) != len(assignments) or len(rows) != len(assignments) or set(lookup) != {r['Scenario_ID'] for r in rows}:
        raise ValueError('overlay_identity_mismatch')
    result = deepcopy(rows)
    for r in result:
        assignment = lookup[r['Scenario_ID']]
        if any(r[k] != assignment[k] for k in ('Base_Event_ID', 'configuration_sha256')) or r['split'] != assignment['original_split'] or r['split_group_id'] != assignment['original_split_group_id']:
            raise ValueError('overlay_source_mismatch')
        r['split'], r['split_group_id'] = assignment['split'], assignment['split_group_id']
    return result


def validate_overlay(rows, overlay):
    if digest(overlay['assignments']) != overlay['assignment_sha256']:
        raise ValueError('overlay_checksum_mismatch')
    result = apply_overlay(rows, overlay)
    registries = [defaultdict(set) for _ in range(5)]
    lookup = {r['Scenario_ID']: r for r in overlay['assignments']}
    for r in result:
        assignment = lookup[r['Scenario_ID']]
        if r['split'] not in PARTITIONS:
            raise ValueError('invalid_partition')
        key = signature(r, overlay['predictors'])
        if digest(key) != assignment['feature_signature_sha256']:
            raise ValueError('feature_signature_mismatch')
        for registry, identity in zip(registries, (r['Base_Event_ID'], assignment['original_split_group_id'], assignment['planning_fingerprint'], key, r['split_group_id'])):
            registry[identity].add(r['split'])
    if any(len(parts) > 1 for registry in registries for parts in registry.values()):
        raise ValueError('cross_split_dependency')
    if {r['split'] for r in result} != set(PARTITIONS):
        raise ValueError('missing_partition')
    return {'status': 'PASS', 'rows': len(result),
            'split_rows': dict(Counter(r['split'] for r in result)),
            'split_groups': dict(Counter(next(iter(parts)) for parts in registries[-1].values())),
            'split_families': dict(Counter(next(iter(parts)) for parts in registries[0].values())),
            'moved_rows': sum(r['split'] != lookup[r['Scenario_ID']]['original_split'] for r in result),
            'cross_split_feature_vectors': 0, 'cross_split_dependency_groups': 0,
            'scenario_values_changed': False}
