"""Create JSON split overlays from checksum-verified frozen archive only."""
import csv
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.release_input import verified_release, sha256, assert_experiment_output
from component4.split_derivative import create_overlay, validate_overlay
import hashlib


def main():
    archive, release = verified_release()
    original = ROOT / release['original_archive']['project_relative_path']
    before = {str(p.relative_to(ROOT)): sha256(p) for p in (archive, original)}
    if before[str(original.relative_to(ROOT))] != release['original_archive']['sha256']:
        raise ValueError('original_archive_checksum_mismatch')
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read('package_manifest.json'))
        names = ['prepared/xgboost/xgboost_risk_dataset.csv', 'prepared/xgboost/grouped_split_manifest.csv',
                 'prepared/xgboost/feature_specification.json', 'prepared/spatial_financial_graphs/graph_index.csv']
        payload = {n: package.read(n) for n in names}
        for name, data in payload.items():
            if hashlib.sha256(data).hexdigest() != manifest['files'][name]:
                raise ValueError('source_payload_checksum_mismatch:' + name)
    def parse(name):
        return list(csv.DictReader(io.StringIO(payload[name].decode('utf-8-sig'))))
    rows, ancestry = parse(names[0]), parse(names[1])
    overlay = create_overlay(rows, json.loads(payload[names[2]]), ancestry)
    validation = validate_overlay(rows, overlay)
    graph_rows = parse(names[3])
    graph_lookup = {r['graph_id']: r for r in graph_rows}
    if len(graph_lookup) != len(graph_rows) or set(graph_lookup) != {r['Scenario_ID'] for r in rows}:
        raise ValueError('graph_identity_mismatch')
    for r in rows:
        if any(graph_lookup[r['Scenario_ID']][k] != r[k] for k in ('Base_Event_ID', 'split', 'split_group_id', 'configuration_sha256')):
            raise ValueError('graph_source_split_mismatch')
    after = {str(p.relative_to(ROOT)): sha256(p) for p in (archive, original)}
    if before != after:
        raise ValueError('immutable_archive_changed')
    overlay['source_archive_sha256'] = release['release_archive']['sha256']
    overlay['source_payload_checksums'] = {n: manifest['files'][n] for n in names}
    overlay['generator_code_sha256'] = {str(p.relative_to(ROOT)): sha256(p) for p in (Path(__file__), ROOT / 'component4/split_derivative.py')}
    overlay['graph_assignment_policy'] = 'Join by Scenario_ID == graph_id; same overlay for all graph tables. Original graph tables remain unchanged.'
    output = assert_experiment_output(ROOT / 'data/experiments/v1.1/split_integrity_derivative')
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'split_manifest.v1.1.json'
    path.write_text(json.dumps(overlay, indent=2), encoding='utf-8')
    saved = json.loads(path.read_text())
    if validate_overlay(rows, saved) != validation:
        raise ValueError('saved_overlay_validation_mismatch')
    report = {'validation': validation, 'overlay_path': str(path), 'overlay_sha256': sha256(path),
              'original_and_frozen_archives_unchanged': before == after, 'source_hashes': before,
              'graph_scenario_split_alignment': True, 'models_trained': False, 'scenarios_generated': 0,
              'historical_values_modified': False, 'ready_for_new_training': False,
              'remaining': ['historical quality flags require source review', 'pre-existing test exposure must be disclosed',
                            'shared-template evaluation only; no real event outcomes', 'no independent formula validation']}
    reports = assert_experiment_output(ROOT / 'reports/dataset_quality_audit_20261012')
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'split_derivative_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
