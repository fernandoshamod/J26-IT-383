"""Independent finite-profile oracle and exported-geometry verifier.
No compiler, baseline, core, engine measurement or reconstruction helpers imported.
Shares JSON policy data, hash primitives, SciPy and Shapely, not inference code.
"""
import math
import re
from collections import Counter
from shapely.geometry import Polygon,box
from scipy.optimize import linear_sum_assignment
import numpy as np
from common import digest

def reference_demand(request,policy):
    event=request['client']['event_type'];n=request['client']['guest_count']
    profile=next(p for p in policy['profiles'].values() if event in p['event_types'])
    functions=set(profile['required_functions'])|set(request['client']['optional_functions']);counts=Counter()
    if 'dining' in functions:counts.update(round_table=(n+7)//8,chair=n)
    if 'audience' in functions:counts['chair']+=n
    if 'presentation' in functions:counts['stage']+=1
    if 'performance' in functions:counts.update(stage=1,speaker=2)
    if 'conference_tools' in functions:counts.update(lectern=1,screen=1)
    if 'celebration' in functions:counts['cake_table']+=1
    if 'buffet' in functions:
        per=policy['functions']['buffet']['objects'][0]['divisor'];counts['buffet_counter']+=(n+per-1)//per
    if 'networking' in functions:
        per=policy['functions']['networking']['objects'][0]['divisor'];counts['standing_table']+=(n+per-1)//per
    return dict(counts),functions

def validate_spec(request,spec,policy,expected_status='accepted',expected_counts=None):
    errors=[];wanted,functions=reference_demand(request,policy)
    if expected_counts is not None and wanted!=expected_counts:errors.append('PREAUTHORED_DEMAND_DISAGREES_WITH_ORACLE')
    if spec['status']!=expected_status:errors.append('EXPECTED_STATUS')
    if spec['spec_sha256']!=digest({k:v for k,v in spec.items() if k!='spec_sha256'}):errors.append('SPEC_HASH')
    b=spec['binding'];v=request['venue']
    if b['request_sha256']!=digest(request) or b['venue_sha256']!=digest(v) or b['venue_version']!=v['version'] or b['source_sha256']!=v['source']['sha256'] or b['policy_sha256']!=digest(policy):errors.append('INPUT_VERSION_SOURCE_BINDING')
    if expected_status=='accepted':
        if any(request[role]['policy_sha256']!=digest(policy) for role in ['client','planner']):errors.append('POLICY_APPROVAL_BINDING')
        if spec['required_quantities']!=wanted or set(spec['functions'])!=functions:errors.append('DEMAND_OR_FUNCTIONS')
        a=spec['allocations'];ids=[x['instance_id'] for x in a]
        if len(set(ids))!=len(ids):errors.append('DOUBLE_ALLOCATION')
        if dict(Counter(x['class'] for x in a))!=wanted:errors.append('ALLOCATION_QUANTITIES')
        observed={o['instance_id']:o for o in v['existing']};new={o['instance_id']:o for o in spec['new_equipment']};removed=set(spec['removed_existing'])
        for x in a:
            iid=x['instance_id'];cls=x['class']
            if x['origin']=='observed_existing':
                o=observed.get(iid)
                if not o or o['class_name']!=cls or o['status']=='uncertain' or o['review_status']!='approved' or iid in removed:errors.append('UNVERIFIED_OR_WRONG_REUSE')
                if not any(p['instance_id']==iid and p['action']=='reuse' and p['approved'] and p['actor_id']==request['planner']['actor_id'] and p['scope']==request['planner']['scope'] for p in request['actions']):errors.append('UNAUTHORIZED_REUSE')
                if o:
                    cat=policy['catalog'][cls];x0,y0,x1,y1=Polygon(o['footprint_m']).bounds
                    if cat['shape']!='rectangle' or abs(x1-x0-cat['width_m'])>1e-7 or abs(y1-y0-cat['depth_m'])>1e-7:errors.append('REUSED_DIMENSIONS')
            elif iid not in new or new[iid]['class']!=cls or iid in observed:errors.append('NEW_EQUIPMENT_IDENTITY')
            expected_functions={f for f in functions if any(r['class']==cls for r in policy['functions'][f]['objects'])}
            if set(x['functions'])!=expected_functions:errors.append('ALLOCATION_FUNCTION_TRACE')
        if set(new)!={x['instance_id'] for x in a if x['origin']=='new_event_equipment'}:errors.append('UNALLOCATED_NEW_EQUIPMENT')
        retained={o['instance_id']:o for o in spec['retained_existing']}
        if set(retained)!=set(observed)-removed:errors.append('EXISTING_IDENTITY_CONSERVATION')
        for iid,o in retained.items():
            if o['footprint_m']!=observed[iid]['footprint_m'] or o['class']!=observed[iid]['class_name']:errors.append('EXISTING_GEOMETRY_CHANGED')
        for iid in removed:
            o=observed.get(iid)
            if not o or o['protected'] or o['status']!='movable' or not any(p['instance_id']==iid and p['action']=='remove' and p['approved'] for p in request['actions']):errors.append('UNAUTHORIZED_REMOVAL')
        if v['review']['status']!='approved' or any(request[p]['approval_status']!='approved' for p in ['client','planner']) or any(o['status']=='uncertain' or o['review_status']!='approved' for o in observed.values()):errors.append('FALSE_READY_ACCEPTANCE')
        kinds=Counter(z['kind'] for z in spec['zones'])
        expected={'dining_area':int('dining' in functions),'audience_area':int('audience' in functions),'stage_access':wanted.get('stage',0),'buffet_access':wanted.get('buffet_counter',0),'dance_area':int('dancing' in functions)}
        for kind,n in expected.items():
            if kinds[kind]!=n:errors.append('ZONE_COMPLETENESS:'+kind)
        for f,kind in [('celebration','celebration_area'),('conference_tools','conference_area'),('networking','networking_area'),('performance','performance_area')]:
            if kinds[kind]!=int(f in functions):errors.append('ZONE_COMPLETENESS:'+f)
        declared={z for f in functions for z in policy['functions'][f]['zones']}
        if set(kinds)!=declared:errors.append('CONFIGURED_ZONE_NAMES')
        all_objects={**retained,**new};zone_ids=[z['zone_id'] for z in spec['zones']]
        if len(set(zone_ids))!=len(zone_ids):errors.append('DUPLICATE_ZONE')
        for z in spec['zones']:
            kind=z['kind'];q=Polygon(z['footprint_m'])
            if not q.is_valid or q.area<=0 or not Polygon(v['boundary_m']).covers(q):errors.append('ZONE_GEOMETRY')
            if kind in ['stage_access','buffet_access']:
                obj=all_objects.get(z.get('anchor_id'));cls='stage' if kind=='stage_access' else 'buffet_counter'
                if not obj or obj['class']!=cls or not z['exclusive']:errors.append('ZONE_ANCHOR_OR_EXCLUSIVITY')
                elif obj['footprint_m']:
                    x,y,b,t=Polygon(obj['footprint_m']).bounds;d=policy['zone_parameters']['access_depth_m']
                    if not q.equals(Polygon([[x,y-d],[b,y-d],[b,y],[x,y],[x,y-d]])):errors.append('FUNCTION_ACCESS_GEOMETRY')
            elif kind=='dance_area':
                if not z['exclusive'] or not q.equals(Polygon(request['dance_zone_m'])) or q.area<policy['zone_parameters']['dance_min_area_m2']:errors.append('DANCE_GEOMETRY_OR_POLICY')
            elif not q.equals(Polygon(v['boundary_m'])) or z['exclusive']:errors.append('BROAD_ZONE_BOUNDARY')
        hard=spec['hard'];a=request['client']['hard'];c=request['planner']['hard']
        if hard['minimum_clearance_m']!=max(a['minimum_clearance_m'],c['minimum_clearance_m']):errors.append('CLEARANCE_MERGE')
        for key in ['maximum_mean_stage_distance_m','maximum_assignment_movement_m']:
            limits=[p[key] for p in [a,c] if p.get(key) is not None]
            if hard[key]!=(min(limits) if limits else None):errors.append('UPPER_BOUND_MERGE')
    return dict(valid=not errors,errors=sorted(set(errors)),oracle_quantities=wanted,oracle_functions=sorted(functions),status=spec['status'])

def env(xy):
    x,y=xy;return Polygon([(x+1.72*math.cos(k*math.pi/64),y+1.72*math.sin(k*math.pi/64)) for k in range(129)])

def validate_layout(request,spec,layout,initial_centers):
    errors=[];p=policy_from_spec(spec);wanted,functions=reference_demand(request,p)
    physical=layout['objects'];byid={o['object_id']:o for o in physical};centers=layout['group_centers_m'];venue=Polygon(request['venue']['boundary_m'])
    expected={o['instance_id']:o for o in spec['retained_existing']+spec['new_equipment']};polys=[]
    if len(byid)!=len(physical) or set(byid)!=set(expected):errors.append('PHYSICAL_IDENTITY_OR_COUNT')
    for oid,o in byid.items():
        q=Polygon(o['footprint_coordinates_m']);polys.append(q)
        if not q.is_valid or q.area<=0 or not venue.covers(q):errors.append('PHYSICAL_GEOMETRY')
        e=expected.get(oid)
        if not e:continue
        if o['class']!=e['class']:errors.append('PHYSICAL_CLASS')
        if e['footprint_m'] is not None and o['footprint_coordinates_m']!=e['footprint_m']:errors.append('PINNED_OR_EXISTING_GEOMETRY_CHANGED')
    for i,q in enumerate(polys):
        if any(q.intersection(other).area>1e-8 for other in polys[:i]):errors.append('PHYSICAL_OVERLAP')
    if dict(Counter(byid[a['instance_id']]['class'] for a in spec['allocations'] if a['instance_id'] in byid))!=wanted:errors.append('DEMAND_COVERAGE')
    zone_ids={z['zone_id'] for z in layout['zones']}
    if zone_ids!={z['zone_id'] for z in spec['zones']} or digest(layout['zones'])!=digest(spec['zones']):errors.append('ZONE_IDENTITY_OR_GEOMETRY')
    fixed=[Polygon(o['footprint_m']) for o in expected.values() if o['footprint_m'] is not None]
    reserved=[Polygon(z['footprint_m']) for z in spec['zones'] if z['exclusive']]
    for z in reserved:
        if any(z.intersection(q).area>1e-8 for q in polys):errors.append('FUNCTION_ACCESS_BLOCKED')
    # Independently reconstruct circle centers/radii and rigid group memberships.
    n=len(centers)
    for i,g in enumerate(sorted(centers),1):
        x,y=centers[g];oid=f'{request["event_id"]}__new_round_table_{i:03d}'
        expected_circles=[(oid,(x,y),.8)]
        for k in range(8):expected_circles.append((f'{request["event_id"]}__new_chair_{(i-1)*8+k+1:03d}',(x+1.45*math.cos(k*math.pi/4),y+1.45*math.sin(k*math.pi/4)),.27))
        for iid,xy,radius in expected_circles:
            o=byid.get(iid)
            if not o or o['group_id']!=g:errors.append('RIGID_GROUP_MEMBERSHIP');continue
            if any(abs(math.dist(v,xy)-radius)>1e-7 for v in o['footprint_coordinates_m']):errors.append('INDIVIDUAL_FURNITURE_GEOMETRY')
    if n*8!=request['client']['guest_count']:errors.append('SEATING_CAPACITY')
    envelopes=[env(xy) for xy in centers.values()]
    gaps=[a.distance(b) for i,a in enumerate(envelopes) for b in envelopes[:i]]+[e.distance(q) for e in envelopes for q in fixed+reserved]
    minimum=min(gaps)
    if any(not venue.covers(e) for e in envelopes) or minimum<spec['hard']['minimum_clearance_m']-1e-6:errors.append('HARD_SPATIAL_CLEARANCE')
    stage=Polygon(next(o['footprint_m'] for o in expected.values() if o['class']=='stage')).centroid
    mean=sum(math.dist(xy,[stage.x,stage.y]) for xy in centers.values())/n
    a=np.array(list(initial_centers.values()));b=np.array([centers[g] for g in sorted(centers)]);cost=np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2);rr,cc=linear_sum_assignment(cost);movement=float(cost[rr,cc].sum())
    if abs(layout['objective_metrics']['mean_stage_distance_m']-mean)>1e-7 or abs(layout['objective_metrics']['initializer_assignment_movement_m']-movement)>1e-7:errors.append('NUMERICAL_OBJECTIVES')
    for key,value in [('maximum_mean_stage_distance_m',mean),('maximum_assignment_movement_m',movement)]:
        if spec['hard'][key] is not None and value>spec['hard'][key]+1e-6:errors.append('HARD_UPPER_LIMIT')
    return dict(valid=not errors,errors=sorted(set(errors)),object_count=len(physical),allocated_counts=wanted,mean_stage_distance_m=mean,initializer_assignment_movement_m=movement,minimum_clearance_m=minimum,verified_functions=sorted(functions),protected_geometry_changes=0 if 'PINNED_OR_EXISTING_GEOMETRY_CHANGED' not in errors else 1)

