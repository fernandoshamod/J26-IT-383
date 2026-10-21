from usability_env import *
from search import solve
from verify import validate,routes
import argparse

def setup():
    preserve_before()
    cases=[]
    base=PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1/data_v3/venue_1/CASE.json'
    old=PP1/'PP1_FINAL_PANEL_RESOLUTION_V1/08_RAW_BENCHMARKS/accessibility'
    for name,path in [('open',base),('barrier',old/'20261019_gap_0/CASE.json'),('narrow',old/'20261020_gap_0.4/CASE.json')]:
        c=read(path);jc.admit(c)
        # Source-qualified existing fixture seed, not an optimizer outcome.
        ref=jc.export_layout(c['seed_design'],c);assert composed(c,ref)['valid']
        cases.append(dict(name=name,case=c,reference=ref,revision=revision(c,ref)))
    save(H/'INPUT_MANIFEST.json',dict(cases=cases,seeds=[20261019,20261020],methods=METHODS,population=40,budget=240,returned_menu_limit=4,radius_m=RADIUS,grid_step_m=STEP,origin_m=ORIGIN,repair_max_trials=16,scope='Three related controlled geometries; two seeds; no human/generalization inference',hypotheses=['Access constraints can reject locally feasible disconnected functions','NEW function-labelled component repair is compared with conventional B2 using identical primitives; equivalence refutes exclusivity','Removing repair may reduce feasible access returns at equal objective-evaluation budget'],endpoint='Count independently certified candidates among first four actual finite nondominated returns; separate from any returned/potential feasible evaluation count'))
    print('Setup and before-hashes saved',flush=True)

def smoke():
    c=read(H/'INPUT_MANIFEST.json')['cases'][0]['case']
    l=jc.export_layout(c['seed_design'],c);start=time.perf_counter();v=validate(c,l)
    save(H/'SMOKE.json',dict(result=v,elapsed_s=time.perf_counter()-start));print('Smoke',v['valid'],v['runtime_s'],flush=True)
    assert v['valid'],v

def benchmark():
    manifest=read(H/'INPUT_MANIFEST.json');out=H/'raw';out.mkdir(exist_ok=False)
    db=sqlite3.connect(H/'results.sqlite3');db.execute('create table results (id text primary key, case_json text, result_json text, verification_json text, sha256 text)');rows=[]
    for entry in manifest['cases']:
      for seed in manifest['seeds']:
       for phase in ['initial','revision']:
        c=entry['case'] if phase=='initial' else entry['revision'];ref=None if phase=='initial' else entry['reference']
        for method in manifest['methods']:
            key=f"{entry['name']}_{seed}_{phase}_{method}";d=out/key;d.mkdir()
            save(d/'CASE.json',c)
            if ref:save(d/'REFERENCE.json',ref)
            result=solve(c,method,seed,ref,budget=manifest['budget'])
            save(d/'RESULT.json',result)
            checks=[validate(c,l,ref) for l in result['candidates']];save(d/'INDEPENDENT.json',checks)
            valid=[l for l,q in zip(result['candidates'],checks) if q['valid']]
            functions={f:sum(q['access'] is not None and all(t['certified'] for t in q['access']['targets'] if t['function']==f) for q in checks) for f in ['seating','stage','buffet','dance']}
            diversity=min((float(np.linalg.norm(np.array(a['decision_vector'])-np.array(b['decision_vector']))) for i,a in enumerate(valid) for b in valid[:i]),default=None)
            row=dict(id=key,geometry=entry['name'],seed=seed,phase=phase,method=method,evaluations=result['evaluations'],runtime_s=result['runtime_s'],returned=len(checks),usable=len(valid),validity_percent=100*len(valid)/len(checks) if checks else None,local_valid=sum(q['local']['valid'] for q in checks),seating_pass=functions['seating'],stage_pass=functions['stage'],buffet_pass=functions['buffet'],dance_pass=functions['dance'],best_usable_service=min((l['objectives'][0] for l in valid),default=None),best_usable_change=min((l['objectives'][1] for l in valid),default=None),minimum_menu_vector_distance=diversity,protected_violations=sum('PROTECTED' in str(q['local']['errors']) for q in checks),repair_access_queries=result['repair_access_queries'],repair_pose_trials=result['repair_pose_trials'],fitness_access_queries=result['fitness_access_queries'],result_path=str(d/'RESULT.json'))
            save(d/'ROW.json',row);rows.append(row)
            payload=json.dumps(result,sort_keys=True,allow_nan=False);checktext=json.dumps(checks,sort_keys=True,allow_nan=False)
            db.execute('insert into results values (?,?,?,?,?)',(key,json.dumps(c,sort_keys=True),payload,checktext,digest(result)));db.commit()
            assert json.loads(db.execute('select result_json from results where id=?',(key,)).fetchone()[0])==result
            print(key,'usable',len(valid),'/',len(checks),'eval',result['evaluations'],'seconds',round(result['runtime_s'],2),flush=True)
    save(H/'RAW_EXPERIMENT_RESULTS.json',rows);db.close()
    save(H/'ENVIRONMENT.json',dict(python=sys.version,flags=FLAGS,network=EVENTS,modules={m:str(sys.modules[m].__file__) for m in ['pymoo','joint_core','engine_initial','compiler','core'] if m in sys.modules}))

if __name__=='__main__':
    {'setup':setup,'smoke':smoke,'benchmark':benchmark}[sys.argv[1]]()
