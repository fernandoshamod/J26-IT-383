"""Identify a verified proposed draft without creating approval or a frozen configuration."""
import hashlib
import json
from pathlib import Path
import sys

from component4.engine import fingerprint, parameter_payload
from component4.gates import pilot_approval_payload

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    data = load('work/approval_review_tables.json')
    config = load('config/simulator.candidate.json')
    checks = load('work/approval_review_verification.json')
    assert checks['status'] == 'passed' and checks['existing_python_tests_passed'] == 45
    assert config['approval_preparation']['candidate_frozen'] is False
    for path, digest in data['input_hashes'].items():
        assert sha(path) == digest, ('input changed', path)
    outputs = ['reports/assumption_decision_matrix.xlsx', 'reports/formula_review_checklist.md',
               'reports/numerical_parameter_review.md', 'config/simulator.candidate.json']
    code = ['component4/engine.py','component4/api.py','component4/gates.py',
            'scripts/research_pipeline/prepare_approval_review.py',
            'scripts/research_pipeline/build_approval_review.mjs',
            'scripts/research_pipeline/verify_approval_review.py',
            'scripts/research_pipeline/build_approval_manifest.py']
    manifest = {
        'manifest_version':'0.2.0-proposed-review', 'audit_date':'2026-10-11',
        'status':'proposed_unresolved', 'assumption_version':data['assumption_version'],
        'config_version':config['config_version'], 'rules_version':config['rules_version'],
        'values_and_units_fully_specified':False, 'candidate_frozen':False, 'frozen_at':None,
        'approved_configuration_sha256':None, 'frozen_configuration_sha256':None,
        'approved_parameter_payload_sha256':{'Wedding':None,'Corporate':None},
        'approved_pilot_payload_sha256':None,
        'draft_identity_only': {
            'candidate_file_bytes_sha256':sha('config/simulator.candidate.json'),
            'canonical_configuration_sha256':fingerprint(config),
            'parameter_payload_sha256':{e:fingerprint(parameter_payload(config['archetypes'][e])) for e in ['Wedding','Corporate']},
            'pilot_payload_sha256':fingerprint(pilot_approval_payload(config)),
            'notice':'Draft content identity only. Null-containing payload hashes are not fully specified, signed, frozen, approved or authorized.'
        },
        'hash_method': {
            'file_identity':'SHA256 of exact file bytes; differs from canonical JSON fingerprint',
            'engine_fingerprint':'SHA256 of UTF-8 json.dumps(value, sort_keys=True, separators=(comma, colon), allow_nan=False, ensure_ascii=True)',
            'parameter_payload_fields':['parameters','rates','billing','av_steps','lighting_steps','approved_override_bounds'],
            'pilot_payload':'configuration excluding pilot, plus pilot_scenario_count; count remains null',
            'manifest_self_hash':'Omitted to avoid a circular self-hash. No claim of RFC JSON Canonicalization Scheme compliance.'
        },
        'input_file_sha256':data['input_hashes'],
        'deliverable_file_sha256':{p:sha(p) for p in outputs},
        'code_file_sha256':{p:sha(p) for p in code},
        'verification': {
            'report_path':'work/approval_review_verification.json',
            'report_sha256':sha('work/approval_review_verification.json'),
            'existing_python_tests_passed':45,
            'additional_fixture_only_diagnostic_groups':len(checks['fixture_only_diagnostic_groups']),
            'active_numeric_nulls':108,'formal_approvals_recorded':0,
            'scope':'Workbook/cached formulas, mapping coverage, preserved source snapshots, live/pilot blocking and existing mock fixture arithmetic; not observed financial validation'
        },
        'runtime':{'python_version':sys.version.split()[0], 'git_revision':None,
                   'git_revision_note':'Not asserted; exact source-file SHA256 identities are recorded instead.'},
        'unresolved_decisions':[
            'Dated itemized local rates, tax/service-charge scopes, inclusions and provider selection',
            'Measured geometry, seating coefficients/capacity and general staffing/paid-hours schedule',
            'Legacy A011 ceiling versus amended independent package steps; venue tariff/unit normalization',
            'Explicit selections of experimental budget, reserve, margin, ranges and stress policies',
            'Genuine version-scoped qualified formula review and separate user parameter decisions',
            'Seed, source snapshots, bounds and later generator/dependence/injection implementation review'
        ],
        'pilot_authorized':False, 'pilot_scenario_count':None,
        'stop_condition':'Present pending decisions. Do not generate a pilot, bulk scenarios or train models. A candidate file or draft hash never grants approval.'
    }
    path = ROOT / 'reports/configuration_hash_manifest.json'
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    saved = load('reports/configuration_hash_manifest.json')
    assert saved['draft_identity_only']['canonical_configuration_sha256'] == fingerprint(config)
    for rel, digest in saved['deliverable_file_sha256'].items():
        assert sha(rel) == digest
    print(json.dumps({'manifest':str(path),'candidate_frozen':False,'approved_configuration_sha256':None,
                      'draft_file_sha256':saved['draft_identity_only']['candidate_file_bytes_sha256']}, indent=2))


if __name__ == '__main__':
    main()
