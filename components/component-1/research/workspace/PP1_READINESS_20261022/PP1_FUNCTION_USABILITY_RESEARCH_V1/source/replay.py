from usability_env import *
from verify import validate,routes
import statistics,itertools

def main():
    out=H/'independent_final';out.mkdir(exist_ok=False)
    rows=read(H/'RAW_EXPERIMENT_RESULTS.json');final=[];pairs=[];changed=[]
    db=sqlite3.connect(H/'results.sqlite3')
    db.execute('create table qualified (id text primary key, qualification_json text, sha256 text)')
    for row in rows:
        p=Path(row['result_path']);folder=p.parent;c=read(folder/'CASE.json');result=read(p);ref=read(folder/'REFERENCE.json') if (folder/'REFERENCE.json').exists() else None
        stored=db.execute('select case_json,result_json,verification_json,sha256 from results where id=?',(row['id'],)).fetchone()
        assert json.loads(stored[0])==c and json.loads(stored[1])==result and stored[3]==digest(result)
        checks=[validate(c,l,ref) for l in result['candidates']]
        old=read(folder/'INDEPENDENT.json')
        valid=[l for l,q in zip(result['candidates'],checks) if q['valid']]
        for i,(before,after) in enumerate(zip(old,checks)):
            if before['valid']!=after['valid']:changed.append(dict(run=row['id'],index=i,before=before['valid'],after=after['valid'],reason='Nearby grid endpoint connector now attempted; every positive segment still checked against exact unbuffered polygon distances and analytic seating disks'))
        for q,l in zip(checks,result['candidates']):
            # Geometry-independent label: local/protected checks; exported candidates must remain correctly typed.
            assert q['local']['valid'],(row['id'],q)
            for target in (q['access']['targets'] if q['access'] else []):
                assert not target['certified'] or len(target['path'])>=3
        summary=dict(row);summary.update(usable=len(valid),validity_percent=100*len(valid)/len(checks) if checks else None,best_usable_service=min((l['objectives'][0] for l in valid),default=None),best_usable_change=min((l['objectives'][1] for l in valid),default=None),minimum_menu_vector_distance=min((float(np.linalg.norm(np.asarray(a['decision_vector'])-np.asarray(b['decision_vector']))) for i,a in enumerate(valid) for b in valid[:i]),default=None),validator_version='GRID_CONNECTORS_V2')
        for f in ['seating','stage','buffet','dance']:summary[f+'_pass']=sum(q['access'] is not None and all(t['certified'] for t in q['access']['targets'] if t['function']==f) for q in checks)
        qualification=dict(run_id=row['id'],case_sha256=digest(c),raw_result_sha256=digest(result),validator_source_sha256=sha(Path(__file__).with_name('verify.py')),checks_sha256=digest(checks),status='QUALIFIED_MENU' if valid else 'NO_INDEPENDENTLY_CERTIFIED_LAYOUT',qualified_layout_sha256=[digest(l) for l in valid],qualified_count=len(valid),returned_count=len(checks),xai={'basis':'Actual demand: 32 seats, one stage, minimum '+str(c['minimum_buffets'])+' buffet counters, dance area '+str(c['dance_area_m2'])+' m2; all require declared origin access.', 'certified':len(valid),'unqualified':len(checks)-len(valid),'best_service_distance_proxy_m':summary['best_usable_service'],'limitations':['Disc radius .3m, conservative seating group envelope, grid .25m; no evacuation or every-guest guarantee','Failed certificate is not a continuous-space impossibility proof','Design change is not physical equipment transportation','Explicit controlled simulated authority only']})
        save(out/(row['id']+'.json'),dict(checks=checks,qualification=qualification,row=summary))
        text=json.dumps(qualification,sort_keys=True,allow_nan=False);db.execute('insert into qualified values (?,?,?)',(row['id'],text,digest(qualification)));db.commit();back=db.execute('select qualification_json,sha256 from qualified where id=?',(row['id'],)).fetchone();assert json.loads(back[0])==qualification and back[1]==digest(qualification)
        final.append(summary)
    db.close()
    index={(r['geometry'],r['seed'],r['phase'],r['method']):r for r in final}
    for g,s,p in itertools.product(['open','barrier','narrow'],[20261019,20261020],['initial','revision']):
        a=index[g,s,p,'NEW'];b=index[g,s,p,'B2'];one=index[g,s,p,'B1'];ab=index[g,s,p,'ABLATION']
        ar=read(a['result_path']);br=read(b['result_path']);o=read(one['result_path']);z=read(ab['result_path'])
        eq=all(ar[k]==br[k] for k in ['trace','repair_trace','candidates','repair_access_queries','repair_pose_trials'])
        abeq=all(o[k]==z[k] for k in ['trace','candidates'])
        assert eq and abeq,(g,s,p)
        pairs.append(dict(geometry=g,seed=s,phase=p,new_b2_trace_candidates_equal=eq,b1_ablation_equal=abeq,new_minus_b1_usable=a['usable']-one['usable'],new_minus_b2_usable=a['usable']-b['usable'],new_minus_b1_service=(a['best_usable_service']-one['best_usable_service']) if a['usable'] and one['usable'] else None))
    summaries={}
    for method in METHODS:
        rs=[r for r in final if r['method']==method];n=sum(r['returned'] for r in rs);v=sum(r['usable'] for r in rs)
        summaries[method]=dict(runs=len(rs),runs_with_certified_output=sum(r['usable']>0 for r in rs),returned=n,certified=v,certified_percent=100*v/n if n else None,evaluations=sum(r['evaluations'] for r in rs),median_optimizer_runtime_s=statistics.median(r['runtime_s'] for r in rs),sum_optimizer_runtime_s=sum(r['runtime_s'] for r in rs),repair_access_queries=sum(r['repair_access_queries'] for r in rs),repair_pose_trials=sum(r['repair_pose_trials'] for r in rs),per_function_certified={f:sum(r[f+'_pass'] for r in rs) for f in ['seating','stage','buffet','dance']})
    clustermeans=[statistics.mean(p['new_minus_b1_usable'] for p in pairs if p['geometry']==g) for g in ['open','barrier','narrow']]
    bootstrap=sorted(statistics.mean(x) for x in itertools.product(clustermeans,repeat=3))
    summary=dict(status='PASS',runs=len(final),evaluations=sum(r['evaluations'] for r in final),methods=summaries,pairs=pairs,paired_summary={'new_minus_b1_mean_certified_candidates':statistics.mean(p['new_minus_b1_usable'] for p in pairs),'new_minus_b2_mean':0.,'geometry_cluster_means':clustermeans,'exact_27_cluster_resamples_percentile_2_5_97_5':np.percentile(bootstrap,[2.5,97.5]).tolist(),'interpretation':'Descriptive resampling of only three related synthetic geometry clusters, not population confidence or significance'},changed_certifications=len(changed),preserved_first_benchmark=True,sqlite_raw_rows=60,sqlite_qualification_rows=60)
    save(H/'RAW_EXPERIMENT_RESULTS_FINAL.json',final);save(H/'FINAL_SUMMARY.json',summary);save(H/'VERIFIER_CORRECTION_REPLAY.json',changed)
    print(json.dumps(summary['methods'],indent=2));print('Pairs',len(pairs),'equal; changed grid certifications',len(changed),flush=True)

if __name__=='__main__':main()
