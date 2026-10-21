"""Freeze a complete proposed bulk configuration. Never generates research rows."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.engine import fingerprint
from component4.unitless_bulk import hashes, validate, blockers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-verification', action='store_true')
    args = parser.parse_args()
    destination = ROOT / 'reports/unitless_bulk_authorization_v0.1'
    candidate_path = ROOT / 'config/unitless_bulk_candidate.v0.1.proposed.json'
    if (destination.exists() or candidate_path.exists()) and not args.refresh_verification:
        raise ValueError('refuse_overwrite_frozen_proposal')
    if args.refresh_verification and (ROOT / 'config/unitless_bulk_authorization.v0.1.user.json').exists():
        raise ValueError('cannot_refresh_an_authorized_proposal')
    model_path = ROOT / 'config/unitless_pilot_candidate.v0.3.proposed.json'
    model = json.loads(model_path.read_text())
    schema_path = ROOT / 'work/original_schema.json'
    columns = json.loads(schema_path.read_text())['Master_Data']['data'][0]
    review_path = ROOT / 'reports/stage6_unitless_pilot_20261012/pilot_review_results.json'
    review = json.loads(review_path.read_text())
    if review['internal_status'] != 'PASS' or review['configuration_sha256'] != fingerprint(model):
        raise ValueError('pilot_review_not_passing_exact_model')
    config = {'version': 'unitless-bulk.0.1', 'status': 'proposed_NOT_authorized',
              'record_kind': 'hypothetical_unitless_bulk_proposal', 'cost_unit': 'dimensionless_score', 'currency': None,
              'financial_model': model, 'financial_model_sha256': fingerprint(model),
              'master_columns': columns, 'master_schema_sha256': fingerprint(columns),
              'field_semantics_version': 'unitless-master-mapping.0.1',
              'sampling': {'roots': 1250, 'states_per_root': 3, 'replications_per_state': 2, 'rows': 7500,
                           'seed': 20261022, 'attempt_cap_per_root': 100,
                           'event_root_quotas': {'Wedding': 625, 'Corporate': 625},
                           'states': ['baseline', 'guest_minus_one', 'guest_plus_one'],
                           'root_policy': 'unique_baselines_uniform_discrete_rejection_sampling',
                           'event_date_start': '2027-01-01', 'event_date_end': '2027-12-31'},
              'split_policy': {'protocol': 'conditional_in_simulator', 'fractions': [.6, .2, .2], 'tolerance': .05},
              'acceptance_criteria': {'invalid_financial_rows': 0, 'invalid_spatial_rows': 0, 'missing_provenance_rows': 0,
                                      'duplicate_ids': 0, 'distinct_baselines': 1250, 'unseen_template_evaluation': False,
                                      'economic_realism_claim': False, 'class_balancing': False},
              'pilot_review': {'path': str(review_path.relative_to(ROOT)).replace('\\', '/'),
                              'sha256': hashlib.sha256(review_path.read_bytes()).hexdigest()},
              'source_snapshot': {'pilot_configuration_file_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
                                  'original_schema_file_sha256': hashlib.sha256(schema_path.read_bytes()).hexdigest(),
                                  'experimental_model_source_sha256': model['source_snapshot_sha256'],
                                  'real_market_calibration': False},
              'limitations': ['Arbitrary experimental scores, not LKR prices or normalized observed data.',
                              '625/625 roots are an experimental quota, not market frequency.',
                              'Sampling is without-replacement baselines, not an IID population sample.',
                              'Variants and paired replications are related; 7500 is not independent sample size.',
                              'Shared venue/vendor/source templates preclude unseen-template evaluation.',
                              'Experimental dates have no seasonal cost effect.',
                              'Quoted columns are planned simulated scores; Actual columns are simulated outcomes.',
                              'Unsupported fields are missing; excluded services are not asserted free.',
                              'No models trained, no risk probabilities or real-world accuracy claims.']}
    validate(config)
    digest = fingerprint(config)
    if args.refresh_verification:
        if not candidate_path.is_file() or fingerprint(json.loads(candidate_path.read_text())) != digest:
            raise ValueError('refresh_cannot_change_candidate_design')
        previous = destination / 'configuration_hash_manifest.json'
        backup = destination / 'configuration_hash_manifest.pre_export_correction.json'
        if previous.is_file() and not backup.exists():
            backup.write_bytes(previous.read_bytes())
    env = dict(os.environ, TEMP=str(ROOT / 'work'), TMP=str(ROOT / 'work'))
    suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT,
                           env=env, capture_output=True, text=True)
    transcript = suite.stdout + suite.stderr
    if suite.returncode:
        raise RuntimeError(transcript)
    count = int(re.search(r'Ran (\d+) tests', transcript).group(1))
    destination.mkdir(exist_ok=args.refresh_verification)
    if not args.refresh_verification:
        candidate_path.write_text(json.dumps(config, indent=2, allow_nan=False) + '\n')
    (destination / 'test_transcript.txt').write_text(transcript, encoding='utf-8')
    receipt = {'exit_code': suite.returncode, 'tests_run': count, 'code_sha256': hashes(),
               'configuration_sha256': digest, 'coverage': 'Small isolated test fixtures; no 7500-row research generation.',
               'transcript_sha256': hashlib.sha256(transcript.encode('utf-8')).hexdigest()}
    receipt_path = destination / 'test_results.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    authorization = {'explicit_bulk_authorization': False, 'configuration_sha256': digest,
                     'code_sha256': hashes(), 'runtime': {'python': platform.python_version(), 'numpy': np.__version__},
                     'scenario_count': 7500, 'event_types': ['Wedding', 'Corporate'],
                     'authorizer': None, 'date': None, 'evidence_ref': None, 'evidence_sha256': None,
                     'approval_rationale': None, 'approval_kind': 'experiment_designer_only_NOT_qualified_review',
                     'test_receipt': {'path': str(receipt_path.relative_to(ROOT)).replace('\\', '/'),
                                      'sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest()},
                     'model_training_authorized': False, 'lkr_generation_authorized': False}
    (ROOT / 'config/unitless_bulk_authorization.v0.1.blank.json').write_text(json.dumps(authorization, indent=2) + '\n')
    manifest = {'status': 'PROPOSED_NOT_EXECUTED', 'canonical_configuration_sha256': digest,
                'configuration_file_sha256': hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
                'code_sha256': hashes(), 'rows': 7500, 'formula_review_kind': 'Inherited pilot experiment-designer review; expanded design pending user approval',
                'source_snapshots': config['source_snapshot'], 'test_results': receipt,
                'execution_blockers': blockers(config, authorization)}
    (destination / 'configuration_hash_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    text = f'''# Unitless bulk-generation authorization decision

Prepared 12 October 2026. No bulk dataset generated. This is a separate proposal, not a reuse of pilot authorization.

## Proposed execution

7,500 synthetic unitless rows = 1,250 distinct root baselines × three guest-count states × two paired outcome replications.
Wedding: 625 roots / 3,750 rows. Corporate: 625 roots / 3,750 rows.
The pilot's seven financial coefficients, capacity model, contingency policy and bounded shock rules are unchanged.
Canonical SHA-256: `{digest}`.

## Decisions for the experiment designer

Approve or reject the 7,500-row count, balanced archetype quotas, discrete uniform planning design, seed 20261022,
100 attempts per root, experimental 2027 date range, guest-minus/plus-one interventions, paired shocks,
conditional family/fingerprint-grouped 60/20/20 split with ±5 percentage-point tolerance, and dimensionless master mapping.
Dates do not imply seasonality. Distinct baseline sampling without replacement is not statistical independence.
Any identical intervention configurations join their families transitively. Splits are determined before outcomes.
No class balancing, favorable-seed selection, invented venue IDs or real-world prediction claims.

## Evidence and scope

Pilot: 30 rows, internal review PASS. Real-world economic realism remains unvalidated.
All {count} current automated tests pass. New bulk tests use isolated 60-row MOCK fixtures only.
Full-scale throughput and final exports will be validated during authorized generation, not claimed tested now.
The isolated exporter QA and any native preview warnings are recorded separately in exporter_verification.json.
Shared template evaluation is conditional; unseen-venue/vendor evaluation is unavailable.
Your earlier supervisor-review waiver applies to the hypothetical pilot; no professional or institutional signoff is claimed here.
This proposal requests your experiment-designer approval of the expanded hypothetical scope. It does not authorize LKR calibration or ML training.

## Schema and accounting

All 46 column names and order retained. Monetary fields are dimensionless scores, never LKR.
Quoted_* means experimental planned charge. Actual_* means simulated outcome. Cost_Variance = simulated minus planned cost.
Space_Utilization and Budget_Utilization are ratios. Profit_Margin and Required_Min_Profit_Margin are percentage points.
Equipment planned cost aggregates chairs + tables + stage; AV is separate. Labor_Hours is unweighted paid person-hours,
while the ledger's labour quantity includes overtime weighting. Reserve is inside the budget, not an expense.
VIP area, decoration, lighting, security, transport, miscellaneous costs, historical mean cost, vendor volatility and health score remain missing.
They are unsupported/excluded, not observed zeros. Null missing values are documented in the final dictionary.

## Output and reproducibility

Use a new unitless-specific directory without overwriting existing LKR, historical or pilot files.
Persist master CSV/XLSX, planning, simulated outcomes, financial ledger, provenance, separate latents, rejection log,
configuration, exact human authorization and manifest/file checksums. Write atomically and reconcile all saved master workbook cells.
If attempts, split tolerance, geometry, arithmetic, approval or export validation fail, do not silently relax rules or alter the seed.
No final-version freeze until output and model-ready-table audits pass.

## Separate explicit execution decision

To approve this exact proposal and authorize its execution, reply:

“I approve and authorize the 7,500-row unitless Wedding/Corporate generation under configuration SHA-256 {digest}.
I accept the hypothetical costs, conditional grouped evaluation, experimental sampling and unitless field definitions.
This does not authorize LKR scenarios or model training.”

No approval has been recorded for this proposal. Generic requests to finish are not treated as hash-specific execution approval.
'''
    (destination / 'bulk_authorization_decision.md').write_text(text, encoding='utf-8')
    (destination / 'README.md').write_text('# Bulk proposal status\n\nThe generator, frozen proposed configuration, blank authorization and test receipt exist.\n'
        'Execution remains blocked by missing separate human bulk approval. Original pilot and LKR configurations were not changed.\n')
    print(json.dumps({'canonical_configuration_sha256': digest, 'tests_passed': count,
                      'status': 'READY_FOR_EXPLICIT_USER_DESIGN_AND_EXECUTION_DECISION',
                      'research_rows_generated': 0, 'decision_packet': str(destination / 'bulk_authorization_decision.md')}, indent=2))


if __name__ == '__main__':
    main()
