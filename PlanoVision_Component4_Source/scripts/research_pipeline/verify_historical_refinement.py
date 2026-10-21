"""Verify persisted historical exports and preserve prior final artifacts."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.historical_refinement import build, read_csv, sha, verify_workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', required=True)
    args = parser.parse_args()
    package = (ROOT / args.package).resolve()
    if not package.is_relative_to((ROOT / 'data/refined').resolve()):
        raise ValueError('Only versioned historical packages may be verified')
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    checks = {}
    checks['all_export_hashes_and_sizes'] = all(sha(package / p) == r['sha256'] and
                                               (package / p).stat().st_size == r['bytes']
                                               for p, r in manifest['files'].items())
    for field in ['source_hashes', 'publisher_hashes', 'code_hashes']:
        checks[field + '_match'] = all(sha(ROOT / p) == h for p, h in manifest[field].items())
    bundle = build(ROOT, manifest['as_of'])
    comparisons = [('historical_observations.csv', 'observations'),
                   ('closed_month_observations.csv', 'closed_month_observations'),
                   ('chronological_partitions.proposed.csv', 'chronological_partitions_proposed'),
                   ('observation_provenance.csv', 'observation_provenance'),
                   ('series_coverage.csv', 'series_coverage')]
    for filename, table in comparisons:
        expected = [{k: '' if v is None else json.dumps(v, ensure_ascii=False, separators=(',', ':'))
                     if isinstance(v, (list, dict)) else str(int(v)) if isinstance(v, bool) else str(v)
                     for k, v in r.items()} for r in bundle[table]]
        checks[filename + '_replays_exactly'] = read_csv(package / filename) == expected
    checks['workbook_all_data_cells_reconcile'] = verify_workbook(package / 'historical_observations.xlsx', bundle)
    older = json.loads((ROOT / 'reports/final_dataset_manifest.candidate.json').read_text())
    preserved = older['preexisting_final_artifacts_preserved']
    checks['all_seven_prior_final_artifacts_preserved'] = (len(preserved) == 7 and all(
        sha(ROOT / p) == r['sha256'] and (ROOT / p).stat().st_size == r['bytes'] for p, r in preserved.items()))
    checks['no_model_training_claim'] = manifest['model_training_authorized'] is False
    checks['no_synthetic_scenario_claim'] = manifest['synthetic_rows_generated'] == 0
    report = {'date': manifest['as_of'], 'scope': 'Historical-track verification only; not Stage 6 or Stage 8 PASS',
              'package': str(package.relative_to(ROOT)).replace('\\', '/'),
              'manifest_sha256': sha(package / 'manifest.json'),
              'runtime': {'python': platform.python_version(),
                          'openpyxl_read_only_verification': importlib.metadata.version('openpyxl'),
                          'bundled_runtime_release': '26.1009.11318'},
              'xlsx_exporter_script_sha256': sha(ROOT / 'work/minimal_pilot_authoring/export_historical.mjs'),
              'checks': checks, 'result': 'PASS' if all(checks.values()) else 'FAIL',
              'renderer_warning': manifest['xlsx_renderer_warning']}
    (ROOT / 'reports/historical_refinement_verification.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not all(checks.values()):
        raise SystemExit('Historical verification failed')


if __name__ == '__main__':
    main()
