"""Independent serialized-geometry checker, not an engine replay wrapper.
No engine or readiness V1 geometry helper is imported. Polygon checks use
Shapely plus a second OpenCV convex-intersection implementation. Analytic
circles test furniture positions/radii; stable IDs and raw vertex locks persist.
"""
import math
from collections import Counter
import numpy as np
import cv2
from shapely.geometry import Polygon,Point
from scipy.optimize import linear_sum_assignment
def finite(value):
    return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value)
def centroid(ring):
    pts=np.array(ring,float)
    if np.array_equal(pts[0],pts[-1]):pts=pts[:-1]
    cross=pts[:,0]*np.roll(pts[:,1],-1)-np.roll(pts[:,0],-1)*pts[:,1];signed=float(cross.sum())
    if abs(signed)<1e-12:raise ValueError('DEGENERATE_POLYGON')
    return np.array([((pts[:,0]+np.roll(pts[:,0],-1))*cross).sum(),((pts[:,1]+np.roll(pts[:,1],-1))*cross).sum()])/(3*signed)
def verify(layout,request,reference,reference_layout=None,require_metrics=True):
    errors=[];objects=layout.get('objects',[]);centers=layout.get('group_centers_m',{});n=request['event_requirements']['guest_count']//8
    expected_groups={f'seating_group_{i:04d}' for i in range(1,n+1)}
    if set(centers)!=expected_groups:errors.append('GROUP_ID_SET')
    if set(reference)!=expected_groups:errors.append('REFERENCE_GROUP_ID_SET')
    for xy in list(centers.values())+list(reference.values()):
        if not isinstance(xy,list) or len(xy)!=2 or not all(map(finite,xy)):raise ValueError('NONFINITE_OR_MALFORMED_CENTER')
    fixed={o['object_id']:o for o in request['venue_twin']['fixed_obstacles']}
    expected=set(fixed)|{g+'_'+s for g in expected_groups for s in ['table']+[f'chair_{k:02d}' for k in range(1,9)]}
    ids=[o['object_id'] for o in objects]
    if len(ids)!=len(set(ids)) or set(ids)!=expected:errors.append('OBJECT_ID_SET_OR_DUPLICATE')
    shapes=[];polyc=[];positions={};radii={};group_counts={g:Counter() for g in expected_groups};locked_count=0;max_shape_error=0.;refobjects={o['object_id']:o for o in reference_layout['objects']} if reference_layout else {}
    target=request.get('revision_request',{}).get('group_id');adaptive=request['mode']=='adaptive_revision';locks=expected_groups-{target} if adaptive else set()
    for ob in objects:
        ring=ob['footprint_coordinates_m']
        if len(ring)<4 or any(len(pt)!=2 or not all(map(finite,pt)) for pt in ring):raise ValueError('INVALID_OR_NONFINITE_RING')
        p=Polygon(ring)
        if not p.is_valid or p.area<=0:raise ValueError('INVALID_POLYGON')
        shapes.append(p);c=centroid(ring);positions[ob['object_id']]=c;polyc.append(c)
        gid=ob.get('group_id')
        if ob['object_id'] in fixed:
            if ob['class']!=fixed[ob['object_id']]['class'] or ring!=fixed[ob['object_id']]['footprint_coordinates_m'] or gid is not None:errors.append('FIXED_OBJECT_CHANGED')
            continue
        if gid not in expected_groups:errors.append('UNEXPECTED_OBJECT_GROUP');continue
        group_counts[gid][ob['class']]+=1;center=np.array(centers[gid]);category=ob['class']
        if category=='round_table':expected_center=center;radius=.8
        elif category=='chair':
            k=int(ob['object_id'].rsplit('_',1)[1])-1;expected_center=center+1.45*np.array([math.cos(2*math.pi*k/8),math.sin(2*math.pi*k/8)]);radius=.27
        else:errors.append('WRONG_GROUP_CLASS');continue
        if ob['object_id']!=(gid+'_table' if category=='round_table' else gid+f'_chair_{k+1:02d}'):errors.append('ID_GROUP_INCONSISTENCY')
        pts=np.array(ring[:-1],float);shape_error=max(float(np.linalg.norm(c-expected_center)),float(np.max(np.abs(np.linalg.norm(pts-c,axis=1)-radius))));max_shape_error=max(max_shape_error,shape_error)
        radii[ob['object_id']]=radius
        if gid in locks and ob['object_id'] in refobjects and ring!=refobjects[ob['object_id']]['footprint_coordinates_m']:locked_count+=1
    if any(v!={'round_table':1,'chair':8} for v in group_counts.values()):errors.append('GROUP_CLASS_COUNTS')
    if max_shape_error>1e-8:errors.append('SERIALIZED_FOOTPRINT_CENTER_OR_RADIUS')
    if locked_count:errors.append('LOCKED_OBJECT_VERTICES_CHANGED')
    venue=Polygon(request['venue_twin']['boundary_polygon_m']);outside=sum(not venue.covers(p) for p in shapes);overlap=0;cv_overlap=0;convex=True
    for i,a in enumerate(shapes):
        aa=np.array(a.exterior.coords[:-1],dtype=np.float32)
        convex=convex and bool(cv2.isContourConvex(aa))
        for j in range(i):
            b=shapes[j]
            # Axis-aligned bounding boxes avoid needless kernel calls.
            if a.bounds[2]<=b.bounds[0] or b.bounds[2]<=a.bounds[0] or a.bounds[3]<=b.bounds[1] or b.bounds[3]<=a.bounds[1]:continue
            if a.intersection(b).area>1e-8:overlap+=1
            bb=np.array(b.exterior.coords[:-1],dtype=np.float32)
            if cv2.isContourConvex(aa) and cv2.isContourConvex(bb):
                ar,_=cv2.intersectConvexConvex(aa,bb)
                if ar>1e-5:cv_overlap+=1
    env=[Point(*centers[g]).buffer(1.72,quad_segs=32) for g in sorted(centers)];obs=[Polygon(o['footprint_coordinates_m']) for o in fixed.values()]
    gaps=[a.distance(b) for i,a in enumerate(env) for b in env[:i]]+[a.distance(b) for a in env for b in obs];min_gap=min(gaps);env_outside=sum(not venue.covers(p) for p in env)
    ds={g:math.dist(centers[g],reference[g]) for g in sorted(centers)};unauthorized=sum(ds[g]>1e-9 for g in locks)
    if outside or overlap or cv_overlap or env_outside or min_gap<request['optimization_request']['experimental_clearance_m']-1e-6 or unauthorized:errors.append('SPATIAL_CONSTRAINT_VIOLATION')
    stage=next(centroid(o['footprint_coordinates_m']) for o in fixed.values() if o['class']=='stage');mean_stage=sum(math.dist(c,stage) for c in centers.values())/len(centers)
    sortedg=sorted(centers);cost=np.array([[math.dist(reference[g],centers[h]) for h in sortedg] for g in sortedg]);a,b=linear_sum_assignment(cost);assignment=float(cost[a,b].sum())
    individual=sum(ds[o['group_id']] for o in objects if o.get('group_id') in ds);moved_objects=sum(ds[o['group_id']]>1e-9 for o in objects if o.get('group_id') in ds)
    measured={'mean_stage_distance':mean_stage,'total_group_movement':sum(ds.values()),'assignment_movement':assignment,'total_individual_object_movement':individual,'moved_group_count':sum(d>1e-9 for d in ds.values()),'moved_object_count':moved_objects,'minimum_clearance':min_gap,'object_count':len(objects),'outside_count':outside,'overlap_count':overlap,'second_kernel_overlap_count':cv_overlap,'convex_objects':convex,'envelopes_outside':env_outside,'locked_object_vertex_changes':locked_count,'unauthorized_movement_count':unauthorized,'locked_group_count':len(locks),'max_footprint_error_m':max_shape_error}
    objective=layout.get('objective_metrics',{});expectedmetrics={'stage_distance_m':math.dist(centers[target],stage),'identity_based_relocation_m':sum(ds.values())} if adaptive else {'average_stage_distance_m':mean_stage,'reference_displacement_m':assignment}
    metricerrors={}
    for key,v in expectedmetrics.items():
        if key not in objective:
            if require_metrics:errors.append('MISSING_OBJECTIVE:'+key)
        elif not finite(objective[key]):errors.append('NONFINITE_OBJECTIVE:'+key)
        else:
            metricerrors[key]=abs(objective[key]-v)
            if metricerrors[key]>1e-6:errors.append('OBJECTIVE_MISMATCH:'+key)
    measured['objective_errors_m']=metricerrors;measured['errors']=sorted(set(errors));measured['valid']=not errors
    return measured
