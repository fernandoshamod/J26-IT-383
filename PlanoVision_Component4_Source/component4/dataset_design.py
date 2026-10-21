"""Metadata-only grouping and generation-plan validation. No financial row generator."""
import hashlib
import math
from .engine import fingerprint

VERSION = 'dataset-design.0.1-proposed'
SPLITS = ('train', 'validation', 'test')
PROTOCOLS = ('conditional_in_simulator', 'unseen_templates')
ANCESTRY = ('venue_template_id', 'vendor_template_id', 'source_dependency_ids')


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError('missing_or_invalid:' + field)


def _validate(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty_metadata_rows_required')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('metadata_object_required')
        for key in ('scenario_id', 'family_id', 'planning_fingerprint', 'venue_template_id', 'vendor_template_id'):
            _text(row.get(key), key)
        deps = row.get('source_dependency_ids')
        if not isinstance(deps, list) or not deps or any(not isinstance(x, str) or not x.strip() for x in deps):
            raise ValueError('source_dependency_ids_required')
        if len(deps) != len(set(deps)):
            raise ValueError('duplicate_source_dependency')
        if row['scenario_id'] in seen:
            raise ValueError('duplicate_scenario_id')
        seen.add(row['scenario_id'])


def split_components(rows, protocol):
    """Conditional groups families/duplicate planning states; strict also joins sources transitively."""
    _validate(rows)
    if protocol not in PROTOCOLS:
        raise ValueError('unsupported_split_protocol')
    parents = {r['family_id']: r['family_id'] for r in rows}

    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def union(a, b):
        a, b = sorted((find(a), find(b)))
        parents[b] = a

    owner = {}
    for row in sorted(rows, key=lambda r: r['scenario_id']):
        keys = [('planning', row['planning_fingerprint'])]
        if protocol == 'unseen_templates':
            keys += [('venue', row['venue_template_id']), ('vendor', row['vendor_template_id'])]
            keys += [('source', x) for x in row['source_dependency_ids']]
        for key in keys:
            if key in owner:
                union(row['family_id'], owner[key])
            owner[key] = row['family_id']
    groups = {}
    for family in sorted(parents):
        groups.setdefault(find(family), []).append(family)
    return {family: 'G-' + fingerprint({'protocol': protocol, 'families': members})
            for members in groups.values() for family in members}


def assign_groups(rows, protocol, seed, fractions=(.7, .15, .15), tolerance=.05):
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('nonnegative_integer_split_seed_required')
    if (len(fractions) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float))
        or not math.isfinite(x) or not 0 < x < 1 for x in fractions) or abs(sum(fractions) - 1) > 1e-12):
        raise ValueError('invalid_split_fractions')
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or not 0 <= tolerance <= 1:
        raise ValueError('invalid_split_tolerance')
    family_groups = split_components(rows, protocol)
    sizes = {}
    for row in rows:
        group = family_groups[row['family_id']]
        sizes[group] = sizes.get(group, 0) + 1
    if len(sizes) < 3:
        raise ValueError('insufficient_indivisible_groups_for_three_splits')
    order = sorted(sizes, key=lambda g: (-sizes[g], hashlib.sha256(
        f'bulk-split-v0.1|{seed}|{g}'.encode('utf-8')).hexdigest()))
    totals = [0, 0, 0]
    assignments = {}
    for index, group in enumerate(order):
        selected = index if index < 3 else max(range(3), key=lambda j: (len(rows) * fractions[j] - totals[j], -j))
        assignments[group] = SPLITS[selected]
        totals[selected] += sizes[group]
    if any(abs(totals[i] / len(rows) - fractions[i]) > tolerance + 1e-12 for i in range(3)):
        raise ValueError('split_fraction_tolerance_failed_do_not_divide_groups')
    return {r['scenario_id']: assignments[family_groups[r['family_id']]] for r in rows}


