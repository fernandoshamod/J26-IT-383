"""Stage 4 audit/package builder. Runs software tests, NEVER calls pilot generation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import unittest

import numpy as np

from component4.engine import FORMULA_IDS, PARAMS, RATE_UNITS, evaluate, fingerprint, parameter_payload
from component4.gates import pilot_approval_payload
from component4.generator_validation import (CODE_FILES, GENERATOR_VERSION, PARAMETER_UNITS,
    REQUIRED_ASSUMPTIONS, generator_approval_payload, software_versions)
from component4.scenario_generator import pilot_execution_blockers

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'pilot-diagnostic.0.1-proposed'
DATE = '2026-10-11'
DOCS = ['reports/pilot_authorization_form.md','reports/pilot_acceptance_criteria.md']


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def write(path,obj):
    (ROOT/path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def value_at(config,path):
    for part in path.split('.'):
        config = config[part]
    return config


def md(value):
    return 'null' if value is None else str(value).replace('|','/').replace('\n',' ')


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(md(x) for x in row)+' |' for row in rows])


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item.id()


def complete_review(record,hash_key=None):
    if not isinstance(record,dict) or record.get('status')!='approved':
        return False
    fields = ['reviewer','reviewer_role','reviewed_at','rationale','evidence_ref']
    if hash_key:
        fields.append(hash_key)
    if not all(isinstance(record.get(k),str) and record[k].strip() for k in fields):
        return False
    try:
        datetime.strptime(record['reviewed_at'],'%Y-%m-%d')
    except ValueError:
        return False
    return True  # Shape only; not an authenticated signature.


def main():
    existing = ROOT/'config/pilot_candidate.json'
    old_manifest = ROOT/'reports/pilot_hash_manifest.json'
    if existing.exists():
        if not old_manifest.exists() or sha('config/pilot_candidate.json')!=read('reports/pilot_hash_manifest.json')['deliverable_sha256']['config/pilot_candidate.json']:
            raise RuntimeError('Existing pilot candidate was manually changed; preserve and review instead of overwriting')
    base = read('config/simulator.candidate.json')
    stage2 = read('reports/configuration_hash_manifest.json')
    stage3 = read('work/generator_verification.json')
    expected = {}
    expected.update(base['evidence_audit']['source_snapshot_hashes_for_audit_only'])
    expected.update(stage2['input_file_sha256'])
    expected.update(stage2['deliverable_file_sha256'])
    expected.update(stage3['code_sha256'])
    historical = {p:{'expected_sha256':h,'actual_sha256':sha(p),'match':sha(p)==h} for p,h in expected.items()}
    require_preserved = all(r['match'] for r in historical.values())
    if not require_preserved:
        raise RuntimeError('Historical input/source/code changed; review the revision before packaging')
    # Tests use their existing isolated 1–16-record mock interfaces and removed temporary directories.
    suite = unittest.TestLoader().discover(str(ROOT/'tests'))
    test_ids = list(flatten(suite))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    tests = {'tests_run':result.testsRun,'original_tests':sum(not x.startswith('test_scenario_generator.') for x in test_ids),
             'generator_tests':sum(x.startswith('test_scenario_generator.') for x in test_ids),
             'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
             'passed':result.wasSuccessful(),'test_ids':test_ids,'software_versions':software_versions(),
             'scope':'Mock software fixtures only; no authorized pilot or project financial rows generated'}
    assert tests['original_tests']==45 and tests['generator_tests']==45 and tests['tests_run']==90

    proposal = {
        'protocol_version':VERSION,'status':'pending_review','reviewer':None,'reviewer_role':None,'review_date':None,
        'rationale_ref':'reports/pilot_acceptance_criteria.md','approval_evidence_ref':None,
        'proposed_total_records':40,'base_configurations':40,'additional_variants_per_base':0,
        'outcome_realizations_per_base':1,'proposed_archetype_weights':{'Wedding':0.5,'Corporate':0.5},
        'expected_profile_counts_not_quotas':{'Wedding':20,'Corporate':20},
        'minimum_records_per_profile_for_scope_review':10,'proposed_seed':20261022,
        'proposed_max_attempts_per_base':20,'minimum_unique_planning_tuples_total':20,
        'minimum_unique_planning_tuples_per_profile':5,'maximum_rejection_fraction_for_scope_review':0.20,
        'proposed_input_policy':{'guest_count':'reviewed uniform_integer bounds; currently null',
            'event_hours':'reviewed discrete choices; currently null','stage_dimensions':'reviewed discrete choices; currently null',
            'venue_geometry':'fixed measured reviewed profile, not generated observations',
            'budget':'fixed ex-ante LKR domain; currently null','retained_receipts':'independent LKR domain; currently null',
            'event_date':'uniform integer day inside reviewed interval; currently null'},
        'proposed_outcome_policy':'independent bounded_uniform_multipliers; bounds/service scope and anomaly regime remain null',
        'not_supported_in_current_generator':['exact stratified quotas','paired child variants','multiple outcomes per fixed base'],
        'warning':'Research-design proposals only; not selected runtime values, population proportions, market prices, approvals or calibrated probabilities'
    }
    candidate = deepcopy(base)
    candidate['config_version'] = '0.3.0-pilot-authorization-proposed'
    candidate['record_kind'] = 'unresolved_pilot_candidate_proposal'
    candidate['scenario_generator'] = read('config/scenario_generator.template.json')
    candidate['scenario_generator'].update(
        code_snapshot_hashes={p:sha(p) for p in CODE_FILES},software_versions=software_versions(),
        assumption_version=base['approval_preparation']['assumption_version'],assumption_ids=sorted(REQUIRED_ASSUMPTIONS))
    candidate['generator_approval'] = {'status':'pending','reviewer':None,'reviewer_role':None,'reviewed_at':None,
        'rationale':None,'evidence_ref':None,'generator_version':GENERATOR_VERSION,
        'assumption_version':base['approval_preparation']['assumption_version'],'payload_sha256':None}
    candidate['pilot_protocol_proposal'] = proposal
    candidate['pilot_preparation'] = {'protocol_version':VERSION,'prepared_date':DATE,'status':'blocked_proposed',
        'parent_candidate_path':'config/simulator.candidate.json','parent_candidate_file_sha256':sha('config/simulator.candidate.json'),
        'protocol_document_sha256':{p:sha(p) for p in DOCS},
        'candidate_frozen':False,'fully_specified':False,'frozen_configuration_sha256':None,
        'notice':'Actual runtime/code metadata recorded for audit only. Proposal counts, seed, thresholds and policies do not activate the generator. All genuine review/authorization fields remain blank.'}
    assert candidate['archetypes']==base['archetypes'] and candidate['formula_approvals']==base['formula_approvals']
    assert candidate['pilot']==base['pilot'] and candidate['seed'] is None
    assert candidate['scenario_generator']['seed'] is None and candidate['scenario_generator']['max_attempts_per_scenario'] is None
    assert all(x is None for x in candidate['scenario_generator']['archetype_weights'].values())
    assert candidate['source_snapshot_hashes'] is None and candidate['scenario_generator']['source_snapshot_hashes'] is None
    write('config/pilot_candidate.json',candidate)

    numeric = []
    for r in base['approval_preparation']['numeric_review_records']:
        path,event = r['path'],r['event_type']
        value = value_at(candidate,path)
        if '.parameters.' in path:
            expected_unit = PARAMETER_UNITS[r['parameter']]
            actual_evidence = r['decision_evidence_ref']
        else:
            item,field = path.split('.rates.')[1].split('.')
            expected_unit = RATE_UNITS[item] if field=='rate' else 'percentage points'
            actual_evidence = candidate['archetypes'][event]['rates'][item]['evidence_ref']
        numeric.append({'path':path,'event_type':event,'value':value,'expected_unit':expected_unit,
            'review_unit':r['unit'],'unit_exact_match':r['unit']==expected_unit,
            'assumption_ids':r['assumption_ids'],'supporting_refs_not_selected_evidence':r['supporting_refs'],
            'selected_evidence_ref':actual_evidence,'decision_status':r['status'],
            'reviewer':r['reviewer'],'review_date':r['review_date'],
            'scope_parameter_approval_status':candidate['archetypes'][event]['parameter_approval']['status'],
            'ready':False})
    assert len(numeric)==108 and all(x['value'] is None for x in numeric)
    unit_aliases = [x for x in numeric if not x['unit_exact_match']]
    assert len(unit_aliases)==6
    formulas = []
    mapping = {x['formula_id']:x for x in base['approval_preparation']['formula_review_records']}
    for aid in FORMULA_IDS:
        r = candidate['formula_approvals'][aid]
        formulas.append({'assumption_id':aid,'rules_version':candidate['rules_version'],
            'decision_version':mapping[aid]['assumption_version'],'supporting_refs':mapping[aid]['supporting_refs'],
            'status':r['status'],'structurally_complete':complete_review(r),
            'reviewer':r['reviewer'],'review_date':r['reviewed_at'],'selected_review_evidence':r['evidence_ref']})
    rates = []
    for event in ('Wedding','Corporate'):
        for item,r in candidate['archetypes'][event]['rates'].items():
            rates.append({'event_type':event,'item':item,**deepcopy(r),
                'unit_matches_engine':r['unit']==RATE_UNITS[item],'charged_or_included':'unresolved inclusion map'})
    assert len(rates)==28
    parents = pilot_execution_blockers(base)
    machine = pilot_execution_blockers(candidate)
    manual = [
        'M01:no_genuine_version_scoped_formula_reviews',
        'M02:no_complete_dated_compatible_quotation_tax_bundle_profiles',
        'M03:no_measured_reviewed_seating_geometry_and_general_staff_paid_hours_scope',
        'M04:no_explicit_user_parameter_budget_margin_reserve_decisions',
        'M05:six_paid_time_unit_descriptions_require_explicit_clarification',
        'M06:40_root_count_weights_seed_attempt_and_diversity_thresholds_are_proposals_only',
        'M07:date_guest_duration_stage_budget_receipt_domains_unresolved',
        'M08:ordinary_shock_dependence_and_injection_parameters_unapproved',
        'M09:pilot_source_snapshots_cutoff_and_ancestry_not_selected_or_approved',
        'M10:AC01_to_AC14_have_no_pre_results_approval',
        'M11:generator_implementation_and_test_acceptance_not_independently_recorded',
        'M12:configuration_not_eligible_for_freeze_no_frozen_hash',
        'M13:no_explicit_exact_count_scope_authorization_or_authenticated_review',
        'M14:external_observed_event_validation_not_performed_disposition_required'
    ]
    if not tests['passed']:
        manual.append('M15:full_test_suite_failed')
    # Preview is explicitly null-containing and non-authoritative; it does not modify the active count.
    requested_preview = deepcopy(candidate)
    requested_preview['pilot']['scenario_count'] = proposal['proposed_total_records']
    draft_hashes = {'file_bytes_sha256':sha('config/pilot_candidate.json'),
        'canonical_configuration_sha256':fingerprint(candidate),
        'parameter_payload_sha256':{e:fingerprint(parameter_payload(candidate['archetypes'][e])) for e in ('Wedding','Corporate')},
        'generator_payload_sha256':fingerprint(generator_approval_payload(candidate)),
        'pilot_payload_null_active_count_sha256':fingerprint(pilot_approval_payload(candidate)),
        'requested_40_count_preview_sha256':fingerprint(pilot_approval_payload(requested_preview))}
    assert machine and all(evaluate(candidate,e)['status']=='blocked' for e in ('Wedding','Corporate'))

    audit = {'protocol_version':VERSION,'prepared_date':DATE,'status':'BLOCKED','numeric_parameters':numeric,
        'formula_audit':formulas,'rate_cards':rates,'historical_hash_checks':historical,'test_run':tests,
        'parent_candidate_machine_blockers':parents,'pilot_candidate_machine_blockers':machine,
        'manual_readiness_blockers':manual,'draft_hashes':draft_hashes,'frozen_configuration_sha256':None,
        'pilot_generated':False,'proposal':proposal}
    write('work/pilot_readiness_audit.json',audit)
    headings = ['Gate / scope','Observed status','Required disposition']
    gate_rows = [
        ['G1 formula scope','0/19 genuine approved engine records; amended A011 remains unresolved','Qualified version-scoped formula reviews; reconcile legacy definitions'],
        ['G2 numerical scope','108/108 active values null; 0/108 selected evidence bindings/review decisions','Complete both profiles with compatible evidence or explicitly reviewed experimental non-price policies'],
        ['G2 units/taxes','28 rate-card units valid; 28 tax scopes/point values unset; six paid-time wording aliases','Review individual-hours meaning, tax/service-charge bases and billing units'],
        ['G2 geometry/bundles','Areas/capacity/staff inputs and inclusion maps/AV steps unresolved','Measured plans, arrangements, staff/paid-hours schedules and supported billing'],
        ['G3 software implementation',f'{tests["tests_run"]} tests run; {tests["failures"]} failures / {tests["errors"]} errors','Independent acceptance and complete frozen sampling/outcome scope still required'],
        ['G3 snapshots',f'{len(historical)} historical byte-hash checks pass; approved pilot source selection is null','Audit integrity is not approval/applicability; obtain dated real evidence and approve source/cutoff/ancestry'],
        ['G3 pilot protocol','40 roots / no variants / 1 outcome proposed; 0.5/0.5 weights, seed and thresholds not selected','Actual user/supervisor decision and pre-results AC01–AC14 acceptance'],
        ['G4 explicit authority','Active count null, authority false, all five pilot references null','Exact 20–50 count-scoped real authorization and approved payload'],
        ['Freeze','Not eligible; authoritative frozen SHA256 null','Complete and review first; draft identities cannot be signed as a completed freeze'],
        ['G5 external validation','No independent observed event financial outcomes/labels','Explicit simulator-only diagnostic limitation/disposition; no field-performance claim']
    ]
    report = f'''# Stage 4 diagnostic pilot readiness report

Prepared 11 October 2026. Protocol `{VERSION}`. PP1: 22 October 2026.

## Decision — BLOCKED

The authorization **review package** is complete; the actual configuration is not complete, frozen or authorized. No pilot rows were generated. All existing engine/generator code, Stage 1/2 artifacts and prior approvals were preserved. No new approval, reviewer identity, date or signature was invented.

The current parent candidate and this Stage 4 derivative both block live calculations. {len(machine)} current machine blocker codes and {len(manual)} separately documented manual readiness reasons are recorded below and in `pilot_hash_manifest.json`. Validation is fail-fast: the proposed generator marker blocks execution before later nested missing settings are checked; those settings have not passed merely because no individual error is returned for them.

## Audit against existing authorization conditions

''' + table(headings,gate_rows) + f'''

The existing `pilot_authorization_conditions.md` remains authoritative. Its statement that no generator exists is historical: Stage 3 implemented it and the current full test run passed. The existing `scenario_generator_not_implemented_or_verified` code persists because independent accepted verification/authorization is still false, not because software is absent. Source quotations/public pages were not downloaded or reinspected; this audit verifies existing byte snapshots and recorded applicability, not current market validity.

## Formula and numerical evidence findings

All 34 assumption decisions remain pending. Nineteen engine-gated formula records have known code-rule version 0.1.0-review and Stage 2 decision version assumption-review.0.2.0-proposed, but no genuine approved reviewer records. The two additional utility mappings are not extra existing engine gate IDs; sampling, outcome and anomaly design need separate generator review. This report does not approve arithmetic identities on a supervisor's behalf.

The 108 audited paths comprise 52 base inputs, 28 service-rate values and 28 tax-point values. Every path has an assumption/unit/support-reference mapping, but all values, selected evidence decisions and actual reviewers remain missing. QUOTE/STAGE1/E identifiers are review references/candidates, not filled and approved quotes. No missing value was changed to zero.

Twenty Stage 1 advertised-price entries from nine source pages remain contextual candidates, not a complete 2026 rate card. The historical 2025 wedding menu is not a current 2026 quotation; per-person meeting bundles cannot be treated as catering alone; first-hour/after-time/day tariffs do not equal the engine's all-hours tariff; item-day prices do not directly define kits/booking totals; service charge is not a tax default. No public procurement total or foreign rate is transferred into the live configuration. No quote date is invented from the page access date.

Refundable deposits and advances are not additional expense lines. Tax-inclusive/exclusive treatment, compound service-charge/tax scope and invoice rounding require accounting review. One-level bundle exclusions need actual quotation support. Contingency stays outside expense/profit calculations; budgets/retained receipts are fixed ex ante. All these financial scopes remain unapproved.

Six base-unit descriptions need clarification: setup/clearance 'paid hours' and regular-hour-limit 'hours/person' versus generator canonical 'hours', in both profiles. They describe per-worker paid duration, not aggregate person-hours. No numerical conversion or automatic approval was applied. The current actual values remain null.

## Sampling and acceptance proposal, not activation

Proposed count: **40 base configurations × one outcome each = 40 rows**, no variants or extra replications. Both archetypes use proposed 0.5/0.5 weighted random selection: expected 20 each, not guaranteed stratification. Coverage minimum 10 each, meaningful diversity minimum 20 tuples overall / 5 each, maximum 20% rejection review threshold, seed 20261022 and attempt cap 20 are explicit proposal-only research choices. No field selection is inferred from this preparation request.

`pilot_acceptance_criteria.md` defines AC01–AC14 before results: exact LKR reconciliation, no double charging, measured physical constraints, paid-hour reconciliation, complete provenance, exact replay, reviewed distribution support, coverage/diversity, independently recalculated labels, predictor allowlist, logged invalid attempts, retention of valid financial failures and intact outputs. Rates, date/geometry/staffing/budget/receipt bounds and outcome/injection regimes remain null. Criteria are PENDING REVIEW and have not been evaluated on pilot data. There is no label-balance target, seed search, post-result adaptation or calibrated probability claim.

## Fresh full-suite verification

Run: {tests['tests_run']} tests = {tests['original_tests']} original + {tests['generator_tests']} generator tests; failures {tests['failures']}, errors {tests['errors']}, skipped {tests['skipped']}. Runtime Python {platform.python_version()}, NumPy {np.__version__}. These tests use only isolated in-memory mock fixtures and a two-record temporary serializer check; no actual pilot dataset was created. Passing tests are software evidence, not real quotation/geometry validation or formal generator acceptance.

All {len(historical)} distinct recorded historical/source/code byte identities match. Audit-only historical hashes include macro, foreign benchmark and software-fixture artifacts; they are not automatically selected calibration evidence. Approved pilot source_snapshot_hashes and calibration_cutoff remain null. There are no hashed provider-issued complete event quotation records or independent observed financial outcome/label records in the selected configuration.

## Configuration hash status

**Frozen configuration SHA256: null — configuration is not eligible for a freeze.**

Draft canonical candidate fingerprint: `{draft_hashes['canonical_configuration_sha256']}`.

Draft exact candidate-file byte SHA256: `{draft_hashes['file_bytes_sha256']}`.

The manifest additionally records draft parameter/generator/pilot identities and an explicitly non-authoritative intended-count-40 preview. Both previews still contain unresolved values/reviews. They are NOT frozen/approved authorization hashes. Active pilot count stays null and authority false. The authoritative frozen/approved fields stay null. Do not write a hash into the same payload it hashes; use the external final manifest and existing self-excluding approval payload definitions.

## Formula-by-formula review status

''' + table(['ID','Rule version','Review status','Selected review evidence','Supporting references'],
            [[r['assumption_id'],r['rules_version'],r['status'],r['selected_review_evidence'],r['supporting_refs']] for r in formulas]) + '''

## Complete active numerical-path audit

All rows are NOT READY. The supporting references below do not constitute a selected evidence binding or approval. Expected canonical units are checked against the engine/generator constants; differing paid-time terms require the review described above.

''' + table(['Configuration path','Expected unit','Recorded review unit','Value','Selected evidence','Review status','Assumptions','Supporting refs'],
            [[r['path'],r['expected_unit'],r['review_unit'],r['value'],r['selected_evidence_ref'],r['decision_status'],';'.join(r['assumption_ids']),r['supporting_refs_not_selected_evidence']] for r in numeric]) + '''

## Service-rate, tax and date audit

All 28 rate cards remain pending. LKR currency and exact service units are present, but prices, quote dates, taxes and concrete evidence references are missing. No bundle map is selected, so there is no reviewed waiver for uncharged items.

''' + table(['Profile/item','Unit','Rate','Quote date','Tax scope','Tax points','Evidence','Approval'],
            [[r['event_type']+'/'+r['item'],r['unit'],r['rate'],r['quote_date'],r['tax_scope'],r['tax_rate_points'],r['evidence_ref'],r['approval_status']] for r in rates]) + '''

## Exact current machine blockers

```text
''' + '\n'.join(machine) + '''
```

## Additional manual authorization decisions still missing

```text
''' + '\n'.join(manual) + '''
```

Use D01–D12 in `pilot_authorization_form.md` to record actual review, not software-generated signatures. An explicitly simulator-only diagnostic may be reviewed without independent observed outcomes only with the limitation/disposition recorded; this is not permission to claim real-world validation.

## Reproduce the package without a pilot

```powershell
Set-Location 'C:\\Users\\User\\Documents\\ChatGPT\\ML'
$env:PYTHONPATH = (Get-Location).Path
python scripts/research_pipeline/prepare_pilot_authorization.py
```

This runs existing tests and refreshes draft audit artifacts, not pilot data. It refuses to overwrite a manually modified pilot candidate. It does not interpret completed forms, authenticate signatures or activate any approval. Final completion/authorization must be a separate real decision followed by a new completeness/hash/gate review. No bulk generation or training is authorized.

BLOCKED
'''
    (ROOT/'reports/pilot_readiness_report.md').write_text(report,encoding='utf-8')
    outputs = ['reports/pilot_readiness_report.md',*DOCS,'config/pilot_candidate.json']
    inputs = ['config/simulator.candidate.json','config/scenario_generator.template.json',
        'reports/pilot_authorization_conditions.md','reports/configuration_hash_manifest.json',
        'reports/generator_design.md','reports/generator_test_results.md','work/generator_verification.json',
        'reports/parameter_evidence_summary.md']
    manifest = {'manifest_version':VERSION,'prepared_date':DATE,'audit_timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'readiness':'BLOCKED','candidate_frozen':False,'values_and_units_fully_specified':False,
        'frozen_configuration_sha256':None,'approved_configuration_sha256':None,'approved_generator_payload_sha256':None,
        'approved_parameter_payload_sha256':{'Wedding':None,'Corporate':None},'approved_pilot_payload_sha256':None,
        'draft_identity_only':draft_hashes,'requested_protocol_proposal':proposal,
        'active_pilot_count':None,'explicit_pilot_authorization':False,
        'hash_serialization':'Engine fingerprint: SHA256 UTF-8 json.dumps(sort_keys=True,separators=(comma,colon),allow_nan=False,ensure_ascii=True); file bytes are a distinct identity. Not a claim of RFC JCS.',
        'hash_warning':'No authoritative frozen hash can be calculated until unresolved scope is completed and reviewed. Hashing nulls only identifies this draft, not an approved freeze. Manifest self-hash is omitted to avoid circularity.',
        'historical_snapshot_checks':historical,'input_sha256':{p:sha(p) for p in inputs},
        'code_sha256':{p:sha(p) for p in CODE_FILES+('component4/api.py','scripts/research_pipeline/prepare_pilot_authorization.py',
            'tests/test_engine.py','tests/test_dashboard_api.py','tests/test_financial_features.py','tests/test_scenario_generator.py')},
        'deliverable_sha256':{p:sha(p) for p in outputs},'audit_json_path':'work/pilot_readiness_audit.json',
        'audit_json_sha256':sha('work/pilot_readiness_audit.json'),'test_summary':{k:v for k,v in tests.items() if k!='test_ids'},
        'machine_blockers':machine,'manual_readiness_blockers':manual,
        'structurally_complete_formula_approvals':sum(x['structurally_complete'] for x in formulas),
        'active_numeric_fields':108,'active_numeric_nulls':108,'rate_cards':28,'paid_time_unit_clarifications':6,
        'source_authenticity':'Not established by file hashes; approved source selection remains null',
        'pilot_rows_generated':False,'models_trained':False}
    write('reports/pilot_hash_manifest.json',manifest)
    saved = read('config/pilot_candidate.json')
    assert saved==candidate
    assert pilot_execution_blockers(saved)==machine
    assert saved['pilot']['explicit_user_authorization'] is False and saved['pilot']['scenario_count'] is None
    assert all(value_at(saved,r['path']) is None for r in numeric)
    assert fingerprint(saved)==manifest['draft_identity_only']['canonical_configuration_sha256']
    for path,digest in manifest['deliverable_sha256'].items():
        assert sha(path)==digest
    assert all(sha(path)==r['actual_sha256'] for path,r in historical.items())
    print(json.dumps({'readiness':'BLOCKED','tests':tests['tests_run'],'test_suite_passed':tests['passed'],
        'active_numeric_nulls':108,'machine_blockers':len(machine),'manual_review_reasons':len(manual),
        'historical_snapshots_preserved':len(historical),'frozen_configuration_sha256':None,
        'pilot_rows_generated':False},indent=2))
    if not tests['passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
