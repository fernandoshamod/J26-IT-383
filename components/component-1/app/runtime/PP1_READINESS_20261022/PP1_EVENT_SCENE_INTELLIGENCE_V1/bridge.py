"""Explicit isolated adapter to the unchanged frozen initial NSGA-II engine.
Does not bypass/register fake objects in the frozen reviewed-Twin HTTP contract.
Observed metric boundary is preserved; designed equipment and computational
reservations are distinctly mapped and independently verified before acceptance.
"""
import copy,importlib.util,time,sqlite3,json,uuid
import numpy as np
from scipy.optimize import linear_sum_assignment
from common import *
from models import Request
from compiler import compile_scene
from baseline import baseline_scene
from oracle import validate_spec,validate_layout

def menu(layouts,spatial_threshold=.5,objective_threshold=.05):
    if not layouts:return dict(selected_ids=[],reason='NO_VALIDATED_CANDIDATES',pairs=[])
    vectors=np.array([[l['objective_metrics'][k] for k in ['mean_stage_distance_m','initializer_assignment_movement_m']] for l in layouts]);scale=np.maximum(np.ptp(vectors,axis=0),1e-12);norm=(vectors-vectors.min(0))/scale
    pairs=[];distance={}
    for i,a in enumerate(layouts):
        for j in range(i):
            aa=np.array(list(a['group_centers_m'].values()));bb=np.array(list(layouts[j]['group_centers_m'].values()));d=np.linalg.norm(aa[:,None,:]-bb[None,:,:],axis=2)**2;rr,cc=linear_sum_assignment(d);rms=float(np.sqrt(d[rr,cc].mean()));objective=float(np.max(np.abs(norm[i]-norm[j])));distance[i,j]=distance[j,i]=(rms,objective)
            pairs.append(dict(a=a['layout_id'],b=layouts[j]['layout_id'],class_matched_rms_m=rms,normalized_objective_difference=objective))
    order=list(dict.fromkeys([int(vectors[:,0].argmin()),int(vectors[:,1].argmin()),*np.linalg.norm(norm,axis=1).argsort().tolist()]));chosen=[]
    for i in order:
        if all(distance[i,j][0]>=spatial_threshold and distance[i,j][1]>=objective_threshold for j in chosen):chosen.append(i)
        if len(chosen)==3:break
    return dict(selected_ids=[layouts[i]['layout_id'] for i in chosen],reason='THREE_ACTUAL_DISTINCT_ALTERNATIVES' if len(chosen)==3 else 'FEWER_CANDIDATES_MEET_PREDECLARED_DIVERSITY',spatial_threshold_m=spatial_threshold,objective_threshold=objective_threshold,normalization='Within this candidate pool only; not cross-case comparable',pairs=pairs)

