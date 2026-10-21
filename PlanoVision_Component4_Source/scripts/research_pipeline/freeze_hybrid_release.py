"""Freeze an existing validated ZIP. No dataset engineering or model execution."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.release_input import sha256, verified_release, assert_experiment_output

ORIGINAL = ROOT / 'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip'
RELEASE = ROOT / 'dataset_releases/v1.0'
EXPECTED = '5baff661b4f6b6e64425b4de2495f77bd395ee1e92dd1f0bf368b753f4e1542f'
UNPACKED = ROOT / 'data/hybrid/Component4_Hybrid_Dataset_Final_v1.0'


def zip_sha(package, name):
    digest = hashlib.sha256()
    with package.open(name) as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def count_rows(package, name):
    with package.open(name) as source:
        reader = csv.DictReader(io.TextIOWrapper(source, encoding='utf-8-sig', newline=''))
        return sum(1 for _ in reader)


def audit_original():
    before = sha256(ORIGINAL)
    if before != EXPECTED:
        raise ValueError('original_differs_from_validated_v1_archive')
    with zipfile.ZipFile(ORIGINAL, 'r') as package:
        names = package.namelist()
        if len(names) != len(set(names)) or package.testzip() is not None:
            raise ValueError('archive_duplicate_member_or_crc_failure')
        manifest = json.loads(package.read('package_manifest.json'))
        for name, expected in manifest['files'].items():
            if zip_sha(package, name) != expected:
                raise ValueError('archive_payload_checksum:' + name)
            if sha256(UNPACKED / name) != expected:
                raise ValueError('existing_dataset_file_changed:' + name)
        receipt = json.loads(package.read('reports/validation_results.json'))
        if not all(receipt['checks'].values()):
            raise ValueError('prior_validation_failure')
        tests = json.loads(package.read('reports/test_results.json'))
        if tests['exit_code'] or 'Ran 213 tests' not in tests['stderr']:
            raise ValueError('missing_prior_213_test_receipt')
        observed = {
            'synthetic_event_scenarios': count_rows(package, 'data/final/unitless-bulk-v0.1/master_event_financial_dataset.csv'),
            'direct_weekly_prices': count_rows(package, 'prepared/real/weekly_retail_observations.csv'),
            'direct_monthly_indices': count_rows(package, 'prepared/real/monthly_inflation_observations.csv'),
            'prophet_ready_records': count_rows(package, 'prepared/prophet/prophet_cost_timeseries.csv'),
            'xgboost_ready_rows': count_rows(package, 'prepared/xgboost/xgboost_risk_dataset.csv'),
            'graph_count': count_rows(package, 'prepared/spatial_financial_graphs/graph_index.csv'),
            'node_records': count_rows(package, 'prepared/spatial_financial_graphs/node_features.csv'),
            'edge_records': count_rows(package, 'prepared/spatial_financial_graphs/edges.csv'),
        }
        with package.open('prepared/xgboost/grouped_split_manifest.csv') as source:
            assignments = list(csv.DictReader(io.TextIOWrapper(source, encoding='utf-8-sig', newline='')))
        observed['synthetic_root_families'] = len({r['Base_Event_ID'] for r in assignments})
        observed['genuine_historical_measurements_selected'] = observed['direct_weekly_prices'] + observed['direct_monthly_indices']
        if any(value != manifest['statistics'][key] for key, value in observed.items()):
            raise ValueError('actual_record_counts_mismatch')
        for split, count in manifest['statistics']['split_rows'].items():
            if sum(r['split'] == split for r in assignments) != count:
                raise ValueError('split_count_mismatch')
        configuration = json.loads(package.read('data/final/unitless-bulk-v0.1/configuration.json'))
        graph = json.loads(package.read('prepared/spatial_financial_graphs/schema.json'))
        features = json.loads(package.read('prepared/xgboost/feature_specification.json'))
    if sha256(ORIGINAL) != before:
        raise ValueError('original_changed_during_audit')
    return before, manifest, configuration, graph, features


def final_check():
    archive, manifest = verified_release(RELEASE)
    original_hash, frozen_hash = sha256(ORIGINAL), sha256(archive)
    if original_hash != frozen_hash or original_hash != EXPECTED:
        raise ValueError('final_archive_integrity_failed')
    checksums = (RELEASE / 'CHECKSUMS.sha256').read_text().splitlines()
    for line in checksums:
        digest, name = line.split('  ', 1)
        if Path(name).name != name or sha256(RELEASE / name) != digest:
            raise ValueError('release_metadata_checksum:' + name)
    for name, digest in manifest['preserved_dataset_file_checksums'].items():
        if sha256(UNPACKED / name) != digest:
            raise ValueError('existing_data_changed:' + name)
    for name, digest in manifest['preserved_original_synthetic_file_checksums'].items():
        if sha256(ROOT / name) != digest:
            raise ValueError('original_synthetic_data_changed:' + name)
    with zipfile.ZipFile(archive, 'r') as package:
        if package.testzip() is not None:
            raise ValueError('frozen_archive_crc_failure')
    return {'status': 'PASS', 'frozen_release_path': str(RELEASE), 'original_zip_sha256': original_hash,
            'frozen_zip_sha256': frozen_hash, 'hashes_match': True,
            'record_counts': manifest['record_counts'], 'copied_zip_read_only': True,
            'ready_for_read_only_synthetic_ml_input': True, 'models_trained': False}


def freeze():
    if RELEASE.exists():
        raise ValueError('refuse_to_overwrite_existing_release; use --verify-only')
    original_hash, package, configuration, graph, features = audit_original()
    limits = [
        'Synthetic financial values are hypothetical dimensionless scores, not LKR quotations.',
        'Zero genuine observed complete event-financial outcomes; no real-world predictive validation.',
        '19 formulas lack independent qualified/domain review; engineering waiver is not institutional approval.',
        '1250 synthetic roots, not 7500 independent real events; original grouped splits must be preserved.',
        'Shared venue/vendor/source assumptions: conditional in-simulator evaluation only; unseen-template evaluation unsupported.',
        'Graphs use one assumed functional topology, not observed adjacency, physical CAD or identified causality.',
        'Prophet monthly price aggregates reuse weekly measurements; do not count them as extra independent observations.',
        'Keep separate price/index series and units; dates are period keys, not verified publication timestamps/vintages.',
        '159 historical measurements and 108 monthly records retain source quality-review flags.',
        '20 advertisements and 60 procurement aggregates are context only, not observed event outcomes or calibrated rates.',
        'Vendor anomaly injections are random and independent of permitted planning features; no substantive predictive signal is expected.',
    ]
    release_manifest = {
        'dataset_version': '1.0', 'release_id': 'Component4_Hybrid_Dataset_Final_v1.0',
        'status': 'FROZEN_INTERNAL_SYNTHETIC_RESEARCH_INPUT', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'original_archive': {'file_name': ORIGINAL.name, 'project_relative_path': str(ORIGINAL.relative_to(ROOT)).replace('\\', '/'), 'sha256': original_hash, 'size_bytes': ORIGINAL.stat().st_size},
        'release_archive': {'file_name': ORIGINAL.name, 'project_relative_path': str((RELEASE / ORIGINAL.name).relative_to(ROOT)).replace('\\', '/'), 'sha256': original_hash, 'size_bytes': ORIGINAL.stat().st_size},
        'metadata_files': ['RELEASE_MANIFEST.json', 'README.md', 'CHECKSUMS.sha256'],
        'record_counts': package['statistics'],
        'configuration': {'canonical_sha256': package['frozen_synthetic_configuration_sha256'],
            'bulk_version': configuration['version'], 'financial_rule_version': configuration['financial_model']['version'],
            'master_mapping_version': configuration.get('field_semantics_version'), 'graph_schema_version': graph['version'],
            'xgboost_feature_specification_version': features['version']},
        'preserved_dataset_file_checksums': package['files'],
        'preserved_original_synthetic_file_checksums': json.loads((UNPACKED / 'reports/validation_results.json').read_text())['synthetic_original_sha256'],
        'known_limitations': limits,
        'validation': {'existing_test_count': 213, 'test_suite_rerun_in_freeze_task': False,
            'original_archive_crc': 'PASS', 'archive_payload_checksums': 'PASS', 'actual_row_counts': 'PASS',
            'dataset_contents_modified': False, 'new_scenarios_generated': 0, 'models_trained': False},
        'immutability': {'windows_read_only_attribute': 'Required on copied ZIP; applied to release metadata too.',
            'attribute_limit': 'Read-only attributes are not ACL enforcement and may be cleared by an authorized user; verify checksums before and after experiments.',
            'input_guard': 'component4.release_input.verified_release', 'output_guard': 'component4.release_input.assert_experiment_output',
            'io_policy': 'config/model_experiment_io.v1.0.json', 'forbidden_write_root': 'dataset_releases',
            'new_output_roots': ['data/experiments/v1.0', 'outputs/experiments/v1.0', 'reports/experiments/v1.0']},
        'freeze_implementation_sha256': sha256(Path(__file__)),
        'input_guard_sha256': sha256(ROOT / 'component4/release_input.py'),
    }
    readme = f'''# Hybrid Dataset v1.0 — frozen release

This is an exact, byte-identical copy of the existing validated hybrid ZIP. No rows, sources, splits, labels, graphs or reports were regenerated or edited.

Archive: `{ORIGINAL.name}`

SHA-256: `{original_hash}`

## Counts and scientific scope

7500 unitless synthetic scenarios; 1250 synthetic roots; 1900 genuine historical measurements (1787 weekly prices + 113 indices); 563 monthly Prophet records in 12 separate series; 7500 XGBoost rows; 7500 synthetic dependency graphs. Zero observed complete event-financial outcomes.

XGBoost/graphs retain train/validation/test rows 4500/1500/1500, root families 750/250/250 and connected groups 711/248/248. Prophet per-series chronological partitions contain 388/87/88 observations. Historical monthly aggregates reuse the direct measurements. Never sum these counts as independent event records.

The prior verification receipt reports 213 passing tests. This freeze performs archive, payload, row-count, source-preservation and final checksum checks without redoing dataset engineering. Full versions, counts, checksums and limitations are in RELEASE_MANIFEST.json.

## Verify/reproduce the release copy (Windows)

Run from the existing project root:

```powershell
$taskPython='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $taskPython scripts/research_pipeline/freeze_hybrid_release.py --verify-only
Get-FileHash outputs/Component4_Hybrid_Dataset_Final_v1.0.zip -Algorithm SHA256
Get-FileHash dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip -Algorithm SHA256
```

To reproduce a release on a separate fresh copy of the same project, run the freeze script without --verify-only. It copies the existing original archive, verifies its recorded hash and refuses any existing release destination. Do not delete or overwrite this release to replay it. Reproducing the dataset preparation itself is documented in the ZIP's root README; it is not necessary to freeze or train from this release.

## Immutable input and future experiments

Never write inside dataset_releases (including extracted/preprocessed data, models, predictions, logs or reports). Future scripts must use this contract:

```python
from component4.release_input import verified_release, assert_experiment_output
archive, metadata = verified_release()  # verifies ZIP checksum, versions and counts
output = assert_experiment_output('outputs/experiments/v1.0/experiment_name/results.json')
# Read ZIP members directly, or extract a working copy outside dataset_releases.
# Fit preprocessing only on training; retain original group and temporal splits.
# Call verified_release() again after an experiment.
```

The canonical input/output policy is config/model_experiment_io.v1.0.json. Working data belongs in data/experiments/v1.0; models/predictions in outputs/experiments/v1.0; evaluation reports in reports/experiments/v1.0. No training scripts or models exist as part of this freeze. Arbitrary future scripts cannot be automatically constrained; integrating the guards is mandatory. Read-only file attributes are defense-in-depth, not an OS security boundary.

To audit an extracted working copy, install the ZIP's requirements and run its scripts/research_pipeline/verify_hybrid_package.py against that extraction. Extract outside this release directory and keep all transformations in an experiment workspace.

## Limitations

''' + '\n'.join('- ' + limitation for limitation in limits) + '\n'
    RELEASE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.freeze-staging-', dir=RELEASE.parent) as temporary:
        stage = Path(temporary) / 'v1.0'
        stage.mkdir()
        copied = stage / ORIGINAL.name
        shutil.copy2(ORIGINAL, copied)
        if sha256(copied) != original_hash or sha256(ORIGINAL) != original_hash:
            raise ValueError('copy_checksum_failed')
        (stage / 'README.md').write_text(readme, encoding='utf-8')
        (stage / 'RELEASE_MANIFEST.json').write_text(json.dumps(release_manifest, indent=2), encoding='utf-8')
        (stage / 'CHECKSUMS.sha256').write_text(''.join(sha256(stage / name) + '  ' + name + '\n' for name in (ORIGINAL.name, 'RELEASE_MANIFEST.json', 'README.md')), encoding='utf-8')
        os.rename(stage, RELEASE)
    for path in RELEASE.iterdir():
        path.chmod(stat.S_IREAD)
    return final_check()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(final_check() if args.verify_only else freeze(), indent=2))
