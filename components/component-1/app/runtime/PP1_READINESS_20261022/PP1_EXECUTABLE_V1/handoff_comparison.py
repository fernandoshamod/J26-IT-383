"""Paired local-warm-start vs uniform-sampling single-group NSGA-II experiment.
Same reference, constraints, seed, operators and evaluation budget. No novelty claim.
"""
import copy,time,math,statistics
import numpy as np
from shapely.geometry import Polygon
from pymoo.algorithms.moo.nsga2 import NSGA2
from fastapi.testclient import TestClient
from support import PACKAGE,save,digest
from api import create_app
from fixtures import controlled_registration,optimization,approval,revise

def main():
    out=PACKAGE/'outputs/HANDOFF_V1/comparison';out.mkdir();app=create_app(out/'research.sqlite3');c=TestClient(app);service=app.state.service
    t=c.post('/twins',json=controlled_registration(out/'fixture',venue_id='COMPARATIVE_CONTROLLED')).json();req=optimization(t);initial=c.post('/optimize',json=req).json();assert initial['status']=='success'
    ar=c.post('/runs/'+initial['run_id']+'/approve',json=approval(initial)).json();base=revise(initial,ar,req);reference=next(l for l in initial['candidate_layouts'] if l['layout_id']==initial['selected_layout_id']);fixed={o['object_id']:o for o in reference['objects'] if o.get('group_id')!='seating_group_0013'}
    save(out/'REFERENCE_INITIAL.json',initial);save(out/'REFERENCE_APPROVAL.json',ar)
    records=[];original=service.engine
    for seed in range(20261016,20261021):
        for method in ['uniform','local_warm_start']:
            request=copy.deepcopy(base);request['seed']=seed
            if method=='uniform':
                def uniform_engine(name):
                    m=original(name);observed=m.minimize
                    def minimize(problem,algorithm,*args,**kwargs):
                        rng=np.random.default_rng(seed);samples=rng.uniform(problem.xl,problem.xu,(48,2));samples[0]=reference['group_centers_m']['seating_group_0013']
                        return observed(problem,NSGA2(pop_size=48,sampling=samples,eliminate_duplicates=True),*args,**kwargs)
                    m.minimize=minimize;return m
                service.engine=uniform_engine
            start=time.perf_counter()
            try:response=c.post('/optimize',json=request).json()
            finally:service.engine=original
            elapsed=time.perf_counter()-start;assert response['status']=='success' and response['optimizer_evaluations']==1680,response
            save(out/(f'{method}_{seed}_REQUEST.json'),request);save(out/(f'{method}_{seed}_RESPONSE.json'),response)
            values=[]
            for layout in response['candidate_layouts']:
                # Independent formulas and raw-object equality; no optimizer measurement helpers.
                stage=Polygon(next(o['footprint_coordinates_m'] for o in layout['objects'] if o['class']=='stage')).centroid
                mean=sum(math.dist(xy,[stage.x,stage.y]) for xy in layout['group_centers_m'].values())/len(layout['group_centers_m'])
                move=sum(math.dist(xy,reference['group_centers_m'][g]) for g,xy in layout['group_centers_m'].items())
                for obj in layout['objects']:
                    if obj['object_id'] in fixed:assert digest(obj)==digest(fixed[obj['object_id']])
                assert abs(mean-response['verification'][layout['layout_id']]['mean_stage_distance'])<1e-8
                values.append((mean,move))
            best=min(values);records.append(dict(seed=seed,method=method,evaluations=1680,returned_alternatives=len(values),best_stage_m=best[0],movement_at_best_stage_m=best[1],reference_sha256=digest(reference),wall_seconds=elapsed))
            print(method,seed,best,flush=True)
    deltas=[]
    for seed in range(20261016,20261021):
        u=next(r for r in records if r['seed']==seed and r['method']=='uniform');l=next(r for r in records if r['seed']==seed and r['method']=='local_warm_start')
        deltas.append(dict(seed=seed,local_minus_uniform_stage_m=l['best_stage_m']-u['best_stage_m'],local_minus_uniform_movement_m=l['movement_at_best_stage_m']-u['movement_at_best_stage_m']))
    result=dict(records=records,paired_deltas=deltas,mean_stage_delta_m=statistics.mean(d['local_minus_uniform_stage_m'] for d in deltas),mean_movement_delta_m=statistics.mean(d['local_minus_uniform_movement_m'] for d in deltas),controls='Same one-group reference/Twin/constraints/seed/population/operators/generations. Only sampling differs; both include the feasible reference.',limitations=['Five seeds, one controlled venue/reference, no statistical independence across venues.','No comparison against full multi-group reoptimization; no speedup/significance/novelty claim.','Returned feasible candidate set only; no global Pareto-front or full-front hypervolume claim.','Wall time includes API/independent verification/persistence, excludes setup; descriptive only.'],novelty_or_superiority_claim=False)
    save(out/'FAIR_COMPARISON.json',result)
if __name__=='__main__':main()