def execute(request,spec,out,seed=20261017,policy=None):
    out=Path(out).resolve()
    if not out.is_relative_to(HERE):raise GateError('OUTPUT_OUTSIDE_ISOLATED_MODULE')
    out.mkdir(parents=True,exist_ok=False);save(out/'REQUEST.json',request);save(out/'SPEC.json',spec)
    policy=read(HERE/'profiles.json') if policy is None else policy;start=time.perf_counter();context={};raw=None;engine_calls=0
    result=dict(schema='EVENT_SCENE_LAYOUT_RESULT_V1',run_id=uuid.uuid4().hex,status='rejected',request_sha256=digest(request),spec_sha256=spec['spec_sha256'],optimizer_evaluations=0,candidate_layouts=[],selected_ids=[],real_planner_authentication=False,detailed_safety_validated=False,sgcn_used=False,weather_used=False)
    try:
        if digest({k:v for k,v in spec.items() if k!='spec_sha256'})!=spec['spec_sha256']:raise GateError('SPEC_TAMPERED')
        strategy=compile_scene if spec.get('method')=='POLICY_DERIVATION_AND_RECONCILIATION' else baseline_scene if spec.get('method')=='CONVENTIONAL_RULE_ASSIGNMENT_BASELINE' else None
        if strategy is None:raise GateError('UNKNOWN_SPEC_METHOD')
        fresh=strategy(request,policy)
        if fresh['spec_sha256']!=spec['spec_sha256'] or fresh['status']!='accepted':raise GateError('SPEC_STALE_OR_NOT_ACCEPTED')
        check=validate_spec(request,spec,policy)
        if not check['valid']:raise GateError('INDEPENDENT_SPEC_CHECK_FAILED')
        r=Request.model_validate(request);n=r.client.guest_count
        if r.client.event_type!='wedding':raise GateError('FROZEN_OPTIMIZER_EVENT_PROFILE_UNSUPPORTED')
        if r.venue.source.domain not in ['controlled_synthetic','plan_derived_controlled']:raise GateError('REAL_SCENE_EXECUTION_UNSUPPORTED')
        if n%8 or n>240:raise GateError('FROZEN_OPTIMIZER_CAPACITY_UNSUPPORTED')
        if spec['required_quantities'].get('round_table')!=n//8 or spec['required_quantities'].get('chair')!=n:raise GateError('FROZEN_OPTIMIZER_GROUP_POLICY_UNSUPPORTED')
        if any(o['class'] in ['chair','round_table'] for o in spec['retained_existing']):raise GateError('EXISTING_SEATING_REGROUPING_UNSUPPORTED')
        if policy['catalog']['chair']['radius_m']!=.27 or policy['catalog']['round_table']['radius_m']!=.8:raise GateError('FROZEN_SEATING_CATALOG_UNSUPPORTED')
        static=[o for o in spec['retained_existing']+spec['new_equipment'] if o['footprint_m'] is not None]
        if sum(o['class']=='stage' for o in static)!=1:raise GateError('FROZEN_ENGINE_REQUIRES_ONE_STAGE_CONTEXT')
        records=[dict(object_id=o['instance_id'],**{'class':o['class']},group_id=None,footprint_coordinates_m=o['footprint_m']) for o in static]
        reservation_ids=set()
        for z in spec['zones']:
            if not z['exclusive']:continue
            iid='COMPUTATIONAL_RESERVATION__'+z['zone_id'];reservation_ids.add(iid)
            records.append(dict(object_id=iid,**{'class':'restricted_zone'},group_id=None,footprint_coordinates_m=z['footprint_m']))
        plan_derived=r.venue.source.domain=='plan_derived_controlled'
        internal=dict(contract_id='STAGE_E_PP1_V1',mode='initial_design',venue_twin=dict(source_type='controlled_source_derived' if plan_derived else 'controlled_synthetic',verification_status='PLAN_DERIVED_SIMULATED_REVIEW_NOT_FROZEN_TWIN_REGISTRATION' if plan_derived else 'EXPLICIT_ISOLATED_METRIC_SCENE_NOT_FROZEN_TWIN_REGISTRATION',boundary_polygon_m=r.venue.boundary_m,fixed_obstacles=records),event_requirements=dict(event_id=r.event_id,event_type='Wedding',guest_count=n,seats_per_table=8),optimization_request=dict(algorithm='NSGA2',experimental_clearance_m=spec['hard']['minimum_clearance_m'],seed=seed),hard_limits=dict(maximum_mean_stage_distance_m=spec['hard']['maximum_mean_stage_distance_m'],maximum_total_movement_m=spec['hard']['maximum_assignment_movement_m']))
        save(out/'FROZEN_ENGINE_REQUEST.json',internal)
        path=BACKEND/'engine_initial.py';loader=importlib.util.spec_from_file_location('scene_frozen_'+uuid.uuid4().hex,path);engine=importlib.util.module_from_spec(loader);loader.loader.exec_module(engine)
        original=engine.initialize;minimize=engine.minimize
        def capture(*a,**k):
            values=original(*a,**k);context['initial']=values.tolist();return values
        def measured(*a,**k):
            nonlocal engine_calls
            engine_calls+=1;t=time.perf_counter();res=minimize(*a,**k);context['evaluations']=int(res.algorithm.evaluator.n_eval);context['optimizer_seconds']=time.perf_counter()-t;return res
        engine.initialize=capture;engine.minimize=measured
        raw=engine.run(internal);save(out/'FROZEN_ENGINE_RESPONSE.json',raw)
        normalized=[];verified={};initial={f'{r.event_id}__group_{i:04d}':xy for i,xy in enumerate(context['initial'],1)}
        static_ids={o['instance_id'] for o in static}
        for layout in raw['candidate_layouts']:
            objects=[]
            for o in layout['objects']:
                if o['object_id'] in reservation_ids:continue
                obj=copy.deepcopy(o)
                if o['group_id']:
                    i=int(o['group_id'].split('_')[-1]);obj['group_id']=f'{r.event_id}__group_{i:04d}'
                    if o['class']=='round_table':obj['object_id']=f'{r.event_id}__new_round_table_{i:03d}'
                    elif o['class']=='chair':obj['object_id']=f'{r.event_id}__new_chair_{(i-1)*8+int(o["object_id"].split("_")[-1]):03d}'
                    else:raise GateError('UNKNOWN_ENGINE_GROUP_CLASS')
                elif o['object_id'] not in static_ids:raise GateError('UNMAPPED_ENGINE_OBJECT')
                objects.append(obj)
            l=dict(layout_id=layout['layout_id'],objects=objects,zones=spec['zones'],group_centers_m={f'{r.event_id}__group_{int(g.split("_")[-1]):04d}':xy for g,xy in layout['group_centers_m'].items()},objective_metrics=dict(mean_stage_distance_m=layout['objective_metrics']['average_stage_distance_m'],initializer_assignment_movement_m=layout['objective_metrics']['reference_displacement_m']))
            v=validate_layout(request,spec,l,initial);verified[l['layout_id']]=v
            if not v['valid']:raise GateError('INDEPENDENT_LAYOUT_CHECK_FAILED:'+','.join(v['errors']))
            normalized.append(l)
        vectors=[list(l['objective_metrics'].values()) for l in normalized]
        if any(all(a<=b+1e-10 for a,b in zip(vectors[j],vectors[i])) and any(a<b-1e-10 for a,b in zip(vectors[j],vectors[i])) for i in range(len(vectors)) for j in range(len(vectors)) if i!=j):raise GateError('RETURNED_SET_DOMINATED')
        selection=menu(normalized);save(out/'MENU_SELECTION.json',selection)
        # Fresh source/evidence/spec checks also apply immediately before persistence.
        if strategy(request,policy)['spec_sha256']!=spec['spec_sha256']:raise GateError('SCENE_CHANGED_DURING_SEARCH')
        result.update(status='success',candidate_layouts=normalized,selected_ids=selection['selected_ids'],menu=selection,verification=verified,initialization_centers_m=initial,engine_source_sha256=filehash(path),engine_integration='UNCHANGED_FROZEN_LOCAL_ENGINE_VIA_ISOLATED_ADAPTER_NOT_EXISTING_HTTP_SERVICE',source_scope='PLAN_DERIVED_CONTROLLED' if plan_derived else 'CONTROLLED_SYNTHETIC',real_venue_twin=False,reserved_geometry_is_not_physical_equipment=True,reason=selection['reason'])
    except (GateError,ValueError) as e:
        result.update(reason=str(e),status='failed_search' if str(e).startswith(('NO_COMPLETE_INITIALIZATION','NO_FEASIBLE_CANDIDATES')) else 'rejected',candidate_layouts=[],selected_ids=[],global_infeasibility_proven=False)
    result.update(optimizer_evaluations=context.get('evaluations',0),optimizer_calls=engine_calls,optimizer_seconds=context.get('optimizer_seconds',0.),elapsed_seconds=time.perf_counter()-start)
    explanations=[]
    for l in result['candidate_layouts']:
        v=result['verification'][l['layout_id']]
        explanations.append(dict(layout_id=l['layout_id'],layout_sha256=digest(l),physical_object_count=v['object_count'],allocated_counts=v['allocated_counts'],verified_functions=v['verified_functions'],metrics={k:v[k] for k in ['mean_stage_distance_m','initializer_assignment_movement_m','minimum_clearance_m','protected_geometry_changes']},rule_trace=spec['derivation'],text=f'{v["object_count"]} physical objects; {len(l["zones"])} separately represented zones; declared function/geometry checks passed. Initializer displacement is not real furniture transport.'))
    result['xai']=dict(request_sha256=digest(request),spec_sha256=spec['spec_sha256'],response_payload_sha256=digest(result),explanations=explanations,denial_reason=result.get('reason') if result['status']!='success' else None,no_learned_or_weather_claim=True,no_safety_certification=True)
    save(out/'RESULT.json',result)
    with sqlite3.connect(out/'scene.sqlite3') as c:
        c.execute('CREATE TABLE results(run_id TEXT PRIMARY KEY, request TEXT, spec TEXT, response TEXT, sha TEXT)');c.execute('INSERT INTO results VALUES(?,?,?,?,?)',(result['run_id'],json.dumps(request),json.dumps(spec),json.dumps(result),digest(result)))
    return result
