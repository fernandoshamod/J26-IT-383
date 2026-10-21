"""Independent conservative grid route construction from exported objects, not fitness helpers.
All positive edges checked against unbuffered polygon distances and exact seating disks.
No-route on this grid is a failure to certify, not continuous-space impossibility.
"""
from usability_env import H,PP1,ROOT,read,save,digest,composed,ORIGIN,RADIUS,STEP
import math,collections,time
import numpy as np
import shapely
from shapely.geometry import Point,Polygon,LineString

def routes(c,l,step=STEP):
    circles=[(tuple(v),1.72+RADIUS) for v in l['group_centers_m'].values()]
    obstacles=[Polygon(o['footprint_coordinates_m']) for o in l['objects'] if o['class'] not in ['chair','round_table']]
    boundary=Polygon(c['boundary'])
    xs=np.arange(step/2,32,step);ys=np.arange(step/2,24,step);xx,yy=np.meshgrid(xs,ys)
    pts=shapely.points(xx,yy);ok=shapely.covers(boundary,pts)&(shapely.distance(boundary.boundary,pts)>=RADIUS)
    for centre,r in circles:ok &= (xx-centre[0])**2+(yy-centre[1])**2>=r*r
    for obstacle in obstacles:ok &= (~shapely.covers(obstacle,pts))&(shapely.distance(obstacle,pts)>=RADIUS)
    xy=np.stack([xx,yy],axis=-1)
    def edges_allowed(a,b):
        lines=shapely.linestrings(np.stack([a,b],axis=-2))
        legal=shapely.covers(boundary,lines)&(shapely.distance(boundary.boundary,lines)>=RADIUS-1e-9)
        for centre,r in circles:legal &= shapely.distance(Point(centre),lines)>=r-1e-9
        for o in obstacles:legal &= shapely.distance(o,lines)>=RADIUS-1e-9
        return legal
    horizontal=edges_allowed(xy[:,:-1],xy[:,1:]);vertical=edges_allowed(xy[:-1],xy[1:])
    def point(n):return (float(xs[n[1]]),float(ys[n[0]]))
    def edge(a,b):
        line=LineString([a,b])
        return boundary.covers(line) and line.distance(boundary.boundary)>=RADIUS-1e-9 and all(line.distance(Point(centre))>=r-1e-9 for centre,r in circles) and all(line.distance(o)>=RADIUS-1e-9 for o in obstacles)
    def cell(p):return (int(p[1]/step),int(p[0]/step))
    def inside(n):return 0<=n[0]<len(ys) and 0<=n[1]<len(xs)
    s=cell(ORIGIN);parents={}
    if inside(s) and ok[s] and edge(ORIGIN,point(s)):
        parents[s]=None;queue=collections.deque([s])
        while queue:
            u=queue.popleft()
            for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
                n=(u[0]+dy,u[1]+dx)
                if inside(n) and n not in parents and ok[n]:
                    # Grid edge may cut a curved disk although both nodes are free.
                    allowed=horizontal[u[0],min(u[1],n[1])] if dy==0 else vertical[min(u[0],n[0]),u[1]]
                    if allowed:parents[n]=u;queue.append(n)
    targets=[('seating',gid,(xy[0],xy[1]-2.12)) for gid,xy in l['group_centers_m'].items()]
    for z in l['zones']:
        f={'presentation':'stage','buffet':'buffet','dancing':'dance'}[z['function']]
        targets.append((f,z['zone_id'],tuple(Polygon(z['polygon']).centroid.coords[0])))
    results=[]
    for f,i,g in targets:
        nearest=cell(g)
        # A nearest grid node may fall inside a disk even when the exact endpoint is free.
        # Try nearby witnessed connectors; absence remains UNKNOWN, never a no-path proof.
        choices=[(nearest[0]+dy,nearest[1]+dx) for dy in range(-2,3) for dx in range(-2,3)]
        choices.sort(key=lambda n:math.dist(point(n),g) if inside(n) else math.inf)
        n=next((a for a in choices if a in parents and edge(point(a),g)),None)
        valid=n is not None;path=[]
        if valid:
            while n is not None:path.append(point(n));n=parents[n]
            path=[list(ORIGIN)]+[list(p) for p in path[::-1]]+[list(g)]
            assert all(edge(a,b) for a,b in zip(path,path[1:])), 'INDEPENDENT_PATH_EDGE_FAILURE'
        results.append(dict(function=f,target_id=i,goal=list(g),certified=bool(valid),path=path))
    return dict(all_certified=all(r['certified'] for r in results),targets=results,reachable_nodes=len(parents),step_m=step)

def validate(c,l,ref=None):
    started=time.perf_counter();local=composed(c,l,ref)
    if not local['valid']:return dict(valid=False,local=local,access=None,runtime_s=time.perf_counter()-started)
    r=routes(c,l)
    # Recompute numerical objectives directly from physical centroids and active stock IDs.
    groups=list(l['group_centers_m'].values());by={o['object_id']:o for o in l['objects']}
    centre=lambda i:tuple(Polygon(by[i]['footprint_coordinates_m']).centroid.coords[0])
    stage=centre(c['stage_id']);buffets=[centre(i) for i in c['buffet_pool_ids'] if i in by]
    service=sum(math.dist(g,stage)+.25*min(math.dist(g,b) for b in buffets) for g in groups)/4
    assert abs(service-l['objectives'][0])<1e-8
    return dict(valid=r['all_certified'],local=local,access=r,numerical_service_replay=service,runtime_s=time.perf_counter()-started)
