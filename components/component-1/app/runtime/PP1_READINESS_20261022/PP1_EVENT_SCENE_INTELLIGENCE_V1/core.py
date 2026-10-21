"""Shared input/evidence and output representation gates; no demand derivation."""
import math
from pathlib import Path
from PIL import Image
from shapely.geometry import Polygon,box
from common import *
from models import venue_payload,party_payload,planner_payload

def issue(code,status='conflict',identity=None):return dict(code=code,status=status,identity=identity)
def status(issues):
    return next((s for s in ['rejected','conflict','pending_review','unsupported'] if any(x['status']==s for x in issues)),'accepted')
def policy_check(policy):
    if policy.get('schema')!='EXPLICIT_EXPERIMENTAL_EVENT_POLICIES_V1':raise GateError('UNKNOWN_POLICY_SCHEMA')
    handlers={'dining_area','audience_area','stage_access','buffet_access','celebration_area','conference_area','networking_area','performance_area','dance_area'}
    for profile in policy['profiles'].values():
        if any(f not in policy['functions'] for f in profile['required_functions']+profile['optional_functions']):raise GateError('UNKNOWN_FUNCTION_HANDLER')
    for f in policy['functions'].values():
        if any(z not in handlers for z in f['zones']):raise GateError('UNKNOWN_ZONE_HANDLER')
        for r in f['objects']:
            if r['class'] not in policy['catalog'] or r['op'] not in ['guests','constant','ceil_guests']:raise GateError('INVALID_POLICY_RULE')
            for k in ['divisor','value']:
                if k in r and (type(r[k]) is not int or r[k]<=0):raise GateError('INVALID_POLICY_QUANTITY')
    for c in policy['catalog'].values():
        if c['shape'] not in ['circle','rectangle']:raise GateError('UNKNOWN_CATALOG_SHAPE')
        keys=['radius_m'] if c['shape']=='circle' else ['width_m','depth_m']
        if any(not isinstance(c[k],(float,int)) or not math.isfinite(c[k]) or c[k]<=0 for k in keys):raise GateError('INVALID_CATALOG_DIMENSIONS')
    for x in policy['zone_parameters'].values():
        if not math.isfinite(x) or x<=0:raise GateError('INVALID_ZONE_POLICY')

def compatible(obj,policy):
    c=policy['catalog'].get(obj.class_name)
    if not c or c['shape']!='rectangle':return False
    p=Polygon(obj.footprint_m);a,b,x,y=p.bounds
    return p.equals(box(a,b,x,y)) and abs(x-a-c['width_m'])<1e-7 and abs(y-b-c['depth_m'])<1e-7

