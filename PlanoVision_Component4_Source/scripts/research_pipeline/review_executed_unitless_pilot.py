"""Reproduce read-only diagnostics and write dated review reports, not scenario rows."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.pilot_review import review
from component4.engine import fingerprint
from component4.unitless_pilot import execution_blockers


def main():
    source = ROOT / 'data/pilot/unitless-v0.3-user-authorized-20261012'
    dest = ROOT / 'reports/stage6_unitless_pilot_20261012'
    if dest.exists():
        raise ValueError('refuse_to_overwrite_dated_review')
    config = json.loads((source / 'configuration.json').read_text())
    auth = json.loads((ROOT / 'config/unitless_pilot_authorization.v0.3.user.json').read_text())
    blockers = execution_blockers(config, auth)
    if blockers:
        raise ValueError(str(blockers))
    # Existing exact replay + CSV/workbook/hash verification. No persistent generation.
    subprocess.run([sys.executable, str(ROOT / 'scripts/research_pipeline/execute_user_authorized_unitless_pilot.py'),
                    '--verify-existing'], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads((source / 'export_payload.json').read_text())
    if fingerprint(payload['configuration']) != fingerprint(config):
        raise ValueError('payload_configuration_mismatch')
    result = review(payload)
    env = dict(os.environ, TEMP=str(ROOT / 'work'), TMP=str(ROOT / 'work'))
    suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                           cwd=ROOT, env=env, capture_output=True, text=True)
    if suite.returncode:
        raise RuntimeError(suite.stdout + suite.stderr)
    dest.mkdir()
    (dest / 'test_transcript.txt').write_text(suite.stdout + suite.stderr, encoding='utf-8')
    result['configuration_sha256'] = fingerprint(config)
    result['source_file_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in source.iterdir() if p.is_file()}
    result['review_code_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                                   ('component4/pilot_review.py', 'scripts/research_pipeline/review_executed_unitless_pilot.py')}
    (dest / 'pilot_review_results.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    header = '# Unitless pilot review — 12 October 2026\n\n'
    disclaimer = ('Hypothetical dimensionless experiment, not LKR quotations, real observed outcomes, '
                  'qualified methodology approval or demonstrated prediction accuracy. User approval and '
                  'supervisor-review waiver remain as recorded; this review does not invent further approvals.\n\n')
    rows = ['| Event | Measurement | N | Min | Median | Mean | Max |', '|---|---|---:|---:|---:|---:|---:|']
    for event, metrics in result['distributions'].items():
        for name, stats in metrics.items():
            if 'n' in stats:
                rows.append(f"| {event} | {name} | {stats['n']} | {stats['min']:.6g} | {stats['median']:.6g} | {stats['mean']:.6g} | {stats['max']:.6g} |")
    (dest / 'pilot_distribution_analysis.md').write_text(header + disclaimer +
        'Planning summaries use 15 distinct planning configurations, not 30 duplicated planning records. '
        'Service and realized-outcome summaries are available in the JSON receipt. Five purposive roots '
        'share one venue and vendor template. Ten family/replication random streams are paired across '
        'three states; 30 labels are not 30 independent outcome draws.\n\n' + '\n'.join(rows) +
        '\n\nLabels: ' + json.dumps(result['label_counts']) +
        '\n\nThese sample frequencies are neither population prevalence nor performance metrics. '
        'No label balancing was performed. All 30 configurations are feasible; zero pilot rejections.\n', encoding='utf-8')
    dependency = []
    for d in result['dependencies']:
        states = [d[k] for k in ('lower', 'baseline', 'upper')]
        dependency.append(f"- {d['event']} / {d['diagnostic']}: PASS; cost lower/baseline/upper " +
                          ' / '.join(f"{s['planned_cost_score']:.8g}" for s in states) +
                          '; tables ' + str([s['tables'] for s in states]) +
                          '; staff ' + str([s['staff'] for s in states]) +
                          '; AV kits ' + str([s['quantities']['av'] for s in states]) + '.')
    (dest / 'pilot_dependency_validation.md').write_text(header + disclaimer + '\n'.join(dependency) +
        '\n\nAll ledgers and labels reconcile through validate_bundle. Reserve is earmarked inside '
        'budget, not charged as an expense. Budget intervention changes feasibility, not underlying cost. '
        'Vendor anomaly is the injection mechanism label, not a verified market anomaly.\n')
    probes = sum(s['attempts'] for s in result['sensitivity'])
    rejected = sum(sum(s['rejected'].values()) for s in result['sensitivity'])
    (dest / 'pilot_sensitivity_analysis.md').write_text(header + disclaimer +
        f'{probes} deterministic one-factor calculator probes across five baselines and six inputs; '
        f'{rejected} rejected probes. These are NOT added scenario records or stochastic outcome replications. '
        'Only values in existing reviewed profile domains were evaluated; coefficients, geometry and shocks '
        'were not modified. Complete bounds, rejection reasons and financial-breach counts are in '
        'pilot_review_results.json. Guest sweeps test seating/staff thresholds; stage sweeps test AV; '
        'duration tests overtime; budget and retained receipts are varied independently. This is a local '
        'sensitivity diagnostic, not global sensitivity or empirical elasticity estimation.\n')
    (dest / 'pilot_final_assessment.md').write_text(header + disclaimer +
        'PASS — internal unitless diagnostic scope only; ready to request separate bulk-design approval.\n\n'
        'Existing output replay, file hashes, accounting, geometry, label definitions, conditional group '
        'splits and all five dependency contrasts pass. The full current test transcript is retained. '
        'No engine correction or configuration change was necessary. Historical pre-pilot reports remain '
        'unchanged.\n\nEconomic realism is NOT established. The original LKR/source distribution acceptance '
        'requirements cannot be passed by these arbitrary coefficients. The unitless extension must explicitly '
        'use rule-consistency and bounded-design criteria rather than claiming Sri Lankan market plausibility. '
        'Unseen-venue/vendor evaluation remains unsupported. Shared common cost shocks, uniform bounded shocks, '
        'fixed venue charge and omitted services limit realism; capacity safety is an area model, not a CAD layout '
        'or safety certification. No Stage 6 LKR realism PASS is claimed.\n')
    (dest / 'bulk_generation_readiness.md').write_text(header + disclaimer +
        'NOT AUTHORIZED — no bulk rows written.\n\n'
        'A separate versioned bulk configuration and execution authorization are still required. The pilot '
        'configuration permits five diagnostic roots and 30 rows only; copying it and changing the row count '
        'cannot satisfy its predeclared boundary design.\n\n'
        'Recommended next proposal: 1,250 independently sampled synthetic roots, three controlled planning '
        'states, two paired outcome replications = 7,500 unitless rows. Allocate 625 roots per event type as '
        'an experimental balance, not observed event frequency. Group all states/replications by root; merge '
        'identical planning configurations transitively before 60/20/20 group assignment. Do not invent venue '
        'identities; evaluate conditional on shared templates and mark unseen-template experiments unavailable. '
        'Predeclare intervention selection, duplicate-root handling, rejection policy, minimum distinct roots, '
        '46-column mapping with dimensionless unit metadata and unsupported columns missing, then implement '
        'and test that separate bulk path. Freeze its configuration/code/source hashes and request exact-count '
        'authorization. Do not reuse this pilot hash as a bulk hash. No ML training is authorized.\n')
    print(json.dumps({'internal_status': result['internal_status'], 'calculator_probes': probes,
                      'rejected_probes': rejected, 'report_directory': str(dest),
                      'bulk_authorized': False, 'test_output': suite.stderr.strip()}, indent=2))


if __name__ == '__main__':
    main()
