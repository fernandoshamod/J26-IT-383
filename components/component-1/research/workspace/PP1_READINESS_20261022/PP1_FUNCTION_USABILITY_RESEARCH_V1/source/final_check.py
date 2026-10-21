from usability_env import *
import csv,importlib.metadata

def main():
    before=read(H/'PRESERVATION_BEFORE.json');drift=[p for p,h in before.items() if sha(ROOT/p)!=h];assert not drift,drift
    freeze=read(PP1/'PP1_FINAL_BACKEND_FREEZE_V1/BACKEND_RUNTIME_FREEZE.json')
    pinned=[p for p,h in freeze['files'].items() if sha(ROOT/p)!=h];assert not pinned,pinned
    packages={p:importlib.metadata.version(p) for p in freeze['packages']};assert packages==freeze['packages']
    rows=read(H/'RAW_EXPERIMENT_RESULTS_FINAL.json');summary=read(H/'FINAL_SUMMARY.json')
    with (H/'RAW_EXPERIMENT_RESULTS_FINAL.csv').open(encoding='utf-8-sig',newline='') as f:csvrows=list(csv.DictReader(f))
    assert len(csvrows)==len(rows)==60
    for a,b in zip(rows,csvrows):
        for k,v in a.items():
            if type(v) in (int,float):assert math.isclose(float(v),float(b[k]),rel_tol=1e-14,abs_tol=1e-14),(a['id'],k,v,b[k])
            else:assert str('' if v is None else v)==b[k],(a['id'],k,v,b[k])
    fulltraces=0;candidatecount=0;qualified=0;db=sqlite3.connect(H/'results.sqlite3')
    for r in rows:
        res=read(r['result_path']);assert res['evaluations']==len(res['trace'])==240;fulltraces+=240
        assert digest(read(Path(r['result_path']).parent/'CASE.json'))==res['case_sha256']
        vectors=[l['objectives'] for l in res['candidates']]
        for i,a in enumerate(vectors):
            assert not any(all(x<=y+1e-9 for x,y in zip(b,a)) and any(x<y-1e-9 for x,y in zip(b,a)) for j,b in enumerate(vectors) if j!=i),'RETURNED_SET_DOMINANCE'
        q=read(H/'independent_final'/(r['id']+'.json'));assert digest(res)==q['qualification']['raw_result_sha256'];assert digest(q['checks'])==q['qualification']['checks_sha256'];assert q['qualification']['validator_source_sha256']==sha(Path(__file__).with_name('verify.py'))
        candidatecount+=len(vectors);qualified+=sum(a['valid'] for a in q['checks']);assert qualified>=0
        stored=db.execute('select qualification_json from qualified where id=?',(r['id'],)).fetchone();assert json.loads(stored[0])==q['qualification']
    assert fulltraces==14400 and candidatecount==176 and qualified==144
    assert summary['runs']==60 and all(p['new_b2_trace_candidates_equal'] and p['b1_ablation_equal'] for p in summary['pairs'])
    assert len(summary['pairs'])==12
    tests=read(H/'TEST_RESULTS_FINAL.json');assert tests['passed']==tests['count']==15
    environment=read(H/'ENVIRONMENT.json');assert not environment['network']['network'] and not environment['network']['denied_writes']
    logs=[]
    for p in sorted((H/'logs').glob('*.COMMAND.json')):logs.append(dict(path=str(p.relative_to(H)),**read(p)))
    expectedfail={'SETUP_001.COMMAND.json','SETUP_002.COMMAND.json','FINAL_CHECK_001.COMMAND.json'}
    assert {Path(r['path']).name for r in logs if r['exit']!=0}==expectedfail
    outputs={str(p.relative_to(H)):sha(p) for p in H.glob('*.md')}
    outputs.update({str(p.relative_to(H)):sha(p) for p in (H/'source').glob('*.py')})
    outputs.update({str(p.relative_to(H)):sha(p) for p in (H/'figures').glob('*.png')})
    report=dict(status='PASS',previous_files_checked=len(before),previous_files_unchanged=len(before)-len(drift),frozen_runtime_files=len(freeze['files']),frozen_files_unchanged=len(freeze['files'])-len(pinned),installed_package_versions=packages,original_datasets_moved_deleted_or_retrained=False,coverage='Bounded recorded dependency/evidence hash set, not a full raw-dataset/whole-project audit',all_new_outputs_root=str(H),network_instrumentation='Python audit hooks; not full OS isolation',network_attempts=environment['network']['network'],denied_writes=environment['network']['denied_writes'],master_plan_sha256=sha(next(ROOT.glob('Component 1 *Updated Full Research.txt'))))
    save(H/'PRESERVATION_REPORT.json',report)
    save(H/'FINAL_ACCEPTANCE.json',dict(status='PASS',search_invocations=60,runs_with_certified_layout=36,actual_evaluations=14400,reported_candidates=176,independently_certified_candidates=144,tests=15,functional_admission_cases=13,mutation_controls=2,paired_b2_new_equal=12,paired_b1_ablation_equal=12,sqlite_raw_rows=60,sqlite_qualification_rows=60,csv_rows=60,finite_returned_set_nondominance_checked=True,outputs_sha256=outputs,commands=logs,additional_searches_during_replay=0,novelty='NOT_ESTABLISHED',application_originality='UNRESOLVED',stop_new_algorithm_work=True))
    print('Final independent readback/denominators/Pareto/CSV/freeze PASS;',len(before),'previous files unchanged;',len(freeze['files']),'frozen files;',len(packages),'package versions',flush=True)

if __name__=='__main__':main()
