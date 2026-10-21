"""Same-fixture, same-seed initial optimization comparison, no performance inflation."""
import csv,math
from fastapi.testclient import TestClient
from support import ROOT,PACKAGE,save
from api import create_app
from fixtures import controlled_registration,optimization

def main():
    out=PACKAGE/'outputs/COMPARISON';out.mkdir(parents=True,exist_ok=True)
    historical=list(csv.DictReader((ROOT/'PP1_READINESS_20261022/03_OPTIMIZATION_BASELINES/BASELINE_RAW_RESULTS.csv').open()))
    rows=[r for r in historical if r['method']=='M1' and r['guests']=='160' and r['layout_id']=='live_best_stage_proximity']
    assert len(rows)==5,[(r['method'],r['layout_id']) for r in historical[:10]]
    c=TestClient(create_app(out/'research.sqlite3'));reg=controlled_registration(out/'fixture');t=c.post('/twins',json=reg).json();records=[]
    for old in rows:
        req=optimization(t,seed=int(old['seed']));response=c.post('/optimize',json=req).json();assert response['status']=='success',response
        save(out/('SEED_'+old['seed']+'_RESPONSE.json'),response)
        best=min(response['verification'].values(),key=lambda m:m['mean_stage_distance'])
        records.append(dict(seed=req['seed'],old_stage_m=float(old['mean_stage_distance']),new_stage_m=best['mean_stage_distance'],stage_difference_m=best['mean_stage_distance']-float(old['mean_stage_distance']),old_evaluations=int(old['function_evaluations']),new_evaluations=response['optimizer_evaluations'],new_alternatives=len(response['candidate_layouts'])))
    save(out/'BEFORE_AFTER.json',{'records':records,'same_fixture_same_seed':True,'algorithmic_superiority_claim':False,'interpretation':'Best stage objective comparison only. Changes add strict admission, generic metric inputs, Pareto export, final independent verification and persistence; no retraining or new optimizer efficacy claim.'})
    print(records)
if __name__=='__main__':main()