def audit_split_leakage(rows, assignments, protocol):
    """Machine-readable independent overlap audit; does not claim source holdout in conditional mode."""
    _validate(rows)
    groups = split_components(rows, protocol)
    if not isinstance(assignments, dict) or set(assignments) != {r['scenario_id'] for r in rows}:
        raise ValueError('split_map_scope_mismatch')
    if any(s not in SPLITS for s in assignments.values()):
        raise ValueError('unknown_split')
    overlaps = {}
    for key, getter in (
        ('family', lambda r: [r['family_id']]),
        ('planning_fingerprint', lambda r: [r['planning_fingerprint']]),
        ('component', lambda r: [groups[r['family_id']]]),
        ('venue_template', lambda r: [r['venue_template_id']]),
        ('vendor_template', lambda r: [r['vendor_template_id']]),
        ('source_dependency', lambda r: r['source_dependency_ids'])):
        use = {}
        for row in rows:
            for value in getter(row):
                use.setdefault(value, set()).add(assignments[row['scenario_id']])
        overlaps[key] = sorted(v for v, partitions in use.items() if len(partitions) > 1)
    prohibited = ('family', 'planning_fingerprint', 'component') if protocol == 'conditional_in_simulator' else tuple(overlaps)
    violations = {k: overlaps[k] for k in prohibited if overlaps[k]}
    empty = [s for s in SPLITS if s not in assignments.values()]
    return {'audit_version': VERSION, 'protocol': protocol, 'status': 'FAIL' if violations or empty else 'PASS',
            'record_count': len(rows), 'group_count': len(set(groups.values())), 'empty_splits': empty,
            'violations': violations, 'shared_source_overlap': {k: overlaps[k] for k in ('venue_template', 'vendor_template', 'source_dependency')},
            'unseen_venue_claim_supported_by_protocol': protocol == 'unseen_templates',
            'financial_realism_validated': False}


def validate_expansion_plan(plan):
    """Strict counts/units/scope only; no authority inferred from a valid plan."""
    fields = ('root_count', 'planning_states_per_root', 'outcome_replications_per_state', 'target_rows')
    if not isinstance(plan, dict):
        raise ValueError('plan_object_required')
    for key in fields:
        v = plan.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError('positive_integer_required:' + key)
    if plan['root_count'] * plan['planning_states_per_root'] * plan['outcome_replications_per_state'] != plan['target_rows']:
        raise ValueError('root_variant_replication_count_mismatch')
    quotas = plan.get('archetype_root_quotas')
    if not isinstance(quotas, dict) or set(quotas) != {'Wedding', 'Corporate'}:
        raise ValueError('wedding_corporate_quotas_required')
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in quotas.values()) or sum(quotas.values()) != plan['root_count']:
        raise ValueError('archetype_quota_mismatch')
    if plan.get('split_protocol') not in PROTOCOLS:
        raise ValueError('explicit_split_protocol_required')
    return True


def bulk_validation_blockers(plan, evidence):
    """Additional fail-closed bulk checks, NOT a writer or replacement for existing pilot gates."""
    reasons = []
    try:
        validate_expansion_plan(plan)
    except (ValueError, TypeError) as exc:
        reasons.append(str(exc))
    if not isinstance(plan, dict):
        return reasons + ['plan_object_required']
    if not isinstance(evidence, dict):
        return reasons + ['bulk_evidence_object_required']
    for key in ('pilot_validated_pass', 'formula_reviews_complete', 'parameter_reviews_complete',
                'expanded_generator_verified', 'split_protocol_reviewed', 'criteria_reviewed', 'explicit_bulk_authorization'):
        if evidence.get(key) is not True:
            reasons.append('missing:' + key)
    for key in ('frozen_simulator_sha256', 'code_sha256', 'source_manifest_sha256', 'authorization_payload_sha256'):
        v = evidence.get(key)
        if not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
            reasons.append('missing_or_invalid:' + key)
    if (evidence.get('authorized_rows') != plan.get('target_rows') or isinstance(evidence.get('authorized_rows'), bool)
        or not isinstance(evidence.get('authorized_rows'), int)):
        reasons.append('authorized_count_mismatch')
    if evidence.get('approved_authorization_payload_sha256') != evidence.get('authorization_payload_sha256') or not evidence.get('authorization_payload_sha256'):
        reasons.append('authorization_hash_mismatch')
    if evidence.get('record_kind') in ('mock_test_only', 'mock_unitless_test'):
        reasons.append('mock_evidence_forbidden')
    return sorted(set(reasons))
