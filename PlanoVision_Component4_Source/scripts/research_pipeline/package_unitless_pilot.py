"""Package existing verified user-authorized pilot, not a final dataset freeze."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / 'data/pilot/unitless-v0.3-user-authorized-20261012'
REPORTS = ROOT / 'reports/unitless_pilot_execution_20261012'


def main():
    result = json.loads((REPORTS / 'pilot_validation_report.json').read_text())
    if result['status'] != 'PASS' or not all(result['checks'].values()):
        raise ValueError('Pilot validation not PASS')
    target = ROOT / 'outputs/Component4_Unitless_Diagnostic_Pilot_30_UserAuthorized.zip'
    if target.exists():
        raise ValueError('Existing pilot package preserved')
    files = [p for p in PILOT.iterdir() if p.is_file() and p.suffix != '.ndjson']
    files += [p for p in REPORTS.iterdir() if p.is_file()]
    files += [ROOT / 'config/unitless_pilot_authorization.v0.3.user.json',
              ROOT / 'reports/unitless_pilot_user_authorization_evidence.json',
              ROOT / 'scripts/research_pipeline/execute_user_authorized_unitless_pilot.py',
              ROOT / 'scripts/research_pipeline/finalize_unitless_pilot_presentation.py',
              ROOT / 'scripts/research_pipeline/package_unitless_pilot.py',
              ROOT / 'work/minimal_pilot_authoring/inspect_authorized_pilot.mjs',
              ROOT / 'work/pilot_visual_qa_20261012/unitless_dataset.original_export.xlsx']
    manifest = json.loads((PILOT / 'manifest.json').read_text())
    files += [ROOT / name for name in manifest['code_sha256']]
    entries = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted(set(files))}
    entries['README.md'] = (REPORTS / 'README.md').read_bytes()
    checksums = {name: {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)} for name, content in entries.items()}
    entries['checksums.json'] = json.dumps({'kind': 'USER_AUTHORIZED_UNITLESS_DIAGNOSTIC_PILOT_ONLY',
        'qualified_review_performed': False, 'realism_validated': False, 'final_dataset_ready': False,
        'files': checksums}, indent=2).encode()
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(entries.items()):
            z.writestr(name, content)
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == set(entries)
        for name, meta in checksums.items():
            content = z.read(name)
            assert hashlib.sha256(content).hexdigest() == meta['sha256'] and len(content) == meta['bytes'], name
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest + '  ' + target.name + '\n')
    print(json.dumps({'pilot_archive': str(target), 'archive_sha256': digest, 'entries_verified': len(entries),
                      'rows': 30, 'internal_validation': 'PASS', 'qualified_review_performed': False,
                      'final_dataset_ready': False}))


if __name__ == '__main__':
    main()
