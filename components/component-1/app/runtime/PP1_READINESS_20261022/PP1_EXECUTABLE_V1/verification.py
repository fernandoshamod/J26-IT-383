"""Reuse the validated V2 checker, adding complete metric/hard-bound checks.
The copied verifier permits retained IDs during guest reduction without renumbering.
"""
import sys,types,math
from support import FUNCTIONAL,digest,ResearchError
source=(FUNCTIONAL/'independent_geometry.py').read_text(encoding='utf-8')
old="expected_groups={f'seating_group_{i:04d}' for i in range(1,n+1)}"
assert source.count(old)==1
source=source.replace(old,"expected_groups=set(request.get('expected_group_ids', [f'seating_group_{i:04d}' for i in range(1,n+1)]))")
module=types.ModuleType('independent_geometry_pp1');exec(compile(source,str(FUNCTIONAL/'independent_geometry.py'),'exec'),module.__dict__)
def verify_final(layout,request,reference,reference_layout,hard,locked_ids):
    metrics=module.verify(layout,request,reference,reference_layout)
    if not metrics['valid']:raise ResearchError('FINAL_GEOMETRY_OR_OBJECTIVE_VALIDATION_FAILED',{'errors':metrics['errors']})
    for key,value in layout['objective_metrics'].items():
        if not isinstance(value,(int,float,str)) or isinstance(value,bool):raise ResearchError('INVALID_OBJECTIVE_TYPE',{'field':key})
        if isinstance(value,(int,float)) and not math.isfinite(value):raise ResearchError('NONFINITE_OBJECTIVE',{'field':key})
    # Check every reported clearance, not only the two optimization objectives.
    from shapely.geometry import Point,Polygon
    centers=layout['group_centers_m'];env={g:Point(*xy).buffer(1.72,quad_segs=32) for g,xy in centers.items()};fixed=[Polygon(o['footprint_coordinates_m']) for o in request['venue_twin']['fixed_obstacles']]
    obj=layout['objective_metrics']
    if 'minimum_group_clearance_m' in obj:
        gaps=[max(0.,math.dist(a,b)-3.44) for i,a in enumerate(centers.values()) for b in list(centers.values())[:i]]+[e.distance(f) for e in env.values() for f in fixed]
        if abs(obj['minimum_group_clearance_m']-min(gaps))>1e-6:raise ResearchError('REPORTED_CLEARANCE_MISMATCH')
    if 'minimum_protected_clearance_m' in obj:
        target=request['revision_request']['group_id'];gaps=[env[target].distance(e) for g,e in env.items() if g!=target]+[env[target].distance(f) for f in fixed]
        if abs(obj['minimum_protected_clearance_m']-min(gaps))>1e-6:raise ResearchError('REPORTED_PROTECTED_CLEARANCE_MISMATCH')
    movement=metrics['total_group_movement'] if request['mode']=='adaptive_revision' else metrics['assignment_movement']
    for key,value in [('maximum_mean_stage_distance_m',metrics['mean_stage_distance']),('maximum_total_movement_m',movement)]:
        if hard[key] is not None and value>hard[key]+1e-6:raise ResearchError('HARD_UPPER_BOUND_VIOLATED',{'constraint':key,'measured':value,'limit':hard[key]})
    if reference_layout:
        originals={o['object_id']:o for o in reference_layout['objects']}
        for o in layout['objects']:
            if o.get('group_id') in locked_ids:
                old=originals.get(o['object_id'])
                if old is None or o!=old:raise ResearchError('LOCKED_OBJECT_NOT_IDENTICAL',{'object_id':o['object_id']})
        if any(centers[g]!=reference[g] for g in locked_ids):raise ResearchError('LOCKED_CENTER_CHANGED')
    metrics['locked_group_ids']=sorted(locked_ids);metrics['layout_sha256']=digest(layout)
    return metrics
