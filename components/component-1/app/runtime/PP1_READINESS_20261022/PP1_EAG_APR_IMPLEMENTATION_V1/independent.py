"""Separate verification of returned layouts, authority and certificate/XAI.
Reuses the established independent geometry/count oracle, not graph/dispatch logic.
Same Shapely/SciPy kernels limit implementation independence.
"""
import math
from runtime import digest,read,filehash,facts,POLICY,oracle,baseline

def verify_candidate(packet,spec,layout,initial,reference=None,target=None):
    errors=[];r=packet['scene'];c=packet['context']
    geometry=oracle.validate_layout(r,spec,layout,initial)
    errors.extend(geometry['errors'])
    # Independent approval/document and freshness checks.
    try:
        e=packet['authority'];doc=read(e['path'])
        if filehash(e['path'])!=e['sha256'] or doc['scene_sha256']!=digest(r) or doc['context']!=c or doc['scope']!='SIMULATED_FIXTURE_NOT_AUTHENTICATED_AUTHORITY':errors.append('AUTHORITY_BINDING')
        if baseline.baseline_scene(r,POLICY)['status']!='accepted':errors.append('CURRENT_EVIDENCE_NOT_QUALIFIED')
    except (OSError,KeyError,ValueError):errors.append('CURRENT_EVIDENCE_INVALID')
    if c['scope']!='SIMULATED_FIXTURE' or c['scenario'] not in ['CONTROLLED_NOMINAL','CONTROLLED_OPERATIONAL_RESTRICTION']:errors.append('UNSUPPORTED_CONTEXT')
    moved=[];individual_distance=0.;protected_changes=[];group_displacement=0.
    if reference:
        old=reference['layout'];oldobjects={o['object_id']:o for o in old['objects']};now={o['object_id']:o for o in layout['objects']}
        immutable=set(c['protected_object_ids'])|{o['instance_id'] for o in reference['request']['venue']['existing'] if o['status']=='fixed' or o['protected']}
        if c['reference_sha256']!=digest(old):errors.append('STALE_REFERENCE')
        for iid in immutable:
            if iid not in now or iid not in oldobjects or now[iid]!=oldobjects[iid]:protected_changes.append(iid)
        if protected_changes:errors.append('PROTECTED_OBJECT_CHANGED')
        for iid,o in oldobjects.items():
            n=now.get(iid)
            if n is None:errors.append('UNSUPPORTED_REFERENCE_REMOVAL');continue
            if n!=o:
                moved.append(iid)
                if not o['group_id'] or o['group_id'] not in c['allowed_groups']:errors.append('UNAUTHORIZED_OBJECT_CHANGE')
                if target and o['group_id']!=target:errors.append('UNAFFECTED_SINGLETON_OBJECT_CHANGED')
            # Real stable-ID centroid displacement, not initializer assignment metric.
            from shapely.geometry import Polygon
            individual_distance+=Polygon(o['footprint_coordinates_m']).centroid.distance(Polygon(n['footprint_coordinates_m']).centroid)
        extra=set(now)-set(oldobjects)
        if extra and not c['new_supply_permitted']:errors.append('UNAUTHORIZED_NEW_SUPPLY')
        for gid,xy in old['group_centers_m'].items():
            if gid in layout['group_centers_m']:group_displacement+=math.dist(xy,layout['group_centers_m'][gid])
        if target:
            if target not in c['allowed_groups'] or any(oldobjects[i]['group_id']==target for i in c['protected_object_ids']):errors.append('SINGLETON_PERMISSION_INVALID')
            actual=math.dist(old['group_centers_m'][target],layout['group_centers_m'][target]);stage=next(o for o in layout['objects'] if o['class']=='stage')
            from shapely.geometry import Polygon
            p=Polygon(stage['footprint_coordinates_m']).centroid;d=math.dist(layout['group_centers_m'][target],[p.x,p.y])
            if abs(layout['search_objectives']['target_stage_distance_m']-d)>1e-7 or abs(layout['search_objectives']['target_relocation_m']-actual)>1e-7:errors.append('ADAPTIVE_SEARCH_OBJECTIVES')
    return dict(valid=not errors,errors=sorted(set(errors)),geometry=geometry,moved_object_count=len(moved),moved_object_ids=moved,stable_group_relocation_m=group_displacement,stable_individual_relocation_m=individual_distance,protected_changes=protected_changes,checked_obligations=['EVIDENCE','ACTOR_APPROVAL','FUNCTION_DEMAND','STOCK_ALLOCATION','GEOMETRY','PROTECTED','PERMISSIONS','HARD_CLEARANCE','HARD_STAGE','HARD_MOVEMENT','SCENARIO_SCOPE','PARETO_STAGE','PARETO_DISRUPTION'])

