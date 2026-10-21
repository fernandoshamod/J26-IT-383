"""Package existing immutable data and successful saved experiments; no fitting."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from component4.release_input import verified_release, sha256

RUNS=[('v1.0','financial_risk_v0_1_20261012'),('v1.0','graph_risk_v0_1_20261012'),
      ('v1.0','prophet_historical_v0_1_native_20261012'),
      ('v1.1','financial_risk_v1_1_20261012'),('v1.1','graph_risk_v1_1_20261012'),
      ('v1.1','financial_shap_v1_1_memory_20261012'),('v1.1','prophet_rolling_v1_1_20261012')]

README="""# Component 4 — datasets and trained models

Existing research outputs packaged without retraining or data changes.

## Contents

- dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip:
  the complete original hybrid dataset archive, including source/provenance,
  CSV/XLSX tables, historical series, synthetic graphs and original splits.
- Current v1.1 XGBoost models, three GAT checkpoints and preprocessing scaler;
  original v1.0 financial/graph runs retained as historical experiments.
- Twelve fixed-origin Prophet models plus rolling-origin experiment artifacts.
- Saved predictions, metrics, explanations, protocols and per-run requirements.
- v1.1 split overlay, current Python source, model scripts, tests and API contracts.
- Research evaluation and dataset-readiness reports.

## Extract and use (Windows)

1. Extract this outer ZIP into a new folder; do not overwrite the existing project.
2. Keep the nested dataset ZIP in dataset_releases/v1.0 unchanged. Current
   inference/training helpers read it directly; no dataset regeneration is needed.
3. To browse the data, extract a COPY of the nested ZIP into a separate folder.
   Its prepared/ and data/ folders contain financial, historical and graph tables.
4. If running the full existing test launcher, copy that same nested ZIP to
   outputs/Component4_Hybrid_Dataset_Final_v1.0.zip; do not rebuild it.
5. Mark the release ZIP read-only in Windows file properties before using the
   verified_release guard. Read-only attributes do not survive ZIP extraction.
6. Create a Python 3.12 environment. Consult each saved run's requirements.txt
   and protocol for its exact runtime; no virtual environment or installed
   dependencies are included. Native Prophet/CmdStan setup may be required.
7. Read reports/research_evaluation_20261013.md first. Existing saved models can
   be loaded without rerunning the trainer. Per-run READMEs contain reproduction
   commands, which are OPTIONAL and require new run IDs to preserve results.

XGBoost native JSON: use Booster.load_model(bytearray(path.read_bytes())).
Prophet JSON: prophet.serialize.model_from_json(path.read_text()).
GAT: use component4/graph_experiment.py, model_metadata.json and training_scaler.npz
with the recorded architecture. Never load untrusted joblib/pickle/checkpoints.
Absolute paths in preserved protocols describe the original execution location;
adjust invocation paths after extraction, not historical evidence or data files.

## Counts and limitations

7,500 unitless synthetic scenarios, 1,250 roots, 1,900 genuine historical
measurements, 563 monthly forecasting records in 12 series, 7,500 synthetic graphs.
Monthly aggregates reuse weekly data. Zero observed completed-event outcomes.
The original split is 4,500/1,500/1,500; current v1.1 overlay is 4,506/1,494/1,500.
Vendor anomaly is a prior negative control, not a successful predictor. Designed
graph benefit is not established. Hypothetical coefficients are not LKR rates;
19 formulas lack independent domain validation. Synthetic test accuracy does not
demonstrate real-world Sri Lankan financial prediction accuracy.

PACKAGE_MANIFEST.json hashes every included source file. The nested archive's
own manifest preserves all original dataset checksums. Failed/incomplete experiment
runs, virtual environments, caches and temporary files are deliberately excluded.
"""


def main():
    archive,release=verified_release()
    destination=ROOT/'outputs/Component4_Datasets_and_Trained_Models_20261014.zip'
    if destination.exists():raise ValueError('package_already_exists_do_not_overwrite')
    inputs={}
    def add(path):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.tmp'):
            inputs[path.relative_to(ROOT).as_posix()]=path
    add(archive)
    for name in ('RELEASE_MANIFEST.json','README.md','CHECKSUMS.sha256'):
        add(archive.parent/name)
    for version,run in RUNS:
        for section in ('outputs','reports'):
            folder=ROOT/section/'experiments'/version/run
            if not folder.is_dir():raise ValueError('missing_successful_run:'+str(folder))
            for file in folder.rglob('*'):add(file)
        inventory=ROOT/'reports/experiments'/version/run/'checksums.sha256'
        for line in inventory.read_text().splitlines():
            digest,name=line.split('  ',1)
            if sha256(ROOT/name)!=digest:raise ValueError('experiment_checksum_mismatch:'+name)
    for folder in ('component4','scripts/model_experiments','scripts/research_pipeline','api/contracts',
                   'tests','config','data/experiments/v1.1/split_integrity_derivative',
                   'reports/model_stage_final_20261012','reports/experimental_indicators_20261012',
                   'reports/unitless_decision_integration_20261012'):
        for file in (ROOT/folder).rglob('*'):add(file)
    for name in ('reports/research_evaluation_20261013.md','reports/prediction_target_dataset_readiness_20261012.md',
                 'fixtures/quote_invoice.mock_test_only.json','fixtures/config.mock_test_only.json'):
        add(ROOT/name)
    hashes={name:sha256(path) for name,path in sorted(inputs.items())}
    manifest={'package_version':'1.0','packaged_date_local':'2026-10-14','timezone':'Asia/Colombo',
              'scope':'existing_research_datasets_and_saved_models_no_retraining',
              'record_counts':release['record_counts'],'runs_included':RUNS,
              'dataset_archive_sha256':release['release_archive']['sha256'],
              'files':hashes,'limitations':release['known_limitations']}
    # Exclusive creation: incomplete output remains clearly labelled until validation succeeds.
    temporary=destination.with_suffix('.zip.partial')
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as target:
        for name,path in sorted(inputs.items()):
            target.write(path,name,compress_type=zipfile.ZIP_STORED if path.suffix=='.zip' else zipfile.ZIP_DEFLATED)
        target.writestr('README_DOWNLOAD.md',README)
        target.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(temporary) as check:
        if check.testzip() is not None:raise ValueError('package_crc_failed')
        for name,digest in hashes.items():
            h=hashlib.sha256()
            with check.open(name) as source:
                for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=digest:raise ValueError('packaged_content_mismatch:'+name)
    if any(sha256(path)!=hashes[name] for name,path in inputs.items()):raise ValueError('input_changed_during_package')
    if sha256(ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip')!=release['release_archive']['sha256']:
        raise ValueError('original_dataset_archive_changed')
    temporary.rename(destination)
    result={'status':'PASS','path':str(destination),'size_bytes':destination.stat().st_size,
            'sha256':sha256(destination),'files':len(inputs)+2,'source_files_unchanged':True,
            'crc_and_payload_hashes':'PASS','models_trained':False,'datasets_generated':False}
    (ROOT/'reports/dataset_models_download_package_20261014.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
