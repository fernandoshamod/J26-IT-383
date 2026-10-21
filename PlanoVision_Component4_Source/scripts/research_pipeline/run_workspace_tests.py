"""Run all existing tests with an explicitly writable workspace temp root.

Windows sandbox temp folders can loop on denied nested directory creation.
This launcher changes only the test process's tempfile location, not rules,
approvals, dataset values or test expectations.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    temporary_root = ROOT / 'work/test_runtime_temp'
    temporary_root.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(temporary_root.resolve())
    zip_paths = [ROOT / 'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip',
                 ROOT / 'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip']
    def digests():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in zip_paths}
    before = digests()
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = digests()
    unchanged = before == after
    summary = {
        'started_at_utc': started,
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds': round(time.monotonic() - timer, 3),
        'python_executable': sys.executable,
        'python_version': sys.version,
        'test_temp_root': str(temporary_root),
        'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped),
        'expected_failures': len(result.expectedFailures),
        'unexpected_successes': len(result.unexpectedSuccesses),
        'full_suite_status': 'PASS' if result.wasSuccessful() else 'FAIL',
        'release_zip_files_unchanged': unchanged,
        'release_zip_sha256_before': before, 'release_zip_sha256_after': after,
        'failure_details': [{'test': str(test), 'traceback': tb} for test, tb in result.failures + result.errors],
        'scope': 'Software verification only; no claim of empirical economic realism or real-world prediction accuracy',
    }
    report = ROOT / 'reports/public_hotel_benchmark_test_results.json'
    report.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