def verify_envelope(packet,response,reference=None):
    errors=[];cert=response['certificate'];base={k:v for k,v in response.items() if k not in ['certificate','xai']}
    if cert['certificate_sha256']!=digest({k:v for k,v in cert.items() if k!='certificate_sha256'}):errors.append('CERTIFICATE_DIGEST')
    if cert['fingerprint']!=facts(packet) or cert['result_payload_sha256']!=digest(base):errors.append('CERTIFICATE_STALE_OR_RESULT_MISMATCH')
    if cert['recommendation_ready']!=(response['status']=='eligible' and bool(response['candidate_layouts'])):errors.append('FALSE_RECOMMENDATION_READINESS')
    if cert['active_hard_constraints']!=response['spec']['hard'] or cert['mandatory_functions']!=response['spec']['functions'] or cert['protected_object_ids']!=packet['context']['protected_object_ids']:errors.append('CERTIFICATE_CONTENT')
    if cert['validation']!=response['validation']:errors.append('CERTIFICATE_VALIDATION')
    if response['status']=='eligible' and (not response['validation'] or any(not v['valid'] for v in response['validation'].values())):errors.append('UNVERIFIED_ELIGIBLE')
    if response['status']=='eligible':
        if response['reference_sha256'] is not None and reference is None:errors.append('REFERENCE_REQUIRED_FOR_COMPLETE_REPLAY')
        if not oracle.validate_spec(packet['scene'],response['spec'],POLICY)['valid']:errors.append('SPECIFICATION_ORACLE')
        for layout in response['candidate_layouts']:
            checked=verify_candidate(packet,response['spec'],layout,response['initialization_centers_m'],reference,packet['context']['requested_group'] if response['operation']=='SELECTIVE_SINGLETON' else None)
            if checked!=response['validation'].get(layout['layout_id']) or not checked['valid']:errors.append('RAW_REPLAY_DISAGREES_WITH_CLAIMED_VALIDATION')
        layouts=response['candidate_layouts'];vectors=[list(l.get('search_objectives',l['objective_metrics']).values()) for l in layouts]
        if any(all(a<=b+1e-9 for a,b in zip(x,y)) and any(a<b-1e-9 for a,b in zip(x,y)) for i,x in enumerate(vectors) for j,y in enumerate(vectors) if i!=j):errors.append('DOMINATED_RETURNED_CANDIDATE')
        ids=response['selected_ids'];lookup={l['layout_id']:l for l in layouts}
        if len(set(ids))!=len(ids) or len(ids)>3 or not set(ids)<=set(lookup):errors.append('MENU_IDENTITIES')
        if len(ids)>1:
            import numpy as np
            from scipy.optimize import linear_sum_assignment
            vals=np.array([[l['objective_metrics'][k] for k in ['mean_stage_distance_m','initializer_assignment_movement_m']] for l in layouts]);ranges=np.maximum(vals.max(0)-vals.min(0),1e-12)
            for i,lid in enumerate(ids):
                for other in ids[:i]:
                    a=lookup[lid];b=lookup[other];x=np.array(list(a['group_centers_m'].values()));y=np.array(list(b['group_centers_m'].values()));cost=((x[:,None,:]-y[None,:,:])**2).sum(2);rr,cc=linear_sum_assignment(cost);rms=float(np.sqrt(cost[rr,cc].mean()));delta=max(np.abs(np.array(list(a['objective_metrics'].values()))-np.array(list(b['objective_metrics'].values())))/ranges)
                    if rms<.5-1e-9 or delta<.05-1e-9:errors.append('MATERIAL_MENU_DIVERSITY')
    expected=[dict(layout_id=l['layout_id'],layout_sha256=digest(l),constraint_ids=sorted(response['graph_constraint_ids']),counts=response['validation'][l['layout_id']]['geometry']['allocated_counts'],mean_stage_distance_m=l['objective_metrics']['mean_stage_distance_m'],initializer_assignment_movement_m=l['objective_metrics']['initializer_assignment_movement_m'],stable_group_relocation_m=response['validation'][l['layout_id']]['stable_group_relocation_m']) for l in response['candidate_layouts']]
    x=response['xai']
    if x['certificate_sha256']!=cert['certificate_sha256'] or x['context_sha256']!=digest(packet['context']) or x['request_sha256']!=digest(packet['scene']) or x['claims']!=expected or x['reasons']!=response['reasons'] or x['evidence_ids']!=cert['verified_evidence_dependencies']:errors.append('XAI_FIDELITY')
    return dict(valid=not errors,errors=sorted(set(errors)))
