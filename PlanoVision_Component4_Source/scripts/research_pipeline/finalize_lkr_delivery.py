"""Record delivery hashes after independent verification; no data/model changes."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.lkr_research import VERSION
from component4.release_input import sha256
from scripts.research_pipeline.verify_lkr_research import verify


def main():
    result=verify(VERSION)
    report=ROOT/'reports/experiments/v2.0'/VERSION
    receipt=json.loads((report/'full_suite_receipt.json').read_text())
    if receipt['full_suite_status']!='PASS' or not receipt['release_zip_files_unchanged']:
        raise ValueError('full_suite_not_passed_or_input_modified')
    files=[]
    for prefix in ('data','outputs','reports'):
        files.extend(p for p in (ROOT/prefix/'experiments/v2.0'/VERSION).rglob('*') if p.is_file())
    for name in ('config/lkr_research.v2.0.json','component4/lkr_research.py','component4/lkr_inference.py',
                 'scripts/model_experiments/train_lkr_research.py','scripts/research_pipeline/run_planner_cli_lkr.py',
                 'scripts/research_pipeline/verify_lkr_research.py','scripts/research_pipeline/finalize_lkr_delivery.py',
                 'tests/test_lkr_research.py','tests/test_lkr_inference.py','Run_LKR_Planner.cmd','README_LKR_RESEARCH.md'):
        files.append(ROOT/name)
    inventory={'status':result['status'],'tests_run':receipt['tests_run'],
               'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(set(files))}}
    destination=report/'completion_checksums.json'
    with destination.open('x',encoding='utf-8') as f:json.dump(inventory,f,indent=2)
    print(json.dumps({'status':'PASS','files_hashed':len(inventory['files']),'tests':receipt['tests_run'],
                      'completion_manifest':str(destination),'manifest_sha256':sha256(destination)},indent=2))


if __name__=='__main__':main()
