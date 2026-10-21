"""Execute active legacy regression suites without historical-output writes."""
import sys,types,tempfile,contextlib,subprocess,json
from support import ROOT,PACKAGE,save,filehash
CORE=ROOT/'PP1_STAGE_E_RESEARCH_CORE';V2=ROOT/'PP1_STAGE_E_EVENT_LAYOUT_V2/backend';POC=ROOT/'PP1_STAGE_E_CONTROLLED_POC_V1'
CASES={
 'B1':CORE/'backend/test_stage_e_api_v1.py',
 'B2':CORE/'backend/test_stage_e_api_v2.py',
 'F2C':CORE/'research/f2c_live_engine_tests_v1.py',
 'StageD':V2/'test_spatial_twin_gate_v1.py',
 'PermissionV1':POC/'tests/test_permission_authorization.py',
 'PermissionV2':POC/'tests/test_permission_v2.py',
 'MultiObjectReplay':POC/'tests/verify_multi_nsga2_results_v1.py',
 'XAIV1':ROOT/'PP1_READINESS_20261022/05_XAI/test_xai_v1.py'}
def one(name,out):
    sys.path[:0]=[str(CORE/'research'),str(CORE/'backend'),str(V2),str(ROOT/'PP1_READINESS_20261022/05_XAI')]
    tempfile.tempdir=str(out/'TEMP');(out/'TEMP').mkdir(exist_ok=True)
    if name=='B2':
        p=CORE/'backend/stage_e_api_v2.py';text=p.read_text();assert text.count('app = create_app()')==1;m=types.ModuleType('stage_e_api_v2');m.__file__=str(p);exec(compile(text.replace('app = create_app()','',1),str(p),'exec'),m.__dict__);sys.modules['stage_e_api_v2']=m
    path=CASES[name];source=path.read_text()
    if name=='F2C':source=source.replace('DEST = OUT / "f2c_live_engine_tests_v1.json"','DEST = Path('+repr(str(out/'F2C_REEXECUTED.json'))+')')
    sys.argv=[str(path)]
    if name=='XAIV1':
        import runpy
        runpy.run_path(str(path),run_name='__main__');return
    exec(compile(source,str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
def main():
    if len(sys.argv)>1:
        one(sys.argv[1],PACKAGE/'outputs/REGRESSION');return
    out=PACKAGE/'outputs/REGRESSION';out.mkdir(parents=True);records=[]
    for name,path in CASES.items():
        command=[sys.executable,'-B',str(PACKAGE/'regression_old.py'),name]
        with (out/(name+'.log')).open('x',encoding='utf-8') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,text=True)
        records.append(dict(case=name,source=str(path.relative_to(ROOT)),source_sha256=filehash(path),command=command,exit_code=r.returncode,adaptation='Only suppress original default DB instantiation for B2; isolate TEMP. Redirect F2C report destination only. Other suite statements unchanged.'))
        print(name,r.returncode,flush=True)
    # Archived snapshots are listed as archives, not silently counted as tests.
    archives=[str(p.relative_to(ROOT)) for p in POC.rglob('test*.py') if 'tests' in p.parts and p not in CASES.values()]
    save(out/'REGRESSION_RESULTS.json',{'active_suites':records,'all_pass':all(r['exit_code']==0 for r in records),'archived_snapshot_scripts_not_active_suites':archives})
    if any(r['exit_code'] for r in records):raise SystemExit(1)
if __name__=='__main__':main()
