import math
import numpy as np
from shapely.geometry import Polygon
def validate_metric(req):
    if req.get('contract_id')!='STAGE_E_PP1_V1' or req.get('mode')!='initial_design':raise ValueError('INVALID_INTERNAL_ENGINE_CONTRACT')
    event=req['event_requirements'];guests=event['guest_count']
    if type(guests) is not int or not 0<guests<=240 or guests%8 or event['seats_per_table']!=8 or event['event_type']!='Wedding':raise ValueError('UNSUPPORTED_EVENT_REQUIREMENTS')
    clearance=req['optimization_request']['experimental_clearance_m'];seed=req['optimization_request']['seed']
    if not math.isfinite(clearance) or clearance<.5 or type(seed) is not int or seed<0:raise ValueError('INVALID_SEARCH_CONFIG')
    venue=Polygon(req['venue_twin']['boundary_polygon_m']);records=req['venue_twin']['fixed_obstacles'];fixed=[Polygon(o['footprint_coordinates_m']) for o in records]
    if not venue.is_valid or venue.area<=0 or min(venue.bounds[2]-venue.bounds[0],venue.bounds[3]-venue.bounds[1])<3.44:raise ValueError('INVALID_OR_TOO_SMALL_VENUE')
    if not records or sum(o['class']=='stage' for o in records)!=1:raise ValueError('EXACTLY_ONE_STAGE_REQUIRED')
    if any(not p.is_valid or p.area<=0 or not venue.covers(p) for p in fixed):raise ValueError('INVALID_FIXED_GEOMETRY')
    if any(a.intersection(b).area>1e-8 for i,a in enumerate(fixed) for b in fixed[:i]):raise ValueError('OVERLAPPING_FIXED_GEOMETRY')
    return venue,fixed,records,guests//8,float(clearance),seed
def select_nondominated(values,measure,maximum=8):
    # Keep only genuinely feasible, spatially distinct solutions, then rank
    # nondominated objective vectors. No manufactured alternative count.
    unique={}
    for x in values:
        x=np.asarray(x,float);m=measure(x)
        if m['feasible']:unique.setdefault(tuple(np.round(x,8)),(x,m['F']))
    candidates=list(unique.values());nd=[]
    for i,(x,f) in enumerate(candidates):
        if not any(all(a<=b+1e-10 for a,b in zip(g,f)) and any(a<b-1e-10 for a,b in zip(g,f)) for j,(_,g) in enumerate(candidates) if i!=j):nd.append((x,f))
    nd.sort(key=lambda item:(item[1][1],item[1][0]))
    if len(nd)>maximum:
        indexes=np.linspace(0,len(nd)-1,maximum,dtype=int);nd=[nd[i] for i in indexes]
    if not nd:raise ValueError('NO_FEASIBLE_CANDIDATES_FOUND_NOT_AN_INFEASIBILITY_PROOF')
    return [x for x,f in nd]
def limits(req,stage,movement):
    hard=req.get('hard_limits',{});constraints=[]
    if hard.get('maximum_mean_stage_distance_m') is not None:constraints.append(stage-hard['maximum_mean_stage_distance_m'])
    if hard.get('maximum_total_movement_m') is not None:constraints.append(movement-hard['maximum_total_movement_m'])
    return constraints
