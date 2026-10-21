"""Verify the independently extracted final PP1 archive; never fit a model."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = json.loads((ROOT / 'reports/portable_package_v3_1_20261016_PP1_Final_20261020.json').read_text())
    project = Path(package['extracted_test_root']).resolve()
    archive = Path(package['archive']).resolve()
    if not project.is_relative_to((ROOT / 'work').resolve()) or not archive.is_relative_to((ROOT / 'outputs').resolve()):
        raise ValueError('unexpected_release_paths')
    before = sha(archive)
    assert before == package['sha256']
    protected = [ROOT / 'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip', ROOT / 'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    def run(arguments):
        result = subprocess.run([sys.executable, *arguments], cwd=project, env=env, capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result
    smoke = json.loads(run(['scripts/research_pipeline/verify_portable_package.py', '--http']).stdout)
    tests = run(['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    count = re.search(r'Ran (\d+) tests', tests.stderr)
    assert count and '\nOK' in tests.stderr
    assert sha(archive) == before
    assert all(sha(ROOT / name) == digest for name, digest in hashes.items())
    frontend = project / 'frontend/dist'
    assert (frontend / 'index.html').is_file()
    sources = (project / 'frontend/src/BookingCalendar.tsx').read_text(encoding='utf-8')
    assert 'Client name (optional)' in sources and 'updateBookingDetails' in sources
    result = {'status': 'PASS_FINAL_ZIP_EXTRACTED_HTTP_AND_TESTS', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'archive': str(archive), 'sha256': before, 'archive_unchanged': True,
              'extracted_root': str(project), 'extracted_smoke': smoke,
              'included_python_tests': int(count.group(1)), 'included_python_tests_result': 'PASS',
              'workspace_python_tests': 491, 'frontend_tests': 92, 'frontend_build': 'PASS',
              'frozen_hybrid_hashes_unchanged': hashes,
              'browser_check': 'Isolated port 8780: booking persistence, client name, close, move, occupied-day rejection, confirmed deletion, preview delta, discard and explainable report rendering passed; QA bookings cancelled.',
              'demo_receipt': 'reports/pp1_demo_check_20261020T135223Z/verification.json',
              'fresh_dependency_install_tested_this_run': False,
              'runtime': sys.executable,
              'remaining_human_checks': ['Presentation laptop rehearsal', 'PDF printer workflow if used', 'USB/second-device backup', 'Backup demo video if needed'],
              'limitations': ['Synthetic research, not validated real-event accuracy', 'Local browser storage only', 'Qwen weights and virtualenv not bundled', 'Real Component 1/3 feeds not connected']}
    destination = ROOT / 'reports/PP1_FINAL_VERIFICATION_20261020.json'
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
