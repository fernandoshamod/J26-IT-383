"""Bundle existing app and viva evidence without altering datasets or model files."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

ROOT=Path(__file__).resolve().parents[2]
APP='outputs/PlanoVision_Component4_VSCode_v3.1_20261016_Complete_Ready.zip'
APP_SHA='e81e58010ad24cd1c8a83725fc6425154a8fcb0fda36702ddf6f5c63b87ecd8c'


def main():
    destination=ROOT/'outputs/PlanoVision_PP1_Offline_Backup_20261017.zip'
    if destination.exists():raise ValueError('refuse_to_overwrite_existing_backup')
    experiment='reports/experiments/v3.1/expense_risk_v3_1_20261016/'
    diagnostic='reports/diagnostics/v3_1_steps1_2_20261016/'
    robustness='reports/robustness/v3_1_frozen_robustness_20261016/'
    names=[APP,'reports/PP1_DEMO_TEST_GUIDE.md','reports/PP1_VIVA_QA_NOTES.md',
           'reports/PP1_FINAL_READINESS_CHECKLIST.md','reports/final_demo_acceptance_20261016.json',
           'reports/public_hotel_benchmark_test_results.json','reports/model_evidence_lab_20261016.jpg',
           experiment+'README.md',experiment+'experiment_summary.json',
           experiment+'independent_verification.json',experiment+'confusion_matrices_browser.jpg',
           diagnostic+'error_audit.md',diagnostic+'learning_curve_report.md',diagnostic+'learning_curves.png',
           robustness+'robustness_report.md',robustness+'regime_performance.png',
           robustness+'independent_verification.json']
    payload={name:(ROOT/name).read_bytes() for name in names}
    digests={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}
    assert digests[APP]==APP_SHA,'app_archive_changed'
    with zipfile.ZipFile(io.BytesIO(payload[APP])) as app:
        assert app.testzip() is None
        manifest=json.loads(app.read('PlanoVision_Component4/PACKAGE_MANIFEST.json'))
        for name,record in manifest['files'].items():
            assert hashlib.sha256(app.read('PlanoVision_Component4/'+name)).hexdigest()==record['sha256']
    readme='''# PlanoVision PP1 offline backup — 17 October 2026

This is an outer backup pack, not a replacement app build. Extract it first.

1. Inside outputs/, extract the included Complete_Ready app ZIP into a new folder.
2. Run its START_PLANOVISION.cmd. Python 3.12 x64 and initial internet setup are
   required; keep the server console open.
3. Follow reports/PP1_DEMO_TEST_GUIDE.md and PP1_VIVA_QA_NOTES.md.
4. Tick PP1_FINAL_READINESS_CHECKLIST.md after real laptop rehearsal.

The app ZIP is byte-identical to the existing verified delivery. This backup
adds notes and selected actual evidence; it does not retrain or modify data.
No slides or demo video are included. This is not the full historical research
archive: the large original hybrid release and unrelated experimental runtimes
are intentionally not duplicated here. Required current-app artifacts are inside
the included app ZIP. Recorded test runs describe software, not real-world accuracy.
'''
    payload['START_HERE.md']=readme.encode('utf-8')
    manifest={'created_local_date':'2026-10-17','timezone':'Asia/Colombo',
              'scope':'existing verified app plus demo notes and selected evidence; no slides/video',
              'app_sha256':APP_SHA,'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),
              'bytes':len(data)} for name,data in payload.items()},'self_hash_excluded':True}
    payload['BACKUP_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in payload.items():archive.writestr('PlanoVision_PP1_Backup/'+name,data)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for name,data in payload.items():assert archive.read('PlanoVision_PP1_Backup/'+name)==data
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in digests.items())
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    result={'status':'PASS','archive':str(destination),'sha256':digest,'files':len(payload),
            'bytes':destination.stat().st_size,'app_unchanged':True,'all_source_files_unchanged':True,
            'manual_rehearsal':'NOT_RECORDED','video':'NOT_CREATED','models_retrained':False}
    (ROOT/'reports/pp1_offline_backup_verification_20261017.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
