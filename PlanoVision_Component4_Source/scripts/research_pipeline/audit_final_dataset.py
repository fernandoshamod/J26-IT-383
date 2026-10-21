"""Stage 10 audit and checksummed NOT READY evidence package; no data generation."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.final_dataset_audit import audit, read_table, sha, chronological_audit


def verify_archive(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate_zip_entries')
        manifest = json.loads(z.read('checksums.json'))
        if set(names) != set(manifest['files']) | {'checksums.json'}:
            raise ValueError('archive_manifest_membership_mismatch')
        for name, expected in manifest['files'].items():
            h = hashlib.sha256()
            with z.open(name) as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            if h.hexdigest() != expected['sha256'] or z.getinfo(name).file_size != expected['bytes']:
                raise ValueError('archive_hash_or_size_mismatch:' + name)
        status = json.loads(z.read('DATASET_STATUS.json'))
        if status['dataset_status'] != 'NOT READY' or status['freeze_authorized'] is not False:
            raise ValueError('incorrect_readiness_claim')
    return {'result': 'PASS', 'entries_verified': len(manifest['files']), 'archive_sha256': sha(path),
            'archive_bytes': path.stat().st_size, 'dataset_status': 'NOT READY',
            'checksum_manifest_self_hash': 'Not self-included; external archive SHA-256 covers checksums.json'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-archive', type=Path)
    args = parser.parse_args()
    if args.verify_archive:
        print(json.dumps(verify_archive(args.verify_archive), indent=2))
        return
    destination = ROOT / 'outputs/Component4_Final_Research_Dataset_v1.0.zip'
    out = ROOT / 'reports/stage10_final_audit'
    if destination.exists() or (out / 'dataset_validation_report.json').exists():
        raise ValueError('Audit snapshot already exists; preserve it and use --verify-archive. New audits require a separately versioned destination.')
    env = dict(os.environ, TEMP=str(ROOT / 'work'), TMP=str(ROOT / 'work'))
    historical_process = subprocess.run([sys.executable, str(ROOT / 'scripts/research_pipeline/verify_historical_refinement.py'),
                                         '--package', 'data/refined/historical.v0.1-20261012'], cwd=ROOT, env=env, capture_output=True, text=True)
    if historical_process.returncode:
        raise RuntimeError('Historical source replay failed:' + historical_process.stderr)
    test_process = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                                  cwd=ROOT, env=env, capture_output=True, text=True)
    transcript = test_process.stdout + test_process.stderr
    match = re.search(r'Ran (\d+) tests? in ([0-9.]+)s', transcript)
    receipt = {'command': 'python -m unittest discover -s tests -q', 'exit_code': test_process.returncode,
               'tests_run': int(match[1]) if match else 0, 'elapsed_seconds': float(match[2]) if match else None,
               'transcript_sha256': hashlib.sha256(transcript.encode()).hexdigest()}
    report = audit(ROOT, receipt)
    refined = ROOT / 'data/refined/historical.v0.1-20261012'
    _, observations = read_table(refined / 'historical_observations.csv')
    _, splits = read_table(refined / 'chronological_partitions.proposed.csv')
    _, coverage = read_table(refined / 'series_coverage.csv')
    report['refined_historical_splits'] = chronological_audit(observations, splits)
    report['refined_historical_counts'] = {
        'observations': len(observations), 'series': len({r['series_id'] for r in observations}),
        'closed_month_observations': sum(r['closed_calendar_month'] == '1' for r in observations),
        'source_quality_review_rows': sum(r['source_quality_review'] == '1' for r in observations),
        'missing_month_positions': sum(int(r['missing_months']) for r in coverage),
    }
    # Saved workbook read-only verification: mapping cells reconcile to actual CSV.
    from openpyxl import load_workbook
    mapping = ROOT / 'reports/source_mapping.xlsx'
    header, rows = read_table(ROOT / 'reports/source_mapping.csv')
    wb = load_workbook(mapping, read_only=True, data_only=True)
    try:
        cells = list(wb['Source_Mapping'].values)
        expected = [header] + [[r[k] or None for k in header] for r in rows]
        report['source_mapping_saved_cells_match_csv'] = [list(r[:len(header)]) for r in cells] == expected
    finally:
        wb.close()
    out.mkdir(exist_ok=True)
    (out / 'test_transcript.txt').write_text(transcript, encoding='utf-8')
    (out / 'test_results.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (out / 'dataset_validation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    counts = report['counts']
    lines = ['# Stage 10 final dataset audit', '', '**NOT READY — validated version 1.0 freeze denied.**', '',
             'Audit date: 2026-10-12 (Asia/Colombo). This is an evidence snapshot, not an approved final dataset.', '',
             '## Counts', '', f'- Context-only master rows: {counts["master_context_rows"]}.',
             '- Generated financial scenarios, financial base families, synthetic variants and outcome replications: 0.',
             '- Real observed event-financial outcome records: 0.',
             '- XGBoost rows: 0; all three target class distributions unavailable, not zero-risk distributions.',
             f'- Historical observations: {counts["prophet_observations"]}; independent price/index series: {counts["prophet_individual_series"]}.',
             '- GNN graphs: 0. Financial train/validation/test group counts unavailable.',
             f'- Fresh software test results: {receipt["tests_run"]} tests; process exit code {receipt["exit_code"]}.', '',
             '## All twenty validation requirements', '', '| ID | Requirement | Result | Evidence / limit |', '|---|---|---|---|']
    for check in report['checks']:
        lines.append(f'| {check["id"]} | {check["check"]} | {check["status"]} | {check["detail"].replace("|", "/")} |')
    lines += ['', '## Missing mandatory artifacts', ''] + ['- ' + x for x in report['missing_mandatory_artifacts']]
    lines += ['', '## Existing but incomplete artifacts', ''] + ['- ' + x for x in report['incomplete_artifacts']]
    lines += ['', '## Historical branch', '', json.dumps(report['refined_historical_counts'], sort_keys=True), '',
              'Historical source/extraction hashes, observations, provenance, splits and workbook cells replayed successfully. '
              'The refined closed-month split is preferred to the legacy proposed split. Neither is a pooled real-time forecasting protocol. '
              'Source-quality flags, missing months and incomplete October observations remain explicit. Geographic context is source-register-derived; publication/vintage dates are missing.', '',
              '## Approval prerequisites', '',
              'Version 0.3 designer decision: changes requested; further details absent. All 19 qualified formula decisions and methodology review are pending. '
              'No executed Stage 5 pilot, Stage 6 validation PASS or separate bulk authorization exists. '
              'The unitless candidate hash identifies a proposal only; it is not an approved production freeze.', '',
              '## Packaging disposition', '',
              'The requested ZIP filename contains only existing source/evidence files plus real audit documents and engineering scripts. '
              'Legacy context-only/header-only/status-only artifacts are under workspace/data/final for inspection, not approved deliverables. '
              'No missing CSV/XLSX/graph has been fabricated. Every ZIP payload has a SHA-256/size entry and is reread for verification. '
              'The archive is NOT READY for financial ML experimentation. Success on synthetic data would not establish validated real-world financial prediction accuracy.']
    (out / 'dataset_validation_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    source_files = []
    for folder in ('component4', 'scripts/research_pipeline', 'tests', 'config', 'fixtures', 'data', 'reports'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.ndjson') and not path.is_relative_to(out):
                source_files.append(path)
    source_files += [ROOT / 'work/original_schema.json']
    source_files += list((ROOT / 'work/minimal_pilot_authoring').glob('*.mjs'))
    source_files += [ROOT / 'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/download_manifest.json']
    # Exclude node_modules junctions, caches, old archives and task scratch copies.
    entries = {'workspace/' + p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted(set(source_files))}
    documents = ['dataset_validation_report.md', 'dataset_validation_report.json', 'test_results.json', 'test_transcript.txt',
                 'data_leakage_audit.md', 'dataset_methodology.md', 'dataset_limitations.md', 'reproduction_instructions.md', 'requirements.txt']
    for name in documents:
        path = out / name
        if not path.exists():
            # Only real authored documents are included; no mandatory data placeholder.
            raise ValueError('Missing audit document:' + name)
        entries[name] = path.read_bytes()
    entries['DATASET_STATUS.json'] = json.dumps({'dataset_status': 'NOT READY', 'freeze_authorized': False,
                                                'validated_dataset_version': None, 'requested_version': '1.0',
                                                'missing_mandatory_artifacts': report['missing_mandatory_artifacts']}, indent=2).encode()
    entries['README.md'] = b'# NOT READY\n\nThis is a Stage 10 audit/evidence archive, not a frozen validated financial dataset.\nRead dataset_validation_report.md before using any file. workspace/data/final includes incomplete legacy artifacts, not approved financial scenarios. No model training or scenario generation was performed.\n'
    checksum_manifest = {'package_kind': 'NOT_READY_AUDIT_EVIDENCE_SNAPSHOT', 'dataset_freeze_authorized': False,
                         'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in sorted(entries.items())}}
    entries['checksums.json'] = json.dumps(checksum_manifest, indent=2).encode()
    with tempfile.TemporaryDirectory(prefix='stage10-', dir=ROOT / 'work') as temp:
        staged = Path(temp) / destination.name
        with zipfile.ZipFile(staged, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name, content in sorted(entries.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, content)
        verification = verify_archive(staged)
        os.rename(staged, destination)
    (out / 'archive_verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    (destination.with_suffix('.zip.sha256')).write_text(verification['archive_sha256'] + '  ' + destination.name + '\n')
    (out / 'checksums.json').write_text(json.dumps(checksum_manifest, indent=2) + '\n')
    print(json.dumps({'dataset_status': 'NOT READY', 'archive': str(destination), 'verification': verification,
                      'tests': receipt, 'counts': counts}, indent=2))


if __name__ == '__main__':
    main()
