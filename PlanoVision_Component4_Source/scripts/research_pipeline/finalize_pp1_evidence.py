"""Run focused tests, protect existing artifacts and package PP1 evidence."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.release_input import sha256


def main():
    folder=ROOT/'reports/pp1_readiness_20261015'
    destination=ROOT/'outputs/Component4_PP1_Evidence_Pack_20261015.zip'
    if destination.exists() or (folder/'test_receipt.json').exists():raise ValueError('refuse_existing_finalization')
    protected=json.loads((ROOT/'reports/experiments/v2.0/lkr_research_v2_0_20261014/completion_checksums.json').read_text())['files']
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('protected_training_artifact_changed')
    suite=unittest.TestSuite()
    for pattern in ('test_pp1_evidence.py','test_lkr_inference.py','test_lkr_research.py'):
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
             'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
             'completed_at_utc':datetime.now(timezone.utc).isoformat(),
             'scope':'5 PP1 demo/packet tests plus 24 existing LKR tests; not the complete suite',
             'latest_prior_full_suite_tests':360,'models_retrained':False,
             'datasets_rewritten':False,'planner_feedback_collected':False}
    (folder/'test_receipt.json').write_text(json.dumps(receipt,indent=2))
    if not result.wasSuccessful():raise ValueError('focused_tests_failed')
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('protected_artifact_changed_after_tests')
    files=[p for p in folder.rglob('*') if p.is_file()]
    files.extend(ROOT/name for name in ('config/pp1_demo_cases.v1.0.json','scripts/research_pipeline/build_pp1_evidence.py',
                                        'scripts/research_pipeline/finalize_pp1_evidence.py','tests/test_pp1_evidence.py','Run_PP1_Demo.cmd'))
    manifest={'package':'Component4_PP1_Evidence_Pack_20261015','files':{p.relative_to(ROOT).as_posix():sha256(p) for p in files},
              'kind':'research_presentation_evidence_not_new_training_data','protected_artifacts_unchanged':True}
    (folder/'package_manifest.json').write_text(json.dumps(manifest,indent=2))
    files.append(folder/'package_manifest.json')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:raise ValueError('evidence_zip_crc_failed')
        import hashlib
        for name,digest in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('evidence_zip_hash_failed')
    print(json.dumps({'status':'PASS','focused_tests':result.testsRun,'zip':str(destination),
                      'zip_sha256':sha256(destination),'protected_artifacts_unchanged':True},indent=2))


if __name__=='__main__':main()