def policy_from_spec(spec):return spec['policy_snapshot']

def validate_result(request,spec,response):
    errors=[];x=response['xai'];base={k:v for k,v in response.items() if k!='xai'}
    if x['response_payload_sha256']!=digest(base) or x['request_sha256']!=digest(request) or x['spec_sha256']!=spec['spec_sha256']:errors.append('XAI_BINDING')
    records=[]
    if response['status']=='success':
        if not response['candidate_layouts']:errors.append('EMPTY_SUCCESS')
        explanations={e['layout_id']:e for e in x['explanations']}
        if set(explanations)!={l['layout_id'] for l in response['candidate_layouts']}:errors.append('XAI_LAYOUT_SET')
        for l in response['candidate_layouts']:
            v=validate_layout(request,spec,l,response['initialization_centers_m']);records.append(dict(layout_id=l['layout_id'],**v));e=explanations.get(l['layout_id'],{})
            if e.get('layout_sha256')!=digest(l) or e.get('physical_object_count')!=v['object_count'] or e.get('allocated_counts')!=v['allocated_counts'] or e.get('verified_functions')!=v['verified_functions']:errors.append('XAI_FUNCTION_OR_COUNTS')
            if any(abs(e.get('metrics',{}).get(k,float('inf'))-v[k])>1e-7 for k in ['mean_stage_distance_m','initializer_assignment_movement_m','minimum_clearance_m','protected_geometry_changes']):errors.append('XAI_NUMERICAL_FIDELITY')
            text=e.get('text','');match=re.fullmatch(r'(\d+) physical objects; (\d+) separately represented zones; declared function/geometry checks passed\. Initializer displacement is not real furniture transport\.',text)
            if not match or int(match[1])!=len(l['objects']) or int(match[2])!=len(l['zones']):errors.append('XAI_TEXT_FIDELITY')
            if e.get('rule_trace')!=spec['derivation']:errors.append('XAI_RULE_TRACE')
        if any(not r['valid'] for r in records):errors.append('RAW_LAYOUT_INVALID')
        selected=response['selected_ids'];byid={l['layout_id']:l for l in response['candidate_layouts']}
        if not set(selected)<=set(byid) or len(selected)!=len(set(selected)) or len(selected)>3:errors.append('MENU_IDENTITIES')
        vectors=np.array([[l['objective_metrics'][k] for k in ['mean_stage_distance_m','initializer_assignment_movement_m']] for l in response['candidate_layouts']]);ranges=np.maximum(vectors.max(0)-vectors.min(0),1e-12)
        for i,s in enumerate(selected):
            for t in selected[:i]:
                a=np.array(list(byid[s]['group_centers_m'].values()));b=np.array(list(byid[t]['group_centers_m'].values()));cost=np.sum((a[:,None,:]-b[None,:,:])**2,axis=2);rr,cc=linear_sum_assignment(cost);rms=float(np.sqrt(np.mean(cost[rr,cc])));diff=max(abs(np.array(list(byid[s]['objective_metrics'].values()))-np.array(list(byid[t]['objective_metrics'].values())))/ranges)
                if rms<response['menu']['spatial_threshold_m']-1e-9 or diff<response['menu']['objective_threshold']-1e-9:errors.append('FABRICATED_MENU_DIVERSITY')
    elif response['candidate_layouts'] or response['selected_ids'] or x['explanations'] or x['denial_reason']!=response['reason']:errors.append('FALSE_SUCCESS_OR_DENIAL_XAI')
    return dict(valid=not errors,errors=sorted(set(errors)),layouts=records)
