"""Prepare proposal metadata only. Does not generate scenarios or approvals."""
from copy import deepcopy
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from component4.engine import fingerprint, FORMULA_IDS
from component4.unitless_pilot import validate, code_hashes, execution_blockers


def candidate(original):
    c = deepcopy(original)
    c['version'] = 'unitless-pilot.0.3'
    c['revision_of_configuration_sha256'] = fingerprint(original)
    c['status'] = 'proposed_revision_not_approved'
    c['profiles']['Wedding']['event_hours'] = [4, 5, 6, 7]
    c['profiles']['Corporate']['budget_score'] = [2, 3, 3.8, 4, 5]
    c['planning_states'] = ['baseline', 'lower_intervention', 'upper_intervention']
    c['sampling_design'] = {
        'kind': 'purposive_boundary_diagnostics_not_population_sample',
        'independent_population_sample_size': None,
        'synthetic_base_families': 5,
        'shared_templates': True,
        'unseen_template_evaluation_supported': False,
        'randomness': 'Only bounded outcome replications; planning states are predeclared',
        'class_balancing': False,
    }
    specs = [
        ('Wedding', 'guest_threshold', 120, 5, 3, 4, 4, 4, 'guests', [120, 119, 121]),
        ('Wedding', 'av_threshold', 150, 5, 4, 3, 4, 4, 'stage_length_m', [3, 2.25, 4]),
        ('Wedding', 'overtime_threshold', 150, 6, 3, 4, 4, 4, 'event_hours', [6, 5, 7]),
        ('Corporate', 'guest_threshold', 60, 3, 3, 4, 3, 3, 'guests', [60, 59, 61]),
        ('Corporate', 'budget_intervention', 120, 4, 5, 6, 3.8, 4, 'budget_score', [3.8, 3, 5]),
    ]
    # Stage intervention keeps width=4: 4*2.25=9, 4*3=12, 4*4=16 m2.
    c['profiles']['Wedding']['stage_length_m'] = [2.25, 3, 4, 6]
    families = []
    for event, kind, guests, hours, width, length, budget, receipts, key, values in specs:
        base = dict(guests=guests, event_hours=hours, stage_width_m=width,
                    stage_length_m=length, budget_score=budget, retained_receipts_score=receipts)
        families.append({'event_type': event, 'diagnostic': kind,
                         'states': [{'name': name, 'inputs': {**base, key: value}}
                                    for name, value in zip(c['planning_states'], values)]})
    c['diagnostic_families'] = families
    c['experimental_source_snapshot'] = {
        'kind': 'HYPOTHETICAL_DESIGN_NOT_PUBLIC_MARKET_EVIDENCE',
        'version': c['version'], 'cost_unit': c['cost_unit'],
        'source_dependency_ids': c['source_dependency_ids'],
        'revision_scope': 'Predeclared boundary interventions; unchanged coefficients and venue template',
    }
    c['source_snapshot_sha256'] = fingerprint(c['experimental_source_snapshot'])
    validate(c)
    return c


def main():
    original = json.loads((ROOT / 'config/unitless_pilot_candidate.json').read_text())
    c = candidate(original)
    digest = fingerprint(c)
    targets = {
        'config/unitless_pilot_candidate.v0.3.proposed.json': c,
        'reports/unitless_pilot_revision_manifest.json': {
            'status': 'PROPOSED_NOT_APPROVED_NOT_EXECUTED',
            'configuration_sha256': digest,
            'previous_configuration_sha256': fingerprint(original),
            'code_sha256': code_hashes(),
            'runtime': {'python': platform.python_version(), 'numpy': np.__version__},
            'scenario_count': 30, 'event_types': ['Wedding', 'Corporate'],
            'missing_execution_conditions': execution_blockers(c),
        },
        'config/unitless_pilot_authorization.v0.3.blank.json': {
            'explicit_authorization': False,
            'configuration_sha256': digest, 'code_sha256': code_hashes(),
            'runtime': {'python': platform.python_version(), 'numpy': np.__version__},
            'scenario_count': 30, 'event_types': ['Wedding', 'Corporate'],
            'authorizer': None, 'date': None, 'evidence_ref': None,
            'approvals': {name: {'status': 'pending', 'reviewer': None, 'role': None,
                                'date': None, 'rationale': None, 'evidence_ref': None,
                                'configuration_sha256': digest}
                          for name in (*FORMULA_IDS, 'numerical_parameters', 'methodology',
                                       'sampling_split', 'acceptance_criteria', 'tests_passed')},
        },
    }
    for path, payload in targets.items():
        if 'authorization' in path and (ROOT / path).exists():
            existing = json.loads((ROOT / path).read_text())
            if existing.get('explicit_authorization') is not False or any(r.get('status') != 'pending' for r in existing.get('approvals', {}).values()):
                raise ValueError('refusing_to_overwrite_review_or_authorization_records')
    for path, payload in targets.items():
        # Never edits original candidate, data directories or completed review records.
        (ROOT / path).write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'configuration_sha256': digest, 'proposal_files': list(targets),
                      'scenarios_generated': 0}))


if __name__ == '__main__':
    main()