def preflight(r,policy):
    issues=[];v=r.venue;src=v.source
    try:
        policy_check(policy);p=Path(src.path).resolve()
        if not p.is_relative_to(ROOT) or not p.is_file() or filehash(p)!=src.sha256:raise GateError('SOURCE_HASH_OR_PATH_MISMATCH')
        with Image.open(p,formats=['PNG','JPEG']) as im:
            if im.size!=(src.width_px,src.height_px):raise GateError('SOURCE_DIMENSION_MISMATCH')
        assert_evidence(v.review.evidence,src.sha256,venue_payload(v))
        assert_evidence(r.client.evidence,src.sha256,party_payload(r.client))
        assert_evidence(r.planner.evidence,src.sha256,planner_payload(r))
        ratios=[];controls=[]
        for c in v.controls:
            for pt in [c.a_px,c.b_px]:
                if not (0<=pt[0]<=src.width_px and 0<=pt[1]<=src.height_px):raise GateError('CALIBRATION_OUTSIDE_SOURCE')
            if math.dist(c.a_px,c.b_px)<=1:raise GateError('DEGENERATE_CALIBRATION')
            ratios.append(c.distance_m/math.dist(c.a_px,c.b_px));controls.append(tuple(sorted([tuple(c.a_px),tuple(c.b_px)])))
        if len(set(controls))!=len(controls) or (max(ratios)-min(ratios))/max(ratios)>.02:raise GateError('INCONSISTENT_OR_DUPLICATE_CALIBRATION')
        scale=sum(ratios)/len(ratios)
        for pt in v.boundary_px+[v.origin_px]:
            if len(pt)!=2 or not (0<=pt[0]<=src.width_px and 0<=pt[1]<=src.height_px):raise GateError('SOURCE_BOUNDARY_OR_ORIGIN_INVALID')
        transformed=Polygon([[(x-v.origin_px[0])*scale,(y-v.origin_px[1])*scale] for x,y in v.boundary_px]);venue=Polygon(v.boundary_m)
        if not venue.is_valid or venue.area<=0 or not transformed.is_valid or transformed.hausdorff_distance(venue)>1e-8:raise GateError('METRIC_BOUNDARY_MISMATCH')
        if len({o.instance_id for o in v.existing})!=len(v.existing):raise GateError('DUPLICATE_EXISTING_ID')
        shapes=[]
        for o in v.existing:
            q=Polygon(o.footprint_m)
            if not q.is_valid or q.area<=0 or not venue.covers(q):raise GateError('EXISTING_GEOMETRY_INVALID')
            if any(q.intersection(x).area>1e-8 for x in shapes):raise GateError('EXISTING_OBJECT_OVERLAP')
            shapes.append(q)
    except (GateError,ValueError,OSError,KeyError) as e:issues.append(issue(str(e),'rejected'))
    if src.domain=='real_source':
        issues.append(issue('EXTERNAL_REVIEW_VALIDATION_UNSUPPORTED','unsupported'))
    elif src.domain=='controlled_synthetic' and (src.origin!='CONTROLLED_GENERATOR' or v.review.scope!='SIMULATED_FIXTURE'):
        issues.append(issue('SOURCE_REVIEW_SCOPE_MISMATCH'))
    elif src.domain=='plan_derived_controlled' and (src.origin!='PLAN_DRAWING_INTERPRETATION' or v.review.scope!='PLAN_DERIVED_SIMULATED'):
        issues.append(issue('PLAN_INTERPRETATION_SCOPE_MISMATCH'))
    if v.review.status!='approved':issues.append(issue('VENUE_REVIEW_REQUIRED','pending_review'))
    for p in [r.client,r.planner]:
        if p.policy_sha256!=digest(policy):issues.append(issue('POLICY_APPROVAL_BINDING_MISMATCH','rejected',p.role))
        if p.approval_status!='approved':issues.append(issue('PARTY_APPROVAL_REQUIRED','pending_review',p.role))
        if p.scope!=v.review.scope:issues.append(issue('ACTOR_SCOPE_MISMATCH',identity=p.role))
        if len(p.optional_functions)!=len(set(p.optional_functions)):issues.append(issue('DUPLICATE_FUNCTION',identity=p.role))
    if r.client.actor_id==r.planner.actor_id:issues.append(issue('ACTOR_SEPARATION_REQUIRED'))
    for k in ['event_type','guest_count','optional_functions']:
        a=getattr(r.client,k);b=getattr(r.planner,k)
        if (set(a)!=set(b) if k=='optional_functions' else a!=b):issues.append(issue('CLIENT_PLANNER_'+k.upper()+'_CONFLICT'))
    ids={o.instance_id:o for o in v.existing};seen=set()
    for a in r.actions:
        if (a.instance_id,a.action) in seen:issues.append(issue('DUPLICATE_ACTION',identity=a.instance_id))
        seen.add((a.instance_id,a.action));o=ids.get(a.instance_id)
        if o is None:issues.append(issue('UNKNOWN_ACTION_OBJECT',identity=a.instance_id));continue
        if a.actor_id!=r.planner.actor_id or a.scope!=r.planner.scope:issues.append(issue('ACTION_AUTHORITY_MISMATCH',identity=a.instance_id))
        if a.approved and a.action in ['remove','move'] and (o.status=='fixed' or o.protected):issues.append(issue('PROTECTED_OR_FIXED_ACTION',identity=a.instance_id))
        if a.approved and a.action=='move':issues.append(issue('EXISTING_RELOCATION_UNSUPPORTED','unsupported',a.instance_id))
    for iid in ids:
        active={a.action for a in r.actions if a.instance_id==iid and a.approved}
        if 'remove' in active and len(active)>1:issues.append(issue('CONTRADICTORY_OBJECT_ACTIONS',identity=iid))
    for o in v.existing:
        if o.status=='uncertain' or o.review_status!='approved':issues.append(issue('OBJECT_REVIEW_REQUIRED','pending_review',o.instance_id))
        if o.class_name in ['round_table','chair']:issues.append(issue('EXISTING_SEATING_REGROUPING_UNSUPPORTED','unsupported',o.instance_id))
    return issues

