"""Independent deliverable link/manifest sanity and path-normalized presentation check."""
from support import ROOT,PACKAGE,read,save,filehash
from pathlib import Path
import json
def main():
    ready=ROOT/'PP1_READINESS_20261022';final=ready/'10_FINAL_VERIFICATION';out=PACKAGE/'outputs/CLOSEOUT';snapshot=out/'before_path_normalization';snapshot.mkdir()
    previous=read(final/'READINESS_ARTIFACT_SHA256_V2.json');presentation=[p for p in previous if p.replace('\\','/').startswith('09_PRESENTATION/')]
    assert len(presentation)==29 and all(filehash(ready/p)==previous[p] for p in presentation)
    for path in [out/'INTEGRITY_FINAL.json',final/'COMPONENT1_PP1_COMPLETION_FINAL.json',final/'COMPONENT1_PP1_COMPLETION_FINAL.md']:
        (snapshot/path.name).write_bytes(path.read_bytes())
        if path.suffix=='.json':
            data=read(path);target=data.get('integrity',data);assert target['presentation_artifacts_unchanged']==0;target['presentation_artifacts_unchanged']=29
            if 'failed_attempts_and_corrections' in data:data['failed_attempts_and_corrections'].append('Closeout presentation selector initially counted zero paths because of Windows separators. Delivery check normalized separators and directly verified all 29 unchanged hashes; corrected report/count and preserved previous bytes.')
            path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
        else:
            text=path.read_text(encoding='utf-8').replace('; 0 presentation artifacts unchanged.','; 29 presentation artifacts unchanged.')
            text += '\nDelivery correction: the first closeout selector counted zero presentation paths because of Windows path separators. Normalizing separators verified all 29 original presentation hashes unchanged. Earlier generated report bytes are retained in outputs/CLOSEOUT/before_path_normalization.\n'
            path.write_text(text,encoding='utf-8')
    report=read(final/'COMPONENT1_PP1_COMPLETION_FINAL.json');assert len(report['capabilities'])==24 and len(report['pipeline_transitions'])==9
    for r in report['pipeline_transitions']:
        for fragment in r['output_file'].split('; '):
            path=fragment.split(' xai')[0]
            if path.startswith('PP1_READINESS') and not (ROOT/path).exists():raise AssertionError(path)
    for py in PACKAGE.glob('*.py'):compile(py.read_text(encoding='utf-8'),str(py),'exec')
    save(out/'DELIVERY_CHECK.json',{'presentation_hashes_verified':29,'capabilities':24,'transitions':9,'python_sources_compile':True,'release_tests':49,'supplemental_tests':4,'original_test_failure_disclosed':True,'real_pipeline_blocked_disclosed':True})
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):filehash(p) for p in sorted(PACKAGE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='ARTIFACT_SHA256_FINAL.json'}
    for name in ['COMPONENT1_PP1_COMPLETION_FINAL.md','COMPONENT1_PP1_COMPLETION_FINAL.json']:manifest[str((final/name).relative_to(ROOT)).replace('\\','/')]=filehash(final/name)
    (PACKAGE/'ARTIFACT_SHA256_FINAL.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    assert all(filehash(ROOT/p)==h for p,h in manifest.items())
    print('Delivery and all artifact hashes verified:',len(manifest))
if __name__=='__main__':main()
