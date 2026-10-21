"""Actual initial and singleton NSGA-II adapters, unchanged frozen engines."""
import copy,time,math
import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon
from runtime import *

def full(request,spec,out,seed):
    raw=bridge.execute(request,spec,out,seed=seed,policy=POLICY)
    return dict(status=raw['status'],layouts=raw['candidate_layouts'],initial=raw.get('initialization_centers_m',{}),evaluations=raw['optimizer_evaluations'],optimizer_calls=raw['optimizer_calls'],seconds=raw['optimizer_seconds'],reason=raw['reason'],path=str(out),engine='INITIAL_NSGA_II_48x25')

def singleton(request,spec,out,seed,reference,target):
    out.mkdir(parents=True,exist_ok=False)
    internal=copy.deepcopy(reference['engine_request']);internal['mode']='adaptive_revision';internal['optimization_request']['seed']=seed
    groups=sorted(reference['layout']['group_centers_m']);mapping={g:f'seating_group_{i:04d}' for i,g in enumerate(groups,1)};reverse={v:k for k,v in mapping.items()}
    internal.update(approved_reference_layout=dict(group_centers_m={mapping[g]:xy for g,xy in reference['layout']['group_centers_m'].items()},approval_status='EXPLICIT_SIMULATED_EAG_REFERENCE'),revision_request=dict(group_id=mapping[target],action='move'),planner_context=dict(permissions={mapping[target]:dict(status='movable',move_allowed=True,scope='SYNTHETIC_DEMO_ONLY',approved_by=request['planner']['actor_id'],approval_reason='Explicit controlled EAG singleton request')}))
    save(out/'FROZEN_ADAPTIVE_REQUEST.json',internal);engine=load_engine('engine_adaptive');start=time.perf_counter();raw=engine.execute(internal);seconds=time.perf_counter()-start;save(out/'FROZEN_ADAPTIVE_RESPONSE.json',raw)
    initial=reference['initial'];reservations={o['object_id'] for o in internal['venue_twin']['fixed_obstacles'] if o['object_id'].startswith('COMPUTATIONAL_RESERVATION__')};layouts=[]
    for old in raw['candidate_layouts']:
        objs=[]
        for ob in old['objects']:
            if ob['object_id'] in reservations:continue
            o=copy.deepcopy(ob);g=o['group_id']
            if g:
                i=int(g.split('_')[-1]);o['group_id']=reverse[g]
                o['object_id']=f'{request["event_id"]}__new_round_table_{i:03d}' if o['class']=='round_table' else f'{request["event_id"]}__new_chair_{(i-1)*8+int(o["object_id"].split("_")[-1]):03d}'
            objs.append(o)
        centers={reverse[g]:xy for g,xy in old['group_centers_m'].items()};stage=Polygon(next(o['footprint_coordinates_m'] for o in objs if o['class']=='stage')).centroid
        mean=sum(math.dist(xy,[stage.x,stage.y]) for xy in centers.values())/len(centers)
        a=np.array(list(initial.values()));b=np.array([centers[g] for g in sorted(centers)]);cost=np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2);rr,cc=linear_sum_assignment(cost);movement=float(cost[rr,cc].sum())
        layouts.append(dict(layout_id=old['layout_id'],objects=objs,zones=spec['zones'],group_centers_m=centers,objective_metrics=dict(mean_stage_distance_m=mean,initializer_assignment_movement_m=movement),search_objectives=dict(target_stage_distance_m=old['objective_metrics']['stage_distance_m'],target_relocation_m=old['objective_metrics']['identity_based_relocation_m'])))
    save(out/'NORMALIZED_ADAPTIVE_LAYOUTS.json',layouts)
    return dict(status=raw['status'],layouts=layouts,initial=initial,evaluations=raw['provenance']['optimizer_evaluations'],optimizer_calls=1,seconds=seconds,reason='ACTUAL_AUTHORIZED_SINGLETON_SEARCH',path=str(out),engine='ADAPTIVE_NSGA_II_48x35')