def effective_hard(r):
    a=r.client.hard;b=r.planner.hard
    def upper(k):
        v=[x for x in [getattr(a,k),getattr(b,k)] if x is not None];return min(v) if v else None
    return dict(minimum_clearance_m=max(a.minimum_clearance_m,b.minimum_clearance_m),maximum_mean_stage_distance_m=upper('maximum_mean_stage_distance_m'),maximum_assignment_movement_m=upper('maximum_assignment_movement_m'))

def assemble(r,policy,functions,demand,reused,removed,issues,method):
    """Common representation/physical gate for both independent decision strategies."""
    if any(i['status']=='rejected' for i in issues):
        # Invalid source/identity/metric inputs have no defensible allocation.
        s=dict(schema='EVENT_SCENE_SPECIFICATION_V1',policy_snapshot=policy,event_id=r.event_id,event_type=r.client.event_type,status='rejected',issues=sorted({digest(x):x for x in issues}.values(),key=lambda x:(x['code'],str(x['identity']))),binding=dict(request_sha256=digest(r.model_dump()),venue_id=r.venue.venue_id,venue_version=r.venue.version,venue_sha256=digest(r.venue.model_dump()),source_sha256=r.venue.source.sha256,policy_sha256=digest(policy)),guest_count=r.client.guest_count,functions=sorted(functions),required_quantities=demand,allocations=[],new_equipment=[],retained_existing=[],removed_existing=[],zones=[],hard=effective_hard(r),derivation=[],stock_decisions=[],scope=dict(review_scope=r.venue.review.scope,real_planner_authentication=False,physical_supply_confirmed=False,detailed_safety_validated=False,sgcn_used=False,weather_used=False),method=method)
        s['spec_sha256']=digest(s);return s
    objects={o.instance_id:o for o in r.venue.existing};allocated={x['instance_id'] for x in reused};new=[];allocations=list(reused);traces=[]
    placements={(p.class_name,p.ordinal):p for p in r.placements}
    if len(placements)!=len(r.placements):issues.append(issue('DUPLICATE_PLACEMENT'))
    used=set()
    for cls,n in sorted(demand.items()):
        have=sum(a['class']==cls for a in reused)
        for k in range(1,n-have+1):
            iid=f'{r.event_id}__new_{cls}_{k:03d}';placement=placements.get((cls,k));ring=placement.footprint_m if placement else None
            if iid in objects:issues.append(issue('NEW_EXISTING_ID_COLLISION','rejected',iid))
            if placement:used.add((cls,k))
            if cls not in ['chair','round_table'] and ring is None:issues.append(issue('NEW_EQUIPMENT_PLACEMENT_REQUIRED','pending_review',iid))
            rec=dict(instance_id=iid,**{'class':cls},origin='new_event_equipment',footprint_m=ring,catalog=policy['catalog'][cls],fixed_by_design=cls not in ['chair','round_table'])
            new.append(rec);allocations.append(dict(instance_id=iid,**{'class':cls},origin='new_event_equipment'))
    for key in set(placements)-used:issues.append(issue('UNUSED_PLACEMENT',identity=str(key)))
    retained=[dict(instance_id=o.instance_id,**{'class':o.class_name},origin='observed_existing',footprint_m=o.footprint_m,protected=o.protected,status=o.status,active_supply=o.instance_id in allocated) for o in r.venue.existing if o.instance_id not in removed]
    zones=[];venue=Polygon(r.venue.boundary_m)
    physical={o['instance_id']:o for o in retained+new}
    for function in functions:
        for kind in policy['functions'][function]['zones']:
            if kind in ['stage_access','buffet_access']:
                cls='stage' if kind=='stage_access' else 'buffet_counter'
                for a in allocations:
                    if a['class']!=cls:continue
                    o=physical[a['instance_id']]
                    if o['footprint_m']:
                        x,y,b,t=Polygon(o['footprint_m']).bounds;d=policy['zone_parameters']['access_depth_m']
                        zones.append(dict(zone_id=kind+'__'+a['instance_id'],kind=kind,exclusive=True,anchor_id=a['instance_id'],footprint_m=[list(v) for v in box(x,y-d,b,y).exterior.coords],derived_from=function,geometry_origin='explicit_south_facing_catalog_policy'))
            elif kind=='dance_area':
                if r.dance_zone_m is None:issues.append(issue('DANCE_ZONE_REQUIRED','pending_review'))
                else:
                    if Polygon(r.dance_zone_m).area<policy['zone_parameters']['dance_min_area_m2']:issues.append(issue('DANCE_AREA_BELOW_DECLARED_POLICY'))
                    zones.append(dict(zone_id=kind,kind=kind,exclusive=True,footprint_m=r.dance_zone_m,derived_from=function,geometry_origin='explicit_planner_design_control'))
            else:zones.append(dict(zone_id=kind,kind=kind,exclusive=False,footprint_m=r.venue.boundary_m,derived_from=function,geometry_origin='broad_activity_membership_not_detailed_access_proof'))
    if 'dancing' not in functions and r.dance_zone_m is not None:issues.append(issue('UNREQUESTED_DANCE_ZONE'))
    shapes=[]
    for o in retained+new:
        if o['footprint_m'] is None:continue
        q=Polygon(o['footprint_m']);cls=o['class'];cat=policy['catalog'].get(cls)
        if not q.is_valid or q.area<=0 or not venue.covers(q):issues.append(issue('DESIGN_GEOMETRY_INVALID',identity=o['instance_id']))
        if cat and o['origin']=='new_event_equipment' and cat['shape']=='rectangle':
            x,y,b,t=q.bounds
            if not q.equals(box(x,y,b,t)) or abs(b-x-cat['width_m'])>1e-7 or abs(t-y-cat['depth_m'])>1e-7:issues.append(issue('NEW_CATALOG_GEOMETRY_MISMATCH',identity=o['instance_id']))
        if any(q.intersection(p).area>1e-8 for p in shapes):issues.append(issue('DESIGN_OBJECT_OVERLAP',identity=o['instance_id']))
        shapes.append(q)
    exclusive=[]
    for z in zones:
        q=Polygon(z['footprint_m'])
        if not q.is_valid or q.area<=0 or not venue.covers(q):issues.append(issue('ZONE_GEOMETRY_INVALID',identity=z['zone_id']))
        if z['exclusive']:
            if any(q.intersection(p).area>1e-8 for p in shapes+exclusive):issues.append(issue('EXCLUSIVE_ZONE_OVERLAP',identity=z['zone_id']))
            exclusive.append(q)
    for f in functions:traces.append(dict(function=f,rule=policy['functions'][f],evidence_roles=['client','planner'],policy_version=policy['version']))
    for a in allocations:a['functions']=sorted(f for f in functions if any(rule['class']==a['class'] for rule in policy['functions'][f]['objects']))
    issues=sorted({digest(x):x for x in issues}.values(),key=lambda x:(x['code'],str(x['identity'])))
    s=dict(schema='EVENT_SCENE_SPECIFICATION_V1',policy_snapshot=policy,event_id=r.event_id,event_type=r.client.event_type,status=status(issues),issues=issues,
      binding=dict(request_sha256=digest(r.model_dump()),venue_id=r.venue.venue_id,venue_version=r.venue.version,venue_sha256=digest(r.venue.model_dump()),source_sha256=r.venue.source.sha256,policy_sha256=digest(policy)),
      guest_count=r.client.guest_count,functions=sorted(functions),required_quantities=demand,allocations=sorted(allocations,key=lambda x:x['instance_id']),new_equipment=new,retained_existing=retained,removed_existing=sorted(removed),zones=zones,hard=effective_hard(r),derivation=traces,
      stock_decisions=[dict(instance_id=o.instance_id,decision='removed_with_explicit_permission' if o.instance_id in removed else 'reused_in_place' if o.instance_id in allocated else 'retained_as_obstacle_not_counted_as_supply',reason='Explicit approved compatible reuse only; uncertainty never counts; retained geometry stays locked') for o in r.venue.existing],
      scope=dict(review_scope=r.venue.review.scope,real_planner_authentication=False,physical_supply_confirmed=False,detailed_safety_validated=False,sgcn_used=False,weather_used=False),method=method)
    s['spec_sha256']=digest(s);return s
